# Acme API (fixture)

A tiny orders API used as the "real repository" for the Veto grill's
repo-task stage. Plain JavaScript, no build step, no dependencies.

## Endpoints

- `GET /orders?page=N` — paged order list (10 per page).
- `GET /orders/:id` — single-order lookup.

## Seed data

The API ships with 25 seeded orders in `src/db/memory.js`, enough to exercise
all endpoints across multiple pages.

## Structure

- `src/server.js` — minimal `node:http` server with Express-style routing.
- `src/routes/orders.js` — the order endpoints.
- `src/db/memory.js` — in-memory order store (`findAll`, `findById`).
- `tests/smoke.test.js` — smoke tests for the store (`node --test`).

## Run it

```sh
node src/server.js   # listens on :3000 (PORT to change)
```

## Test it

```sh
npm test              # node --test tests/smoke.test.js
```
