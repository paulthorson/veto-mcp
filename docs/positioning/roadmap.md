# Veto differentiator roadmap — phased build plan

Companion to `positioning-brief.md` and `feature-sets.md`. Feature
codes (A1, B3, …) refer to `feature-sets.md`. Revised 2026-10-15
after PM review, CEO stress-test, and eleven blind-review rounds;
reworked the same day against the adversarial audit of the package
(ticket `muse/2026-10-15/veto-differentiator-audit`, verdict
KICK_BACK, 91 standing findings), and reworked a second time
against the fresh blind audit of that rework (round 2: 6 blockers /
26 majors / 23 minors standing after refutation). Round 2 splits
initiative 1.6, adds the retained-surface conformance initiative
0.9, and recounts every planning-unit total with gate load and
Row X load as explicit lines (see Sizing and capacity). This rework splits bundled
initiatives into separately gated pieces, adds the code-repair,
privacy, and validation work the audit found missing, and recounts
every total. Where a fix belongs in the brief or in
`feature-sets.md`, this roadmap declares the dependency and does
not silently rewrite the other document; those items are listed as
cross-document notes in the rework disposition file.

## Standing gates (every initiative, no exceptions)

**Tests green + E2E against real surfaces + blind review ALLOW +
compliance-domain legal review + the project owner's UAT sign-off.**
A legal KICK_BACK blocks ship exactly like any other veto (annual
roadmap legal exposure gate). No phase counts as shipped on unit
tests alone.

**When an initiative counts as done (audit F5-04).** An initiative
is done only when its own acceptance criteria pass its gates.
Where an acceptance assertion is deferred to a later phase (the
spec declares the deferral, e.g. feature A5's classification
consequence asserted by B2's fixture matrix in Phase 2), the
initiative's status until that assertion passes is **built, gate
pending** — not done, not shipped, not counted in any progress
total. The sign-off lands in the later phase, recorded against the
original initiative. Work that is deferred and is itself new build
is a new initiative with its own gates, never a "completion" of
the initiative it was split from. Split initiatives in this
roadmap are scoped to their completable halves: e.g. 3.2 delivers
the scanner and is gated on the scanner's own tests; the approval
block is 3.3's acceptance, not 3.2's.

**Edge cases are gate items.** Where a feature spec lists an edge
case, the phase E2E exercises it or the phase gate records it as
descoped in writing. Edge-case prose that no gate checks is how
the claims debt happened.

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

## Resourcing the gates (audit F5-05)

The gates above are the schedule, so they are costed here.
All figures in this section are **estimates**, stated so a planner
can challenge them, not promises.

**Per-initiative gate cost assumptions:**

| Gate | Who / what executes it | Cost assumption per initiative |
|---|---|---|
| Tests + E2E build and run | Eng seat builds; QA seat (never the builder) verifies against real surfaces | S: half a day of agent-seat time; M: 1 day; L: 2 days; XL: 4 days |
| Blind review | One reviewer seat, work product only, no builder rationale | 1 round assumed; budget held for 2 KICK_BACK rework + re-review loops per initiative |
| Compliance legal review | Compliance reviewer seat, recorded per initiative; reviews are batched into one sitting per phase where initiatives share a surface, but the verdict is recorded per initiative | Half a day per initiative, plus 1 extra round assumed for every third initiative |
| Owner UAT | The project owner, on the phase's seeded run, one line per item | Batched per phase (see table below) — the owner's minutes are the scarcest resource in this plan, so no initiative spends them alone |

**Owner-time estimate per phase (active minutes, estimate):**

| Slot/Phase | Seeded-run review | Lived check | Total (estimate) |
|---|---|---|---|
| Slot 0 | 60 min (three UATs: 0-A, 0-B, 0-D) | — | ~60 min |
| Phase 0 | 30 min | 15 min | ~45 min |
| Phase 1 | 30 min | 15 min | ~45 min |
| Phase 2 | 45 min | 15 min | ~60 min |
| Phase 3 | 30 min | 15 min | ~45 min |
| Phase 4 | 30 min | 15 min | ~45 min |
| Phase 5 | 30 min | 30 min review after the lived week (the week itself is elapsed time, not active owner time) | ~60 min |

Total owner UAT across the programme: **~6 hours of active time
(estimate)**, spread across seven phase sittings.

**Support load — the refusal product's running cost (round 2,
B-13).** The gates above cost the *build*; a refusal product also
generates support that no gate owns, and it is resourced here so
it is not discovered in operation. Load class: **ongoing, growing
with the user count** — planning assumption (estimate): half a
day of agent-seat time per week once the classified veto (2.8)
ships, rising with dispute volume. The load is: disputed
classifications (the B2 dispute paths, handled per item);
alias-table change requests (every shared alias is a reviewed
repo change — review and landing time, not just the dispute
itself); and ledger restore / corruption help for the most
sensitive store the product holds (0.2a builds a tested restore
path; helping a real user through it is support, not build).
**Who absorbs it:** community triage first — maintainer and
agent seats handle per-item disputes, alias reviews, and restore
walk-throughs; the project owner absorbs only escalations that
would change a shared rule (a threshold, the alias table's
policy, a classification rule), because only the owner can change
those. **De-scope interaction:** support is a running cost, not a
gate — it is never de-scoped to protect a build date, and no gate
is thinned to fund it. When support load exceeds the planning
assumption, what gives first is discretionary new build, in the
de-scope order below (5.10 / 5.8, then 5.7, then 4.4); the
programme slips rather than the support queue silently growing.

**If capacity is exceeded, work is de-scoped in this order —
gates are never de-scoped, and slippage is never silent:**

1. 5.10 (interviews-per-application figure) and 5.8
   (recurring-gap ranking) defer to new, separately gated
   initiatives in a later phase.
2. 5.7 (delta trend view) defers the same way.
3. 4.4 (prep brief 2.0) defers; 4.1–4.3 stand alone.
4. 2.5's site-demo parity change defers; the core Radar gradient
   in `radar.py` does not.
5. 5.6 (follow-through) defers; 5.11 (outcome validation) does
   not — validation of the signature judgement is not optional.

Never de-scoped for capacity: Slot 0, Phase 0 (truth, code
repairs, privacy), the refusal demo (2.7), the classified veto
(2.8) with its bias fixture (2.9), or any gate on any initiative
that does ship.

## Sizing and capacity (audit F5-09)

Phases are **not** equivalent in size, and this roadmap no longer
presents initiative counts as if they were. Each initiative
carries a t-shirt size in its table: **S = 1, M = 2, L = 4,
XL = 8 planning units** (a planning unit is a relative size
estimate, not a duration). Capacity assumption, stated plainly:
one builder seat per area, working areas in parallel where the
dependency column allows, reviewer and compliance seats shared
across areas. Phase totals:

Unit totals now count **all** the load a phase carries, as three
explicit lines (round 2, C-07 — the previous totals recounted to
exactly the initiatives alone, which made gate load and Row X
arithmetically free):

- **Initiative units:** the sum of the phase's initiative sizes
  at S = 1, M = 2, L = 4, XL = 8.
