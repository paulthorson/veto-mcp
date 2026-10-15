# Veto differentiator roadmap — phased build plan

Companion to `positioning-brief.md` and `feature-sets.md`. Feature
codes (A1, B3, …) refer to `feature-sets.md`. Revised 2026-10-15
after PM review (31 changes), CEO stress-test, and eleven blind-review
rounds (the UAT pattern, state model, and metric definitions in
these phases are blind-review-driven); the revision notes are in
the phase text where they bite.

## Standing gates (every initiative, no exceptions)

**Tests green + E2E against real surfaces + blind review ALLOW +
compliance-domain legal review + the project owner's UAT sign-off.**
A legal KICK_BACK blocks ship exactly like any other veto (annual
roadmap legal exposure gate). No phase counts as shipped on unit
tests alone.

**UAT method (all phases):** each phase's UAT is an executable
acceptance run on a disposable stack — seeded fixture profile,
fixture postings, scripted steps — executed *before* the owner's
time is spent, per the annual roadmap's synthetic-participant
methodology. The owner then gives one-line-per-item accept/reject.
Prose "try it and see" outlines are not UAT scripts. Each phase
below names its seeded run and its pass/fail lines.

**One writer per area.** Where initiatives share modules, the phase
text states the serial order instead of implying parallelism that
the file layout does not allow.

## Where this sits against the annual roadmap

Current state (team-progress record, 2026-10-15): complete — 00, 04,
05, 06, 07, 10, 11, 12. Built 100% but ship-blocked: **01** (owner
UAT owed), **02** (owner UAT owed + a fix-first item open on the
model card), **03** (owner UAT owed + a legal RESHAPE to build:
per-event notification choice in the installer wizard, default
off). **08 stays CUT** (Rule 2). **09**: circuit-breaker STRICT
shape locked 2026-09-29; this roadmap produces drafts only for
third parties, everywhere. A ruling on 09's scope for messages to
the user's *own* channels is recorded in feature E1 (consent model
governs; the owner may overturn).

### Slot 0 — owed annual work (scheduled first, named owners)

These run **before** Phase 0's build work, on the current tree —
because 0.2 migrates the profile shape and Phase 2 changes the
scoring path, and running those first would change the data and
behaviour the owed UATs were written against (PM change 1). One
exception, stated plainly: initiative 0.1 (copy-only claims
corrections) may run in parallel with Slot 0 — it touches no code
or data shape the UATs exercise.

| Slot | Work | Owner |
|---|---|---|
| 0-A | Initiative 01 UAT — seeded acceptance run, owner accept/reject | Owner, with team-run script |
| 0-B | Initiative 02 UAT + model-card fix-first item, closed and re-checked | 02 team |
| 0-C | Initiative 03 legal RESHAPE build — per-event notification choice in the installer wizard, default off; blind compliance review. **Scope includes the consent-model reconciliation** specified in feature E1 (the two existing consent systems — grill channel preferences and the notify per-event catalog — merged into the one model, catalog wins), so the model exists before Phase 1 depends on it | 03 team |

0-C landing early is what lets Phase 1 use real channels lawfully
(PM changes 10, 26): the consent model exists before any new send
is built on top of it.

## Standing row X — cross-cutting (every phase, named owner per phase)

