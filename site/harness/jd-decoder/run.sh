#!/usr/bin/env bash
# Byte-identical fidelity harness: Python jd_decoder vs the TS port.
# 1. Dump jd_verdict() JSON for every sample via the real Python engine.
# 2. Compile the TS port standalone and run the same samples through it.
# 3. Compare canonicalized JSON byte-for-byte. Any mismatch fails loudly.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"
python3 site/harness/jd-decoder/gen_expected.py
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
echo '{"type":"module"}' > "$TMP/package.json"
site/node_modules/.bin/tsc site/src/lib/jdDecoder.ts \
  --outDir "$TMP" --module es2022 --target es2022 --strict --skipLibCheck
node site/harness/jd-decoder/run.mjs "$TMP/jdDecoder.js"