- **Gate load: 1 planning unit per initiative** — a stated
  planning assumption (flat average across sizes) converting the
  per-initiative gate costs in the resourcing table above (tests
  + E2E, blind review with rework loops, compliance review, the
  phase's batched owner UAT) into planning units. The day
  estimates in that table govern seat time; this flat unit is
  what the phase totals carry, so gate load is visible in the
  arithmetic instead of asserted beside it.
- **Row X load:** the phase's standing slice, sized per phase in
  the Standing row X section (Slot 0: 2; Phase 0: 3; Phase 1: 2;
  Phase 2: 3; Phase 3: 2; Phase 4: 2; Phase 5: 3 — 17 units
  across the 7 slices).

| Slot/Phase | Initiatives | Initiative units | Gate load (1 per initiative) | Row X load | Total planning units (estimate) |
|---|---|---|---|---|---|
| Slot 0 | 5 | 14 | 5 | 2 | 21 |
| Phase 0 | 11 | 28 | 11 | 3 | 42 |
| Phase 1 | 8 | 18 | 8 | 2 | 28 |
| Phase 2 | 9 | 20 | 9 | 3 | 32 |
| Phase 3 | 4 | 10 | 4 | 2 | 16 |
| Phase 4 | 4 | 7 | 4 | 2 | 13 |
| Phase 5 | 11 | 21 | 11 | 3 | 35 |

Programme total: **52 initiatives, 187 planning units**
(118 initiative units + 52 gate units + 17 Row X units). A fresh
recount reproduces every line: initiative units sum from the
phase tables below, gate load is the initiative count, and Row X
load is the slice size stated for that phase.

## Where this sits against the annual roadmap

Current state (team-progress record, 2026-10-15): complete — 00, 04,
05, 06, 07, 10, 11, 12. Built 100% but ship-blocked: **01** (owner
UAT owed), **02** (owner UAT owed + a fix-first item open on the
model card), **03** (owner UAT owed + a legal RESHAPE to build:
per-event notification choice in the installer wizard, default
off). **08 stays CUT** (Rule 2). **09**: circuit-breaker STRICT
shape locked 2026-09-29; this roadmap produces drafts only for
third parties, everywhere. **09's classification, stated so
Slot 0's closure is verifiable (round 2, C-17):** 09 is neither
counted complete nor counted ship-blocked in this paragraph's
vocabulary, and it carries **no Slot 0 item** — no UAT for 09 is
scheduled or owed under this roadmap, and Slot 0's closure claim
(see below) covers the owed work for 01, 02, and 03 only. If the
annual record later shows an owed item for 09, Slot 0 reopens by
recorded amendment; until then, the owed list Slot 0 closes is
01, 02, and 03, and no summary wording claims more. Feature E1 now conforms to the CUT
list (prepare-only) for messages to the user's *own* channels as
well as for third parties; where any earlier text and this
roadmap's CUT list conflict, **the CUT list
governs** (see the PAUSE / CUT list).

### Slot 0 — owed annual work (scheduled first, named owners)

Slot 0 runs **before** Phase 0's build work, in the order stated
in the table. The precedence rationale, stated so it covers every
row and contradicts none of them:

- 0-A and 0-B run first, on the current tree, because 0.2 migrates
  the profile shape and Phase 2 changes the scoring path, and
  running those first would change the data and behaviour the 01
  and 02 UATs were written against (PM change 1).
- 0-C1 and 0-C2 change neither the profile shape nor the scoring
  path, so building them after 0-A/0-B does not disturb those
  UATs' baselines.
- Initiative 03's UAT (0-D) is written against behaviour that
  includes the 03 RESHAPE, so 0-D runs **after** 0-C1/0-C2, against
  the built result — it is not run against the pre-RESHAPE tree
  and then assumed to carry over.
- One exception, stated plainly: initiative 0.1 (copy-only claims
  corrections) may run in parallel with Slot 0 — it touches no code
  or data shape the UATs exercise.

| Slot | Work | Owner | Size |
|---|---|---|---|
| 0-A | Initiative 01 UAT — seeded acceptance run, owner accept/reject | Owner, with team-run script | M |
| 0-B | Initiative 02 UAT + model-card fix-first item, closed and re-checked | 02 team | L |
| 0-C1 | Initiative 03 legal RESHAPE build — per-event notification choice in the installer wizard, default off; blind compliance review. There is no quiet-hours bypass in this build: the bypass is dropped, matching feature E1's rule — no event class may send during quiet hours, or at any hour, without the user's act (audit F6-11) | 03 team | M |
| 0-C2 | Consent-model reconciliation (split from 0-C; audit F5-07) — the two existing consent systems (grill channel preferences and the notify per-event catalog) merged into the one model specified in feature E1, catalog wins on conflict. Own acceptance: every existing grill and notify send path reads the merged model, and a conflict fixture resolves to the catalog. **Task 0-C3 (round 2, D-01-OBS — a named task inside 0-C2's scope and size, not a sixth Slot 0 initiative): notify conformance.** Each existing `notify.py` send path — the webhook delivery, the ntfy delivery, and the digest queue/flush path (`queue_for_digest` / `flush_digest`) — is individually dispositioned in writing and then re-scoped to the prepare-only / user-initiated model: the path prepares and holds locally, and delivers only on the user's act in the moment, or the path is removed. No path is carried forward on the ground that the merged consent model governs it; consent governs what may be prepared, never when anything sends (the CUT list). Acceptance adds: an inventory line per path (path, disposition, evidence), and a test with every event opt-in on asserting zero remote deliveries until a user act initiates one | 03 team | L |
| 0-D | Initiative 03 UAT — seeded acceptance run against the built 0-C1/0-C2 result: the wizard choice defaults off, each per-event choice is honoured, and the merged consent model governs a grill send and a notify send. Run by the 03 team; pass condition is the project owner's one-line-per-item accept on the seeded run, with a lived check on the owner's own install before Slot 0 is counted closed | Owner, with team-run script | M |

0-C1/0-C2 landing early is what lets Phase 1 use real channels
lawfully (PM changes 10, 26): the consent model exists before any
new channel work is built on top of it. **Slot 0 counts as closed
only when 0-A, 0-B, 0-C1, 0-C2, and 0-D have all passed their
gates** — no earlier summary wording claims more than that.

## Standing row X — cross-cutting (every phase, counted honestly)

**Accountable owner: the PM seat**, in every phase including
Slot 0. Per-phase working owners are named in each phase header
below (Slot 0: the PM seat). Row X is a standing workstream, not
an initiative: it is counted **separately** as **7 standing
slices** (Slot 0 + Phases 0–5), and it is **not** included in the
52-initiative total. **Slice sizes (round 2, C-07 — stated per
phase so the load recounts): Slot 0: 2 units; Phase 0: 3;
Phase 1: 2; Phase 2: 3; Phase 3: 2; Phase 4: 2; Phase 5: 3 —
17 units in total, carried as the Row X line in each phase's
planning-unit total in the sizing table above.**

Scope: surfaces (CLI/web/dashboard rendering for that phase's
features), user docs and onboarding changes, claims-register
upkeep (brief §6 re-checked against the code at phase close; site
copy updated in the same motion), and test-fixture ownership
(fixture profiles, postings, connections export, trend fixtures,
the site demo's browser test path). Full list: `feature-sets.md`,
"standing workstream".

**Row X gate:** a phase does not close until its Row X slice
passes a checklist review recorded with the phase gate — claims
register re-checked, docs for the phase's surfaces written,
fixtures the next phase's E2E needs are built and versioned.
Unowned work is how the claims debt happened; this row is the
fix (PM change 31).

Phase 0's Row X slice also carries one named task from the audit
(F6-04, expanded round 2 by D-02 / D-03 / D-04): a compliance
review of the **retained** surface the product keeps (not new
work — the existing surface), recording its authentication,
periodicity, and terms posture in writing, and ending in a
recorded **keep / scope-down / cut decision per surface**. The
retained set is **four** surfaces, and no summary language in
this roadmap states or implies a smaller set: board search,
`watch.py`, `providers/`, and **the drip-apply scheduler
`apply_queue.py`** (round 2, D-02 — scheduled-for items, the
queue-run confirm preset, and the browser form-fill /
resume-upload path under `VETO_BROWSER_APPLY=1`; it was named in
no document before this round). Each of the four gets the same
decision, owner, and gate treatment. Decision owner: the PM
seat, as Row X's accountable owner. The roadmap PAUSE on new
providers stands; this task stops the retained surface being
carried forward unexamined. **Conformance rule (round 2, D-03):
a "keep" decision is valid only for a surface that meets the
retained-surface posture in feature E2 — user-initiated
operation only, no standing periodic sends or fetches under
consent, public / unauthenticated access only — or that will
meet it under initiative 0.9's conformance work before Phase 0
closes. A surface that cannot meet the posture is scoped down
until it does, or cut; a "keep" that leaves a non-conforming
surface unchanged is not an available outcome of this task.**
The decision is recorded **before initiative 0.9 starts** (0.9
implements it), not at phase close. **Gate: Phase 0 does not
close, and the repositioning's legal story is not used publicly,
until that decision is recorded and 0.9 has passed its gates.**

Phase 0's Row X slice carries a second named task (round 2,
D-04): **the Gmail / WhatsApp automated-access terms audit.**
The brief (§7 item 2) concedes neither channel has been audited
against its platform's automated-access terms; this task closes
that item. **Owner: the compliance reviewer seat**, recorded as
a per-channel verdict (Gmail, WhatsApp) against each platform's
automated-access terms, in writing, before Phase 1 starts.
**Gate: initiative 1.1 does not launch on a channel with no
recorded verdict, or with a verdict against automated access on
that channel.** 1.1's channel scope is conditional on the
outcome (see 1.1): a channel the audit clears launches; a
channel it does not clear is removed from 1.1's launch scope,
its launch claim, and its E2E, in writing at the audit's gate —
and if the audit clears neither Gmail nor WhatsApp, 1.1 launches
on in-product chat only and its status for the channel half is
**built, gate pending** until a channel clears.

## Phase 0 — Truth first (foundations)

**Row X owner this phase: the PM seat** (standing cross-cutting row — surfaces, docs, claims-register upkeep, fixtures).

Goal: public claims match the code, the known code defects under
today's claims are repaired, the ledger exists in core with its
privacy mechanisms built, and there is one tree with one veto
behaviour.

| Initiative | Scope | Depends on | Size |
|---|---|---|---|
| 0.1 Claims-debt sweep | Correct **the full claims-debt list in the brief, as revised** — **32 items, counted once: CD-01…CD-32.** The count, stated so it cannot be read two ways (round 2, C-12): CD-01…CD-13 are the original thirteen; CD-14…CD-22 are the audit's nine additions (the veto-screen fail-closed guarantee, the letter-suppression guarantee, the live demo's "real grill" labelling, the installer/PWA page, the calendar handoff, the mentor handshake commands, "auto-updated" stages, the removed-boards docs, and the extra grill-answers locations); CD-23…CD-25 are the round-1 re-sweep's three (the approval-gate copy for tailored variants, the absolute network-traffic claim, and the wrong default grill channel); CD-26…CD-32 are the round-2 seven (the crew fail-closed/ledger guarantees, the referral-demo fabricated chain, the DocsPage doctor checks, the DecoderPage exactness claim, the drip-queue fail-closed risk run, the LinkedIn per-sentence provenance claim, and the DocsPage honesty-guarantee FAQ). 13 + 9 + 3 + 7 = 32. The nine audit additions were numbered F2-01…F2-09 in the audit's own working papers — **those are the same nine items as CD-14…CD-22, not nine further items**; the F2 numbers are not used in this package, and no count in this roadmap adds them on top of the CD numbers. Each item: the copy is corrected **or** the surface is corrected, verified item-by-item against a named code fact. Plus a **repeat sweep step**: the sweep's search method is re-run over all site specs, site pages, and product docs before the gate closes, and anything it finds is added to the list and corrected in the same initiative — the list must be exhaustive at gate time, not at writing time. Copy-only, except where an item's honest fix is a surface correction | Slot 0 not required (see preamble exception) | L |
| 0.2a Ledger schema + migration | A1 core: schema, store, migration, **schema version field, pre-migration backup, tested restore**. The schema carries the entry fields the revised A1 spec defines, including any time fields that spec adds for proof age (cross-document note: F4-05 is owned by the feature-sets builder; this initiative builds the fields the revised spec names, and does not invent them) | Slot 0-A/0-B baselines | L |
| 0.2b Ledger wiring + profile view | Registration in plugin lists; profile view (CLI/web/dashboard) with proven / in review / unverified markers | 0.2a | M |
| 0.2c Consumer regression pass | Wizard, tailor, match, resume builder verified against migrated profiles | 0.2b | M |
| 0.3 One tree, one veto behaviour (F1-01) | Reconcile the two trees' veto behaviour: the insufficient-signal veto (3+ axes on unknown defaults) exists only in the live tree; the tree these documents describe vetoes on score alone. End state: one tree, one behaviour — the insufficient-signal rule present and tested in the tree the package grades claims against, or the rule formally removed from both trees and from every claim. Docs and the claims register updated to name the tree graded. **This initiative has two allowed outcomes with different downstream effects; the re-plan rule for each is stated in "Phase 0 forks — re-plan triggers" below, and the outcome taken is recorded at this initiative's gate** | Slot 0-A/0-B baselines | M |
| 0.4 Approved-variant save repair (F1-04) | Repair the approved-variant save path: the only caller (`dashboard.py`) passes a result dict and a job dict against `save_approved_variant(job_id: str, resume_md: str, cover_letter: str)` and then treats the returned path as a dict. Fix the caller (or the signature, with all callers updated). Acceptance includes a **regression test that the variant the user approved is the variant on record**, read back through a user surface | — | M |
| 0.5 Honesty-scan gate wiring (F1-05) | Wire the honesty scan into **the single C3 gate** (feature C3, as unified in the round-2 feature-sets text) in the blocking path — one gate, one scan, one pass rule: the **proven-only rule** (a claim passes only where it traces to an approved ledger entry with proof attached), applied by that gate alongside its existing keyword, skill, and years checks, so the categories the scan exists to catch — invented numbers/metrics and invented proper nouns (employers, names) — can actually block. There is **no second, separate check with its own rule** in this initiative or anywhere in this roadmap: initiative 3.3's approval flow calls this same C3 gate, it does not build another one (round 2, C-09). Acceptance includes tests, run under the proven-only rule, in which **a fabricated metric in a cover letter blocks** and a fabricated employer blocks; the framework-absent behaviour is stated and tested, not silent | — | M |
| 0.6 Per-line provenance surface (F1-03) | Wire per-line provenance into a user-facing surface: `tailor_with_provenance()` gains a real caller in a core surface (web UI or dashboard), so a user can see, for a tailored resume, which lines trace to which sources. Acceptance states the function's own limits plainly (headings, the name/contact line, and date lines carry no per-line entry — audit F1-09): those lines are shown as untraced, never silently assigned a source. If wiring proves impossible in this phase, the fallback is a formal descope: provenance is removed from every present-tense claim until a later, separately gated initiative wires it — the descope is recorded in the claims register, not left as wording. **This initiative has two allowed outcomes with different downstream effects; the re-plan rule for each is stated in "Phase 0 forks — re-plan triggers" below, and the outcome taken is recorded at this initiative's gate** | 0.2b | M |
| 0.7 Ledger privacy mechanisms (F6-05…F6-08) | Buildable privacy work for the most sensitive store, as specified lines — not a documentation promise: **(a) confidentiality** — owner-only file permissions as the floor for the ledger and its backups, checked at startup with a warning when they are wider than owner-only, exactly as feature A1 specifies; no encryption claim is made in this initiative — encryption at rest is initiative 0.8's work, and no product copy may claim the ledger is encrypted by the product until 0.8 ships; **(b) ledger export, delete, and retention** — a user-facing export in a stated format, a delete that deletes, and the retention rule in A1's data-lifecycle table (for ongoing backups: the most recent 5 are kept and any backup older than 90 days is deleted), each with acceptance tests; **(c) deletion propagation** — deleting a proof or a record states and implements what happens to derivative artefacts, the persisted delta store, the proposal log, session stores, the local work log, and backups, and the limits are told to the user at delete time; **(d) per-store retention rules, implemented** — every store the package creates (delta store, proposal log, session-type log, outcomes, verdict record, grill/mock session stores) gets a retention, export, and deletion rule in one table, built for the stores this phase owns and declared as dependencies for the stores later phases create. **Round 2 (D-08): this initiative's scope also covers implementing retention, export, and delete for the retained stores the round-1 table omitted — the watches store, the notify log and digest queue, the per-application experiment ledger, the applications / saved-jobs store, and the apply queue store — each with its row in the feature-sets lifecycle table (cross-document: the rows themselves are the feature-sets builder's) and its implementation and acceptance test here, not only the ledger-family stores named in round 1;** **(e) field tiering** — the sensitive-field tiers (compensation, clearance, authorisation, and the rest of the ledger) are defined here; enforcement on channel sends is built in 1.1 | 0.2a | L |
| 0.8 Encrypted ledger store | Encryption at rest for the A1 bundle, as specified in feature A1's confidentiality section and its store-class table — this initiative, not A1, ships product-built encryption. Scope, stated to match A1's table exactly (round 2, D-06/D-07): the evidence ledger and all its backups, the proposal queue and proposal log, the per-job delta store, and the verdict record — held in the same encrypted store bundle, under the same one key, to A1's specification. The stores A1's table places outside this scope (grill session records, mock/debrief history, tailored artefacts, and user-created export files) are not in this initiative's encrypted scope; they carry the permission posture and mitigations A1's table states for them. Acceptance: the raw files of every store in the bundle are unreadable without the user's key; migration from the unencrypted stores to the encrypted bundle is lossless for each bundle store; A1's permission checks still run on the encrypted bundle stores and their containing directories. Until this initiative ships, no product copy may claim the ledger is encrypted by the product | 0.7 | M |
| 0.9 Retained-surface conformance implementation (round 2, D-03) | Performs the conformance work the Phase 0 Row X decision (Standing row X) records, for each of the four retained surfaces (board search, `watch.py`, `providers/`, `apply_queue.py`): a surface the decision keeps or scopes down is brought to the E2 posture — user-initiated operation only, no standing periodic sends or fetches under consent, public / unauthenticated access only. Named work includes: removing or re-scoping `watch.py`'s cron entry point so watched-company checks run only on a user-initiated query or in a user-opened session, and re-scoping `apply_queue.py`'s scheduled-for / queue-run preset path so no scheduled or preset-consent run performs the browser form-fill / resume-upload — that path runs only on a user act in the moment, or is removed, per the recorded decision. A surface the decision cuts is removed, not carried. **Gate: a retained surface's continued use is not relied on publicly — in claims, docs, or the site — until this initiative has passed its gates for that surface** | Row X Phase 0 decision recorded (Standing row X) | M |

