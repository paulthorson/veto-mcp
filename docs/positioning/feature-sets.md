# Veto feature sets — the differentiator, specified

Companion to `positioning-brief.md` (§6 claims register) and
`roadmap.md`. Each feature names what exists today (module:function,
from the code audit) and what is new. "Reuses" is a hard constraint:
extend the named code, do not build a parallel version.

Conventions: **user seat** = what the user sees and does, end to end.
Acceptance criteria are testable statements; the roadmap attaches E2E
and UAT scripts to each.

---

## A. Evidence-ledger profile

### A1. Evidence ledger core (promote the built model)

- **What it does.** Promotes the unwired i04/i05 evidence model into
  the core profile. Every claim in the profile (skill, bullet,
  achievement) becomes a ledger entry: the claim text, its proof
  (verbatim story/metric/link), a source, and a **proof state**.
  Tailoring, delta, and prep all read from the ledger, not from flat
  profile fields.
- **The one state set (defined here; every other feature cites it).**
  One vocabulary spans two stores. A claim starts in the **proposal
  queue** as `draft` — written by a producer (grill answers — per-job and profile (A2), C1's tailoring sessions, D3's debriefs, and outcome updates — the producers A3 names; A5 is the exception: intake claims enter the ledger directly as `unverified`, never via the queue); a draft is
  **not** a ledger entry, and the ledger is unchanged until approval.
  On approval (A3) the claim is written to the **ledger** in one of
  two states:
  - `unverified` — on record, no approved proof attached (includes
    every claim at intake, A5, migrated claims with no proof, and
    approved proposals that carried no proof).
  - `approved` — proof attached and approved in the same review.
    "Proven" in user-facing text means exactly this state.
  **Migration rule:** no migrated claim enters as `approved` —
  migration runs no review, so every migrated claim enters
  `unverified`, including claims whose text already contains
  numbers; a quantified claim becomes proven only when its proof
  is attached and approved through A3 (A5's rule).
  There is no other state vocabulary for entries. (B2's
  supported / evidence-gap / skill-gap / contested are *delta
  classifications of requirements*, a different machine that reads
  these states — not entry states.) Entry sources are enumerated
  here too: `wizard`, `manual`, `grill:<job_id>`, `grill:profile`,
  `mock:<session_id>`, `tailor:<job_id>`, `outcome`.
- **User seat.** After migration, the user opens their profile and
  sees claims grouped by role, each marked with its state: *proven*
  (`approved`), *in review* (`draft` — in the proposal queue,
  awaiting their approval; shown alongside the ledger, stored
  separately), or *unverified*. Nothing about their existing
  data changes shape on screen except the proof markers; unverified
  is a normal starting state, not an error.
- **Inputs/outputs.** In: existing `profiles/profile.json`
  (`experience[].bullets`, `achievements[]`, `skills`,
  `skill_years{}` from `wizard.py: blank_profile()`). Out: ledger store
  alongside the profile; a read API the other features consume.
- **Versioning, backup, restore (required, not optional).** The
  ledger/profile carries a schema version field from day one — B3
  persists deltas "with ledger version" and C2 stamps approvals with
  it, so the field is minted here, not invented per phase. Migration
  first writes a pre-migration backup of the user's profile; a tested
  restore path ships with the migration. The user's storage and
  protection story (where the ledger lives, what a backup is, how to
  delete it) is documented as part of this feature — the ledger is the
  most sensitive file the product holds (brief §7, item 1).
- **Profile view.** This feature also owns the first rendering: the
  profile view in CLI/web/dashboard showing proven / in review / unverified markers
  (today no surface renders the evidence model at all — audit §1).
- **Reuses.** `initiatives/i04/evidence_map.py: build_evidence_map()`
  status model (`supported` / `grill_question` / `gap`),
  `initiatives/i05/evidence_library.py: build_from_profile()` /
  `add_item()` / `approve_item()` / `find_for_requirement()` (schema
  and approval state), `profiles.py: load_profile()` / `save_profile()`.
- **Edge cases.** Migration of a profile with zero achievements
  (all claims unverified — depth 0, no crash); duplicate claims across
  roles (one entry, many role links); a claim whose proof the user
  deletes (entry reverts to unverified, dependent tailored variants are
  flagged — marked *stale* in C2's terms ("stale — built from older proof") — never silently kept); corrupt ledger file (fail closed
  with a readable error, profile untouched).
- **Acceptance criteria.**
  - Migrating the seeded test profile produces one ledger entry per
    claim with correct source and state; no claim text is altered.
  - Restoring the pre-migration backup reproduces the pre-migration
    profile byte-for-byte.
  - `find_for_requirement()` returns the same results against the core
    ledger as against the i05 standalone library on the fixture set.
  - Deleting a proof flags every approved tailored variant that cited
    it.
  - The migrated profile carries the schema version field, and the
    existing profile consumers (wizard, tailor, match, resume
    builder) pass their current test suites against a migrated
    profile unchanged.

### A2. Conversational evidence extraction (the standing grill)

- **What it does.** Turns the per-application grill into a standing
  profile practice. A dedicated session type — *evidence grill* — asks
  about unverified claims and thin areas of the ledger (unquantified
  wins first), a few questions at a time, over the user's chosen
  channel. Answers become draft proposals in the queue (A3); the user approves them there.
- **User seat.** The user picks "deepen my profile" (or accepts a
  companion nudge, E1) and gets ~5 short questions: "You list
  'cut deploy time' at Acme — by how much, and how was it measured?"
  They answer in chat/WhatsApp/Gmail as today; a summary shows the new
  draft entries; one approval writes them to the ledger.
- **Inputs/outputs.** In: ledger entries in state `unverified`, plus
  `approved` entries whose proof lacks a number; the user's answers.
  Out: draft proposals for the queue; on approval, ledger entries with source
  `grill:profile`.
- **Reuses.** `grill.py: generate_questions()` quantify logic
  (`_evidence_is_quantified()`), channel machinery (`get_grill_prefs()`,
  `outbound_for_channel()`, `ingest_reply()` / `parse_reply_body()`),
  session store pattern from `grill_sessions.json`. New: a
  profile-scoped session type distinct from per-job sessions, and the
  write-back path that does not exist today (audit claim risk 1).
- **Edge cases.** User answers "I don't remember the number" (entry
  stays unverified; the answer is recorded as asked-and-unknown so it is
  not re-asked for 90 days); user contradicts an existing claim
  (surface the conflict, never overwrite silently); channel `off`
  (feature explains it needs a channel, does not nag); session
  abandoned mid-way (queue drafts persist, resumable — the ledger is untouched).
- **Acceptance criteria.**
  - An evidence grill on the fixture profile asks only about unverified
    or unquantified claims, capped at 5, motivation question absent
    (that kind stays per-job).
  - Approved answers appear in the ledger with source `grill:profile`;
    queue drafts appear nowhere downstream as profile facts — the
    one stated exception is C1's session path; tailoring and delta
    read ledger entries (both `unverified` and `approved`), with
    per-feature restrictions stated where they apply (proof use
    in C4/D4 is approved-only).
  - Re-running the grill does not re-ask a claim answered
    asked-and-unknown within 90 days.

### A3. Write-back from everywhere (profile compounding)

- **What it does.** One write-back contract: any surface that produces
  a user-approved fact about the user — grill answers (per-job and profile, A2), mock
  interview debriefs (D3), tailoring sessions, outcome updates — can
  propose a ledger entry. Proposals queue for approval in one place
  (the action inbox, E1); nothing writes silently.
- **User seat.** A weekly-ish "new evidence to review" item: "From
  your grill for the Staff role at Northwind: 'led migration of 14
  services' — add to ledger?" Approve / edit / reject.
- **Inputs/outputs.** In: proposals with source + payload from producer
  modules. Out: ledger entries written on approval — state
  `unverified`, or `approved` when proof was attached and approved
  in the same review; a proposal log (kept / rejected / expired) for audit.
- **Reuses.** Producer stores that exist today and currently dead-end:
  `grill_sessions.json` (`grill.py: get_qa_pairs()`),
  `initiatives/i06/longitudinal.py`, `outcomes.py: record_event()`.
  Review surface: `action_inbox.py: inbox()` — **read-only today**
  (audit §7: it "applies nothing itself"). The approval behaviour
  (approve / edit / reject, conflict display, rejection suppression),
  the proposal store, and the proposal log are **new build**, costed
  as such in the roadmap (initiatives 1.2a/1.2b); nothing about this
  feature is a small wiring job.
- **Proposal lifetime (defined here; D3 spends it).** Proposals expire
  30 days after creation if unreviewed. Expired proposals leave the
  inbox's active list at expiry and stay visible in the proposal
  log as *expired* until dismissed; they can never be approved
  after expiry — the producer must re-propose from
  fresh source data.
- **Edge cases.** Two producers propose conflicting values for the
  same claim (both shown, user picks; never auto-merge); proposal for
  a claim the user previously rejected (suppressed unless the source
  is new evidence, and labelled as such); bulk import (CSV outcomes)
  generates no proposals (facts about jobs, not the user).
- **Acceptance criteria.**
  - Completing a per-job grill produces exactly one proposal per
    answered question, visible in the action inbox.
  - A rejected proposal never reappears from the same source payload.
  - No code path writes to the ledger without an approval record
    (test: run all producers, assert ledger unchanged until approval).

### A4. Profile depth meter

- **What it does.** A single 0–100 depth score for the ledger, with
  the weighting formula pinned here (not left to the builder):
  **depth = 40 × (proven share of claims matching the user's target
  roles) + 30 × (share of experience roles carrying ≥1 quantified,
  proven win) + 30 × (share of all claims proven)**. A claim counts
  as proven only in state `approved` **with** proof attached —
  unverified intake claims (A5) never count. Plus coverage checks
  (every role has ≥1 quantified win; every target skill has proof or
  an open gap entry). Shown wherever the profile is shown (the
  surfaces are owned by the roadmap's cross-cutting row), with the
  top 3 "cheapest depth gains" (unverified claims one answer away from
  proven), each gain's point value computed by re-running the formula
  with that claim proven.
- **User seat.** "Profile depth 62. Cheapest gains: quantify the
  platform win at Acme (+6), add proof for Kubernetes (+5), one story
  for the 2023 role (+4)." Each gain links into an evidence grill (A2)
  pre-loaded with that claim.
- **Inputs/outputs.** In: ledger + `target_titles` from the profile.
  Out: score, per-area breakdown, ranked gain list.
- **Reuses.** Nothing equivalent exists (audit §1: ABSENT in core);
  nearest neighbour is `linkedin_optimizer.py: audit_profile()`
  sub-score pattern (presentation only). New computation over the A1
  ledger.
- **Edge cases.** Empty ledger (depth 0 with a getting-started path,
  not an error); target titles changed (score recomputed, change
  explained: "depth for data roles 48, for platform roles 62" —
  per-family views use the shared role-family definition
  (authored as Phase 1 pre-work in 1.3, implemented by 2.1 /
  feature B2), never a local variant — the per-family views
  themselves render once 2.1 implements the definition in
  Phase 2; in Phase 1 the meter reports the overall score, and
  the per-family breakdown is specced here, gated in Phase 2);
  a
  claim proven for one role family and irrelevant to another (counts
  only where relevant).
- **Acceptance criteria.**
  - Score is deterministic for a fixed ledger + targets (same input,
    same score, shown in a test).
  - Two fixture ledgers ship in the spec's test pack with
    **hand-computed expected scores** (computed from the formula
    above by the spec author, not by the code under test); the
    implementation must reproduce both exactly.
  - A gain list entry's predicted points equal the formula's output
    with that claim flipped to proven — verified against the
    hand-computed fixture, not against the implementation's own
    prediction.
  - Breakdown sums to the headline score.

### A5. Intake standard (proof at the door)

- **What it does.** Closes the intake hole in the honesty claim
  (brief §3, Pillar 3): today a claim typed into setup is
  indistinguishable from a proven one, and every downstream check
  traces to it. With A5, every claim enters the ledger in state
  **unverified**. At entry (wizard or manual edit), the user is asked
  for the proof (the number, the story, the link) and may defer —
  deferral is allowed, invisibility is not: an unverified claim is
  labelled as such in the profile view, in tailoring provenance, and
  in the delta, where it can classify at best as an *evidence gap*,
  never *supported*. Attaching proof later moves it through the A3
  approval flow like any other proposal.
- **User seat.** Adding a win at setup: "You wrote 'cut deploy time
  40%'. Add the source now (a review, a dashboard, your own note) or
  keep it marked unverified?" Downstream, the user sees the label
  wherever the claim works: "deploy time — unverified (your entry,
  no proof attached yet)."
- **Inputs/outputs.** In: claim entry/edit flows in `wizard.py` and
  the profile editor. Out: ledger entries with proof state from
  creation; a count of unverified claims feeding A4's gains list.
- **Reuses.** `wizard.py: collect_*()` intake points, A1 ledger
  states, A3 approval flow, `tailor_with_provenance()` display.
- **Edge cases.** Bulk import of an existing resume (every imported
  claim enters unverified, with a single review pass offered — never
  silently trusted, never blocked from importing); user insists a
  claim is true but has no attachable proof (stays unverified with
  the user's own note as its source label — the label is the
  honesty, the note is the context); claim edited after proof
  attached (edited text returns to unverified until re-approved).
- **Acceptance criteria.**
  - A claim entered with no proof renders with the unverified label
    in profile view, provenance map, and delta report.
  - An unverified claim is never presented as proven anywhere in
    Phase 1's surfaces. (Its *classification* consequence — B2 must
    return evidence gap, never supported, for an unverified-but-
    listed skill — is asserted by B2's fixture matrix in Phase 2,
    where B2 exists; it is declared here so the dependency is
    explicit, not discovered.)
  - The honesty promise in the brief (§3) is testable against this
    feature: no surface presents an unverified claim without its
    label (checked in the Phase 1 E2E sweep).

