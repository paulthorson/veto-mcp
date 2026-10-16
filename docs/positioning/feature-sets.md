# Veto feature sets — the differentiator, specified

Companion to `positioning-brief.md` (§6 claims register) and
`roadmap.md`. Each feature names what exists today (module:function,
from the code audit) and what is new. "Reuses" is a hard constraint:
extend the named code, do not build a parallel version.

Conventions: **user seat** = what the user sees and does, end to end.
Acceptance criteria are testable statements; the roadmap attaches E2E
and UAT scripts to each.

**Scope and count.** This document specifies **23 features**: A1–A5,
B1–B6, C1–C4, D1–D4, E1–E4. Where a "what exists today" statement
differs between the two code trees, the text says which tree it
describes: the tree these documents ship in
(`wt-veto-differentiator`) or the live tree (`job-apply-mcp`). A
capability that exists only in unwired initiative code, or only in
the other tree, is never described here as shipped in the build
tree.

---

## A. Evidence-ledger profile

### A1. Evidence ledger core (promote the built model)

- **What it does.** Promotes the unwired i04/i05 evidence model into
  the core profile. Every claim in the profile (skill, bullet,
  achievement) becomes a ledger entry: the claim text, its proof
  (verbatim story/metric/link), a source, a **proof state**, and
  two timestamps every entry carries from creation:
  `captured_at` (when the claim entered the ledger) and
  `proof_verified_at` (when its proof was last attached and
  approved through A3, or last re-verified under the staleness
  policy below; null while the entry is `unverified`). Consumers
  read proof age from these fields; no consumer may treat an
  entry's age as unknown or as zero.
  Tailoring, delta, and prep all read from the ledger, not from flat
  profile fields.
- **The one state set (defined here; every other feature cites it).**
  One vocabulary spans two stores. A claim starts in the **proposal
  queue** as `draft` — written by a producer (grill answers — per-job and profile (A2), C1's tailoring sessions, D3's debriefs — the producers A3 names; A5 is the exception: intake claims enter the ledger directly as `unverified`, never via the queue); a draft is
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
  One further state exists only as history: `superseded` — an
  entry replaced by a newer approved entry under A3's supersession
  rule. A superseded entry is never read as current by any
  consumer; it stays visible in the entry's history view. There is
  no other state vocabulary for entries. (B2's
  supported / evidence-gap / skill-gap / contested are *delta
  classifications of requirements*, a different machine that reads
  these states — not entry states.) Entry sources are enumerated
  here too: `wizard`, `manual`, `grill:<job_id>`, `grill:profile`,
  `mock:<session_id>`, `tailor:<job_id>` (owned by C1: a fact first
  stated by the user inside a tailoring session, proposed through
  A3 — see C1). Outcome updates are **not** a ledger source: an
  outcome is a fact about a job, not a claim about the user, and
  no outcome update — single or bulk — ever proposes a ledger
  entry.
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
- **Staleness policy (proof ages; this is the rule B2, B5 and D2
  consume).** Proof age is measured from `proof_verified_at`.
  - **Fresh (under 24 months):** no label, no action.
  - **Ageing (24–36 months):** the entry shows its proof age
    ("proof verified 26 months ago") in the profile view; A2 may
    offer one re-verification question for it, suppressed for
    90 days after the user answers or defers (the A2
    asked-and-unknown suppression pattern).
  - **Stale (over 36 months, not re-verified):** the entry keeps
    state `approved` in the ledger — history is not rewritten —
    but B2 may classify a requirement it backs at best as an
    *evidence gap* with the stated reason "proof stale —
    re-verify"; it may not classify as *supported*. D4 may not
    cite a stale entry as a STAR story, and B5 counts a
    proof-closing only if the proof is present and not stale at
    the window's end.
  - **Re-verification** is an A3 review: the user confirms the
    proof is still accurate, corrects it, or attaches new proof.
    Confirmation or new approved proof sets `proof_verified_at`
    to the review date; correction follows the supersession rule
    in A3. Nothing re-verifies silently or by the passage of a
    session.
