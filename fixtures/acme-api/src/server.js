// src/server.js — minimal HTTP server, Express-style routing, no deps.
import { createServer } from 'node:http';
import { listOrders, getOrder } from './routes/orders.js';

const PORT = Number.parseInt(process.env.PORT ?? '3000', 10);

const server = createServer((req, res) => {
  const parts = new URL(req.url, 'http://localhost').pathname.split('/').filter(Boolean);
  if (req.method === 'GET' && parts[0] === 'orders' && parts.length === 1) {
    return listOrders(req, res);
  }
  if (req.method === 'GET' && parts[0] === 'orders' && parts.length === 2) {
    return getOrder(req, res, parts[1]);
  }
  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'not found' }));
});

server.listen(PORT, () => {
  console.log(`acme-api listening on http://localhost:${PORT}`);
});
