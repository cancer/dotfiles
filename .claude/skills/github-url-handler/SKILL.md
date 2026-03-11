---
name: github-url-handler
description: When a GitHub URL is provided in the user's message, use the gh CLI command instead of WebFetch to retrieve the information. This applies to issues, pull requests, repositories, files, and directories.
---

# GitHub URL Handler Skill

## 指示
GitHub URLが提供されたら、WebFetchではなくghコマンドを使用すること。

## URLとコマンドの対応

- **リポジトリ**: `https://github.com/{owner}/{repo}`
  → `gh repo view {owner}/{repo}`

- **Issue**: `https://github.com/{owner}/{repo}/issues/{number}`
  → `gh issue view {number} --repo {owner}/{repo}`

- **Pull Request**: `https://github.com/{owner}/{repo}/pull/{number}`
  → `gh pr view {number} --repo {owner}/{repo}`

- **ファイル**: `https://github.com/{owner}/{repo}/blob/{branch}/{path}`
  → `gh api repos/{owner}/{repo}/contents/{path}?ref={branch}`

- **ディレクトリ**: `https://github.com/{owner}/{repo}/tree/{branch}/{path}`
  → `gh api repos/{owner}/{repo}/contents/{path}?ref={branch}`