- **Confidentiality (mechanisms, not a documentation promise —
  brief §7 item 1 names disclosure, not just loss).** The ledger
  store and every backup of it are created with owner-only file
  permissions (`0700` for the containing directory, `0600` for
  the files on POSIX systems; the equivalent owner-only ACL on
  Windows). At startup the product checks the store's permissions
  and warns in the profile view if they are wider than owner-only,
  with the one command or setting that tightens them. Backups
  live in the same protected directory as the ledger (never a
  second, less-protected location), carry the same permissions,
  and follow the retention rule in the data-lifecycle table
  (cross-cutting section): for ongoing backups, the product keeps
  the most recent 5 backups and deletes any ongoing backup older
  than 90 days, whichever limit is reached first; the
  pre-migration backup follows its own hard-limit rule in that
  table (D-13: a limit, not a repeating offer). **That limit's
  consequence, stated honestly (D2-07):** the pre-migration
  backup is the sole restore copy, and it **is deleted on
  schedule at its limit whether or not a restore was ever
  needed** — the limit is not paused by disuse, and it is
  not paused or defeated by declining a notice either:
  **the scheduled deletion at the limit is not a
  confirmation-gated act.** This paragraph and the lifecycle
  table's pre-migration row state **one** rule, and it is
  this one: notice is given **before** the deadline through
  the Phase-0-operable mechanism the lifecycle table's
  pre-migration row specifies (local surfaces that exist from
  Phase 0 — the profile view, the CLI, and the dashboard), the
  first local run on or after the limit deletes the backup
  and states that deletion plainly in that same run, and the
  deletion is noted in the local work log. A confirmation act
  governs the user's own **early** deletion of the backup and
  its disposition at encryption enablement — voluntary acts
  before the limit — and no confirmation, decline, or absence
  of a run extends the backup past its limit: a backup whose
  limit has passed is deleted by the next run whenever it
  happens, and the run's statement of that fact is a notice,
  not an offer the user can refuse to keep the copy. Notice
  is never given through the prepared check-in,
  which does not exist until Phase 5 and is not a mechanism
  any Phase 0–4 deletion may rely on.
  **Store-class rule (D-06 — confidentiality follows the content,
  not the one file).** Every store that holds ledger-derived
  content inherits the ledger's permission posture: it lives in
  the ledger's protected directory or in its own directory created
  `0700` with files `0600` (owner-only ACL equivalent on Windows),
  and the startup permission check covers every store in the
  table below, warning in the profile view for any store found
  wider than owner-only. No store holding ledger-derived content
  is silent in this table.

  | Store | Ledger-derived content it holds | In 0.8's encrypted scope (below)? |
  |---|---|---|
  | Evidence ledger + all its backups (incl. the pre-migration backup, once migrated) | The claims and proofs themselves | Yes |
  | Proposal queue + proposal log (A3) | Draft claims and proof payloads awaiting or past review | Yes — held in the same encrypted store bundle, under the same key |
  | Per-job delta store (B3/B5) | Classifications citing ledger entries, with the deciding entry named | Yes — same bundle, same key |
  | Verdict record (B4) | Verdict reasons citing entries and proofs | Yes — same bundle, same key |
  | Grill session records (A2/C1) | Answers restating quantified wins and proofs | No — permission posture only. Reason, stated plainly: session records are working files the grill reads and resumes across sittings, and 0.8's first scope is the record stores above. Residual risk is disclosed, not hidden: these files are owner-only, never transmitted, and governed by the lifecycle table's delete row |
  | Mock / debrief history (D2/D3) | Transcripts and debriefs restating proofs | No — permission posture only, for the same reason and with the same disclosure as grill sessions |
  | Tailored artefacts + approved variants (C2) | Approved proofs rendered as resume / letter text | No — permission posture only. Reason: an artefact exists to be read and handed off by the user in other tools; encrypting it in the product's format would defeat its use. An artefact contains only claims approved for that artefact (C3), and its delete row applies |
  | Export files created by the user (A1/B4 exports) | Whatever the export includes (Tier 2 excluded by default — see the tiering section) | No — the export is the user's own portable copy, created as a file they choose. Mitigations, all specified: the file is created `0600` where the filesystem allows, it carries the protection note specified in the export section below, and the product never transmits it |
  | Offers store (`offers.json` + `offer_weights.json`) (D2-06) | User-supplied compensation figures (base, bonus, equity) and the user's offer weights — Tier 2-class content by this feature's own tiering (compensation), held outside the ledger | Yes — the same posture as the ledger: this row joins the encrypted bundle under the same key, and roadmap 0.8's scope and the lifecycle table's offers row are conformed to it (CROSS-DOC: 0.8's scope grows by this row) |
  | Preferences store (`preferences.json`) (D2-06) | The user's salary floor and related preference values — the salary floor is a Tier 2 compensation fact held outside the ledger | Yes — the same posture as the ledger, for the same reason as the offers row: Tier 2 content does not lose the ledger's posture by living in a second file (CROSS-DOC: 0.8's scope grows by this row) |
  | Filled-form screenshots (`screenshots/`) (D2-06) | Images of filled application forms holding the user's name, email, phone, and address as entered on third-party forms | No — permission posture only, with the same disclosure pattern as grill sessions: these are transient working images the browser-apply flow reads during a run, they are owner-only, never transmitted by the product, and the lifecycle table's screenshots row gives them a hard retention limit and a user delete act that does not depend on ever running browser-apply again |
  | Approval-preview temp files (`veto-approval-preview-*.txt` in the OS temp directory) | The full body of an over-length approval draft for the product's one wired third-party send — send-bound draft content that may restate claims and contact details | No — permission posture only, and the exception is named: these files live in the OS temp directory, outside the protected store directory, because the approval flow's preview mechanism (`email_sync.py: _save_approval_preview()`, created `0600` via `mkstemp`) writes them there. Mitigations, all specified: `0600` creation, the lifecycle table's approval-preview row (10-newest and 7-day hard limit, pruning at startup and at each save, a named user delete path on the approval surface, and the path stated at save time), and no transmission by the product |
  | Flat profile store (`profiles/*.json`, incl. `profile.json`) | The migration's source claim text — experience bullets, achievements, skills — in plaintext. It is **not** a copy of the ledger: it holds no proof payloads, no proof states, and no ledger timestamps, and no claim entered directly into the ledger after migration appears in it | No — outside the encrypted bundle (roadmap 0.8 lists it outside its scope by name). Its retention is disclosed in this table and in its lifecycle row, **and at encryption enablement**: the enablement act names this store and states that pre-migration claim text remains in it in plaintext — see the encryption section below, where that disclosure is a step of enablement, not a footnote |

  **What this feature does not ship:** built-in at-rest
  encryption. Encryption at rest is scheduled roadmap work —
  roadmap initiative 0.8 — and is not a present mechanism of
  this feature. Until initiative 0.8 ships, at-rest encryption
  is the user's own device/volume encryption, the onboarding
  docs say exactly that, and no product copy may claim the
  ledger is encrypted by the product. What this feature *does*
  do is specify the 0.8 mechanism in full, immediately below,
  so 0.8 implements a specification rather than inventing one.
- **Encryption, specified (D-07 — the mechanism 0.8 must ship;
  this section is the specification 0.8 points at).**
  - **Algorithm:** AES-256-GCM, applied per store file, with a
    fresh random 96-bit nonce per file write. A file either
    decrypts whole and authenticates, or fails whole — there is
    no partial plaintext on a failed attempt.
  - **Key derivation:** the user's passphrase, through Argon2id
    with a 16-byte random salt stored in the (plaintext) store
    header, memory cost 64 MiB, 3 iterations, parallelism 2,
    producing the 32-byte file key. There is no second key path:
    no key file beside the data, no product-held recovery key.
  - **Key custody:** the product never stores the passphrase.
    The derived key is held in process memory for the session
    only, and is cleared when the product locks or exits. An
    OS-keychain copy is **not** kept — that is the decided
    posture, stated so no builder adds one silently.
  - **Loss consequence, stated honestly wherever encryption is
    offered:** a lost passphrase means the encrypted store is
    unrecoverable. The product says exactly that, in plain
    words, before the user enables encryption, and offers no
    recovery flow, because none exists.
  - **Backups and the pre-migration plaintext copy:** ongoing
    backups are encrypted under the same key. Enabling
    encryption lists every existing plaintext copy of the
    ledger (including the pre-migration backup) and requires
    the user to disposition each one — encrypt it under the
    same key, or delete it — before enablement completes; no
    plaintext copy of an encrypted store may remain beside it.
  - **The flat profile store, named at enablement (it is not a
    copy of the ledger, and this rule does not pretend it is):**
    the enablement list above also names the flat profile store
    (`profiles/*.json`) **by name**, in its own line, and the
    enablement act states in plain words, before the user
    confirms, that this store is the migration's retained
    source — it holds the user's pre-migration claim text
    (bullets, achievements, skills) in plaintext, it is
    **not** encrypted by enabling ledger encryption, and it
    stays until the user deletes that profile under its own
    lifecycle row. Enablement cannot complete until that line
    has been shown and the user has recorded a choice for the
    flat store — keep it (the choice the existing consumers
    require), or delete the profile as its own act. Keeping it
    is an allowed, recorded choice; **skipping the disclosure
    is not an available path.** No product copy about
    encryption may claim a wider scope than the bundle this
    section defines, and the enablement surface is where that
    limit is told to the user, not only in a table elsewhere
    in this package.
  - **Exports are not encrypted by 0.8** (see the store-class
    table): the export's own protections are its Tier 2 default
    exclusion, its `0600` creation, and its protection note.
- **Sensitive-field tiering (the content-level limit every
  outbound surface obeys — channel messages *and* exports,
  D-05).** The ledger may hold compensation floors, clearance
  status, sponsorship needs, and work authorisation facts.
  Those four field classes — plus any field the user marks
  private in the profile editor — are **Tier 2**: they are never
  quoted, paraphrased with their values, or named with their
  values in any message sent over Gmail, WhatsApp, or any other
  channel or endpoint outside the local product surfaces.
  Question generation (A2, E1) must abstract them ("your
  work-authorisation answer on file") or omit the topic; the
  local profile, delta, and prep surfaces may show them because
  they do not leave the machine. Acceptance criteria for the
  channel side of this rule sit in A2 and E1, where the messages
  are built.
  **Exports obey the same tiering, by this mechanism:** the
  exporter carries a field-level exclusion list — the four
  Tier 2 field classes plus every user-marked-private field —
  and applies it to every export the product produces (the
  ledger export below, the delta export, and B4's verdict-record
  export alike; a classification or reason that rests on a
  Tier 2 fact is exported with the Tier 2 value removed and the
  removal marked). By default an export therefore contains no
  Tier 2 field, value, or proof text at all: a Tier 2 entry is
  represented only by a count line ("Tier 2 fields omitted: N"),
  never by its name paired with a value. Including Tier 2 is an
  explicit user act, never a default: the export action offers
  an unchecked-by-default "include sensitive (Tier 2) fields"
  choice, choosing it shows a confirmation naming what will be
  included, and only that confirmation includes them. Every
  export file, either way, carries a protection note as its
  header (readable text) or top-level metadata (JSON): what the
  file contains, that it is a plaintext copy outside the
  product's protected store, and the recommendation to keep it
  owner-only or encrypted by the user's own tools. The export
  file is created with `0600` permissions where the filesystem
  allows.
- **Ledger export (the ledger gets the mechanism B4's record
  already had).** One action in the profile view exports the
  ledger: JSON (machine-readable, schema version stamped) and
  readable text, covering every current entry, its state,
  source, timestamps, and proof text, plus superseded entries
  marked as such — **subject to the Tier 2 exclusion above**:
  by default Tier 2 entries contribute only the omitted-count
  line, and the completeness test in the acceptance criteria
  runs with Tier 2 inclusion explicitly chosen. Export is a
  local file the user saves where they choose; nothing is
  transmitted. Ledger **delete** is specified in the
  data-lifecycle table: deleting the ledger deletes the
  profile's claims with it (the user is told this in the
  confirmation, in plain words — including what happens to
  derivatives, per the deletion-disclosure rule in the
  lifecycle section) and cascades per that table.
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
  deletes (entry reverts to unverified; the deletion cascades, and
  the cascade is described to the user honestly, per D-09:
  dependent tailored variants are marked *stale* in C2's terms
  ("stale — built from older proof"), every persisted delta that
  cited the entry is marked stale under B3's invalidation rule —
  **marked stale only; nothing is recomputed until the user
  invokes B3's recompute action** (C-14) — verdict reasons in
  B4's record that cited it are annotated "proof withdrawn" —
  the verdict itself stays, its stated basis is corrected — D4
  briefs citing the entry are marked stale, and B5's proof-closing
  counts are recalculated from the stores (they are derived
  aggregates, not stored deltas presented as fresh). Marking is
  not deletion: the proof's text can still sit inside those
  flagged derivatives. The delete confirmation therefore lists
  the derivatives that will remain, by store and count, and
  offers the act specified in the lifecycle section —
  **delete the source and the listed derivatives together**,
  which purges the variants, the citing delta-history entries
  and briefs, and replaces citing verdict-reason text with
  "proof withdrawn — reason text deleted" — or source-only
  deletion, after which the retained derivatives stay listed in
  a "retained derivatives" view where each can be deleted
  later. Anything already exported or handed off outside the
  product cannot be recalled, and the delete confirmation says
  so in plain words, in the same breath as the retained-
  derivatives disclosure, before the user confirms); corrupt ledger file (fail closed
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
  - Export produces a file containing every ledger entry (current
    and superseded) with state, source, both timestamps, and proof
    text; a test diffs the export against the fixture ledger and
    finds no entry or field missing. (This completeness test runs
    with Tier 2 inclusion explicitly chosen, per the export
    section.)
  - Tier 2 export default (D-05): on a fixture ledger holding
    compensation, clearance, sponsorship, and work-authorisation
    values plus one user-marked-private field, the default export
    contains **zero Tier 2 content** — no Tier 2 value, no Tier 2
    proof text, and no field name paired with its value — only
    the omitted-count line, asserted by searching the export file
    for each seeded value. Choosing inclusion without the
    confirmation step produces the default export, not an
    inclusive one.
  - Encryption (D-07, acceptance for the 0.8 mechanism specified
    above): with encryption enabled on the fixture store, a raw
    read of the store file finds ciphertext only — a search for
    every seeded claim and proof string finds none; an attempt
    to open it with a wrong passphrase fails whole, with an
    authentication error and no partial plaintext; opening with
    the correct passphrase reproduces the fixture ledger exactly;
    and enabling encryption on a fixture that has a plaintext
    pre-migration backup cannot complete until that backup is
    encrypted under the same key or deleted. On a fixture that
    also has a flat profile store, enablement likewise cannot
    complete until the flat-store line has been shown by name
    and a keep-or-delete choice for it recorded; a build whose
    enablement flow never mentions the flat store fails this
    criterion even if every bundle file reads as ciphertext.
  - The ledger store and its backup are created owner-only; a
    fixture store with widened permissions produces the startup
    warning in the profile view.
  - Staleness: with the fixture clock set 25 months past
    `proof_verified_at`, the entry renders with its proof age and
    A2 offers re-verification once; at 37 months, B2's fixture
    classification for its requirement is evidence gap with the
    reason "proof stale — re-verify", never supported; after an
    A3 re-verification approval, the same fixture classifies as
    before and `proof_verified_at` equals the review date.
    **Deferral (C2-11): the B2-dependent assertion in this bullet
    is deferred to Phase 2 — this feature is built, gate pending
    for that assertion until it passes in Phase 2 and is
    recorded against it; no earlier gate counts it passed or
    passes by omitting it.**
  - Deleting a proof marks every citing delta stale, annotates
    every citing verdict reason "proof withdrawn", and marks every
    citing D4 brief stale — each asserted against the stores
    directly, not only against the surfaces. **Deferral (C2-11):
    the D4-dependent assertion in this bullet (citing D4 briefs
    marked stale) is deferred to Phase 4 — this feature is
    built, gate pending for that assertion until it passes in
    Phase 4 and is recorded against it; no earlier gate counts
    it passed or passes by omitting it.**

### A2. Conversational evidence extraction (the standing grill)

- **What it does.** Turns the per-application grill into a standing
  profile practice. A dedicated session type — *evidence grill* — asks
  about unverified claims and thin areas of the ledger (unquantified
  wins first), a few questions at a time, over the user's chosen
  channel. Answers become draft proposals in the queue (A3); the user approves them there.
- **User seat.** The user picks "deepen my profile" (or opens a
  prepared companion prompt, E1) and gets ~5 short questions:
  "You list
  'cut deploy time' at Acme — by how much, and how was it measured?"
  They answer in the session they are in — in-product chat, or a
  Gmail/WhatsApp thread **they** start or are actively replying in.
  **Initiation, the one definition (D-11 — stated once in E1's
  consent model, cited here, never restated in a weaker form):**
  initiation is the user's act that causes *this* batch's
  content to go out — tapping send for that batch, or issuing
  the in-session send command for it. Merely opening a session
  or a prepared item is an act of inspection, not initiation:
  it displays the batch on the local surface and sends nothing
  over any channel. Questions are assembled locally in advance
  and are sent over a channel only on that send act, at the
  moment the user performs it (E1's consent model states the
  full rule; there is no scheduled or standing-consent send of
  grill questions). A summary shows the new
  draft entries; one approval writes them to the ledger.
- **Inputs/outputs.** In: ledger entries in state `unverified`,
  `approved` entries whose proof lacks a number, and `approved`
  entries whose proof is ageing or stale under A1's staleness
  policy (re-verification questions); the user's answers.
  Out: draft proposals for the queue; on approval, ledger entries with source
  `grill:profile`.
- **Reuses.** `grill.py: generate_questions()` quantify logic
  (`_evidence_is_quantified()`), channel machinery (`get_grill_prefs()`,
  `outbound_for_channel()`, `ingest_reply()` / `parse_reply_body()`),
  session store pattern from `grill_sessions.json`. New: a
  profile-scoped session type distinct from per-job sessions, and the
  write-back path that does not exist today (audit claim risk 1).
  **Supersession of the reused function's outbound notes
  (D2-01 — a condition of reuse, not an editorial note).**
  `grill.py`'s outbound deliverables carry runtime notes that
  instruct the sending agent to (a) treat one explicit go-ahead
  on the exact text as **standing approval covering later grill
  emails**, and (b) reach the user proactively through a
  **scheduled task** created inside a side chat. **Both notes
  are superseded by this package's initiation model** (E1's
  consent model and the D-11 definition of initiation cited
  above): consent captured in advance is not initiation, and
  no scheduled send exists in this package. Reuse of
  `outbound_for_channel()` and the channel machinery is
  **conditional on those notes being rewritten** to the
  prepare-only / user-initiated model — a batch is prepared
  locally and sent only on the user's send act for that batch
  — before any surface built on this machinery ships. A build
  that carries either old note forward, in code, in a
  deliverable template, or in agent-facing instructions,
  fails this feature's acceptance, however the rest of the
  feature behaves. **The inventory expressly includes the
  module docstring.** `grill.py`'s module docstring (lines
  14–21 in both code trees) is agent-facing text in the very
  module this feature reuses, and it states the same
  scheduled-task routing as old note (b) — that a channel
  message can only be sent from that channel's own side chat
  and that proactive reach from the main chat requires a
  scheduled task created inside the WhatsApp side chat. The
  docstring is **inside** this supersession, not beside it:
  it is rewritten to the prepare-only / user-initiated model
  in the same act as the deliverable notes, and a build that
  rewrites the notes and leaves the docstring standing fails
  this feature's acceptance under the "in code, or in
  agent-facing instructions" sentence above.
  **Roadmap home (CROSS-DOC, roadmap round
  3): task 0-C4, inside 0-C2**, inventories and rewrites every
  `grill.py` `outbound_for_channel()` note **and the module
  docstring at `grill.py:14–21`** (both trees, where the same
  text stands) to the
  prepare-only / user-initiated model, with a
  zero-standing-approval test, and Slot 0 is gated on it; the
  brief carries the claims-debt items for these notes. This
  paragraph is the feature-spec half of that fix.
- **Edge cases.** User answers "I don't remember the number" (entry
  stays unverified; the answer is recorded as asked-and-unknown so it is
  not re-asked for 90 days); user contradicts an existing claim
  (surface the conflict, never overwrite silently — the answer
  becomes an A3 proposal, and only an A3 approval supersedes the
  existing entry, under A3's one supersession rule); a question
  whose topic touches a Tier 2 field (A1) is abstracted so no
  Tier 2 value or field-with-value leaves the local surfaces;
  channel `off`
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
  - Channel `off`: starting an evidence grill explains that a
    channel or an in-product session is needed, sends nothing, and
    creates no nag or retry entry.
  - Abandoned session: drafts persist in the queue, the session
    resumes where it stopped, and the ledger is byte-identical to
    before the session.
  - No-send rule: with a grill batch prepared and every event
    opt-in on, zero messages leave the machine until the user
    performs the send act for that batch — opening a session or
    a prepared item alone sends nothing, asserted as its own
    case under outbound-call mocks; the send that follows the
    send act is exactly that batch, once.
  - Supersession (D2-01): the outbound deliverable text for
    every grill channel, as built on the reused machinery,
    contains no standing-approval instruction and no
    scheduled-send or proactive-task instruction — asserted by
    text search over the deliverables the sender receives, on
    both the email and the messaging-channel paths. **The same
    search also runs over `grill.py` itself** — its module
    docstring (lines 14–21), its comments, and every
    agent-facing string in the module — and over deliverable
    templates: no carrier in that wider set may contain a
    standing-approval, scheduled-send, or proactive-task
    instruction either. A search that covers only the
    deliverables does not pass this criterion.
  - Tier 2 rule: on a fixture ledger holding compensation,
    clearance, sponsorship, and work-authorisation values, the
    generated question payload for every channel contains none of
    those values and no field name paired with its value.

### A3. Write-back from everywhere (profile compounding)

- **What it does.** One write-back contract: any surface that produces
  a user-approved fact about the user — grill answers (per-job and profile, A2), mock
  interview debriefs (D3), tailoring sessions (C1) — can
  propose a ledger entry. (Outcome updates never propose entries:
  outcomes are facts about jobs, not claims about the user — A1's
  source list is the authority.) Proposals queue for approval in one place
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
- **Supersession rule (the one rule; A2, C1 and D2 cite it, none
  restates a variant).** An approved ledger entry is the current
  record until a new proposal that **explicitly names the entry it
  replaces** is approved in A3. At that approval, in one step: the
  new entry becomes current (state `unverified`, or `approved`
  when proof was attached and approved in the same review), and
  the named old entry moves to `superseded` and is thereafter
  read by no consumer as current. No producer outranks another:
  grill, debrief, tailoring, and manual proposals are equal, and
  the **last approved** proposal wins — an unapproved proposal
  never supersedes anything. An edit made **inside** the approval
  review is approved by that review itself, so the entry enters in
  its reviewed state directly; A5's return-to-unverified rule
  governs edits made outside a review. A contradiction flagged by
  D2 in a mock session follows this same path: it becomes a
  proposal naming the contradicted entry, never a silent flag with
  no outcome.
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
  - Supersession: approving a proposal that names a current entry
    leaves exactly one current entry for that claim, the named
    entry in state `superseded`, and every consumer (tailoring,
    delta, depth) reading the new entry; approving a proposal that
    names no entry changes no existing entry's state.
    **Deferral (C2-11): the delta-consumer part of this assertion
    is deferred to Phase 2, where the delta consumer exists —
    this feature is built, gate pending for that part until it
    passes in Phase 2 and is recorded against it; no earlier
    gate counts it passed or passes by omitting it.**

### A4. Profile depth meter

- **What it does.** A single 0–100 depth score for the ledger, with
  the weighting formula pinned here (not left to the builder):
  **depth = 40 × (proven share of claims matching the user's target
  roles) + 30 × (share of experience roles carrying ≥1 quantified,
  proven win) + 30 × (share of all claims proven)**. A claim counts
  as proven only in state `approved` **with** proof attached —
  unverified intake claims (A5) never count.
  **The matching predicate (the 40-point term, defined
  operationally).** Each ledger entry carries the role it was
  worked in and a set of skill tags (from the entry's claim text,
  normalised through B2's alias table). An entry **matches** the
  user's target roles when either test passes: (a) the entry's
  worked-in role title has the same family key as one of the
  user's `target_titles` under the frozen role-family
  definition in this feature (the "Role family" section below —
  normalisation, family key, and cluster formation are stated
  there, in full, once), or (b) at least one of the entry's
  skill tags appears in that cluster's skill set, derived
  without circularity as that section specifies (family
  assigned by the title rule first; the skill set built from
  already-assigned postings second). Matching is binary
  per entry — an entry counts once however many tests or skills
  hit; there is no partial credit inside the term. The first term
  is then: (entries that match **and** are proven) ÷ (entries
  that match). *Worked example:* 10 entries, 6 match a target
  family, 3 of those 6 are proven → first term = 40 × 3/6 = 20.
  **"Proven", one reading only (C-05):** proven means exactly
  A1's state — `approved` **with proof attached** — in every
  term of this formula. Quantification is the *second term's
  own additional qualifier*, not a condition on proven anywhere
  else. A "gain" that flips a claim to proven therefore means
  flipping it to `approved` with proof attached. Where that
  proof is quantified, the flip can move all three terms;
  where the proof is not quantified, the flip moves the first
  and third terms only — it does not move the second term,
  whose wins must be quantified — and the gain list must
  compute and predict each term separately, never predicting a
  second-term movement for a non-quantified proof. (Worked
  check, frozen as a fixture in the acceptance criteria: 10
  claims, all matching, exactly one `approved` with a
  non-quantified proof, the rest unverified → that entry
  contributes 40 × 1/10 + 30 × 1/10 = 7 points, term 2 = 0.)
  **Empty denominators (cold start, owned here with A5).** When
  the denominator of any term is zero — no matching entries, no
  experience roles, or no claims at all — that term contributes
  0, the breakdown shows it as "no data yet" rather than a
  percentage, and the meter shows the getting-started path. An
  empty `target_titles` list therefore yields first term 0 —
  the meter is capped at 60 in that case, because the second
  and third terms still score as defined — with the note "no
  target roles set — the 40-point target term scores 0 until
  you set target roles", never an error and never a silent 100. Plus coverage checks
  (every role has ≥1 quantified win; every target skill has proof or
  an open gap entry). Shown wherever the profile is shown (the
  surfaces are owned by the roadmap's cross-cutting row), with the
  top 3 "cheapest depth gains" (unverified claims one answer away from
  proven), each gain's point value computed by re-running the formula
  with that claim proven.
- **Role family — the frozen definition (C-04; frozen here, in
  this feature, before roadmap initiative 1.3 starts).** This is
  the one definition of **target role family** for this package;
  B2 and B5 cite this section and neither authors nor amends a
  variant. Initiatives 1.3 and 2.1 *implement* it; neither
  authors it. A change to this definition is a revision of this
  section, made before any consumer's gate is measured against
  the changed text.
  - *Normalisation.* A title is normalised by these steps, in
    this order: (1) lowercasing; (2) expanding the
    abbreviations in the alias table's title section (e.g.
    "swe" → "software engineer"); (3) splitting the title into
    tokens on whitespace **and on hyphens**, so "Full-Time"
    yields the two tokens `full`, `time` before any deletion
    runs; (4) deleting every token — or, for a hyphenated list
    entry, every token sequence — on the seniority/level list
    (`entry`, `junior`, `jr`, `senior`, `sr`, `staff`,
    `principal`, `lead`, `head`) and on the arrangement list
    (`remote`, `hybrid`, `onsite`, `contract`, and the
    two-token sequences `full` + `time` and `part` + `time`,
    which are the list entries `full-time` and `part-time`
    under this tokenisation); (5) removing any remaining
    punctuation from the surviving tokens, dropping empty
    tokens, and collapsing whitespace. Because the list
    entries are matched at step (4), under the same splitting
    that produced the title's tokens, `full-time` / `part-time`
    are deletable exactly as written in a title (hyphenated or
    written as two words) — no implementation
    needs a special case, and none may add one that changes
    another title's key. Both lists are
    versioned data files beside the alias table, changed only
    by reviewed change.
  - *Family key and clusters.* A title's **family key** is the
    sorted set of its remaining normalised tokens (so "Staff
    Backend Engineer" and "Backend Engineer" share the key
    {backend, engineer}; "Platform Engineer" is a different
    key, {engineer, platform}). Each distinct family key among
    the user's `target_titles` is one **cluster**; target titles
    that normalise to the same key are the same cluster, never
    two. A posting or a worked-in role belongs to a cluster
    when its family key **equals** the cluster's key — exact
    key equality is the whole match rule for family assignment;
    there is no similarity threshold and no partial match.
  - *Cluster skill set, without circularity.* A posting is
    assigned to a cluster by the title rule alone, first. A
    cluster's skill set is then the union of the skills named
    in the target title itself and the skills B1 extracts from
    postings already assigned to that cluster by the title
    rule. No posting enters a cluster's skill set by way of the
    skill set itself. **The postings already assigned are an
    input to this feature, not a detail of this paragraph:**
    the *evaluated-posting history* — every posting the user
    has had B1 extract, with its title-rule cluster assignment
    and its extracted skill list — is the feature's third
    stated input (Inputs/outputs below), and the depth score
    is a function of ledger + targets + that history, never of
    ledger + targets alone.
  - *No targets, no family.* With an empty `target_titles`
    list there are no clusters; B5 files such postings under
    "unassigned" (A5's rule) and no family trend is drawn.
  - *Reconciliation with `calibration.py: role_family()`.*
    That function already assigns every role to one of five
    keyword buckets (engineering, design, data, product,
    other). It is **not** this definition, and the two must not
    be conflated: `role_family()`'s output — called the
    **calibration family** wherever this package needs to name
    it — governs calibration slices and E4's evidence gate
    only, and continues unchanged there. The target role family
    defined here governs this feature's matching predicate and
    depth views, B2's family references, and B5's trends. No
    surface, trend, or score may mix the two taxonomies in one
    figure, and code that needs the target family implements
    this definition rather than calling `role_family()`.
- **User seat.** "Profile depth 62. Cheapest gains: quantify the
  platform win at Acme (+6), add proof for Kubernetes (+5), one story
  for the 2023 role (+4)." Each gain links into an evidence grill (A2)
  pre-loaded with that claim.
- **Inputs/outputs.** In: (1) the ledger; (2) `target_titles` from
  the profile (collected and validated at intake by A5, which
  owns them; this feature only reads them); and (3) the
  **history of evaluated postings** — every posting B1 has
  extracted for this user, with the cluster the title rule
  assigned it to and the skills B1 extracted from it (the
  cluster skill sets in the role-family definition are built
  from this history and from nothing else).
  Out: score, per-area breakdown, ranked gain list.
- **Reuses.** Nothing equivalent exists (audit §1: ABSENT in core);
  nearest neighbour is `linkedin_optimizer.py: audit_profile()`
  sub-score pattern (presentation only). New computation over the A1
  ledger.
- **Edge cases.** Empty ledger (depth 0 with a getting-started path,
  not an error); target titles changed (score recomputed, change
  explained: "depth for data roles 48, for platform roles 62" —
  per-family views use this feature's frozen role-family
  definition, never a local variant. Sequencing: the definition
  is frozen in this section **before roadmap initiative 1.3
  starts** (1.3's start gate); 1.3 implements the definition,
  its token lists, and the initial alias-table version the
  matching predicate needs, and B2's initiative (2.1) implements
  the same frozen definition for classification — neither
  initiative authors or amends it. Before the 1.3
  implementation lands, the meter reports the overall score
  only and marks this feature built, gate pending, rather than
  reporting a per-family figure produced by an interim
  predicate);
  a
  claim proven for one role family and irrelevant to another (counts
  only where relevant — relevance is the matching predicate above,
  nothing else); empty `target_titles` and zero experience roles
  (the empty-denominator rule above).
- **Acceptance criteria.**
  - Score is deterministic for a fixed ledger + targets +
    evaluated-posting history (same three inputs, same score,
    shown in a test). A test that varies only the history —
    corpus fixture F7 in B2 — changes the score by exactly the
    fixture's stated amount, which is the positive proof that
    the history is an input and not an accident.
  - Two fixture ledgers ship in the spec's test pack with
    **hand-computed expected scores** (computed from the formula
    above by the spec author, not by the code under test); the
    implementation must reproduce both exactly. **Each fixture
    also freezes its evaluated-posting history** (an empty
    history, or the named postings with their cluster
    assignments and extracted skills) as part of the fixture —
    a fixture that does not state its history is incomplete
    and may not be used to pass this criterion.
  - A gain list entry's predicted points equal the formula's output
    with that claim flipped to proven — verified against the
    hand-computed fixture, not against the implementation's own
    prediction.
  - Breakdown sums to the headline score.
  - The worked example above is a third fixture: 10 entries, 6
    matching, 3 of those proven reproduces first term 20 exactly,
    computed by the spec owner by hand from the predicate, not by
    the code under test. Its frozen history is **empty** and its
    six matches are by test (a) (role-family key equality), so
    the history contributes nothing to this fixture's number.
  - History fixture (corpus F7, frozen in B2): with the
    fixture's ledger and target title fixed, depth is 45 with
    an empty evaluated-posting history and 85 after the one
    named posting is evaluated — the implementation reproduces
    both figures exactly, from the three stated inputs.
  - Normalisation fixture (hyphenated arrangement tokens): with
    target title "Backend Engineer", a worked-in role titled
    "Backend Engineer (Full-Time)" matches test (a) — its
    family key is {backend, engineer}, the `full-time`
    arrangement tokens having been deleted under the
    normalisation steps above — and "Backend Engineer
    (Part-Time)" produces the same key.
  - A fixture with empty `target_titles` scores first term 0,
    shows the "no target roles set" note, and does not error; a
    fixture with zero experience roles shows the second term as
    "no data yet" and contributes 0 for it.
  - Role-family fixtures (C-04): with target title "Backend
    Engineer", a worked-in role titled "Staff Backend Engineer"
    matches test (a) (same family key after the seniority token
    is deleted) and "Platform Engineer" does not; both results
    are produced by the frozen definition in this feature, and
    a build that assigns families through
    `calibration.py: role_family()`'s keyword buckets fails
    this fixture.
  - Non-quantified proof (C-05): the worked check in the
    definition above is a fixture — 10 claims, all matching
    (by test (a); its frozen evaluated-posting history is
    empty),
    exactly one `approved` with a non-quantified proof, the rest
    unverified — and the implementation reproduces its
    hand-computed contribution of 7 points (term 1 = 4, term 3
    = 3, term 2 = 0) exactly; a gain prediction for flipping
    that same proof predicts terms 1 and 3 only.

### A5. Intake standard (proof at the door)

- **What it does.** Closes the intake hole in the honesty claim
  (brief §3, Pillar 3): today a claim typed into setup is
  indistinguishable from a proven one, and every downstream check
  traces to it. (Today's setup grill is itself opt-in — the
  wizard's `--grill` mode — so the default intake captures no
  quantified wins at all; this standard is written for the default
  flow, not the opt-in one.) With A5, every claim enters the ledger in state
  **unverified**.
- **Target titles (owned here).** Intake also owns `target_titles`:
  the wizard already collects them (`wizard.py` basics/targets
  step, stored by `blank_profile()`); A5 makes that step explicit
  and validated — titles are normalised, duplicates merged, and
  the user may defer ("not sure yet"), which leaves the list empty
  rather than inventing targets. When the list is empty: A4
  applies its empty-denominator rule, B2/B3 classify per posting
  as normal, B5 files the posting under an "unassigned" family
  (no family trend is drawn from it), and E2's first fed posting
  offers — once, without blocking the flow — "use this posting's
  title as your first target?". Nothing downstream requires
  targets to exist. At entry (wizard or manual edit), the user is asked
  for the proof (the number, the story, the link) and may defer —
  deferral is allowed, invisibility is not: an unverified claim is
  labelled as such in the profile view, in tailoring provenance, and
  in the delta, where it can classify at best as an *evidence gap*,
  never *supported*. **The labelling surfaces include
  resume-builder output and the LinkedIn drafts (D2-08):** the
  builder's preview and emitted files, and the LinkedIn draft
  review, label every claim with its proof state wherever the
  claim appears — a generated resume is where claims work most,
  and it is not exempt from the label (C3's artefact-path
  inventory, paths 4 and 5, states the gate behaviour).
  Attaching proof later moves it through the A3
  approval flow like any other proposal.
- **Fallback for a descoped provenance surface (the fallback
  roadmap Fork 0.6 Outcome B states is stated in feature-sets —
  it is stated here, for this feature).** If the provenance
  surface initiative ends in Fork 0.6 Outcome B (provenance
  formally descoped, no wired per-line provenance surface),
  this feature's labelling does **not** wait for a surface
  that does not exist, and its acceptance reverts to this
  fallback, word for word: (i) the unverified label renders on
  the surfaces that exist without the descoped surface —
  **starting with the profile view**, and including the delta
  report **when Phase 2 builds it**, the C2 review surface's
  claim list (each claim in a tailored draft listed with its
  proof state, in place of a per-line provenance map), and the
  resume-builder and LinkedIn draft reviews named above — the
  same fallback roadmap Fork 0.6 Outcome B states, in the same
  terms; (ii) no acceptance
  assertion for this feature requires a provenance map or a
  provenance surface, because none exists under the descope;
  (iii) the assertions that do require a wired provenance
  surface (any delta / provenance-map label assertion beyond
  the claim-list form in (i)) stay **built, gate pending**
  until a later, separately gated wiring initiative lands a
  surface, exactly as Fork 0.6 Outcome B records for
  initiative 1.5; and (iv) the rule itself does not change
  under the fallback: an unverified claim is never presented
  as proven on any fallback surface. Outcome A (the surface
  is wired) leaves the primary text above untouched; this
  fallback is the whole of the descoped behaviour, and a
  builder at the descope trigger invents nothing further.
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
    in profile view, provenance map, and delta report. **Under
    Fork 0.6 Outcome B, this bullet is read in its fallback form
    (the fallback section above): profile view, delta report,
    and the C2 review claim list — no provenance map exists to
    assert against, and the provenance-map assertions stay
    built, gate pending until a wiring initiative lands.**
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
  verbatim quotes + the existing decode verdict. Each requirement
  carries three fields the rest of the B set consumes:
  `requirement_level` — `must_have` or `preferred`, assigned
  **only** by Step 2 of the closed classification decision
  procedure in B2 (section-to-level mapping, bullet-wording
  precedence, and the stated no-signal default). No other
  sentence in this package defines the level, and no builder
  assigns it from the old keyword-only reading: a bullet under
  a must-have heading is `must_have` even when the words
  required / essential / minimum appear nowhere in the posting;
  `extraction_confidence` — `high` or `low`, with a
  `confidence_reason` string. Confidence is `low` when the
  requirement was extracted from responsibility lines rather than
  an explicit requirements section, when the level fell to the
  procedure's no-signal default (Step 2), when the posting text was
  supplied in a non-English language, or when the quote had to be
  assembled from more than one line; otherwise `high`; and
  `requirement_kind` — exactly one of `quantitative`,
  `threshold`, or `categorical`, assigned **only** by Step 4 of
  the procedure in B2 (the ordered kind priority). The kind
  names mean what Step 4 says they mean and nothing else.
  There is no fourth field anywhere for this:
  B2 aggregates these values into the delta's confidence and
  its classification, B3 renders them, and no feature invents
  its own confidence mark or its own kind list.
- **Extraction is governed by one procedure, stated in B2.**
  B4 asserts that two builders implementing this package
  produce the same veto; that is true only if the requirement
  list itself is a function of the posting. Extraction,
  level assignment, duplicate identity and merge, kind
  assignment, the seniority rule, and location matching are
  therefore **not** stated in this feature as separate rules.
  They are Steps 1–6 of the single closed classification
  decision procedure in B2 ("The closed classification
  decision procedure"), which this feature and B2 both
  implement and which no other text in this package restates
  in a competing form. The former producibility rules (a)–(d)
  — presented-unit atomicity and the conjunctive test,
  ordered kind priority, the disjunction rule, and the
  seniority at-or-above rule — are carried into that
  procedure in substance (Steps 1, 4, and 5) and survive only
  there. Where any summary of extraction in this feature
  appears to differ from a procedure step, the step governs.
- **Reuses.** `jd_decoder.py: decode_jd()` / `jd_verdict()` (posting
  side), `initiatives/i04/schemas.py` requirement shape,
  `initiatives/i04/file_ingest.py` parsing patterns. Requirement
  extraction must stay deterministic — no model call invents a
  requirement that is not quotable from the posting.
- **Edge cases.** Posting with no explicit requirements section
  (extract from responsibility lines, mark confidence lower, still
  quote-backed); requirements stated as years ("8+ years") map to the
  years check, not a skill; duplicate requirements are merged under
  Step 3 of the procedure in B2 (alias-table identity, must-have
  wins on a level conflict, both quotes kept, the losing
  presentation recorded on the merged requirement).
- **Acceptance criteria.**
  - Every extracted requirement carries a verbatim quote found in the
    posting text (test asserts quote ∈ posting for the fixture set).
  - For each of the three fixture postings (clean / vague / overwork),
    the **expected requirement list — items plus their quotes — is
    authored by the spec owner and frozen in the fixture files before
    implementation begins**; extraction must reproduce those lists
    exactly. Whoever writes the code does not set the bar they are
    tested against.
  - Duplicate requirements: a fixture posting stating the same
    requirement twice produces one extracted requirement carrying
    both verbatim quotes. The corpus fixtures in B2 assert the
    harder cases: F2 (same requirement at two levels — one merged
    requirement, `must_have`, both quotes, losing presentation
    recorded) and F3 ("Kubernetes" / "k8s" — one merged requirement
    under the alias table's identity rule).
  - Level mapping (Procedure Step 2): corpus fixture F1 (a
    "Requirements"-headed list with no required / essential /
    minimum wording anywhere) extracts every bullet as
    `must_have`; fixture F16 (a heading in neither closed set and
    no bullet wording signal) extracts `preferred` by the stated
    default, at `low` confidence with the default named as the
    reason.
  - Confidence: the fixture posting with no requirements section
    yields `extraction_confidence: low` with a reason naming the
    responsibility-line source on each extracted requirement; the
    clean fixture yields `high` throughout.
  - Atomicity (Procedure Step 1): the frozen split fixture — a
    posting whose must-have bullets are "Kubernetes and Go"
    (one bullet) plus three further must-haves the fixture
    profile supports — extracts to **M = 4**, never 5; the same
    posting with the "Kubernetes and Go" bullet wrapped across
    two physical lines still extracts to M = 4. With the
    fixture profile supporting Kubernetes and holding nothing
    on record for Go, the compound unit classifies skill gap
    (most severe part), so S = 1: S ÷ M = 0.25 (not skill-gap
    heavy), supported 3 ÷ 4 = 0.75 (not thin), and at a fixture
    score of 60 or above B4 fires no veto. An implementation
    that splits the bullet produces M = 5, S = 2 and a veto —
    and fails this fixture.
  - Kind priority (Procedure Step 4): the three worked quotes in
    Step 4 are fixtures with their stated kinds —
    "5+ years operating Kubernetes clusters serving 2M
    requests/day" → `threshold` (one requirement, not two),
    "Scaled a system to 2M requests/day" → `quantitative`,
    "AWS Certified Solutions Architect" → `categorical`.
  - Disjunction (Procedure Step 4): the fixture requirement
    "Bachelor's degree or 7 years' equivalent experience" is
    one requirement; with 7 years' experience on approved
    record and no degree on record it classifies supported;
    with the degree claimed but unverified and 5 years on
    approved record (the threshold disjunct contested) it
    classifies evidence gap.
  - Seniority (Procedure Step 5 — the one place the seniority
    rule is stated): the three cells of corpus fixture F14 —
    Staff vs required Senior → supported; Mid vs required
    Senior → contested; unverified level vs required Senior →
    evidence gap — plus F4 (nothing on record → evidence gap,
    never skill gap) and F5 (level token read from the raw title
    before A4 normalisation deletes it → supported).

### B2. Delta classification (evidence gap vs skill gap)

- **What it does.** For one job: run the requirement list (B1) against
  the ledger (A1) and classify each requirement —
  **supported** (the requirement meets Step 7's per-kind
  comparison in the procedure below), **evidence gap** (claim on record,
  proof missing, of the wrong kind for the requirement,
  alias-only, or not quotable),
  **skill gap** (nothing on record) —
  plus a fourth state, **contested** (record contradicts the
  requirement, e.g. years below a stated minimum), which is the veto
  feeder (B4). This promotes i04's three-way status model into the
  core scoring path and joins it with `match.py` components.
  Stated plainly: i04's built model has only the first three
  states; **contested is new in this feature**, not a promotion of
  existing code. A requirement backed only by proof that is stale
  under A1's staleness policy classifies at best as evidence gap
  (reason "proof stale — re-verify"), never supported. The delta
  as a whole carries one `delta_confidence` field. It is the
  delta's confidence, not extraction confidence alone (C2-21):
  it is `low` when any must-have requirement has
  `extraction_confidence: low`, and it is also `low` — capped
  below `high`, whatever the extraction confidence — when any
  must-have classification rests on a provisional alias match
  (B2's dispute path 4), on a combined-proof construction (two
  entries jointly supplying the proof, under the combined-roles
  rule below), or on ageing proof (the deciding entry's proof
  in A1's ageing band, 24–36 months — gate-passing, but not
  fresh); otherwise it is `high`. Where the cap applies, the
  capping reason is named beside the field wherever B3 renders
  it, so a capped delta never presents as a plain `high`. B3
  renders the field, and E2's non-English case reaches it
  through B1 alone.
- **The closed classification decision procedure (one
  procedure for B1 and B2 — every extraction and every
  classification in this package is produced by running these
  nine steps in this order, and by nothing else).** The
  procedure's only inputs are the posting text, the ledger
  (read through Step 7's gate), the versioned alias table and
  metro-locality table (both defined in "Three shared
  definitions" below), and the fixture
  or system clock for staleness. Each step is a function of
  those inputs. **A case a step does not cover falls to the
  default that step states; no step, and no case, is left to
  builder judgment.** Earlier rounds stated pieces of this
  procedure as separate rules in B1 and B2 (the producibility
  rules (a)–(d), the evidence-state gate, the per-kind rows);
  those pieces are carried into the steps below in substance,
  survive only there, and are not restated anywhere else in
  this package in a competing form. B3, B4, B5, and B6 consume
  the procedure's outputs and restate none of its steps.
  - **Step 1 — Presented units and atomicity.** A requirement
    is the smallest unit the posting's own structure
    presents: one list item (a bullet, a numbered item, one
    line of a requirements list) or, where the posting
    presents requirements as prose, one presented clause (text
    the posting itself separates by a line break, a semicolon,
    or a sentence boundary inside a requirements passage). A
    quote assembled from more than one physical line is still
    one requirement when it is one presented unit (its
    `extraction_confidence` is `low` — the count does not
    change). Conjunctions inside one presented unit
    ("Kubernetes and Go" in one bullet) stay **one**
    requirement, never two: its satisfaction test is
    **conjunctive** — every part (each distinct demand joined
    inside the unit) is tested under its own kind's comparison
    in Step 7, through Step 7's gate, and the unit is
    *supported* only when **all** parts are supported. When
    the parts disagree, the unit's class is the **most severe
    part's class**, in the severity order contested > skill
    gap > evidence gap > supported. The delta counts
    presented units, never extracted fragments: no builder may
    split a presented unit into multiple requirements, merge
    two presented units into one (Step 3's merge is the only
    merge), or count a part as a requirement. Re-presentation
    of the same posting content — the same bullet wrapped
    across two lines, the same clause re-flowed — changes no
    count. *Default:* text that presents no demand on the
    candidate (company description, benefits, team prose) is
    not a presented unit and extracts nothing.
  - **Step 2 — Level: section-to-level mapping first, bullet
    wording second, one precedence order.** Each presented
    unit gets its `requirement_level` by applying, in this
    exact order, the first rule that decides it:
    1. **Bullet demotion wording.** If the unit's own text
       contains any demoting phrase from this closed list —
       "nice to have", "nice-to-have", "a plus", "preferred",
       "bonus", "desirable", "ideally", "not required",
       "optional" — the level is `preferred`, whatever heading
       the unit sits under and whatever other wording it
       carries. (A unit carrying both a demoting and a
       promoting phrase is decided here: demotion wins, and
       the conflict is recorded in the unit's
       `confidence_reason`.)
    2. **Bullet promotion wording.** Else, if the unit's own
       text states it as required, essential, or as a stated
       minimum — the closed promotion forms are the words
       "required", "requirement", "essential", "must", and a
       minimum form applied to the candidate ("5+", "at least
       5", "minimum of 5", "5 or more", including minimum
       years) — the level is `must_have`.
    3. **Heading.** Else, the heading of the section the unit
       sits under decides, by this closed table. Heading
       comparison is case-insensitive, ignores trailing
       punctuation and a trailing colon, and a heading's scope
       runs until the next heading. **Must-have heading set:**
       "Requirements", "Qualifications", "Must have",
       "Must-haves", "Minimum qualifications", "Minimum
       requirements", "Required qualifications", "Required
       skills", "Essential qualifications", "What we're
       looking for", "What we are looking for", "What you'll
       bring", "What you will bring", "Who you are".
       A unit under a heading in this set is `must_have`.
       **Preferred heading set:** "Nice to have",
       "Nice-to-have", "Preferred qualifications", "Preferred
       skills", "Bonus", "Bonus points", "Pluses", "Desired
       qualifications", "Desirable skills". A unit under a
       heading in this set is `preferred` (rules 1–2 above
       have already handled a unit whose own wording says
       otherwise).
    4. **No heading, or a heading in neither set.** A heading
       that appears in neither set is treated as no heading —
       that rule is stated here and has no exceptions. With
       no deciding heading and no bullet wording signal under
       rules 1–2, the level is the stated default:
       **`preferred`**, the unit's `extraction_confidence` is
       `low`, and its `confidence_reason` records "no heading
       and no level wording — default preferred".
    This step is also the whole interaction between heading
    evidence and the keyword rules: bullet wording (rules
    1–2) outranks the heading (rule 3), the heading outranks
    the default (rule 4), and no other precedence exists.
    The keyword forms that defined the level in earlier
    drafts survive only as rule 2's promotion forms.
  - **Step 3 — Requirement identity and merge (the only
    merge).** Two presented units are **the same requirement**
    when, after normalisation, they demand the same thing:
    normalisation lowercases the demanded skill, fact,
    credential, place, or level, strips punctuation, and maps
    every alias in the alias table to its canonical form
    ("k8s" → "Kubernetes"). **The alias table governs
    extraction identity under this step, not only
    classification matching in Step 7.** Identity includes
    the demanded value where the demand carries one: two
    threshold units for the same canonical skill with
    different minima are the same requirement (the merged
    minimum is the higher of the two, per the conflict rule
    below); two categorical units naming different places,
    statuses, credentials, or levels are different
    requirements, because the value differs. Units demanding
    different canonical things never merge, however similar
    their wording. When two or more presented units are the
    same requirement, they merge into **one** requirement:
    - **Level conflict: must-have wins.** The merged level
      is `must_have` if any presentation was `must_have`
      under Step 2, else `preferred`.
    - **Kind conflict:** the merged kind is the kind Step 4's
      ordered priority assigns first among the presentations'
      kinds (threshold before categorical before
      quantitative); each presentation's own kind is still
      used for its part's comparison in Step 7 where Step 4's
      conjunctive test applies.
    - **Threshold conflict:** the merged minimum is the
      higher minimum presented.
    - **Quotes and the losing presentation:** the merged
      requirement carries **every** verbatim quote from every
      presentation, and records, for each presentation that
      did not supply the merged level, kind, or minimum, a
      `merged_presentations` entry naming that presentation's
      heading (or "no heading"), its Step 2 level, its kind,
      and its quote — the losing presentation is recorded on
      the merged requirement, never silently dropped.
    *Default:* a unit that merges with nothing is one
    requirement carrying its own quote, with no
    `merged_presentations` entries.
  - **Step 4 — Kind: ordered priority, conjunctions,
    disjunctions.** `requirement_kind` is assigned by the
    first step that matches; the steps are a total order,
    applied in this sequence, and no step is skipped because
    a later step also matches:
    1. **Threshold.** The unit states a candidate-facing
       numeric minimum — a floor the candidate must meet,
       marked by a minimum form in the quote ("5+", "at
       least 5", "minimum of 5", "5 or more") applied to the
       candidate's years, experience, or scale. A number with
       no minimum form is not a threshold number.
    2. **Categorical.** The unit is satisfied by a yes/no
       fact with no quantity to meet and no accomplishment
       to prove: a place, a status, a credential held, a
       seniority level, a stated language.
    3. **Quantitative.** Everything else: a skill or an
       experience accomplishment whose proof is a number or
       a measurable result the user has achieved.
    The discriminator is the unit's satisfaction test, read
    in that order — never the mere presence of a number.
    *Worked examples (also fixtures in B1's acceptance):*
    "5+ years operating Kubernetes clusters serving 2M
    requests/day" is one presented unit; step 1 matches
    ("5+" is a candidate-facing minimum) so the kind is
    `threshold` and the satisfaction test is the threshold
    test on the years number. "Serving 2M requests/day" is
    an elaboration of that one demand — it carries no
    minimum form and is joined by no conjunction presenting
    a second candidate demand — so it creates no second,
    quantitative requirement. By contrast, "Scaled a system
    to 2M requests/day" (no minimum form, an accomplishment)
    is `quantitative` under step 3, and "AWS Certified
    Solutions Architect" (no minimum, a credential held) is
    `categorical` under step 2. For a conjunctive unit whose
    parts fall under different steps, the unit's
    `requirement_kind` label is the kind this procedure
    assigns to the whole unit, and satisfaction still tests
    each part under its own kind's comparison (Step 1's
    conjunctive test, Step 7's comparisons).
    **Disjunctions — "A or B" is one requirement.**
    Alternatives presented inside one unit ("Bachelor's
    degree or 7 years' equivalent experience") are one
    requirement with a disjunctive satisfaction test, not
    two requirements. Each disjunct is tested under its own
    kind's comparison, through Step 7's gate. The
    requirement is **supported when any disjunct is
    supported**. When no disjunct is supported, the class is
    the most favourable disjunct class in the order
    evidence gap > skill gap > contested — equivalently:
    evidence gap if any disjunct is an evidence gap, else
    skill gap if any disjunct is a skill gap, else contested,
    which applies only when **every** disjunct is contested
    (the record affirmatively blocks every alternative).
  - **Step 5 — Seniority: the one place this rule is
    stated.** A seniority requirement ("Senior", "Staff
    level") is `categorical` under Step 4. Its comparison is
    not verbatim equality: levels are ordered **entry < mid <
    senior < staff < principal** (the level order `match.py`
    scores with). The requirement is supported when the
    user's level on record — read through Step 7's gate — is
    **at or above** the required level; contested when that
    gated level is **below** the required level; and an
    **evidence gap when no approved level is on record** —
    a seniority requirement has **no skill-gap outcome**:
    the absence of level evidence is a missing proof about a
    fact the user holds, not an absent skill, and the scoring
    default of "mid" in `match.py` is a scoring default,
    never classification evidence. Every other passage that
    touches seniority — the categorical comparison in Step 7,
    B1's kind list, A4's family key — points at this step and
    states no seniority classification of its own.
    **Extract-then-delete order, stated explicitly:** a level
    token is read from the **raw** title or raw requirement
    text **before** any A4 normalisation runs. A4's
    normalisation deletes seniority tokens to build a family
    key; that key is a family-assignment output only and is
    never an input to this step or to any classification.
    (The existing mechanism this step cites,
    `filters.py: detect_seniority()`, reads the raw lowercased
    title the same way.) A title such as "Staff Backend
    Engineer" therefore yields the level token `staff` for
    this step first, and the family key {backend, engineer}
    for A4 second — the two outputs never compete.
  - **Step 6 — Location matching: one rule, no similarity
    judgment.** This step decides only whether the record's
    locality matches the posting's required place; Step 7's
    gate decides whether that record counts as evidence at
    all, and this step runs only on gated evidence.
    Localities are normalised before comparison: lowercased,
    punctuation stripped, and a trailing state / province /
    country qualifier after a comma dropped ("Philadelphia,
    PA" and "Philadelphia" are the same locality).
    1. **Posting names a locality** (one place, or a list of
       places joined by commas or "or"): a gated record whose
       normalised locality **equals** a named locality is a
       match (supported, through Step 7); a gated record
       whose normalised locality equals **none** of the named
       localities states a different location and is
       **contested**. There is no near match.
    2. **Posting uses metro phrasing** — the closed set of
       forms is: "<Place> area", "Greater <Place>", "<Place>
       metro", "<Place> metro area", "<Place> metropolitan
       area": a gated record matches when its normalised
       locality equals <Place>, **or** when the locality is
       listed under that metro in the versioned
       **metro-locality table** (defined with the alias table
       in "Three shared definitions" below; a data table
       changed only by reviewed change, never a judgment
       made at classification time). A gated record whose
       locality is neither <Place> nor listed under that
       metro in the table is contested. *Default:* a
       locality not in the metro table is not a metro match,
       however close it is geographically.
    3. **Posting states no locality demand** (remote wording,
       or no location text at all): no location requirement
       is extracted from that text under Step 1, so this step
       is not reached for it.
  - **Step 7 — Evidence-state gate, then the per-kind
    comparison (one rule for every kind; every comparison
    below routes through the gate and no comparison restates
    a weaker form).** A requirement classifies **supported
    only on evidence in the approved / proven state**: the
    deciding evidence is a ledger entry in state `approved`
    (A1), in the per-kind form the comparison names
    (quantified proof for `quantitative`, attestation or
    documentary evidence for `categorical`, an approved
    number for `threshold`), whose proof is not stale under
    A1's staleness policy. **Profile facts are not a
    separate, exempt evidence class.** Every profile fact
    this procedure consumes (years, authorisation, location,
    seniority level, language, credential) is read through
    the ledger entry that carries it, and that entry must
    carry both fields for the fact to count as evidence at
    all: its proof state and its `proof_verified_at`. **A
    fact with no `proof_verified_at` is unverified by
    definition** — including a fact that exists only as a
    typed value in the flat profile with no ledger entry
    behind it — and anything resting on unverified profile
    content caps at **evidence gap**, for quantitative,
    threshold, and categorical kinds alike (A5's rule,
    applied without a kind exception). Staleness applies to
    profile facts exactly as it applies to any entry: a fact
    whose `proof_verified_at` is over 36 months old and not
    re-verified caps at evidence gap with the reason "proof
    stale — re-verify". Classification then proceeds in this
    order, and the order is the rule: (1) if the deciding
    evidence passes the gate, apply the kind's comparison
    below — it yields supported, or contested where the
    approved evidence affirmatively contradicts the
    requirement; (2) if a claim or fact is on record but its
    evidence fails the gate (unverified, no
    `proof_verified_at`, stale, alias-only, unquantified
    where the kind requires a quantity, or not quotable),
    the class is evidence gap — never supported, and never
    contested, because an unproven record does not
    affirmatively contradict anything; (3) if nothing is on
    record for the requirement at all, the class is skill
    gap — **with the one stated exception in Step 5:
    seniority never takes the skill-gap outcome under this
    step; Step 5 gives it evidence gap instead, and this
    step states no competing seniority outcome.**
    Compound and disjunctive requirements (Steps 1 and 4)
    apply this gate to each part or disjunct separately.
    **The per-kind comparisons (the one supported test;
    Step 4's kind selects the comparison, and no other
    supported test exists in this package).** Each comparison
    is read **through the gate above**: "on record" never
    means merely typed or listed — it means the gate has
    passed for that evidence.
    - `quantitative` (skills, experience accomplishments):
      supported means **verbatim, quantified proof on
      record** — an `approved` ledger entry whose proof
      states the fact and its number or measurable result. A
      claim with proof that carries no quantity is an
      evidence gap for this kind.
    - `threshold` (stated numeric minimums, in practice
      years): supported means the number carried by evidence
      that passes the gate — an `approved` entry (a profile
      fact counts only as the approved ledger entry carrying
      it, with `proof_verified_at` set and not stale) —
      meets or exceeds the stated minimum. An approved,
      non-stale number below the minimum is contested, not
      a gap. A number on record whose evidence fails the
      gate (typed years with no approved entry, no
      `proof_verified_at`, or stale proof) is an evidence
      gap, whether the number itself is above or below the
      minimum. No number or claim on record at all is a
      skill gap.
    - `categorical` (location, work authorisation, a named
      credential held, seniority level, stated language):
      supported means an `approved` ledger entry states the
      required fact, backed by the evidence kind that fits a
      fact of this type — attestation or documentary
      evidence, specifically: the user's stated authorisation
      status recorded as an approved entry (the attestation
      is the proof), located-in evidence (the user's base or
      address locality, matched to the required place by
      **Step 6's rule and no other rule**, carried by an
      approved entry with `proof_verified_at` set and not
      stale — a typed, unverified base is not located-in
      evidence), or the credential itself on record (issuer
      and credential name; a certificate or issuer record
      attached where the user has one). The seniority
      instance of this comparison is decided by **Step 5**
      and by nothing in this row. No quantity is required,
      and none may be demanded: a categorical requirement
      whose fact is on record in this form is supported in
      full. A categorical fact claimed but failing the gate
      (no approved entry behind it, no `proof_verified_at`,
      or stale) is an evidence gap; approved, non-stale
      evidence that states the opposite (a different location
      under Step 6, a conflicting authorisation status) is
      contested; nothing on record claiming the fact at all
      is a skill gap — subject, for seniority only, to Step
      5's exception, which this sentence does not restate or
      override.
    *Worked fixture (retained, frozen in the acceptance
    criteria):* a posting with M=3 must-haves, all
    `categorical` — located in Philadelphia, US work
    authorisation, and a named certification — where the
    user's record holds all three verbatim, each with its
    approved attestation or documentary evidence,
    `proof_verified_at` set and not stale for each,
    classifies **supported = 3, E = 0, S = 0, C = 0**:
    no thin-evidence veto fires, and B6's location axis
    renders green for this job.
    **Evidence-state transitions (how a class changes over
    time — the only ways it can).** A requirement's class is
    recomputed by running this procedure again; it is never
    edited in place. The transitions that move an input, and
    therefore can move a class on the next run, are exactly:
    a claim moves `unverified` → `approved` (or an entry is
    superseded) through A3 — an evidence gap on gate-fail can
    become supported, or contested if the newly gated evidence
    contradicts the requirement; proof ages fresh → ageing →
    stale under A1's staleness clock — a supported requirement
    becomes an evidence gap ("proof stale — re-verify") at the
    stale boundary and at no earlier moment; a proof is
    deleted or withdrawn — the entry reverts to `unverified`
    under A1 and the class follows the gate on the next run;
    and a dispute outcome under B2's dispute flow supplies
    evidence, corrects the record, or corrects the extraction,
    each of which re-runs the procedure for that job from
    Step 1. A stored delta keeps its as-of class and ledger
    version until a recompute run replaces it (B3's
    invalidation rule); no transition rewrites a stored delta
    or a recorded verdict retroactively.
  - **Step 8 — The four classes and the contested class's
    path.** The procedure outputs exactly one class per
    merged requirement: **supported** (Step 7's comparison
    passed on gated evidence), **evidence gap** (a claim or
    fact is on record but its evidence failed Step 7's gate,
    or Step 5's no-approved-level case), **skill gap**
    (nothing on record at all, seniority excepted by Step 5),
    or **contested** (gated, approved, non-stale evidence
    affirmatively contradicts the requirement — a number
    below a threshold minimum, a different locality under
    Step 6, a conflicting status, or a lower seniority level
    under Step 5). A hard requirement the user simply lacks
    is a skill gap, not contested: contested requires the
    affirmative contradiction, never mere absence.
    **Contested is not exempt from the change-my-answer
    statement.** Every contested requirement feeds Step 9's
    counts and, where B4 vetoes, B4's "what would change the
    answer" statement names for that requirement the same
    prove-it / disprove-it paths B4 specifies (correct the
    record through the dispute flow, or correct the
    extraction or level through the dispute flow, or the
    named date or condition at which the contradiction
    resolves) — a contested class with no change path named
    is a defect in the delta, not a closed case. When a
    contested must-have vetoes is decided by B4's thresholds
    in Step 9, stated there and nowhere else.
  - **Step 9 — Counts, and the feed into B4's veto and
    headline.** From the merged requirement list (Step 3),
    after Steps 4–8 have run on every requirement:
    **M** = the number of merged requirements whose Step 2 /
    Step 3 level is `must_have`. Among those must-haves only:
    **S** = the count classified skill gap, **E** = the count
    classified evidence gap, **C** = the count classified
    contested, and **supported** = the count classified
    supported (so M = S + E + C + supported, always).
    Preferred requirements are classified by the same steps
    and listed in the report, but they enter none of M, S, E,
    C, or supported, and they never decide a veto or a
    headline. B4 then applies its veto thresholds to these
    counts and the job's score, exactly as B4 states them —
    score < 60; C ≥ 1; skill-gap heavy (S ≥ 2, or S ≥ 1 and
    S ÷ M ≥ 0.40); thin evidence (supported ÷ M < 0.50 and
    E ≥ 2, or the insufficient-signal rule) — and, only when
    a veto fires, produces the headline word by B4's headline
    production rule (the word of the most severe class
    present among the must-haves, contested > skill gap >
    evidence gap; supported → neither word; evidence gap →
    *unproven*; skill gap or contested → *unqualified (for
    this posting as written)*, the qualifier never dropped).
    This step states how each count derives; B4 owns the
    thresholds and the headline rule, and no text in this
    procedure changes either.
- **User seat.** The delta report (B3) — classification itself is the
  engine, not a screen.
- **Inputs/outputs.** In: requirement list + ledger + profile facts
  (years, authorization, location for the contested checks) —
  profile facts are consumed **only** as the ledger entries
  carrying them, each with its proof state and
  `proof_verified_at` (Step 7 of the procedure above); a flat
  profile value with no ledger entry behind it is an
  unverified input, never a second evidence source. Out:
  per-requirement classification with the ledger entry (or absence)
  that decided it.
- **Reuses.** `initiatives/i04/evidence_map.py: build_evidence_map()`
  (classification core), `match.py: score_job()` components (the fit
  axes stay; the delta explains them), `grill.py`'s per-application
  two-way split (quantify/gap) as the behavioural precedent.
- **Three shared definitions.** (1) The **alias table**
  ("k8s" ↔ "Kubernetes"), owned here: it lives in a versioned
  data file in the repo; entries are added by reviewed change,
  never by user machines silently, and every alias-based match
  is recorded in the delta as alias-based (visible, not
  hidden). Its initial version — the title/skill aliases the
  Phase 1 consumers need — is implemented under roadmap 1.3;
  this feature extends the table in Phase 2. The table
  governs two things, both stated in the procedure: extraction
  identity and merge (Step 3) and classification matching
  (Step 7). (2) The **metro-locality table**, owned here with
  the alias table: a versioned data file beside the alias
  table, changed only by the same reviewed-change process,
  mapping a metro name (as Step 6's metro forms name it) to
  the closed list of localities that count as that metro. Its
  initial version lists, under "Greater Philadelphia" /
  "Philadelphia" metro, at least the fixture locality King of
  Prussia, PA (corpus fixture F6). A locality absent from a
  metro's list is not a metro match for that metro (Step 6's
  default); no classification-time judgment adds one.
  (3) **Role
  family:** this feature uses the **target role family**
  definition **frozen in A4** (C-04 — normalisation, family
  key, clusters, the non-circular cluster skill set, and the
  reconciliation with `calibration.py: role_family()`, whose
  calibration family governs calibration/E4 only). B2 cites
  A4's frozen text, implements it under roadmap 2.1, and
  neither authors nor amends a variant; B5 cites the same
  frozen definition for its trends.
- **Dispute and re-classification (the user's appeal, owned here;
  B3 renders it, B4 records it).** **Scope, stated plainly
  (B-09): this flow is per-item correction and re-classification
  only.** A dispute can correct the evidence, the record, the
  extraction, or one provisional alias for the one requirement
  disputed, and it re-classifies that requirement (and recomputes
  that job's delta and veto). It does not re-review the
  classifier, its thresholds, its extraction rules, or the
  alias table as a system, and it is not a remedy for
  classification bias; the classifier re-review and the bias
  remedy live in roadmap initiative 2.9, which owns them, and
  no sentence in this feature may describe a dispute as
  providing them. Every classification in the
  delta report carries a "dispute this" action. Disputing opens
  one flow with four named paths, and the user picks the one that
  fits: (1) **"I have this — here is the evidence"**: the supplied
  evidence becomes an A3 proposal; on approval the requirement is
  re-classified. (2) **"The record is wrong"**: the user corrects
  the deciding ledger entry through the A3 review; on approval the
  old entry is superseded (A3's rule) and the requirement is
  re-classified. **Path 2 validation:** no re-classification
  happens before that A3 approval lands; the correction must name
  the entry it replaces (A3's supersession rule), and a correction
  that would leave the entry in a weaker evidence state than the
  original (for example, removing its proof) re-classifies under
  the evidence-state gate (Step 7) like any other state — it produces an
  evidence gap, never a supported result carried over from the
  superseded entry. (3) **"The posting was misread"**: the user
  corrects the extracted requirement or its level; B1's extraction
  for that posting is amended with the correction recorded, and
  the requirement is re-classified. **Path 3 validation — a
  corrected requirement must stay quote-backed, and its boundary
  is stated here:** (i) the corrected requirement's quote must be
  verbatim text present in the posting — B1's quote test (quote
  ∈ posting) applies to the corrected requirement exactly as to
  an extracted one, and a correction whose quote is not in the
  posting is refused and the original classification stands;
  (ii) a level correction (`must_have` ↔ `preferred`) is accepted
  only where the posting's own wording supports the corrected
  level **under Step 2 of the procedure** (a heading in Step 2's
  closed tables, or a Step 2 bullet promotion / demotion phrase),
  and the correction records that wording (for example,
  the section heading or the "nice to have" phrasing the
  requirement sits under); a level correction with no such
  wording in the posting is refused; (iii) a correction may fix
  the quote selection, the kind, or the level — it may not
  delete a requirement outright: a requirement extracted wholly
  in error is corrected by marking it "not a requirement" with
  the posting wording that shows the error recorded, and that
  marking, with its reason, stays in the record and in the
  delta's history. **What path 3 may never do:** it may never
  rewrite a requirement to change a recorded verdict's basis
  retroactively. The original extraction, the original
  classification, and any veto and headline already recorded
  from them stay in the verdict record exactly as issued; a
  path 3 correction creates a new classification and a
  recomputed delta and veto from that moment forward, recorded
  as a dispute outcome (counted separately, per the rule below)
  — it never edits the history it corrects, never supplies
  evidence (that is path 1), and never corrects the ledger
  (that is path 2). (4) **"These are the same
  skill"**: the user proposes an alias; the alias applies
  provisionally to this user's deltas only, is marked
  "provisional alias" wherever it decides a classification, and
  enters the shared alias table only through the reviewed repo
  change the alias table already requires — it never merges
  silently. **Path 4's resulting classification, stated
  (C-15):** a requirement that was a skill gap and matches
  only through the provisional alias re-classifies to
  **evidence gap** — an alias-only match is never supported
  (the edge-case rule below) — marked "provisional alias";
  when the disputed requirement is a must-have, the counts in
  B4's notation therefore move S−1, E+1, and the job's veto and
  headline are recomputed from those new counts like any
  other dispute outcome; when it is a preferred requirement,
  B4's must-have counts do not move, and the veto and headline
  are recomputed unchanged by that move alone. In every path: the dispute, the original
  classification, the path chosen, the evidence or correction
  supplied, and the resulting classification are written to the
  job's verdict record (B4) and to the delta's history; the delta
  is recomputed (not patched) and B4's veto is recomputed from
  the new delta. A dispute is **not** an override: disputes and
  overrides are counted separately in B4's record, so a corrected
  classification never inflates the overturn rate. If the
  re-classification changes nothing, the record says so and the
  original classification stands, with the dispute attached.
- **Edge cases.** Skill present under an alias ("k8s" vs "Kubernetes")
  — alias table consulted, and an alias-only match is evidence gap,
  not supported (mirrors i04's rule); skill in bullets but not the
  skill list — evidence gap, never silently supported; requirement
  the user meets via a combination of two roles (supported, both
  entries cited — combined support requires that the cited
  entries **together** supply the proof the requirement's kind
  requires (for a `quantitative` requirement: verbatim,
  quantified proof; for a `categorical` requirement: the
  attestation or documentary evidence Step 7's categorical
  comparison names); no single entry need cover it alone, and the delta
  names both entries and which part each proves). Combined
  support routes through the evidence-state gate (Step 7) per entry:
  every cited entry must itself pass the gate (`approved`,
  `proof_verified_at` set, not stale) — a pair in which one
  entry is unverified classifies at best as evidence gap.
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
  - The fixture matrix gains a combined-roles cell: two entries
    that jointly prove one requirement classify it supported with
    both entries cited, and a pair whose joint proof is
    unquantified classifies evidence gap (F4-20 coverage).
  - Evidence-state gate (Procedure Step 7, frozen constructions): the
    fixture posting requiring "5+ years" (threshold, must-have)
    against a profile whose years value is 7, typed at intake,
    sitting `unverified` with no approved entry and
    `proof_verified_at` null, classifies **evidence gap, never
    supported**; the fixture posting requiring "located in
    Philadelphia" (categorical, must-have) against a profile
    whose Philadelphia base is typed and unverified in the same
    state classifies **evidence gap, never supported**. The
    same two fixtures with the deciding facts carried by
    approved entries (`proof_verified_at` set, not stale)
    classify supported. A third cell carries the Philadelphia
    attestation approved but with `proof_verified_at` 37
    months before the fixture clock: evidence gap with the
    reason "proof stale — re-verify".
  - Frozen fixture corpus: every fixture F1–F17 in the
    B1/B2 frozen fixture corpus following this feature
    reproduces exactly as written there — extraction, levels,
    kinds, classes, M / S / E / C / supported counts, veto
    outcome, and headline word — when the procedure's nine
    steps are run on the fixture's stated posting, ledger, and
    fixture score.
  - Dispute: disputing the fixture skill-gap requirement by path 1
    and approving the supplied evidence re-classifies it, writes
    the dispute and both classifications to the verdict record,
    and recomputes the fixture's veto; disputing by path 4 marks
    the resulting classification "provisional alias" in the
    report **and asserts its class is evidence gap** (C-15) —
    the label alone does not pass this test.
  - Dispute path 2 (C2-09): the fixture requirement classified
    contested on a deciding entry the user corrects through A3
    (the correction names the entry it replaces) re-classifies
    only after the approval lands, from the new entry; before
    approval the original classification and veto stand, and a
    correction that removes the entry's proof re-classifies to
    evidence gap, never to a carried-over supported.
  - Dispute path 3 (C2-09): the fixture must-have extracted from
    a passage the posting itself heads "Nice to have" is
    corrected to `preferred` with that heading recorded as the
    supporting wording, and the job's veto and headline are
    recomputed forward from the correction while the verdict
    record keeps the original extraction, classification, and
    veto exactly as issued. Two negative cells: a correction
    whose quote does not appear in the posting is refused and
    the original classification stands; a level correction
    with no supporting wording in the posting is refused.
  - Categorical fixture (C-02): the worked fixture in the
    Step 7 comparison above — M=3 categorical must-haves (Philadelphia
    location, US work authorisation, a named certification), all
    three on record verbatim with approved attestation or
    documentary evidence — classifies supported = 3 with E = 0,
    and, **at the fixture's stated score of 72**, B4's
    delta-driven trigger conditions (conditions 2–4) fire no
    veto on that delta and no thin-evidence veto fires. (The
    fixture asserts nothing wider: B4's condition 1 is a
    function of the score, not the delta, and the score is
    stated here so the run is complete.) A second
    cell in the same fixture, in which the certification is
    claimed with no approved entry behind it, classifies
    evidence gap, never supported.


### B1/B2 frozen fixture corpus (the rulebook's fixtures)

These fixtures are part of the spec. Each one states its posting
and ledger inputs, the expected extraction, levels, kinds,
classes, the Step 9 counts (M / S / E / C / supported — S, E, and
C count must-haves only), a fixture score where a veto outcome
is asserted (the score is a fixture input; the procedure does
not compute scores), the veto outcome under B4's thresholds,
and the headline word under B4's production rule (a headline
exists only when a veto fires). A re-audit or an implementation
must be able to re-derive every line mechanically from the
procedure's nine steps; a build that reproduces the posting and
ledger and reaches a different line in any fixture fails that
fixture. Unless a fixture says otherwise, every approved entry
named carries `proof_verified_at` set and not stale, and every
fixture clock is the date the delta is computed.

- **F1 — "Requirements"-headed list, no level keywords
  anywhere.** *Posting:* title "Backend Engineer"; one section
  headed "Requirements" with four bullets: "Kubernetes
  experience", "Go experience", "PostgreSQL experience",
  "Python experience". The words required / essential /
  minimum appear nowhere in the posting. *Ledger:* approved,
  quantified proof for Go, PostgreSQL, and Python; nothing on
  record for Kubernetes. *Expected:* Step 2 rule 3 (must-have
  heading) makes all four bullets `must_have` — Step 1 units,
  all `quantitative` under Step 4 step 3. Classes: Kubernetes
  skill gap; the other three supported. **M = 4, S = 1, E = 0,
  C = 0, supported = 3.** Fixture score 72: S ÷ M = 0.25 (not
  skill-gap heavy), supported ÷ M = 0.75 (not thin), C = 0,
  score ≥ 60 — **no veto, no headline word.**
- **F2 — The same requirement at two levels (merge and
  conflict).** *Posting:* under "Requirements", the bullet
  "Kubernetes experience"; under "Nice to have", the bullet
  "Kubernetes a plus". *Ledger:* nothing on record for
  Kubernetes. *Expected:* Step 3 identity (same canonical
  demand) merges the two presentations into **one**
  requirement carrying both verbatim quotes; the merged level
  is `must_have` (must-have wins); the merged requirement
  records a `merged_presentations` entry for the "Nice to
  have" presentation (its Step 2 level `preferred`, its quote,
  its heading). Kind `quantitative`. Class: skill gap.
  **M = 1, S = 1, E = 0, C = 0, supported = 0.** Fixture score
  78: S ≥ 1 and S ÷ M = 1.00 ≥ 0.40 — skill-gap heavy —
  **veto fires; headline *unqualified (for this posting as
  written)*.**
- **F3 — Alias identity ("Kubernetes" / "k8s").** *Posting:*
  under "Requirements", two bullets: "Kubernetes experience"
  and "k8s experience". *Ledger:* one approved entry with
  verbatim, quantified proof for Kubernetes. *Expected:*
  Step 3 normalisation maps "k8s" to the canonical
  "Kubernetes" through the alias table, so the two bullets are
  the same requirement and merge into **one** requirement
  carrying both quotes, level `must_have`, kind
  `quantitative`. The deciding entry matches the merged
  requirement's canonical demand, so this is a canonical
  match, not an alias-only evidence case. Class: supported.
  **M = 1, S = 0, E = 0, C = 0, supported = 1.** Fixture score
  80 — **no veto, no headline word.** (A build that counts
  two requirements here fails identity under Step 3.)
- **F4 — Seniority, nothing on record.** *Posting:* under
  "Requirements", the bullet "Senior level". *Ledger:* no
  seniority level on record at all — no entry, approved or
  otherwise, states a level. *Expected:* kind `categorical`
  (seniority, Step 4 step 2), level `must_have`; Step 5
  decides the class: **evidence gap** — a seniority
  requirement has no skill-gap outcome, and Step 7 step (3)
  states no competing outcome for it. **M = 1, S = 0, E = 1,
  C = 0, supported = 0.** Fixture score 75: thin evidence
  needs E ≥ 2 — **no veto, no headline word.**
- **F5 — "Staff Backend Engineer" as level evidence
  (extract-then-delete).** *Posting:* under "Requirements",
  the bullet "Senior level". *Ledger:* an approved seniority
  entry, `proof_verified_at` set and not stale, stating the
  user's level as Staff — the level value that was read from
  the raw worked-in role title "Staff Backend Engineer" when
  the entry was created. *Expected:* Step 5 reads the level
  token `staff` from the raw title **before** A4 normalisation
  deletes seniority tokens (the role's A4 family key is
  {backend, engineer}; the key is not a classification input).
  Staff is at or above Senior — class: supported. **M = 1,
  S = 0, E = 0, C = 0, supported = 1.** Fixture score 80 —
  **no veto, no headline word.**
- **F6 — Location: named locality vs metro phrasing (two
  cells, one record).** *Ledger (both cells):* an approved
  located-in entry stating the user's base as King of Prussia,
  PA, `proof_verified_at` set and not stale.
  - **F6a — posting names a locality.** *Posting:* under
    "Requirements", the bullet "Based in Philadelphia".
    *Expected:* kind `categorical`, level `must_have`; Step 6
    rule 1 — the record's normalised locality (king of
    prussia) equals none of the named localities
    (philadelphia) — class: **contested**. **M = 1, S = 0,
    E = 0, C = 1, supported = 0.** Fixture score 82: C ≥ 1 —
    **veto fires at any score; headline *unqualified (for
    this posting as written)*;** the change-my-answer
    statement names the contested paths (Step 8 / B4).
  - **F6b — posting uses metro phrasing.** *Posting:* the
    same bullet as "Based in the Greater Philadelphia area".
    *Expected:* Step 6 rule 2 — "Greater <Place>" is a closed
    metro form, and the metro-locality table lists King of
    Prussia under the Philadelphia metro — class:
    **supported**. **M = 1, S = 0, E = 0, C = 0,
    supported = 1.** Fixture score 82 — **no veto, no
    headline word.**
- **F7 — A4 depth score before / after one evaluated posting
  (the evaluated-posting history is an A4 input).** *Target
  titles:* "Backend Engineer" (one cluster, family key
  {backend, engineer}; the title names no skills). *Ledger
  (fixed in both runs):* entry A — worked in the role
  "Operations Engineer", skill tags {kubernetes}, `approved`
  with verbatim, quantified proof ("operated Kubernetes
  clusters for 14 services"); entry B — worked in the role
  "Operations Engineer", skill tags {python}, `unverified`.
  *Evaluated posting (the second run only):* title "Backend
  Engineer", under "Requirements" the bullet "Kubernetes
  experience" — assigned to the Backend Engineer cluster by
  A4's title rule, and B1 extracts Kubernetes from it.
  *Expected extraction / classification for that posting:*
  one unit, `must_have` (Step 2 rule 3), `quantitative`,
  supported by entry A — **M = 1, S = 0, E = 0, C = 0,
  supported = 1**; fixture score 80 — **no veto, no headline
  word.** *Expected depth (A4's formula):* terms 2 and 3 are
  the same in both runs — one experience role (Operations
  Engineer) carrying a quantified, proven win gives term 2 =
  30 × 1/1 = 30; one of two claims proven gives term 3 =
  30 × 1/2 = 15. Term 1 turns on the history. **Before** any
  posting is evaluated (history empty): the cluster skill set
  is empty, entry A's family key {engineer, operations} does
  not equal the cluster key and its kubernetes tag is in no
  cluster skill set, so no entry matches — term 1's
  denominator is 0, term 1 = 0 ("no data yet"), **depth =
  45**. **After** that one posting is evaluated (history =
  that posting): the cluster skill set is {kubernetes}, entry
  A matches by test (b) and is proven — term 1 = 40 × 1/1 =
  40, **depth = 85**. Same ledger, same targets, different
  history, different score — the fixture names the history as
  an input, which is what makes both runs deterministic.
- **F8 — Unverified threshold.** *Posting:* under
  "Requirements", "5+ years of backend development".
  *Ledger:* years = 7, typed at intake, `unverified`, no
  approved entry behind it, `proof_verified_at` null.
  *Expected:* kind `threshold`, level `must_have`; Step 7's
  gate fails (the 7 ≥ 5 comparison is never reached) —
  class: **evidence gap**, never supported and never
  contested. **M = 1, S = 0, E = 1, C = 0, supported = 0.**
  Fixture score 72 — **no veto, no headline word.**
- **F9 — Unverified categorical.** *Posting:* under
  "Requirements", "Located in Philadelphia". *Ledger:* a
  Philadelphia base typed at intake, `unverified`, no approved
  entry behind it, `proof_verified_at` null. *Expected:*
  kind `categorical`, level `must_have`; Step 7's gate fails
  (a typed, unverified base is not located-in evidence) —
  class: **evidence gap**, never supported. **M = 1, S = 0,
  E = 1, C = 0, supported = 0.** Fixture score 72 — **no
  veto, no headline word.**
- **F10 — Stale proof (37 months).** *Posting:* as F9.
  *Ledger:* the Philadelphia attestation is an approved entry,
  but its `proof_verified_at` is 37 months before the fixture
  clock and it has not been re-verified. *Expected:* Step 7's
  gate fails on staleness — class: **evidence gap** with the
  reason "proof stale — re-verify", never supported.
  **M = 1, S = 0, E = 1, C = 0, supported = 0.** Fixture score
  72 — **no veto, no headline word.**
- **F11 — Split-bullet counts (atomicity).** *Posting:* under
  "Requirements", four bullets: "Kubernetes and Go" (one
  bullet) plus three further must-have bullets the ledger
  supports. *Ledger:* Kubernetes supported on approved,
  quantified proof; nothing on record for Go; the other three
  bullets supported. *Expected:* Step 1 counts presented
  units — **M = 4**, never 5 (the same posting with the first
  bullet wrapped across two physical lines still gives
  M = 4). The compound unit's conjunctive test: Kubernetes
  part supported, Go part skill gap, most severe part
  governs — the unit's class is skill gap. **M = 4, S = 1,
  E = 0, C = 0, supported = 3.** Fixture score 64: S ÷ M =
  0.25 (not heavy), supported ÷ M = 0.75 (not thin) — **no
  veto, no headline word.** (A splitting build reaches M = 5,
  S = 2, a skill-gap-heavy veto — and fails this fixture.)
- **F12 — Mixed-kind quote (kind priority).** *Posting:*
  under "Requirements", one bullet: "5+ years operating
  Kubernetes clusters serving 2M requests/day". *Ledger:* an
  approved entry carrying years = 6, `proof_verified_at` set
  and not stale. *Expected:* one presented unit; Step 4 step
  1 matches first ("5+") — kind `threshold`, **one**
  requirement, not two ("serving 2M requests/day" creates no
  quantitative requirement). The threshold comparison on the
  gated number: 6 ≥ 5 — class: supported. **M = 1, S = 0,
  E = 0, C = 0, supported = 1.** Fixture score 77 — **no
  veto, no headline word.**
- **F13 — Disjunction (two cells).** *Posting (both cells):*
  under "Requirements", one bullet: "Bachelor's degree or
  7 years' equivalent experience" — one requirement, kind
  assigned per disjunct under Step 4 (the degree disjunct is
  `categorical`, the years disjunct is `threshold`).
  - **F13a:** *Ledger:* 7 years on approved record; no degree
    on record. The years disjunct is supported, so the
    requirement is **supported**. **M = 1, S = 0, E = 0,
    C = 0, supported = 1.** Fixture score 81 — **no veto, no
    headline word.**
  - **F13b:** *Ledger:* the degree is claimed but unverified;
    5 years on approved record. Degree disjunct: evidence gap
    (gate fail). Years disjunct: contested (approved 5 below
    the 7 minimum). No disjunct supported; the most
    favourable disjunct class in Step 4's order (evidence gap
    > skill gap > contested) governs — class: **evidence
    gap**. **M = 1, S = 0, E = 1, C = 0, supported = 0.**
    Fixture score 81 — **no veto, no headline word.**
- **F14 — Seniority, three cells.** *Posting (all cells):*
  under "Requirements", "Senior level" — `categorical`,
  `must_have`. Fixture score 85 in all three cells.
  - **F14a:** approved level on record: Staff. At or above
    Senior — **supported**. M = 1, supported = 1, S = E =
    C = 0 — **no veto, no headline word.**
  - **F14b:** approved level on record: Mid. Below Senior —
    **contested**. M = 1, C = 1, S = E = 0, supported = 0 —
    **veto fires (C ≥ 1, at any score); headline
    *unqualified (for this posting as written)*.**
  - **F14c:** a level typed at intake but `unverified`, no
    approved entry, `proof_verified_at` null. Gate fail —
    **evidence gap** (Step 5; never skill gap). M = 1, E = 1,
    S = C = 0, supported = 0 — **no veto, no headline word.**
- **F15 — Contested, with its change-my-answer path.**
  *Posting:* under "Requirements", "5+ years of backend
  development". *Ledger:* an approved entry carrying years =
  3, `proof_verified_at` set and not stale. *Expected:* kind
  `threshold`, level `must_have`; the gated number is below
  the minimum — class: **contested**. **M = 1, S = 0, E = 0,
  C = 1, supported = 0.** Fixture score 80: C ≥ 1 — **veto
  fires; headline *unqualified (for this posting as
  written)*.** The veto's change-my-answer statement is
  present for this contested requirement — contested is not
  exempt (Step 8): it names **prove it** (if the record is
  wrong or out of date, supply correcting evidence through
  the dispute flow, path 1 or 2, and the requirement
  re-classifies), **disprove it** (if the posting was misread,
  dispute path 3 corrects the extraction or level), and,
  where neither can happen today, the plain condition: the
  contradiction resolves when the approved record reaches
  5 years. A rendering of this fixture with no
  change-my-answer statement for the contested requirement
  fails the fixture.
- **F16 — No heading, no wording signal (the stated
  default).** *Posting:* no section headings at all; after an
  introductory paragraph, a bare list with the bullet
  "Kubernetes experience". No demotion phrase, no promotion
  word, no minimum form. *Ledger:* nothing on record for
  Kubernetes. *Expected:* Step 2 rule 4 — the level is the
  default **`preferred`**, `extraction_confidence` is `low`,
  and `confidence_reason` records "no heading and no level
  wording — default preferred". Kind `quantitative`; class
  skill gap — **as a preferred requirement**: it is listed in
  the report and enters none of the must-have counts.
  **M = 0, S = 0, E = 0, C = 0, supported = 0** (over
  must-haves). Fixture score 70 — **no veto from this
  requirement, no headline word.** (The same bullet under a
  heading that appears in neither of Step 2's closed sets —
  for example "About the team" — reaches the identical
  result by the same rule: an unlisted heading is treated as
  no heading.)
- **F17 — `delta_confidence` caps (three cells).** Each cell
  is a one-must-have delta at fixture score 75, no veto in any
  cell; the asserted output is the delta's `delta_confidence`
  and its named capping reason (B2's definition of the field).
  - **F17a — provisional alias:** the must-have's
    classification rests on a provisional alias match
    (dispute path 4; class evidence gap, M = 1, E = 1) —
    `delta_confidence: low`, reason "provisional alias".
  - **F17b — combined proof:** the must-have is supported by
    two approved entries jointly (combined proof; M = 1,
    supported = 1) — `delta_confidence: low`, reason
    "combined proof".
  - **F17c — ageing proof:** the must-have is supported on an
    approved entry whose `proof_verified_at` is 30 months
    before the fixture clock (A1's ageing band; M = 1,
    supported = 1) — `delta_confidence: low`, reason "ageing
    proof". (A must-have supported on fresh, single-entry,
    canonical proof with `extraction_confidence: high`
    renders `delta_confidence: high` — the uncapped case.)

### B3. Delta report (the per-job product surface)

- **What it does.** The screen/report a user reads for one job: fit
  score and Radar (existing), then the delta in plain language —
  proven strengths (with the proof), evidence gaps (with the one
  action that closes each), skill gaps (with what would close them:
  project/course/time, from `skill_gaps.py: gap_plan()`), contested
  items (why a veto is on the table). Ordered by impact on the score
  (score impact, defined operationally immediately below, is the
  one ordering criterion for **per-job** gap lists in this
  package; D4 uses this same list in this same order. B5's
  cross-job recurring-gap ranking is a different list — a
  frequency ranking across jobs, not a per-job gap list — and
  is not ordered by this criterion).
  **Score impact, defined (C2-14 — the quantity, the mapping,
  the tie-breaks, stated once here; D4 cites this definition).**
  For one job's delta, a requirement's **score impact** is the
  share of its fit axis's points attributable to it under the
  weights `score_job()` used for this job's score (the weights
  are recorded with the score; the static defaults are skills
  50, seniority 15, salary 15, location 15, recency 5):
  *impact(r) = W(axis(r)) ÷ N(axis(r))*, where *W* is the
  axis's point weight and *N* is the number of requirements
  in this job's delta — must-have and preferred, gaps and
  supported alike, because the axis term is spread over all
  of them — mapped to that axis. The axis mapping is fixed:
  `quantitative` and `threshold` requirements map to the
  **skills** axis; a seniority `categorical` requirement maps
  to the **seniority** axis; a location `categorical`
  requirement maps to the **location** axis; every other
  `categorical` requirement (work authorisation, a named
  credential, a stated language) maps to **no fit axis** and
  its impact is **0** — defined as zero, never left undefined.
  No requirement maps to the salary or recency axes (B6's
  rule: those axes carry no requirement classification).
  The gap list (every non-supported requirement) is ordered
  by impact **descending**; ties are broken, in order, by
  (1) must-have before preferred, (2) class severity —
  contested before skill gap before evidence gap, (3) B1
  extraction order, earliest first. That is a total order:
  two builders computing it from the same delta and the same
  recorded weights produce the same list.
  *Worked example (frozen in the acceptance criteria):*
  static weights; a delta with R1 Kubernetes (`quantitative`,
  must-have, evidence gap, skills), R2 Go (`quantitative`,
  must-have, skill gap, skills), R3 Python (`quantitative`,
  must-have, supported, skills), R4 Senior (seniority,
  must-have, contested), R5 Philadelphia (location,
  must-have, supported), R6 a named certification
  (`categorical`, preferred, skill gap, no axis). N(skills)
  = 3, so R1 and R2 each carry impact 50 ÷ 3 ≈ 16.67;
  N(seniority) = 1, so R4 carries 15; R6 carries 0. The gap
  list is therefore **R2, R1, R4, R6**: R2 before R1 on the
  severity tie-break (skill gap before evidence gap), then
  R4, then R6 — and D4's top-3 gaps for this job are R2, R1,
  R4, in that sequence.
  The report's headline answer, when B4 vetoes, is the binary the
  brief promises — **unproven** or **unqualified (for this posting
  as written)** — produced only by B4's mapping (B4 owns it; this
  report renders the result and never invents its own wording for
  it), and the report renders the delta's `delta_confidence` when
  it is `low`, in plain words next to the headline.
- **User seat.** "Strong where it counts: distributed systems —
  proven, '14 services' story. Two evidence gaps: Kubernetes (you
  list it, no proof — answer one grill question to close), cost
  optimisation (win exists, no number). One skill gap: Go — not in
  your history; this posting leans on it. Verdict: apply after
  closing the Kubernetes proof, or skip."
- **Inputs/outputs.** In: B2 classification + `score_job()` result.
  Out: rendered report (CLI + web UI + dashboard card), and the
  machine-readable delta stored per job for trending (B5).
  **Delta invalidation (owned here; B5 consumes it).** Every
  stored delta is stamped with the ledger version it was computed
  against. Any ledger write — an A3 approval, a supersession, a
  proof deletion, a dispute outcome — increments the ledger
  version, and every stored delta stamped with an older version
  immediately enters the visible state **"delta stale"**: the
  report shows the stale banner with its as-of version and a
  "recompute" action, and the headline binary and veto are shown
  as as-of that version, never as current. Recompute is a fresh
  B2/B3 run against the stored posting and the current ledger;
  the new delta replaces the stored one and the old one moves to
  the delta's history with its version stamp. Nothing recomputes
  silently in the background and presents itself as fresh.
- **Reuses.** `radar.py` rendering, `skill_gaps.py: gap_plan()`
  (lesson/project mapping), `near_miss.py` queue for the 50–59 band.
  New: report assembly + delta persistence.
- **Edge cases.** Job with zero extractable requirements (report says
  so and shows decode only — never a fabricated delta); delta where
  everything is supported (report leads with that; before D1
  ships, it points to prep from the delta itself with no reference
  to D1, and once D1 ships it links to D1 — the wording is
  phase-aware, never a pointer to a feature that does not exist
  yet); score and delta disagree (high score, one contested
  must-have requirement — contested wins the headline, per B4's
  rule that a contested must-have vetoes on its own).
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
  - Invalidation: after a fixture ledger write (an A3 approval for
    a different job), every previously stored delta for other jobs
    renders with the "delta stale" banner and its as-of version;
    recomputing one clears its banner, replaces its
    classifications with the current-ledger result, and keeps the
    prior delta in history with its version stamp.
  - Score-impact ordering (C2-14): the worked example in the
    score-impact definition above is a fixture — the report's
    gap list for that delta is exactly R2, R1, R4, R6 in that
    sequence (impacts 16.67, 16.67, 15, 0, with the R2/R1 tie
    broken on severity), and a build that orders the same delta
    differently, or leaves the no-axis requirement's impact
    undefined instead of 0, fails.

### B4. Veto with a path (do-not-apply, specified)

- **What it does.** Formalizes today's score veto into the product
  answer the brief promises. Tree note, stated once and plainly:
  the score veto (`score_job()` veto < 60) exists in both trees;
  the insufficient-signal rule exists **only in the live tree**
  (`job-apply-mcp/match.py`: `_INSUFFICIENT_SIGNAL_AXES = 3`,
  `signal_veto` at the veto line) — in the tree these documents
  ship in, `score_job()` vetoes on score alone
  (`wt-veto-differentiator/match.py`). Building B4 in the build
  tree therefore includes landing the insufficient-signal rule
  there and fixturing it there; no text in this package may call
  it shipped in the build tree until that lands.
- **The headline mapping (owned here; B2, B3, B6 and the brief's
  headline all cite this rule and no other).** The mapping has
  two parts, and only the second part ever produces a headline.
  *Part 1 — what each classification means for its own
  requirement* (a per-requirement gloss, never a job headline):
  - **supported** → neither word; the requirement is met.
  - **evidence gap** → the requirement is *unproven* (a claim is
    on record; its proof is missing, of the wrong kind for the
    requirement, alias-only, not quotable, or stale under A1's
    policy).
  - **skill gap** → the requirement is *unqualified (for this
    posting as written)* (nothing on record meets the
    requirement; the qualifier is part of the answer, never
    dropped in rendering).
  - **contested** → the requirement is *unqualified (for this
    posting as written)* (the record affirmatively contradicts
    the requirement).
  *Part 2 — the headline production rule (C-03 — the ONE rule;
  every headline in the product, the brief included, is
  produced by this rule and by nothing else).* **When, and only
  when, a veto fires, the job's headline word is the word of
  the most severe classification present among the posting's
  must-have requirements, in the order contested > skill gap >
  evidence gap**: any contested or skill-gap must-have makes
  the headline *unqualified (for this posting as written)*; a
  vetoed job whose must-haves carry only evidence gaps (and
  supported requirements) headlines *unproven*.
  **Veto classes never assign a headline word.** The trigger
  classes named below (contested, skill-gap heavy, thin
  evidence) name *why a veto fired*; they are recorded and
  shown as reasons, and none of them — thin evidence included —
  maps to a headline word directly. A thin-evidence veto over a
  delta that also contains a skill-gap must-have headlines
  *unqualified (for this posting as written)*, because the
  presence rule, not the veto class, decides. Gaps on preferred
  requirements are listed in the report but never decide the
  headline word. A job with no veto gets no headline word — the
  report leads with its supported strengths instead, even if a
  must-have carries a skill gap that fired no trigger. A veto
  that fires on the score rule or the insufficient-signal rule
  alone, with every must-have supported, also gets no headline
  word: the banner states the score or missing-facts reason in
  plain words, because the binary is an answer about
  requirements and is never forced onto an event that is not
  one. Every statement of the headline anywhere in the product
  must be producible by this rule from the job's stored delta;
  a rendering that cannot be so produced is a defect.
  *Worked fixtures (C-03, frozen in the acceptance criteria):*
  (i) M=6, supported=2, E=3, S=1, C=0, score ≥ 60 — the only
  trigger that fires is thin evidence, and the headline is
  *unqualified (for this posting as written)*, because a
  skill-gap must-have is present; (ii) the same delta with no
  veto trigger firing at all (e.g. M=10, supported=9, S=1,
  score 85) gets **no headline word**, however its one skill
  gap glosses per-requirement.
- **The veto trigger (measurable; two builders implementing this
  text produce the same veto).** Notation: for one job, let
  **M** = the number of must-have requirements (B1
  `requirement_level`), and among them **S** = skill-gap count,
  **E** = evidence-gap count, **C** = contested count. A veto
  fires when **any** of these holds:
  1. the existing score rule fires (score < 60), or
  2. **C ≥ 1** — a contested must-have vetoes on its own, at any
     score (this is the one rule for contested; every other
     mention in this package agrees with it, including B3's
     "contested wins the headline"), or
  3. the delta is **skill-gap heavy**: **S ≥ 2**, or **S ≥ 1 and
     S ÷ M ≥ 0.40**, or
  4. the evidence is **thin**: supported must-haves ÷ M < 0.50
     **and** E ≥ 2, or the insufficient-signal rule fires.
     **The insufficient-signal rule — one axis list, stated
     here once (C-01); every other mention in this package
     cites this paragraph and restates nothing.** What is
     adopted from the live-tree `match.py` rule is stated
     exactly (C2-03): the rule itself — the rule fires when
     **3 or more of the 5 axes** are scored on their neutral
     ("unknown") defaults — and the axis set: the five fit
     axes are **skills, seniority, salary, location, and
     recency**. The per-axis unknown tests are the live
     code's tests, pinned here so no reader has to re-derive
     them from the code; the short gloss that used to stand
     here ("an axis is unknown when the fact it scores is
     missing") is a summary of this list, never a substitute
     for it, and where the two differ this list governs:
     - **skills** is unknown when no skill keywords are
       detected in the posting (it then scores half its
       weight);
     - **seniority** is unknown when no seniority marker is
       detected in the posting's title — and only then: a
       missing *profile* seniority does **not** make the axis
       unknown (the scoring defaults the profile level to
       "mid" when unset, and the axis is scored on the
       detected title level against that default);
     - **salary** is unknown when no salary floor is set in
       preferences, or a floor is set but no salary hint is
       parsed from the posting;
     - **location** is unknown **only in the fully-neutral
       branch**: no location preferences are set **and** the
       posting is not a remote posting. A remote posting
       scores location on a real value (13.0 at static
       weights) and the axis is known, even with no location
       preferences at all; preferences set in either
       direction (remote-only, or a wanted-locations list)
       likewise make the axis known, scored on the match or
       mismatch;
     - **recency** is unknown when the posting's date cannot
       be determined from the posting.
     **Salary and recency count**, exactly as in the
     imported rule; there is no carve-out for them, here or in
     B6. B6's word *unclassified* is a different, rendering-only
     fact (an axis carries no requirement classification); an
     unclassified axis scored on a default is still an unknown
     axis for this rule, and a classified axis scored on a real
     value is not.
     **What "unknown" means, by side (no narrower gloss is
     correct):** an axis is unknown when the fact **it scores**
     is missing, wherever that fact lives — and under the
     pinned tests above most of those facts are **posting-side**
     (no skill keywords detected in the posting, no seniority
     marker in the posting's title, no salary hint parsed from
     the posting, no determinable posting date); only the
     salary floor and the location preferences are profile-side
     facts in this list. Any summary of this rule — in any
     document or surface — that glosses "unknown" as a missing
     **profile** fact only misstates the rule and does not
     conform to this section.
  A veto names **every** class that applies, checked in the order
  contested → skill-gap heavy → thin evidence, with contested
  first. The classes are the trigger conditions above:
  *contested* (condition 2), *skill-gap heavy* (condition 3),
  *thin evidence* (condition 4; an insufficient-signal veto is
  recorded under this class with its cause marked "insufficient
  signal", and its change-my-answer names **each missing fact
  that made an axis unknown, by side**: a missing profile fact
  routes to A2 / profile completion, as below; a missing
  posting fact (no salary hint, no posting date) is named as a
  posting fact — no grill can supply it, and the answer says
  what would change it: a fuller posting text carrying that
  fact, or a re-score once the fact exists). Where M = 0 (no must-haves extracted) only the
  score and insufficient-signal rules can fire. Worked edges,
  frozen as fixtures below: S=1, M=4 is **not** skill-gap heavy
  (1 ÷ 4 = 0.25); S=2, M=6 **is** (S ≥ 2); S=1, M=2 **is**
  (1 ÷ 2 = 0.50 ≥ 0.40); supported 2 of 5 must-haves with E=3
  **is** thin evidence (0.40 < 0.50, E ≥ 2); supported 2 of 5
  with E=1 is **not**. **C-01 worked fixture, frozen (per-axis
  conditions pinned, C2-03):** a job
  whose skills axis scores on a real value (skill keywords
  detected in the posting) and whose seniority axis scores
  on a real value (a seniority marker detected in its
  title), while
  salary (no salary floor set — a profile fact), recency (no
  determinable posting date — a posting fact), and location
  (**no location preferences set, and the posting is not a
  remote posting** — the fully-neutral branch, stated
  explicitly because a remote posting would score location
  on a real value and the axis would be known) all score on their neutral
  defaults has **3 unknown axes under the one axis list
  above, salary and recency included**, so the
  insufficient-signal rule fires and the veto is recorded as
  thin evidence with cause "insufficient signal". No reading
  of this package produces any other result for that job.
  Two pinning cells ride with it: the same job re-presented
  as a **remote** posting has location known, only 2 unknown
  axes, and the rule does **not** fire; and a job whose title
  carries no seniority marker counts seniority as unknown
  whether or not the profile sets a seniority level, while a
  job with a title marker and no profile seniority set does
  **not** count seniority as unknown.
  **Disambiguation rule:** a hard
  requirement the user simply lacks is a skill gap, not contested —
  contested requires the record to affirmatively contradict the
  requirement (e.g. years on record below a stated minimum,
  authorization on record conflicting with a stated requirement).
- **What would change the answer — for every class, contested
  included (no class is exempt).** Each veto states, per deciding
  requirement, the named gap or proof that would change it:
  - evidence gap → attach the named proof, or re-verify the stale
    proof (routes to A2/A3);
  - skill gap → the `gap_plan()` path (project / course / time)
    that would put the skill on record, stated as a path with a
    next step, never as a bare no; **where `gap_plan()` has no
    plan for that gap (C-16 — B3's no-plan case), the statement
    uses B3's fallback in the veto's own text**: an explicit
    "no plan available" plus the smallest next step the user
    can take toward putting the skill on record — a veto-deciding
    gap never ships without that fallback statement;
  - contested → one of two named paths: **prove it** (the record
    is wrong or out of date — supply the correcting evidence
    through B2's dispute flow, path 1 or 2, and the requirement
    re-classifies) or **disprove it** (the posting was misread or
    the requirement is not a must-have as written — dispute flow
    path 3 corrects the extraction or level, or the posting
    itself changes, and the requirement re-classifies); where
    neither can happen today (e.g. years that only time adds),
    the answer says that in plain words and names the date or
    condition at which it changes.
  - score-only veto (trigger condition 1 alone — score < 60,
    every must-have supported) → the score statement itself:
    the axis or axes whose movement would lift the score to
    the bar (60), as the fit-score breakdown shows them —
    which axis, and the movement on it that reaches the bar.
    No class-based path is invented for it, because no
    requirement is unmet; the banner states the score reason
    in plain words, and this statement is its
    change-my-answer.
  The user can always proceed anyway; the veto is
  advice with a record, not a lock (the existing near-miss human
  verdict flow is the precedent). A classification the user
  believes is wrong is handled by B2's dispute flow, which is
  distinct from proceeding anyway: a dispute corrects the record,
  an override accepts the record and proceeds regardless, and the
  two are counted separately.
- **User seat.** A veto banner on the delta report + the verdict
  written to the verdict record with its class and reasons.
- **Inputs/outputs.** In: B2/B3 + score. Out: veto class, reasons,
  change-my-answer conditions; recorded via
  `governance/adapter.py: record_application_verdict()`.
- **User-visible verdict record.** B4 also owns the per-job verdict
  history surface (delta report + a verdict list in CLI/web): the
  unified, inspectable record the brief lists as claim 7b. Stated
  against today's code: verdict recording today is conditional on
  the governance framework checkout — absent the framework, the
  existing recorder reports not-recorded and the apply path's
  recorder is a no-op, and the per-application experiment log is
  not written by the apply path at all. B4 changes the ownership:
  **the local record is the canonical store.** Every verdict,
  override, and dispute outcome is written to the local record
  first, in all configurations; the framework log, when present,
  receives a pointer entry only (record id, job id, class,
  timestamp — no reasons text, no proof text), so the substance
  lives in exactly one deletable place. A recording failure of
  either store is shown to the user — never silent (the Phase 2
  gate tests the framework-absent case).
- **Export, delete, and the record's own description (brief §7,
  item 5 — requirements, not current facts).** The record surface
  ships with: one-action export of the full record (JSON + readable
  text — subject to A1's Tier 2 export exclusion: reasons resting
  on Tier 2 facts export with the Tier 2 values removed and the
  removal marked, unless the user makes A1's explicit inclusion
  act), delete with confirmation, and an in-product
  description — what the record holds, where it lives, that it
  is never transmitted to author infrastructure
  (Rule 2), and how to export/delete it — shown where the
  record is first encountered. **Delete reaches the stores, not
  just the surface:** deleting the record deletes its entries
  from the local canonical store and deletes the pointer entries
  from the framework log and any per-application log that
  references them; the acceptance test inspects those stores
  directly. **Deletion disclosure, in the same breath as the
  promise (D-09/D-15):** the in-product description and the
  delete confirmation state, before the user confirms, both
  limits together — (1) copies the user already exported
  outside the product cannot be recalled; and (2) deleting
  *this record* leaves derivative content elsewhere in the
  product exactly as the lifecycle table states for each store
  (a ledger or proof deletion, by contrast, flags derivatives
  and offers the delete-them-too act specified there — the two
  deletions are never described with each other's wording);
  and (3) the deletion itself leaves one residue: it is noted
  in the local work log as date + record-id hash only — no
  content — that note is retained under the work log's own
  retention rule (rolling 12 months, lifecycle table) or until
  the user deletes the work log, which is itself user-deletable
  under that table. A description or confirmation that omits
  the work-log residue does not meet this spec.
- **Overturn rate (brief §9's signature metric).** The record
  computes, from `near_miss.py` resolutions and recorded overrides (each override entry states whether the veto's named change-my-answer condition had been met at override time — the brief §9 kill criterion reads this),
  the share of reviewed vetoes the user overturned, shown on the
  record surface with its sample size ("overturned 2 of 9 reviewed —
  small sample" below 10). No rate is displayed without its count.
  Dispute outcomes (B2) are reported next to it as their own count
  and never enter this rate. **"Routinely overridden" is defined
  here for every consumer, including the brief §9 kill criterion:**
  the routine-override flag is raised when, over at least 10
  reviewed vetoes, more than 1 in 3 were overturned **without** the
  named change-my-answer condition having been met at override
  time. Below 10 reviewed vetoes the flag cannot be raised,
  whatever the share.
  **"Reviewed", defined producibly (the denominator is a set
  of veto records, not an impression).** A veto is **reviewed**
  exactly when the verdict record holds at least one *review
  event* for that veto's record id, where a review event is
  exactly one of: (a) a `near_miss.py` resolution for that veto
  (the queue covers the 50–59 band; a resolution is a review
  event only for a veto that entered that queue); (b) a
  recorded override for that veto; or (c) a **reviewed-upheld
  mark** — the record surface offers, for **every** veto it
  shows at any score and in any class, a "mark reviewed —
  upheld" act, and using it writes a review event (veto record
  id, timestamp, disposition upheld) to the verdict record.
  Clause (c) is what makes a veto outside the near-miss band —
  for example a contested veto at score 80 that the user read
  and obeyed — capable of entering the denominator at all: it
  enters when, and only when, the user marks it reviewed on
  the record surface. The denominator is the number of
  **distinct veto record ids** holding at least one review
  event: a veto carrying both a near-miss resolution and an
  override, or an override and an upheld mark, is **one**
  denominator entry, never two — the sources are unioned by
  veto id, not added. The numerator is the number of those
  distinct vetoes that hold a recorded override; for the
  routine-override flag, the numerator is the number of those
  vetoes whose recorded override states the named
  change-my-answer condition had **not** been met at override
  time (a veto holds at most one override record for this
  computation — a second override of the same veto updates
  that veto's entry, it does not add a second one). A veto
  with no review event of any of the three kinds is **not**
  reviewed, however it was displayed. *Worked fixture (frozen
  in the acceptance criteria):* 12 classified vetoes; 4 carry
  recorded overrides, each stating the condition was not met;
  the other 8 are contested vetoes at scores above 60, outside
  the near-miss band, each carrying a reviewed-upheld mark.
  Reviewed = 12 distinct vetoes, overturned-without-condition
  = 4; 4 of 12 is 1 in 3, which is **not** more than 1 in 3 —
  the routine-override flag does **not** fire. A build that
  counts only the recorded-event vetoes (4 of 4) or that
  double-counts a veto holding two event kinds fails this
  fixture.
- **Veto-moment return measure — the 14-day return (B-10;
  named here; roadmap initiative 2.8 carries it in its scope,
  acceptance, and the Phase 2 E2E).** This feature, which issues
  the first classified veto, also measures what the brief's
  §8/§9 claim needs: **whether the user returns within 14 days
  of a first classified veto.** The measure is counted locally
  only, from local records, and is never transmitted. The
  verdict record stores, for the first classified veto this
  install issues, `first_veto_at`; the measure then reads the
  local session record for the first
  session of any type that starts **after** the session in
  which that veto was issued and **within 14 days** of
  `first_veto_at`, and records its date as `returned_at`.
  **Instrument and dependency, stated plainly (C2-07,
  conformed to the roadmap):** E1's session-type log is a
  Phase 5 build (initiative 5.2) and does **not** exist when
  this measure ships in Phase 2 (initiative 2.8). The measure
  therefore does not wait for it: 2.8 ships an **interim
  instrument** — a minimal local session marker that records
  a timestamp for each session start, nothing more — and the
  measure reads `first_veto_at` plus that marker. Initiative
  2.8 declares its dependency on E1's session-type log
  (Phase 5, 5.2) in the roadmap, and 5.2 is the
  **migration and reconciliation** of the interim marker
  into E1's session-type log — not the log's first build for
  this measure: when 5.2 lands, marker history migrates into
  the log, the measure reads the log from then on, and a
  return already recorded from the marker is never
  recomputed or lost in the migration. No text in this
  feature may imply the session-type log exists before 5.2.
  **The marker is a store in its own right, with its own
  lifecycle row** (the interim session marker row in the
  data-lifecycle table: retention until 5.2 migration or user
  deletion, export with the recap data, and the stated
  consequence of deleting it for this measure) — that row
  governs the marker from the day 2.8 ships it, and the
  roadmap's reference to a retention rule "from the table"
  points at that row. The
  record surface shows exactly one of three states for the
  measure: "returned on day N" (N = whole days from the veto
  to that session, 1–14), "window still open — day N of 14",
  or, once day 14 passes with no such session, "did not return
  within 14 days". Only the *first* classified veto starts the
  measure; later vetoes do not restart it, overrides and
  disputes do not change it, and a veto issued by the score or
  insufficient-signal rules alone, with no classified
  (requirement-based) veto class, does not start it.
- **Reuses.** `match.py` veto + `veto_reason`, `near_miss.py: scan()` /
  `resolve()` (human override with verdict), experiment ledger entry.
- **Edge cases.** User overrides a contested veto (allowed; the
  override and the contested item are both recorded; tailoring still
  cannot invent the missing qualification — C3); veto on a job the
  user fed themselves via BYOL (same treatment — no friendlier math
  for user-fed jobs); insufficient-signal veto (unknown axes)
  explains which missing facts caused it, by side: profile-side
  facts route to A2 / profile completion; posting-side facts
  (a missing salary hint or posting date) are named as posting
  facts, with the fuller-posting change that would resolve them.
- **Acceptance criteria.**
  - Each veto class has a fixture job that produces it, with reasons
    matching the classification that fed it; an insufficient-signal
    fixture (3+ unknown axes) produces a thin-evidence veto marked
    "insufficient signal" naming the missing facts by side. The
    **C-01 worked fixture** (skills and seniority known; salary,
    recency, and location on neutral defaults) is one of these
    fixture jobs and must produce that veto — a build that
    excludes salary or recency from the count fails it. Its two
    pinning cells (C2-03) are asserted with it: the remote
    re-presentation of the same job produces **no**
    insufficient-signal veto (location known, 2 unknown axes),
    and the seniority cells produce their stated counts
    (no title marker → seniority unknown regardless of the
    profile level; title marker with no profile level set →
    seniority known).
  - Trigger edges: the five worked edges in the trigger definition
    (S=1/M=4 not heavy; S=2/M=6 heavy; S=1/M=2 heavy; supported
    2/5 with E=3 thin; supported 2/5 with E=1 not thin) each have
    a fixture job, and the implementation reproduces the stated
    verdict for each; a fixture with one contested must-have and
    a score above 60 vetoes (contested vetoes on its own).
  - Headline mapping: for each fixture job, the rendered headline
    word equals the headline production rule's output from that
    job's stored delta — including a mixed fixture (evidence gap
    + skill-gap must-haves → *unqualified (for this posting as
    written)*) and an evidence-gaps-only fixture (→ *unproven*).
    The two C-03 worked fixtures are asserted explicitly: (i)
    the thin-evidence-only trigger over M=6, supported=2, E=3,
    S=1 renders *unqualified (for this posting as written)* —
    a build that maps the thin-evidence veto class to a word
    fails it; (ii) the no-veto fixture (M=10, supported=9, S=1,
    score 85) renders **no headline word**.
  - Overriding never removes the original veto from the record.
  - "What would change the answer" is present and specific (named
    gaps/proofs) for **every** class — contested included, naming
    its prove-it or disprove-it path; and the no-plan case
    (C-16): a fixture whose veto-deciding skill gap has no
    `gap_plan()` entry renders "no plan available" plus the
    smallest next step, not a bare refusal and not an empty
    change-my-answer.
  - Veto-moment return (B-10): with the fixture clock, a first
    classified veto on day 0 and a local session on day 9
    produce the state "returned on day 9"; a second fixture
    with no session by day 14 produces "did not return within
    14 days" only after day 14 closes (before that it reads
    "window still open"); a score-only veto in a third fixture
    starts no measure.
  - Export produces the complete record; delete removes it from
    the local store **and** its pointer entries from the framework
    log and per-application log (asserted by inspecting those
    stores, not only the surface), and the surface then shows the
    empty state with the in-product
    description — both exercised in the Phase 2 E2E.
  - The overturn rate on the fixture record (seeded vetoes +
    resolutions) equals the hand-computed rate, count displayed
    alongside; a fixture with 0 reviewed vetoes shows no rate.
    The worked fixture in the overturn-rate section is asserted
    as written: 12 vetoes (4 overrides without the condition
    met, 8 reviewed-upheld marks on above-60 contested vetoes)
    compute reviewed = 12, overturned-without-condition = 4,
    and the routine-override flag does **not** fire; a second
    fixture cell gives one veto both a near-miss resolution and
    an override and asserts it enters the denominator once.

### B5. Delta trending (the gap, over time)

- **What it does.** Stores each delta (B3) and rolls them up per role
  family — **target role family, as frozen in A4** (never the
  calibration family from `calibration.py: role_family()`):
  how the user's evidence-gap count, skill-gap count, and
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
  when the approval lands **and the proof is still present and
  not stale at the window's end**, whether or not a new posting was
  evaluated in that family). The brief §9 kill criterion reads
  this measure. **Zero denominator, stated:** when no evidence
  gaps are open in a family at a window's start (denominator
  0) — or, for the kill criterion's per-user form, in the
  user's whole record — the rate is **not a percentage at
  all**: it is reported as "no data — no gaps open at window
  start", with its counts shown as 0 of 0. It is never
  reported as 0%, never as 100%, and a no-data window cannot
  fire, satisfy, or count toward the kill criterion's
  "proof-closing rate near zero" reading — that reading
  applies only to windows whose denominator is at least 1,
  and the window's sample size is shown wherever the rate is
  shown, as with every rate in this package.
- **Ledger-version discipline (B3's invalidation, consumed here).**
  Trend roll-ups group deltas by the ledger version they were
  computed against and never mix versions in one trend line: the
  headline trend for a family uses current-version deltas only,
  stale deltas (B3) are shown as their own count ("4 deltas stale
  — recompute to refresh this trend"), and a family whose deltas
  are all stale shows counts with no trend line. Recomputing a
  stale delta moves it into the current-version group.
- **User seat.** "Staff backend roles, 90 days: evidence gaps 9 → 3;
  one skill gap keeps recurring — Go, in 6 of 11 postings. Closing it
  is your highest-value project this quarter."
- **Inputs/outputs.** In: persisted deltas + `outcomes.jsonl` + A3's proposal log (the approval record — the proof-closing rate joins gap identity from the delta store to the closing approval event). Out:
  trend aggregates per role family; recurring-gap ranking; and the
  per-user outcomes figure brief §9 is judged by — interviews per
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
  - A fixture history spanning two ledger versions renders two
    version groups, not one mixed trend; after a ledger write,
    the family's headline trend excludes the now-stale deltas and
    shows the stale count.
  - A family with 2 deltas renders counts only, no trend claim.
  - Recurring-gap ranking matches `analyze_gaps()` output on the same
    job set (one engine, two views — no divergent math).
  - Proof-closing rate: on the fixture window (gaps open at start,
    closings in the fixture proposal log), the computed rate
    equals the spec owner's hand-computed rate — including a
    closing whose approval landed with no new posting evaluated
    in the family. A second fixture window with **zero** gaps
    open at its start renders "no data — no gaps open at window
    start" (0 of 0), not 0% and not 100%, and the kill
    criterion's near-zero reading does not fire on it.
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
  the unclassified treatment, below.) **Axis mapping:** the skills, seniority, and
  location axes carry requirement classifications and take the
  colour rule; the **salary and recency axes have no requirement
  classification** (a preference comparison and a posting-age
  fact, not evidence about the user) and always render in the
  unclassified treatment — grey, labelled "not evidence-scored" —
  never borrowing a
  colour they did not earn. Terminology, stated once (C-11):
  B6's axes are **unclassified**, a rendering fact about axes
  with no requirement classification; it is **not** B4's
  "unknown", which means a fit axis scored on a neutral default
  because the fact it scores is missing. The two facts are
  independent, and this feature conforms to B4's one axis list
  (C-01): salary and recency render unclassified in every case,
  **and** when either is scored on a neutral default it counts
  toward B4's insufficient-signal rule exactly as B4 states —
  unclassified governs colour only, never counting. The word
  "unknown" appears in this feature only in B4's sense.
  **Precedence** on a classified axis
  carrying several classes: contested > skill gap > evidence gap
  > supported; an axis carrying both classified requirements and
  data with no classification shows
  its worst classified colour and lists the unclassified part in its state
  words.
- **Reuses.** `radar.py: normalize_components()` / `radar_svg()`,
  site demo `site/src/demos/radar.tsx` (both updated to one spec).
- **Edge cases.** Axis whose underlying data is missing (grey,
  labelled with its state word — never green by default);
  colour-blind safety: colour never carries
  meaning alone — each axis also shows its state word.
- **Acceptance criteria.**
  - Fixture score sets render the documented colour per axis in both
    `radar.py` SVG and the site demo — including the salary and
    recency axes rendering grey / "not evidence-scored" in every
    fixture. Rendering and counting are asserted separately: the
    C-01 fixture job (salary, recency, and location on neutral
    defaults) still renders salary and recency grey, **and** its
    B4 result is the insufficient-signal veto, with all three
    axes counted under B4's one axis list.
  - Every axis label includes its state in text.
  - Demo, stage 1 (before B4 lands): a scripted visitor run answers
    the fixture grill, receives a refusal on the unqualified
    fixture path — "unqualified fixture path" means the fixture
    profile/posting pair for which B4's headline production rule
    (most severe must-have class present, once a veto fires)
    produces *unqualified (for this posting as written)*;
    at this stage the refusal shown is the existing score veto,
    and the demo copy may not call it a classified veto — and sees
    the fixture delta report; no visitor input is persisted
    (asserted in the demo's browser test).
  - Demo, stage 2 (once B4 lands, in the same phase, before the
    Phase 2 gate): the same run receives the B4 classified veto
    with its headline word and change-my-answer; the gate tests
    this stage, and no public description of the demo as showing
    the classified refusal may run before it.
- **Demo surfaces (built inside roadmap 2.7).** The project site's
  interactive demo — the brief §4 acquisition channel: a visitor
  answers a short grill (the four real question kinds only)
  against a fixture profile, can be refused, and sees the fixture
  delta report (B3 rendering). Fixture data only; nothing a
  visitor types is stored; no install, no account. **Hosted
  posture, stated explicitly (a pre-install visitor is owed it):**
  visitor input is processed only to render that visitor's run
  and is never written to any store; the hosting configuration
  logs no request bodies for the demo route; analytics events for
  the demo carry event names and counts only, never typed
  content; error reporting for the demo route sends stack traces
  with input fields redacted. **Access logs, processors, and
  retention (D-14):** ordinary host/CDN access logs for the demo
  route do exist and do hold visitor metadata (IP address, user
  agent, timestamps) — the posture states that plainly rather
  than implying no log exists. The hosting configuration for
  the demo route sets access-log retention to the shortest
  period the host offers, and access-log entries are never used
  for analytics, profiling, or any purpose beyond operating and
  securing the site. Any analytics or error-reporting processor
  for the demo is named, with what it receives, in the demo
  page's hosted-posture statement before the demo ships: if
  either is a third-party service, the statement names the
  service and states that it receives event names and counts
  only (analytics) or stack traces with input fields redacted —
  including values carried in a URL or in local variables —
  (error reporting), and the retention that service applies;
  if no third-party processor is used, the statement says so.
  No processor identity, access-log setting, or retention period
  is left unstated in that statement. The demo's browser test asserts
  non-persistence, and a configuration check in the same test run
  asserts the log/analytics/error-reporting settings above,
  including the access-log retention and the named processors.

---

## C. Tailoring service

### C1. Grill-fed tailoring (make the documented claim true)

- **What it does.** Wires `grill.py: get_qa_pairs()` into the
  tailoring path: when a user starts tailoring for a job with a
  completed grill, the answers join the profile facts as tailoring
  inputs — visibly, as their own provenance class (`grill:<job_id>`),
  and proposed to the ledger via A3 at the same time.
  **Precondition this feature must fix, stated against today's
  code:** a grill session created by the apply gate starts from a
  stripped job record (empty description, no requirements), and
  question generation reads only the posting text fields — on
  that path no gap or quantify questions can be generated at all,
  only logistics and motivation. C1's flow therefore loads the
  full posting record before any session it consumes is treated
  as complete, and a session created from a stripped record is
  labelled partial wherever it is shown.
  **Tailoring-session proposals (this feature owns the
  `tailor:<job_id>` source in A1's list):** a fact the user first
  states inside a tailoring session — in a hand edit or a session
  note — becomes an A3 proposal with source `tailor:<job_id>`. It
  is not used as a proven fact in that session's artefact; C3's
  rule governs it like any other unapproved claim.
  **Session-input distinction:** the per-job answers are session
  inputs to this job's tailoring, consumed in the flow the user
  is sitting in — they are not profile facts, and they enter the
  profile only through A3 approval.
  **Fallback for a descoped provenance surface (the fallback
  roadmap Fork 0.6 Outcome B states is stated in feature-sets —
  it is stated here, for this feature).** This feature's
  primary rendering of the grill provenance class is on the
  provenance surface wired by roadmap initiative 0.6. If that
  initiative ends in Fork 0.6 Outcome B (provenance formally
  descoped), this feature renders grill provenance **without
  that surface, as follows, and in no other improvised form —
  the same fallback roadmap Fork 0.6 Outcome B states, in the
  same terms:** (i) the C2 tailoring review shows the grill
  provenance class as a **per-line source list** — the "from
  your grill answers" list: each answer used, the job it
  came from (`grill:<job_id>`), and its proof state — in place
  of any per-line provenance rendering; (ii) the tailored
  artefact's own session record carries the same list, so the
  provenance class survives in the record even though no
  surface renders it per line; (iii) no acceptance assertion
  for this feature requires per-line rendering under the
  descope, and any assertion that does require the wired
  surface stays **built, gate pending** until the separately
  gated wiring initiative Fork 0.6 Outcome B provides for
  lands, or that trigger's amendment re-scopes this feature
  to this fallback as its final form; and (iv) the
  session-input distinction above is unchanged — the fallback
  changes where provenance is shown, never what an answer is.
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
  half-answered grill (only answered pairs are used, listed as such);
  session created from a stripped job record (labelled partial;
  tailoring proceeds profile-only for the missing question kinds
  and says so).
- **Acceptance criteria.**
  - Fixture job + completed grill: the tailored output contains the
    grill-sourced line with `grill:<job_id>` provenance, and the base
    profile-only run does not.
  - `docs/grill.md`'s claim becomes testable-true: an E2E test runs
    grill → tailor and asserts the answer appears (roadmap gate).
  - A session that began at the apply gate for a fixture job with
    posting keywords yields gap/quantify questions once the full
    posting is loaded — the stripped-record session alone is
    asserted partial and is never presented as the full grill.

### C2. Diff-approval flow, completed

- **What it does.** Builds one canonical flow for every tailored
  artefact — resume and cover letter: view diff → per-line provenance on hover/tap → approve all
  or per section → approved version is the only version downstream
  steps (packet, apply handoff) can use. Unapproved edits expire with
  the session, never leak into a later job's base. **Artefact
  sources include the resume builder (D2-08):** a draft produced
  by `resume_builder.py` from the profile is an artefact entering
  this flow like any other — it has no finished-file emission of
  its own outside this flow (C3's artefact-path inventory, path
  4, states the gate behaviour; roadmap initiative 3.3 builds
  the wiring).
  **Present state, corrected (this is first surfacing and repair,
  not completion of a working flow).** The diff ships and is wired
  in the web UI (both trees). Per-line provenance does **not**
  ship: `tailor_with_provenance()` exists in `tailor.py` but has
  no caller in any core surface in either tree — its only callers
  are unwired i05 code (`initiatives/i05/packet.py`,
  `initiatives/i05/studio.py`) and tests; wiring it into the
  review surface is new work in this feature. The approved-variant
  save is **broken**, not shipped: the store function
  `save_approved_variant(job_id, resume_md, cover_letter)` exists,
  but its only non-test caller passes a result dict and a job dict
  against that signature and then treats the returned path as a
  dict (`dashboard.py`), so no working surface can put an approved
  variant on record today; repairing that caller and adding the
  save to the review flow is new work in this feature. The fuller
  review flow in unwired i05 is reference material, as before.
  Provenance completeness, also corrected: the current statement
  map skips headings, the name line, lines containing `|`, and
  date lines, and assigns untraced lines a `profile:base` fallback
  that can assert a source the code did not establish. Under this
  flow, a line is either traced to a named source or explicitly
  tagged `untraced`; no line may carry a fallback-assumed source,
  and the review shows the untraced count.
- **User seat.** One review screen per job; approving is a single
  deliberate act; the approved artefact carries its approval stamp
  (when, which ledger version it was built from).
- **Reuses.** `tailor.py: tailor_with_diff()` / `resume_diff()` /
  `save_approved_variant()`, `cover_letters.py: approve_letter()`,
  `initiatives/i05/diff_explain.py: explain_resume_diff()` /
  `mark_reviewed()`, `initiatives/i05/versions.py: approve_version()` /
  `trace_report()`.
- **Handoff is a fresh human act (approval is not handoff).**
  Approval happens at creation time and stamps the artefact;
  **packet assembly, apply handoff, and export each require their
  own fresh human act** — a distinct command or confirm in a live
  session at the moment of the handoff, never implied by the
  earlier approval, never performed by a scheduler, another
  feature, or a stored setting. What "apply handoff" does,
  mechanically: (1) the user, in session, selects the approved
  artefact and invokes handoff; (2) the product assembles the
  packet locally and returns it to the user — a saved file in a
  location the user picks at that moment, and/or the
  application's URL opened for the user with the approved text
  available to paste or fill as a preview; (3) a handoff stamp
  (time, artefact version, ledger version, destination the user
  chose) is written to the job's record. The product never
  transmits the packet to an employer or a board, and the submit
  click in the browser remains the user's own act (claim 10). A
  stale artefact cannot be handed off until the user has seen the
  stale warning in that same session and either re-approved or
  explicitly confirmed proceeding with the stale version; that
  confirmation is part of the handoff stamp.
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
  - Handoff: invoking packet assembly, apply handoff, or export
    without a fresh in-session act fails (test drives each
    consumer with approval alone and asserts nothing is assembled,
    opened, or written); a completed handoff writes its stamp,
    and a stale artefact's handoff records the user's stale
    confirmation or does not happen.
  - Provenance: the fixture resume's heading, name, contact, and
    date lines each render as traced or `untraced` — none renders
    with a fallback-assumed source — and the review's untraced
    count equals the fixture's untraced lines.

### C3. Honesty gate, extended to all tailored output

- **What it does.** Extends the cover-letter honesty machinery to
  every tailored artefact. **One gate, one pass rule (C-09 —
  this paragraph is the unification; no other gate, check, or
  pass rule for tailored output exists in this package).**
  There is a single honesty gate: one scanner, one block, and
  the proven-only pass rule stated below. It applies at **every
  artefact path that can reach a user or a third party** —
  enumerated here in full (D2-08: this list **is** the
  coverage claim; a new artefact path may not ship until it
  is added to this list with its gate behaviour stated):
  (1) the **C2 approval flow**, where approval of a
  failing artefact is refused; (2) the **application confirm
  path** (the `apply_to_job` governance gate), where the same
  gate runs on the artefact being confirmed and a failing
  artefact blocks the confirmation; (3) **packet assembly,
  apply handoff, and export under C2**, where an artefact that
  has changed since its last passing scan is re-scanned by the
  same gate before the handoff act can complete; (4) the
  **resume-builder path** (`resume_builder.py`), which today
  emits a finished resume (Markdown, HTML, and PDF where
  possible) straight from the flat profile with no approval,
  no scan, and no labelling: under this gate the builder
  produces a **draft only**; the draft enters the C2 approval
  flow, the same scanner runs on it under the same pass rule,
  **A5's labelling applies to builder output** (the builder's
  preview, and any emitted file, label every claim with its
  proof state wherever the claim appears), and finished files
  are written only for an approved, passing draft — a
  builder-emitted resume carries its approval state and scan
  result, or it does not emit; (5) the **LinkedIn draft paths**
  (`linkedin_optimizer.py: rewrite_headline()` /
  `rewrite_about()`), whose drafts are built to be pasted onto
  a third-party platform: the same scanner and pass rule run
  on the draft before it is shown as paste-ready, A5's
  labelling applies to it in the review surface, and the
  product never posts it — pasting is the user's own act.
  Paths (1)–(3) are three installation points of one gate, not
  three gates: same scanner code, same pass rule, same failure
  wording, and no path may substitute a looser standard (in
  particular, no path passes a claim merely because profile
  text contains it). Paths (4) and (5) run that same scanner
  and that same pass rule through the C2 approval flow they
  feed. **Build vehicle (CROSS-DOC, roadmap round 3):**
  roadmap initiative **3.3** wires the resume-builder path
  (path 4) to this gate, the C2 approval flow, and A5
  labelling, with the acceptance stated there — a
  builder-emitted resume carries approval state and scan
  result, or does not emit — and a Phase 3 E2E assertion.
  Roadmap initiative 0.5's wiring is the early installation of
  exactly this gate at path (2) — as the roadmap now states,
  it wires the single C3 gate with the proven-only rule — and
  when the C2 flow lands, paths (1) and (3) run the same gate;
  0.5's installation is not additional to this one, and it
  is not retired by them; the one rule it wires is this
  package's one rule from the start — what waits, per the
  activation sequencing below, is only its blocking
  activation, not its rule.
  **Activation sequencing (C2-06, conformed to the roadmap):**
  0.5 is **built in Phase 0 with its blocking activation
  gate-pending**: the gate code, the scanner wiring, and its
  fixture tests land in Phase 0, but the confirm path does
  **not** refuse confirmations under the proven-only rule
  until the approval machinery that can create an
  `approved`-with-proof entry exists (roadmap 1.2a/1.2b,
  Phase 1) — before that machinery lands, no claim could
  pass the rule at all (A1's migration admits only
  `unverified` entries), so a blocking gate would refuse
  every letter-bearing application for reasons no user act
  could cure. In the gate-pending interval the gate runs in
  scan-and-name mode at the confirm path: it scans, names the
  lines that would fail, and records the result, without
  refusing the confirmation; blocking activation switches on
  when 1.2b lands, and 0.5's status until then is **built,
  gate pending**, in both documents.
  "Unconditional" is used in its precise sense throughout this
  package: at every one of those paths the gate runs with no
  configuration, framework checkout, or user setting able to
  disable it — and this feature claims nothing about text that
  never enters any of those paths.
  **Present state, stated against the code (both trees):** the
  standalone `honesty_scan()` exists and runs as a display and
  self-check only — nothing blocking calls it. The blocking gate
  that exists today runs a different, narrower check (framework
  veto keywords, claimed skills, claimed years) and never calls
  `honesty_scan()`; an invented metric or an invented employer in
  a cover letter therefore cannot block anything today. Wiring
  the real scan into the block is the work of this feature, not
  a description of the present.
  Two halves, sequenced honestly: **(i) the scanner** — the standalone
  `honesty_scan()` extracted to run on any artefact (resume or
  letter), with no governance-framework dependency; this half is
  independent work. **(ii) the block** — at each installation
  point above, the act that point exists to perform (approval,
  confirmation, handoff) is refused for an artefact that fails
  the pass rule below; the C2 approval installation is
  delivered with C2 (the roadmap tables it that way; C3 alone
  cannot be "done" with its headline behaviour untestable). The scan runs on the full
  tailored resume + letter at each installation point, without
  depending on the governance framework checkout being present
  (today the blocking gate silently disables itself when the
  framework is absent — audit §5).
- **The pass rule (the one rule; the headline stands or falls on
  this text).** A number, a proper noun (an employer, a product,
  a credential), or a skill presented as the user's own fact may
  pass **only** when it traces to a ledger entry in state
  `approved` with proof attached (A1's meaning of proven), or —
  for wording that is not presented as fact — it is hedged
  phrasing ("eager to develop"), which stays exempt as today and
  is labelled intent in the C2 review. Everything else blocks:
  a claim that traces only to an `unverified` entry blocks (the
  ledger having the text is not the claim being backed); a claim
  that traces only to a grill answer blocks as a proof claim —
  the answer is a session input (C1) and becomes usable as proof
  only after A3 approval with proof attached; a claim that
  traces to the posting blocks always — the posting is never a
  source for the user's claims. Failures block approval with the
  offending lines listed, and the three exits are the honest
  ones in the user seat below: attach proof and approve it
  through A3 first, reword to labelled intent, or remove the
  line. This is the rule the brief's end-state claim must match:
  the gate refuses unbacked claims, where "backed" means proven
  in A1's sense, not merely traceable.
- **User seat.** Approving a draft with an unbacked claim stops:
  "'40% cost reduction' — on record as unverified, no approved
  proof. Attach the proof and approve it, reword as intent, or
  remove the line." Three exits, all honest.
- **Reuses.** `cover_letters.py: honesty_scan()` (the scanner),
  `governance/adapter.py: check_cover_letter_honesty()` /
  `governance_gate()` (gate semantics + verdict recording — with
  the wiring correction above: the extended gate calls the
  scanner; it does not rename the narrower check),
  `assess_qualification()` thresholds behaviour on the apply path.
- **Edge cases.** Framework checkout absent (gate still runs via the
  standalone scanner; verdict recorded locally, labelled as such);
  user's own hand-edited line (scanned identically — no trusted-user
  bypass); numbers that come from the posting, not the user (always
  flagged — the posting is never a source for the user's claims).
- **Acceptance criteria.**
  - Seeded draft with one invented metric, one invented employer, one
    invented skill: all three flagged, approval blocked, lines named.
  - The same metric **added to the ledger as `unverified`** still
    blocks, with the line named and its state shown; the same
    metric with proof attached and approved through A3 passes.
  - A grill-sourced line whose answer has not been through A3
    approval with proof blocks as a proof claim; its hedged
    rewording passes and renders labelled intent in the review.
  - Gate runs with `GOVERNANCE_ROOT` unset (test asserts it).
  - One gate, both paths (C-09): the seeded invented metric
    blocks at the C2 approval installation **and** at the
    application confirm path, with the same named line and the
    same failure wording; the metric present in the profile as
    an `unverified` claim blocks at both — a build in which
    either path applies a profile-text standard fails.
  - Builder path (D2-08): a fixture profile holding one
    unverified claim and one claim with approved proof, run
    through `resume_builder.py`, emits **no finished file**
    before approval; the builder draft labels the unverified
    claim as unverified in the preview, the scanner names any
    line tracing to no ledger entry, and after approval of a
    passing draft the emitted Markdown, HTML, and PDF carry
    the approval state and scan result. The LinkedIn about
    draft for the same fixture passes through the same scanner
    with the same named failing lines before it is shown as
    paste-ready.

### C4. Cover letters from evidence

- **What it does.** Completes the shipped letter flow: each proof
  paragraph must cite a ledger entry (not just a profile bullet), the
  motivation grill answer is a first-class input (C1), and unevidenced
  requirements are phrased as interest/development — the existing
  honest fallback — now labelled in the review UI so the user sees
  which paragraphs are proof and which are intent.
  **Paragraph classes (every paragraph in a letter has exactly
  one, and the review balance counts all five):** `proof` — cites
  an approved entry that backs one of **this job's** requirements;
  `transferable` — cites an approved entry that backs a different
  requirement or role, presented in the letter's own words as
  adjacent experience, never as backing for this job's
  requirement; `intent` — interest/development phrasing for an
  unevidenced requirement, carrying no factual claim; `motivation`
  — built from the user's motivation grill answer (a C1 session
  input, labelled as such in the review; it asserts enthusiasm and
  fit in the user's own words and carries no proof claim);
  `framing` — the letter's non-claim paragraphs: the salutation,
  the sign-off, and any connective opening or closing paragraph
  that carries **no factual claim about the user, no claim about
  a requirement, and no proof claim of any kind**. `framing` is
  not a hiding place for a claim: a paragraph that asserts a
  fact about the user's work is classified by that fact's class
  above (or fails the C3 scan where the fact is untraceable),
  never as `framing` — an opening hook that cites an approved
  entry for this job is `proof`, one built from the motivation
  answer is `motivation`, and one asserting an untraced fact is
  a defect, not a framing paragraph. The balance counts
  `framing` paragraphs separately and never folds them into any
  of the four claim classes, so the counts a reviewer reads are
  counts of claim paragraphs plus an honest framing count.
- **Reuses.** `cover_letters.py: draft_cover_letter()` (`proofs[]`
  mapping), `approve_letter()`, A1 ledger citations, C3 scan.
- **Edge cases.** Job whose requirements have zero direct ledger
  proof — "zero" means zero approved entries backing **this job's**
  requirements; approved proof for other requirements may still
  exist. The letter is then drafted from intent paragraphs plus,
  where one exists, a transferable paragraph labelled as such,
  with the five-class balance shown honestly — never fabricated
  proof, and a transferable paragraph is never counted or worded
  as direct proof. User has no motivation answer (letter omits the
  paragraph rather than generating generic enthusiasm).
- **Acceptance criteria.**
  - Every proof paragraph in a generated letter resolves to an
    approved ledger entry (state `approved`) backing one of this
    job's requirements; unverified and draft entries cannot carry
    a proof or a transferable paragraph.
  - A letter for the zero-direct-proof fixture that has one
    approved entry elsewhere contains **no proof paragraph**, one
    transferable paragraph labelled as such, and its review view
    shows the five counts: 0 proof / 1 transferable / N intent /
    M motivation / K framing, with M = 0 when the fixture has no
    motivation answer and that paragraph absent, and K equal to
    the fixture letter's framing paragraphs as the fixture
    authors them (its salutation and its sign-off at minimum).
  - Exactly-one, over a whole letter: the fixture letter's full
    paragraph list — salutation, hook, body, close, and sign-off
    included — is classified paragraph by paragraph, every
    paragraph carries exactly one of the five classes, the five
    counts sum to the letter's paragraph count, and the
    salutation and sign-off classify `framing`. A build that
    leaves any paragraph unclassified, or classifies the
    salutation as `intent` to make the counts fit, fails.

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
  Every question in the plan carries its reason tag into the
  session record; an honest-framing question's answers are tagged
  **rehearsal** at capture, which D2/D3 obey: rehearsal answers
  are practice, never evidence (see D3).
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
  **Outbound-text inventory for the reused module (its runtime
  note is in scope, not only grill and notify text).**
  `mock_interview.py`'s WhatsApp deliverable carries a runtime
  note (lines 419–425 in the branch tree) framing WhatsApp as
  "the only proactive channel" and a message as sendable only
  from the WhatsApp side chat. That framing is the same
  agent-facing routing language this package retires for the
  grill: **no channel is a proactive channel in this package**,
  and a mock-session message, like every prepared item, is sent
  only on the user's act in the moment under E1's initiation
  model. The note's truthful half — that the function itself
  sent nothing — is kept; its proactive-channel framing is
  rewritten to the prepare-only / user-initiated model before
  any D1/D2 surface built on this module ships. The inventory
  that covers this text is named here because no other
  inventory in the package reaches it: it is an inventory line
  for the Slot 0 outbound-text work alongside the grill (0-C4)
  and notify (0-C3) inventories, and the brief / roadmap owners
  record it there (see the dispositions for this rework).
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
  - Outbound text: a text search over `mock_interview.py`'s
    deliverable notes and agent-facing strings finds no
    "proactive channel" framing and no side-chat-only routing
    instruction; the WhatsApp deliverable note as built states
    the prepare-only / user-initiated model and that the
    function sent nothing.

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
  pattern + published weights — the same rubric that already
  scores answers in today's mock flow, alongside
  `mock_interview.py: _score_feedback()`), `mock_interview.py: _score_feedback()`
  / `_star_coverage()` (craft heuristics stay), C3's traceability
  logic for the overclaim check, A1 ledger lookups
  (`find_for_requirement()`).
- **Edge cases.** Answer uses a story that is not in the ledger
  (not penalized as overclaim — routed to A3 as a **proposal** with
  source `mock:<session_id>`, labelled **self-reported** with
  corroboration `none`; the session statement itself is never
  treated as proof of the story, so on the user's approval it
  enters in state `unverified`, and it can move to `approved`
  only when proof separate from the session transcript is
  attached and approved like any other entry); answer contradicts
  the ledger (flagged plainly: "That number differs from your record
  — 14 here, 40 in the session" — **and** the session's version
  becomes an A3 proposal naming the contradicted entry, so the
  flag has an outcome under A3's supersession rule, not a flag
  alone); job has no delta (evidence axis
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
  **Data-quality rule (what a debrief may and may not mint).** A
  debrief proposal is generated only from an answer to a
  proof/depth question in which the user states a past fact about
  their own work. Every debrief proposal carries the label
  **self-reported, corroboration: none** and the session id; the
  statement in the transcript is not proof, so approval alone
  enters it as `unverified` (D2's rule), and `approved` requires
  proof attached separately from the transcript. Answers tagged
  rehearsal (D1's honest-framing questions), hypothetical or
  role-played answers, and answers about what the user *would* do
  generate **no** proposal, whatever they contain. Extraction is
  conservative by rule: a statement the extractor cannot tie to a
  specific past action, result, or artefact the user named is not
  proposed — the debrief lists it as "mentioned, not recorded"
  rather than guessing it into the queue.
- **Reuses.** `mock_interview.py: mock_summary()` +
  `_record_longitudinal_result()`, `initiatives/i06/longitudinal.py:
  observed_gaps()`, `skill_gaps.py: practice_observed_gaps()` /
  `recommend_next_drill()`, A3 proposal queue.
- **Edge cases.** User aces a mock with stories already in the ledger
  (no duplicate proposals — matched against existing entries);
  terrible session (proposals still generated for the past-fact
  statements the user actually made, under the data-quality rule
  above; tone of the debrief stays factual, not punitive);
  user never reviews proposals (after 30 days they leave the
  inbox's active list and stay visible in the proposal log as
  *expired* until dismissed, per A3 — nothing auto-applies).
- **Acceptance criteria.**
  - Completing the fixture mock yields proposals for exactly the new
    facts stated in the scripted answers.
  - The fixture script includes a rehearsal-tagged answer stating
    a plausible past fact and a hypothetical answer: neither
    yields a proposal, and the debrief's "mentioned, not recorded"
    list names the hypothetical. Every proposal the fixture does
    yield carries the self-reported label and corroboration
    `none`, and approving one without separate proof leaves it
    `unverified`.
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
  three top gaps in **B3's score-impact ordering** (the same list,
  in the same order, as the B3 delta report, under the
  score-impact definition stated in B3 — the quantity, the axis
  mapping, and the tie-breaks live there and nowhere else; no
  probe-likelihood ranking is claimed or computed), the STAR stories from the
  ledger that answer them (today's `_star_stories()` reads profile
  free text; it now reads approved, non-stale ledger entries only), and
  honest-framing lines for the skill gaps. Salary talking points stay.
- **Reuses.** `briefs.py: prep_interview()` structure,
  `company_brief()` unverified-field marking (kept — claims discipline
  applies to company facts too), B2/B3.
- **Edge cases.** Empty ledger (brief says prep is limited until
  evidence exists, routes to A2 instead of generating hollow
  stories — today's empty-stories behaviour, made explicit).
- **Acceptance criteria.**
  - Every STAR story in the brief cites an approved ledger entry (state `approved`).
  - Brief for the fixture job names its top-3 gaps in exactly the
    B3 delta report's score-impact ordering (same items, same
    sequence — asserted against the fixture's B3 report).

---

## E. Companion loop

### E1. Daily check-in (assemble the shipped pieces)

- **What it does.** A daily session that assembles what
  exists into one short conversation: today's top five (fit-ranked,
  with delta one-liners), the action inbox (approvals waiting —
  including A3 evidence proposals and C2 stale artefacts), follow-ups
  due, and one question back to the user ("anything new to feed me —
  a posting, an outcome, a story?"). **The item cap, stated here
  (the check-in never exceeds it: 5 jobs / 3 decisions / 1
  question).** The jobs segment is the top five, fit-ranked. The
  decisions segment shows **at most 3 decisions**, selected as
  the first 3 items in `action_inbox.py: inbox()` order — that
  function's own sort (kind priority first, then overdue before
  upcoming, as the shipped code orders them) with its `limit`
  applied at 3; no other selection order exists for this
  segment. Decisions beyond the cap are **not dropped, consumed,
  or reordered**: they stay in the action inbox, the check-in
  states how many more are waiting ("+4 more decisions
  waiting"), and they surface in later check-ins in the same
  inbox order. The question segment is exactly the one feed
  question. A builder that shows a fourth decision, or that
  selects the three by any other rule, does not meet this
  feature — and the roadmap's Phase 5 UAT cap line is testable
  against this paragraph as written. **Assembling is local; sending
  is a human act.** A scheduler may run on the user's machine to
  *prepare* the day's check-in — assemble its content and hold it
  locally as a prepared item — and that is all a scheduler may do.
  The prepared check-in reaches the user in exactly two ways: the
  user opens it on a local surface (in-product, CLI, dashboard), or
  the user, inside a live session they initiated, taps or commands
  "send this to me" for that prepared item on a chosen channel, and
  that one item is sent once, at that moment. Delivery and event
  opt-ins follow the per-event, default-off choice model locked for
  Initiative 03's legal RESHAPE — the user picks which events exist;
  nothing is default-on — and opt-in governs content categories and
  quiet hours only. **Opt-in is never initiation:** no setting,
  schedule, standing consent, or prior approval sends anything.
- **User seat.** Morning, the user opens the product (or their
  prepared-items list) and finds one screen: 5 jobs, 3 decisions, 1
  question — or taps once to have that item sent to the channel
  they are using. Replying to the question with a posting link starts the
  BYOL feed path (E2). If the user never opens it, nothing arrives
  anywhere else; an unopened prepared check-in simply waits, then
  is replaced by the next day's.
- **Inputs/outputs.** In: saved/watched jobs, inbox state, outcome
  staleness, preferences. Out: the prepared check-in (held locally)
  + replies recorded when the user engages with it, routed to the
  right module (posting → E2, outcome → `outcomes.py`,
  story → A3 proposal). E1 also adds **session typing** to the
  streak machinery: every session is logged locally by type (delta
  check, proof-closing, prep, application-touching), and the
  weekly recap shows the count of no-application sessions — the
  brief §9 return measure, which E1 owns. The session-type log's
  retention, export, and delete rules are in the data-lifecycle
  table (cross-cutting section).
- **Reuses.** `briefs.py: daily_top_five()`, `action_inbox.py:
  inbox()`, `followup.py: followups_with_drafts()`,
  `outcome_nudges.py: pending_prompts()`, `notify.py` (digest cadence,
  quiet hours, per-event opt-in catalog), `streaks.py` (the day's rep
  counts in the footer). New: the **local preparation** hookup
  (assemble + hold; no send path) + reply routing.
  An external scheduler may trigger preparation only, under the
  same no-send rule — the product gains a first-class `check-in`
  command either way, and `check-in send` exists only as the
  in-session act described above.
- **One consent model (specified here, built early).** Two consent
  systems exist today (`grill_channel` in preferences; `notify.py`'s
  per-event catalog). The reconciliation into the single per-event,
  default-off model (the Initiative 03 RESHAPE shape) is specified
  here but **built in roadmap Slot 0-C1/0-C2**, alongside the wizard choice
  build, so it exists before any feature depends on it: channel
  choice says *where a user-initiated send may go*, the per-event
  catalog says *what content categories may be prepared and offered
  at all*, and the catalog wins on conflict. **Neither says *when
  anything sends* — the user's act in the moment is the only
  initiation there is.** Grill delivery (A2) obeys the same rule:
  questions are prepared locally and sent only inside a session
  the user initiated or on the user's in-session send command for
  that batch. The supersession A2 states for `grill.py`'s
  outbound notes (standing approval; a scheduled proactive
  task) is part of this model: those notes are superseded
  here as well, and reuse of that machinery is conditional on
  their rewrite (A2 carries the condition in full).
  **Remote-endpoint delivery, scoped exactly (C2-10 — this
  paragraph is the whole rule; any shorter summary of it
  elsewhere must carry this scope or cite this paragraph).**
  (i) For **check-ins and grill questions** — profile-derived
  content — delivery to remote endpoints / webhooks is
  **removed as a class**: no user act sends check-in or grill
  content to a webhook or push endpoint, because an endpoint
  is not a surface the user is present on to act in the
  moment. (ii) The pre-existing `notify.py` **event
  notifications** (job and company notices — not
  profile-derived check-in or grill content) are **not**
  removed as a class by this rule: what Slot 0 keeps for them
  is webhook / push delivery **on the user's act in the
  moment, within this merged model** — each such path is
  re-scoped to prepare-only (it prepares and holds locally,
  and delivers only when the user acts for that item), or
  individually dispositioned as local-log-only or removed,
  per the notify-paths paragraph below. (iii) What **is**
  removed as a class, for every flow without exception, is
  **event-triggered** remote delivery: no path delivers
  because an event fired, a timer fired, or a setting
  allowed it.
  **Sends to third parties, stated accurately (D2-02).**
  Exactly one wired send to a third party exists today: the
  follow-up send — `followup.py: send_followup()` delegating
  to `email_sync.py: send_followup()` — and it is
  approval-gated in the form this package's initiation
  principle requires: a genuine interactive approval of the
  **exact recipient, subject, and body** (a caller-asserted
  confirm flag is not proof of approval), the approval is
  **single-use** with a **15-minute TTL**
  (`APPROVAL_TTL_SECONDS` in the channel registry), and the
  send is refused without an interactive terminal. That gate
  is named here as the model any third-party send must take.
  **Terms-audit consequence for this send, stated here so no
  enumeration of Gmail flows can omit it:** the follow-up send
  is a Gmail flow — it runs in `email_sync.py` over the same
  external Gmail CLI as that module's recruiter-mail scan — and
  it is **gated on the same channel-terms audit outcome** (the
  brief §7 / roadmap Row X audit) as the scan, grill-over-Gmail,
  `reply_radar.py`, and initiative 1.1's Gmail launch. Its
  keep-as-model disposition covers its **initiation form only**;
  it is not a terms verdict. If the audit's Gmail verdict is
  adverse, or no Gmail verdict is recorded, the send does not
  continue on the ground that it predates the audit: it is
  **suspended**, the suspension is recorded with the verdict,
  and the fallback is the user-initiated manual path — the
  product prepares the exact draft locally and the user sends
  it from their own mail tools, by their own act — until a
  recorded verdict clears the Gmail channel. A verdict that
  changes nothing for this send is not an available outcome of
  the audit for this flow either.
  It stays the **only** third-party send: every other draft
  surface in this package — check-in and grill drafts,
  network and mentor drafts, prepared items of every kind —
  does not send at all; those drafts are prepared and held,
  and sending them is the user's own act in the user's own
  tools. No new third-party send may be added except through
  a gate of the follow-up send's form (interactive,
  exact-content, single-use, short-TTL), and no sentence in
  this package may state or imply that third-party sends do
  not exist today. (The provisional coordinator ruling that
  previously exempted these sends from per-message initiation is
  deleted, not relied on: the governing principle — every outbound
  action initiated by a human hand at the moment it happens; the
  product never the last actor before a third party — admits no
  standing-consent exception, and this spec conforms to the
  roadmap's CUT of any auto-send under any flag, not the reverse.)
  On the roadmap's ordering 0-C1/0-C2 land in Slot 0, before A2 builds,
  so A2 never launches ahead of the consent model (the dependency
  is stated in initiative 1.1). This feature (E1) consumes the
  model; it does not rebuild it.
  **Existing notify paths are in scope (D-01-OBS — a hardening
  statement, added after the refutation pass refuted D-01 as
  filed).** The merged consent model governs sends; `notify.py`'s
  *existing* delivery paths do not inherit compliance merely by
  reading it. Every existing notify path — the webhook delivery,
  the ntfy delivery, the per-event sends fired by producers, and
  the digest queue/flush that delivers queued items later — must
  be **re-scoped** to prepare-only / user-initiated behaviour
  under this model (assemble and hold locally; deliver only on
  the user's act for that item), **or individually
  dispositioned** in writing (kept as a local-log-only path, or
  removed). No existing path keeps event-triggered remote
  delivery under any opt-in. This re-scope has an explicit
  roadmap home: **task 0-C3, inside 0-C2's scope**, which
  inventories each notify path, re-scopes or removes it, and
  tests for zero delivery without the user's act.
- **Content limit in prepared items.** A prepared check-in or
  grill batch that could be sent on a channel obeys A1's Tier 2
  rule at preparation time: Tier 2 values are never placed in the
  sendable payload, even if the user later taps send — the local
  surfaces may show them, the channel payload may not.
- **Edge cases.** Nothing to report (check-in is one line — "quiet
  day, depth 62, no decisions waiting" — never manufactured urgency);
  user ignores check-ins for a week (preparation cadence steps down
  to weekly per preferences, no guilt mechanics, and nothing is
  sent in either cadence); quiet hours (a user-initiated send
  inside quiet hours is the user's own act and proceeds; **there
  is no urgent bypass** — no event class may send during quiet
  hours, or at any hour, without the user's act).
- **Acceptance criteria.**
  - Fixture state produces a prepared check-in containing exactly the seeded
    top-5, the 3 seeded decisions, and the feed question.
  - Item cap, overflow case: a fixture state with **7 decisions**
    waiting produces a check-in showing exactly 3 — the first 3
    in `inbox()` order — a "+4 more decisions waiting" count,
    and no fourth decision anywhere in the prepared item; the
    other 4 remain in the action inbox afterwards, unshown and
    unconsumed, and the next day's check-in selects from the
    same inbox order.
  - With all event opt-ins off, nothing is prepared for sending and
    no remote delivery occurs (local log only) — the Initiative 03
    legal condition, tested.
  - **No-initiation, no-send:** with every event opt-in **on**, a
    scheduler clock advanced through a full week, and outbound
    calls mocked, the channel send count is zero until the user
    issues the in-session send command for the prepared item
    (opening the item displays it on the local surface and
    sends nothing — D-11's one definition of initiation); that act
    sends exactly the one prepared item, once, on the chosen
    channel.
  - Tier 2: the sendable payload of the fixture check-in (ledger
    seeded with compensation, clearance, sponsorship, and
    authorisation values) contains none of those values.
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
  `watch.py` for watched companies, `providers/` search (unchanged
  as a source list — its operating posture is specified next, not
  left as "unchanged" by implication).
- **Fetch and search posture (the terms boundary for both intake
  paths).** A posting link is fetched **unauthenticated only**:
  no cookies, no stored sessions, no credentials are ever supplied
  or requested, and nothing is fetched from behind a login. A
  domain or board that restricts automated fetching in its terms
  or robots policy is not fetched at all — the flow asks for
  pasted text instead. A fetch that returns 401/403, redirects to
  a login page, or otherwise hits a login wall falls back to the
  paste path; the product never offers to "log in and fetch it".
  Retained board search and watched-company checks run only on a
  user-initiated query or a user-opened session — there are no
  standing periodic checks that fetch or send on a timer — use
  only the boards' public/unauthenticated access, and inherit
  the same exclusion for boards that restrict automated access.
  (Whether the retained surface should continue at all is the
  brief §7 / roadmap question; this feature's spec no longer
  carries it forward unexamined or on a timer.) **Conformance
  has a roadmap home:** new initiative **0.9** implements
  retained-surface conformance with this posture — including
  `watch.py`'s cron entry point, the apply queue's
  scheduled / preset fill path, **and a third surface of the
  same cron instruction: `wizard.py`'s setup output, which
  tells the user to run `python watch.py` "(or schedule it via
  cron)" to check their watches (branch tree `wizard.py:531`;
  the same line stands in the live tree)** — which 0.9
  inventories and
  conforms or dispositions, the wizard line included: it is
  removed or reworded to a user-initiated run in the same
  initiative, and a conformance pass that touches the entry
  point and the server documentation but leaves the wizard's
  printed instruction standing does not pass — so a "keep" decision under the
  Phase 0 disposition gate is a decision about a surface that
  an initiative has actually brought to this posture, not a
  paper decision over unchanged code.
- **Edge cases.** Duplicate posting (matched to the existing job,
  delta refreshed, user told); link that cannot be fetched (ask for
  pasted text, keep the flow alive — never a dead end); link behind
  a login wall or on a fetch-restricted board (paste path, same
  handling — never a credential prompt); posting in a
  non-English language (decode proceeds, delta marked
  lower-confidence, stated plainly).
- **Acceptance criteria.**
  - Pasting the fixture posting end-to-end yields decode + delta +
    grill queue without a board search occurring.
  - Duplicate paste returns the existing job id and a refreshed delta
    timestamp.
  - Fetch boundary: the fixture link set (login-wall redirect,
    403 board, fetch-restricted board, plain public posting)
    produces paste-path fallbacks for the first three with no
    credential prompt anywhere, and a successful unauthenticated
    fetch only for the public posting (asserted under network
    mocks that record headers: no cookies or auth headers sent).

### E3. Warm intros as network delta

- **What it does.** Presents the shipped network machinery in delta
  terms: for a target company, the delta report gains a network
  line. **The example output shows only derivations the mechanism
  specified below actually produces (A-03/D-10):** "1 path in:
  a connection now at TargetCo (1st degree, from your import) —
  and a draft for it. No 2nd-degree path is shown: your import
  does not contain the second edge." No example in this feature
  shows a person-to-person chain ("you > A > B at the target"),
  an inferred relationship label (such as "ex-colleague" — the
  product's rule, kept from `referrals.py`, is that the
  relationship label is `connection` unless the import itself
  records stronger evidence), or a bridge derived from a note
  or a mention. Drafts stay drafts; sending is
  the user's act, in the user's own tools, exactly as the current
  code enforces. The mentor surface joins the same view (a mentor
  who has made this transition is a delta-closer, listed as such when
  the consent rules below allow).
- **Third-party data rules (the contacts are other people's data;
  this paragraph is the mechanism, not a pledge).**
  - **Source and terms.** Contact data enters only from an export
    the user generates through the source platform's own export
    feature and imports themselves. The import screen states, in
    plain words, that the export is governed by that platform's
    terms, that the product does not scrape or enrich any contact,
    and that importing is the user's act. No contact data arrives
    any other way.
  - **What may be shown.** A 1st-degree path uses only fields in
    the user's own import (name, employer, title, the recorded
    relationship evidence). A **2nd-degree path is shown only
    when both edges exist in the user's own imported data** —
    edge 1: the intermediate contact is in the import; edge 2:
    an imported record (a field of the import, never a note, a
    history entry, or a text mention) shows the intermediate's
    link to the target, such as the intermediate's recorded
    employment at the target company or their recorded
    connection to a named person at the target who is also in
    the import. Where the export does not support the second
    edge, no 2nd-degree path is shown or hinted at — there are no
    unsourced paths, and **a company name mentioned in a
    contact's notes is not an edge** under any reading of this
    rule.
  - **Consent — two mechanisms, each governing its own thing
    (D-12).** *(a) Listing: user-recorded attestation governs.*
    A person appears on the **mentor surface** or the **nudge
    list** only when their contact record carries
    `consent_status: granted`. That status is named honestly
    wherever it is shown: it is a **user-recorded attestation**
    — the user records, in the contact view, the date and the
    source of the consent as they understand it (e.g. "agreed
    in conversation, 2026-10-01") — it is not consent captured
    from the person by the product, and no surface may word it
    as the person's own in-product act. Default is `unknown`,
    which excludes the person from both surfaces (they may
    still appear as a labelled path in the user's own delta
    report, from the user's own data). Revocation is a
    first-class action in the same view — the user records that
    the person withdrew consent, or the person asks the user to
    remove them and the user records the request — and a
    revoked or declined record is suppressed from every surface
    immediately, including prepared check-ins. The attestation
    status, its date, and its source are shown wherever the
    gated surface lists the person. *(b) Contact details: the
    mentor's own sealing governs.* Where a mentor record comes
    from the mentor directory (`mentors.py`), the mentor's own
    `preferred_contact` field seals their contact details:
    `hidden` (the default) means no contact URL or address is
    shown until mutual consent through the mentor flow reveals
    it; only the mentor's own `linkedin_public` choice unseals
    it. **An attestation under (a) can never unseal contact
    details under (b), and where both mechanisms apply, the
    stricter outcome governs each field:** attestation governs
    whether the person is listed at all; sealing governs
    whether their contact details appear on the listing. A
    listed mentor whose details are sealed is reached through
    an introduction request, never through a revealed address.
    The same sealing posture is imported for stored contact
    details generally in this feature: an imported contact's
    details beyond the path fields (name, employer, title) —
    addresses and URLs held in the import — are not displayed
    on the mentor or nudge surfaces unless the record's own
    fields mark them public.
  - **Retention, correction, deletion.** Imported connections data
    is retained until the user deletes the import or the contact;
    there is no other copy. Every contact record can be corrected
    (name, employer, title, relationship label) and deleted
    individually from the contact view; deletion removes the
    record and every path, nudge, and mentor entry derived from
    it. The whole import can be exported (the user's own data
    back out, CSV/JSON) and deleted as a whole. Once a year the
    prepared check-in offers a connections review ("review or
    remove contacts you no longer know") — an offer inside a
    prepared item, never a send (E1's rule).
- **Reuses (scoped honestly).** Wired machinery only:
  `referrals.py: find_referrals_data()` / `rank_referrals()` /
  `draft_outreach()`, `network_crm.py: nudge_list()`,
  `mentors.py: matchmake()` consent gates (the gates are the
  consent rules above, implemented in this feature —
  not deferred to any unwired package). **`network_crm.py:
  warm_path_to()` is NOT reused for 2nd-degree paths (D-10):**
  as wired, it derives "2nd degree" from a contact's notes or
  history *mentioning* the target company, reading the CRM
  store — a mention is not an edge in the user's import, so
  that derivation cannot satisfy this feature's sourcing rule
  and no surface in this feature may call it for a path. Its
  1st-degree result (a contact who works at the target) may be
  used only where that contact is also in the user's import.
  **Roadmap ask (D-10):** the 2nd-degree derivation this
  feature actually needs — both edges from imported records
  only, per the rule above — is new or changed code (an
  import-consuming path function, not a parallel network
  feature), carried as a roadmap task with this acceptance:
  an import fixture with both edges yields the path; a fixture
  whose only bridge is a notes mention of the target company,
  in the import or in the CRM store, yields **no** path and no
  hint of one. The i07
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
  - Stale contact: the fixture's stale contact (per the nudge-list
    staleness rules) is excluded from suggested paths until its
    record is refreshed, and the report says why (F4-20 coverage).
  - 2nd-degree source rule: the fixture export supporting both
    edges yields the 2nd-degree path; the fixture variant missing
    the second edge yields no 2nd-degree path and no hint of one;
    and a fixture whose bridge contact's notes mention the
    target company — with no imported second edge — yields no
    2nd-degree path and no hint of one (D-10).
  - Sealing vs attestation (D-12): the fixture mentor with
    `consent_status: granted` recorded and
    `preferred_contact: hidden` renders listed, with the
    attestation and its source shown, and **no contact URL or
    address anywhere in the rendering**; the same fixture with
    the mentor's own `linkedin_public` renders the URL; no
    attestation value renders a hidden mentor's details.
  - Mentor gate, both ways: with the fixture mentor's
    `consent_status: granted` (date + source recorded), the mentor
    renders on the surface with that attestation shown, worded as
    a user-recorded attestation; with status
    `unknown` or `revoked`, the mentor section renders without
    that person — no name, no placeholder — and a revocation
    recorded mid-test removes them from the nudge list and any
    prepared check-in content in the same run.
  - Per-contact delete: deleting the fixture contact removes its
    paths and nudge entries everywhere they appeared, asserted
    against the stores as well as the surfaces.

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
    **Correctness is defined, not just presence:** the expected
    explanation for the fixture is hand-authored by the spec owner
    and frozen with the fixture, and the produced explanation is
    correct only when (a) every delta gap it cites exists, with
    that classification, in the stored deltas of the fixture jobs
    it names, (b) every stage it names matches those jobs'
    recorded outcome stages, and (c) its count ("3 of 4") equals
    the fixture outcomes that actually share the cited gap and
    stage. The test resolves every citation against the stores;
    an explanation citing a gap or stage the stores do not hold
    fails, however plausible its wording.
  - No weight change occurs without the evidence gate + recorded
    human approval (existing tests keep passing, unchanged).

---

## Data lifecycle — every store, one table (owned by A1 and B4)

**Enumeration method and scope (D2-06 — the completeness
claim is checkable, and this table is the reference set).**
This table was built by **code enumeration, not by naming
stores from memory**: on **2026-10-15** every repo-root
module in both code trees (`~/workspace/job-apply-mcp` and
the branch tree this package ships in) was swept for its
persisted stores — the sweep greps for store constants
(`*_FILE`, `*_PATH`, `*_DIR`, `STORE_PATH` assignments) and
for the JSON / JSONL / directory filenames those modules
write — and **every store the sweep found is dispositioned
in this table**: either it already had a row (the
disposition record for this round cites the row), or it has
a new row below. **The enumeration method is extended in one
named respect, because the first sweep's method missed
stores it should have caught:** the sweep also greps for
temp-file and indirect creation calls (`tempfile.mkstemp`,
preview / temp filename prefixes) in the same modules, and
for stores a swept module's docstring or comments name as
its store even where no matching constant pattern exists.
Under that extended method the outcome-migration family
(`outcomes_canonical.jsonl`, `outcomes_migration.jsonl`,
`migration_watermark.json`), the autopsy outcome store
(`outcomes.json`), the approval-preview temp files, and the
interim session marker each have their own row below — the
first enumeration's Outcomes row did not reach them, and no
completeness claim in this section is read as covering a
store by a neighbouring row's name again: a store is covered
only by a row that names it. Scope of the claim: the wired core product
(the repo-root modules and the governance log). Stores
belonging to unwired initiative packages (`initiatives/`)
are outside this table until the package is promoted — and
promotion may not ship until that package's stores have rows
here, under the standing rule at the end of this section.
**This enumerated table is the reference set roadmap
initiative 0.7(d) points at** (CROSS-DOC, roadmap round 3:
0.7(d) scopes to this table's full store set by reference,
including the round-3 additions named in its scope line —
and any store a later enumeration adds joins 0.7(d)'s scope
by the same reference, with no roadmap edit needed).

No store in this package is silent about its end of life. Rules
below are product behaviour with acceptance criteria, not
documentation promises. "Delete" always means the store itself is
purged, verified against the store, and derivatives are handled
as the row states. **The honest limit, in user-visible wording
(D-09 — this wording, not a broader promise, is what every
in-product description and delete confirmation uses):**
*deleting a source removes that source and the copies its row
names as deleted with it. Content derived from it inside other
stores — a proof rendered in a tailored variant, a reason
quoted in a verdict, a classification kept in delta history —
is flagged where the row says so, is listed to you by store and
count before you confirm, and stays in the product until you
delete it too: the confirmation offers a single
delete-source-and-derivatives act that purges the listed
derivatives, and anything you keep stays listed in a
"retained derivatives" view where you can delete it later.
Artefacts and exports you have already taken outside the
product cannot be recalled.* No text in this package or in the
product may shorten that to "delete reaches everything the
product still holds" or any equivalent broader promise.
(Roadmap initiative 0.7(d) carries the retention / export /
delete implementation for this table's full store set by
reference — the rows earlier rounds added (watches, notify
log and digest queue, experiment ledger, applications /
saved-jobs, and the apply queue) and the round-3
code-enumerated additions below (offers, screenshots,
network CRM, mentors, reply proposals, the soft-skill
stores, streaks, AI proficiency, and the further stores the
2026-10-15 enumeration found) alike.)

| Store | Retention | Export | Delete and propagation |
|---|---|---|---|
| Evidence ledger (A1) | Until the user deletes it; backups of it follow the backup rows | One-action JSON + readable text (A1), Tier 2 excluded by default per A1's export mechanism | Deletes the profile's claims with it (confirmation says so in plain words, **and discloses the derivatives in the same breath**: variants, deltas, verdict reasons, and D4 briefs citing its entries are flagged, listed by store and count, and persist until the user takes the confirmation's delete-source-and-derivatives act or deletes them later from the retained-derivatives view); proposal queue drafts that cite its entries are marked orphaned and removed on the user's confirm |
| Pre-migration backup (A1) | **Hard limit (D-13):** kept until the earlier of (a) 30 days after the user verifies the migration, or (b) 90 days after the backup was created — the same 90-day age ceiling as ongoing backups. **Notice (D2-07 — Phase-0-operable; the prepared check-in is not the mechanism and no part of this notice depends on any E1 surface):** from 30 days before the limit, and again at 7 days and 1 day before it, every local surface that exists from Phase 0 carries the notice — a banner in the profile view and the dashboard naming the deletion date and that this backup is the sole pre-migration restore copy, and the same notice printed by the CLI on any command run in that window. At the limit the backup is flagged delete-due, and **the first local run on or after the limit (the next CLI, dashboard, or profile-view run) deletes it in that run** and states the deletion plainly in that same surface, in the same words as the advance notices: the sole restore copy has been deleted on schedule, whether or not a restore was ever needed. **This scheduled deletion is not a confirmation-gated act and cannot be declined, paused, or postponed by any act or absence of an act** — the limit is a hard limit (A1 states the same rule; the two texts state one rule, not two). The deletion never happens silently or off-surface in the sense that matters here: it happens only inside a local run, and that run states it as it happens; it never happens in a background process with no surface present. A user who wants the copy gone sooner, or preserved under encryption, acts **before** the limit (the early-deletion and encryption-disposition acts described in this row), and those voluntary acts are confirmation-gated — the scheduled limit deletion is not. The completed deletion is noted in the local work log. The user may delete it earlier (through a confirmation act, without waiting for the limit), or disposition it under A1's encryption rule (encrypt or delete) when enabling encryption | Part of the ledger export when present | Same owner-only protected directory and permissions as the ledger; deleting the ledger offers deleting the backup in the same action, and says what survives if the user declines |
| Ongoing ledger backups (A1) | The product keeps the most recent 5 backups and deletes any backup older than 90 days, whichever limit is reached first; excess and expired backups are deleted automatically and the deletion is noted in the local work log | Part of the ledger export when present | Same owner-only protected directory and permissions as the ledger; deleting the ledger offers deleting its ongoing backups in the same action |
| Proposal queue + proposal log (A3) | Active proposals expire at 30 days (A3); expired/rejected entries stay in the log until the user dismisses them or clears the log | Included in the ledger export (proposals reference entries) | Clearing the log purges it; a proposal that was approved lives on as its ledger entry and is governed by the ledger row, which the log-clearing confirmation states |
| Per-job delta store (B3/B5) | Until the user deletes the job or the store | Exportable per job with the job's record (JSON) | Deleting a job deletes its deltas and delta history; deleting a proof or superseding an entry marks citing deltas stale (B3) — it does not silently rewrite their history |
| Verdict record (B4) | Until the user deletes it | One-action JSON + readable text (B4), Tier 2 values removed per A1's export mechanism unless the user makes the explicit inclusion act | Purges the local canonical store and the pointer entries in the framework and per-application logs (B4); the work-log note of the deletion is date + record-id hash only, retained under the work log's own row — and that residue is disclosed in B4's in-product description and delete confirmation before the user confirms (D-15) |
| Local work log (B4) | Rolling 12 months of entries, then older entries are deleted by the product and the user is told the window in the log's own view | Exportable as text | User-deletable in full at any time; deleting it affects no other store |
| Tailored artefacts + approved variants (C2) — the `tailored/` store, the cover-letter drafts store (`cover_letters/`), and resume-builder outputs (D2-08) | Until the user deletes the job or the artefact; a resume-builder output is kept until the user deletes that file or the profile it was built from | Export is the C2 handoff act (fresh human act each time) | Deleting an artefact deletes its stored variant and diff; deleting a builder output deletes the emitted Markdown / HTML / PDF files together; artefacts already handed off are outside the product (the standing limit above) |
| Outcomes (`outcomes.jsonl` + its `outcomes_meta.json` sidecar) (E4/B5) | Until the user deletes the job or the outcome store | Exportable as JSON/CSV from the outcomes view | Deleting an outcome removes it from B5/E4 aggregates, which are recomputed without it; deleting a job deletes its outcomes with it. **The outcome family's other stores — the canonical store, the migration log, the watermark, and the autopsy store — are governed by their own rows immediately below, not by this row; a whole-outcome-store delete act names and purges all five stores** |
| Outcome canonical store (`outcomes_canonical.jsonl`, `outcome_migration.py`) | Canonical outcome events, append-only in normal operation; kept until the user deletes the job or the outcome store | Exportable as JSON/CSV from the outcomes view, with the Outcomes row's export | Deleting an outcome removes its canonical events — append-only governs normal writes, not a user delete act: the delete act is the one operation that rewrites the file without the deleted events, and the rewrite is verified against the store; deleting a job deletes its canonical events with it; B5/E4 aggregates are recomputed without the deleted events. This row, not the Outcomes row above, governs this store |
| Outcome migration log (`outcomes_migration.jsonl`, `outcome_migration.py`) | Migration and rollback records for the canonical store, append-only in normal operation; kept until the user deletes the outcome store or this log | Exportable as JSON with the outcome-store export | Deleting the outcome store purges this log with it (same rewriting mechanism as the canonical row, verified against the file); deleting this log alone purges only the migration/rollback records and does not delete any outcome — the confirmation states that, so a log delete is never mistaken for an outcome delete |
| Migration watermark (`migration_watermark.json`, `outcome_migration.py` — named in the live tree; the branch-tree module carries the same migration without a separate watermark file) | Per-migration watermark state; kept until the user deletes the outcome store or resets the migration state | No separate export — operational state, shown in the outcomes / migration view; the settings are exportable as JSON with the outcome-store export | Deleting the outcome store purges it; deleting it alone resets the watermark to none and the next migration run re-creates it — the confirmation states that consequence before the act |
| Autopsy outcome store (`outcomes.json`, `rejection_autopsy.py`) | One outcome record per job, with the user's notes, read and written by the autopsy / diagnose surfaces; kept until the user deletes the job or this store | Exportable as JSON from the outcomes view | Deleting a job deletes its autopsy record with it; deleting an outcome record removes it from E4's autopsy inputs, and any autopsy explanation is recomputed without it; deleting the whole store purges every record and affects no other outcome store — the confirmation names the stores it does not touch |
| Approval-preview temp files (`veto-approval-preview-*.txt` in the OS temp directory, created by `email_sync.py: _save_approval_preview()`) | **Hard limit, two parts, whichever comes first:** at most the **10 newest** preview files (the count cap the code already enforces at each save), **and** no preview older than **7 days** — the age limit is checked, and expired previews are pruned, at product startup and at every new preview save, not only when a later preview happens to be saved; a preview that is never followed by another preview therefore does not persist indefinitely. Each file is created `0600` and holds the full body of an over-length approval draft — send-bound content, treated as such everywhere in this table and in A1's store-class table | No export — the file itself is the user's readable copy, and the save act shows its path; there is no second copy to export | **User deletion path, named:** the approval surface that saved a preview lists the existing preview files (path, age, size) and offers a delete act for any one of them or for all of them; deletion is verified against the temp directory's preview glob. The user may also delete the files directly in the OS temp directory at any time — the product states the path at save time so that act is available without the product running. Pruning under the hard limit above is noted in the local work log |
| Grill sessions (per-job + profile) (A2/C1) | Session records kept until the user deletes the job (per-job) or the session (profile) | Included in the job record / ledger export as applicable | Deleting a session deletes its Q&A record; answers already approved into the ledger are governed by the ledger row, and the confirmation states that |
| Mock / debrief history (D2/D3) | Until the user deletes the session history | Exportable as text/JSON from the practice view | Deleting a session deletes its transcript, scores, and debrief; proposals already created live in the proposal log row; ledger entries already approved live in the ledger row |
| E1 session-type log | Detail kept 13 months; older detail is collapsed to monthly counts (types only, no content ever) and the detail is deleted | Monthly counts exportable with the weekly-recap data | User-deletable in full at any time from the companion settings |
| Interim session marker (B4's veto-moment return measure; roadmap initiative 2.8) | A timestamped record of each user-initiated session start — **start time only; no session-type classification, no content**. Kept until initiative 5.2 migrates it into E1's session-type log, or the user deletes it; in no case kept as detail for longer than the E1 log's own detail window (13 months), after which unmigrated marker detail is collapsed to monthly counts on the same terms as that log | Timestamps exportable with the weekly-recap / session-type data | User-deletable in full at any time from the companion settings; the confirmation states the consequence for the return measure — returns not yet recorded from deleted marker history cannot be recorded afterwards, and the measure's surface then states that the marker history was deleted rather than presenting a "did not return" result from it. On 5.2 migration: the marker history migrates into E1's session-type log, the migration is reconciled (no recorded return is recomputed or lost — B4), and the marker store itself is then deleted; from that point the E1 session-type log row above governs the migrated history. **This row is the marker's lifecycle row from the day 2.8 ships it** — the table's closing rule (no new store ships without its row) is met by this row, not by the E1 log's row alone |
| Connections import (E3) | Until the user deletes the import or a contact | CSV/JSON export of the user's import | Per-contact and whole-import delete per E3; derived paths, nudges, and mentor entries are removed in the same action |
| Prepared check-ins (E1) | An unopened prepared item is replaced by the next preparation cycle; opened items become part of the session record | n/a (content is assembled from the stores above) | No separate store of sent content exists; the session-type log row governs what is counted |
| Watches store (`watch.py`) (D-08) | Each watch (search terms, locations, target companies) is kept until the user deletes that watch or the whole store; no watch is kept silently after its company is removed from the user's targets without the watch list showing it as inactive | Exportable as JSON from the watches view | Deleting a watch purges its stored queries and results; deleting the whole store purges every watch in the same action. This row governs the store only — the surface's operating posture is E2's, and its conformance implementation is roadmap 0.9's |
| Notify log + digest queue (`notify.py`) (D-08) | Log entries roll at 12 months, like the work log, then older entries are deleted by the product; queued digest items are held only until they are shown as part of a prepared item or for 7 days, whichever comes first, then discarded unsent | Log exportable as text/JSON; the digest queue has no export (its content is assembled from other stores) | User-deletable in full at any time (log and queue separately); deleting the queue discards its items — nothing in it is delivered by, or after, deletion. A1's store-class rule applies: the log holds notification titles and bodies naming companies and roles, so it sits under the same owner-only posture |
| Per-application experiment ledger (D-08) | Entries are kept until the user deletes the job they belong to or deletes the whole ledger | Exportable as JSON with the job's record | Deleting a job deletes its experiment entries; deleting the verdict record (B4) deletes its pointer entries here per B4's rule; deleting the whole ledger purges every entry and is confirmed separately from the verdict record |
| Applications / saved-jobs store (D-08) | Each job is kept until the user deletes that job; the whole store is kept until the user deletes it | Exportable as JSON/CSV from the jobs view | Deleting a job triggers the deletions its dependent rows name (deltas, outcomes, grill sessions, experiment entries for that job) and the confirmation lists them; deleting the whole store deletes every job with the same per-job propagation, confirmed as one act with the dependent stores listed |
| Apply queue store (D-08) | A queued item is kept until it runs, is cancelled, or the user deletes it; completed or cancelled items are kept 90 days as a record, then deleted by the product | Exportable as JSON from the queue view | Deleting a queued item discards it — it is never run as part of, or after, deletion; deleting the whole store discards every pending item in the same action and keeps no copy. This row governs the store only — the scheduled / preset fill path's disposition is roadmap 0.9's |
| Offers store (`offers.json` + `offer_weights.json`) (D2-06) | Each offer is kept until the user deletes that offer or the whole store; no offer expires silently | Exportable as JSON from the offers view, subject to A1's Tier 2 export mechanism (the store holds compensation figures) | Deleting an offer purges its figures and its weights entry; deleting the whole store purges every offer in the same action. The store sits in A1's confidentiality table with the ledger's posture (owner-only, in 0.8's encrypted scope) |
| Filled-form screenshots (`screenshots/`) (D2-06) | **Hard limit:** a screenshot is kept at most 30 days and at most the 50 newest are kept; the cleanup runs at startup and at the start of each browser-apply run (the code today runs it at apply-run start only — the startup run is new under this row, so a user who never runs browser-apply again still gets the limit), and each cleanup is noted in the local work log | No export — a screenshot is a working image of a filled form, viewable in the product; the user may save a copy outside the product by their own act | User-deletable at any time, singly or as a whole store, from the browser-apply view — the delete act does not require running browser-apply; deletion purges the image files, verified against the directory |
| Network CRM store (`network.json`) (D2-06) | Each contact record is kept until the user deletes that contact or the whole store; this store is distinct from the connections import (E3) — contacts are added and annotated independently of any import, and both stores' rows apply to their own records | Exportable as JSON/CSV from the network view (the user's own records back out) | Per-contact delete removes the record and every path, nudge, and mentor entry derived from it, in the same action as E3's per-contact delete where the same person sits in both stores (the confirmation says which stores it touches); deleting the whole store purges every contact |
| Mentors store (`mentors.json` + `contributions/outbox/` drafts) (D2-06) | Each mentor record is kept until the user deletes that record or the whole store; outbox drafts are kept until the user sends them by their own act in their own tools, deletes them, or deletes the store | Exportable as JSON from the mentor view | Deleting a mentor record purges it and its outbox drafts; deleting the whole store purges every record and draft. E3's sealing rules govern what any surface shows from this store while it lives |
| Reply proposals (`reply_proposals.json`) (D2-06) | Each proposal (derived from the user's recruiter email) is kept until the user dismisses it, acts on it, deletes the application it belongs to, or deletes the whole store | Exportable as JSON with the job's record | Deleting an application deletes its proposals with it (named in the applications row's confirmation list); deleting the whole store purges every proposal and affects no application |
| Soft-skill practice stores (`soft_skill_sessions.json`, `soft_skills.json`, `soft_skill_lab_sessions.json`) (D2-06) | Session transcripts, progress, and lab sessions are kept until the user deletes the practice history (per store or as the whole set) | Exportable as text/JSON from the practice view | Deleting a store purges it; the three stores are listed separately in the delete confirmation so the user sees which parts of the practice history a delete act covers. These are distinct from the mock / debrief history row (D2/D3's module) |
| Streaks store (`streaks.json`) (D2-06) | Timestamped rep history is kept until the user deletes it; this is the existing streak store E1 builds session typing alongside — E1's session-type log is its own row above, not this store | Exportable as JSON from the companion settings | User-deletable in full at any time; deletion purges the rep history and affects no other store |
| AI proficiency store (`ai_proficiency.json`, with the i06 practice history / focus files it joins) (D2-06) | Practice records are kept until the user deletes the practice store | Exportable as JSON from the practice view | Deleting the store purges the proficiency record and its practice history / focus files in the same action, listed in the confirmation |
| Flat profile store (`profiles/*.json`, incl. `profile.json`) (D2-06 enumeration) | Each profile file is kept until the user deletes that profile; migration to the ledger does not delete it (existing consumers read it), and the ledger row — not this row — governs the migrated claims' lifecycle | Exportable as JSON (the profile export); Tier 2 fields in it follow A1's export mechanism | Deleting a profile purges its file; the confirmation states plainly that deleting the flat profile does not delete the ledger, and deleting the ledger does not delete the flat profile — each is its own act |
| Preferences store (`preferences.json`) (D2-06 enumeration) | Kept until the user resets or deletes it; it holds the salary floor (a Tier 2 compensation fact) and sits in A1's confidentiality table with the ledger's posture | Exportable as JSON; the salary floor follows A1's Tier 2 export mechanism | Deleting it purges the file and the product regenerates defaults on the next run — the confirmation says so, so the delete is never mistaken for a settings freeze |
| Notify preferences (`notify_prefs.json`) (D2-06 enumeration) | Kept until the user disables notifications or deletes it; it holds the user's notification preferences **and the secret push topic** — a credential-bearing file, owner-only under A1's store-class posture | Settings are viewable in the product; the secret topic is never exported — an export shows the settings with the topic redacted | Deleting it purges the preferences and the topic and disables push delivery until the user sets it up again |
| Compliance record (`compliance.json`) (D2-06 enumeration) | Kept until the user deletes it | Exportable as JSON | Deleting it purges the record; the confirmation states the record is regenerated from defaults on the next apply-path run |
| Model card (`model_card.jsonl`, with its `.bak` and `.corrupt` sidecars) (D2-06 enumeration) | Entries are kept until the user resets or deletes the card | Exportable as JSON | Deleting the card purges the card and both sidecars in the same action; no calibrated weights survive a delete the user believes removed them |
| Near-miss queue (`near_miss.json`) (D2-06 enumeration) | Each queued item is kept until it is resolved, dismissed, its job is deleted, or the whole queue is deleted | Exportable as JSON with the job's record | Deleting a job deletes its queue items (named in the applications row's confirmation list); deleting the whole queue purges every item and touches no verdict already recorded (the verdict record row governs those) |
| Skill-gap store (`skill_gaps.json`) (D2-06 enumeration) | Kept until the user deletes it; it is a derived store — deleting it loses no source data | Exportable as JSON from the gaps view | Deleting it purges the store; the next gap analysis regenerates it from the jobs and profile, and the delete confirmation says so |
| Provider health store (`provider_health.json`, with its entry-quarantine files) (D2-06 enumeration) | Operational board-health state, kept until the user resets or deletes it; quarantine files are kept with the store and deleted with it | Exportable as JSON | Deleting the store purges the health state and every quarantine file in the same action |
| BYOL listings store (`listings/`) (D2-06 enumeration) | Each user-fed listing is kept until the user deletes that job or the whole store | Exportable as JSON with the job's record | Deleting a job deletes its listing file (named in the applications row's confirmation list); deleting the whole store purges every listing |
| Browser session files (`sessions/`) (D2-06 enumeration) | Kept until the user deletes them; the product lists them wherever it detects them (the doctor / startup check) rather than holding them silently | No export — session files are working state, not user content | User-deletable in full at any time from the same surface that lists them; deletion purges the session files |
| Web UI token file (`~/.veto_webui_token`) (D2-06 enumeration) | Kept until the user revokes it (regenerates the token) or deletes it; a credential file, owner-only | No export — the token is a secret, shown only at the user's own setup act | Deleting or regenerating it revokes LAN access under the old token immediately; the settings surface states that consequence before the act |
| Governance verdict log (the framework log B4 points into) (D2-06 enumeration) | Pointer entries are kept until the verdict record is deleted (B4's rule deletes them with it) or the user deletes the log | Exportable with the verdict record export (B4) | Deleting the verdict record deletes its pointer entries here (B4's row governs); deleting the log file itself is the user's act outside the product and the product states that plainly rather than promising to reach it |

Acceptance for the table as a whole: for each row, a test creates
the fixture store, exports it, deletes it, and asserts the store
and the derivatives the row names are gone or handled as stated —
against the stores directly, not only the surfaces. A feature
that creates a new store may not ship until its row exists in
this table.

---

## Cross-cutting: claims-debt fixes (from brief §6)

Not a feature — a correctness sweep. Stated with the roadmap's
actual ordering, so the three documents stop saying three
different "firsts": Slot 0 (owed UAT and RESHAPE work) runs first;
this Phase 0 sweep follows it, with the copy-corrections item
allowed in parallel only as the roadmap states. The sweep:
correct the copy named in the brief §6 claims-debt list — every
item on that list as reworked (CD-01…CD-13 as originally audited,
plus any items the rework adds; the brief's list governs, this
section does not freeze its count) — in `docs/grill.md`, the site
specs, and product copy. Each fix is a
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
  how an open-source user sets up the external scheduler that may
  trigger check-in **preparation** (never sending — E1's rule), and
  the ledger storage/protection story (A1), including its stated
  limit: no product-built at-rest encryption until roadmap
  initiative 0.8 (the encrypted ledger store) ships.
- **Claims-register upkeep.** At each phase's close, §6 of the brief
  is re-checked against the code and the site copy updated in the
  same motion — Phases 1–5 must not recreate the debt Phase 0 pays
  off.
- **Test fixtures.** Fixture profiles and postings (B1's frozen
  expected lists, A4's hand-computed ledgers), the fixture
  connections export (E3), hand-computed trend fixtures (B5), and
  the site demo's browser test path (used by the Phase 2 gate for
  the Radar gradient story) — built once, owned, versioned.
