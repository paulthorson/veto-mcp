#!/usr/bin/env python3
"""Deterministic unicode fuzz parity: Python jd_decoder vs the TS port.

Regenerates a 400-case fuzz corpus with a seeded RNG (same seed always
yields the same corpus), runs BOTH engines over every case, and asserts
zero mismatches. Exits non-zero on any mismatch.

Run (from the repo root):

    python3 site/harness/jd-decoder/fuzz.py

Optional flags: --cases N (default 400), --seed S (default 20260912).

How it works:
  1. Build the corpus deterministically with random.Random(SEED).
  2. Compute jd_verdict() for each case with the real Python engine.
  3. Compile site/src/lib/jdDecoder.ts with tsc (same flags as run.sh)
     into a temp dir and run every case through the TS jdVerdict() via
     the sibling fuzz_runner.mjs.
  4. fuzz_runner.mjs canonicalizes both results (object keys sorted
     recursively, arrays in order; same canon as run.mjs) and compares
     them byte-for-byte. Any mismatch fails loudly.

Known limitation (not a bug in either engine, and not something either
side can fix without changing matching behavior):
  Python's `re` classifies word characters with unicodedata 15.0 (this
  repo's Python 3.12), while the TS port's \\w equivalent ([\\p{L}\\p{N}_])
  uses the host ICU (Node 24 ships ICU 78, roughly Unicode 17). 9,661
  code points assigned in Unicode 16.0/17.0 are word characters to ICU
  but unknown (hence non-word) to Python's unicodedata 15.0, so the two
  engines disagree on \\b boundaries adjacent to those characters. The
  fuzz alphabet excludes exactly those code points (SKEW_RANGES below),
  which were found by an exhaustive sweep: every code point 0..0x10FFFF
  (minus surrogates) was tested against Python's re \\w and Node's
  /[\\p{L}\\p{N}_]/u; all 9,661 disagreements were one-directional (ICU
  says word, Python says not) and all sit in recently-assigned blocks.
  To regenerate for a newer Python/ICU pair, re-run that sweep and
  replace SKEW_RANGES. Texts using such brand-new characters are
  vanishingly rare in real job descriptions.
"""

import argparse
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # repo root: site/harness/jd-decoder -> parents[2]
sys.path.insert(0, str(ROOT))

from jd_decoder import jd_verdict  # noqa: E402

DEFAULT_SEED = 20260912
DEFAULT_CASES = 400

# Code points where the engines' \w classifications inherently disagree:
# ICU (Node/Chrome) says word, Python's unicodedata 15.0 says non-word.
# Derived by exhaustive sweep; see the module docstring. (start, end)
# inclusive ranges, 51 ranges / 9,661 code points.
SKEW_RANGES = (
    (0x088F, 0x088F),
    (0x0C5C, 0x0C5C),
    (0x0CDC, 0x0CDC),
    (0x1C89, 0x1C8A),
    (0xA7CB, 0xA7CF),
    (0xA7D2, 0xA7D2),
    (0xA7D4, 0xA7D4),
    (0xA7DA, 0xA7DC),
    (0xA7F1, 0xA7F1),
    (0x105C0, 0x105F3),
    (0x10940, 0x10959),
    (0x10D40, 0x10D65),
    (0x10D6F, 0x10D85),
    (0x10EC2, 0x10EC7),
    (0x11380, 0x11389),
    (0x1138B, 0x1138B),
    (0x1138E, 0x1138E),
    (0x11390, 0x113B5),
    (0x113B7, 0x113B7),
    (0x113D1, 0x113D1),
    (0x113D3, 0x113D3),
    (0x116D0, 0x116E3),
    (0x11BC0, 0x11BE0),
    (0x11BF0, 0x11BF9),
    (0x11DB0, 0x11DDB),
    (0x11DE0, 0x11DE9),
    (0x13460, 0x143FA),
    (0x16100, 0x1611D),
    (0x16130, 0x16139),
    (0x16D40, 0x16D6C),
    (0x16D70, 0x16D79),
    (0x16EA0, 0x16EB8),
    (0x16EBB, 0x16ED3),
    (0x16FF2, 0x16FF6),
    (0x187F8, 0x187FF),
    (0x18CFF, 0x18CFF),
    (0x18D09, 0x18D1E),
    (0x18D80, 0x18DF2),
    (0x1CCF0, 0x1CCF9),
    (0x1E5D0, 0x1E5ED),
    (0x1E5F0, 0x1E5FA),
    (0x1E6C0, 0x1E6DE),
    (0x1E6E0, 0x1E6E2),
    (0x1E6E4, 0x1E6E5),
    (0x1E6E7, 0x1E6ED),
    (0x1E6F0, 0x1E6F4),
    (0x1E6FE, 0x1E6FF),
    (0x2B73A, 0x2B73F),
    (0x2CEA2, 0x2CEAD),
    (0x2EBF0, 0x2EE5D),
    (0x323B0, 0x33479),
)
_SKEW = {cp for start, end in SKEW_RANGES for cp in range(start, end + 1)}
assert len(_SKEW) == 9661, "SKEW_RANGES must cover exactly the 9,661 skewed code points"


