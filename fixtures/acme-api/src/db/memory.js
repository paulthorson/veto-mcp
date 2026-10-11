// src/db/memory.js — tiny in-memory order store. No build step, no deps.
const orders = Array.from({ length: 25 }, (_, i) => ({
  id: i + 1,
  customer: `Customer ${i + 1}`,
  total: (i + 1) * 12.5,
  status: i % 3 === 0 ? 'shipped' : 'pending',
}));

/** All orders, in id order. */
export function findAll() {
  return orders;
}

/** One order by id (string or number), or null. */
export function findById(id) {
  return orders.find((o) => String(o.id) === String(id)) ?? null;
}
