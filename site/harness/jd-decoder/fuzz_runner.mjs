/* Fuzz parity runner: feeds fuzz corpus cases through the compiled TS
 * port and compares each result against the Python engine's output.
 *
 * Usage: node fuzz_runner.mjs <compiled-jdDecoder.js> <cases.json>
 *
 * cases.json is [{input, expected}] where `expected` is the Python
 * engine's jd_verdict() output. Each case is compared after
 * canonicalization (object keys sorted recursively, arrays in order;
 * same canon as run.mjs). Exits 0 on zero mismatches, 1 otherwise,
 * printing a diff snippet for every failure.
 */
import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const libPath = process.argv[2];
const casesPath = process.argv[3];
if (!libPath || !casesPath) {
  console.error('usage: node fuzz_runner.mjs <compiled-jdDecoder.js> <cases.json>');
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

const cases = JSON.parse(readFileSync(casesPath, 'utf8'));
let mismatches = 0;
for (let i = 0; i < cases.length; i++) {
  const { input, expected } = cases[i];
  const actual = jdVerdict(input);
  const e = canon(expected);
  const a = canon(actual);
  if (e === a) continue;
  mismatches += 1;
  if (mismatches <= 10) {
    console.log(`FAIL case ${i} (input ${JSON.stringify(input.slice(0, 80))})`);
    for (let j = 0; j < Math.max(e.length, a.length); j++) {
      if (e[j] !== a[j]) {
        console.log(`  expected[${j}]: ...${JSON.stringify(e.slice(Math.max(0, j - 100), j + 160))}`);
        console.log(`  actual[${j}]:   ...${JSON.stringify(a.slice(Math.max(0, j - 100), j + 160))}`);
        break;
      }
    }
  }
}

console.log(`\n${cases.length - mismatches}/${cases.length} match, ${mismatches} mismatches`);
process.exit(mismatches === 0 ? 0 : 1);
