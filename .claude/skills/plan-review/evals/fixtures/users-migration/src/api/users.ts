import { UserService } from "../services/UserService";

const users = new UserService();

export async function getUser(req: { params: { id: string } }) {
  const user = await users.findById(Number(req.params.id));
  if (!user) return { status: 404, body: { error: "not_found" } };
  return {
    status: 200,
    body: { id: user.id, email: user.email, fullName: user.full_name },
  };
}

export async function searchUsers(req: { query: { q: string } }) {
  const found = await users.search(req.query.q);
  return {
    status: 200,
    body: found.map((u) => ({ id: u.id, fullName: u.full_name })),
  };
}
