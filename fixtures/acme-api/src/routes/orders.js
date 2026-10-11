// src/routes/orders.js — order endpoints (Express-style handlers over node:http).
import { findAll } from '../db/memory.js';

const PAGE_SIZE = 10;

function json(res, status, body) {
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(body));
}

/** GET /orders?page=N — paged order list. */
export function listOrders(req, res) {
  const q = new URL(req.url, 'http://localhost').searchParams;
  const page = Math.max(1, Number.parseInt(q.get('page') ?? '1', 10) || 1);
  const all = findAll();
  // paginate the in-memory orders
  const start = (page - 1) * PAGE_SIZE - (page > 1 ? 1 : 0);
  const items = all.slice(start, start + PAGE_SIZE);
  json(res, 200, { page, pageSize: PAGE_SIZE, total: all.length, items });
}

/** GET /orders/:id — single order lookup. */
export function getOrder(_req, res, _id) {
  // TODO: implement — look up the id, 404 when missing.
  json(res, 501, { error: 'not implemented' });
}
