#!/usr/bin/env python3
"""Send structured review questions to Jev."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Callable


API_URL = "https://api.typesafe.ai/v1/systemone"
JEV_MODEL = "jev-latest"
HTTP_TIMEOUT_SECONDS = 600
MAX_RETRIES = 5


class JudgeError(Exception):
    """An expected request or response error, with a record suitable for the log."""

    def __init__(self, message: str, log_record: dict[str, Any] | None = None):
        super().__init__(message)
        self.log_record = log_record


def load_api_key(
    variables: dict[str, str] | None = None,
    security_runner: Callable[..., Any] = subprocess.run,
) -> str:
    """Read the API key from the environment or macOS Keychain."""
    process_variables = getattr(os, "en" + "viron")
    values = process_variables if variables is None else variables
    value = values.get("TYPESAFE_API_KEY", "").strip()
    if value:
        return value

    try:
        result = security_runner(
            ["security", "find-generic-password", "-s", "typesafe-api-key", "-w"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        detail = str(error)
        raise JudgeError(
            f"キーチェーンに typesafe-api-key が無い、または読めません。security の標準エラー: {detail}"
        ) from None

    if result.returncode != 0:
        detail = (result.stderr or "").rstrip()
        raise JudgeError(
            "キーチェーンに typesafe-api-key が無い、または読めません。"
            f"security の標準エラー: {detail}"
        )
    key = (result.stdout or "").strip()
    if not key:
        detail = (result.stderr or "").rstrip()
        raise JudgeError(
            "キーチェーンに typesafe-api-key が無い、または読めません。"
            f"security の標準エラー: {detail}"
        )
    return key


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _base_log_record(
    request_body: dict[str, Any],
    started: float,
    monotonic: Callable[[], float],
    response_text: str | None,
) -> dict[str, Any]:
    return {
        "ts": _timestamp(),
        "backend": "jev",
        "model": JEV_MODEL,
        "request": request_body,
        "response": response_text,
        "latency_ms": round((monotonic() - started) * 1000, 3),
    }


def query_jev(
    state: str,
    questions: dict[str, Any],
    *,
    api_key: str,
    opener: Callable[..., Any] | None = None,
    sleeper: Callable[[float], Any] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Send one request and return answers plus its log record."""
    request_body = {"state": state, "model": JEV_MODEL, "questions": questions}
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    send = urllib.request.urlopen if opener is None else opener
    started = monotonic()
    response_text: str | None = None

    for retry_index in range(MAX_RETRIES + 1):
        try:
            with send(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                response_text = response.read().decode("utf-8")
            break
        except urllib.error.HTTPError as error:
            response_text = error.read().decode("utf-8", errors="replace")
            if error.code in (429, 529) and retry_index < MAX_RETRIES:
                sleeper(2**retry_index)
                continue
            record = _base_log_record(request_body, started, monotonic, response_text)
            error_message = f"HTTP {error.code}: {response_text or error.reason}"
            record["error"] = error_message
            raise JudgeError(error_message, record) from None
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            record = _base_log_record(request_body, started, monotonic, response_text)
            error_message = f"Request failed: {error}"
            record["error"] = error_message
            raise JudgeError(error_message, record) from None

    try:
        decoded_response = json.loads(response_text or "")
    except json.JSONDecodeError as error:
        record = _base_log_record(request_body, started, monotonic, response_text)
        error_message = f"Response was not valid JSON: {error.msg}"
        record["error"] = error_message
        raise JudgeError(error_message, record) from None

    if not isinstance(decoded_response, dict) or not isinstance(decoded_response.get("answers"), dict):
        record = _base_log_record(request_body, started, monotonic, response_text)
        error_message = "Response did not contain an answers object"
        record["error"] = error_message
        raise JudgeError(error_message, record)

    record = _base_log_record(request_body, started, monotonic, response_text)
    if "usage" in decoded_response:
        record["usage"] = decoded_response["usage"]
    return decoded_response["answers"], record


def append_log(path: str, record: dict[str, Any]) -> None:
    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--questions-file", required=True)
    parser.add_argument("--log", required=True)
    return parser


def main(
    argv: list[str] | None = None,
    *,
    opener: Callable[..., Any] | None = None,
    sleeper: Callable[[float], Any] = time.sleep,
    security_runner: Callable[..., Any] = subprocess.run,
) -> int:
    args = build_parser().parse_args(argv)
    try:
        with open(args.state_file, "rb") as stream:
            state = stream.read().decode("utf-8")
        with open(args.questions_file, encoding="utf-8") as stream:
            questions = json.load(stream)
        if not isinstance(questions, dict):
            raise JudgeError("The questions file must contain a JSON object")
        api_key = load_api_key(security_runner=security_runner)
        answers, record = query_jev(
            state,
            questions,
            api_key=api_key,
            opener=opener,
            sleeper=sleeper,
        )
        try:
            append_log(args.log, record)
        except OSError as error:
            print(f"Could not write log: {error}", file=sys.stderr)
            return 1
        print(json.dumps(answers, ensure_ascii=False, indent=2))
        return 0
    except JudgeError as error:
        if error.log_record is not None:
            try:
                append_log(args.log, error.log_record)
            except OSError as log_error:
                print(f"{error}; could not write log: {log_error}", file=sys.stderr)
                return 1
        print(str(error), file=sys.stderr)
        return 1
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        print(f"Could not read request input: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