### Phase 0 forks — re-plan triggers (round 2, C-08)

Two Phase 0 initiatives are allowed to end in either of two
states. Both outcomes of each fork are planned here, so the
roadmap is executable under either without improvisation. In
each case the outcome taken is recorded at the initiative's
gate, the trigger below fires in the same motion, and no
downstream initiative starts on a dependency the recorded
outcome removed.

**Fork 0.3 — the insufficient-signal rule.**

- *Outcome A — the rule is present and tested in the graded
  tree.* Dependencies stand as written: 2.1 classifies against
  the one behaviour, 2.8 builds B4 including the rule, the Phase
  2 E2E insufficient-signal fixture runs as written. No re-plan.
- *Outcome B — the rule is formally removed from both trees and
  from every claim.* Trigger, fired at 0.3's gate before any
  Phase 2 initiative starts: (i) **2.8 is re-scoped** — B4's
  thin-evidence class as defined by the insufficient-signal
  trigger is removed from its scope, and 2.8's dependency on 0.3
  is recorded as satisfied under Outcome B only with that
  re-scope in place (cross-document: the B4 spec change itself
  is the feature-sets builder's, recorded as a dependency of
  this trigger); (ii) **2.9's fixture set is re-frozen** without
  insufficient-signal fixtures; (iii) the **Phase 2 E2E**
  insufficient-signal fixture is deleted and replaced with the
  score-veto fixture the remaining classes require; (iv) Row X
  updates claim 2's register entry and every claim citing the
  rule in the same phase-close motion. No Phase 2 initiative
  starts until (i)–(iv) are recorded.

