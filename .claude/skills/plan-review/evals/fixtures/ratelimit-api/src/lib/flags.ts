function current(): Set<string> {
  return new Set((process.env.FEATURE_FLAGS ?? "").split(",").filter(Boolean));
}

export function isEnabled(name: string): boolean {
  return current().has(name);
}