Surfaces (CLI/web/dashboard rendering for that phase's features),
user docs and onboarding changes, claims-register upkeep (brief §6
re-checked against the code at phase close; site copy updated in
the same motion), and test-fixture ownership (fixture profiles,
postings, connections export, trend fixtures, the site demo's
browser test path). Full list: `feature-sets.md`, "standing
workstream". Unowned work is how the claims debt happened; this row
is the fix (PM change 31).

## Phase 0 — Truth first (foundations)

**Row X owner this phase: the PM seat** (standing cross-cutting row — surfaces, docs, claims-register upkeep, fixtures).

Goal: public claims match the code, and the ledger exists in core.

| Initiative | Scope | Depends on |
|---|---|---|
| 0.1 Claims-debt sweep | Correct **all thirteen** debt items in brief §6, each with a checklist ID (CD-01…CD-13) mapped to the audit's fourteen claim risks (the mapping is printed in brief §6; item 13 covers risk 1). Copy-only. | Slot 0 not required (see preamble exception) |
| 0.2a Ledger schema + migration | A1 core: schema, store, migration, **schema version field, pre-migration backup, tested restore**. | Slot 0-A/0-B baselines |
| 0.2b Ledger wiring + profile view | Registration in plugin lists; profile view (CLI/web/dashboard) with proven / in review / unverified markers. | 0.2a |
| 0.2c Consumer regression pass | Wizard, tailor, match, resume builder verified against migrated profiles. | 0.2b |

- **E2E — 0.1 (tests truth, not absence; PM change 4):** for each
  CD item, assert the replacement line is *true* against a named
  code fact (function, path, behaviour) from the audit — a page that
  merely stops making the claim does not pass.
- **E2E — 0.2:** migration against fixture profiles (full, empty,
  corrupt) via the real CLI; backup → migrate → restore reproduces
  the original byte-for-byte; `find_for_requirement()` parity core
  vs standalone i05.
- **UAT (seeded run is the gate; lived check follows — the Phase 5
  pattern, applied everywhere):** seeded run items = the 13 CD pages
  checked against fixtures + migration/restore on fixture profiles.
  Only after the seeded run passes: a lived check on the owner's own
  profile (view shows proven / in review / unverified markers; nothing missing or
  reworded) — the owner's real profile is never the migration test
  bed. One line per item.

## Phase 1 — The profile compounds

**Row X owner this phase: the UX seat** (standing cross-cutting row — surfaces, docs, claims-register upkeep, fixtures).

Goal: the ledger deepens through use, with approval at every write,
and claims carry a proof state from intake.

| Initiative | Scope | Depends on |
|---|---|---|
| 1.2a Proposal contract | A3 core: proposal store, proposal log, **30-day expiry** semantics. | 0.2a |
| 1.2b Approval surface | A3 in the action inbox: approve / edit / reject, conflict display, rejection suppression. **New build** — the inbox is read-only today. | 1.2a |
| 1.1 Evidence grill | A2: profile-scoped grill sessions. Launches on the **chat channel**; WhatsApp/Gmail enable only once 0-C's consent model exists and the two consent systems are reconciled (feature E1's one-model rule). | 1.2b (the approval half lands first — PM change 7), 0-C for non-chat channels |
| 1.5 Intake standard | A5: unverified state at entry, proof request at intake, labels on the surfaces that exist in Phase 1 (profile view, provenance). Its classification consequence is asserted in Phase 2 (B2's fixture matrix carries the listed-but-unverified cell) — declared here, not hidden. | 0.2b, 1.2a/1.2b (the proof-attachment path runs through the A3 approval flow) |
| 1.3 Depth meter | A4, formula as specced (feature A4), gains list wired to 1.1. **Pre-work — authorship owned here:** the shared role-family definition (authored once here, implemented by 2.1) that A4's per-family views and B5 both cite. | 0.2a; gains links need 1.1; role-family definition as pre-work |
| 1.4 Requirement extraction | B1, with the frozen expected lists in the fixtures before build starts. | — (parallel) |

- **E2E:** disposable-stack loop — seed profile → evidence grill
  over chat → approve two answers → depth moves by the
  hand-computed amounts → **Gmail reply path exercised** (subject-tag
  parsing against the new profile-scoped session type; if WhatsApp
  cannot be exercised on the stack, it is descoped from the phase's
  launch claim in writing) → **A3 invariant test:** run all
  producers, assert the ledger is unchanged until an approval exists
  → **A5 sweep:** an unverified claim renders labelled on the
  profile view and provenance surfaces (the delta-surface label
  check runs in Phase 2's E2E, where delta surfaces exist).
- **UAT (seeded run is the gate; lived check follows):** seeded run
  on the fixture profile — items: questions target genuinely
  unverified claims; one approval lands in the ledger with its
  source; depth moved by the hand-computed amount; one unverified
  claim shows its label on every surface. Lived check: the same
  grill run once on the owner's own profile as confirmation.
  One line per item.

## Phase 2 — The delta engine

**Row X owner this phase: the Research seat** (standing cross-cutting row — surfaces, docs, claims-register upkeep, fixtures).

Goal: per-job delta, classified and explained, with the veto given a
path. Entry condition: Slot 0-B closed (the scoring path is frozen
until the model-card fix lands — PM change 15).

| Initiative | Scope | Depends on |
|---|---|---|
| 2.1 Classification | B2 into the core scoring path; the **alias table** ships here; the **role-family definition** — authored in 1.3's pre-work — is **implemented** here (feature B2). One owner per act: 1.3 authors, 2.1 implements. | 0.2a, 1.4 |
| 2.2 Delta assembly | B3 engine: report assembly, impact ordering, per-job delta persistence (with ledger version). | 2.1 |
| 2.3 Delta report — CLI | B3 rendering, CLI surface. | 2.2 |
| 2.4 Delta report — web/dashboard + Radar gradient | B3 rendering on web UI + dashboard; **B6 gradient as a story inside this initiative**, same writer, including the site-demo parity change through the site's preview-then-owner-pass process; **plus the demo stories** (brief §4's acquisition channel, specced in feature B6): the site demo gains a read-only delta report view fed by fixture data once 2.2 exists, **and the interactive refusal demo** — a visitor grill flow against a fixture profile, refusal possible, delta report shown; fixture data only, nothing stored; the site surface ships through the preview-then-owner-pass process, never direct to production. | 2.2 |
| 2.5 Veto with a path | B4: three veto classes, change-my-answer conditions, user-visible verdict record (claim 7b). | 2.2 |

- **E2E:** fixture matrix (supported / alias-only / unquantified /
  absent / years-short / listed-but-unverified) through the real CLI
  and web UI with identical classifications; **delta-surface A5
  label check** (an unverified claim renders labelled on the delta
  report — the Phase 1 deferral, closed here); dashboard card
  rendered and checked;
  the three veto classes each produced by their fixture job;
  the insufficient-signal fixture (3+ unknown axes) produces the
  thin-evidence veto marked "insufficient signal" (B4);
  gradient colours asserted in rendered SVG **and** in the site demo
  via its browser test path (built under row X if absent);
  **demo flow:** the fixture grill completes in the site demo's
  browser test, the unqualified fixture path renders a refusal,
  the delta view matches the fixture's B3 output, and no visitor
  input is stored (asserted in the same browser test);
  **model-card + calibration suites run unchanged** and a written
  note records what 2.1/2.5 change under a pinned personalised card;
  **framework-absent case:** with the governance root unset, a veto
  is recorded to the local record, labelled as such, and a recording
  failure is surfaced to the user (PM change 17); **verdict record:**
  export produces the complete fixture record, delete removes it,
  and the displayed overturn rate equals the hand-computed rate for
  the seeded vetoes and resolutions (B4 acceptance).
- **UAT (seeded run is the gate; lived check follows — the pattern
  every phase now states in both steps):** seeded run with two
  fixture postings (one the fixture profile is qualified for, one it
  is not). Items: the evidence gaps named are really evidence gaps;
  the skill gaps are really absent; the unqualified posting's veto
  class and path are right; the verdict record shows the fixture
  overturn rate with its count (B4). **Plus the recognition run
  set (brief §8, owned here): five seeded personas each produce a
  first-session summary; pass line — the refusal/split wording is
  present, as a content check on the summary text, in at least 3
  of the 5 summaries.** The split is
  tested in **both** directions before it carries the brand. Lived
  check: the owner pastes two real postings — one they are
  qualified for, one they know they are not — and confirms the same
  items against their own history. One line per item.

## Phase 3 — Tailoring service, completed

**Row X owner this phase: the PM seat** (standing cross-cutting row — surfaces, docs, claims-register upkeep, fixtures).

Goal: every tailored artefact is grill-fed, diff-approved, and
honesty-gated. **Serial order (one writer over `tailor.py` /
`cover_letters.py`): 3.1 → 3.2 → 3.3 → 3.4.** The phase is sized as
serial work; no parallelism is claimed (PM change 21).

| Initiative | Scope | Depends on |
|---|---|---|
| 3.1 Grill-fed tailoring | C1: `get_qa_pairs()` wired in; grill provenance class. | 1.2b |
| 3.2 Honesty scanner | C3 part (i): standalone scanner runnable on any artefact, no framework dependency. | 0.2a |
| 3.3 Approval flow + the block | C2 canonical flow **including C3 part (ii)** — approval-time blocking lives here, where the flow exists (PM change 19); stale-artefact handling; named consumers: packet, apply handoff, export. | 3.1, 3.2 |
| 3.4 Letters from evidence | C4: ledger citations per proof paragraph; proof/intent labelling. | 3.3 |

- **E2E:** grill → tailor → approve on a fixture job, asserting the
  grill-sourced line and its provenance; seeded invented-claim drafts
  (metric / employer / skill) blocked at approval with lines named;
  the same flow with the governance root unset; **stale flow:**
  approve an artefact, write to a ledger entry it cites, assert the
  artefact flips to stale and each named consumer warns (PM change
  20); **letter balance:** zero-proof fixture letter shows 0 proof /
  N intent in its review view.
- **UAT (seeded run is the gate; lived check follows):** seeded run
  tailors the fixture application; items include attempting to
  hand-edit an inflated line past the gate — it must stop the
  approval and offer the three honest exits. Lived check: the same
  flow on one real application of the owner's. One line per item.

## Phase 4 — Prep closes the loop

**Row X owner this phase: the UX seat** (standing cross-cutting row — surfaces, docs, claims-register upkeep, fixtures).

Goal: mocks built from the delta, graded against the ledger,
debriefs that deepen the profile.

| Initiative | Scope | Depends on |
|---|---|---|
| 4.1 Delta-driven mocks | D1: question plans from 2.1 classifications, reason tags. | 2.1 |
| 4.2 Evidence grading | D2: second rubric axis (proof used / missed / overclaimed). | 4.1, **3.2** (traceability logic — PM change 22) |
| 4.3 Debrief write-back | D3: proposals into the 1.2 queue (expiry per A3). | 4.2, 1.2b |
| 4.4 Prep brief 2.0 | D4: delta-first brief. **Sequenced after 4.1 under the same `briefs.py` writer** (PM change 22); ordering must match the B3 report's. | 4.1, **2.2** (PM change 23) |

- **E2E:** scripted mock (deterministic answers) for a fixture job —
  question reason tags match the delta; paired answers (uses proof /
  ignores proof) score apart on the evidence axis only, craft within
  the ±5 band; debrief produces exactly the expected proposals;
  approving one reclassifies (B2) and leaves depth unchanged;
  attaching proof and approving the proof then moves depth (A4);
  **brief check:** every STAR story in the fixture brief cites an
  approved ledger entry and its top-3 probed gaps match the delta report's
  ordering (PM change 25).
- **UAT (seeded run is the gate; lived check follows):** seeded run
  executes the scripted fixture mock and brief; items: reason tags
  correct; brief's top-3 gaps match the delta report. Lived check:
  one mock for a real target role in hiring-manager mode **plus
  reading the prep brief**; item: the "stronger proof you missed"
  callouts are right about the owner's own history. One line per
  item.

## Phase 5 — Companion loop + trending

**Row X owner this phase: the PM seat** (standing cross-cutting row — surfaces, docs, claims-register upkeep, fixtures).

Goal: the daily habit and the long view. The legal piece (0-C) is
already landed in Slot 0 — it is not buried in this phase (PM
change 26).

| Initiative | Scope | Depends on |
|---|---|---|
| 5.1 Check-in assembly | E1 part 1: assembly of the shipped pieces + the first-class `check-in` command + **session typing in the streak machinery and the weekly-recap no-application count (E1; brief §8's return measure is built here)**. | 1.2b, 2.2 |
| 5.2 Scheduler + reply routing | E1 part 2: scheduler hookup (external scheduler supported and documented), cadence step-down, reply routing. The posting-in-reply flow depends on 5.3. | 5.1; 5.3 for the posting flow |
| 5.3 Feed-me intake | E2: paste-a-posting → decode → delta → grill queue. | 2.2 |
| 5.4 Network delta | E3, **wired machinery only** (`referrals.py`, `network_crm.py`, `mentors.py` — including E3's mentor surface and its consent gates); i07 promotion is out of scope (PAUSE list). | 2.2 |
| 5.5 Follow-through | E4: autopsy → delta explanations; calibration evidence feed (rules unchanged). | 2.2 |
| 5.6 Delta trending | B5: per-family trends, recurring-gap ranking; owns the per-user interviews-per-application figure (brief §8). Reads persisted deltas + the outcome store directly; **does not depend on 5.5** (PM change 27). | 2.2; 5.1 for the check-in trend line (the trend view itself needs only 2.2) |

Note on 01: 5.5/5.6 can be *built* before Slot 0-A closes, but
cannot be announced or counted shipped until it does — outcome data
is 01's surface, and the brief's claims wait for the owner's accept.

- **E2E:** fixture day — seeded jobs/inbox/outcomes produce the
  exact check-in; all-opt-ins-off run performs **zero remote sends**
  (asserted from logs); a posting pasted in reply yields decode +
  delta + queued grill in-session; **network delta under
  outbound-call mocks records zero sends** while producing the
  documented warm paths from the fixture connections export (PM
  change 29); **follow-through fixture** produces the autopsy →
  delta explanation with its sample size printed, and the
  calibration gate test passes (no weight change without evidence
  gate + recorded human approval); trend view reproduces
  hand-computed counts and renders counts-only below 3 deltas;
  **B5's two owned measures:** the proof-closing rate on the
  fixture window equals the hand-computed rate from the fixture
  delta store + A3's proposal log, and the
  interviews-per-application figure equals its hand-computed
  value with its sample size shown.
- **UAT (seeded run first, then a lived check with defined lines —
  PM change 30):** Seeded run (the gate): the fixture day —
  check-in assembly, one consented nudge, one silent event, reply
  routing — each accepted/rejected on its own line; plus the
  trending items: the proof-closing rate and the
  interviews-per-application figure for the fixture window match
  their hand-computed values. Lived check: one full week on the
  live profile, the window fixed in advance, pass lines fixed
  before it starts: a check-in never exceeds the item cap
  (5 jobs / 3 decisions / 1 question); a quiet day produces
  exactly the one-line quiet form; **at least one no-application
  session recorded during the week (E1 session typing — brief
  §8's return target, evaluated here)**; the proof-closing rate
  shown for the week matches the owner's own count of gaps
  closed, and the interviews-per-application figure displays
  with its sample size; the send log for the week shows zero
  sends the owner did not initiate. Any line failed = reject.
  One line per item.

## Explicit PAUSE / CUT list

Marked here rather than silently dropped, per the legal program:

- **CUT — pooled/cross-user intelligence** (the old Initiative 08 in
  any new clothes): no user data flows to author infrastructure (Rule 2) and the ledger is never pooled;
  "users like you" features are out.
- **CUT — live-interview assistance** (copilot-style answers during a
  real interview): the exact opposite of the honesty brand.
- **CUT — any auto-submit, auto-send, or auto-contact feature**, in
  any phase, under any flag: Rule 1. Drafts end at a human hand.
- **PAUSE — fit-weight personalisation expansion:** the model-card
  machinery stays gated and human-approved as shipped; 5.5 feeds its
  evidence count and nothing more until Slot 0-B clears.
- **PAUSE — new board providers / search expansion:** search exists
  and is secondary by strategy; no new provider work is scheduled.
  Revisit only if feed-me intake (5.3) data says users cannot get
  postings in.
- **PAUSE — i07 warm-path promotion:** E3/5.4 uses the wired network
  machinery only. Promoting `initiatives/i07/warm_path.py` is its
  own future initiative, costed with registration, wiring, and
  tests — never smuggled in as a display change.

## Phase summary

| Slot/Phase | Initiatives | One-line outcome |
|---|---|---|
| Slot 0 | 3 (0-A/0-B/0-C) | Owed annual work closed before building on it |
| 0 | 4 (0.1, 0.2a–c) | Claims match code; ledger in core, safely |
| 1 | 6 (1.1, 1.2a–b, 1.3, 1.4, 1.5) | Profile compounds with approval; proof state from intake |
| 2 | 5 (2.1–2.5) | Delta classified, reported, veto has a path |
| 3 | 4 (3.1–3.4) | Tailoring grill-fed and honesty-gated, serially |
| 4 | 4 (4.1–4.4) | Prep from the delta, graded vs evidence |
| 5 | 6 (5.1–5.6) | Daily loop + delta trending |

32 initiatives plus standing row X in every phase. Phases are
dependency-ordered; parallelism is claimed only where the phase text
shows different files and satisfied dependencies.
