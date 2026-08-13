export type Duration = { ms: number };

const UNITS: Record<string, number> = {
  ms: 1,
  s: 1000,
  m: 60 * 1000,
  h: 60 * 60 * 1000,
  d: 24 * 60 * 60 * 1000,
};

export function parseDuration(input: string): Duration {
  const trimmed = input.trim();
  if (trimmed === "") throw new Error("empty duration");

  const match = /^(-?\d+(?:\.\d+)?)\s*(ms|s|m|h|d)$/.exec(trimmed);
  if (!match) throw new Error("invalid duration: " + input);

  const value = Number(match[1]);
  const unit = UNITS[match[2]];
  if (value < 0) throw new Error("negative duration: " + input);

  return { ms: Math.round(value * unit) };
}
