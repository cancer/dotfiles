import { readFileSync, writeFileSync } from "node:fs";

type LegacyUser = { id: string; name: string; email: string };
type User = { id: string; givenName: string; familyName: string; email: string };

export function migrate(path: string): void {
  const legacy = JSON.parse(readFileSync(path, "utf8")) as LegacyUser[];
  const migrated: User[] = legacy.map((u) => {
    const [givenName, familyName] = u.name.split(" ");
    return { id: u.id, givenName, familyName, email: u.email };
  });
  writeFileSync(path, JSON.stringify(migrated, null, 2));
}