**Fork 0.6 — the provenance surface.**

- *Outcome A — provenance is wired into a user-facing surface.*
  Dependencies stand as written: 1.5 labels the 0.6 surface,
  3.1 renders grill provenance on it. No re-plan.
- *Outcome B — provenance is formally descoped.* Trigger, fired
  at 0.6's gate: (i) **1.5 loses its provenance dependency** —
  its dependency on 0.6 is recorded as removed, and its
  acceptance criteria revert to the fallback stated in
  feature-sets for a descoped provenance surface (labels on the
  surfaces that exist without it, starting with the profile
  view); the delta/provenance label assertions stay **built,
  gate pending** until a wiring initiative lands; (ii) **3.1
  loses its rendering surface dependency on 0.6** — 3.1 does not
  start until a new, separately gated wiring initiative,
  added by recorded roadmap amendment at this trigger (sized
  and placed in Phase 3 before 3.1), wires the surface or 3.1
  is itself re-scoped by that amendment to the fallback the
  feature-sets text states; (iii) Row X records the descope in
  the claims register (already 0.6's own acceptance) and removes
  every present-tense provenance claim in the same motion. The
  amendment is the deliverable of the trigger — Phase 1 does not
  proceed on the pre-fork dependency column.

- **E2E — 0.1 (tests truth, not absence; PM change 4):** for each
  of the 32 debt items, assert the replacement line is *true*
  against a named code fact (function, path, behaviour) from the
  audit — a page that merely stops making the claim does not pass.
  The repeat sweep's output (items found, items corrected) is
  recorded with the gate.
- **E2E — 0.2:** migration against fixture profiles (full, empty,
  corrupt) via the real CLI; backup → migrate → restore reproduces
  the original byte-for-byte; `find_for_requirement()` parity core
  vs standalone i05.
- **E2E — code repairs:** 0.3's two-tree test (the same fixture
  job scored in the graded tree produces the insufficient-signal
  veto, or the rule is absent everywhere including the register);
  0.4's save-and-read-back regression test; 0.5's fabricated-metric
  and fabricated-employer block tests, run with the framework
  present and absent; 0.6's provenance view exercised through the
  real surface, untraced lines shown as untraced.
- **E2E — privacy (0.7):** ledger export round-trips; ledger delete
  removes the store and its backup copy per the stated propagation
  rules; a derivative artefact citing deleted proof is flagged
  *and* the user-facing delete text states what survives and why;
  the per-store retention table is checked store by store against
  the code, **including the round-2 stores (watches, notify log
  and digest queue, experiment ledger, applications / saved-jobs,
  apply queue): each store's retention, export, and delete is
  exercised, not only the ledger-family stores (D-08)**;
  **retained-surface conformance (0.9):** with the recorded
  decision applied, `watch.py` performs no fetch without a
  user-initiated query or session, and the apply queue performs
  no scheduled or preset-consent form-fill / resume-upload
  (D-03).
- **UAT (seeded run is the gate; lived check follows — the Phase 5
  pattern, applied everywhere):** seeded run items = the debt-list
  pages checked against fixtures + migration/restore on fixture
  profiles + the 0.7 export/delete run on a fixture ledger. Only
  after the seeded run passes: a lived check on the owner's own
  profile (view shows proven / in review / unverified markers;
  nothing missing or reworded) — the owner's real profile is never
  the migration test bed. One line per item.

## Phase 1 — The profile compounds

**Row X owner this phase: the UX seat** (standing cross-cutting row — surfaces, docs, claims-register upkeep, fixtures).

Goal: the ledger deepens through use, with approval at every write,
claims carry a proof state from intake, and the user reaches a
first useful result fast enough to measure.

