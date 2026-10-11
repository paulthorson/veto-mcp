// tests/smoke.test.js
// Dual runner: the fixture's own `npm test` runs this under `node --test`;
// the site's vitest suite also collects this file (VITEST is set), in which
// case the same assertions register with vitest instead of node:test.
import assert from 'node:assert/strict';
import { findAll, findById } from '../src/db/memory.js';

const runner = process.env.VITEST ? await import('vitest') : await import('node:test');
const { describe, it } = runner;

describe('acme-api smoke', () => {
  it('seeds 25 orders in id order', () => {
    const all = findAll();
    assert.equal(all.length, 25);
    assert.equal(all[0].id, 1);
    assert.equal(all[24].id, 25);
  });

  it('finds an order by id', () => {
    assert.equal(findById(3)?.id, 3);
  });

  it('returns null for unknown ids', () => {
    assert.equal(findById(999), null);
  });
});
