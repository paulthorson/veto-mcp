# Veto positioning brief — the core differentiator

Status: bake-out v13, 2026-10-15 (revised after CEO stress-test, PM
review, and eleven blind-review rounds — eight KICK_BACK rework
rounds and three ALLOW rounds; see §9). Companion documents: `feature-sets.md` (what gets
built) and `roadmap.md` (in what order). Evidence base:
`code-grounding.md` (read-only audit of this repo's code) and
`competitive-landscape.md` (research seat, sources cited inline in §5).

**Claims discipline, applied throughout:** every statement about the
product is marked **[ships]** (wired into a user-facing surface today:
MCP tools, CLI, web UI, dashboard), **[built, unwired]** (real, tested
code in an initiative package with no user surface), or **[bet]**
(roadmap work, does not exist yet). The full register is §6. Bets are
never stated as fact anywhere in this brief, including the front half.

---

## 1. The decision

Veto stops competing on application volume. That ground is crowded
(§5) — and most of it is closed to Veto anyway by its legal posture
(§7): a tool that never submits on the user's behalf was never going
to out-submit the auto-apply tools. The honest statement is that this
is a constraint the strategy turns into the position, not a free
choice dressed up as one.

Veto hyper-focuses on the work before the application:

1. **Knowing the user deeply** — a detailed profile built as an
   evidence ledger, not a resume. [bet — thin core today, real model
   built-unwired; §6 claims 12–13]
2. **Resume tailoring as a service** — per-job tailoring where every
   changed line traces to a source and is approved by the user.
   [ships in core form; §6 claims 3–6]
3. **Interview prep** — practice tied to one specific job. [ships in
   posting-based form; the delta-driven, evidence-graded form is a
   bet; §6 claim 16]
4. **Understanding deltas** — for every job, the gap between the user
   and the posting, classified by kind. [bet — core matching is
   binary today; the classified form is built-unwired; §6 claim 14]

The apply-and-track workflow stays in the product (it exists and works — with the submit click always the user's),
but they are plumbing, not the pitch.

## 2. One-line positioning

> **The resume tool that refuses. Veto will not invent a claim for
> your resume — and when a job is not right, it tells you whether
> you are unproven or unqualified, and what would change the
> answer.**

Status of this line, stated where the line is stated (not buried in
§6): the refusal to invent **ships today** — the tailor and letter
writer generate only from what the user gave them (§6 claims 5–6,
with claim 6's stated limits). The classified answer — *unproven or
unqualified, and what would change it* — is the **[bet]** half
(claims 14/20; features A5, B2–B4). Until those land, this line is
the target positioning and is used publicly only with this status
attached; the narrower promise in §3 (Pillar 3) is the one that may
stand alone today.

Why this line and not a broader one (stress-test §2): "every other
tool helps you apply to more jobs" is false for seven of the nine
competitors in §5 — only the auto-apply tools sell volume. "Gets to
know you" and "based on your real experience" are already claimed by
Sonara and Teal. Prep wording is contested ground too: job-specific
prep is already sold by Final Round AI and Teal (§5), so a readiness
claim alone carries nothing.
The words a competitor cannot copy with equal truth today are the
mechanism: **refusal**, and the **split** —

- **Not unqualified — unproven.** The four-word form of the delta
  split (§3, Pillar 2).
- **Free, open-source, local-first [P]** (posture — claim 11). No user data flows to author
  infrastructure — that is the exact claim (Rule 2, §7). Profile-
  derived text leaves the machine only over delivery channels the
  user chose (their own email, chat, or per-event notification endpoint), a limit stated
  wherever this line is used, not buried.

## 3. The three pillars

Each pillar is stated in two parts: what ships today, and the bet.
Nothing in the "today" column depends on the bet being built.

### Pillar 1 — The profile is an evidence ledger, not a resume

**Today [ships/thin]:** the profile is flat fields (contact, targets,
skills list, experience with free-text bullets) plus up to two
quantified wins per role captured by the wizard's one-time setup
grill (`wizard.py: collect_grill()`). A real evidence model — claims
linked to verbatim quotes with an approval state — exists as
**[built, unwired]** code in the i04/i05 initiative packages.

**The bet:** promote that model into the core profile. Every claim
carries its proof (story, number, result), a source, and a proof
state — including claims the user typed in themselves, which enter
as *unverified* until proof is attached (the intake standard,
feature A5). The grill becomes a standing practice that deepens the
ledger; answers and practice results flow back as proposals the user
approves (features A2–A3). A depth meter makes the ledger's strength
visible (A4).

**On the moat — stated honestly:** the ledger is **not** a switching-
cost moat. The proof in it is the user's own history; they could
re-enter it elsewhere in an afternoon, and the data is portable by
design — the product intends to win on continued use, not exit cost.
What can compound is trust: a record of refusals and verdicts the
user can inspect, accumulated graded practice, and outcome-linked
history are slower for a competitor to earn than a feature is to
copy. That is the claim. It is weaker than a data moat, and it is
the one the architecture supports.

### Pillar 2 — The delta is the product

**Today [ships]:** a fit score with per-axis breakdown and a score
veto below the bar (`match.py: score_job()`), plus the
insufficient-signal veto (3+ axes on unknown defaults); gap analysis that ranks
missing skills across jobs (`skill_gaps.py: analyze_gaps()`); a
near-miss queue that gives borderline scores a human second look
(`near_miss.py`). Core matching is **binary**: a skill counts if it
is in the profile's skill list, missing otherwise — which produces
both false "proven" (listed, no supporting evidence) and false
"missing" (in the experience text, not the list).

**The bet:** classify every requirement of a job into the product
taxonomy (this is the taxonomy; feature B2 implements it, reconciled
with the i04 evidence map it promotes):

- **Supported** — a verbatim, quantified proof is on record.
- **Evidence gap** — the claim is on record but the proof is missing,
  unquantified, alias-only, or not quotable. *Unproven, not
  unqualified.* Fixable fast: surface the proof.
- **Skill gap** — nothing on record. Not fixable by editing text.
  Veto names what would close it (feature B2 + `gap_plan()`).
- **Contested** — the record contradicts the requirement (e.g. a
  stated years minimum the record does not meet). The veto feeder.

The classification is deliberately conservative: it can mistake a
real-but-paraphrased history for an evidence gap (cost: one grill
question), and it is built to never mistake an absent proof for a
supported one (cost if it did: the honesty brand). The match tools
that report gaps at all (Teal, Jobscan, Rezi, Simplify) report one
blended "missing" list; three of them (Teal, Jobscan, Rezi) offer
to generate the missing text, and Simplify offers general AI
tailoring on its paid tier; LinkedIn reports a blended fit
judgement without the list; the
volume tools have no gap model to split. None makes this split.

**Retention, stated with its condition:** delta *trending* counts
postings the user **evaluates**, not applications submitted — a
considered searcher evaluates many postings and applies to few, and
every pasted posting produces a delta (feature E2). Trending is
therefore available to the primary segment. Fit-weight
*personalisation* is a different matter: it stays gated behind
outcome evidence and human approval exactly as shipped, and is
**paused** as a roadmap item (roadmap, PAUSE list) — it is not part
of this segment's early value and the brief does not sell it.

### Pillar 3 — Honesty is the brand

The promise, narrowed to what the machinery can keep **today**:
**Veto adds nothing to what you told it.** One clause more is the
target, and it is marked as what it is: **[bet]** that everything
you told it carries a visible proof state (feature A5, claim 20) —
today a claim typed into setup is indistinguishable from a proven
one, and no sentence in this brief may imply otherwise. Three
mechanisms:

1. **Construction guards [ships].** The tailor and the cover-letter
   writer generate only from profile facts; skills the profile lacks
   come back as `missing_skills`, never inserted
   (`tailor.py`, `cover_letters.py`).
2. **Traceability + approval [ships, with limits].** Tailoring shows
   a diff; the approved variant is the one on record; a per-line
   statement map traces each line to a profile source — with
   renderer-composed text explicitly tagged `system:template` so it
   cannot pass as the user's words (`tailor_with_provenance()`). A
   cover-letter honesty scan flags claims the profile text cannot
   back, and a governance gate can block an application over an
   unsupported letter claim — **limits:** the blocking gate runs on
   the confirm path, with a letter attached, and only when the
   governance framework checkout is present; when absent it disables
   itself silently. The roadmap removes that dependency (feature C3)
   precisely because a brand promise cannot be conditional on a
   second codebase being installed.
3. **The verdict record [ships in part].** Allow/block verdicts are
   appended through the governance adapter into the framework's log
   (`record_application_verdict()`), and a per-application experiment
   log exists (`experiment_ledger.py`). A single, unified,
   user-inspectable verdict record is **[bet]** (feature B4) — the
   brief does not claim it exists today.

**The intake hole, named:** the gate checks claims against the
profile; nothing today checks the profile itself. A user can type an
invented win into setup and watch every later artefact trace cleanly
to it — the system would prove consistency, not honesty. The intake
standard (feature A5) is the product answer: claims enter as
unverified, proof is requested at entry, and unverified claims are
labelled everywhere they are used and can never classify as
*Supported* in a delta. Until A5 ships, every honesty sentence about
Veto must be the narrowed promise above, not "will not lie for you."

In a market flooded with generated applications, a tool that refuses
— on the record — is a claim users can repeat. Final Round AI's
live-interview copilot (answers supplied during the real interview)
is the far end of the opposite position; Veto's roadmap explicitly
CUTs any equivalent (roadmap, PAUSE/CUT list).

### The loop — labelled as what it is

Delta → prep → evidence → smaller delta is the **target design**
(feature sets B, D, A3), not a description of the current product.
Today **no arrow in it runs**: grill answers do not reach tailoring,
prep questions are not generated from gaps, grading is answer-craft
heuristics, and nothing writes back to the profile (§6 claims
13/15/16). The loop is the roadmap's reason to exist; the brief sells
it as the bet it is.

## 4. Who this is for — and how they arrive

- **Primary:** experienced professionals in considered searches — few
  target roles, high cost per missed interview, a real history worth
  proving. The trigger event the brief is built around: the user has
  been burned — rejected after a generated application, or caught in
  an interview unable to back a bullet a tool wrote for them. Veto
  may be their **second tool**, the check on the first; the brief
  accepts that position rather than pretending to replace the
  tracker, the graph, and the autofill on day one.
- **Volume users are not the design target, and are not written
  off.** They are the feeder segment: they run the most cycles, hit
  the failure the brand is built on first, and — for an open-source
  project — produce the stories, stars, and issues growth runs on.
  The product does not optimise for them; it welcomes them when they
  hit the wall.
- **Secondary:** career changers. Their problem is delta — and their
  ledger is the emptiest, so the product's first honest output to
  them is a list of skill gaps. The roadmap's answer is that the
  delta report pairs a gap with its closing path where one exists
  (B3/B4); where no plan exists, the report says so and still names
  the smallest next step the user can take, so "not yet" never
  arrives empty-handed.
- **Acquisition — the named path.** A free local tool grows by
  arrival and sharing or not at all. The channels, in order of fit:
  (1) the interactive demo on the project site — **planned, not a
  present asset.** The strategy's primary channel is a demo where a
  visitor answers a grill and can be refused **before** any install.
  This package does not claim that demo exists today: the evidence
  behind it reviewed the site's spec copy — whose demo content is
  itself claims debt (item 2: the spec demo shows a salary question
  the grill cannot generate) — and one shipped radar demo
  component, not a running visitor grill flow. The refusal demo,
  including a delta-report view, is scheduled work (roadmap
  initiative 2.4) that lands once the delta engine exists to show.
  The demo is named as the bridge because it is the only surface
  that could carry a considered searcher over the install distance
  hosted and extension competitors do not impose — which is why the
  strategy depends on building it, and why nothing in this brief
  may describe it in the present tense until it ships; (2) open-source discovery —
  the repo itself, MCP directories and registries, community
  job-search spaces where the refusal story is tellable; (3) the
  project owner's writing. Pretending the install distance does not
  exist would be the kind of claim this document exists to stop.

## 5. Competitive landscape

Full research with per-claim sources: `competitive-landscape.md`
(research seat, checked 2026-10-15). Summary table — competitor rows
describe the products as they are today, on their public record.
**The Veto row is graded by the same standard and carries its §6
status per cell** (stress-test change 3). [S] = ships, [B] = bet, [P] = posture (a program fact outside this package's evidence exhibits — claim 11).

| Product | What it owns | Profile model | Proof vs skill gap | Says don't apply? | Refuses unbacked claims? | Prep graded vs user evidence? | Price shape |
|---|---|---|---|---|---|---|---|
| Teal | Organize + tailor in one workspace | Resume + versions | No — missing terms, AI generates bullets for them | No | No | No — delivery + posting relevance | Freemium, Teal+ paid |
| LinkedIn Premium | The hiring graph; rank vs other applicants | LinkedIn profile text | No — one blended fit judgement | No — steers to strong fits | No | No — course library + AI coaching, not evidence-graded | Paid subscription |
| Jobscan | The ATS match score for one application | One resume vs one posting | No — one missing list | No | No — user approves generated edits | No (consumer) | Freemium / paid |
| Yoodli | How you sound | None — session from a job title or roleplay scenario | No | No | n/a — writes no resume | No — delivery only, per its reviews | Freemium / paid |
| LazyApply | Application volume | Form-fill data | No — same resume to every job | No — the opposite | No | No | Paid annual |
| Sonara | Set-and-forget autopilot search | Short profile + preferences | No | No | No | No | Paid after trial |
| Rezi | The strict ATS resume | Document built in-editor | No — missing keywords | No | No — writes bullets from role + company; user may approve lines | No | Freemium / paid |
| Final Round AI | Help during the live interview | Resume + posting as inputs to a goal | No — debrief flags weak answers | No | No — supplies answers live | Partly — tailored to job, graded on answer quality, not evidence | Paid |
| Simplify | Free autofill on 100+ boards | Form-fill profile | No — score + missing keywords | No — and submission is the user's, like Veto | No | No | Freemium / paid tier (Simplify+) |
| **Veto** | **The tool that refuses: no invented claims [S]; proof-state labels [B]; a named delta [B]** | **Evidence ledger [B] — thin flat profile [S]** | **[B] — core matching is binary [S]** | **Yes [S] — score veto; classified veto with a path [B]** | **Partly [S] — by construction + letter scan; gate conditional (see §3); resume-wide at approval [B]** | **[B] — craft grading [S]** | **Free, open source, local-first [P]** |

Open ground (no competitor claims it on the public record): the
evidence-ledger profile, the proof-gap/skill-gap split, refusal of
unbacked claims, a do-not-apply verdict with the reason and the path,
and prep graded against the user's own evidence. All five are Veto
**bets or partials today** — the ground is open, and Veto has not
taken it yet. That is what the roadmap is for.

Contested ground (do not claim as new): per-job tailoring with a
score; "know your fit" (LinkedIn owns it with applicant-pool data
Veto does not have); approve-before-send in general form (Jobscan,
Rezi, Simplify); job-specific prep in general form (Final Round AI,
Teal); "gets to know you" phrasing (Sonara, Teal). Veto's defensible
versions are the narrower ones stated in §2–§3.

## 6. Claims register — what is true today, what is a bet

Checked against the code audit. "Ships" means wired into a user-facing
surface (MCP tools, CLI, web UI, dashboard). "Built, unwired" means
real, tested code in an initiative package with no user surface yet —
it may be described as built, never as available.

| # | Claim | Status today | Evidence |
|---|---|---|---|
| 1 | Per-application grill with quantify / gap / logistics / motivation questions; application waits for answers (when `grill_on_apply` is on and the channel is not `off`) | **Ships, with the conditions stated** | `grill.py: generate_questions()`; apply gate in `server.py: apply_to_job()` |
| 2 | Fit score with per-axis breakdown and a veto below the bar — plus the second shipped veto: 3+ axes scored on unknown defaults (the insufficient-signal rule) | **Ships** | `match.py: score_job()` (axes 50/15/15/15/5, veto < 60), `radar.py` renders the breakdown |
| 3 | Tailoring shows a diff; the approved variant is the one on record | **Ships** | `tailor.py: tailor_with_diff()`, `save_approved_variant()` |
| 4 | Tailored lines trace to sources — profile sources per line, renderer-composed text tagged `system:template` so it cannot pass as the user's words | **Ships — the template tag is part of the claim: renderer text is tagged, never presented as the user's words** | `tailor.py: tailor_with_provenance()` per-line statement map |
| 5 | The tailor cannot add skills the profile lacks | **Ships** | `tailor.py` returns them as `missing_skills`, never inserted |
| 6 | Cover letters are scanned for claims the profile cannot back; unsupported claims can block an application | **Ships, with limits** | `cover_letters.py: honesty_scan()`; governance gate in `governance/adapter.py` — runs on the confirm path, with a cover letter, when the framework checkout is present |
| 7a | Allow/block verdicts are recorded | **Ships** | `governance/adapter.py: record_application_verdict()` (framework log; recording never raises, failure is reported not blocking); `experiment_ledger.py` per-application log |
| 7b | A unified verdict record the user can inspect | **Bet** | No single product surface unifies these records today (audit §5) |
| 8 | Mock interviews with a published rubric; salary negotiation sims incl. hard modes | **Ships** | `mock_interview.py`, `initiatives/i06/rubric.py: score_answer()`, `soft_skills.py: negotiation_sim()` |
| 9 | Who-do-you-know finder + warm-path drafts; nothing is ever sent | **Ships** | `referrals.py: find_referrals_data()`, `network_crm.py: warm_path_to()` (the i07 package's `plan_warm_path()` is built, **unwired** — not evidence for this claim) |
| 10 | The submit click is always the user's | **Ships (architecture)** | `browser_apply.py` has no submit path; `ats_apply.py` is preview-only; `apply_to_job()` returns the URL for the user to finish |
| 11 | Free, open source, local-first; no user data to author infrastructure | **Posture (program fact)** — attested by the project's public-release program (2026-09-14), which sits outside this package's evidence exhibits; Exhibits D/E neither confirm nor refute it, and no product claim in this brief rests on it beyond posture | Public-release program record (outside Exhibits D/E) |
| 12 | The profile is an evidence ledger | **Bet** — thin core today (flat fields, up to two quantified wins per role from the wizard's one-time setup grill); a real evidence model is **built, unwired** | Core: `wizard.py: collect_grill()`. Unwired: `initiatives/i04/evidence_map.py: build_evidence_map()`, `initiatives/i05/evidence_library.py`; packet approval: `initiatives/i05/packet.py: approve_packet()` |
| 13 | The profile deepens with use (grill answers, practice results write back) | **Bet** — no write-back exists today | Audit §2, §6: answers stay in `grill_sessions.json`; practice goes to i06 history only |
| 14 | Delta split: evidence gap vs skill gap, per job, in the product taxonomy (§3) | **Bet** — core matching is binary (listed or missing); a three-way split is **built, unwired** (i04 statuses `supported` / `grill_question` / `gap`; the product taxonomy in Pillar 2 is the reconciliation feature B2 implements) | `initiatives/i04/evidence_map.py`; core: `skill_gaps.py: analyze_gaps()` |
| 15 | Grill answers feed tailoring | **Bet** — claimed in docs and site today, **not true in core**; the only consumers of the answers today are the unwired i05 packet and a web-UI display | `grill.py: get_qa_pairs()` — no caller in `tailor.py` / `cover_letters.py`; consumers: `initiatives/i05/packet.py`, `webui.py: _h_grill_qa_pairs()` (display only) |
| 16 | Mock interviews built from a job's gaps; answers graded against the user's evidence | **Bet** — questions come from the posting's likely questions or role banks; grading is answer-craft heuristics | `mock_interview.py: start_mock_interview()`, `_score_feedback()` |
| 17 | A daily companion check-in that nudges you to feed it jobs | **Bet** — the pieces ship (daily top five, action inbox, follow-up drafts, digests, streaks, outcome nudges) but no scheduled loop assembles them | `briefs.py: daily_top_five()`, `action_inbox.py: inbox()`, `followup.py: followups_with_drafts()`, `notify.py`, `streaks.py`, `outcome_nudges.py` |
| 18 | Fit shown as a green/amber/red gradient | **Bet** — directed for the dataviz (program history; the audit records only the non-implementation), **not implemented**; radar is single-colour with a red veto state | `radar.py` (one amber polygon, red veto); `site/src/demos/radar.tsx` (binary) |
| 19 | Delta trending over time per role family | **Bet** — outcome events and practice history exist; no delta time series | `outcomes.py`, `initiatives/i06/longitudinal.py`, i04 `career_graph.py` (unwired) |
| 20 | Profile claims carry a proof state from intake (unverified until proof attached) | **Bet** — intake is flat self-reported fields today; nothing marks or checks them | Audit §1; feature A5 |

### Claims debt — public statements to correct, before any launch

The marketing site and docs currently state things the code does not
support — the audit's fourteen claim risks, grouped. **Order of
operations (a decision, not a note): the corrections land first
(roadmap Phase 0), before this positioning ships anywhere public.**
An honesty brand invites checking; the product's own site must pass
the check first.

1. (CD-01) "Grill answers feed tailoring" (`docs/grill.md`, site grill spec)
   — false in core (claim 15; audit risk 2). Fix by building it (roadmap Phase 3)
   **and** correcting the copy until it lands.
2. (CD-02) The grill demo shows a salary question; `generate_questions()` has
   no salary kind (audit risk 3).
3. (CD-03) Site fit-score spec: "weights are fixed constants, never learned"
   — contradicted by the shipped, gated model-card design
   (`model_card.py`); the honest claim is "static until evidence and
   a human approval say otherwise" (audit risk 5).
4. (CD-04) Site skill-gaps spec: one-click close, instant re-rank, streak
   updates, gaps "mapped to a mock-interview pack", a
   `veto gaps --role …` command, percentage frequencies — none
   exist; closing requires an evidence note (audit risk 6).
5. (CD-05) Site verdict-ledger spec names a ledger path/fallback the code
   does not implement (claim 7a's records live elsewhere;
   audit risk 13).
6. (CD-06) Green/amber/red gradient language anywhere it implies it ships
   (claim 18; audit risk 4).
7. (CD-07) Site JD-decoder copy implying the decoder compares the posting to
   the profile or extracts its requirements — `decode_jd()` is
   posting-only (audit risk 7).
8. (CD-08) Any "every claim in your resume is checked against evidence"
   wording — the wired check covers the cover letter, conditionally
   (claim 6); the resume is protected by construction, not audited
   (audit risk 8).
9. (CD-09) Mock-prep wording, both halves of audit risk 9: (1) any "mock
   interviews built from your gaps" wording — claim 16 is a bet;
   (2) any wording saying answers are graded against your evidence
   — grading today is craft heuristics; evidence grading is D2's
   bet (claim 16), and copy must not claim it until D2 ships.
10. (CD-10) Daily check-in / proactive companion framing — claim 17 is a
    bet (audit risk 10).
11. (CD-11) Any wording implying Veto contacts people, sends outreach, or
    submits applications — all three are false by architecture
    (claims 9–10; audit risks 11–12).
12. (CD-12) Evidence-map / evidence-library / career-graph / packet-approval
    features described as available to users — all four are built,
    unwired (claims 12 and 19; audit risk 14).
13. (CD-13) "Veto learns you over time / your profile gets deeper with use"
    wording anywhere it appears — no write-back exists, so the
    profile today is what the user typed on day one (claim 13;
    audit risk 1). This completes the mapping: items 1–13 cover all
    fourteen audit claim risks.

## 7. Legal posture — analysis, not advocacy

Governing principle (legal exposure program, 2026-09-14): **Veto is
never the last actor before a third party receives something; every
outbound action is initiated by a human hand at the moment it
happens; no authenticated sessions on platforms that restrict
automated access; no user data flows to author infrastructure
(Rule 2, absolute).**

**What the differentiator genuinely improves.** The ledger, the
delta, tailoring drafts, and prep are local computation over the
user's own data, and refusal **reduces** outbound actions — a user
talked out of a bad application produces fewer submissions and less
platform contact. The repositioning moves effort away from the
highest-exposure surfaces (search/apply automation) toward the
lowest (knowing the user). Every artefact the pillars produce
(tailored resume, letter, outreach draft, follow-up draft) stops at
a human approval step, consistent with the STRICT circuit-breaker
shape locked 2026-09-29 for AI-drafted outbound messages. Initiative
08 (collective intelligence) stays CUT under Rule 2 — the ledger is
per-user and local, never pooled.

**The exposure the pillars create — named, with the roadmap's
answer:**

1. **Concentration of sensitive data.** The ledger deliberately
   holds more than a resume: quantified wins alongside compensation
   floors, sponsorship, clearance, work authorisation. Local-first
   moves the richest copy of a person's career onto their own
   machine. Rule 2 answers the author's exposure, not the user's.
   Roadmap answer: ledger versioning, pre-migration backup, and a
   tested restore ship **with** the ledger (feature A1), and the
   ledger's storage/protection story is documented for users in
   Phase 0 — not discovered later.
2. **Profile-derived data leaves the machine over chosen channels.**
   Grill questions derived from the profile can be delivered over
   Gmail and WhatsApp; notifications can go to remote endpoints on
   per-event opt-in; company briefs fetch from the web. None of this
   breaks Rule 2; all of it falsifies any "nothing leaves your
   machine" wording, which the brief therefore never uses (§2).
   Roadmap answer: channel sends inherit the per-event, default-off
   consent model (Initiative 03 RESHAPE plus the reconciliation of
   the two existing consent systems into one model — both built in
   roadmap Slot 0-C, before Phase 0; the model is specified in
   feature E1).
3. **The blocking gate can be silently off.** When the governance
   framework checkout is absent, the gate returns disabled and the
   caller proceeds (audit §5). A promise backed by a gate that
   vanishes per-install is a reliance gap. Roadmap answer: feature
   C3 makes the honesty gate unconditional on the standalone
   scanner; until C3 ships, §3 states the limit wherever the gate
   is claimed.
4. **Third-party contact data.** The warm-intro finder holds other
   people's names, employers, and titles from an imported
   connections export, with deliberately thin relationship labels.
   Drafts stop at the user — Veto never sends — but data *about*
   third parties is a surface even when nothing is sent. The i07
   consent/handshake material exists (unwired) and the roadmap's
   network work (E3) is scoped to the wired machinery with its
   honesty labels intact; no contact is ever enriched by scraping.
5. **The verdict/practice record cuts both ways.** An inspectable
   record of what the tool blocked, and grades against the user's
   own evidence, is the trust feature — and a durable list of every
   claim the tool called unbacked. Two facts hold today: it lives on
   the user's machine, and it is never transmitted to author
   infrastructure (Rule 2). The third fact a user needs — that they
   can **export or delete** the record — is **not supported today**
   (the audit describes the verdict record's two stores and no unifying
   surface — claim 7 — and does not address export or delete at
   all; that silence is the gap) and is therefore a
   requirement on feature B4, which owns the unified record: export,
   delete, and an in-product description of what the record holds
   ship with it, or the record does not ship.

**Net judgement:** the differentiator strengthens the posture on the
axis the legal program governs (third-party contact, Rule 2) and
adds user-side data exposure that the roadmap must actively manage
(items 1–5). Both halves are the finding.

## 8. What success looks like — with numbers and a kill criterion

Targets below are **targets for the built state**, set 2026-10-15,
to be re-based when each phase ships. Five of the measures are
computed by machinery or instruments the roadmap builds — the
depth meter (Phase 1) for Profile depth; B4's verdict record
and overturn computation (Phase 2) for Veto correctness; B5's
outcome computation for Outcomes; E1's session typing (Phase 5)
for Return; and the Phase 2 seeded UAT run set as Recognition's
instrument — and each measure's paragraph below states its own
timing; no success claim is made on a metric the product cannot
yet count.

- **Recognition (a content check, not a mind-read).** The measure
  is whether the first-session summary each seeded persona run
  produces states the difference in its own words — "the others apply for
  me; this one checks my proof and tells me no." Instrument: the
  Phase 2 UAT seeded run set — five seeded personas, one
  first-session summary collected per persona (denominator: 5).
  Target: the refusal/split wording present in at least 3 of the
  5 summaries by end of Phase 2. Owner: the Phase 2 UAT item,
  maintained under roadmap row X. No claim about real users'
  unprompted wording is made — a local-first product cannot
  sample them.
- **Profile depth (per user — there is no population version).**
  Rule 2 means no telemetry: the product can never count a median
  across users, so this target is per-ledger and is evaluated where
  it can be counted — the seeded synthetic-persona runs and any
  single user's own ledger. Target: a persona ledger (and a real
  user's, when they look) gains +15 depth points within its first
  8 weeks of use, driven by proof-closing (A2/A3), not by new
  unverified claims (the meter weights `approved` proof only; A5).
  Owner: feature A4 computes it; roadmap Phase 1's UAT measures a
  persona depth move against hand-computed amounts (the 8-week
  target itself is evaluated on lived ledgers, not in the
  Phase 1 gate).
- **Veto correctness — the signature metric.** The near-miss queue
  (`near_miss.py`) already exists to give borderline calls a human
  second look; feature B4 computes the overturn rate from those
  resolutions and recorded overrides (B4's definition) and
  displays it on the verdict record (its acceptance
  criteria carry it, and roadmap Phase 2's E2E tests it). Target:
  of vetoes the user reviews, the overturn rate is **tracked from
  Phase 2 and published in the product's own record**; a sustained
  overturn rate above 1 in 3 means the veto is wrong too often to
  carry the brand, and triggers a threshold review before any
  further positioning use. A veto nobody can check is a claim; a
  veto with a visible overturn rate is a record.
- **Outcomes, not prevention (per user, owned by B5):**
  interviews per application, computed on the user's own machine
  from their outcome store against their own pre-Veto baseline
  where they have one, and surfaced by delta trending (B5) with its
  sample size. The positioning is judged on interviews won, not
  applications prevented — a fall in applications with flat
  interviews is a failure wearing a success's clothes. Timing: first
  countable when B5 ships (Phase 5); before that the figure is
  reported as not yet countable, never as zero.
- **Return between applications (per user; countable only once
  E1 ships its session typing, Phase 5).** Today this cannot be
  counted: `streaks.py` counts reps by type, and neither delta
  checks nor proof-closing is a rep type. Feature E1 adds session
  typing (delta check, proof-closing, prep, application-touching)
  to the streak machinery and shows the count in the weekly recap —
  E1 owns this measure. Target, evaluated in the Phase 5 UAT lived
  week and visible to each user in their own recap: the week
  includes at least one no-application session. No cross-user
  share is claimed, because none can be counted (§7, Rule 2).
- **Kill criterion:** if, two quarters after Phase 5 ships — the first point at which all three triggers can be counted (the overturn trigger alone is countable from Phase 2 and is watched from then; the criterion as a whole is judged only when every trigger has a measure) — the
  delta report does not change behaviour — proof-closing rate near
  zero (B5's measure), vetoes routinely overridden without the
  named change-my-answer condition met (B4's record),
  interviews-per-application flat against baseline (B5) — the
  positioning goes back to the seats for rework or abandonment.
  The bet (§3's loop) is falsifiable, and this paragraph is where
  it is falsified.

## 9. Revision record

v2 (2026-10-15) folds in: CEO stress-test required changes 1–12
(one-liner rewritten around refusal and the split; intake hole named
and specced as feature A5; §5 re-graded symmetrically; bet markers
moved into §§1–3; moat paragraph replaced; delta taxonomy reconciled
with the i04 model; claims 4/7 corrected; claims debt completed and
sequenced first; acquisition path named; segment/mechanics tension
faced; §7 rewritten as analysis; §8 given numbers, a
veto-correctness metric, and a kill criterion) and PM review changes
affecting this document (full claims register in the Phase 0 sweep;
gate's silent-off state and its C3 fix stated wherever the gate is
claimed). The stress-test's strongest objection is answered where it
can be — and where it cannot (the loop does not run yet; the brand
precedes the built product), the brief now says so in the sections a
reader actually reads, not only in the register.

v3 (2026-10-15) folds in the blind review's 16 findings (1 blocker,
9 majors, 6 minors): the §2 headline now carries its own status (the
refusal to invent ships; the classified answer is the bet, labelled
at the line itself); claim 9's evidence no longer cites an unwired
function; the claims-debt list covers all fourteen audit risks
(item 13 added); the Pillar 2 universal claim is restricted to the
tools the research actually shows; §4's demo channel is re-tensed
and its delta half scheduled (roadmap 2.4); export/delete of the
verdict record is a B4 requirement, not a claimed fact; §8's metrics
are wired to owners (B4 overturn rate; Phase 2 UAT recognition item);
the ledger state set is defined once in feature A1 and cited
everywhere; the consent reconciliation is owned by roadmap Slot 0-C;
and every phase UAT now runs seeded-gate first, lived check second.

v4 (2026-10-15) folds in the second blind review's findings
(1 blocker, 5 majors, 5 minors, 1 nit): the §3 today-promise is now
only the construction claim, with the labelling clause marked [bet]
in the sentence itself; §4's demo is no longer graded [ships] by
this package; §5's lead and price cells carry their markers; §8's
population targets are replaced by per-user measures with named
owners (Rule 2 makes cross-user medians uncountable, and the brief
now says so); Phase 2's UAT states its lived check; Phase 1's
forward dependencies on the delta engine (A5's classification
assertion, A4's role-family definition) are declared and scheduled
instead of hidden; and the vocabulary drift the review found
(`verified`, "mixed", contested in B4, the weekly-recap attribution)
is reconciled to the one defined set.

v5 (2026-10-15) folds in the third blind review's findings
(1 blocker, 3 majors, 7 minors, 1 nit): the §4 demo is now described
as planned work, not a present asset — the evidence reviewed spec
copy, not the live surface, and the spec demo itself carries debt.
The mock write-back path is reconciled to the one state machine (a
mock proposal enters `unverified`; depth counts it only when proof
is approved). §8's recognition measure is a defined content check
on the five seeded-run summaries (denominator stated, owner
named), and the return measure is owned by E1, which now builds
the session typing it needs. B6 documents its axis mapping (salary
and recency axes render unknown — they carry no requirement
classification) and its precedence rule. Role-family ownership is
stated one act at a time; 1.5 declares its approval-flow
dependency; Phase 5's UAT names its seeded items and fixes its
lived window at one week; debt items 9 and 12 now carry their full
sub-claims; §4's gap promise matches B3's no-plan case; claim 4's
condition is stated in words.

v6 (2026-10-15) folds in the fourth blind review's findings
(0 blockers, 5 majors, 5 minors, 1 nit): the interactive refusal
demo is now actually scheduled (feature B6's demo spec, roadmap
2.4) instead of only its read-only half; the Phase 2 UAT runs the
five-persona recognition set with the 3-of-5 content-check line
§8 specifies; E1's session typing is inside initiative 5.1's
scope and the Phase 5 lived week carries the no-application-
session line; the state model is one model — drafts live in the
proposal queue, the ledger is unchanged until approval writes an
entry as `unverified` or `approved` — stated identically in A1,
A2, A3, and D3; row X names an owner in every phase; the claims
register states both shipped vetoes; debt items carry their
CD-01…CD-13 checklist IDs in print; D4 and C4 read approved
entries only; B1 extracts the location/authorisation requirements
B6's location axis consumes.

v7 (2026-10-15) folds in the fifth blind review's findings
(0 blockers, 2 majors, 7 minors, 2 nits): A2's acceptance now
states the read model correctly (queue drafts appear nowhere
downstream; tailoring and delta read ledger entries in both
states, with approved-only restrictions stated per feature);
Phase 4's E2E asserts reclassification on approval and the depth
move only after proof approval; the recognition summary's
producer is the seeded persona run in both §8 and the roadmap;
claim 11 is graded as a program fact outside the exhibits rather
than self-cited; the Pillar 2 generation claim is restricted to
the three tools the research supports; §8's intro counts all
five unbuilt measures; A1 pins the migration rule (no migrated
claim enters as `approved`); 5.4's scope names `mentors.py`;
the expired-proposal location and the flagged/stale terms are
stated once, identically.

v8 (2026-10-15) folds in the sixth blind review's findings
(0 blockers, 1 major, 6 minors, 2 nits): the §5 Veto row's price
cell now carries claim 11's actual grade ([P], posture) with the
legend extended to define it; expired proposals have one visible
home (the proposal log) in both A3 and D3; §8's intro maps each
measure to its own machinery or instrument; the kill criterion's
triggers are all defined measures (B5 owns the proof-closing
rate, now specced; B4's record states whether an override's
named condition had been met); §7 item 5 cites what the audit
actually shows; B2's fixture matrix gains the frozen-oracle rule
and the taxonomy's full supported bar; the interactive demo
gains acceptance criteria and a Phase 2 E2E line; the 2026-10
gradient direction is labelled program history; E1's consent
timing matches the roadmap's ordering.

v9 (2026-10-15) folds in the seventh blind review's (the v8
bundle) remaining minors and nits — that round returned ALLOW
(0 blockers,
0 majors); these fixes clear that round's open-issues list: A1's producer enumeration names the
producers A3 names, with A5's direct-entry path stated as the
exception; the insufficient-signal veto is assigned to B4's
thin-evidence class with its cause marked, and fixtured; B5's
proof-closing rate names its source (the delta store joined to
the A3 approval record); §2's posture bullet carries its [P]
marker at the line; B2's summary definition of evidence gap
carries the taxonomy's full wording; §8 credits Phase 1's UAT
with the depth move it actually measures; the proposal log has
one name in the roadmap too.

v10 (2026-10-15) folds in the eighth blind review's findings
(0 blockers, 2 majors, 1 minor, 2 nits) — the confirmation round
for v9, which caught two things the v9 pass itself introduced or
left open: the headers' round count claimed a confirmation round
that had not happened when written (now corrected to the eight rounds §9 then enumerated — seven KICK_BACK rounds and an ALLOW), and B5's two owned measures (proof-closing
rate, interviews-per-application) had no acceptance criteria,
E2E, or UAT lines (acceptance criteria and UAT lines added in
that pass; the Phase 5 E2E lines land in v11). A1 and A3 now list both
grill producers identically; §7 item 5 says "the verdict record's
two stores"; Phase 5's UAT paragraph runs in its stated order.

v11 (2026-10-15) folds in the ninth blind review's findings
(0 blockers, 2 majors, 5 minors, 2 nits): the headers' round
count now matches §9's enumeration in both exhibits (nine rounds
at this version: eight KICK_BACK rounds and an ALLOW); B5's two
measures are asserted in Phase 5's E2E as the v10 entry said
they were; §8's Outcomes paragraph states its own timing; the
overturn rate's source is stated as B4 defines it; A2's
nowhere-downstream rule carries the C1 session-path exception,
and C1 states the session-input distinction; A4 uses the
one-act-at-a-time role-family ownership; the kill criterion is
clocked from Phase 5, when all three triggers can be counted;
A3's proposal log lists its expired state; claim 17 and CD-12
carry their full citations.

v12 (2026-10-15) folds in the tenth blind review's remaining
items — that round returned ALLOW (0 blockers, 0 majors,
2 minors, 2 nits): claim 12's evidence now cross-references
packet approval (CD-12's fourth feature); Phase 2's E2E names
the insufficient-signal fixture B4's acceptance carries; A4's
role-family clause is stated once; B5 uses one name (A3's
proposal log) for the approval record throughout.

v13 (2026-10-15) folds in the eleventh blind review's remaining
items — that round returned ALLOW (0 blockers, 0 majors,
4 minors, 2 nits): the two "never leaves the machine" absolutes
(in B4's record description and the roadmap's pooled-data CUT)
now use §7's Rule-2 wording; §2's channel enumeration includes
per-event notification endpoints; Phase 5's E2E uses the
canonical name (A3's proposal log); A4 states its per-family
deferral (views render once 2.1 implements the definition);
the claims-debt sweep's scope sentence no longer enumerates a
partial list; two §5 cells carry the detail the research
supports (Simplify's paid tier, Yoodli's roleplay sessions).
