# Channel consent store — integrity-key recovery runbook

Applies to: `initiatives/i09/channels/registry.py` (the channel consent /
send-approval store used by the `gmail` channel and every channel send).

## What the key is

The store is an append-only JSONL log (`channel_consent.jsonl`) where every
entry is HMAC-SHA256-signed with a **machine-local integrity key** —
`channel_consent.key`, 32 random bytes, written `0o600` next to the log,
generated once on first use, never hardcoded, never leaves the machine.

The key is NOT an encryption key: the log is plaintext (it is a local
audit trail). The key proves *integrity* — that an entry was written by
this machine's registry and not tampered with afterward.

## What key loss looks like (fail closed, by design)

If the key is lost (deleted, corrupted, unreadable, or the log was copied
from another machine), **nothing silently degrades**:

* `is_enabled()` returns `False` for every channel — channels read as
  disabled.
* Every send is refused (`consent_store_unverifiable` / `not_interactive`).
* The log carries ERROR entries pointing here, e.g.:

```
CONSENT INTEGRITY: cannot load machine key (...); treating existing
consent data as unverifiable — all channels read as disabled and pending
send approvals are void. Recovery procedure:
initiatives/i09/channels/RECOVERY.md.
```

There is deliberately no way to "accept" the old entries: with the key
gone, a signature can no longer be checked, and trusting them would let an
attacker who planted entries in the log bypass every consent gate.

## Recovery procedure (operator steps)

1. **Confirm the diagnosis.** Check the ERROR logs above; confirm
   `channel_consent.key` is missing/corrupt (or its backup is the one you
   want to abandon). If the key file merely has wrong permissions, fixing
   permissions (`chmod 600`) and restarting is enough — no re-keying
   needed.

2. **Re-key.** Either:
   * call `registry.rotate_consent_key()` — it archives the current key
     (if any) as `channel_consent.key.<epoch>.bak` (`0o600`) and forces a
     fresh key to be generated on next use; or
   * delete `channel_consent.key` — a fresh 32-byte key is generated
     automatically on the next consent write.

   Both paths are equivalent: the new key will NOT verify anything signed
   with the old one.

3. **Verify the new key exists and is private.**
   `ls -l channel_consent.key` → `-rw-------` (0o600), 32+ bytes. The
   registry enforces this on write; the check is a sanity step.

4. **Re-establish consents.** Every channel must be explicitly re-enabled
   by the user — there is no bulk restore (the old entries are
   cryptographically dead). Run the guided wizard (or call
   `enable_channel(name, confirm=True, via="cli-wizard")` interactively)
   for each channel the user wants back. `enabled_channels()` should list
   them afterward.

5. **Re-approve pending sends.** All `send_approval` records are void.
   Re-present each draft to the user and collect a fresh interactive
   approval (`request_send_approval`); approvals are 15-minute TTL,
   single-use.

6. **Audit.** `consent_history(channel, with_integrity=True)` returns
   `(entries, integrity_ok)` — confirm `integrity_ok` is `True` and the
   history shows the fresh enables. Any remaining ERROR integrity logs
   mean some old/foreign entry is still in the file.

## Operational guidance

* **Back up the key with the machine's other secrets** (same backup that
  holds SSH keys / credential files). Restoring the key file restores
  trust in the existing log — no re-enabling needed.
* **Do not copy `channel_consent.jsonl` between machines** and expect it
  to verify: the key is per-machine. A copied log fails closed, which is
  the safe direction.
* **Rotation is the same procedure** (`rotate_consent_key()`), used
  proactively when the key may have been exposed (e.g. a backup was
  shared). Exposure of the key alone does not decrypt anything (the log
  is plaintext), but it would let someone forge entries — rotate and
  re-enable.
* **Old entries are never re-trusted.** Even if the lost key is found
  later, `rotate_consent_key()` archives it; to re-trust the old log you
  must deliberately restore the archived `.bak` file over
  `channel_consent.key` — a conscious operator decision, never automatic.

## Design note (why fail-closed is the safe default)

The store gates real-world sends. If key loss *silently* invalidated
consents but sends still went out (or worse, silently re-enabled
channels), an attacker who deletes the key file could bypass the entire
consent layer. Failing closed — disabled channels, refused sends, loud
logs, and this runbook — keeps the failure visible and recoverable.
