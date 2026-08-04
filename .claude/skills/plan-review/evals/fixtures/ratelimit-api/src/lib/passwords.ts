const store = new Map<string, string>([["user@example.com", "hunter2"]]);

export async function verifyPassword(email: string, password: string): Promise<boolean> {
  return store.get(email) === password;
}
