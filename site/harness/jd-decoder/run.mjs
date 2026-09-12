/* Harness runner: feeds every sample/*.txt through the compiled TS port
 * and compares the result against expected/*.json byte-for-byte after
 * canonicalization (object keys sorted recursively, arrays in order).
 * Usage: node run.mjs <path-to-compiled-jdDecoder.js>
 */
import { readFileSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const libPath = process.argv[2];
if (!libPath) {
  console.error('usage: node run.mjs <compiled-jdDecoder.js>');
  process.exit(2);
}
const { jdVerdict } = await import(pathToFileURL(libPath).href);

function canon(v) {
  if (Array.isArray(v)) return `[${v.map(canon).join(',')}]`;
  if (v !== null && typeof v === 'object') {
    const keys = Object.keys(v).sort();
    return `{${keys.map((k) => JSON.stringify(k) + ':' + canon(v[k])).join(',')}}`;
  }
  return JSON.stringify(v);
}

function stripTrailingNewlines(s) {
  let i = s.length;
  while (i > 0 && s[i - 1] === '\n') i -= 1;
  return s.slice(0, i);
}

const samplesDir = join(here, 'samples');
const expectedDir = join(here, 'expected');
const files = readdirSync(samplesDir).filter((f) => f.endsWith('.txt')).sort();

let mismatches = 0;
for (const f of files) {
  const text = stripTrailingNewlines(readFileSync(join(samplesDir, f), 'utf8'));
  const expectedPath = join(expectedDir, f.replace(/\.txt$/, '.json'));
  const expected = JSON.parse(readFileSync(expectedPath, 'utf8'));
  const actual = jdVerdict(text);
  const e = canon(expected);
  const a = canon(actual);
  if (e === a) {
    console.log(`OK   ${f}`);
  } else {
    mismatches += 1;
    console.log(`FAIL ${f}`);
    for (let i = 0; i < Math.max(e.length, a.length); i++) {
      if (e[i] !== a[i]) {
        console.log(`  expected[${i}]: ...${JSON.stringify(e.slice(Math.max(0, i - 100), i + 160))}`);
        console.log(`  actual[${i}]:   ...${JSON.stringify(a.slice(Math.max(0, i - 100), i + 160))}`);
        break;
      }
    }
  }
}

console.log(`\n${files.length - mismatches}/${files.length} match, ${mismatches} mismatches`);
process.exit(mismatches === 0 ? 0 : 1);
