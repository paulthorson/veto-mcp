# Veto positioning brief — the core differentiator

Status: bake-out v15, 2026-10-15 (rework round 2 after the fresh
blind audit of v14 returned KICK_BACK — 6 blockers / 26 majors /
23 minors standing after the refutation pass; this version
re-corrects the Jobscan, LazyApply, and Sonara rows from the
products' own current pages, adds MaxCV and the five missing scaled
competitors to §5, restates the open ground as the narrower
combination that remains unoccupied, conforms the headline to its
own qualifier rule, and re-sweeps the claims-debt list by claim
concept — see §10). Companion documents: `feature-sets.md` (what
gets built) and `roadmap.md` (in what order). Evidence base:
`code-grounding.md` (read-only audit of this repo's code) and
`competitive-landscape.md` (research seat, sources cited inline in §5).

**Claims discipline, applied throughout:** every statement about the
product is marked **[ships]** (wired into a user-facing surface today:
MCP tools, CLI, web UI, dashboard), **[built, unwired]** (real, tested
code in an initiative package with no user surface), or **[bet]**
(roadmap work, does not exist yet). The full register is §6. Bets are
never stated as fact anywhere in this brief, including the front half.

**Tree discipline (new in v14):** two code trees exist — this branch
tree (veto-mcp, the tree these documents live in) and the live tree
(job-apply-mcp). They have diverged, including on the exact function
claim 2 cites. §6 grades claims against **this branch tree** unless an
entry says otherwise; where the trees differ, the entry names both.
Earlier versions of the register did not say which tree was graded,
and at least one [ships] grade was true only of the other tree.

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
2. **Resume tailoring as a service** — per-job tailoring with a shown
   diff. [ships in part — the diff ships; per-line provenance is
   built, unwired, and the approved-variant save path is broken
   today; §6 claims 3–6]
3. **Interview prep** — practice tied to one specific job. [ships in
   posting-based form; the delta-driven, evidence-graded form is a
   bet; §6 claim 16]
4. **Understanding deltas** — for every job, the gap between the user
   and the posting, classified by kind. [bet — core matching is
   binary today; a three-way split (supported / grill-question /
   gap) is built-unwired; the fourth class, contested, and the full
   product taxonomy are bet only; §6 claim 14]

The apply-and-track workflow stays in the product (it exists and works — with the submit click always the user's),
but they are plumbing, not the pitch.

## 2. One-line positioning

> **The resume tool that refuses. Veto will not invent a claim for
> your resume — and when a job is not right, it tells you whether
> you are unproven or unqualified for this posting as written, and
> what would change the answer.**

Status of this line, stated where the line is stated (not buried in
§6): the refusal to invent **ships today as a construction rule** —
the tailor and the letter writer generate only from what the user
gave them (§6 claim 5). It does **not** ship today as an enforced
blocking gate: the gate checks a cover letter's skills, years, and
veto keywords only, so an invented metric or an invented employer in
a letter — the canonical unbacked claims — **cannot block an
application today** (§6 claim 6, corrected in this round). Full
enforcement — the complete honesty scan (numbers, names, skills)
blocking approval of every tailored artefact — is the **[bet]** half
of the honesty promise (feature C3). Under feature C3 a factual
claim passes only traced to an `approved` ledger entry with proof
attached; a claim tracing only to an unverified entry or a grill
answer blocks. The classified answer —
*unproven or unqualified for this posting as written, and what
would change it* — is also a
**[bet]** (claims 14/20; features A5, B2–B4), under **one
production rule, owned by feature B4 and restated here without
variation**: the headline word exists only when a veto fires, and
it is decided by the most severe class present among the posting's
must-have requirements (contested > skill gap > evidence gap). A
veto whose must-haves carry only evidence gaps reads as
**unproven**. Any contested or skill-gap must-have makes the
answer **unqualified for this posting as written** — so a
thin-evidence veto that also carries a skill-gap must-have reads
*unqualified*, not *unproven*: the veto's named class never
overrides the most-severe-present rule, and no passage in this
brief assigns a headline word to a veto class directly. A veto
that fires on score or insufficient signal alone, with every
must-have supported, gets no headline word at all. The qualifier
*for this posting as written* is part of the claim wherever the
word *unqualified* appears in the positioning — the headline
included, with no exception (§8, risk 2). Every
class, contested included, gets a named "what would change the
answer"; no class is exempt. Until those features land, this line is
the target positioning and is used publicly only with this status
attached; the narrower promise in §3 (Pillar 3) is the one that may
stand alone today.

Why this line and not a broader one (stress-test §2): "every other
tool helps you apply to more jobs" is false for most of the
competitors in §5 — only the auto-apply tools sell volume. "Gets to
know you" and "based on your real experience" are already claimed by
Sonara and Teal. Prep wording is contested ground too: job-specific
prep is already sold by Final Round AI, Teal, LinkedIn, Rezi,
Jobscan, JobCopilot, and EarnBetter
(§5), so a readiness claim alone carries nothing.
**What remains open ground is narrower than earlier versions of
this brief claimed, and it is stated as a combination, scoped to
the §5 table as now constituted (twenty competitor rows, checked
2026-10-15).** Refusal of unbacked claims as a stated mechanism is
**already occupied**: MaxCV markets a hard fabrication ban — only
skills and experience already in the CV are used, skills the user
lacks are not added, risky claims are stripped, softer claims wait
for approval, and each requirement is mapped to evidence in the CV
versus not in the CV (§5). JobCopilot's FAQ and AI Applyd's
comparison copy state no-invention postures in the same direction,
and Enhancv's tailoring copy states real-experience-only tailoring
with a placeholder used instead of an invented figure. The
narrowing is plain: Veto cannot claim refusal, a fabrication ban,
or requirement-to-evidence mapping as its own ground. What no row
in the corrected table combines is the full set together:
**refusal of unbacked claims + the four-state proof classification
(supported / evidence gap / skill gap / contested, split by proof
state and not only by whether an item is on record) + an
inspectable verdict record that shows its own overturn data +
prep driven by that delta and graded against the user's own
evidence.** MaxCV is the nearest occupant: it holds the first
element and a record-presence mapping (in the CV versus not in the
CV); it does not split on-record-but-unproven from absent, publish
a verdict record with overturn data, or drive prep from that
split. That combination — not any single word in it — is the open
ground this brief claims, and only for the table as constituted:
products outside the table were not checked, and the claim must be
re-checked before any public use (§5).

- **Not unqualified — unproven.** The short form of the delta
  split (§3, Pillar 2) — a form of words for the evidence-gap case
  only, under the production rule above, never a label for a veto
  class as such.
- **Free, open-source, local-first [P]** (posture — claim 11). A
  posture, not a unique one: Resume Matcher already occupies free +
  open-source + local tailoring and scoring (§5), and AIHawk's
  original form occupied free + open-source + locally run bulk
  applying at scale before the project pivoted (§5). What no row
  in the corrected table combines with that posture is the
  combination stated above; the posture alone differentiates
  nothing, and this brief no longer presents it as if it did. No user data
  flows to author infrastructure — that is the exact claim (Rule 2,
  §7). Profile-derived text leaves the machine only over delivery
  channels the user chose (their own email or chat, inside a
  session they initiated), a limit stated wherever this line is
  used, not buried.

## 3. The three pillars

Each pillar is stated in two parts: what ships today, and the bet.
Nothing in the "today" column depends on the bet being built.

### Pillar 1 — The profile is an evidence ledger, not a resume

**Today [ships/thin]:** the profile is flat fields (contact, targets,
skills list, experience with free-text bullets) plus up to two
quantified wins per role captured by the wizard's opt-in `--grill`
mode (`wizard.py: collect_grill()`). The default setup flow never
runs that mode, so a default profile starts with zero captured wins
— thinner than earlier versions of this brief implied. A real
evidence model — claims linked to verbatim quotes with an approval
state — exists as **[built, unwired]** code in the i04/i05
initiative packages.

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
the one the architecture supports. Its countable form is per-user
only: the user's own verdict record — vetoes issued, vetoes
overturned, proofs closed — which the product shows the user about
itself. Rule 2 means there is no population version, so trust is
never claimed as a market statistic (§8, risk 10). The copyability
problem behind this paragraph is priced in full at §8, risk 1.

### Pillar 2 — The delta is the product

**Today [ships]:** a fit score with per-axis breakdown and a score
veto below the bar (`match.py: score_job()`); gap analysis that ranks
missing skills across jobs (`skill_gaps.py: analyze_gaps()`); a
near-miss queue that gives borderline scores a human second look
(`near_miss.py`). One correction from the audit round: the
insufficient-signal veto (3+ axes scored on unknown defaults) ships
**only in the live tree** (`job-apply-mcp/match.py:133,594-595`); in
this branch tree the score veto is the only veto
(`match.py:336`) — claim 2 grades the two trees separately, and any
sentence in this brief that names the insufficient-signal veto names
its tree. Core matching is **binary**: a skill counts if it
is in the profile's skill list, missing otherwise — which produces
both false "proven" (listed, no supporting evidence) and false
"missing" (in the experience text, not the list).

**The bet:** classify every requirement of a job into the product
taxonomy (this is the taxonomy; feature B2 implements it, reconciled
with the i04 evidence map it promotes):

- **Supported** — the proof the requirement's kind requires is on
  record (feature B2's per-kind test): verbatim quantified proof for
  a quantitative requirement, the stated minimum met for a threshold
  requirement, and verbatim approved attestation or documentary
  evidence for a categorical requirement (location, work
  authorisation, credentials) — no quantity is demanded of a
  categorical fact.
- **Evidence gap** — the claim is on record but the proof is missing,
  unquantified, alias-only, or not quotable. Fixable fast: surface
  the proof. (Its headline reading is governed by the single
  production rule below, not by this list.)
- **Skill gap** — nothing on record. Not fixable by editing text.
  Veto names what would close it (feature B2 + `gap_plan()`).
- **Contested** — the record contradicts the requirement (e.g. a
  stated years minimum the record does not meet). The veto feeder.

**How the taxonomy reads in the headline's two words** (the mapping
is defined in feature B4; it is stated here so the headline is never
wider than the spec, and B4's rule is the only production rule —
this paragraph restates it, it does not add a second one): per
requirement, *Supported* is not a "no" at all, an *evidence gap*
points toward **unproven**, and a *skill gap* or *contested*
requirement points toward **unqualified for this posting as
written**. Per job, the headline word exists only when a veto
fires, and it follows the most severe class present among the
posting's must-have requirements (contested > skill gap >
evidence gap): a veto whose must-haves carry only evidence gaps
answers *unproven*; any skill-gap or contested must-have makes
the answer *unqualified for this posting as written* — including
when the veto's named trigger class is thin evidence. Veto-class
labels never override that rule, and a job with no veto gets no
headline word. And the headline's
second half has no exemption: contested requirements also get a
named "what would change the answer" — the proof, the changed fact,
or the different posting — exactly as the skill-gap and
evidence-gap classes do.

The classification is deliberately conservative: it can mistake a
real-but-paraphrased history for an evidence gap (cost: one grill
question), and it is built to never mistake an absent proof for a
supported one (cost if it did: the honesty brand). The match tools
that report gaps at all (Teal, Jobscan, Rezi, Simplify, LinkedIn)
report missing items **categorised** — by skill type, section, or
keyword class: Jobscan's report separates hard skills, soft skills,
and other keywords, with frequencies, and LinkedIn publishes a
met/missing qualification list for a posting. None of the rows in
the §5 table, as checked 2026-10-15,
categorises by **proof state** — whether a missing-looking item is
on the user's record without proof, or not on record at all. The
nearest case is MaxCV (§5): it maps each requirement to evidence
in the CV versus not in the CV — a split by whether an item is on
record, not by proof state, because an on-record item is not
further split into proven and on-record-but-unproven. That
proof-state split, not categorisation itself, is the distinction,
and it is the only form of the claim this brief makes. (Earlier
versions of this paragraph said competitors report "one blended
list" and that LinkedIn reports a judgement "without the list";
both statements were false and are withdrawn — see §5 source notes.)

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
mechanisms, each graded as it actually stands after the audit round:

1. **Construction guards [ships].** The tailor and the cover-letter
   writer generate only from profile facts; skills the profile lacks
   come back as `missing_skills`, never inserted
   (`tailor.py`, `cover_letters.py`). This — not a gate — is what
   enforces the headline promise today.
2. **Traceability, approval, and the gate [mixed — read the
   grades].** (a) A per-line statement map that traces each tailored
   line to a profile source, with renderer-composed text tagged
   `system:template`, exists in `tailor_with_provenance()` — and is
   **[built, unwired]**: no core surface calls it in either tree, so
   no user can see it today (claim 4, corrected). Inside the
   function the map is not literally per line either: headings, the
   name/contact line, and date lines are skipped with no entry, and
   remaining untraced lines are assigned `profile:base` by fallback.
   (b) Tailoring shows a diff [ships]; the approved-variant save is
   **broken today** — its only caller passes the wrong types and the
   flow errors (claim 3, corrected), so "the approved variant is the
   one on record" is not a claim this brief makes until feature C2
   repairs it. (c) A standalone cover-letter honesty scan flags
   claims the profile text cannot back — numbers, names, and skills
   — and **blocks nothing**; it runs as a self-check and on display
   surfaces. (d) The blocking gate is a different, narrower check:
   `check_cover_letter_honesty()` tests veto keywords, claimed
   skills, and claimed years only. It never runs the honesty scan,
   so an invented metric or employer cannot block an application
   today. The gate also runs only on the confirm path, with a letter
   attached, and only when the governance framework checkout is
   present; when absent it disables itself silently. Feature C3
   makes the full scan the single gate — one scanner, one block,
   one proven-only pass rule — unconditional at every installation
   point (the C2 approval flow; the application confirm path, where
   roadmap initiative 0.5 installs it early; and packet assembly,
   apply handoff, and export re-scan), precisely because a brand
   promise cannot rest on a narrower check behind a conditional
   gate. Under feature C3 a
   factual claim passes only traced to an `approved` ledger entry
   with proof attached; a claim tracing only to an unverified
   entry or a grill answer blocks.
3. **The verdict record [ships in part, with limits].** Allow/block
   verdicts are appended through the governance adapter into the
   framework's log (`record_application_verdict()`) — **only when
   the framework checkout is present**; without it, recording
   returns not-recorded and the server's allow-path recorder is a
   no-op. The per-application experiment log
   (`experiment_ledger.py`) exists, but the apply path does not
   write verdicts to it; production code reads it for assignment
   lookups and offers a manual record tool. A single, unified,
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
  tracker, the graph, and the autofill on day one. (The cost of
  choosing this segment, and of deprioritising the highest-intent
  seekers, is priced at §8, risk 6.)
- **Volume users are not the design target, and are not written
  off.** They are the feeder segment: they run the most cycles, hit
  the failure the brand is built on first, and — for an open-source
  project — produce the stories, stars, and issues growth runs on.
  The product does not optimise for them; it welcomes them when they
  hit the wall. (The tension in expecting stories from users the
  brand has just refused is named at §8, risk 4.)
- **Secondary:** career changers. Their problem is delta — and their
  ledger is the emptiest, so the product's first honest output to
  them is a list of skill gaps. The roadmap's answer is that the
  delta report pairs a gap with its closing path where one exists
  (B3/B4); where no plan exists, the report says so and still names
  the smallest next step the user can take, so "not yet" never
  arrives empty-handed. (That this segment is also the one the
  classifier is most likely to misjudge is §8, risk 3.)
- **Acquisition — the named path.** A free local tool grows by
  arrival and sharing or not at all. The channels, in order of fit:
  (1) the interactive demo on the project site — **planned, not a
  present asset.** The strategy's primary channel is a demo where a
  visitor answers a grill and can be refused **before** any install.
  This package does not claim that demo exists today: the evidence
  behind it reviewed the site's spec copy — whose demo content is
  itself claims debt (item 2: the spec demo shows a salary question
  the grill cannot generate) — and one shipped radar demo
  component, not a running visitor grill flow. Worse, the live demo
  page today labels a hardcoded three-question widget "a real Veto
  grill… the product working"; that labelling is claims debt
  CD-16, a blocker, and correcting it is Phase 0 work. The refusal
  demo, including a delta-report view, is scheduled work (roadmap
  initiative 2.7) that lands once the delta engine exists to show.
  The demo is named as the bridge because it is the only surface
  that could carry a considered searcher over the install distance
  hosted and extension competitors do not impose — which is why the
  strategy depends on building it, and why nothing in this brief
  may describe it in the present tense until it ships. The demo's
  honest limit, stated now rather than after it is built: a fixture
  demo can show a refusal happening to a fictional profile and the
  shape of a delta report; it **cannot** show a visitor their own
  delta on their own history, because the local-first posture keeps
  their real data out of a hosted page. What it can honestly show
  is the mechanism and the wording; the personal version exists
  only after install and intake (§8, risks 5 and 9); (2) open-source discovery —
  the repo itself, MCP directories and registries, community
  job-search spaces where the refusal story is tellable; (3) the
  project owner's writing. Pretending the install distance does not
  exist would be the kind of claim this document exists to stop.

## 5. Competitive landscape

Full research with per-claim sources: `competitive-landscape.md`
(research seat, checked 2026-10-15); corrections from the audit
round carry their own sources in the notes under this table.
Summary table — competitor rows describe the products as they are
today, on their public record. **The Veto row is graded by the same
standard and carries its §6 status per cell.** [S] = ships,
[B] = bet, [P] = posture (a program fact outside this package's
evidence exhibits — claim 11).

| Product | What it owns | Profile model | Proof vs skill gap | Says don't apply? | Refuses unbacked claims? | Prep graded vs user evidence? | Price shape |
|---|---|---|---|---|---|---|---|
| Teal | Organize + tailor + job-specific prep in one workspace | Resume + versions | No — missing terms by category; AI generates bullets for them | No | No | No — job-specific sessions built from saved postings, feedback on response quality and delivery; not evidence-graded | Freemium, Teal+ paid |
| LinkedIn Premium | The hiring graph; rank vs other applicants; Job Match | LinkedIn profile text | No — publishes met/missing qualification lists; no proof-state split | No — steers to strong fits | No | No — job-specific prep from real job descriptions, with readiness score and feedback; not evidence-graded | Paid subscription |
| Jobscan | The ATS match score, job matching + tracker, and Auto Apply (launched June 2026) | One resume vs one posting; saved preferences for matching | No — missing items categorised (hard skills / soft skills / other keywords, with frequencies); no proof-state split | No — surfaces matched roles and steers by fit; review-before-submit is the **default**, not a requirement: its own pages state an optional auto-submit / Auto mode exists that the user can enable (checked 2026-10-15) | No — user approves generated edits | No — consumer mock-interview practice is sold as an **optional add-on, not included in a standard subscription** (job description + CV in, timed video/audio answers, feedback on answers and delivery plus a proposed answer; page published 2026-08-04, checked 2026-10-15); not evidence-graded | Freemium / paid |
| Yoodli | How you sound | None — session from a job title, a roleplay scenario, or an uploaded job description | No | No | n/a — writes no resume | No — delivery-focused per consumer reviews (vendor enterprise material also claims content scoring); not evidence-graded | Freemium / paid |
| LazyApply | Application volume | Form-fill data + resume profiles by plan tier (1 on Basic, 5 on Premium, 20 on Ultimate, on its own current pricing — checked 2026-10-15) | No — volume-first; its Job GPT fills applications from the user's information and a user can hold multiple resume profiles by plan, so it is not one same resume sent to every job; no proof-state split | No — the opposite | No | No | Paid per year on its own current pricing, checked 2026-10-15 on lazyapply.com: Basic $99/yr, 15 applications/day, 1 resume profile; Premium $149/yr, 150 applications/day, 5 resume profiles; Ultimate $999/yr, 1500 applications/day, 20 resume profiles; older lifetime-billing listings exist in secondary sources and are not relied on |
| Sonara | Automated apply under BOLD (the brand was acquired in 2024): on its own current site, continuous matching and applying to relevant openings on the user's behalf (checked 2026-10-15, sonara.ai) | Short profile + preferences (its site's own sequence: it gets to know you, finds jobs, applies for you) | No | No — the opposite: it applies for the user | No | No | Paid — no price is stated on the home page checked 2026-10-15, and no price figure is relied on |
| Rezi | The strict ATS resume | Document built in-editor | No — missing keywords | No | No — writes bullets from role + company; user may approve lines | No — ships consumer interview practice built from resume + job description, with transcript, score, and delivery feedback; not evidence-graded | Freemium / paid |
| Final Round AI | Help during the live interview | Resume + posting as inputs to a goal | No — debrief flags weak answers | No | No — supplies answers live | Partly — tailored to job, graded on answer quality, not evidence | Paid |
| Simplify | Free autofill across thousands of ATS platforms (vendor figure) | Form-fill profile | No — score + missing keywords | No — and submission is the user's, like Veto | No | No | Freemium / paid tier (Simplify+) |
| Jobright | AI matching feed with match scores, tailored resumes, an autofill/auto-apply agent, referrals | Resume-based profile | No — match score + missing keywords | No — steers by match score | No | No — copilot prep (Orion), not evidence-graded | Freemium / paid |
| Careerflow | Tracker + LinkedIn optimiser + resume/ATS workspace, application autofill, and a Job Fit Analyzer that tailors documents per job (vendor-claimed seven-figure user base; checked 2026-10-15, careerflow.ai) | Resume + LinkedIn profile | No — keyword and ATS gaps, and a named Skill Gap Analyzer; still no proof-state split | No | No | No — mock interviews with feedback on the top plan; not evidence-graded | Freemium / paid |
| Huntr | Tracker + AI tailoring + autofill workspace | Resume + form-fill data | No — match score across qualifications, responsibilities, and keywords | No | No — generates achievements and summaries | No | Freemium / paid |
| AIApply | End-to-end builder / scanner / auto-apply | Resume + preferences | No — missing keywords | No — the opposite (auto-apply) | No | No — mock prep plus a live Interview Buddy that supplies answers during the real interview; not evidence-graded | Freemium / paid (credits) |
| Resume Matcher | Free, open-source, local tailoring + ATS scoring | Resume | No — keyword gaps | No | No | No | Free, open source; runs locally if self-hosted |
| MaxCV | Truthful tailoring + ATS match score, with each requirement mapped to evidence in the CV versus not in the CV (checked 2026-10-15, maxcv.ai) | Master CV, uploaded once and reused per offer | No — its split is by record presence (in the CV / not in the CV), not by proof state: an on-record item is not split into proven versus on-record-but-unproven | No | **Yes, as a stated mechanism** — its FAQ states a hard fabrication ban (only skills and experience already in the CV are used); its feature copy states skills the user lacks are not added, risky claims are stripped, and softer claims wait for the user's approval | No — an interview cheat sheet for the role is included; it is not graded practice against the user's evidence | Free tier (tailorings without an account, more after free sign-up) + paid pack / per-30-days unlimited, per its site |
| Enhancv | Resume building at scale — vendor-claimed 10M+ job applicants, 15M+ resumes created, 11 years operating — with AI writing, ATS check, and one-click job tailoring (checked 2026-10-15, enhancv.com) | Resume + versions | No — ATS match shows terms present versus missing and gaps such as a bullet with no number; no proof-state split | No | Partly, as copy — its tailoring is stated to be built from the user's real experience only, with no invented facts, its writing help uses a placeholder rather than inventing a figure it cannot know, and tailoring changes are highlighted and not applied automatically; no blocking refusal mechanism is stated | No — its site bundles interview prep with building, checking, tailoring, and tracking; not evidence-graded | Free entry + paid plans; no price figure is relied on from the home page checked |
| JobCopilot | Auto-apply at scale — vendor-stated applications across 500,000+ company career pages, up to 50 applications a day on its top tier (checked 2026-10-15, jobcopilot.com) | Resume + screening answers per copilot; multiple copilots allow different resumes for different searches | No — matching and filtering; no proof-state split | No — auto-apply is the product; a review mode exists and the user can switch a copilot to auto-apply | Partly, as copy — its FAQ states auto-filled answers are generated from the data the user provided and that it does not invent information about the user; no stripping or blocking refusal mechanism is stated | No — its AI mock interviewer tailors questions by job title and description and gives feedback on content, relevance, and structure; not evidence-graded | Paid tiers (Premium / Elite in its FAQ) |
| LoopCV | Bulk auto-apply "loops" — server-side scanning of 30+ job boards, with Auto-Apply and Mass Apply (checked 2026-10-15, loopcv.pro) | CV + personal details + preferences per job search | No — stored CV and details are used for each application; Premium AI answers can tailor responses to job-specific questions; no proof-state split | No — the opposite; Auto-Apply can be disabled per search, leaving review / one-click apply | No | No — no prep product is stated on the auto-apply page checked | Free plan with a limited monthly application count + paid plans and extra credit packs, per its page |
| EarnBetter (now Earn Better by EarnIn) | Free job-search assistant: resume rewrite, personalised matches, per-job tailored documents, and interview prep (checked 2026-10-15, earnbetter.com) | Uploaded resume + profile and preferences | No — matches are ranked by fit; no proof-state split | No | No — it rewrites the resume; no refusal mechanism is stated on the site checked | No — a role-tailored cheat sheet and mock interview; not evidence-graded | Free — inside the EarnIn app, with no subscription or credit card, per its FAQ; the original launch was funded free (a $4.5M seed, per its launch post), so free in this space is not only a community posture |
| AIHawk | **Historical / pivoted row, not a current competitor:** bulk job-application automation in its original form; the repository that housed it had roughly 29,000 stars in the audit's record and about 32,000 on the repo checked 2026-10-15, which now redirects to a different project, and secondary summaries record the original job applier as archived / pivoting in 2026 | Resume + preferences (original form) | No | No — the opposite (original form) | No | No | Free, open source (MIT), locally run in its original form — its existence, at that star count, is why free + open-source + local applying cannot be treated as ground only Resume Matcher and Veto occupy |
| **Veto** | **The tool that refuses: no invented claims by construction [S]; proof-state labels [B]; a named delta [B]** | **Evidence ledger [B] — thin flat profile [S]** | **[B] — core matching is binary [S]** | **Yes [S] — score veto (this branch tree); classified veto with a path [B]** | **Partly [S] — by construction in tailoring; the standalone letter scan flags but does not block; the blocking gate checks skills/years/keywords only and is framework-conditional (see §3); resume-wide blocking at approval [B] — "backed" means proven in A1's sense: traced to an `approved` ledger entry with proof attached** | **[B] — craft grading [S]** | **Free, open source, local-first [P] — a posture Resume Matcher also holds; differentiating only in combination with refusal and the split** |

