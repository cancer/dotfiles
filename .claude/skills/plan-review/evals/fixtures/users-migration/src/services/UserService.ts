import { query } from "../db/client";

export type User = {
  id: number;
  email: string;
  full_name: string;
};

export class UserService {
  async findById(id: number): Promise<User | null> {
    const rows = await query<User>(
      "SELECT id, email, full_name FROM users WHERE id = $1",
      [id],
    );
    return rows[0] ?? null;
  }

  async search(term: string): Promise<User[]> {
    return query<User>(
      "SELECT id, email, full_name FROM users WHERE full_name ILIKE $1 ORDER BY full_name LIMIT 50",
      [`%${term}%`],
    );
  }

  async rename(id: number, fullName: string): Promise<void> {
    await query("UPDATE users SET full_name = $1, updated_at = now() WHERE id = $2", [
      fullName,
      id,
    ]);
  }

  displayName(user: User): string {
    return user.full_name;
  }
}