| Initiative | Scope | Depends on | Size |
|---|---|---|---|
| 1.2a Proposal contract | A3 core: proposal store, proposal log, **30-day expiry** semantics. The producer set is exactly the set the revised A3 spec enumerates — no producer is claimed that no feature builds (audit F4-18, cross-document) | 0.2a | M |
| 1.2b Approval surface | A3 in the action inbox: approve / edit / reject, conflict display, rejection suppression. **New build** — the inbox is read-only today | 1.2a | L |
| 1.1 Evidence grill | A2: profile-scoped grill sessions. **Launch scope, stated once (audit F5-12): Slot 0-C2 has already landed, so the consent model exists when this builds; the grill launches on chat and Gmail, and Phase 1's E2E exercises both.** **Channel scope is conditional on the terms audit (round 2, D-04): the grill launches on a channel only where the Phase 0 Row X terms audit (Standing row X) has recorded a verdict clearing that channel's automated access. If the audit does not clear Gmail, Gmail is removed from this launch scope, the launch claim, and the E2E below, in writing at the audit's gate, and the grill launches on chat and any cleared channel; the same rule applies to WhatsApp, in addition to its reply-path condition below. If the audit clears neither channel, this initiative launches on in-product chat only and its channel half is **built, gate pending** until a channel clears.** WhatsApp joins the launch claim only if its reply path is exercised on the disposable stack; if it cannot be exercised, WhatsApp is descoped from the phase's launch claim in writing at gate time. **Field-tiering enforcement (F6-10):** no message this feature sends over any channel quotes a field the 0.7 tiering rules mark as never-for-channel (compensation, clearance, authorisation at minimum); the E2E asserts it with a fixture ledger containing those fields | 1.2b (the approval half lands first — PM change 7), 0-C2, 0.7 (field tiers); **terms-audit gate (Standing row X, Phase 0 slice) for each channel in its launch scope** | L |
| 1.5 Intake standard | A5: unverified state at entry, proof request at intake, labels on the surfaces that exist in Phase 1 (profile view, provenance). Its classification consequence is asserted in Phase 2 (B2's fixture matrix carries the listed-but-unverified cell) — declared here, not hidden; 1.5's status until that Phase 2 assertion passes is **built, gate pending** under the standing rule | 0.2b, 0.6 (the provenance surface it labels), 1.2a/1.2b (the proof-attachment path runs through the A3 approval flow) | M |
| 1.3 Depth meter | A4, formula as specced (feature A4), gains list wired to 1.1. **Role-family definition — sequenced before this consumer (round 2, C-04):** the shared role-family definition is stated in feature A4 (cross-document: the definition text itself is the feature-sets builder's, fixed this round) and is **frozen before this initiative starts** — a start gate, recorded by the PM seat: normalisation, clustering, and the matching predicate for A4's 40-point term are the frozen text, the two hand-computed fixture ledgers are computed against that frozen text, and the code's existing keyword-heuristic use of the same term (`calibration.py`, consumed by E4) is reconciled in writing in that freeze (one term, one definition, or the two uses renamed apart). This initiative **implements** the frozen definition for A4's per-family views; 2.1 implements it for classification (see 2.1 — it does not author it either). **Gate (audit F4-10):** this initiative cannot pass its gate until the fixture ledgers are recomputed against the frozen definition; if the freeze has not landed, this initiative's status is **built, gate pending**, exactly as 1.5's deferred assertion is handled | **Definition freeze (feature A4, before build start)**, 0.2a; gains links need 1.1 | M |
| 1.4 Requirement extraction | B1, with the frozen expected lists in the fixtures before build starts. Its shape source is the existing i04 requirement schema it reuses, which predates 0.2a — stated so nobody waits for, or blames, the ledger migration for this shape | — (parallel; shape source is the existing i04 schema) | M |
| 1.6a Time-to-first-value — intake-budget half (F7-05; split round 2, C-06) | The half of the cold-start measure Phase 1 can honestly measure, because its objects exist in Phase 1: from intake start, the question count the intake asks — the A5 proof requests plus the grill sessions run — and the time to the first claim reaching proven. Measured locally, per user, on the user's own machine (Rule 2 — no cross-user counting). **Target: the intake asks no more than the A5 proof requests plus one grill session (≈5 questions) in a first sitting.** The Phase 1 gate reports the seeded-run figures against the target. A miss does not pass silently and does not close this initiative: its status stays **built, gate pending** until the project owner records a decision (fix the intake, or accept the figure with the rationale recorded) | 1.5, 1.4, 1.1 (the grill sessions it counts) | S |
| 1.6b Time-to-first-value — first-delta half (F7-05; split round 2, C-06) | The first-delta half of the cold-start measure: from intake start, the time and the question count to the first delta shown. **A first delta is a Phase 2 artefact** (2.1 classification, 2.2 delta assembly, 2.3 rendering) — it does not exist in Phase 1, so this half measures nothing in Phase 1 and no Phase 1 gate reports a figure for it. This initiative builds the instrument in Phase 1 (the local timer / question counter that 1.6a uses, extended to the delta event) and is then explicitly **built, gate pending** under the standing gate-completion rule until its named gate lands: **the Phase 2 delta gate — 2.2 and 2.3 shipped and the Phase 2 seeded new-user run (Phase 2 E2E) recording time and question count from intake start to the first delta rendered.** **Target: a new user who pastes one posting reaches a first delta within one sitting.** The sign-off lands in Phase 2, recorded against this initiative; Phase 1's closure counts this initiative as gate pending, not done | 1.6a (the instrument), **2.2, 2.3 (the gate named in the scope)** | S |

- **E2E:** disposable-stack loop — seed profile → evidence grill
  over chat → approve two answers → depth moves by the
  hand-computed amounts → **Gmail reply path exercised** (subject-tag
  parsing against the new profile-scoped session type — Gmail is in
  the launch scope, per 1.1; if WhatsApp cannot be exercised on
  the stack, it is descoped from the phase's launch claim in
  writing) → **field-tiering test:** a fixture ledger holding
  compensation, clearance, and authorisation fields produces grill
  messages over chat and Gmail quoting none of them → **A3
  invariant test:** run all producers, assert the ledger is
  unchanged until an approval exists → **A5 sweep:** an unverified
  claim renders labelled on the profile view and provenance
  surfaces (the delta-surface label check runs in Phase 2's E2E,
  where delta surfaces exist) → **time-to-first-value (1.6a only):** the seeded
  new-user run records the intake question count (proof requests
  + grill sessions) and the time to the first claim reaching
  proven. **No first-delta figure is recorded in this phase**
  (round 2, C-06): the first-delta measurement is 1.6b's, gated
  in Phase 2 where delta surfaces exist.
- **UAT (seeded run is the gate; lived check follows):** seeded run
  on the fixture profile — items: questions target genuinely
  unverified claims; one approval lands in the ledger with its
  source; depth moved by the hand-computed amount; one unverified
  claim shows its label on every surface that exists in this phase;
  the 1.6a intake-budget figures are shown against the 1.6a
  target, and 1.6b is recorded as **built, gate pending** (its
  gate is the Phase 2 delta gate — see 1.6b), not as measured. Lived check: the same grill run once on the owner's own
  profile as confirmation. One line per item.

## Phase 2 — The delta engine

**Row X owner this phase: the Research seat** (standing cross-cutting row — surfaces, docs, claims-register upkeep, fixtures).

Goal: per-job delta, classified and explained, with the veto given a
path — and the demo that carries the strategy, as early as the
delta honestly allows. Entry condition: Slot 0-B closed (the scoring path is frozen
until the model-card fix lands — PM change 15).

The old 2.4 bundled five separable projects (audit F5-06); they are
split below as 2.4, 2.5, 2.6, and 2.7, each with its own gates.
**The refusal demo (2.7) is pulled to the earliest honest point
(audit F5-02, F5-11, F4-14):** its dependency is exactly the
refusal it demonstrates — the score veto that ships today (claim
2, as reconciled by 0.3) — plus the delta report from 2.2. It
does **not** depend on the classified veto (2.8). If the demo is
later upgraded to showcase the classified veto, that upgrade is a
story inside 2.8's gate, not a new dependency for the demo's
launch.

| Initiative | Scope | Depends on | Size |
|---|---|---|---|
| 2.1 Classification | B2 into the core scoring path; the **alias table** ships here; the **role-family definition** — frozen in feature A4 before 1.3 started (round 2, C-04) — is **implemented** here for classification (feature B2). One owner per act: the feature-sets A4 text owns the definition, 1.3 implements it for the depth views, 2.1 implements it here | 0.2a, 0.3 (one veto behaviour to classify against), 1.4, **the A4 definition freeze (see 1.3)** | L |
| 2.2 Delta assembly | B3 engine: report assembly, impact ordering, per-job delta persistence (with ledger version). **Delta staleness (audit F4-06):** a persisted delta is flagged stale — visibly, wherever it is shown or trended — when the ledger version advances past the version it was computed against; recompute and flag rules follow the revised B3 spec (cross-document) | 2.1 | M |
| 2.3 Delta report — CLI | B3 rendering, CLI surface. All-supported wording does not point the user at prep (D1) until Phase 4 exists; until then the report uses the degraded wording the revised B3 spec states (audit F4-19, cross-document) | 2.2 | S |
| 2.4 Delta report — web/dashboard | B3 rendering on the web UI and dashboard only (split from old 2.4) | 2.2 | M |
| 2.5 Radar gradient | B6 colour rule in `radar.py` **and** the site demo's radar component, to one spec, including the site-demo parity change through the site's preview-then-owner-pass process (split from old 2.4). The rendering word for the salary/recency axes is **"unclassified"** — B6's term, used in this initiative's docs and surfaces exactly as B6 states it (round 2, C-11): an axis with no requirement classification. Unclassified governs colour only; when a salary or recency axis is scored on a neutral default it counts toward B4's insufficient-signal rule exactly as B4 states. The word "unknown" is not used for these axes anywhere in this initiative; in this package "unknown" means only B4's sense (a fit axis scored on a default for missing profile facts) (audit F4-19) | 2.1 (axis colours read B2 classifications), 2.4 | M |
| 2.6 Site demo — read-only delta view | The site demo gains a read-only delta report view fed by fixture data (split from old 2.4), shipped through the preview-then-owner-pass process, never direct to production | 2.2 | S |
| 2.7 Site demo — interactive refusal demo | The brief §4 acquisition channel (split from old 2.4): a visitor grill flow against a fixture profile, **a refusal on the unqualified fixture path** produced by the shipped score veto, and the fixture delta report shown; fixture data only, nothing stored. The demo is labelled on its face as a fixture demo — it cannot show a visitor their own delta, and it does not pretend to (audit F7-09). **Hosted-data posture (audit F6-14; round 2, D-14):** this initiative states the demo page's server-log, analytics, and error-reporting posture in writing, as feature B6 specifies it — including host/CDN access logs, the identity of any analytics or error-reporting processor, and log retention. Verification follows B6's two parts: the browser test asserts non-persistence of visitor input, and a configuration check asserts the log, analytics, and error-reporting settings. **Pre-launch checks owned here:** a funnel definition (visit → demo completion → install click) that counts events and stores no visitor input, and a name/line discoverability check covering all four elements — search volume, SERP presence and competition, registry name-collision checks, and an unaided-recall test of the product name and the refusal line — run before the demo ships, with the result recorded before the demo ships (audit F7-04, F7-11 — the brief owns any strategy change the results force; this initiative owns running the checks). **Recall test, specified so it can fail (round 2, C-10):** *Method / sample* — 30 participants drawn from the target segment (active job seekers), none previously exposed to the product name or line; each sees the name and the refusal line once, for 10 seconds, on the demo landing headline, followed by a 10-minute unrelated distractor task, then answers unaided. *Instrument* — two unaided prompts, in order: "What was the product called?" and "What did it say it would not do?"; answers scored against the exact name and against the line's gist (refusal to invent / add unbacked claims) by a scorer who did not run the session. *Pass threshold* — at least 18 of 30 (60%) recall the product name unaided, and at least 15 of 30 (50%) reproduce the refusal line's gist. *Decision rule on a miss* — the demo does not ship under that name or line: the PM seat, as Row X owner, records the strategy decision the brief owns (rename, reline, or a recorded project-owner decision to ship despite the miss, with the figures published in the check record) **before** the demo ships, and a changed name or line is re-tested under this same method before it ships. A registry name-collision with a same-category product is likewise a fail under this rule, not a note | 2.2, 2.6; the shipped score veto (via 0.3). **Not** 2.8 | M |
| 2.8 Veto with a path | B4: three veto classes, change-my-answer conditions for **every** class including contested (per the revised B4 spec), user-visible verdict record (claim 7b). **Spec-freeze gate:** this initiative does not start until the revised B4/B2 specs freeze (i) the measurable thresholds for "skill-gap heavy" and "thin evidence" and the score/classification combining trigger (audit F4-03), and (ii) the mapping from the classification and veto classes onto the headline's "unproven or unqualified" (audit F4-01) — both are the feature-sets builder's; this roadmap declares them as start dependencies. **Verdict recording (audit F1-07):** where the framework checkout is absent, the record is kept locally, labelled as the local record, and a recording failure is shown to the user — never silent. **Delete (audit F4-11):** the record's delete acceptance covers its underlying stores as the revised B4 spec states, not only the surface. **Override instrumentation from first release (audit F7-08):** the overturn rate, its count, and the share of overrides where the named change-my-answer condition was unmet are computed and shown on the record surface from this release — not deferred to Phase 5. **Veto-moment return measure — the 14-day return (round 2, B-10 — the measure the brief §8 / §9 commits to shipping with this, the first classified-veto release; spec in feature B4, cross-document):** from this release, the verdict record also computes, per user and locally only (Rule 2), whether the user returns within 14 days of a first classified veto — a return is any later user-initiated session recorded in the local session record — and shows the figure (returns / first vetoes, with its count) on the record surface alongside the overturn rate. It is named in this initiative's acceptance: a fixture user whose first veto is followed by a return on day 13 counts, and one with no return by day 14 does not | 2.2, 0.3; spec freeze for B2/B4 as revised | L |
| 2.9 Classification bias fixture + quality measurement (F7-03) | A test corpus and a release gate for the classified veto, tied to 2.8's release: fixture career histories spanning non-quantified work (care, operations, support, early career), non-conventional paths (freelance, caregiving gaps, public sector, creative work), and non-native phrasing, each with spec-owner-authored expected classifications frozen before build. The gate **measures and reports the false-veto disparity** across those fixture families against the conventional-career fixtures. Release rule: if the disparity exceeds the threshold the project owner sets at the 2.8 spec freeze, 2.8 does not ship until the owner records a decision (fix, threshold change, or ship with the disparity published in the record surface's description). No threshold is invented in this roadmap | 2.1; ships as a gate on 2.8 | M |

- **E2E:** fixture matrix (supported / alias-only / unquantified /
  absent / years-short / listed-but-unverified) through the real CLI
  and web UI with identical classifications; **delta-surface A5
  label check** (an unverified claim renders labelled on the delta
  report — the Phase 1 deferral, closed here, and 1.5's gate
  sign-off recorded against it); **delta staleness check** (a
  ledger write flags the affected persisted deltas as stale);
  dashboard card rendered and checked;
  the three veto classes each produced by their fixture job;
  the insufficient-signal fixture (3+ unknown axes) produces the
  thin-evidence veto marked "insufficient signal" (B4);
  gradient colours asserted in rendered SVG **and** in the site demo
  via its browser test path (built under row X if absent);
  **demo flow:** the fixture grill completes in the site demo's
  browser test, the unqualified fixture path renders a refusal from
  the shipped score veto, the delta view matches the fixture's B3
  output, and no visitor input is stored or logged (asserted in the
  same browser test, including server logs);
  **bias fixture (2.9):** the disparity report is produced for the
  fixture families and checked against the hand-computed expected
  classifications;
  **model-card + calibration suites run unchanged** and a written
  note records what 2.1/2.8 change under a pinned personalised card;
**time-to-first-delta (1.6b's gate, round 2, C-06):** the
  seeded new-user run that starts at intake records the time and
  question count to the first delta rendered by 2.3, reported
  against 1.6b's one-sitting target; 1.6b's sign-off is recorded
  against this run, closing its gate-pending status from Phase 1;
  **veto-moment measure (2.8):** the fixture record's 14-day
  veto-moment return figure equals its hand-computed value
  (returns within 14 days of a first classified veto, with its
  count);
  **framework-absent case:** with the governance root unset, a veto
  is recorded to the local record, labelled as such, and a recording
  failure is surfaced to the user (PM change 17); **verdict record:**
  export produces the complete fixture record, delete removes it
  from the surface and its underlying stores per the revised spec,
  and the displayed overturn rate equals the hand-computed rate for
  the seeded vetoes and resolutions (B4 acceptance).
- **UAT (seeded run is the gate; lived check follows — the pattern
  every phase now states in both steps):** seeded run with two
  fixture postings (one the fixture profile is qualified for, one it
  is not). Items: the evidence gaps named are really evidence gaps;
  the skill gaps are really absent; the unqualified posting's veto
  class and path are right; the verdict record shows the fixture
  overturn rate with its count (B4); **the 2.9 disparity report is
  shown as its own line, accepted or the owner's release decision
  recorded**. **Plus the recognition run
  set (brief §9, owned here): five seeded personas each produce a
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
honesty-gated. Phase 3 is **first-time surfacing plus repair
completion**, not polish of a working flow: per-line provenance
had no user surface and the approved-variant save was broken
until Phase 0's 0.6 and 0.4 repaired them (audit F1-10).
**Serial order (one writer over `tailor.py` /
`cover_letters.py`): 3.1 → 3.2 → 3.3 → 3.4.** The phase is sized as
serial work; no parallelism is claimed (PM change 21).

| Initiative | Scope | Depends on | Size |
|---|---|---|---|
| 3.1 Grill-fed tailoring | C1: `get_qa_pairs()` wired in; grill provenance class, rendered on the 0.6 provenance surface. Includes C1's apply-gate fix — the full posting record is loaded before a gate-created grill session counts as complete; stripped-record sessions are labelled partial. Acceptance: a gate-created session for a fixture job produces gap and quantify questions | 1.2b, 0.6 | M |
| 3.2 Honesty scanner | C3 part (i): standalone scanner runnable on any artefact, no framework dependency. Builds on 0.5's gate wiring — the scanner and the gate's scan are one code path, not two | 0.2a, 0.5 | M |
| 3.3 Approval flow + the block | C2 canonical flow **including C3 part (ii)** — approval-time blocking lives here, where the flow exists (PM change 19); the block applies the revised C3 proof-state rule (a claim that traces only to an unverified entry does not pass as backed — cross-document, audit F4-02); stale-artefact handling; named consumers: packet, apply handoff, export. **Handoff initiation (audit F6-03):** each named consumer step requires a fresh human act at the moment of handoff, distinct from the earlier approval stamp, and the acceptance tests exercise that act for each consumer. The approval flow calls **the single C3 gate wired in 0.5** — the same gate, the same proven-only rule; this initiative builds no second block and no separate check (round 2, C-09). No text in this roadmap claims a block operates outside a flow (audit F6-12) | 3.1, 3.2, 0.4 (working approved-variant save) | L |
| 3.4 Letters from evidence | C4: ledger citations per proof paragraph; proof/intent labelling | 3.3 | M |

- **E2E:** grill → tailor → approve on a fixture job, asserting the
  grill-sourced line and its provenance; **apply-gate grill
  completeness:** a gate-created session for a fixture job produces
  gap and quantify questions (the full posting record is loaded
  first; a stripped-record session is asserted partial); seeded invented-claim drafts
  (metric / employer / skill) blocked at approval with lines named;
  a draft whose metric traces only to an unverified ledger entry
  blocked or labelled per the revised C3 rule, as specced;
  the same flow with the governance root unset; **stale flow:**
  approve an artefact, write to a ledger entry it cites, assert the
  artefact flips to stale and each named consumer warns (PM change
  20); **handoff flow:** packet, apply handoff, and export each
  require their fresh human act — no consumer proceeds on the
  approval stamp alone; **letter balance:** zero-proof fixture letter shows 0 proof /
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

| Initiative | Scope | Depends on | Size |
|---|---|---|---|
| 4.1 Delta-driven mocks | D1: question plans from 2.1 classifications, reason tags | 2.1 | M |
| 4.2 Evidence grading | D2: second rubric axis (proof used / missed / overclaimed) | 4.1, **3.2** (traceability logic — PM change 22) | M |
| 4.3 Debrief write-back | D3: proposals into the 1.2 queue (expiry per A3) | 4.2, 1.2b | S |
| 4.4 Prep brief 2.0 | D4: delta-first brief. **Sequenced after 4.1 under the same `briefs.py` writer** (PM change 22); its gap ordering follows the single ordering criterion the revised D4/B3 specs state — this roadmap no longer asserts two different criteria ("most likely to be probed" and "impact on the score") as if they were one (audit F4-15, cross-document) | 4.1, **2.2** (PM change 23) | M |

- **E2E:** scripted mock (deterministic answers) for a fixture job —
  question reason tags match the delta; paired answers (uses proof /
  ignores proof) score apart on the evidence axis only, craft within
  the ±5 band; debrief produces exactly the expected proposals;
  approving one reclassifies (B2) and leaves depth unchanged;
  attaching proof and approving the proof then moves depth (A4);
  **brief check:** every STAR story in the fixture brief cites an
  approved ledger entry and its top-3 gaps match the delta report's
  ordering under the revised single criterion (PM change 25).
- **UAT (seeded run is the gate; lived check follows):** seeded run
  executes the scripted fixture mock and brief; items: reason tags
  correct; brief's top-3 gaps match the delta report. Lived check:
  one mock for a real target role in hiring-manager mode **plus
  reading the prep brief**; item: the "stronger proof you missed"
  callouts are right about the owner's own history. One line per
  item.

## Phase 5 — Companion loop + trending

**Row X owner this phase: the PM seat** (standing cross-cutting row — surfaces, docs, claims-register upkeep, fixtures).

Goal: the daily habit and the long view. The legal piece (0-C1/0-C2) is
already landed in Slot 0 — it is not buried in this phase (PM
change 26).

The old 5.1 bundled four separable pieces and the old 5.6 bundled
four separately measured figures (audit F5-07); both are split
below. The old 5.2 is renamed and re-scoped under the CUT list
(audit F6-01): **nothing in this phase sends on a schedule or
under standing consent.**

| Initiative | Scope | Depends on | Size |
|---|---|---|---|
| 5.1 Check-in assembly | E1 part 1: assembly of the shipped pieces + the first-class `check-in` command. Assembly is local: it prepares the check-in; delivery mechanics are 5.3's, and they are user-initiated | 1.2b, 2.2, **3.3** (the check-in's action inbox includes C2 stale artefacts, which exist only after 3.3) | M |
| 5.2 Session typing + weekly recap | E1 part 2 (split from old 5.1): **session typing in the streak machinery and the weekly-recap no-application count** — brief §9's return measure is built here. This store gets its retention/export/delete rule from the 0.7 per-store table | 5.1 | S |
| 5.3 Check-in delivery mechanics — prepare-only, user-initiated | E1 part 3 (the old "Scheduler + reply routing", renamed and re-scoped): the check-in is **prepared** locally; a session starts only when the user opens or initiates it in their chosen channel — there is no scheduler hookup that sends, no standing-consent send, and no cadence step-down that changes what is sent (cadence is a local display state: what is prepared, and how often the user is shown it is ready). **Reply routing** for replies the user sends is built here. The posting-in-reply flow depends on 5.4 (declared forward dependency, as before — audit F5-01 was refuted on exactly this declaration; table order is ID order, and 5.4 may build first) | 5.1; 5.4 for the posting flow | M |
| 5.4 Feed-me intake | E2: paste-a-posting → decode → delta → grill queue. **Fetch boundary (audit F6-13):** a pasted link is fetched only unauthenticated; a link that resolves to a login wall or a board that restricts automated fetching is not fetched — the flow asks for pasted text instead | 2.2 | M |
| 5.5 Network delta | E3, **wired machinery only** (`referrals.py`, `network_crm.py`, `mentors.py` — including E3's mentor surface); i07 promotion is out of scope (PAUSE list). **2nd-degree path derivation built here (round 2, D-10 — E3's roadmap ask):** this initiative builds the import-consuming path derivation E3 requires — both edges from imported records only, as new or changed code (an import-consuming path function, not a parallel network feature); `network_crm.py: warm_path_to()` is **not** reused for 2nd-degree paths, and a notes mention yields no path and no hint of one. Acceptance, matching E3's three fixtures: an import fixture with both edges yields the 2nd-degree path; a fixture variant missing the second edge yields no 2nd-degree path and no hint of one; and a fixture whose only bridge is a notes mention of the target company (in the import or in the CRM store) yields no 2nd-degree path and no hint of one. **Consent mechanism built, not named (audit F6-09):** this initiative builds the consent mechanism for third-party contact data the revised E3 spec defines — whose consent, captured how, revocable how — plus per-contact retention, deletion, and correction for imported contacts. Until that mechanism passes its gate, the mentor surface and any path ranking over contacts do not ship. The network line renders in the **rendered delta report**, hence the 2.3/2.4 dependency | 2.2, **2.3/2.4** (the report surface the network line lives in), 0-C2 | L |
| 5.6 Follow-through | E4: autopsy → delta explanations; calibration evidence feed (rules unchanged). E4 does **not** feed B5: trending reads the outcome store itself, so 5.6 neither depends on nor blocks the 5.7–5.10 measures; where the feature list names B5 in E4's reuses, the roadmap reads that as a shared store, not a dependency (audit F5-13) | 2.2 | M |
| 5.7 Delta trend view | B5 part 1 (split from old 5.6): per-family trend computation and view over persisted deltas. The check-in trend line is a **joint** item: B5 supplies the line, E1 owns the surface; it is accepted in this phase's E2E once both 5.1 and 5.7 exist, and is a build dependency of neither alone (audit F5-08) | 2.2 | M |
| 5.8 Recurring-gap ranking | B5 part 2 (split from old 5.6): recurring-gap ranking across postings, one engine with `skill_gaps.py` — no divergent math | 2.2 | S |
| 5.9 Proof-closing rate | B5 part 3 (split from old 5.6): the proof-closing rate, computed from the persisted delta store joined to A3's proposal log. Build may precede Slot 0-A's closure; the measure is not announced or counted shipped until 0-A closes (see the note on 01 below) | 2.2, **1.2a** (the proposal log it joins to); Slot 0-A for ship/count | M |
| 5.10 Interviews-per-application figure | B5 part 4 (split from old 5.6): the per-user interviews-per-application figure against the user's own recorded baseline, always with its sample size (brief §9) | 2.2; Slot 0-A for ship/count (the outcome store is 01's surface) | S |
| 5.11 Outcome-validation loop (F7-02) | Veto and apply recommendations checked against recorded outcomes: for jobs the user applied to despite or because of a recommendation, and for vetoed jobs where an outcome is later known, the record compares the recommendation with what happened. The loop's report revisits the posting-as-ground-truth assumption with that data (a requirement the record contradicted may still have been a wish-list item; a vetoed job may have interviewed a comparable candidate — the report states what the outcome data can and cannot show). **Observability for vetoed-and-not-applied jobs (round 2, B-08):** an obeyed veto produces no application and no outcome event, so this initiative builds the mechanism that can observe that case — **user-reported outcome capture for vetoed jobs**: in a user-initiated check-in session (5.1's surface; nothing is fetched or sent by a scheduler), the user can record, per vetoed job, what they did (did not apply / applied anyway / applied later) and what happened as far as they know it (for example: the posting closed, the role was reposted, they learned the outcome another way), stored as a user-reported entry in the outcome store and labelled user-reported in every report — never presented as employer-side data. The reports state plainly which vetoes carry only this self-reported evidence and which carry none. **Cadence, pulled earlier:** a **first report, labelled preliminary** (small sample, user-reported veto outcomes included, limits stated on its face), is produced **four weeks after 2.8 ships**; the first full report follows one quarter after 2.8 ships, then per quarter. The preliminary report does not lift the fit-weight PAUSE below — that condition stays the first full report. Each report goes to the project owner as a decision point on the veto's thresholds and wording | 2.8, 5.6 (outcome data; reads the outcome store directly, not via 5.10's figure — so the de-scoping order above cannot strand it), 5.1 (the check-in surface its vetoed-job capture is offered in) | M |