**Source notes for the corrected and new cells** (checked
2026-10-15; the audit's verification pass re-fetched the F3 sources
live): LinkedIn met/missing lists and Job Match —
linkedin.com/business/talent/blog/product-tips/linkedin-how-you-match,
corroborated by Fast Company's Job Match coverage
(fastcompany.com/91329471). LinkedIn job-specific prep —
linkedin.com/help/learning/answer/a9308146. Teal prep —
tealhq.com/tools/ai-interview-practice. Rezi prep —
rezi.ai/posts/how-to-use-ai-for-an-interview. Jobscan Auto Apply
(2026-06-10) — jobscan.co/blog/auto-apply/; Jobscan categorised
missing items — jobscan.co/blog/hard-skills-examples/ and
jobscan.co/lp/ats-wrapper-2. Yoodli job-description sessions —
finalroundai.com/blog/yoodli-review-pros-cons. Simplify scale —
the Chrome Web Store listing for Simplify Copilot. Sonara,
LazyApply, and Careerflow — see the round-2 methods note below:
each of those rows is sourced there from the product's own
current page, and the earlier secondary sources for them are
withdrawn and not relied on.
Jobright — hirecarta.com/blog/jobright-review and
jobscan.co/blog/jobscan-vs-jobright/. Huntr — huntr.co and
jobscan.co/blog/jobscan-vs-huntr/. AIApply —
aiapply.co/compare/aiapply-vs-sonara. Resume Matcher —
scored.tools/blog/huntr-vs-resume-matcher-best-ai-job-application-tools/.

