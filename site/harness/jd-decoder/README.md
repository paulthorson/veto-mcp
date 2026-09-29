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

## Initiative 04 parity status (2026-09-13)

The browser-supported text domain is exactly the `jd_verdict` surface
proven above. Initiative 04's new surfaces are **Python-only in Q1**
and must not be assumed to run in the browser:

| Surface | Browser status |
|---|---|
| `jd_verdict` (JD decode + risk flags) | ✅ byte-identical parity (this harness) |
| `resume_decoder`, `evidence_map`, `fit_explain`, `role_compare`, `career_graph`, `share_card`, `file_ingest` | ❌ no TS port in Q1 (deferred; decision record in `initiatives/i04/integration_notes.md`) |

Limitations of the supported browser domain (unchanged by 04):
* The fuzz corpus excludes 9,661 code points where Python `re` and TS
  `\p{L}\p{N}_` `\w` classifications disagree (unicodedata vs host
  ICU). Inputs outside the ASCII/latin-1 core may classify word
  boundaries differently — both engines agree on the seeded corpus,
  not on arbitrary Unicode.
* Only `jd_verdict` is ported; `fit_explain` and friends are pure
  text-in/JSON-out Python and intentionally not ported until the
  follow-on workstream extends this harness with a seeded
  `fit_explain` corpus.

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