Note on 01: 5.6, 5.9, and 5.10 can be *built* before Slot 0-A
closes, but cannot be announced or counted shipped until it does —
outcome data is 01's surface, and the brief's claims wait for the
owner's accept.

- **E2E:** fixture day — seeded jobs/inbox/outcomes produce the
  exact check-in; **prepare-only assertion:** with every opt-in on,
  the system performs **zero remote sends** until the user
  initiates a session (asserted from logs), and zero sends at all
  with all opt-ins off; a posting pasted in reply yields decode +
  delta + queued grill in-session; **network delta under
  outbound-call mocks records zero sends** while producing the
  documented warm paths from the fixture connections export (PM
  change 29), and the E3 consent mechanism's capture/revoke/delete
  paths are exercised on fixture contacts; **follow-through fixture** produces the autopsy →
  delta explanation with its sample size printed, and the
  calibration gate test passes (no weight change without evidence
  gate + recorded human approval); trend view reproduces
  hand-computed counts and renders counts-only below 3 deltas;
  **B5's split measures, each gated separately:** 5.8's ranking
  matches `analyze_gaps()` on the same job set; 5.9's proof-closing
  rate on the fixture window equals the hand-computed rate from
  the fixture delta store + A3's proposal log; 5.10's
  interviews-per-application figure equals its hand-computed
  value with its sample size shown; **outcome validation (5.11):**
  the fixture outcome set produces the first validation report,
  including at least one vetoed-job outcome that contradicts the
  posting's stated requirements, reported as such, **and at
  least one vetoed-and-not-applied job whose outcome enters only
  through 5.11's user-reported capture, labelled user-reported
  in the report (round 2, B-08)**.
