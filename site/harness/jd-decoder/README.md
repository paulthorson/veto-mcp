# jd-decoder parity harness

Byte-identical fidelity checks between the Python engine
(`jd_decoder.py` at the repo root) and the TypeScript port
(`site/src/lib/jdDecoder.ts`, used by the live decoder at `#/decoder/try`).

## Sample harness

Runs the fixed corpus in `samples/` through both engines and compares
canonicalized JSON byte-for-byte:

    bash site/harness/jd-decoder/run.sh

`gen_expected.py` regenerates `expected/` from the Python engine;
`run.mjs` runs the compiled TS port and diffs. Any mismatch fails loudly.

## Fuzz parity

`fuzz.py` regenerates a 400-case unicode fuzz corpus with a seeded RNG
(same seed always yields the same corpus), runs BOTH engines over every
case, and asserts zero mismatches. Exits non-zero on any mismatch:

    python3 site/harness/jd-decoder/fuzz.py

Optional flags: `--cases N` (default 400), `--seed S` (default 20260912).

The fuzz alphabet deliberately excludes 9,661 code points where the two
engines' `\w` classifications inherently disagree: Python's `re` uses
unicodedata 15.0 while the TS port's `[\p{L}\p{N}_]` uses the host ICU
(Unicode 16.0/17.0 assignments). See the `fuzz.py` docstring for the
derivation. Neither engine's matching behavior is changed to
accommodate this; the exclusion is documented in the script.
