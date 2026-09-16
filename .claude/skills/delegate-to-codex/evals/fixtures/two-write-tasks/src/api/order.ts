import type { Request, Response } from "express";
import { orderStore } from "../store.js";

export async function createOrder(req: Request, res: Response) {
  const order = await orderStore.create({
    userId: req.body.userId,
    items: req.body.items,
    total: req.body.total,
  });
  res.status(201).json(order);
}