---

## B. Delta engine

### B1. Requirement extraction wired to the profile (JD decode, part 2)

- **What it does.** Gives `jd_decoder.py` the second half it lacks
  today: extract the posting's requirement list (skills, years, location and work-authorisation requirements — the location axis's classification input (B6) —,
  seniority signals, responsibilities) in the same shape the evidence
  map consumes, so a posting can be compared against the ledger —
  quote level, not keyword level.
- **User seat.** Pasting a posting shows two panels: what the posting
  *is* (today's decode: transparency, overwork phrases, vagueness —
  unchanged) and what it *asks for* (the requirement list, each item
  quoted from the posting).
- **Inputs/outputs.** In: posting text. Out: requirement list with
  verbatim quotes + the existing decode verdict.
- **Reuses.** `jd_decoder.py: decode_jd()` / `jd_verdict()` (posting
  side), `initiatives/i04/schemas.py` requirement shape,
  `initiatives/i04/file_ingest.py` parsing patterns. Requirement
  extraction must stay deterministic — no model call invents a
  requirement that is not quotable from the posting.
- **Edge cases.** Posting with no explicit requirements section
  (extract from responsibility lines, mark confidence lower, still
  quote-backed); requirements stated as years ("8+ years") map to the
  years check, not a skill; duplicate requirements merged with both
  quotes kept.
