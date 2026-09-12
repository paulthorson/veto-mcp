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

## 2026-09-12 - Follow-up: persist JD-decoder fuzz parity script (`0ef1403`)

- **Effort:** commit `0ef1403829f061e3c5e2775a3c1aff862d5d90eb`
- **Shipped:** `site/harness/jd-decoder/fuzz.py` (+ `fuzz_runner.mjs`,
  `README.md`). Deterministic seeded 400-case corpus, dual-engine parity
  assertion, non-zero exit on mismatch, ~3s runtime, documented command.
- **What happened:** closed the gap the enhancement program left (400/400
  claim, no rerunnable artifact). Independent verifier ran the script from
  repo root: 400/400 match, exit 0. The corpus embeds the skew exclusion
  (`SKEW_RANGES`) so the two engines are never asked to agree on code
  points where Python's unicodedata and browser ICU inherently disagree.
- **Learning:** a parity claim without a rerunnable artifact is a claim,
  not evidence. Persist the harness alongside the port.
- **What changed:** `fuzz.py` is now the runnable parity proof for the TS
  decoder port.

## 2026-09-12 - Follow-up: circuit-breaker recovery path (`d8c9bd9`)

- **Effort:** commit `d8c9bd95113fa1e500fced08b00daf4f87162281`
- **Shipped:** `compliance.RECOVERY_SUCCESS_WINDOW = 3` with
  `record_search_success`; 3 consecutive genuine successes clear a block
  via `record_block_cleared` and reset the cooldown. Escalation (1h base,
  doubling, 24h cap) unchanged. Genuine-fetch call sites in
  `providers/ziprecruiter.py` (search + details). `docs/compliance.md`
  updated. 11 tests in `tests/test_block_recovery.py`.
- **What happened:** adversarial QA rejected the first version -
  `server.py` counted blocked/CAPTCHA'd fetches toward recovery because
  the ZipRecruiter provider swallows pushback and returns `[]`. Fix:
  providers record successes themselves after block/CAPTCHA checks; the
  server-side counting call was removed, with a comment at the call site
  explaining why. Two regression tests pin the corrected contract.
  Verifier re-ran the 11 tests (all pass) and confirmed via grep that
  `record_search_success` no longer appears in `server.py`.
- **Learning:** "returned without raising" is not "succeeded." Success
  signals must be recorded at the point where success is actually known,
  never inferred from a non-raising return.
- **What changed:** sporadic 429s no longer ratchet irreversibly toward
  the 24h cap; the missing decay path exists.

## 2026-09-12 - Follow-up: `/api/tools` catalog covers new dashboard modules (`0024815`)

- **Effort:** commit `00248158a51052ace658f0c2fbb137a57bbf44a3`
- **Shipped:** 4 new tools in the `webui.TOOLS` catalog (watch, grill,
  briefs, email_sync) with handlers (`_h_watch_*`, `_h_grill_*`,
  `_h_briefs_*`, `_h_email_*`), plus one softened help-text string.
  16 tests in `tests/test_webui_catalog.py`.
- **What happened:** the catalog predated the wizard work, so 4 real
  dashboard modules had no entry. Verifier ran the catalog tests (16/16
  pass) and reviewed the full handler diff: `email_sync.scan` is
  hardwired to `apply_updates=False` (proposals only), `draft_followup`
  never sends mail, grill validates its `job` param shape, and watch
  check persists baselines.
- **Learning:** a tool catalog is a contract surface. Verify it against
  reality programmatically (tests against the catalog object), not by
  eyeballing.
- **What changed:** the catalog is now a tested, truthful surface for the
  dashboard's tool layer.

## 2026-09-12 - Follow-up: document inherent Python-vs-ICU `\w` skew (`a034770`)

- **Effort:** commit `a034770536ea050929552c0452a82975e692138d`
- **Shipped:** code comment at `PY_WORD` in `site/src/lib/jdDecoder.ts`
  + 3-sentence caveat in the decoder specs "Honesty gates" block
  (`site/src/pages/specs/jd-decoder.ts`). Zero behavior change.
- **What happened:** documented the inherent ~9.6k newest-code-point
  skew between Python's `unicodedata` and browser ICU for `\w`.
  Fixing it would mean shipping a Unicode table to the browser - not
  worth it. Verifier confirmed the diff was comment/copy only (6+/1+1
  lines) and that `npm run build` in `site/` still succeeds with the
  copy addition in place.
- **Learning:** some limitations are inherent. State them plainly in the
  user's language instead of silently accepting the skew or
  over-engineering a fix.
- **What changed:** the methodology page now discloses the limitation
  honestly.

## 2026-09-12 - Follow-up: status_summary recovery observability

- **Shipped:** `compliance.status_summary()` now surfaces `recovery_successes`
  and `recovery_window` per board, closing the observability gap left by the
  circuit-breaker recovery work.
- **What happened:** Small, direct change plus one regression test pinning the
  streak through block, partial recovery, and full recovery. 12/12 recovery
  tests pass.
- **Learning:** A new state machine field that no status surface shows is a
  field nobody can debug. Ship the observability with the mechanism, not
  after.
- **What changed:** None to process; applied the lesson the same turn.