def _skewed(cp: int) -> bool:
    return cp in _SKEW


# ---------------------------------------------------------------------------
# Corpus alphabet (no skewed code points, no surrogates)
# ---------------------------------------------------------------------------

_BASE = (
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    " .,;:!?()[]{}\"'/\\|@#$%^&*+=<>~`"
)
_WS = list(
    "\t\n\v\f\r \x1c\x1d\x1e\x1f\x85\xa0"
    "\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a"
    "\u2028\u2029\u202f\u205f\u3000"
)
# Punctuation/symbols the decoder's regexes care about. The em dash
# (U+2014) is spelled as an escape so the literal character never
# appears in this file.
_SYM = list("$£€•▪–" + "\u2014" + "…''«»‹›¿¡§¶©®™°±×÷")
_WORD_RANGES = (
    (0x00C0, 0x02FF),   # Latin Extended etc.
    (0x0370, 0x052F),   # Greek, Cyrillic
    (0x0530, 0x058F),   # Armenian
    (0x0590, 0x05FF),   # Hebrew
    (0x0600, 0x06FF),   # Arabic
    (0x0900, 0x097F),   # Devanagari
    (0x3040, 0x30FF),   # Hiragana/Katakana
    (0x4E00, 0x9FFF),   # CJK Unified
    (0xAC00, 0xD7A3),   # Hangul
    (0x1F300, 0x1FAFF), # emoji/symbols
)

for _ch in _BASE + "".join(_WS) + "".join(_SYM):
    assert not _skewed(ord(_ch)), f"pool char U+{ord(_ch):04X} is skewed"

# Feature tokens so the generated texts actually exercise the decoder's
# signals (salary, equity, overwork, buzzwords, bullets, growth, green
# flags, newline variants).
_TOKENS = [
    "$120k-$150k", "USD 100k to 130k", "£60,000–£75,000", "€90K-€110K",
    "$95,000", "competitive salary", "market-rate pay",
    "salary: negotiable", "salary: TBD",
    "stock options", "RSUs", "equity", "ESOP", "vesting over 4 years",
    "annual grant refreshers", "15% bonus",
    "fast-paced", "fast paced", "wear many hats", "always on", "24/7",
    "unlimited PTO", "unlimited vacation", "work hard play hard",
    "do whatever it takes", "nights and weekends", "hustle",
    "synergy", "synergies", "rockstar", "rock star", "ninja", "guru",
    "thought leader", "game changer", "game-changer", "paradigm",
    "- own the roadmap", "• shipped v2", "1. write tests", "> quoted note",
    "▪ draft docs", "3) review PRs",
    "mentorship", "mentoring program", "learning budget",
    "professional development", "career growth", "promotion track",
    "training budget", "conference stipend",
    "remote-first", "work from home", "flexible hours", "must-haves",
    "nice-to-haves", "required qualifications", "bonus points",
    "distributed team",
    "\n", "\r\n", "\r", "\u2028", "\u2029", "\x85",
]
for _tok in _TOKENS:
    for _ch in _tok:
        assert not _skewed(ord(_ch)), f"token char U+{ord(_ch):04X} is skewed"