- **Acceptance criteria.**
  - Every extracted requirement carries a verbatim quote found in the
    posting text (test asserts quote ∈ posting for the fixture set).
  - For each of the three fixture postings (clean / vague / overwork),
    the **expected requirement list — items plus their quotes — is
    authored by the spec owner and frozen in the fixture files before
    implementation begins**; extraction must reproduce those lists
    exactly. Whoever writes the code does not set the bar they are
    tested against.

### B2. Delta classification (evidence gap vs skill gap)

- **What it does.** For one job: run the requirement list (B1) against
  the ledger (A1) and classify each requirement —
  **supported** (verbatim, quantified proof on record), **evidence gap** (claim on record,
  proof missing, unquantified, alias-only, or not quotable),
  **skill gap** (nothing on record) —
  plus a fourth state, **contested** (record contradicts the
  requirement, e.g. years below a stated minimum), which is the veto
  feeder (B4). This promotes i04's three-way status model into the
  core scoring path and joins it with `match.py` components.
- **User seat.** The delta report (B3) — classification itself is the
  engine, not a screen.
- **Inputs/outputs.** In: requirement list + ledger + profile facts
  (years, authorization, location for the contested checks). Out:
  per-requirement classification with the ledger entry (or absence)
  that decided it.
- **Reuses.** `initiatives/i04/evidence_map.py: build_evidence_map()`
  (classification core), `match.py: score_job()` components (the fit
  axes stay; the delta explains them), `grill.py`'s per-application
  two-way split (quantify/gap) as the behavioural precedent.
- **Two shared definitions, owned here.** (1) The **alias table**
  ("k8s" ↔ "Kubernetes") lives in a versioned data file in the repo;
  entries are added by reviewed change, never by user machines
  silently, and every alias-based match is recorded in the delta as
  alias-based (visible, not hidden). (2) **Role family** — used by
  this feature, A4, and B5 — is defined once: a family is the set of
  postings whose normalised title matches one of the user's
  `target_titles` clusters; the clustering rule ships with this
  feature and the other features cite it, not their own. **Timing:**
  because A4 (Phase 1) shows per-family depth views, the definition
  itself is authored as Phase 1 pre-work (roadmap initiative 1.3
  carries it as a dependency) and implemented here — one definition,
  written once, before either consumer builds on it.
