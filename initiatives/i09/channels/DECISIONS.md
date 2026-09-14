# Initiative 09 — communication connectors: decision records

## 2026-09-13 — Interactive confirmation at the send boundary (Rule 1 rework)

**Context.** The Rule 1 blind RE-review (`init-09-comms-rereview`,
KICK_BACK) demonstrated two live attacks against the consent/token send
boundary:

1. A caller with zero user involvement minted its own "approval token"
   (`draft_approval_token` — a public deterministic SHA-256 of public
   content), then called `send_followup(confirm=True,
   approval_token=self_minted)` and sent arbitrary email. The token bound
   content to content, not a human approval event to content.
2. `email_sync.send_followup` could be called directly with a
   caller-asserted `confirm=True`, bypassing the registry/token layers
   entirely.

**Decision.** Implement interactive confirmation AT THE SEND BOUNDARY —
the send path itself presents the actual recipient/subject/body and
requires a genuine interactive user approval before sending:

* `registry.request_send_approval(draft)` prints the exact payload on the
  terminal and requires the user to type `send`. Only this function can
  mint an approval record: `{nonce, content_hash(to/subject/body),
  timestamp}`, HMAC-signed into the consent log.
* `registry.authorize_send` accepts only (a) an `approval_id` naming a
  valid, fresh (15-min TTL), unconsumed approval for the EXACT draft, or
  (b) a fresh unconsumed approval already on file for that exact
  content. Otherwise it runs the interactive prompt (TTY) or REFUSES
  (no TTY — agents, scripts, MCP servers fail closed).
* `email_sync.send_followup` enforces the identical boundary internally —
  it never trusts caller-passed flags. `confirm=True` is demoted to a
  deprecated no-op (warns, still routes through the interactive prompt).
  `draft_approval_token` remains as a display/reconciliation digest only;
  the send path never accepts it as authorization.
* Approvals are single-use (`consume_approval` before the transport
  attempt; a failed send does not refund).

**Alternatives considered.**

* *Signature from a user-held key.* Stronger for headless/agentic flows,
  but no user-held signing key exists in this codebase and introducing
  key management (generation, storage, agent access) is a larger,
  riskier change. Revisit if a standing user key (e.g. SSH agent) is
  adopted project-wide.
* *Removing `confirm=` from signatures entirely.* Would break existing
  callers with TypeError; demotion to a fail-closed no-op was chosen so
  old call sites refuse safely with instructions instead of crashing.
* *Per-channel send methods each implementing their own prompt.* Rejected:
  one boundary in `email_sync.send_followup` (enforced via
  `authorize_send`) covers every caller, including direct calls —
  closing the bypass the review demonstrated.

**Residual question (for Paul — veto clearance).** Channel *enablement*
is still a caller-asserted `confirm=True` + enumerated `via` source.
A rogue enable alone can never cause a send (the send boundary is
independent), but whether enablement itself should be interactive is
undecided. The veto still needs Paul's explicit clearance after
re-review — disclosure does not clear it.

## 2026-09-13 — Consent-store integrity and fail-loud writes (kept)

Prior rework, attack-verified by the RE-reviewer and kept intact: consent
writes that do not land are reported as operation FAILURES (never as
success), and the consent log is HMAC-signed with a machine-local key —
tampered/malformed entries are loudly logged and never trusted
(fail closed). `consent_history(..., with_integrity=True)` exposes the
integrity flag so callers can distinguish "no consents" from
"store unverifiable". Key loss fails closed with a recovery procedure —
see `RECOVERY.md`.
