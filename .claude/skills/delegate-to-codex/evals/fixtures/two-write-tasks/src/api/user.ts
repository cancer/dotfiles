import type { Request, Response } from "express";
import { userStore } from "../store.js";

export async function getUser(req: Request, res: Response) {
  const user = await userStore.find(req.params.id);
  res.json(user);
}

export async function createUser(req: Request, res: Response) {
  const created = await userStore.create(req.body);
  res.status(201).json(created);
}
