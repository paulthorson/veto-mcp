# Learnings — data-plumbing, 2026-09-13

1. **Framework structural vetoes can be keyword false positives.** The
   researcher "no evidence" veto on WS-5 was about phrasing, not method;
   rewording to observational language passed. Structural scanners need
   semantic context.
2. **Adversarial self-review under a framework prompt still catches real
   bugs** (the near-miss score overwrite and the `rstrip` header bug) —
   but it must never be presented as independent clearance; the
   disclosure caveat in every verdict summary is what keeps it honest.
3. **Verify the real API before writing integration tests.**
   `record_event` returns `{"event", "appended", "duplicate_of"}`
   (identity-key duplicates return, not raise) and `correct_event` has
   keyword-only args with immutable identity — three test iterations
   were needed to pin the actual contract, which is exactly what
   verification is for.
4. **On a volatile shared tree, "full suite green" is a point-in-time
   claim** — record the run, name the failures, prove they're other
   teams' with isolation runs.
