# ATS connectors decisions (Initiative 09, 2026-09-13)

Constitutional format: genuine options (Rule 2, each phrased "trades X
for Y"), a `schedule_driven` flag (Rule 3), and an `ops_goal` naming a
metric and direction (Rule 4).

Honest framing: this is a local pre-launch library. Veto has no public
users yet, no production traffic, and no measured operational statistics
— every "metric" below is a test-enforced target, not an observed
number. Nothing here invents users, incidents, partner agreements, or
launch dates.

## D1: enrichment posture for the ATS connectors (Greenhouse/Lever/Ashby)

- **Chosen: read-only enrichment + honest capability declaration +
  browser-assisted fill-only flow.**
  - `get_details` on each board pulls only the vendor's official public
    API (no auth, no scraping of gated surfaces) and surfaces the
    application surface it can actually see: question counts where the
    API answers `?questions=true` (Greenhouse), 0 with an explicit
    "does not expose" note where it does not (Lever, Ashby). Every
    connector's `readiness_note` states plainly that direct API
    submission is not permitted to job seekers, and
    `ats_apply.describe_apply_path` names the browser flow as the
    recommended path, with the human performing the actual submit.
  - Trades away one-click auto-apply convenience (the user must still
    complete and submit applications in the browser) to get ToS-safe
    read-only enrichment, an honestly-declared capability surface, and
    zero fabricated fields — when a vendor omits a value, the field is
    `""`, never invented.
- **Surviving option B: direct API submission where the board's terms
  permit it.**
  - Trades away the uniform fill-only architecture (per-board submit
    paths, per-board key handling, and a permanently larger ToS-review
    burden — plus employer-issued API keys where the platform restricts
    POST to employers, e.g. Greenhouse's Job Board API key and Lever's
    API-key POST) to get true one-click submission on any board that
    opens a job-seeker submission path. Survives as the direction to take
    if a vendor publishes a job-seeker-facing submission API — today none
    of the three does, so `can_apply_direct` returns False for all of
    them and the option stays dormant rather than being implemented on
    hope.
- **Surviving option C: deeper HTML scraping of the hosted job pages
  (jobs.lever.co, boards.greenhouse.io) to extract application question
  lists the public APIs withhold.**
  - Trades away contract stability and honesty (scrapers break on
    markup changes, hosted pages can serve different content to bots
    than to humans, and the line between "public page" and gated
    application surface is thinner than an API contract) to get fuller
    question extraction for Lever and Ashby without waiting on vendor
    API changes. Survives only as a fallback if a vendor's API stops
    answering a field the enrichment genuinely needs — and even then it
    would ship with a stated fragility caveat, not as a quiet upgrade.

- `schedule_driven`: false — this work was correctness-driven (a blind
  review KICK_BACK rework), not calendar-driven; no launch date was
  traded.
- `ops_goal`: "share of get_details calls that raise instead of
  returning the declared error/empty-field shapes — keep at/near zero
  (test-pinned: malformed payloads, missing postings, and hostile
  vendor timestamps all return shapes, never raise)."

## D2: hostile vendor timestamp handling (Lever createdAt)

`datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc)` on a hostile
`createdAt` (e.g. `10**22`) raises `OverflowError: timestamp out of
range for platform time_t`, which the original `(TypeError, ValueError,
OSError)` guard did not catch — the exception escaped `get_details`
uncaptured, breaking the never-raise contract from D1.

- **Chosen: widen the guard to
  `(TypeError, ValueError, OSError, OverflowError)` and fall back to
  `posted_date = ""`.**
  - Trades away a more "informative" failure (letting the traceback
    surface to the caller) to get the invariant D1 promises: no vendor
    payload can crash detail retrieval. The OverflowError case is pinned
    in `tests/test_ats_deepening.py` (`test_bad_created_at_falls_back_to
    _empty_posted_date`).
- `schedule_driven`: false. `ops_goal`: same as D1 — vendor-shaped
  hostile inputs never raise.

## D3: Greenhouse employment_type wiring

`get_details` hardcoded `"employment_type": ""` while `custom_fields`
already extracted the `"Employment Type"` metadata name — the value
(`"Full-time"` in the fixture) was dropped on the floor.

- **Chosen: read the value from the first metadata entry whose name
  matches "employment type" case-insensitively, first hit wins; `""`
  when absent.**
  - Trades away a few lines of extraction logic to get no fabricated
    data and no dropped data: the field now reflects what the vendor
    actually said, or stays honestly empty.
- `schedule_driven`: false. `ops_goal`: "employment_type empty on a
  detail response whose metadata names an Employment Type — zero
  (test-pinned)."

## Standing constraints (non-negotiable, all three boards)

- **No invented data.** A field the vendor does not supply is `""` (or
  `0`, or `[]`) — posted dates, question counts, and employment types
  are never fabricated, never estimated, never carried over from
  another source. `readiness_note` says what the connector cannot see.
- **Fill-only automation.** Tooling may populate application fields in
  the browser flow; it never invents answers the user did not provide.
- **Human submits.** No write path exists: no POST, no submission, no
  API-key plumbing for apply endpoints. Read-only enrichment stays
  read-only — this record's options (B and C) describe dormant or
  fallback directions, not shipped behavior.
