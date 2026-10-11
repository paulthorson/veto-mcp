/* Feature D: vitest for getRepoTasks() and the acme-api fixture. */
/// <reference types="node" />
import { describe, it, expect } from 'vitest';
import { existsSync, readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { getRepoTasks } from '../repoTasks';
import type { JobContext } from '../chakraTypes';

const testDir = dirname(fileURLToPath(import.meta.url));
const fixtureRoot = join(testDir, '..', '..', '..', 'public', 'fixtures', 'acme-api');

const fixtureFiles = [
  'package.json',
  'README.md',
  'src/server.js',
  'src/routes/orders.js',
  'src/db/memory.js',
  'tests/smoke.test.js',
];

function readFixture(rel: string): string {
  return readFileSync(join(fixtureRoot, rel), 'utf8');
}

const backendJob: JobContext = {
  title: 'Backend Engineer',
  company: 'Example Corp',
  rawText: '8+ years backend, Node.js APIs',
  requirements: ['Node.js APIs'],
  roleKeywords: ['backend', 'node.js', 'api'],
  source: 'paste',
};

const unrelatedJob: JobContext = {
  ...backendJob,
  title: 'Visual Designer',
  roleKeywords: ['figma', 'design-system'],
};

describe('getRepoTasks', () => {
  it('returns exactly 2 tasks', () => {
    expect(getRepoTasks()).toHaveLength(2);
    expect(getRepoTasks(backendJob)).toHaveLength(2);
    expect(getRepoTasks(unrelatedJob)).toHaveLength(2);
  });

  it('every task carries the required fields', () => {
    for (const t of getRepoTasks()) {
      for (const k of ['id', 'title', 'repoPath', 'taskDescription', 'checkDescription'] as const) {
        expect(typeof t[k], k).toBe('string');
        expect(t[k].trim().length, k).toBeGreaterThan(0);
      }
    }
  });

  it('is deterministic', () => {
    expect(JSON.stringify(getRepoTasks(backendJob))).toBe(JSON.stringify(getRepoTasks(backendJob)));
    expect(JSON.stringify(getRepoTasks())).toBe(JSON.stringify(getRepoTasks()));
  });

  it('keeps the acme-api default set for backend and non-backend jobs', () => {
    const ids = (j?: JobContext) => getRepoTasks(j).map((t) => t.id);
    expect(ids(backendJob)).toEqual(['acme-api-pagination-fix', 'acme-api-order-detail']);
    expect(ids(unrelatedJob)).toEqual(ids(backendJob));
    expect(ids()).toEqual(ids(backendJob));
  });

  it('pagination task check is the page-2/page-3 contract', () => {
    const t = getRepoTasks().find((x) => x.id === 'acme-api-pagination-fix');
    expect(t?.checkDescription).toContain('page=2');
    expect(t?.checkDescription).toContain('no duplicates');
  });

  it('order-detail task check is the 200/404 contract', () => {
    const t = getRepoTasks().find((x) => x.id === 'acme-api-order-detail');
    expect(t?.checkDescription).toContain('/orders/3');
    expect(t?.checkDescription).toContain('404');
  });
});

describe('acme-api fixture on disk', () => {
  it('all fixture files exist', () => {
    for (const f of fixtureFiles) {
      expect(existsSync(join(fixtureRoot, f)), f).toBe(true);
    }
  });

  it('README exists and describes the codebase', () => {
    const readme = readFixture('README.md');
    expect(readme).toContain('Acme');
    expect(readme).toContain('src/routes/orders.js');
  });

  it('the pagination off-by-one is actually present in the source', () => {
    const orders = readFixture('src/routes/orders.js');
    // The planted bug: every page after 1 starts one slot early.
    expect(orders).toContain('(page > 1 ? 1 : 0)');
    expect(orders).toContain('const start = (page - 1) * PAGE_SIZE - (page > 1 ? 1 : 0);');
  });

  it('the GET /orders/:id stub is present and unimplemented', () => {
    const orders = readFixture('src/routes/orders.js');
    expect(orders).toContain('getOrder');
    expect(orders).toContain('501');
    expect(orders).toContain('not implemented');
  });

  it('carries no secrets, emails, or PII', () => {
    const leak = /password|secret|api[_-]?key|private[_-]?key|\btoken\b|@gmail\.|@yahoo\.|@hotmail\./i;
    for (const f of fixtureFiles) {
      expect(readFixture(f), f).not.toMatch(leak);
    }
  });
});