- **Edge cases.** Skill present under an alias ("k8s" vs "Kubernetes")
  — alias table consulted, and an alias-only match is evidence gap,
  not supported (mirrors i04's rule); skill in bullets but not the
  skill list — evidence gap, never silently supported; requirement
  the user meets via a combination of two roles (supported, both
  entries cited).
- **Acceptance criteria.**
  - On the fixture matrix (supported / alias-only / unquantified /
    absent / years-short / **listed-but-unverified** — the A5 case:
    must return evidence gap, never supported), classification
    matches the documented expected state for every cell.
    Expected states for every cell — including unquantified →
    evidence gap — are authored by the spec owner and frozen in
    the fixture files before implementation begins (the B1 rule:
    whoever writes the code does not set the bar they are tested
    against).
  - Every classification names its deciding ledger entry or states
    "no entry" — no unexplained verdicts.

### B3. Delta report (the per-job product surface)

- **What it does.** The screen/report a user reads for one job: fit
  score and Radar (existing), then the delta in plain language —
  proven strengths (with the proof), evidence gaps (with the one
  action that closes each), skill gaps (with what would close them:
  project/course/time, from `skill_gaps.py: gap_plan()`), contested
  items (why a veto is on the table). Ordered by impact on the score.
- **User seat.** "Strong where it counts: distributed systems —
  proven, '14 services' story. Two evidence gaps: Kubernetes (you
  list it, no proof — answer one grill question to close), cost
  optimisation (win exists, no number). One skill gap: Go — not in
  your history; this posting leans on it. Verdict: apply after
  closing the Kubernetes proof, or skip."
- **Inputs/outputs.** In: B2 classification + `score_job()` result.
  Out: rendered report (CLI + web UI + dashboard card), and the
  machine-readable delta stored per job for trending (B5).
- **Reuses.** `radar.py` rendering, `skill_gaps.py: gap_plan()`
  (lesson/project mapping), `near_miss.py` queue for the 50–59 band.
  New: report assembly + delta persistence.
- **Edge cases.** Job with zero extractable requirements (report says
  so and shows decode only — never a fabricated delta); delta where
  everything is supported (report leads with that, suggests prep D1);
  score and delta disagree (high score, one contested hard
  requirement — contested wins the headline).
- **Acceptance criteria.**
  - Report renders for the three fixture jobs in CLI and web UI with
    identical classifications.
  - Every evidence gap in the report carries a concrete closing
    action; every skill gap carries a `gap_plan()` entry or, where
    no plan exists, an explicit "no plan available" plus the
    smallest next step the user can take — a gap never ships as a
    bare refusal.
  - Delta is persisted per job with timestamp and ledger version, so
    B5 can diff it later.

### B4. Veto with a path (do-not-apply, specified)

- **What it does.** Formalizes today's score veto (`score_job()` veto
  < 60, insufficient-signal rule) into the product answer the brief
  promises: when Veto says no, it says which class of no —
  *contested* (a B2 **contested** classification is present: the
  record contradicts a stated requirement — never softened),
  *skill-gap heavy* (delta dominated by skill gaps: "not yet — here
  is what closes it"), *thin evidence* (fit plausible, proof too
  thin to survive a screen: "close these two proofs first") — and
  what would change the answer. **The insufficient-signal veto**
  (3+ axes scored on unknown defaults) is recorded under the
  *thin evidence* class with its cause marked "insufficient
  signal" — missing profile facts, not thin proof — and its
  change-my-answer names the missing facts. **Disambiguation rule:** a hard
  requirement the user simply lacks is a skill gap, not contested —
  contested requires the record to affirmatively contradict the
  requirement (e.g. years on record below a stated minimum,
  authorization on record conflicting with a stated requirement).
  Classes are checked in the order contested → skill-gap heavy →
  thin evidence, and a veto names every class that applies, with
  contested first. The user can always proceed anyway; the veto is
  advice with a record, not a lock (the existing near-miss human
  verdict flow is the precedent).
- **User seat.** A veto banner on the delta report + the verdict
  written to the verdict record with its class and reasons.
- **Inputs/outputs.** In: B2/B3 + score. Out: veto class, reasons,
  change-my-answer conditions; recorded via
  `governance/adapter.py: record_application_verdict()`.
- **User-visible verdict record.** B4 also owns the per-job verdict
  history surface (delta report + a verdict list in CLI/web): the
  unified, inspectable record the brief lists as claim 7b. Where the
  framework checkout is absent, the record is kept locally and
  labelled as the local record, and a recording failure is shown to
  the user — never silent (the Phase 2 gate tests this case).
- **Export, delete, and the record's own description (brief §7,
  item 5 — requirements, not current facts).** The record surface
  ships with: one-action export of the full record (JSON + readable
  text), delete with confirmation (the record is the user's; a
  deleted record is gone, and the deletion itself is noted in the
  local work log, not in the deleted record), and an in-product
  description — what the record holds, where it lives, that it
  is never transmitted to author infrastructure
  (Rule 2), and how to export/delete it — shown where the
  record is first encountered.
