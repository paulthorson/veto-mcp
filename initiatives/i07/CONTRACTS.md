# Initiative 07 — Consent Handshake Contracts

Published contracts for the mentor-introduction consent system. These are
the normative definitions the code implements; reviewers judge the code
against this document, not the other way around.

Version: 1 · Date: 2026-09-13 · Status: draft for adversarial review

## 1. Parties and identities

* **Mentee** — the local Veto user requesting an introduction. Identified
  by `mentee_id` (local) plus a `mentee_label`: a display name **or
  initials** — the mentee's privacy choice, symmetric with the mentor's.
* **Mentor** — a person with an opted-in mentor card in the local
  directory. Identified by the card id (derived from their LinkedIn URL).

Identity attributes (demographics, background, etc.) are **never**
collected by the system. The match questionnaire accepts `identity_preferences`
**only when voluntarily supplied** by the mentee, stores them verbatim on
the handshake record, and never uses them for ranking — they are a note to
the human reader, not a model input.

## 2. What counts as consent

Consent is an explicit, recorded act by an identified party:

* Mentee consent = calling `request_introduction` with a stated `goal`.
  A request without a goal is rejected — it is not a consent-bearing act.
* Mentor consent = `mentor_respond(..., decision="approve", channel=...)`
  where `channel` names how the mentor communicated the decision
  (e.g. `linkedin_dm`, `email`, `in_person`). The channel is REQUIRED.

**Anti-fabrication rule:** there is no code path that records a party's
consent without that party's explicit recorded act. In the local-first
pilot, the mentor's reply arrives out-of-band (LinkedIn, email) and the
user records it; the receipt requires the channel as provenance.

**Trust boundary (stated plainly):** in the local-first deployment the
`actor` argument is caller-asserted — the device belongs to one user, and
the tool trusts that user to record each party's acts honestly (their own
consent as mentee; the mentor's reply as reported to them). The code
cannot cryptographically authenticate the remote mentor; it can only
refuse to *invent* consent, require provenance, and keep a tamper-evident
append-only audit trail. A future hosted deployment must replace
caller-asserted actors with authenticated identities before any pilot
that involves real remote parties.

## 3. Revelation rule

Neither party's contact detail is revealed to the other until the
handshake is in state `mutual` (both consents recorded):

* Pre-consent, each side sees only **redacted previews**: name/initials,
  industry, role, seniority band, topics, bio, availability text, rating
  summary, match reasons. No LinkedIn URL, no email, no phone, no exact
  contact path — unless the mentor explicitly opted their LinkedIn URL
  into the public discovery card (`preferred_contact="linkedin_public"`).
* Blocked and quarantined actors are excluded from discovery entirely
  (`safety.discovery_exclusions` → `matchmake(..., exclude_mentor_ids=...)`),
  not just from handshakes.
* `reveal_contact` refuses in every non-`mutual` state, including
  `withdrawn`-after-`mutual`. Block status is re-checked at reveal time.

## 4. Withdrawal

Either party may withdraw **at any time, at any stage**, via `withdraw`.
Withdrawal is immediate and final:

* Pending requests end as `withdrawn`.
* Post-`mutual` withdrawal seals contact details for all future reads
  through that handshake. It cannot un-see details already read — the
  audit log records the revocation as a receipt for both sides.

## 5. Decline and expiry

* A mentor decline ends the handshake as `declined` and starts a 30-day
  re-request cooldown for that pair (anti-pestering).
* Unanswered requests expire after 7 days (`expired`); the mentee may
  re-request after expiry.
* At most one `awaiting_mentor` handshake per mentor/mentee pair, and at
  most 5 new requests per mentee per rolling 24h (rate limits; see
  `safety.py` for the general engine).

## 6. Audit

Every transition appends one JSON line to `consent_audit.jsonl` with
timestamp, event, handshake id, actor, and detail. **There is no API to
edit or delete audit entries.** Deletion requests redact handshake
payloads but leave a tombstone (`deleted: true`, no PII) in the trail.

## 7. Segregation from job-application decisions

Mentorship data — cards, questionnaires, handshakes, ratings, session
notes — **must never influence job-application decisions** (fit scores,
shortlists, application queues). `safety.segregation_check()` scans the
mentorship stores and the application stores for cross-references and
fails loudly if any exist. This is a hard boundary, not a guideline.

## 8. Honesty invariants (cold-start)

* Empty mentor directory / no capacity / no path: the system says so
  plainly and offers next steps. It never invents mentors, people, or
  sessions.
* Synthetic fixtures (tests, demos) carry `SYNTHETIC-` prefixed ids and
  `synthetic: true`. Production code paths reject synthetic records
  where identity matters.
* The warm-path planner (epic 5) and the introduction handshake DRAFT
  only — Veto never sends messages, connection requests, or emails on
  anyone's behalf. Sending is always the human's explicit act in their
  own client.

## 9. Abuse controls (epic 6, `safety.py`)

* Block: a blocked actor never appears in matches/previews and cannot
  start or answer handshakes with the blocker; pending handshakes between
  the pair auto-withdraw.
* Report: reports carry a fixed category and free-text detail; 2+
  distinct reporters quarantine an actor (hidden from discovery, pending
  handshakes withdrawn, audit entry written).
* Rate limits: token-bucket per (actor, action); introduction requests
  are additionally capped per pair and per day (contract §5).
* Deletion: full erase of a mentor card, handshake payloads, session
  notes, and reports on request; block entries keep the id only (safety
  needs to remember who is blocked, never why in PII terms).

## 10. Assumption flags

* **NETWORK-LAYER EVIDENCE GATE (assumption-built):** the roadmap holds
  network work until the individual product proves itself. This package
  is built anyway on the explicit assumption that Q4/Q1 product
  usefulness justifies the network layer. If the assumption breaks, this
  package is shelved behind the same evidence gate — it degrades to the
  pre-existing local-only cold-contact flow and nothing is lost.
* **Cold start:** built on the assumption that mentor supply and mentee
  demand exist. All empty-marketplace states are honest and guiding;
  activity is never faked.
* **Human gates (not build gates):** the two-sided-consent + abuse-case
  suite must pass Paul and the independent framework reviewer before any
  pilot; Q2-day-10 pilot targets need Paul + contracted user researcher +
  independent reviewer approval. The code ships the suite; humans clear
  the gates.
