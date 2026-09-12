# Retro Ledger

Running retrospectives from agentic build efforts on this project, written as
work ships. Intended for the agentic governance team: each entry records what
was built, what went wrong or right, the extracted learning, and what changed
as a result. Newest entries at the bottom.

Entry schema:

- **Date:** YYYY-MM-DD
- **Effort:** what was worked on (commit hash when shipped)
- **Shipped:** the concrete outcome
- **What happened:** the notable events, including defects caught and how
- **Learning:** the transferable lesson
- **What changed:** the process or code default adopted because of it

---

## 2026-09-12 - Enhancement program, WS1: interactive JD decoder (`bd4c3c2`)

- **Shipped:** `#/decoder/try` route on the marketing site. Paste any job
  posting, get the real transparency verdict from a TypeScript port of
  `jd_decoder.py`. Parity harness: 18/18 samples, 16/16 adversarial inputs,
  400/400 unicode fuzz, zero mismatches. Browser smoke at 390x844 and 1440x900.
- **What happened:** Adversarial QA round 1 *rejected* the port. The TS regex
  diverged from Python on non-ASCII input: JS `\s`/`\b`/multiline `^` do not
  mean what Python's do. Fixing it surfaced four more divergences: a broken
  `\p{}` without the `u` flag, UTF-16 vs code-point windows, `trim()` vs
  NEL/FS, and a `\r` bug in the harness itself. Round 2 passed clean.
- **Learning:** "Same regex" is not the same semantics across languages. A
  cross-language port of a deterministic engine needs an adversarial parity
  harness, including unicode fuzz, *before* acceptance. The harness caught
  bugs the author's own tests did not.
- **What changed:** Parity harness is now a required deliverable for any
  engine port. Follow-up parked: persist the fuzz script as a rerunnable
  artifact (`site/harness/jd-decoder/`).

## 2026-09-12 - Enhancement program, WS2: streaks date-bucket bug (`32e51f0`)

- **Shipped:** Fix for two consecutive mornings of red nightly suite
  (`test_log_rep_stores_entry`, `test_cli_register_and_log`,
  `test_register_tools_smoke`, all showing `today_count=0` after `log_rep`).
- **What happened:** Root cause was a partial seam. `_today()` honored the
  injectable `_TODAY_OVERRIDE`, but `log_rep()` stamped reps with real
  wall-clock `time.time()`. Counts and stamps never shared a day bucket. Fix:
  `_default_ts()` returns local noon of `_today()`; explicit `ts` still
  honored. Diagnosis was stash-proven: exactly the 3 known failures reproduce
  with the fix reverted.
- **Learning:** When a function has an injectable seam, *every* code path that
  must agree with it has to go through the seam. A partial seam is worse than
  none: tests exercise the seam while production diverges silently.
  Stash-proving a fix (revert -> exact failures -> reapply -> green) is the
  right verification bar for "root cause found."
- **What changed:** New tests pin counts and stamps to the same bucket.

## 2026-09-12 - Enhancement program, WS3: job providers (`c3046c9`)

- **Shipped:** ZipRecruiter is now a real, policy-hardened provider
  (robots.txt honored pre-request, CAPTCHA trips the circuit breaker with one
  fetch and no retry, 40/day UTC budget, 1h/2h/4h cooldowns capped at 24h,
  ledger entries on allow and block). Glassdoor stays a stub, but an honest
  one: no public API (verified closed ~2021), bot mitigation, and the risk
  policy forbids CAPTCHA bypass. The exact reason is documented in
  `providers/glassdoor.py` and surfaced by `server.py` instead of a bare
  `NotImplementedError`.
- **What happened:** QA verified the policy machinery with live probes, not
  code comments. QA also caught 7 em dashes in new docstrings, which were
  fixed.
- **Learning:** An honest, documented "no" with the reason beats a fake
  implementation or a bare stub. The risk policy is a design input, not an
  obstacle to route around. Style rules (no em dashes) need adversarial or
  automated enforcement; author discipline alone leaks.
- **What changed:** Stub-reasons are now surfaced to callers as documentation,
  not just raised. Follow-up parked: `compliance.record_block_cleared` is
  never called (pre-existing), so sustained 429s escalate toward the 24h cap
  with no decay path.

## 2026-09-12 - Enhancement program, WS4: wizard coverage (`48cb656`)