- **Overturn rate (brief §8's signature metric).** The record
  computes, from `near_miss.py` resolutions and recorded overrides (each override entry states whether the veto's named change-my-answer condition had been met at override time — the brief §8 kill criterion reads this),
  the share of reviewed vetoes the user overturned, shown on the
  record surface with its sample size ("overturned 2 of 9 reviewed —
  small sample" below 10). No rate is displayed without its count.
- **Reuses.** `match.py` veto + `veto_reason`, `near_miss.py: scan()` /
  `resolve()` (human override with verdict), experiment ledger entry.
- **Edge cases.** User overrides a contested veto (allowed; the
  override and the contested item are both recorded; tailoring still
  cannot invent the missing qualification — C3); veto on a job the
  user fed themselves via BYOL (same treatment — no friendlier math
  for user-fed jobs); insufficient-signal veto (unknown axes) explains
  which missing profile facts caused it and routes to A2.
- **Acceptance criteria.**
  - Each veto class has a fixture job that produces it, with reasons
    matching the classification that fed it; an insufficient-signal
    fixture (3+ unknown axes) produces a thin-evidence veto marked
    "insufficient signal" naming the missing profile facts.
  - Overriding never removes the original veto from the record.
  - "What would change the answer" is present and specific (named
    gaps/proofs) for skill-gap and thin-evidence classes.
  - Export produces the complete record; delete removes it and the
    surface then shows the empty state with the in-product
    description — both exercised in the Phase 2 E2E.
  - The overturn rate on the fixture record (seeded vetoes +
    resolutions) equals the hand-computed rate, count displayed
    alongside; a fixture with 0 reviewed vetoes shows no rate.

### B5. Delta trending (the gap, over time)

- **What it does.** Stores each delta (B3) and rolls them up per role
  family: how the user's evidence-gap count, skill-gap count, and
  average fit for a family move over 30/90 days, and which recurring
  skill gaps appear across postings (joining `skill_gaps.py`
  frequency analysis with outcome data). Surfaced as a simple trend
  view, plus a line in the daily check-in (E1) when a family's trend
  changes materially — E1 owns the check-in surface; this feature
  supplies the line.
- **Proof-closing rate (owned here).** Of the evidence gaps open
  in a role family at a window's start, the share that reach
  `approved` proof by its end — computed from the persisted
  delta store joined to A3's proposal log (a closing counts
  when the approval lands, whether or not a new posting was
  evaluated in that family). The brief §8 kill criterion reads
  this measure.
- **User seat.** "Staff backend roles, 90 days: evidence gaps 9 → 3;
  one skill gap keeps recurring — Go, in 6 of 11 postings. Closing it
  is your highest-value project this quarter."
- **Inputs/outputs.** In: persisted deltas + `outcomes.jsonl` + A3's proposal log (the approval record — the proof-closing rate joins gap identity from the delta store to the closing approval event). Out:
  trend aggregates per role family; recurring-gap ranking; and the
  per-user outcomes figure brief §8 is judged by — interviews per
  application against the user's own recorded baseline, always with
  its sample size (this feature owns that measure).
- **Reuses.** `skill_gaps.py: analyze_gaps()` (frequency × seniority),
  `outcomes.py: timeline()`, `initiatives/i04/career_graph.py`
  (read-model patterns), `initiatives/i06/longitudinal.py`
  (over-time comparison precedent). New: delta store queries + view.
- **Edge cases.** Fewer than 3 deltas in a family (show the count, no
  trend line — never a trend from two points presented as a slope);
  role family redefined by the user (history kept under both labels
  with the change dated); gaps closed by ledger edits vs by new jobs
  (both shown as distinct causes).
- **Acceptance criteria.**
  - Trend for the fixture history reproduces hand-computed counts.
  - A family with 2 deltas renders counts only, no trend claim.
  - Recurring-gap ranking matches `analyze_gaps()` output on the same
    job set (one engine, two views — no divergent math).
  - Proof-closing rate: on the fixture window (gaps open at start,
    closings in the fixture proposal log), the computed rate
    equals the spec owner's hand-computed rate — including a
    closing whose approval landed with no new posting evaluated
    in the family.
  - Interviews-per-application: the fixture outcome set yields the
    hand-computed figure against the fixture baseline, displayed
    with its sample size.

### B6. Radar gradient (finish the directed dataviz)

- **What it does.** Implements the green/amber/red gradient for the
  fit Radar that was directed in 2026-10 (program history, outside
  the exhibits) and never built — the audit records only the
  non-implementation (claim risk 4): per-axis colour from that axis's B2 classifications —
  axis carried by *supported* requirements → green; axis whose gaps
  are *evidence gaps* only → amber; axis with a *skill gap* or a
  *contested* requirement → red — keeping the existing red veto
  treatment for the headline. (No "mixed" state exists in the
  taxonomy; the colour rule uses only the four B2 classes plus
  unknown, below.) **Axis mapping:** the skills, seniority, and
  location axes carry requirement classifications and take the
  colour rule; the **salary and recency axes have no requirement
  classification** (a preference comparison and a posting-age
  fact, not evidence about the user) and always render in the
  unknown treatment — grey, labelled unknown — never borrowing a
  colour they did not earn. **Precedence** on a classified axis
  carrying several classes: contested > skill gap > evidence gap
  > supported; an axis mixing classified and unknown data shows
  its worst classified colour and lists the unknown in its state
  words.
- **Reuses.** `radar.py: normalize_components()` / `radar_svg()`,
  site demo `site/src/demos/radar.tsx` (both updated to one spec).
- **Edge cases.** Axis with unknown data (grey, labelled unknown —
  never green by default); colour-blind safety: colour never carries
  meaning alone — each axis also shows its state word.
- **Acceptance criteria.**
  - Fixture score sets render the documented colour per axis in both
    `radar.py` SVG and the site demo — including the salary and
    recency axes rendering grey/unknown in every fixture.
  - Every axis label includes its state in text.
  - Demo: a scripted visitor run answers the fixture grill,
    receives a refusal on the unqualified fixture path, and sees
    the fixture delta report; no visitor input is persisted
    (asserted in the demo's browser test).
- **Demo surfaces (built inside roadmap 2.4).** The project site's
  interactive demo — the brief §4 acquisition channel: a visitor
  answers a short grill (the four real question kinds only)
  against a fixture profile, can be refused, and sees the fixture
  delta report (B3 rendering). Fixture data only; nothing a
  visitor types is stored; no install, no account.

---

## C. Tailoring service

### C1. Grill-fed tailoring (make the documented claim true)

- **What it does.** Wires `grill.py: get_qa_pairs()` into the
  tailoring path: when a user starts tailoring for a job with a
  completed grill, the answers join the profile facts as tailoring
  inputs — visibly, as their own provenance class (`grill:<job_id>`),
  and proposed to the ledger via A3 at the same time.
  **Session-input distinction:** the per-job answers are session
  inputs to this job's tailoring, consumed in the flow the user
  is sitting in — they are not profile facts, and they enter the
  profile only through A3 approval.
- **User seat.** Tailoring for the job shows a "from your grill
  answers" section listing which answers were used where; an answer
  never silently becomes a permanent profile fact (that is A3's
  approval).
- **Inputs/outputs.** In: completed grill session + profile/ledger.
  Out: tailored resume + cover letter inputs with grill provenance.
- **Reuses.** The unwired precedent `initiatives/i05/packet.py:
  _grill_answers()` (how answers were assembled into a packet),
  `tailor.py: tailor_with_provenance()` statement map (extended with
  the grill source class), `cover_letters.py` proof mapping (the
  motivation answer feeds the letter, as `docs/grill.md` intends).
- **Edge cases.** Grill skipped/off for this job (tailoring proceeds
  profile-only, and says so); grill answer contradicts the profile
  (tailoring uses the profile version, flags the contradiction,
  proposes the grill version via A3 — never merges silently);
  half-answered grill (only answered pairs are used, listed as such).
- **Acceptance criteria.**
  - Fixture job + completed grill: the tailored output contains the
    grill-sourced line with `grill:<job_id>` provenance, and the base
    profile-only run does not.
  - `docs/grill.md`'s claim becomes testable-true: an E2E test runs
    grill → tailor and asserts the answer appears (roadmap gate).

### C2. Diff-approval flow, completed

- **What it does.** Takes the shipped pieces (diff, provenance,
  approved-variant store; fuller review flow in unwired i05) and makes
  one canonical flow for every tailored artefact — resume and cover
  letter: view diff → per-line provenance on hover/tap → approve all
  or per section → approved version is the only version downstream
  steps (packet, apply handoff) can use. Unapproved edits expire with
  the session, never leak into a later job's base.
- **User seat.** One review screen per job; approving is a single
  deliberate act; the approved artefact carries its approval stamp
  (when, which ledger version it was built from).
- **Reuses.** `tailor.py: tailor_with_diff()` / `resume_diff()` /
  `save_approved_variant()`, `cover_letters.py: approve_letter()`,
  `initiatives/i05/diff_explain.py: explain_resume_diff()` /
  `mark_reviewed()`, `initiatives/i05/versions.py: approve_version()` /
  `trace_report()`.
- **Edge cases.** Ledger changes after approval (artefact marked
  *stale — built from older proof*, re-approval offered; downstream
  use warns, does not silently proceed); user edits an approved line
  by hand (edited line loses provenance, triggers C3 scan before it
  can be approved again); two jobs tailored from the same base
  (variants are per-job, no cross-contamination).
- **Acceptance criteria.**
  - No downstream consumer can load an unapproved or stale-without-
    warning variant (tests on each consumer).
  - Approval record includes ledger version; a ledger write to a cited
    entry flips the artefact to stale.

### C3. Honesty gate, extended to all tailored output

- **What it does.** Extends the shipped cover-letter honesty machinery
  to every tailored artefact and makes it unconditional. Two halves,
  sequenced honestly: **(i) the scanner** — the standalone
  `honesty_scan()` extracted to run on any artefact (resume or
  letter), with no governance-framework dependency; this half is
  independent work. **(ii) the block** — approval of an artefact with
  untraceable claims is refused; this half exists only inside the C2
  approval flow and is delivered with it (the roadmap tables it that
  way; C3 alone cannot be "done" with its headline behaviour
  untestable). The scan runs on the full tailored resume + letter at
  approval time (C2), without depending on the governance framework
  checkout being present (today the blocking gate silently disables
  itself when the framework is absent — audit §5). Numbers,
  proper nouns, and skill claims must trace to ledger/profile text or
  to a grill answer (C1); failures block approval with the offending
  lines listed, and hedged phrasing ("eager to develop") stays exempt
  as today.
- **User seat.** Approving a draft with an untraceable claim stops:
  "'40% cost reduction' — no source on record. Add the proof, reword,
  or remove the line." Three exits, all honest.
- **Reuses.** `cover_letters.py: honesty_scan()` (the scanner),
  `governance/adapter.py: check_cover_letter_honesty()` /
  `governance_gate()` (gate semantics + verdict recording),
  `assess_qualification()` thresholds behaviour on the apply path.
- **Edge cases.** Framework checkout absent (gate still runs via the
  standalone scanner; verdict recorded locally, labelled as such);
  user's own hand-edited line (scanned identically — no trusted-user
  bypass); numbers that come from the posting, not the user (always
  flagged — the posting is never a source for the user's claims).
- **Acceptance criteria.**
  - Seeded draft with one invented metric, one invented employer, one
    invented skill: all three flagged, approval blocked, lines named.
  - Same draft with the metric added to the ledger first: passes.
  - Gate runs with `GOVERNANCE_ROOT` unset (test asserts it).

### C4. Cover letters from evidence

- **What it does.** Completes the shipped letter flow: each proof
  paragraph must cite a ledger entry (not just a profile bullet), the
  motivation grill answer is a first-class input (C1), and unevidenced
  requirements are phrased as interest/development — the existing
  honest fallback — now labelled in the review UI so the user sees
  which paragraphs are proof and which are intent.
- **Reuses.** `cover_letters.py: draft_cover_letter()` (`proofs[]`
  mapping), `approve_letter()`, A1 ledger citations, C3 scan.
- **Edge cases.** Job whose requirements have zero ledger proof
  (letter can still be drafted from intent paragraphs + the closest
  transferable proof, with the balance shown honestly — never
  fabricated proof); user has no motivation answer (letter omits the
  paragraph rather than generating generic enthusiasm).
- **Acceptance criteria.**
  - Every proof paragraph in a generated letter resolves to an
    approved ledger entry (state `approved`); unverified and draft
    entries cannot carry a proof paragraph.
  - A letter for the zero-proof fixture contains no proof paragraph
    and its review view shows 0 proof / N intent.

---

## D. Interview prep

### D1. Delta-driven mock interviews

- **What it does.** Adds the missing question source: when a mock is
  started for a job with a delta (B2), questions are generated from
  the delta first — evidence gaps become "prove it" questions ("Tell
  me about your Kubernetes work" for a listed-but-unverified skill),
  supported strengths become depth questions, skill gaps become one
  honest-framing question ("This role uses Go heavily; talk me
  through your closest adjacent experience") — then filled out from
  the existing likely-questions and mode banks to the session length.
- **User seat.** Starting a mock for a job shows why each question is
  there: "Asked because: Kubernetes is an evidence gap on this job's
  delta." The interviewer modes (recruiter / hiring manager / peer /
  executive / adversarial — the i06 mode banks) stay as the tone
  layer over the same question plan.
- **Inputs/outputs.** In: job delta + ledger + mode. Out: a question
  plan with per-question reason tags, then the session as today.
- **Reuses.** `mock_interview.py: start_mock_interview()` session
  machinery + channels, `briefs.py: prep_interview()` likely questions
  (becomes the filler source), `initiatives/i06/modes.py` banks,
  B2 classifications.
- **Edge cases.** No delta for the job (falls back to today's
  behaviour exactly; the UI says questions are posting-based); delta
  exists but all supported (depth questions + one stretch question —
  a mock with nothing to probe is a wasted mock); user asks for a
  generic mock with no job (mode banks, as today).
- **Acceptance criteria.**
  - Fixture job with a known evidence gap produces a session whose
    first questions carry that gap's reason tag.
  - No-delta fixture: the ordered list of question IDs selected
    equals today's selection for the same seed, exactly (UI copy and
    reason-tag text excluded — selection equality, not byte
    equality of rendered output).

### D2. Grading against evidence

- **What it does.** Adds a second grading axis to the shipped rubric:
  alongside today's answer-craft scores (STAR coverage, numbers,
  ownership), each answer is checked against the ledger — did it use
  the proof on record for this requirement? Did it claim anything
  beyond the record (flagged, in the spirit of C3)? Did it miss the
  strongest available proof (the debrief names it: "Your 14-services
  story was the stronger proof here")? The rubric stays published up
  front, as i06 does today.
- **User seat.** Debrief shows two scores per answer — craft and
  evidence — with the specific proof used / missed / overclaimed
  called out per answer.
- **Inputs/outputs.** In: session answers + ledger + job delta. Out:
  per-answer dual scores + evidence notes; session summary as today,
  extended.
- **Reuses.** `initiatives/i06/rubric.py: score_answer()` (axis
  pattern + published weights), `mock_interview.py: _score_feedback()`
  / `_star_coverage()` (craft heuristics stay), C3's traceability
  logic for the overclaim check, A1 ledger lookups
  (`find_for_requirement()`).
- **Edge cases.** Answer uses a true story that is not in the ledger
  (not penalized as overclaim — routed to A3 as a **proposal** with
  source `mock:<session_id>`; it becomes a ledger entry only on the
  user's approval, entering in state `unverified` until its proof is
  checked like any other); answer contradicts
  the ledger (flagged plainly: "That number differs from your record
  — 14 here, 40 in the session"); job has no delta (evidence axis
  grades against the ledger alone).
- **Acceptance criteria.**
  - Fixture answer that ignores the on-record proof scores lower on
    the evidence axis than the paired answer that uses it, while the
    two answers' craft scores land within ±5 points of each other
    (documents the axes are independent, with a testable band).
  - An overclaim fixture is flagged with the untraceable claim named.
  - Rubric display shows both axes and their weights before the
    session starts.

### D3. Debrief → profile (close the loop)

- **What it does.** At session end, the debrief generates A3
  proposals: stories told well become draft evidence entries; gaps
  the session exposed become ledger gap notes linked to the job's
  delta; recurring weak rubric dimensions feed the existing
  observed-gaps drill recommender. Practice history keeps working as
  today — the profile now also gains from it, with approval.
- **Reuses.** `mock_interview.py: mock_summary()` +
  `_record_longitudinal_result()`, `initiatives/i06/longitudinal.py:
  observed_gaps()`, `skill_gaps.py: practice_observed_gaps()` /
  `recommend_next_drill()`, A3 proposal queue.
- **Edge cases.** User aces a mock with stories already in the ledger
  (no duplicate proposals — matched against existing entries);
  terrible session (proposals still generated for anything factual
  the user stated; tone of the debrief stays factual, not punitive);
  user never reviews proposals (after 30 days they leave the
  inbox's active list and stay visible in the proposal log as
  *expired* until dismissed, per A3 — nothing auto-applies).
- **Acceptance criteria.**
  - Completing the fixture mock yields proposals for exactly the new
    facts stated in the scripted answers.
  - Approved proposal appears in the ledger with source
    `mock:<session_id>` in state `unverified` (the D2 path);
    B2 classification picks it up immediately as an on-record
    claim — it can classify as evidence gap, never supported,
    until proof is attached — and it counts in A4 depth only
    after proof is attached and approved through the A3 flow
    (A4 weights `approved` proof only).

### D4. Prep brief 2.0 (delta-first prep doc)

- **What it does.** Rebuilds the prep doc around the delta: likely
  questions stay, but the brief leads with this job's delta — the
  three gaps most likely to be probed, the STAR stories from the
  ledger that answer them (today's `_star_stories()` reads profile
  free text; it now reads approved ledger entries only), and
  honest-framing lines for the skill gaps. Salary talking points stay.
- **Reuses.** `briefs.py: prep_interview()` structure,
  `company_brief()` unverified-field marking (kept — claims discipline
  applies to company facts too), B2/B3.
- **Edge cases.** Empty ledger (brief says prep is limited until
  evidence exists, routes to A2 instead of generating hollow
  stories — today's empty-stories behaviour, made explicit).
- **Acceptance criteria.**
  - Every STAR story in the brief cites an approved ledger entry (state `approved`).
  - Brief for the fixture job names its top-3 probed gaps, matching
    the B3 delta report's ordering.

---

## E. Companion loop

### E1. Daily check-in (assemble the shipped pieces)

- **What it does.** A scheduled daily session that assembles what
  exists into one short conversation: today's top five (fit-ranked,
  with delta one-liners), the action inbox (approvals waiting —
  including A3 evidence proposals and C2 stale artefacts), follow-ups
  due, and one question back to the user ("anything new to feed me —
  a posting, an outcome, a story?"). Delivery and event opt-ins
  follow the per-event, default-off choice model locked for
  Initiative 03's legal RESHAPE — the user picks which events exist;
  nothing is default-on.
- **User seat.** Morning message, one screen: 5 jobs, 3 decisions, 1
  question. Replying to the question with a posting link starts the
  BYOL feed path (E2).
- **Inputs/outputs.** In: saved/watched jobs, inbox state, outcome
  staleness, preferences. Out: the check-in message + recorded replies
  routed to the right module (posting → E2, outcome → `outcomes.py`,
  story → A3 proposal). E1 also adds **session typing** to the
  streak machinery: every session is logged locally by type (delta
  check, proof-closing, prep, application-touching), and the
  weekly recap shows the count of no-application sessions — the
  brief §8 return measure, which E1 owns.
- **Reuses.** `briefs.py: daily_top_five()`, `action_inbox.py:
  inbox()`, `followup.py: followups_with_drafts()`,
  `outcome_nudges.py: pending_prompts()`, `notify.py` (digest cadence,
  quiet hours, per-event opt-in catalog), `streaks.py` (the day's rep
  counts in the footer). New: the scheduler hookup + reply routing.
  External scheduler remains an option, per `notify.py`'s documented
  pattern — the product gains a first-class `check-in` command either
  way.
- **One consent model (specified here, built early).** Two consent
  systems exist today (`grill_channel` in preferences; `notify.py`'s
  per-event catalog). The reconciliation into the single per-event,
  default-off model (the Initiative 03 RESHAPE shape) is specified
  here but **built in roadmap Slot 0-C**, alongside the wizard choice
  build, so it exists before any feature depends on it: channel
  choice says *where*, the per-event catalog says *what may be sent
  at all*, and the catalog wins on conflict. Grill sends (A2) inherit
  the same rule — and on the roadmap's ordering 0-C lands in Slot 0, before A2 builds, so A2 never launches ahead of the consent model (the dependency is stated in initiative 1.1).
  This feature (E1) consumes the model; it does not rebuild it.
- **Circuit-breaker ruling (recorded 2026-10-15, coordinator; the
  project owner may overturn).** Initiative 09's STRICT rule covers
  AI-drafted messages **to third parties**. Messages to the user's own
  chosen channels (grill questions, check-ins) are governed by the
  per-event consent model above, not by per-message tap approval —
  the recipient is the user. Drafts addressed to anyone else never
  send from any surface, as today.
- **Edge cases.** Nothing to report (check-in is one line — "quiet
  day, depth 62, no decisions waiting" — never manufactured urgency);
  user ignores check-ins for a week (cadence steps down to weekly
  digest per preferences, no guilt mechanics); quiet hours (urgent
  bypass stays limited to the existing urgent event class).
- **Acceptance criteria.**
  - Fixture state produces a check-in containing exactly the seeded
    top-5, the 3 seeded decisions, and the feed question.
  - With all event opt-ins off, no remote delivery occurs (local log
    only) — the Initiative 03 legal condition, tested.
  - A posting pasted in reply creates a BYOL entry and a delta within
    the same session flow.

### E2. Feed-me loop (user-fed jobs, first-class)

- **What it does.** Makes feeding a job the primary intake: paste a
  posting or link in chat/dashboard/check-in reply, and Veto decodes
  it (B1), deltas it (B2/B3), and queues the grill — the
  repositioning's "user feeds postings, Veto preps" path gets a named,
  measured flow instead of being a side door. Board search stays, as
  the secondary source it already is.
- **Reuses.** `byol.py` intake, `jd_decoder.py`, B-pipeline,
  `watch.py` for watched companies, `providers/` search (unchanged).
- **Edge cases.** Duplicate posting (matched to the existing job,
  delta refreshed, user told); link that cannot be fetched (ask for
  pasted text, keep the flow alive — never a dead end); posting in a
  non-English language (decode proceeds, delta marked
  lower-confidence, stated plainly).
- **Acceptance criteria.**
  - Pasting the fixture posting end-to-end yields decode + delta +
    grill queue without a board search occurring.
  - Duplicate paste returns the existing job id and a refreshed delta
    timestamp.

### E3. Warm intros as network delta

- **What it does.** Presents the shipped network machinery in delta
  terms: for a target company, the delta report gains a network line
  — "2 paths in: a former teammate now there (1st degree), one 2nd-
  degree path — and a draft for each." Drafts stay drafts; sending is
  the user's act, in the user's own tools, exactly as the current
  code enforces. The mentor surface joins the same view (a mentor
  who has made this transition is a delta-closer, listed as such when
  consent gates allow).
- **Reuses (scoped honestly).** Wired machinery only:
  `referrals.py: find_referrals_data()` / `rank_referrals()` /
  `draft_outreach()`, `network_crm.py: warm_path_to()` /
  `nudge_list()`, `mentors.py: matchmake()` consent gates. The i07
  package's `plan_warm_path()` is **not** wired into any surface
  (audit §8); promoting it is explicitly **out of scope** here — if
  it is ever promoted, that is its own initiative with registration,
  wiring, and tests costed, not a display change.
- **Edge cases.** No connections data imported (network line says so
  and offers the export-import path — never scrapes to fill the gap);
  contact with no recorded relationship evidence (labelled
  `connection`, evidence "same company" only — today's honesty rule
  in `referrals.py`, kept); stale contact (nudge list staleness rules
  apply before a path is suggested).
- **Acceptance criteria.**
  - Fixture connections export yields the documented paths with
    evidence labels. The no-send property is a **runtime** assertion,
    not a code-reading claim: the flow runs in E2E under outbound-call
    mocks and must record zero sends (roadmap Phase 5 gate).
  - Delta report for a company with a warm path shows the network
    line; for one without, shows the import offer, not a blank.

### E4. Follow-through loop (outcomes feed the delta)

- **What it does.** Connects the shipped outcome machinery back into
  the differentiator: rejection autopsies propose delta explanations
  ("3 of 4 losses at screen stage, all with the same evidence gap"),
  and calibration's evidence gate gains the resolved outcomes the
  loop produces — still gated, still human-approved before any weight
  moves (the model-card rules do not change). Trending (B5) reads the
  outcome store itself; E4 does not feed it, so neither blocks the
  other (the roadmap orders them independently).
- **Reuses.** `rejection_autopsy.py: autopsy()` / `diagnose()`,
  `outcomes.py: guided_update()` / `missing_outcome_prompts()`,
  `calibration.py: evidence_gate_status()`, `model_card.py` approval
  flow, B5.
- **Edge cases.** Autopsy pattern based on <5 outcomes (labelled
  anecdote, not pattern — the module's honesty standard, kept);
  outcome recorded for a job with no delta (delta reconstructed from
  the stored posting where possible, else marked unlinked).
- **Acceptance criteria.**
  - Fixture outcome set produces the documented autopsy → delta
    explanation with its sample size printed next to it.
  - No weight change occurs without the evidence gate + recorded
    human approval (existing tests keep passing, unchanged).

---

## Cross-cutting: claims-debt fixes (from brief §6)

Not a feature — a correctness sweep the roadmap schedules first:
correct the copy named in the brief §6 claims-debt list — all
thirteen items, CD-01…CD-13, in `docs/grill.md`, the site specs,
and product copy. Each fix is a
copy change to match the code, verified by the same audit method that
found the debt.

## Cross-cutting: standing workstream (owned in every phase)

Work the features imply and no single feature owns — the roadmap
carries it as a standing row in every phase, with a named owner per
phase (PM change 31):

- **Surfaces.** Ledger, depth meter (A4: "shown wherever the profile
  is shown"), proposals, delta and verdict views rendered in CLI, web
  UI, and dashboard as each phase's features land.
- **Docs and onboarding.** User docs for each new surface, including
  how an open-source user sets up the external scheduler the
  check-in can run under, and the ledger storage/protection story
  (A1).
- **Claims-register upkeep.** At each phase's close, §6 of the brief
  is re-checked against the code and the site copy updated in the
  same motion — Phases 1–5 must not recreate the debt Phase 0 pays
  off.
- **Test fixtures.** Fixture profiles and postings (B1's frozen
  expected lists, A4's hand-computed ledgers), the fixture
  connections export (E3), hand-computed trend fixtures (B5), and
  the site demo's browser test path (used by the Phase 2 gate for
  the Radar gradient story) — built once, owned, versioned.