def _rand_word_char(rng: random.Random) -> str:
    """A random word-ish unicode char, never skewed, never a surrogate."""
    while True:
        lo, hi = _WORD_RANGES[rng.randrange(len(_WORD_RANGES))]
        cp = rng.randrange(lo, hi + 1)
        if not _skewed(cp):
            return chr(cp)


def _gen_case(rng: random.Random) -> str:
    n = rng.randrange(0, 401)
    chars: list[str] = []
    for _ in range(n):
        r = rng.random()
        if r < 0.80:
            chars.append(_BASE[rng.randrange(len(_BASE))])
        elif r < 0.88:
            chars.append(_WS[rng.randrange(len(_WS))])
        elif r < 0.94:
            chars.append(_SYM[rng.randrange(len(_SYM))])
        else:
            chars.append(_rand_word_char(rng))
    text = "".join(chars)
    # Splice in 0-4 feature tokens at random positions.
    for _ in range(rng.randrange(0, 5)):
        tok = _TOKENS[rng.randrange(len(_TOKENS))]
        pos = rng.randrange(0, len(text) + 1)
        text = text[:pos] + tok + text[pos:]
    return text


def gen_corpus(seed: int, n_cases: int) -> list[str]:
    """Deterministic corpus: same seed always yields the same cases."""
    rng = random.Random(seed)
    cases = [
        "",  # empty input exercises the no-signals path
        "   \n\t  ",  # whitespace-only
        "Software Engineer\n$120k-$150k\n- build things\n- ship fast\n",
    ]
    while len(cases) < n_cases:
        cases.append(_gen_case(rng))
    return cases[:n_cases]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Deterministic unicode fuzz parity: Python jd_decoder vs the TS port."
    )
    ap.add_argument("--cases", type=int, default=DEFAULT_CASES)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = ap.parse_args()

    tsc = ROOT / "site" / "node_modules" / ".bin" / "tsc"
    if not tsc.exists():
        print(f"error: tsc not found at {tsc}; run npm install in site/ first",
              file=sys.stderr)
        return 2

    cases = gen_corpus(args.seed, args.cases)
    print(f"generated {len(cases)} cases (seed={args.seed})")

    expected = [jd_verdict(t) for t in cases]
    print(f"python engine: {len(expected)} verdicts computed")

    with tempfile.TemporaryDirectory(prefix="jd-fuzz-") as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "package.json").write_text('{"type":"module"}\n')
        (tmp_path / "cases.json").write_text(
            json.dumps(
                [{"input": t, "expected": e} for t, e in zip(cases, expected)],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print("compiling TS port...")
        cp = subprocess.run(
            [str(tsc), "site/src/lib/jdDecoder.ts",
             "--outDir", tmp, "--module", "es2022", "--target", "es2022",
             "--strict", "--skipLibCheck"],
            cwd=ROOT, capture_output=True, text=True, timeout=300,
        )
        if cp.returncode != 0:
            print("error: tsc failed:\n" + cp.stderr, file=sys.stderr)
            return 2
        print("running TS engine over corpus...")
        cp = subprocess.run(
            ["node", str(HERE / "fuzz_runner.mjs"),
             str(tmp_path / "jdDecoder.js"), str(tmp_path / "cases.json")],
            cwd=ROOT, timeout=600,
        )
        return cp.returncode


if __name__ == "__main__":
    sys.exit(main())
