# Scrub / Quarantine Contract — Initiative 08

**Status: ACTIVE (contract v1, 2026-09-13)** · Owner: Initiative 08 build team ·
Machine-readable mirror: `initiatives/i08/contracts.py`

This contract is the hard gate between a contributor's device and anything
that leaves it. It is published before the surrounding product work so
reviewers, the contracted security/privacy specialist, and Paul can judge
the mechanism on its own.

## 1. Definitions

- **Transmission.** In Veto's local-first model, `submit_contribution`
  never pushes, uploads, or transmits anything itself: it stages a bundle
  to `contributions/outbox/` for the contributor's own manual delivery
  (e.g. a `gh` PR they run themselves). "Sending" in this contract means
  *staging a bundle for delivery* — the last step Veto controls. The
  quarantine lock disables staging for all purposes and all bundles.
- **Nothing transmitted by default.** Every purpose is OFF by default;
  no collection runs without an explicit grant (diagnostics, provider
  health, research) or a per-bundle preview + confirmed submit (persona
  improvements). There is no network code path in the contribution flow —
  verified by test (`test_i08_default_off.py`).
- **Personal or secret data.** Anything matching the scrub ruleset's
  detectors (names, emails, phones, handles, street addresses, employer
  names from session metadata, IBAN/account/SSN-shaped strings, API
  credentials, tokens, high-entropy secrets, absolute paths, IPs /
  internal hostnames), plus anything a runtime check flags.

## 2. The scrub contract

- Scrubbing runs **on-device, before preview**, with ruleset
  **v2** (`initiatives/i08/scrub.py`). Unicode normalization (NFKC,
  zero-width stripping, homoglyph folding) and email deobfuscation run
  *before* detection so obfuscated PII cannot smuggle past the detectors.
- The rule table is **versioned** and published verbatim in every
  preview and in the public methodology. Every bundle records
  `scrub_ruleset: "2"` so a future rule change can never silently alter
  what "scrubbed" meant for an already-consented payload.
- Transcripts contribute **excerpts only** (2000 chars/turn cap), never
  verbatim walls of text.
- **Scrub tests are adversarial by contract**: the fixture suite has
  clean / dirty / adversarial tiers (zero-width emails, homoglyph names,
  "j dot doe at gmail", base64 secrets, PII split across excerpt
  boundaries, secrets in code snippets, addresses, API-key shapes). Any
  dirty/adversarial miss is a **scrub-test failure** → quarantine (§3),
  not a silent pass.
- The contract is **detect-and-quarantine, not provably perfect**.
  Residual risk (unusual names, non-US ID formats, paraphrased personal
  data) is disclosed in the methodology's "known limitations".

## 3. The quarantine contract (load-bearing)

On **any** scrub-test failure, fixture miss, or runtime check hit:

1. **Payload quarantined.** Moved to
   `contributions/quarantine/<incident_id>/` with the raw bundle, the
   failing check name, and a machine-generated incident record. It is
   never transmittable from quarantine.
2. **Sending disabled globally.** The kill-switch flips to a **locked**
   state (`contributions_locked` in settings). All purposes, all
   bundles. User toggles (`set_contributions_enabled`) **cannot** clear
   the locked state — tested.
3. **Clearing requires a named human.** A **named contracted
   security/privacy specialist** writes a clearing entry that **names
   themselves and the reason**, with root cause, fix, and re-test
   evidence. Schema rejects vague entries ("looks fine", "ok", "n/a").
   > **Assumption flag:** this role does not exist yet. Until a named
   > specialist is contracted, a quarantine lock **cannot be cleared by
   > design** — the mechanism working, not a bug. This is the
   > initiative's critical-path dependency.
4. **Independent verification.** The **independent framework reviewer**
   re-runs the failing check + the fix against the adversarial fixtures
   and records a `verified`/`rejected` verdict with evidence summary.
5. **Paul retains veto authority** at every step. A recorded veto blocks
   clearing until the veto author withdraws it.

Unlock requires, in order: open incident → valid clearing entry →
reviewer `verified` recorded *after* the clearing entry → no active veto
recorded after that verification. Incidents are append-only and never
deleted, only closed — a bad clear is auditable after the fact. There is
no "override for convenience" path. Deliberate.

## 4. Runtime checks (where quarantine triggers fire)

Quarantine is reserved for **evidence that personal/secret data escaped
or could escape** — not for user error. By construction, submit can only
ever stage the exact bytes persisted at preview time, so a preview/submit
mismatch can never result in unreviewed bytes being staged: mismatches
refuse (re-preview required) without quarantining.

| Check | When | On hit |
|---|---|---|
| `runtime_post_scrub_audit` | At submit: quarantine-trigger detectors re-run over the final scrubbed bundle text | Quarantine + global lock |
| `residual_pii` | At submit: sensitive candidates extracted from raw turns must not appear verbatim in scrubbed output | Quarantine + global lock |
| `scrub_selftest` | Adversarial fixture suite (CI + on-demand) | Quarantine of the offending payload in drill mode; CI failure |
| preview missing / bundle not previewed | At submit: no preview record, or the exact bundle was never previewed | Refuse WITHOUT quarantine (user error; nothing staged) |
| preview bytes integrity failure | At submit: persisted preview bytes do not hash to their key | Refuse WITHOUT quarantine (re-preview required) |

## 5. Aggregation rules

- Minimum cohort **k ≥ 25** contributing devices per published slice
  (tunable, published). Slices below k are **suppressed entirely** —
  never shown as "low N", never interpolated.
- Generalization ladder: exact → industry/category → all.
- Research-purpose data **never ships record-level rows**; content
  fields are rejected by schema before aggregation.

## 6. Consent & receipts (summary)

- Four purposes (product diagnostics, persona improvements, provider
  health, research), each with a versioned definition; all OFF by
  default. Consent is per-purpose (standing grant) + per-bundle
  (purpose, purpose version, ruleset version, bundle hash in the
  append-only log).
- Every accepted contribution gets a **local, hash-chained receipt**:
  what (hash, ruleset, bytes), why (purpose + definition version), when,
  removal path with honest limits, impact pointer. Receipts never leave
  the device and never appear in the public methodology.

## 7. Evidence this contract holds

- `tests/test_i08_scrub.py` — ruleset v2 unit + adversarial fixtures.
- `tests/test_i08_quarantine.py` — full drill: dirty payload →
  quarantine → locked (all purposes, toggle cannot clear) → clearing
  entry schema → reviewer verification → unlock; veto blocks.
- `tests/test_i08_default_off.py` — nothing transmittable by default;
  no network in the contribution path.
- Framework adversarial review: security + privacy domains (ticket
  `muse/2026-09-13/roadmap-exec/init-08`), then QA.