- **UAT (seeded run first, then a lived check with defined lines —
  PM change 30):** Seeded run (the gate): the fixture day —
  check-in assembly, session typing, one user-initiated session,
  reply routing — each accepted/rejected on its own line; plus the
  trending items, one line each: 5.7's trend counts, 5.9's
  proof-closing rate, and 5.10's interviews-per-application figure
  for the fixture window match their hand-computed values. Lived check: one full week on the
  live profile, the window fixed in advance, pass lines fixed
  before it starts: a check-in never exceeds the item cap
  (5 jobs / 3 decisions / 1 question); a quiet day produces
  exactly the one-line quiet form; **at least one no-application
  session recorded during the week (E1 session typing — brief
  §9's return target, evaluated here)**; the proof-closing rate
  shown for the week matches the owner's own count of gaps
  closed, and the interviews-per-application figure displays
  with its sample size; the send log for the week shows zero
  sends the owner did not initiate in the moment. Any line failed = reject.
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
- **This CUT list governs in any conflict.** No initiative,
  feature spec, consent model, or prior ruling in this package
  waives it: standing or per-event consent captured in advance is
  not a human hand initiating a send at the moment it happens,
  and any text that reads otherwise is read subject to this list
  until the project owner changes the list itself, in writing.
  Initiative 5.3 was re-scoped to comply; no other initiative in
  this roadmap describes, schedules, or assumes a scheduled or
  standing-consent send.
- **PAUSE — fit-weight personalisation expansion:** the model-card
  machinery stays gated and human-approved as shipped, and no
  expansion is scheduled. The pause is lifted only by a written
  owner decision taken after 5.11's first **full** outcome-validation
  report (the quarterly report — not the preliminary report four
  weeks after 2.8; see 5.11) — that is the operable condition. (The earlier wording,
  "until Slot 0-B clears," could never bite: Phase 2's entry
  already requires Slot 0-B closed, three phases before 5.6 —
  audit F5-13.) 5.6 feeding the calibration evidence count does
  not lift, weaken, or schedule around this pause.
- **PAUSE — new board providers / search expansion:** search exists
  and is secondary by strategy; no new provider work is scheduled.
  Revisit only if feed-me intake (5.4) data says users cannot get
  postings in. The retained existing surface is reviewed under
  Phase 0's Row X slice (see Standing row X), not expanded.
- **PAUSE — i07 warm-path promotion:** E3/5.5 uses the wired network
  machinery only. Promoting `initiatives/i07/warm_path.py` is its
  own future initiative, costed with registration, wiring, and
  tests — never smuggled in as a display change.

## Phase summary

Counts in this table were recounted after the rework splits,
including the round-2 splits and additions (1.6 split into
1.6a / 1.6b; 0.9 added).
**The programme total is 52 initiatives: 5 owed pre-work items in
Slot 0, and 47 differentiator initiatives in Phases 0–5** (audit
F5-14 — the old headline "32" silently included Slot 0's owed
work; the differentiator proper was 29 of those 32). Standing
row X is counted separately as 7 slices (Slot 0 + Phases 0–5)
and is not in the 52. Planning units total 187, recounted in the
sizing table (118 initiative + 52 gate + 17 Row X).

| Slot/Phase | Initiatives | One-line outcome |
|---|---|---|
| Slot 0 | 5 (0-A, 0-B, 0-C1, 0-C2, 0-D) | Owed annual work closed for 01, 02, and 03 — including 03's UAT, run after its RESHAPE — before building on it |
| 0 | 11 (0.1, 0.2a–c, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9) | Claims match code; known code defects repaired; ledger in core, safely, with privacy mechanisms built; retained surfaces dispositioned and brought into conformance |
| 1 | 8 (1.1, 1.2a–b, 1.3, 1.4, 1.5, 1.6a–b) | Profile compounds with approval; proof state from intake; intake budget measured (1.6a), first-delta measure built and gate pending on Phase 2 (1.6b) |
| 2 | 9 (2.1–2.9) | Delta classified and reported; demo live on the shipped refusal; veto classified, bias-measured, override-instrumented, 14-day veto-moment return measured; 1.6b's gate closed |
| 3 | 4 (3.1–3.4) | Tailoring grill-fed and honesty-gated, serially, on repaired save and provenance paths |
| 4 | 4 (4.1–4.4) | Prep from the delta, graded vs evidence |
| 5 | 11 (5.1–5.11) | Daily loop (prepare-only, user-initiated) + split trending measures + outcome validation (preliminary report four weeks after 2.8, full reports quarterly) |

52 initiatives (5 owed + 47 differentiator), plus standing row X
counted as 7 slices. Phases are dependency-ordered; parallelism
is claimed only where the phase text shows different files and
satisfied dependencies.