- **Shipped:** 7 new guided wizards in the terminal dashboard (watch, apply
  guided dry-run, grill, briefs, email, analytics, search; menu keys 20-26,
  new APPLY group) plus a public `grill.get_grill_session()` accessor. Full
  audit table of module coverage; skips justified. Safety contract traced:
  no wizard can send email, submit, or transmit personal data.
- **What happened:** Adversarial QA round 1 *rejected* (vacuous queue test,
  unenforced email kwarg, missing search wizard, partial queue coverage). All
  fixed and re-proven with QA's own mutation flips. Round 2: zero open
  issues.
- **Learning:** The reject-role earns its keep. Two of five workstreams
  shipped real defects that only the adversarial pass caught. Re-proof with
  the reviewer's own mutation flips is stronger than re-running the author's
  tests.
- **What changed:** None to process; confirmed the builders-never-verify
  default from AGENTS.md.

## 2026-09-12 - Enhancement program, WS5: CLI polish (`b160235`)

- **Shipped:** All 44 commands grouped under
  FIND/TAILOR/APPLY/TRAIN/WIN/GOVERN/UTILITIES in `--help` (was one flat
  dump). `-v`/`--verbose` restores log chatter, `--quiet` leaves errors only,
  stderr silent on success. 13 tests + 48 subtests.
- **What happened:** QA verified all 44 commands present exactly once and
  confirmed stderr behavior empirically. Zero open issues, first pass.
- **Learning:** Small, well-scoped workstreams with empirical checks pass QA
  cleanly on round 1. Scope discipline is a QA accelerator.
- **What changed:** None.

## 2026-09-12 - Program-level retro: the five-workstream program

- **Shipped:** All five workstreams built, adversarially QA'd, independently
  verified, pushed to `main`. Final suite: 900 passed, 0 failures.
- **What happened:** One coordinator fanned out to 18 workers across five
  workstreams. JD decoder was ordered first (highest viral leverage); the
  streaks fix ran in parallel as the independent quick win. Two workstreams
  were rejected by QA on round 1 and fixed before shipping. Per-tier
  reporting kept the human informed without gating.
- **Learning:** Parallel workstreams with a shared adversarial-QA bar compose
  well. Ordering by user value (decoder first) while running the independent
  fix in parallel beat strict sequencing. "Report per tier, never gate on
  review" held up at this scale.
- **What changed:** This ledger. Every future program writes retros here as
  work ships.

## 2026-09-12 - Follow-up pass: JD fuzz parity, circuit-breaker recovery, /api/tools catalog, \w skew docs

- **Shipped:** Four follow-ups, each adversarially QA'd then independently
  verified before committing separately: (1) seeded 400-case JD-decoder
  fuzz parity harness (`site/harness/jd-decoder/fuzz.py`,
  `fuzz_runner.mjs`, `README.md`) - 400/400 match; (2) circuit-breaker
  recovery in `compliance.py` (`RECOVERY_SUCCESS_WINDOW=3`,
  `record_search_success`) wired into `providers/ziprecruiter.py` genuine
  fetches, server-side counting removed after a QA rejection (blocked/
  CAPTCHA'd fetches must never count), 11 tests in `test_block_recovery.py`;
  (3) four new `/api/tools` entries (watch, grill, briefs, email_sync) in
  `webui.py`, 16 tests in `test_webui_catalog.py`; (4) Python-vs-ICU
  `\w` skew documented as comment + specs copy, no behavior change.
- **What happened:** Independent verifier ran the full checklist from
  scratch: tree matched expected files exactly, full suite 927 passed +
  4 skipped (green), fuzz 400/400 exit 0, `npm run build` succeeded,
  `npm run lint` 0 errors (2 pre-existing warnings in untouched App.tsx),
  Item 2 fix re-verified via its 11 tests plus a grep confirming
  `record_search_success` is absent from `server.py`, diff review showed
  no `.github/workflows` touches, no secrets, and the only new U+2014
  occurrences are an escaped `\\u2014` in fuzz test data and an
  `assertNotIn("\\u2014")` test - both intentional. Committed as four
  separate commits and pushed; tree clean.
- **Learning:** The QA rejection on server-side recovery counting was the
  value event of this pass - independent verification caught it again
  only as a grep; a verifier can confirm the fix but only the adversarial
  QA reviewer catches it first. Also: a concurrent process pushed my
  commits between my `git commit` and `git push` (push reported
  "Everything up-to-date"), so verifying remote state via
  `git branch -r --contains` after push matters more than the push output.
- **What changed:** Retro-ledger convention itself landed in AGENTS.md
  mid-pass; this entry honors it.