**Round-2 methods note — check date and source per corrected or
new row (all fetched 2026-10-15; primary sources only, and no
absolute is stated beyond what the source itself states).**
Jobscan prep and Auto Apply — Jobscan's own pages:
jobscan.co/ai-interview-practice (page details stamp: published
2026-08-04; the add-on sentence is in its FAQ) and
jobscan.co/blog/auto-apply/ (published 2026-06-10) for the launch
and the review flow, plus jobscan.co/blog/jobscan-vs-simplify/
and jobscan.co/blog/auto-apply-job-tools/ for the auto-submit
sentence (review is the default; an optional auto-submit setting
exists) — the launch page's own approval wording and the
comparison pages' auto-mode wording are both Jobscan's, and the
cell states the default/optional structure that reconciles them
instead of picking the half that suits the table. LazyApply —
its own home/pricing page, lazyapply.com, checked 2026-10-15
(resume profiles 1 / 5 / 20 by tier; per-year prices and per-day
application caps as shown on the check date: Basic $99/yr,
15 applications/day; Premium $149/yr, 150/day; Ultimate $999/yr,
1500/day). Sonara —
its own current home page, sonara.ai (continuous matching;
applies on the user's behalf); the acquisition fact is BOLD's
2024 company-history record as summarised in the round-1
refutation — **the earlier February-2024 shutdown sub-claim is
not repeated in this brief: the source that carried it has
removed that precision as unsupported, so the brief states the
acquisition and the current offer, and no shutdown date or
cause.** (The previous Sonara source, a rival's comparison page,
is withdrawn as a source for this row.) Careerflow — its own
home page, careerflow.ai, checked 2026-10-15 (AI Resume Builder,
Job Fit Analyzer tailoring documents per job, AI Application
Autofill, job tracker, and a Skill Gap Analyzer listed in its
plan features; the earlier secondary review source for this row
is superseded by the vendor's own page). MaxCV — maxcv.ai in full
(hero, how-it-works, pricing, FAQ). Enhancv — enhancv.com home
page (scale figures are the vendor's own claims and are labelled
as such in the row). JobCopilot — jobcopilot.com home page and
jobcopilot.com/automate-job-applications/ FAQ (application counts,
multiple copilots, per-job tailoring on its top tier, the
no-invention FAQ answer, its mock interviewer page for the prep
cell). LoopCV — loopcv.pro/autoapply/ (boards, Mass Apply,
per-search disable, credits). EarnBetter — earnbetter.com
(current Earn Better by EarnIn page and FAQ; the seed figure is
from its own launch post). AIHawk — the GitHub repository record
checked 2026-10-15 (the original job-applier repo now redirects
to a different project; star counts in the row are the audit's
roughly-29,000 figure and the roughly-32,000 shown on the checked
repo) plus secondary summaries of its 2026 archive/pivot, which
the row labels as secondary.

Open ground — **scoped to the twenty competitor products in this
table as now constituted**, on their public record as checked
2026-10-15: no checked competitor combines the evidence-ledger
profile, the proof-state split (on-record-but-unproven versus
not-on-record, across the four classes), refusal of unbacked
claims as a stated mechanism, a do-not-apply verdict with the
reason and the path, an inspectable verdict record showing its
own overturn data, and prep graded against the user's own
evidence and driven by that delta. Stated item by item, most of
the set is **not** open: refusal as a stated mechanism is occupied
by MaxCV; requirement-to-evidence mapping is occupied by MaxCV in
record-presence form; no-invention copy is occupied by JobCopilot
and Enhancv as well. What remains unoccupied, per this table, is
the **combination** in §2, with MaxCV named as the nearest
occupant and the narrowing stated there. The claim
is scoped to this table, not to the market: products outside the
table were not checked, the table must be re-checked before any
public use of this paragraph, and the six rows added in this round
(MaxCV, Enhancv, JobCopilot, LoopCV, EarnBetter, AIHawk) are a reminder of how fast
the set changes. Every element of the combination is a Veto **bet or
partial today** — the ground that remains is open, and Veto has not taken it
yet. That is what the roadmap is for.

Contested ground (do not claim as new): per-job tailoring with a
score; "know your fit" (LinkedIn owns it with applicant-pool data
Veto does not have); approve-before-send in general form (Jobscan,
Rezi, Simplify — Jobscan's Auto Apply defaults to review, which
the brief once overstated as an every-submission approval rule;
its optional auto-submit mode is exactly the contrast Veto's
always-human posture can honestly use, stated that way and no
wider); refusal / fabrication-ban / no-invention wording in
general form (MaxCV's hard fabrication ban, JobCopilot's and
AI Applyd's no-invention copy, Enhancv's real-experience-only
tailoring); requirement-to-evidence mapping in record-presence
form (MaxCV); job-specific prep in general form (Final Round AI, Teal,
LinkedIn, Rezi, Jobscan, JobCopilot, EarnBetter); free, open-source, local-first tailoring and
scoring (Resume Matcher; AIHawk's original form for free,
open-source, locally run applying); free as a funded offer, not
only a community posture (EarnBetter); "gets to know you" phrasing (Sonara,
Teal). Veto's defensible versions are the narrower ones stated in
§2–§3.

## 6. Claims register — what is true today, what is a bet

Checked against the code audit, and re-checked against both code
trees in rework round 1. "Ships" means wired into a user-facing
surface (MCP tools, CLI, web UI, dashboard). "Built, unwired" means
real, tested code in an initiative package with no user surface yet —
it may be described as built, never as available. Unless an entry
says otherwise, grades are against this branch tree
(wt-veto-differentiator); live-tree (job-apply-mcp) differences are
stated inside the entry.

| # | Claim | Status today | Evidence |
|---|---|---|---|
| 1 | Per-application grill with quantify / gap / logistics / motivation questions; application waits for answers (when `grill_on_apply` is on and the channel is not `off`) | **Ships, with the conditions stated — and one more, added in this round:** on the apply-gate path the session is created from a stripped job dict (`description: ""`, no requirements or snippet), and question generation reads only posting text, so a gate-created session produces logistics and motivation questions only — no gap or quantify questions at all. The full question set requires a session first started through a full-detail path (e.g. `grill_start_for_job_id()`) | `grill.py: generate_questions()`; apply gate in `server.py: apply_to_job()` (stripped dict at `server.py:854-863` in this tree) |
| 2 | Fit score with per-axis breakdown and a veto below the bar — plus a second veto: 3+ axes scored on unknown defaults (the insufficient-signal rule) | **Ships in part, by tree (corrected).** This branch tree: the score veto only. The insufficient-signal veto ships **only in the live tree** and does **not** ship in the tree these documents live in; earlier versions of this register claiming it as shipped here were wrong. Weights: the axes listed are the static defaults of this tree; in the live tree the default path resolves weights through the model card when a personalised card is active (gated by evidence and human approval), so the unqualified fixed-weights wording is also corrected | This tree: `match.py: score_job()` (axes 50/15/15/15/5, veto < 60 at `match.py:336`), `radar.py` renders the breakdown. Live tree only: `job-apply-mcp/match.py:133` (`_INSUFFICIENT_SIGNAL_AXES = 3`), `:594-595` (`signal_veto`); model-card weights at `job-apply-mcp/match.py:20-27,544-550` |
| 3 | Tailoring shows a diff; the approved variant is the one on record | **Broken today (was: Ships).** The diff half ships. The approval half has no working save path: the only non-test caller passes the wrong types against the function's signature and then treats the returned `Path` as a dict, so the flow writes a malformed payload and errors. No other surface can save an approved variant at all (web UI lists/loads only; the MCP tailor tool has no approval step). A working approval flow is feature C2's work — repair plus build, not polish | `tailor.py: tailor_with_diff()` (web UI: `webui.py:310-313`); broken caller: `dashboard.py:536` against `tailor.py:483-510: save_approved_variant(job_id: str, resume_md: str, cover_letter: str) -> Path` |
| 4 | Tailored lines trace to sources — profile sources per line, renderer-composed text tagged `system:template` so it cannot pass as the user's words | **Built, unwired (was: Ships).** The function exists but has zero callers in any core surface in either tree; its only production callers are the unwired i05 packet/studio, so no user can see a provenance map today. Inside the function the map is also not literally per line: section headings, the name line, any line containing `\|` (the contact line), and date lines are skipped with no entry, and remaining untraced lines are assigned `profile:base` by fallback rather than flagged as untraced | `tailor.py:277: tailor_with_provenance()`; caller grep across `server.py`/`cli.py`/`webui.py`/`dashboard.py` in both trees: zero hits; skipping at `tailor.py:334-340`, fallback at `tailor.py:380-383` |
| 5 | The tailor cannot add skills the profile lacks | **Ships** | `tailor.py` returns them as `missing_skills`, never inserted |
| 6 | Cover letters are scanned for claims the profile cannot back; unsupported claims can block an application | **Ships, with larger limits (corrected).** The standalone scan ships and flags — including numbers/metrics and proper nouns — as a self-check and on display surfaces; it blocks nothing. The blocking gate never runs that scan: its honesty layer checks veto keywords, claimed skills, and claimed years only, so an invented metric or employer in a letter **cannot block an application today**. The gate also runs only on the confirm path, with a cover letter attached, and only when the framework checkout is present. Blocking on the full scan is feature C3's bet: under feature C3 a factual claim passes only traced to an `approved` ledger entry with proof attached; a claim tracing only to an unverified entry or a grill answer blocks | Scan: `cover_letters.py: honesty_scan()` (numbers/proper nouns at `:303-452`), callers at `cover_letters.py:253,550,659`, `dashboard.py:547`, `webui.py:344` — none blocking. Gate: `governance/adapter.py:616-680: check_cover_letter_honesty()` (keywords `:637-645`, skills `:652-660`, years `:661-672`); no `honesty_scan` caller in `adapter.py` or `server.py` in either tree |
| 7a | Allow/block verdicts are recorded | **Ships, with limits (corrected).** Recording is framework-conditional: without the framework checkout, recording returns not-recorded and the server's allow-path recorder is an explicit no-op. The experiment-ledger leg is not written by the apply path: no production caller records verdicts to it; the module is read for assignment lookups and offers a manual record tool | `governance/adapter.py:362-375: record_application_verdict()` returns `{"recorded": False, ...}` when the framework is unavailable; `server.py` allow-path recorder ("No-op when the governance framework is not installed"); `experiment_ledger.py:131-147` (manual tool), read at `funnels.py:159-171` |
| 7b | A unified verdict record the user can inspect | **Bet** | No single product surface unifies these records today (audit §5) |
| 8 | Mock interviews with a published rubric; salary negotiation sims incl. hard modes | **Ships** | `mock_interview.py`, `initiatives/i06/rubric.py: score_answer()`, `soft_skills.py: negotiation_sim()` |
| 9 | Who-do-you-know finder + warm-path drafts; **those referral/network drafts are never sent by Veto** (scoped in round 2 — the unscoped headline "nothing is ever sent" was wrong: a separate, wired, approval-gated follow-up send exists, see CD-11 as rewritten) | **Ships, as scoped** | `referrals.py: find_referrals_data()`, `network_crm.py: warm_path_to()` (the i07 package's `plan_warm_path()` is built, **unwired** — not evidence for this claim). The follow-up send that does exist: `followup.py: send_followup()` → `email_sync.py: send_followup()`, a server-plugin MCP tool that sends via Gmail only with a genuine interactive approval for the exact recipient, subject, and body |
| 10 | The submit click is always the user's | **Ships (architecture)** | `browser_apply.py` has no submit path; `ats_apply.py` is preview-only; `apply_to_job()` returns the URL for the user to finish. Scope note (round 2): this claim covers the submit click only. The scheduled queue path around it — `apply_queue.py`, with scheduled-for items, a queue-run invocation whose confirm is preset, and browser form-fill / resume upload under `VETO_BROWSER_APPLY=1` — is a retained surface named in §7 item 6, and its exposure is dispositioned there and by roadmap initiative 0.9; no sentence in this brief may use claim 10 to imply that scheduled path has been examined and cleared |
| 11 | Free, open source, local-first; no user data to author infrastructure | **Posture (program fact)** — attested by the project's public-release program (2026-09-14), which sits outside this package's evidence exhibits; Exhibits D/E neither confirm nor refute it, and no product claim in this brief rests on it beyond posture | Public-release program record (outside Exhibits D/E) |
| 12 | The profile is an evidence ledger | **Bet** — thin core today (flat fields; up to two quantified wins per role from the wizard's opt-in `--grill` mode only — the default setup flow never calls `collect_grill()`, so a default profile captures zero wins); a real evidence model is **built, unwired** | Core: `wizard.py: collect_grill()` (opt-in flag at `wizard.py:858`, call at `:877-878`). Unwired: `initiatives/i04/evidence_map.py: build_evidence_map()`, `initiatives/i05/evidence_library.py`; packet approval: `initiatives/i05/packet.py: approve_packet()` |
| 13 | The profile deepens with use (grill answers, practice results write back) | **Bet** — no write-back exists today | Audit §2, §6: answers stay in `grill_sessions.json`; practice goes to i06 history only |
| 14 | Delta split: evidence gap vs skill gap, per job, in the product taxonomy (§3) | **Bet** — core matching is binary (listed or missing); a three-way split is **built, unwired** (i04 statuses `supported` / `grill_question` / `gap`; the product taxonomy in Pillar 2 is the reconciliation feature B2 implements). The fourth class, **contested**, has no built code anywhere — it is bet only, and §1 now says so | `initiatives/i04/evidence_map.py`; core: `skill_gaps.py: analyze_gaps()` |
| 15 | Grill answers feed tailoring | **Bet** — claimed in docs and site today, **not true in core**; the only consumers of the answers today are the unwired i05 packet and a web-UI display | `grill.py: get_qa_pairs()` — no caller in `tailor.py` / `cover_letters.py`; consumers: `initiatives/i05/packet.py`, `webui.py: _h_grill_qa_pairs()` (display only) |
| 16 | Mock interviews built from a job's gaps; answers graded against the user's evidence | **Bet** — questions come from the posting's likely questions or role banks; grading is answer-craft heuristics: `_score_feedback()` plus the shipped i06 rubric, which receives the answer text and the candidate's own questions only — no profile, ledger, or delta is passed, so nothing grades against the user's evidence | `mock_interview.py: start_mock_interview()`, `_score_feedback()`, rubric call at `mock_interview.py:604-607` |
| 17 | A daily companion check-in that nudges you to feed it jobs | **Bet** — the pieces ship (daily top five, action inbox, follow-up drafts, digests, streaks, outcome nudges) but no scheduled loop assembles them | `briefs.py: daily_top_five()`, `action_inbox.py: inbox()`, `followup.py: followups_with_drafts()`, `notify.py`, `streaks.py`, `outcome_nudges.py` |
| 18 | Fit shown as a green/amber/red gradient | **Bet** — directed for the dataviz (program history; the audit records only the non-implementation), **not implemented**; radar is single-colour with a red veto state | `radar.py` (one amber polygon, red veto); `site/src/demos/radar.tsx` (binary) |
| 19 | Delta trending over time per role family | **Bet** — outcome events and practice history exist; no delta time series | `outcomes.py`, `initiatives/i06/longitudinal.py`, i04 `career_graph.py` (unwired) |
| 20 | Profile claims carry a proof state from intake (unverified until proof attached) | **Bet** — intake is flat self-reported fields today; nothing marks or checks them | Audit §1; feature A5 |

### Claims debt — public statements to correct, before any launch

The marketing site and docs currently state things the code does not
support. The list has four layers: the original thirteen items
(CD-01…CD-13, from the code audit's fourteen claim risks), nine more
found by the adversarial audit (CD-14…CD-22), three more found by
the re-sweep in rework round 1 (CD-23…CD-25), and seven more found
in rework round 2 (CD-26…CD-32), with locations and scope added to
CD-01, CD-02, CD-05, CD-14, and CD-22 and CD-11 rewritten (its
stated code reality was itself false). **Round-2 sweep method —
changed because the list missed surfaces in two consecutive
audits:** the round-2 sweep did not start from a list of known
files. It swept by **claim concept**: a grep for guarantee
vocabulary — "fail closed" / "fail-closed", "never", "every",
"always", "guarantee", "exactly", "auto-", "no override",
"is written to" — over the **entire** live site source tree
(`job-apply-mcp/site/src`, every page, spec, and demo script,
including `crew.ts`, `win.tsx`, and their siblings) and the whole
of `job-apply-mcp/docs`. The sweep returned 579 hit lines across
72 files (248 in `site/src`, 331 in `docs`). Every hit is
dispositioned in this list: as an existing CD item (named), as a
new CD item (CD-26…CD-32), as accurate against a named code fact,
or — for the internal decision, contract, plan, and report
documents under `docs/` — as design-record language that makes no
public product statement, in the sweep disposition table that
follows the numbered list. Ordinary quantifier uses in
non-guarantee prose and code comments were read in context and are
dispositioned in that table by file class, not silently dropped.
Each numbered item states its surface(s), the exact claim, the
code reality, and a severity. **Order of operations (a decision, not a note): the
corrections land first (roadmap Phase 0), before this positioning
ships anywhere public.** An honesty brand invites checking; the
product's own site must pass the check first.

1. (CD-01) "Grill answers feed tailoring" (`docs/grill.md`, site grill spec;
   **additional location added in round 2:** `site/src/pages/DemoPage.tsx` —
   "(In the real grill these arrive over WhatsApp, and your answers shape
   the resume tailoring.)", which repeats this item's claim and CD-25's
   wrong default channel on the same page CD-16 flags)
   — false in core (claim 15; audit risk 2). Fix by building it (roadmap Phase 3)
   **and** correcting the copy until it lands.
2. (CD-02) The grill demo shows a salary question; `generate_questions()` has
   no salary kind (audit risk 3). **Additional locations added in
   round 2:** `site/src/App.tsx` — its "What is the grill?" FAQ lists
   salary among the question kinds, and its grill feature card lists
   "missing skills, unquantified wins, salary, logistics" — the same
   non-existent salary kind, on surfaces this item did not name.
3. (CD-03) Site fit-score spec: "weights are fixed constants, never learned"
   — contradicted by the shipped, gated model-card design
   (`model_card.py`); the honest claim is "static until evidence and
   a human approval say otherwise" (audit risk 5).
4. (CD-04) Site skill-gaps spec: one-click close, instant re-rank, streak
   updates, gaps "mapped to a mock-interview pack", a
   `veto gaps --role …` command, percentage frequencies — none
   exist; closing requires an evidence note (audit risk 6).
5. (CD-05) Site verdict-ledger spec names a ledger path/fallback the code
   does not implement (claim 7a's records live elsewhere — and claim
   7a is itself framework-conditional, which the spec also does not
   state; audit risk 13). **Expanded in round 2 — the item as
   previously written covered only the path/fallback name; the
   universality claims on the same and neighbouring surfaces are
   part of this item now:** `site/src/pages/specs/verdict-ledger.ts`
   lede ("Every allow/block decision is written to a verdict
   ledger") and its "Every decision logged" point (which adds that a
   user can ask why "a search skipped, an application vetoed, and
   get an answer") and its FAQ ("doctor tells you which one is
   active"); `site/src/App.tsx`'s verdict-ledger card ("Every pass
   and every block lands in an auditable ledger. Ask why anything
   happened and get an answer"); the crew-govern card lines in
   `App.tsx` ("every veto logged" — see also CD-26); and the
   Changelog page's **Shipped** "Decision ledger" entry ("Every
   allow/block decision Veto makes is written to a verdict ledger
   on your machine"). Code reality for the expansion: recording is
   framework-conditional (claim 7a) — with the framework checkout
   absent, `record_application_verdict()` returns not-recorded and
   the server's allow-path recorder is a no-op, so no decision is
   written at all; the only fallback in the code fires inside a
   successful framework load when its runs directory is unwritable
   and creates no record when the checkout is absent; no production
   path records search decisions to this ledger, so "a search
   skipped" is not answerable from it; and `doctor.py` in both trees
   contains no verdict or ledger check at all (its checks are
   profile, compliance, Playwright, sessions, preferences, boards),
   so the doctor cannot tell a user which log is active. Correcting
   only the path name would leave all of this standing.
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
    bet (audit risk 10). Locations include the Changelog page's
    **Shipped** entry "A daily routine for your job search" ("Veto
    now runs a daily loop…"), which states the assembled loop as
    running today; no scheduled loop assembles the pieces.
11. (CD-11) **[Rewritten in round 2 — the previous version of this
    item was itself wrong, and is withdrawn in that form.]** The
    previous text directed Phase 0 to correct "any wording implying
    Veto contacts people, sends outreach, or submits applications —
    all three are false by architecture". That code reality is
    false for sending: a wired, approval-gated follow-up send
    exists — `followup.py: send_followup()` delegates to
    `email_sync.py: send_followup()`, which sends via Gmail only
    with a genuine interactive approval for the exact recipient,
    subject, and body (a caller-asserted confirm flag is not proof
    of approval; without an interactive terminal the send is
    refused); `followup` is in the server's plugin list and the send
    is exposed as an MCP tool. The site copy this item would have
    directed Phase 0 to "correct" is in fact accurate:
    `site/src/pages/specs/followups.ts` states that sending needs
    the exact recipient, subject, and body approved and that the
    bytes approved are the bytes that send, and
    `site/src/pages/specs/email-sync.ts` states there is no
    auto-send and that the user confirms the exact draft — **those
    surfaces are not debt and must not be stripped.** What actually
    remains wrong, and is this item's corrected scope: (a) any
    wording that states the scoped truths without their scope —
    that **referral and network drafts** are never sent (claim 9, as
    scoped) and that **no application is ever submitted** by Veto
    (claim 10) — as a blanket "Veto never sends anything" claim,
    which the follow-up send falsifies; and (b) any wording implying
    Veto submits applications or contacts people outside that one
    approval-gated follow-up path. If a surface's copy turns out, on
    the corrected facts, to be accurate, it is left alone — this
    item no longer instructs a correction sweep against true copy.
12. (CD-12) Evidence-map / evidence-library / career-graph / packet-approval
    features described as available to users — all four are built,
    unwired (claims 12 and 19; audit risk 14). Locations include the
    Changelog page's **Shipped** entries "The application studio"
    ("an evidence library of your real achievements") and "Fit
    decoder and career graph" ("a map of how your skills connect to
    target roles"), which list both as shipped product.
13. (CD-13) "Veto learns you over time / your profile gets deeper with use"
    wording anywhere it appears — no write-back exists, so the
    profile today is what the user typed on day one (claim 13;
    audit risk 1). This completes the original mapping: items 1–13
    cover all fourteen audit claim risks.
14. (CD-14) **[Blocker]** Fail-closed veto screen with no override,
    guaranteed. Surfaces: `site/src/pages/specs/veto-gates.ts` ("Every
    confirmed application passes a constitutional veto screen… A veto
    hit, or a failed veto check, blocks the action, fail-closed";
    "There is no bypass switch"; FAQ: "Can I override a veto? — No,
    by design") and the home page (`site/src/App.tsx`: "A trip blocks
    it outright, and only a human can clear a veto"); a related
    "no override switch" line appears in the honesty-check spec's
    demo script. Code reality: with the framework checkout absent the
    gate returns `{"enabled": False}` and the caller proceeds
    (`governance/adapter.py:712,724`) — the opposite of fail-closed —
    and an override path exists: the blocked response itself directs
    the user to the framework's `overturn_verdict` with a reason
    (`adapter.py:762`). CD-08, the nearest original item, covers the
    honesty check's scope only; it says nothing about the veto
    screen's universality, fail-closed behaviour, or overrides.
    **Additional location added in round 2:** `docs/compliance.md`'s
    fail-safe section states the same guarantee in product docs (a
    failed veto check blocks the action), while its own audit
    section states the qualified truth for the ledger ("written via
    the framework when available") — the fail-safe sentence is this
    item's, the ledger sentence is accurate as qualified and is not
    debt. The crew subsystem's separate version of this guarantee
    is CD-26, and the drip queue's is CD-30.
15. (CD-15) **[Blocker]** Cover-letter suppression guarantee: a draft
    that fails its honesty scan "never reaches you". Surfaces:
    `site/src/pages/specs/cover-letters.ts` ("the scan result must be
    empty. A letter that fails its own audit never reaches you"),
    `site/src/pages/DocsPage.tsx` ("flags invented numbers,
    companies, and skills before you see the letter"), and
    `site/src/App.tsx` ("honesty-scanned three ways before you ever
    see them"). Code reality: `draft_cover_letter()` returns the
    letter and its scan flags together, unconditionally
    (`cover_letters.py:253`); there is no suppression anywhere in the
    draft path — the spec's own FAQ says the opposite ("You see the
    flags, sentence by sentence"). CD-08 covers which artefact is
    checked, not draft suppression.
16. (CD-16) **[Blocker]** The live demo labelled as the real product.
    Surface: `site/src/pages/DemoPage.tsx` ("A real Veto grill,
    shrunk to three questions… Answer honestly. Most people get
    refused. That's the product working."). Code reality: the
    widget's verdict is a self-contained function
    (`DemoPage.tsx:23-39`) — flat refusal on reported years,
    Kubernetes, or work authorisation — that calls no product code;
    the real grill derives its questions from a profile/posting pair
    and the product's refusal is the fit-score veto. The interactive
    refusal demo is roadmap work (initiative 2.7), not a present
    asset (§4). CD-02 covers a salary question in a different spec's
    demo script, not this labelling.
17. (CD-17) **[Major]** The veto-to-go package sold as current
    product. Surface: `site/src/pages/specs/veto-to-go.ts` ("One
    command installs Veto", a real PWA with manifest, service
    worker and offline page, an IndexedDB offline action queue,
    encrypted backups, opt-in end-to-end encrypted device sync).
    Code reality: the whole i10 package is built, unwired — its own
    integration notes state the modules do not touch `cli.py`,
    `webui.py`, or `dashboard.py` and the MCP registration snippet
    is "provided but NOT applied"
    (`initiatives/i10/integration_notes.md:3-7`); the documented
    phone path is the web dashboard over home Wi-Fi or a private
    mesh VPN with a login token (`docs/phone-access.md`). CD-12's
    list is closed to four i04/i05 features and does not name i10.
18. (CD-18) **[Major]** Calendar handoff presented as an end-to-end
    working feature. Surfaces: `site/src/pages/specs/calendar-handoff.ts`
    ("the handoff payload goes to your connected calendar, which
    does the writing", with demo commands `veto calendar
    propose-prep …` / `veto calendar handoff --draft … --confirm`)
    and the Changelog page's "Calendar handoff" entry. Code reality:
    those commands exist in no CLI registration and no core surface
    references the handoff functions (grep across `server.py`,
    `cli.py`, `webui.py`, `dashboard.py`, `briefs.py`, `followup.py`:
    zero); the i09 module itself states the calendar write happens
    "at the wiring layer" and "this module never touches a
    calendar" — and that wiring layer was never built
    (`initiatives/i09/calendar_handoff.py`,
    `initiatives/i09/integration_notes.md`).
19. (CD-19) **[Major]** Mentor consent handshake presented as
    `veto mentor` commands. Surfaces:
    `site/src/pages/specs/consent-handshake.ts` (demo: `veto mentor
    request --mentor …`, `veto mentor respond … --decision approve`)
    and the Changelog page's "Consent handshake" entry. Code reality:
    no such commands exist in the main CLI, which registers only the
    core `mentors` category; the real entry point is an in-package
    module (`python -m initiatives.i07.cli intro request …`), main-CLI
    registration was left as a snippet for a later integration sweep,
    and web/phone were explicitly deferred
    (`initiatives/i07/cli.py:8-9`,
    `initiatives/i07/integration_notes.md`). Partial credit, stated
    for accuracy: the sealing logic is partly reachable through a
    lazy i07 import in core `mentors.py` — the user-facing handshake
    flow the page demonstrates is what does not exist.
20. (CD-20) **[Major]** "Auto-updated" application stages and
    "automated" rejection handling. Surfaces: `site/src/App.tsx`
    ("application stages auto-updated") and
    `site/src/pages/specs/email-sync.ts` FAQ ("moves the application
    to rejected… Closure, automated"); an additional location found
    in the round-1 re-sweep: `site/src/pages/specs/lifecycle-analytics.ts`
    FAQ ("Proposals apply only on high-confidence matches"), which
    drops the approval condition the same way. Code reality: the
    default is propose-only (`apply_updates=False`); applying updates
    requires a genuine interactive approval bound to the exact
    proposed updates (`email_sync.py:509-528`). Availability is also
    overstated by silence: the whole Gmail path runs through an
    external CLI that is not publicly distributed
    (`email_sync.py:61,215`; the README discloses it, the spec page
    does not). CD-11 covers outbound contact wording, not
    inbound-driven stage mutation.
21. (CD-21) **[Major]** Product docs present removed boards as
    working. Surface: `docs/compliance.md` (LinkedIn, Indeed,
    Glassdoor, ZipRecruiter listed as a working scraping tier —
    "Works until it doesn't" — with standard-mode and fill-only
    rules written as descriptions of working capability). Code
    reality: `providers/` contains no LinkedIn, Indeed, or
    ZipRecruiter module (removed in the post-hardening pass;
    `providers/_contract.py:80`), Glassdoor is a locked stub that
    reports itself unavailable, and the site's own multi-board spec
    admits both facts (`site/src/pages/specs/multi-board-search.ts:48-50`).
    This branch tree's copy of the same document is already
    corrected; the live tree's is stale. No original CD item
    addresses board coverage.
22. (CD-22) **[Minor]** "Grill answers feed tailoring" repeated in
    locations CD-01 does not name, and extended to a different
    consumer. Surfaces: `site/src/pages/specs/tailoring.ts` ("Grill
    answers plug in — …quantified wins land in the bullets,
    motivation lands in the letter"; demo: "grill answers folded
    in"), `site/src/pages/specs/resume-diffs.ts` ("your quantified
    wins land in the bullets automatically"), and
    `site/src/pages/specs/fill-only-apply.ts` FAQ ("Screening
    questions are filled from your profile and grill answers where
    possible" — the form-filling variant). Code reality: claim 15
    (no caller in `tailor.py` / `cover_letters.py`); for the
    form-filling variant, `browser_apply.py` contains no reference
    to the grill at all. The claim itself is CD-01's; the locations
    and the form-filling extension are new.
23. (CD-23) **[Major]** Approval-gate copy for tailored variants
    (round-1 re-sweep find). Surfaces: `site/src/App.tsx` ("Line-by-line
    diffs of every tailored variant, with an approval gate. Nothing
    ships unapproved"), the Changelog page's **Shipped** "application
    studio" entry ("line-by-line diffs you approve before anything
    is final"), and the site diff demo's label ("Side-by-side resume
    diff with an approval gate"). Code reality: claim 3 as corrected
    — the only variant-save caller is broken
    (`dashboard.py:536`), and no surface offers a working approval
    action (web UI lists/loads variants only; the MCP tailor tool
    has no approval step). The diff itself ships; the approval gate
    the copy promises does not work today.
24. (CD-24) **[Minor]** An absolute network-traffic claim (round-1
    re-sweep find). Surface: `site/src/App.tsx` FAQ ("Where is my
    data?" — "the only other network traffic is the job-board
    searches you trigger yourself"). Code reality: the core privacy
    claim beside it holds (profile, applications, and ledger live in
    local files and are not uploaded to author infrastructure), but
    the "only" enumeration is false: company briefs run web searches
    (`briefs.py: company_brief()`), BYOL fetches a pasted posting URL
    once, grill and follow-up flows use the user's configured
    Gmail/WhatsApp channels, and notifications can post to
    user-configured webhook/ntfy endpoints (`notify.py`). All of it
    is user-triggered or user-configured; none of it is board search.
25. (CD-25) **[Minor]** Wrong default grill channel in the product
    docs (round-1 re-sweep find). Surface: `docs/grill.md` (channel
    table marks `whatsapp` as "(default)" and a section heading
    calls WhatsApp the default, "the only proactive channel"). Code
    reality: the default channel is `chat`
    (`grill.py:93: data.get("grill_channel", "chat")`); WhatsApp is
    an opt-in channel. This branch tree's copy of the same document
    already states the default correctly; the live tree's does not.
26. (CD-26) **[Major]** The crew spec repeats CD-14's guarantee for a
    different subsystem, with its own additional guarantees
    (round-2 concept-sweep find; the round-1 audit's A-01, downgraded
    to major on refutation because roadmap 0.1's gate-time repeat
    sweep is designed to catch a listed claim's stray locations —
    this item names the surface so the sweep does not have to rely
    on that). Surfaces: `site/src/pages/specs/crew.ts` (lede:
    agents are "veto-screened before work"; point: "The verdict is
    written to a ledger"; limits: "Governance vetoes fail closed.
    If the framework is unreachable, you get compliance-only mode,
    not freedom"), the crew card lines in `site/src/App.tsx`
    ("Every plan reviewed, every veto logged"), and the persona
    labels in `site/src/demos/crew.tsx` (e.g. the chief-of-staff
    persona's "Never clears a veto"). Code reality: `crew.py`'s
    `run_agent()` — when the framework is unavailable the work still
    runs and returns success in compliance-only mode, with no veto
    screen, no adversarial review, and no verdict written to any
    ledger (`"verdict": {"recorded": False, …}`); only the
    deterministic compliance pattern list can block in that mode.
    So in the framework-absent install, all three crew guarantees —
    fail-closed, adversarial review, ledger write — are false, on a
    code path (`crew.py`) distinct from the apply gate CD-14 cites.
27. (CD-27) **[Major]** The referral and network demos show a
    second-degree person chain no code produces (round-2 find; the
    round-1 audit's A-03). Surfaces: `site/src/pages/specs/referrals.ts`
    demo ("Maya R.: platform eng (ex-colleague, 2nd degree)",
    "J. Chen: hiring manager, platform (via Maya)", "+ warm path:
    you > Maya R. > J. Chen"; point: it "traces 1st- and 2nd-degree
    routes through your network: who to ask, and who they can
    introduce you to") and `site/src/pages/specs/network-crm.ts`
    demo ("+ warm path to TargetCo: you > Priya S. > J. Chen
    (hiring mgr)"; warm paths "reusing the referral radar's company
    matching"). Code reality: `referrals.py` never emits degrees or
    relationship labels other than its deliberate default —
    `relationship` is always `"connection"` — and
    `find_referrals_data()` ranks only direct contacts at target
    companies. `network_crm.py: warm_path_to()` returns either a
    first-degree contact at the target, or a bridge contact at
    another company whose notes/history **mention** the target
    company name (a company-mention graph); it names no
    target-company employee and no intermediate-to-employee chain.
    (One sub-point corrected on refutation: company-name
    normalisation in `network_crm.py` does delegate to
    `referrals.normalize_company` when importable — that is the
    whole of the "reusing" claim that is true, and it produces no
    person chain.) The names in the demos are fictional; the
    capability they depict is the debt. This item is also the
    site-side half of feature E3's sourcing rule (§7 item 4).
28. (CD-28) **[Minor]** DocsPage's doctor description invents checks
    the doctor does not run (round-2 find; the round-1 audit's
    A-06). Surface: `site/src/pages/DocsPage.tsx`, System tool group
    ("doctor — Setup health check: profile, **keys, channels**.
    (Also a CLI command.)"). Code reality: `doctor.py` in both
    trees implements exactly six checks — profile, compliance,
    Playwright, sessions, preferences, boards — and contains no
    API-key check and no channel check. (Pairs with CD-05's doctor
    expansion: two surfaces overclaim the doctor in two different
    directions.)
29. (CD-29) **[Minor]** DecoderPage claims the in-browser decoder
    matches the Python engine "exactly" (round-2 find; the round-1
    audit's A-07). Surfaces: `site/src/pages/DecoderPage.tsx`
    (header comment: the numbers "match `cli.py decode-jd`
    **exactly**"; hero: "This is the real decoder, running in your
    browser. Same regex, same arithmetic as jd_decoder.py"). Code
    reality: the product's own JD-decoder spec
    (`site/src/pages/specs/jd-decoder.ts`, "Honesty gates") states
    the qualifier this page omits — the TypeScript port can disagree
    with the Python engine on word-boundary checks for brand-new
    Unicode characters (roughly the newest 9,600 assigned code
    points). The port is faithful for ordinary text; the unqualified
    absolute is the debt, and the honest qualifier already exists
    on the adjacent spec page.
30. (CD-30) **[Major]** The drip-queue spec's fail-closed risk run
    (round-2 concept-sweep find). Surfaces:
    `site/src/pages/specs/drip-queue.ts` ("The entire run goes
    through the risk policy first. If policy says no, the run stops
    immediately with risk_blocked and nothing is attempted. Fail
    closed."; FAQ: each item goes through "grill, honesty check,
    veto screen, fill-only rules"). Code reality: the queue's risk
    gate is additive and conditional — in `apply_queue.py` the
    `risk_policy` import is wrapped so that if the module is
    unavailable the gate is skipped entirely and the run proceeds,
    and `governance/risk_policy.py: adjudicate_automation()` itself
    falls back when the framework is unavailable (a warning, with
    the automation allowed), so a framework-absent or
    module-absent run is not adjudicated at all, let alone failed
    closed. The per-item pipeline sentence inherits every limit in
    claims 1 and 6 and CD-14. This is the site-side surface of the
    retained drip-apply scheduler named in §7 item 6.
31. (CD-31) **[Minor]** The LinkedIn spec's per-sentence provenance
    claim for the about-section draft (round-2 concept-sweep find).
    Surface: `site/src/pages/specs/linkedin.ts` ("your quantified
    bullets reused verbatim, **every claim listed in a provenance
    array. You can trace each sentence** to the fact it came from";
    demo line: "every number in the rewrite appears in your
    profile. Verified."). Code reality: `linkedin_optimizer.py:
    rewrite_about()` returns a grouped `built_from` list (years,
    title, skills, company, a count of quantified bullets reused
    verbatim, education) — not a per-claim or per-sentence array:
    framing sentences (the "Open to … roles — happy to connect"
    close, the "Selected results" placeholder when no quantified
    bullet exists) carry no entry at all. The numbers half of the
    demo line is accurate by construction (numbers are only ever
    reused from the profile); the trace-each-sentence half is the
    same overstatement shape as claim 4, on a shipped surface.
32. (CD-32) **[Minor]** DocsPage's honesty-guarantee FAQ is broader
    than the machinery (round-2 concept-sweep find). Surface:
    `site/src/pages/DocsPage.tsx` ("What honesty guarantees does it
    make?" — "The tailor, cover letter, and interview modules never
    invent experience, employers, skills, or metrics; achievements
    and numbers are copied verbatim from your profile"). Code
    reality: the sentence bundles three different facts into one
    guarantee. The tailor half is the construction rule of claim 5,
    scoped to skills it cannot add; the cover-letter half is subject
    to claim 6's limits (the scan flags, the blocking gate checks
    less, and neither runs on the resume); and the interview half
    has no such machinery at all — mock grading receives no profile
    or ledger (claim 16), prep stories are built from profile
    achievements in `briefs.py` (the one path where "copied
    verbatim" is the design), and the negotiation sim's counterpart
    is an invented persona by design. "Copied verbatim" is true of
    named paths (prep proof lines, the LinkedIn about draft's
    quantified bullets), not of every module the sentence names.

**Round-2 concept sweep — disposition of the remaining hits.**
The grep described in this section's introduction returned 579
hit lines; the numbered items above (CD-01…CD-32, including the
round-2 expansions of CD-01, CD-02, CD-05, and CD-14) account for
every hit that states a product guarantee the code contradicts.
The remaining hits disposition as follows, by class — each class
was read in context, not assumed:

- **Accurate against a named code fact (site):** the fill-only /
  never-submits sentences in `fill-only-apply.ts`, `DocsPage.tsx`,
  `ChangelogPage.tsx`, and `App.tsx` (claim 10's architecture:
  `browser_apply.py` has no submit path, `ats_apply.py` is
  preview-only — subject to CD-11's corrected scope and claim 10's
  queue-path scope note); the email-sync / followups
  no-auto-send sentences (accurate — that is the approval-gated
  send CD-11 as rewritten describes); the referrals
  never-scraped and relationship-never-inflated sentences
  (`referrals.py` reads the user's own export; `relationship` is
  always `"connection"` — the demos that go beyond this are
  CD-27); the interview-prep "unverified" sentences (`briefs.py`
  degrades unfilled fields to `"unverified"`, never to invented
  facts); the offers spec and `site/src/demos/win.tsx`
  estimated-figures sentences (derived figures are labelled
  estimated in `offer_compare`'s output); the streaks share-card
  sentence (`streaks.py: share_card()` builds the card from rep
  counts); the honesty-check spec's skills-and-years sentences
  (that is the blocking gate's actual scope — its missing
  conditionality is CD-08/CD-14, not a new item); and the
  qualification-scoring spec's fail-open sentences (they state the
  opposite of a guarantee, accurately, for that advisory check).
- **Demo and display scripts (site):** `site/src/demos/diff.tsx`
  and `cover.tsx` restate the tailoring and honesty concepts in
  demo form — dispositioned under CD-08, CD-15, CD-22, and CD-23,
  whose concepts they repeat; `growth.tsx` restates the
  ai-proficiency spec's never-a-credential sentence (accurate —
  practice is not credentialed anywhere in the code); `crew.tsx`
  is CD-26; `career.tsx` restates the negotiation sim (claim 8).
  Code comments and internal notes in `site/src/lib/jdDecoder.ts`,
  `jdShare.ts`, `routeAnalytics.ts`, `DecoderPage.tsx`, and
  `DecoderSharePage.tsx` use the swept vocabulary about their own
  implementation (hash key order, fire-and-forget analytics,
  payload handling) and make no product claim — except
  DecoderPage's user-facing "exactly", which is CD-29.
- **User docs (`docs/*.md`, top level):** `docs/grill.md` —
  CD-01/CD-02/CD-25; `docs/compliance.md` — CD-21 (boards) and
  CD-14 (fail-safe sentence), with its ledger sentence accurate as
  qualified (see CD-14); `docs/byol.md` — checked, accurate (the
  BYOL fetch is robots-checked and user-supplied; adv-a's held
  check in round 1); `docs/phone-access.md` — checked, accurate
  (token-gated LAN serving as described; it is also CD-17's
  stated real phone path).
- **Internal records (`docs/` subtrees and reports):**
  `docs/capability-report.md` (a runtime-observation report whose
  never-submits / never-operates-a-session findings are the claim
  10 architecture, stated with its evidence labels),
  `docs/legal-hardening-plan.md` (a plan: its fail-closed and
  never sentences are proposals, costs, and spec demands, not
  statements that a capability ships), `docs/outcome-event-contract.md`
  (a data contract: its guarantees are migration and format rules
  for its own store), and the decision records under `docs/i06/`,
  `docs/i09/`, `docs/i11/`, and `docs/i12/` (design-tradeoff
  records for initiative packages — they state what a design
  trades away, in the record's own terms, and are not user-facing
  product statements; where a capability from those packages is
  sold on the site as current product, that sale is already a
  numbered item: CD-12, CD-17, CD-18, CD-19). No new public claim
  was found in this class in round 2.
- **Ordinary quantifiers:** the balance of the hits — "every" /
  "always" / "exactly" in non-guarantee prose (stage histories,
  per-application logs, form fields, mentor-match weights, cap and
  pacing descriptions) and in the swept files not named above —
  were read in context and state mechanics, not guarantees; where
  a mechanic sentence also carried a guarantee concept, it is
  named in a numbered item above.

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
platform contact. The repositioning moves **new effort** away from
the highest-exposure surfaces (search/apply automation) toward the
lowest (knowing the user) — it does not remove the existing
retained surfaces, which are four, named, and dispositioned in
item 6. Every artefact
the pillars produce (tailored resume, letter, outreach draft,
follow-up draft) stops at a human approval step **at creation
time**, consistent with the STRICT circuit-breaker shape locked
2026-09-29 for AI-drafted outbound messages. That is not the same
as initiation at handoff time: approval stamps an artefact at time
T; the packet, apply-handoff, and export steps that consume it at
T+n are required — by feature C2's spec, owned by the feature-sets
document — to demand their own fresh human act, distinct from the
earlier approval. The brief's claim is the creation-time fact plus
that C2 requirement; it is not a claim that the handoff step is
specified in this package or built today. The submit click itself
stays the user's (claim 10). Initiative 08 (collective intelligence)
stays CUT under Rule 2 — the ledger is per-user and local, never
pooled.

**The exposure the pillars create — named, with the roadmap's
answer:**

1. **Concentration of sensitive data.** The ledger deliberately
   holds more than a resume: quantified wins alongside compensation
   floors, sponsorship, clearance, work authorisation. Local-first
   moves the richest copy of a person's career onto their own
   machine. Rule 2 answers the author's exposure, not the user's.
   Stated plainly before any answer: ledger versioning, backup, and
   restore answer **loss, not disclosure** — and a pre-migration
   backup is a second, equally rich copy, not a protection. The
   confidentiality mechanisms are therefore **requirements on
   feature A1**, and this item is not counted answered until A1
   specifies and ships them: (a) restrictive file permissions on
   the ledger and its backups — owner-only, checked at startup,
   with a readable error when they cannot be set; (b) backup
   protection — backups inherit the same permissions, live in the
   same protected location as the ledger, and follow a stated
   retention rule for backups generally: the product keeps the
   most recent 5 ongoing backups and deletes any ongoing backup
   older than 90 days, whichever limit is reached first, not an
   accumulating plaintext trail (the pre-migration backup follows
   its own hard-limit rule in A1's data-lifecycle table: it is
   deleted automatically at the earlier of 30 days after the user
   verifies the migration or 90 days after it was created, with
   notice in the prepared check-in 7 days and 1 day before, and
   the deletion noted in the work log);
   (c) encryption at rest for the ledger and its backups is
   **scheduled roadmap work, not a present mechanism**: it is a
   requirement on roadmap initiative 0.8 (the encrypted ledger
   store), not on feature A1, and no present-day text may state
   or imply the product encrypts the ledger until 0.8 ships;
   (d) minimisation
   and field-tiering — the most sensitive fields (compensation
   floors, sponsorship, clearance, work authorisation, plus any
   field the user marks private) form a
   separate tier, **excluded by default from channel messages
   and from exports** (see item 2), with each
   surface's permitted fields stated. This is one statement, and
   it is the statement feature A1 now specifies for exports as
   well as messages (round 2, D-05 — A1's tiering previously
   covered messages only, while its export spec exported every
   entry in full): by default an export represents a Tier 2 entry
   only by an omitted-count line, with no Tier 2 name, value, or
   proof text; including Tier 2 in an export is an explicit,
   unchecked-by-default opt-in the user chooses for that export,
   and a delta or verdict export whose reasons rest on a Tier 2
   fact carries the classification without the Tier 2 value.
   Remote endpoints are not a
   channel this package delivers profile-derived content over
   (item 2), so no tier rule for such payloads is needed or
   claimed. The ledger's
   storage/protection story is documented for users in Phase 0
   **with these mechanisms named**; a documentation promise without
   the mechanisms is not an answer. (Dependency: A1's spec text is
   owned by the feature-sets document. If the mechanisms A1
   specifies differ from this list, this item is re-opened, not
   silently satisfied.)
2. **Profile-derived data leaves the machine over chosen channels —
   analysed against every prong of the governing principle, not
   only Rule 2.** The flows, as this package specifies them: grill
   questions derived from the profile, delivered over Gmail and
   WhatsApp inside a session the user initiated; company briefs
   fetched from the web. Two flows from the earlier spec are
   **superseded, not current flows of this package**: notifications
   to remote endpoints on per-event opt-in, and scheduled check-in
   and grill sends under standing per-event consent. Remote-endpoint
   / webhook delivery is removed as a channel class (feature E1);
   existing `notify.py` behaviour can post notifications to
   user-configured webhook/ntfy endpoints today — that is current
   code, corrected as claims debt CD-24 — but this package does
   not deliver profile-derived content over that class.
   - *Rule 2:* none of these flows sends data to author
     infrastructure. That is the only prong the previous version of
     this item analysed, and it is not the whole principle.
   - *What leaves, and to whom:* a grill question can quote ledger
     content — a win, a number, a role — and it leaves to a
     third-party messaging platform (Gmail, WhatsApp), inside a
     session the user initiated. A company-brief fetch
     transmits the company name, and role context, to web search
     and fetch endpoints. Neither flow is content-free, and this
     brief does not describe them as if they were.
   - *Automated-access terms:* Gmail delivery runs through an
     external Gmail CLI that is not publicly distributed (CD-20);
     WhatsApp delivery runs through a user-linked side-chat bridge.
     Neither channel was audited against its platform's
     automated-access terms when this item was first written; that
     concession now has an owner and a gate, and the brief states
     both instead of leaving it as an open item (round 2, D-04):
     the audit is a named Phase 0 task in the roadmap's standing
     Row X slice, **owned by the compliance reviewer seat**, which
     records a per-channel verdict (Gmail, WhatsApp) in writing
     before Phase 1 starts. **Gate: initiative 1.1 does not launch
     on a channel with no recorded verdict, or with a verdict
     against automated access on that channel**; a channel the
     audit does not clear is removed from 1.1's launch scope, its
     launch claim, and its E2E in writing at the audit's gate —
     and if the audit clears neither channel, 1.1 launches on
     in-product chat only. Until that verdict exists, no sentence
     in this brief treats either channel as cleared.
   - *Fresh initiation:* this package **conforms** to the
     fresh-initiation prong through the decided prepare-only
     redesign (feature E1; audit F6-01 resolved in favour of the
     principle, not deferred). A scheduler prepares locally only:
     it assembles a check-in or a grill batch and holds it on the
     user's machine. Sends occur only inside a user-initiated
     session, at the user's act in that session. Standing or
     per-event consent is not initiation, and no setting, schedule,
     or prior approval sends anything. Where any other text in
     this package could be read otherwise, the roadmap's CUT list
     — no auto-send under any flag — governs the conflict.
   - *Content-level limit:* the consent model governs where a
     message may go and what may be sent by event type; it is not
     per-content control. The requirement (feature A1's
     field-tiering, item 1) is that compensation, sponsorship,
     clearance, and work-authorisation fields are excluded from
     channel messages by default, and
     that question content carries the minimum the question needs.
     Until that tiering ships, the honest statement is that no
     content-level limit exists today.
   Roadmap answer, restated to match the analysis: the consent
   reconciliation (roadmap Slot 0-C1/0-C2, model specified in
   feature E1) owns the consent model — Slot 0-C2's merged consent
   model is built to E1's prepare-only rule; A1's field-tiering
   owns the content limit; the initiation question is settled by
   the prepare-only redesign above, with the roadmap CUT list
   governing any conflict. None of
   this falsifies Rule 2 — and all of it falsifies any "nothing
   leaves your machine" wording, which the brief therefore never
   uses (§2).
3. **The blocking gate can be silently off.** When the governance
   framework checkout is absent, the gate returns disabled and the
   caller proceeds (audit §5). A promise backed by a gate that
   vanishes per-install is a reliance gap — wider after this round's
   correction, because the gate that does run checks less than the
   headline implies (claim 6). Roadmap answer: feature C3 is a
   single gate — one scanner, one block, and the proven-only pass
   rule — installed at three points: the C2 approval flow, the
   application confirm path (roadmap initiative 0.5 is that gate's
   early installation at the confirm path), and packet assembly,
   apply handoff, and export re-scan. The gate is unconditional at
   every installation point — no configuration, framework checkout,
   or user setting can disable it there — so the accurate claim,
   used in §3 and here, is "unconditional at every installation
   point", not "unconditional" plain. Under feature C3 a factual
   claim passes only traced to an `approved` ledger entry with
   proof attached; a claim tracing only to an unverified entry or
   a grill answer blocks. Until C3 ships, §3 states the
   limit wherever the gate is claimed.
4. **Third-party contact data.** The warm-intro finder holds other
   people's names, employers, and titles from an imported
   connections export, with deliberately thin relationship labels.
   Referral drafts stop at the user — that finder never sends
   (claim 9, as scoped; the one wired send in the product is the
   approval-gated follow-up send described in CD-11) — but data *about*
   third parties is a surface even when nothing is sent. The i07
   consent/handshake material exists (unwired) and the roadmap's
   network work (E3) is scoped to the wired machinery with its
   honesty labels intact; no contact is ever enriched by scraping.
   Stated so this item is not read as answered: labels and a
   no-scraping pledge do not address retention, per-contact
   deletion or correction, an accuracy remedy for a wrongly
   labelled relationship, or the source platform's terms governing
   the connections export itself. Those are open requirements on
   E3.
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
   ship with it, or the record does not ship. The same reasoning
   applies to stores the previous version of this section did not
   name — the per-job delta store, the proposal log, E1's
   session-type log, grill and mock session stores, and outcome
   history: each accumulates with no retention, export, or deletion
   rule specified anywhere except the verdict record. Indefinite
   retention by default is a decision; the roadmap must disposition
   each store explicitly rather than by silence.
6. **Retained surfaces — four of them, named — an open exposure.**
   The repositioning does not leave the search surface, and this
   item corrects the opening of this section wherever it implied
   otherwise. The retained set is **four surfaces**, and this brief
   does not present a smaller set anywhere: board search stays as
   the secondary source (feature E2), `watch.py` keeps watched
   companies, `providers/` search carries forward, and — **named
   in round 2 (D-02); previous versions of this brief never named
   it at all** — the **drip-apply scheduler, `apply_queue.py`**.
   The roadmap PAUSEs only **new** providers and search expansion.
   The scheduler's exposure, stated plainly: it is a scheduled
   application pipeline — items can be added with a
   `--scheduled-for` timestamp, `queue-run` is documented
   cron-friendly and invokes the apply path with its confirm preset
   in the invocation (its own comment treats the run as explicit
   consent to record), it paces items with a random sleep between
   applications, and with `VETO_BROWSER_APPLY=1` set, the apply
   path it calls opens the apply URL, fills the form from the
   profile, and uploads the resume — so a scheduled run performs a
   form-fill and upload interaction with a third-party ATS at a
   preset time, with no human hand at the moment it happens. The
   submit click remains the user's (claim 10, with its scope note);
   the scheduled fill-and-record path before it is the exposure,
   and it is also sold on the site (CD-30). `watch.py` carries the
   parallel exposure: its entry point invites cron scheduling, and
   the server documents watched-company checks as runnable on a
   cron. This package does not analyse the retained surfaces
   beyond naming them: it does not state what authentication any
   provider uses, what rate limits apply, or each board's terms
   posture for automated access — and the surfaces are unaudited
   by this package, stated plainly. The disposition story is the
   roadmap's, and it is the same for all four surfaces: the
   Phase 0 standing Row X slice records a keep / scope-down / cut
   decision per surface against feature E2's posture —
   user-initiated operation only, no standing periodic sends or
   fetches under consent, public / unauthenticated access only —
   under the rule that a "keep" that leaves a non-conforming
   surface unchanged is not an available outcome, recorded before
   Phase 0 closes and before the repositioning's legal story is
   used publicly. **New roadmap initiative 0.9 then performs the
   conformance implementation** the decision records — named work
   includes removing or re-scoping `watch.py`'s cron entry point
   and re-scoping `apply_queue.py`'s scheduled-for / queue-run
   preset path so no scheduled or preset-consent run performs the
   browser form-fill / resume upload (that path runs only on a
   user act in the moment, or is removed, per the recorded
   decision) — and **a retained surface's continued use is not
   relied on publicly, in claims, docs, or the site, until 0.9 has
   passed its gates for that surface.** Until then, the accurate
   sentence is: the repositioning moves new effort away from the
   highest-exposure surfaces; the existing surfaces remain,
   named, with their disposition owned and gated as above.

**Net judgement:** the differentiator strengthens the posture on the
axis the legal program governs (third-party contact, Rule 2) and
adds user-side data exposure that the roadmap must actively manage
(items 1–6). Both halves are the finding.

## 8. Strategy risks — the honest treatment

The audit round attacked the strategy itself, not just its claims.
This section prices those attacks in the brief's own words. None of
it is boosterism; where a risk has no answer yet, the section says
so and names who owns finding one.

1. **The mechanism is copyable within a quarter — conceded.** The
   taxonomy, the construction guard, and the refusal toggle are
   specification, not invention; the substrates a funded rival
   needs (match score, missing-keywords list, tailoring,
   job-specific prep) already exist in its own product, and Veto's
   code is public, so a rival does not even need to re-implement
   from a description. Rule 2 forbids the pooled-corpus moat, and
   there is no patent, exclusive data, network effect, or
   distribution advantage to rest on. The claimed durable advantage
   is narrower: the **accumulated personal record** — a user's own
   ledger of graded proof, verdicts and overturns, and outcome
   history, built over months — and the trust that record earns
   when its verdicts prove right (Pillar 1). The evidence that
   would falsify it must be evidence this architecture can actually
   count, and earlier wording here failed that test — it named
   "users switch anyway" as a falsifier, which Rule 2 / no
   telemetry makes unobservable: the product cannot see a user
   leave for a rival, and cannot see non-users' outcomes, so that
   sentence is withdrawn as a test and is not presented as one
   (round 2, B-12). The falsifiers that remain are the countable,
   local ones §9's kill criterion already carries: a proof-closing
   rate near zero in the user's own delta record, vetoes routinely
   overridden without the named change-my-answer condition having
   been met (feature B4's definition), and
   interviews-per-application flat against the user's own baseline
   — each counted on the user's own machine, per user, with no
   population form claimed. One half of the old trigger **is**
   publicly observable and stays: whether a competitor ships the
   combination in §2 is visible on its public record — MaxCV's
   occupation of the refusal element (§5) is exactly that kind of
   observation — and if a competitor ships the full combination,
   the advantage claim narrows again in the open, as it did this
   round. The record's portability cuts both ways — the user can
   take their ledger elsewhere — so the advantage lasts only while
   the product keeps earning it.
2. **The classification is against the posting as written — not
   against the employer's real bar.** Postings are employer
   wish-lists: candidates are routinely hired without meeting every
   stated requirement, and applying at partial fit is standard,
   advised behaviour. A classification can be correct about the
   ledger and wrong about the market. That is why the headline's
   second word is always qualified in this brief — **unqualified
   for this posting as written** (§2, §3) — and why no surface may
   present a delta or a veto as a judgement about the person's
   employability. The commitment that keeps this honest is outcome
   validation: the outcomes loop (roadmap initiative 5.11, §9's
   Outcomes measure — B5 measures and E1 session typing are inputs
   to that loop, not the loop itself) compares verdicts against
   what employers actually did,
   and a veto class that employers routinely contradict is a defect
   to fix, not a brand to defend. One visible "vetoed for a job
   someone like me then got" story damages a judgement brand more
   than a hundred quiet correct calls help it; the package's
   correctness measure (§9) is user overturns today, and employer
   outcomes are the check that must be added to it.
   **The observability limit, stated plainly (round 2, B-08):**
   that loop can only compare verdicts where an outcome exists —
   and a veto the user **obeys** produces no application and no
   outcome event, and Rule 2 provides no employer-side channel by
   which the outcome of a job never applied to reaches the record.
   Outcome validation therefore cannot observe its decisive case
   from employer data; overridden vetoes are a self-selected subset
   and do not stand in for obeyed ones. What 5.11 builds for that
   case, as the roadmap now specifies it, is **user-reported
   outcome capture for vetoed jobs**: in a user-initiated check-in
   session (initiative 5.1's surface; nothing is fetched or sent
   by a scheduler), the user can record, per vetoed job, what they
   did (did not apply / applied anyway / applied later) and what
   happened as far as they know it, stored as a user-reported entry
   in the outcome store and labelled user-reported in every report
   — never presented as employer-side data. The reports state
   which vetoes carry only this self-reported evidence and which
   carry none. **Timing, pulled earlier:** 5.11's first report is
   a **preliminary report four weeks after initiative 2.8 ships**
   (small sample, user-reported veto outcomes included, limits
   stated on its face); the first full report follows one quarter
   after 2.8 ships, then per quarter. The preliminary report does
   not lift the fit-weight PAUSE, which stays conditioned on the
   first full report.
3. **Classification falls hardest on the users least able to fix
   it.** *Supported* requires the proof the requirement's kind
   requires (feature B2's per-kind test): verbatim quantified proof
   for quantitative requirements, the stated minimum met for
   threshold requirements, and verbatim approved attestation or
   documentary evidence for categorical requirements (location, work
   authorisation, credentials), with no quantity demanded of a
   categorical fact. That bar
   is easiest to clear for conventional, quantified,
   well-documented career histories, and hardest for work that is
   hard to quantify (care, operations, support, early career), for
   non-conventional or non-native phrasing, for freelance and
   caregiving-gap histories, and for proof sitting in systems the
   user no longer has access to. "Unproven" will not fall randomly;
   the brief states that plainly rather than discovering it in
   public. The mitigations are specified work, not sentiments —
   and they are described here as what they actually are (round 2,
   B-09; earlier wording in this paragraph promised more than the
   spec delivers, and is corrected): **the dispute flow in feature
   B2 is per-item correction and re-classification of the disputed
   requirement** — the user supplies evidence (which becomes an A3
   proposal), corrects the ledger entry, corrects the extraction,
   or proposes a provisional alias — and the classification of that
   requirement is then recomputed. It is **not** a re-review of the
   classifier: no dispute path re-examines the classifier's
   thresholds, extraction rules, or alias table as a whole (a
   provisional alias reaches the shared table only through a
   reviewed repo change), and this brief no longer describes the
   flow as a bias remedy. **The bias remedy is roadmap initiative
   2.9**: a bias fixture plus measured disparity across user types,
   with a release decision on the result. Stated honestly, as the
   roadmap states it: **2.9's disparity threshold is set by the
   project owner at spec freeze — no threshold exists in this
   package — its corpus is synthetic fixtures with
   spec-owner-authored expected classifications, and a
   ship-with-disparity waiver exists**: if measured disparity
   exceeds the threshold, the release rule can be satisfied by the
   owner recording a decision to ship with the disparity
   published. That is a waiver, held by the same person who sets
   the threshold and authors the corpus, and the brief names it as
   one rather than presenting 2.9 as an external check. There is
   also no real-user bias measurement anywhere in the package —
   and under Rule 2 there cannot be a population one; that
   constraint is part of this risk, not a footnote to it.
   Until both the dispute flow and 2.9 exist, the classifier ships with a known, unmeasured
   bias risk, and career changers — the segment with the emptiest
   ledger (§4) — are the most exposed to it.
4. **Refusal is a growth liability, and it is priced here, not
   wished away.** Job-search search intent is help-seeking ("resume
   builder", "ATS checker"), not refusal-seeking; a refusal-led
   headline competes for clicks against promises of interviews.
   Word of mouth has the same problem in reverse: the tellable
   story the brand offers a vetoed user is "this tool told me I was
   unproven", a story that requires publicly owning a negative
   verdict — while the package's growth model expects volume users
   to produce the stories growth runs on (§4). Being memorable is
   not the same as converting, and this package contains no funnel
   — no visit→install→first-delta conversion assumption for any
   channel. The honest position: refusal is the differentiator and
   simultaneously the acquisition handicap; the demo (§4) exists to
   show the *yes* side of the mechanism (proof surfaced, gaps named
   with a path) and not only the refusal, and §9's Recognition
   measure is a content check, not evidence that the funnel works.
   **Relabelled (round 2, B-16): the feeder logic in §4 is not a
   priced cost of this risk — it is an untested open dependency of
   the acquisition model, the only growth model this package
   offers. No funnel, conversion assumption, or story-elicitation
   mechanism in this package tests it, and none is claimed. Owner
   for testing it: the PM seat, which owns the acquisition model
   and must record a test (or a decision to proceed untested)
   before the Phase 2 demo ships.**
5. **Cold start is severe.** The product asks for the most work —
   intake, proof at the door, repeated grill sessions — at the
   moment of least trust, before it has proven anything, to people
   in a time-pressured search. Hosted rivals deliver a score from a
   resume paste in minutes; Veto's first real delta presupposes the
   ledger, migration, and approval surface the roadmap builds
   first. Time-to-first-value is therefore named as a measure in
   §9, split in round 2 into the two halves that can honestly be
   measured when they are measured (initiative 1.6 is now 1.6a and
   1.6b): **1.6a owns the intake budget** — the question count and
   time the intake asks before the first claim reaches proven,
   with the target that the intake asks no more than the A5 proof
   requests plus one grill session (≈5 questions) in a first
   sitting; the Phase 1 gate reports the seeded persona runs
   against that target, and a miss leaves 1.6a built, gate pending
   on a recorded owner decision, not silently passed. **1.6b owns
   the first-delta half** — time and question count from intake
   start to the first delta shown, target: a new user who pastes
   one posting reaches a first delta within one sitting. A first
   delta is a Phase 2 artefact, so **no Phase 1 gate measures or
   reports a first-delta figure**: 1.6b builds its instrument in
   Phase 1 and is built, gate pending until the Phase 2 delta gate
   (2.2 and 2.3 shipped, and the Phase 2 seeded new-user run
   recording the figure). This brief claims no Phase 1 first-delta
   measurement anywhere. The
   eight-week horizon §9 sets for a partial depth payoff is the
   package's own admission of how slow the payoff is.
6. **Audience mismatch.** The highest-intent seekers — urgent,
   high-volume, financially pressed — are the segment the strategy
   deprioritises, and their behaviour (apply at partial fit, move
   fast) is the behaviour the veto exists to slow down. The chosen
   primary segment is small, slow, already well-served, and needs a
   prior bad experience before the pitch applies; because the
   product is free, its low volume carries no revenue to offset it.
   The feeder logic is close to circular: growth needs volume
   users' stories, while the product is deliberately not optimised
   for them (risk 4). **As relabelled at risk 4 (round 2, B-16),
   that feeder logic is an untested open dependency of the
   acquisition model — not a priced cost of choosing this segment —
   with the PM seat as the named owner for testing it.** The brief
   keeps the segment choice — depth over volume is the positioning
   — and records that it is a choice with a cost, not a discovery
   that the market happens to agree with.
7. **Free and community-groomed vs the support a refusal product
   needs.** A refusal product generates adversarial support demand
   — "I disagree with your verdict about me" — which is more
   expensive per user than ordinary bug support, and it arrives
   with no revenue to fund it. Users will need humans: alias-table
   additions by reviewed change, disputed classifications, ledger
   restore problems — and seeking help can mean disclosing the most
   sensitive file the product holds (§7, item 1). The roadmap's own
   resourcing (every initiative gated on tests, E2E, blind review,
   legal review, and one person's UAT) is the throughput the
   strategy actually has; the roadmap document owns reconciling
   that with the delivery window risk 1 sets, and this brief does
   not contradict its numbers. The programme those numbers describe
   is, as the roadmap now totals it, **52 initiatives (5 owed
   Slot 0 items + 47 differentiator initiatives across Phases 0–5)
   and 187 planning units (118 initiative units + 52 gate units +
   17 standing Row X units)** — the load risk 1's one-quarter
   copyability window is priced against. If delivery slips, competitors close
   the window while the bet is still being built — that is the
   combined cost of risks 1 and 7, stated once, plainly.
8. **The veto paradox: overridable, or obeyed — both horns are
   measured late unless the instrumentation moves up.** If the user
   can always proceed anyway, a hostile reviewer can collapse the
   differentiation to "a warning dialog". If users instead take
   the veto seriously, the veto moment is the likeliest churn
   moment, arriving at a point of documented rejection stress.
   Either way the product must know which is happening. Correction
   made in this round: the override/overturn rate is measured
   **from the first release that issues a classified veto** — not
   from Phase 5, and not two quarters after everything ships — and
   a veto-moment measure (whether the user returns within 14 days
   of a first veto, counted on their own machine like every other
   measure here) ships with that release (§9). That measure now has
   a named home (round 2, B-10 — in the previous version it appeared
   in no other document): **roadmap initiative 2.8 owns it in its
   scope and acceptance** — the verdict record computes, per user
   and locally only, returns within 14 days of a first classified
   veto (a return is any later user-initiated session in the local
   session record; a fixture return on day 13 counts and no return
   by day 14 does not), shown as returns / first vetoes with its
   count alongside the overturn rate — **the Phase 2 E2E asserts
   it**, and the feature spec it cites is feature B4 (the veto-moment return measure — the 14-day return). A brand can survive
   learning this early; it cannot survive learning it after the
   positioning has done its damage.
9. **The second-tool trap, plus install distance.** Veto accepts
   being the second tool (§4) — which means it must earn a place
   next to the tracker, the graph, and the autofill the user
   already has, while asking for a local install, channel and
   scheduler setup, and the intake of risk 5 before delivering the
   personal version of what the demo simulated. Every hosted rival
   in §5 delivers its weaker value in-browser with no install. The
   demo is the only bridge, and §4 states its structural limit: it
   can show the mechanism on a fixture, never the visitor's own
   delta. The strategy depends on that bridge anyway; the brief
   names the dependence instead of hiding it.
10. **The trust claim has no population form — its proxy is
    per-user, and the claim is downgraded to match.** Rule 2 / no
    telemetry means trust can never be counted across users,
    published as proof, or compared by cohort — while hosted rivals
    can publish outcome statistics from real populations. The
    countable proxy is the per-user verdict record: vetoes issued,
    vetoes overturned, proofs closed, shown to the user about the
    product's own record (Pillar 1, §9). Anything stronger —
    "users trust Veto more" — is unfalsifiable inside this
    architecture and is not claimed.
11. **Naming and discoverability are untested assumptions.** No
    document in this package contains a search-volume,
    SERP-competition, registry-name-collision, or unaided-recall
    test for the product name or for the refusal line; the generic
    political meaning of the name and the negative head-term in the
    line are adopted unexamined. For a product that grows by arrival
    and sharing or not at all (§4), discoverability is the strategy,
    and its two central words currently rest on zero evidence either
    way. The test is cheap and is owed before the Phase 2 demo
    ships; until it runs, this is recorded as an untested
    assumption, not a fact in either direction.

## 9. What success looks like — with numbers and a kill criterion

Targets below are **targets for the built state**, set 2026-10-15,
to be re-based when each phase ships. The measures are
computed by machinery or instruments the roadmap builds — the
depth meter (Phase 1) for Profile depth; B4's verdict record
and overturn computation (Phase 2) for Veto correctness; B5's
outcome computation for Outcomes; E1's session typing (Phase 5)
for Return; the Phase 1 UAT seeded runs for Time to first value;
and the Phase 2 seeded UAT run set as Recognition's
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
- **Time to first value (cold start — §8, risk 5).** The first
  delta report is the product's first real value; everything before
  it is intake cost. The measure is two, because its halves are
  countable at different times (round 2 split of initiative 1.6):
  **(a) the intake budget** — minutes of intake and number of
  questions answered before the first claim reaches proven;
  target: the intake asks no more than the A5 proof requests plus
  one grill session (≈5 questions) in a first sitting. Owner:
  roadmap initiative **1.6a**; the Phase 1 gate reports the
  seeded-run figures against this target, and a miss leaves 1.6a
  built, gate pending on a recorded owner decision. **(b) time to
  first delta** — minutes and questions from intake start to the
  first delta shown; target: a new user who pastes one posting
  reaches a first delta within one sitting. Owner: roadmap
  initiative **1.6b** — it builds the instrument in Phase 1 and is
  built, gate pending until the Phase 2 delta gate, where the
  Phase 2 seeded new-user run records the figure. No Phase 1 gate
  reports a first-delta number, and none is claimed here.
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
  the first release that issues a classified veto** (corrected in
  this round — earlier versions started the clock far too late)
  **and published in the product's own record**; the threshold-review
  trigger is feature B4's, stated in B4's words: over at least 10
  reviewed vetoes, more than 1 in 3 overturned without the named
  change-my-answer condition having been met at override time —
  below 10 reviewed vetoes the trigger cannot fire. When it fires,
  the veto is wrong too often to carry the brand, and a threshold
  review is triggered before any further positioning use. The same release ships the veto-moment
  measure: whether the user returns within 14 days of a first
  veto, counted on their own machine. Its home (round 2, B-10):
  roadmap **initiative 2.8** owns it in scope and acceptance —
  the record computes returns / first vetoes locally and shows
  the count alongside the overturn rate — the Phase 2 E2E asserts
  it, and the feature spec is feature B4 (the veto-moment return measure — the 14-day return). A veto nobody can check is a claim; a
  veto with a visible overturn rate is a record.
- **Outcomes, not prevention (per user, owned by roadmap
  initiative 5.11):**
  interviews per application, computed on the user's own machine
  from their outcome store against their own pre-Veto baseline
  where they have one, and surfaced by delta trending (B5) with its
  sample size. B5 computes the figure; initiative 5.11 owns the
  outcome-validation loop that checks verdicts against outcomes. The positioning is judged on interviews won, not
  applications prevented — a fall in applications with flat
  interviews is a failure wearing a success's clothes. This measure
  is also the employer-side check §8, risk 2 commits to: verdicts
  compared against what employers actually did, not only against
  the user's own overturns. **The vetoed-job half of that check
  is user-reported, and §8 risk 2 states why it must be:**
  vetoed jobs produce no employer-side outcome unless the user
  reports one, so 5.11's design includes user-reported outcome
  capture for vetoed jobs (check-in session; per job: did not
  apply / applied anyway / applied later, and what happened as far
  as the user knows; stored and labelled user-reported), which
  B5's veto analyses consume. Timing: the
  interviews-per-application figure is first countable when B5
  ships (Phase 5); before that it is reported as not yet countable,
  never as zero. 5.11's own reporting starts earlier than the
  previous version of this package said — a **first preliminary
  report four weeks after initiative 2.8 ships**, then the first
  full report one quarter after 2.8, then quarterly (round 2,
  B-08). The preliminary report does not lift the fit-weight
  PAUSE, which stays conditioned on the first full report.
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
- **Kill criterion:** if, two quarters after Phase 5 ships — the first point at which all three triggers can be counted (the overturn trigger alone is countable from the first classified-veto release and is watched from then; the criterion as a whole is judged only when every trigger has a measure) — the
  delta report does not change behaviour — proof-closing rate near
  zero (B5's measure), vetoes routinely overridden without the
  named change-my-answer condition met (B4's record),
  interviews-per-application flat against baseline (B5) — the
  positioning goes back to the seats for rework or abandonment.
  The bet (§3's loop) is falsifiable, and this paragraph is where
  it is falsified.

## 10. Revision record

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

v14 (2026-10-15) is rework round 1 against the adversarial audit
of v13 (verdict KICK_BACK; 91 standing findings after
verification). In this document: the claims register is regraded
against both code trees, with the tree named per entry (claims
1, 2, 3, 4, 6, 7a, 12, 14, 16 corrected — the "second shipped
veto" exists only in the live tree, per-line provenance is
built-unwired, the approved-variant save is broken, and the
blocking gate never runs the honesty scan); the front half no
longer restates the corrected claims as shipped core (§§1–3);
the claims-debt list is completed — nine audit finds added
(CD-14…CD-22) and three more from this round's own re-sweep of
every site spec, site page, and product doc (CD-23…CD-25), with
locations added to CD-05, CD-10, CD-12, and CD-20; the competitor
table is corrected (LinkedIn's met/missing lists and job-specific
prep, Teal's and Rezi's prep, Jobscan's Auto Apply and categorised
missing items, Yoodli's job-description sessions, Simplify's
scale, Sonara's review-and-submit, LazyApply's ambiguous billing)
and extended with Jobright, Careerflow, Huntr, AIApply, and Resume
Matcher, with the open-ground claim scoped to the table as now
constituted and the free/open-source/local-first posture no longer
presented as unique; §7 is rewritten so each exposure's answer
addresses the exposure named (item 1: confidentiality mechanisms
specified as A1 requirements, backup/restore stated as answering
loss not disclosure; item 2: all four prongs analysed for the
channel and fetch flows, with the scheduled-send conflict resolved
in favour of the principle through the prepare-only redesign; item 6:
the retained board search/watch/provider surface named as an open
exposure); §8 is new — the strategy risks priced honestly
(copyability, posting-as-written, classifier bias, refusal as a
growth liability, cold start, audience mismatch, resourcing, the
veto paradox, the second-tool trap, the uncountable trust claim,
untested naming); the success measures move to §9, with veto
correctness now tracked from the first classified-veto release
and time-to-first-value added as a measure carrying the target
stated in roadmap initiative 1.6, with 1.6 as its owner. Note for readers of the older
entries above: their §8 references are to the success-measures
section, which is §9 from this version.

v15 (2026-10-15) folds in round 2 of the same audit's fix loop —
the findings that stood after the round-1 refutation pass (6
blockers, 26 majors, 23 minors across the package; this document
owns its share, dispositioned in
`~/workspace/veto-differentiator-audit/fix-r2/dispositions-brief.md`).
What changed here: the Jobscan row was re-corrected from Jobscan's
own pages (Auto Apply is review-by-default with an optional
auto-submit mode, not approval-required, and its interview practice
is a consumer optional add-on, not enterprise-only); the LazyApply
row was re-corrected from its own pricing (three per-year tiers,
1/5/20 resume profiles — the "same resume to every job" cell is
withdrawn); the Sonara row is now sourced to Sonara's own current
site under BOLD (the rival compare page is withdrawn as a source,
and the February 2024 shutdown sub-claim is not repeated — the
source that carried it no longer carries it). MaxCV, Enhancv,
JobCopilot, LoopCV, EarnBetter, and AIHawk (as a historical /
pivoted row) were added to §5 from their own pages, and §2's open
ground is restated as the narrower combination that remains —
refusal declared occupied by MaxCV, fabrication bans and
requirement→evidence mapping declared common ground — scoped to
the twenty-competitor-row table as constituted, with a §5 methods note
stating the check date and the primary source per corrected or
new row. The §2 headline now carries the qualifier itself ("for
this posting as written"), and §2/§3 restate feature B4's single
production rule for the headline word (most severe class present
among must-haves; veto-class labels never override; no veto, no
headline word) wherever the veto classes were previously assigned
headline words directly. Claim 9 is scoped to referral/network
drafts, with the wired approval-gated follow-up send named; claim
10 carries a scope note naming the scheduled apply-queue path.
The claims-debt list was re-swept by claim concept rather than by
file (guarantee vocabulary across the whole site source and
docs — 579 hits dispositioned in the list or its sweep table):
CD-11 was found false as written and is rewritten (a wired,
approval-gated send exists; the follow-up site copy is accurate
and is not debt), CD-05 and CD-14 were expanded (the Changelog
ledger entry, the doctor FAQ, the compliance document's fail-safe
sentence), and CD-26 through CD-32 were added (crew fail-closed
and ledger guarantees, the referral demos' fabricated
second-degree chain, the drip queue's "Fail closed" risk run,
DocsPage's honesty-guarantee FAQ, and the minor items). §7 states
the Tier 2 rule once, for channel messages and exports both,
aligned with feature A1 as fixed this round; the Gmail/WhatsApp
terms concession now names its owner (compliance reviewer seat),
its Phase 0 Row X task, and its gate on initiative 1.1; §7 item 6
names all four retained surfaces — board search, `watch.py`,
`providers/`, and the drip-apply scheduler `apply_queue.py`,
whose scheduled form-fill exposure is stated — with the Row X
disposition decision and new roadmap initiative 0.9's conformance
work as their story. §8 risk 1's uninstrumentable "users switch
anyway" falsifier is withdrawn in favour of the countable local
falsifiers; risk 2 states the veto-outcome observability limit
and 5.11's user-reported capture for vetoed jobs, with the first
preliminary report four weeks after 2.8 ships; risk 3 describes
feature B2's dispute flow as per-item correction, not a classifier
re-review or bias remedy, and names 2.9's owner-set threshold and
ship-with-disparity waiver as a waiver; risks 5 and 7 carry the
1.6a/1.6b split and the programme totals as the roadmap now states
them (52 initiatives, 187 planning units); risk 8 and §9 name
roadmap 2.8 (with the feature B4 spec) as the home of the
veto-moment return measure — the 14-day return. §9's time-to-first-value measure is split to match
1.6a (intake budget, Phase 1 gate) and 1.6b (first delta,
gate-pending on the Phase 2 delta gate) — no Phase 1 first-delta
measurement is claimed.
