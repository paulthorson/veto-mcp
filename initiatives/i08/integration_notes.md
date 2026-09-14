# Initiative 08 — integration notes (for the later integration sweep)

**Do not apply by editing cli.py / webui.py / dashboard.py / server.py
directly in this workstream** — those files belong to other teams. The
snippets below are exact, paste-ready wiring for the sweep owner.

All snippets assume repo root on `sys.path` (as today).

---

## 1. server.py — register Initiative 08 MCP tools

`server.py` already imports `contribute` and calls
`contribute.register_tools(mcp)` (near the module registry). Add,
immediately after that call:

```python
from initiatives.i08.tools import register_i08_tools
register_i08_tools(mcp)
```

New tools registered: `contribution_purposes`,
`contribution_grant_consent`, `contribution_withdraw_consent`,
`contribution_receipts`, `contribution_impact_digest`,
`contribution_quarantine_status`, `contribution_methodology`,
`contribution_scrub_rules`. None transmit anything.

Also add `"initiatives.i08"` (or the tool names) to the server module
allow-list where `contribute` appears (server.py ~line 180,
`"contribute",` in the module tuple) so the tools are exposed.

## 2. cli.py — new `contribute` sub-actions (no top-level changes needed)

`contribute.register_cli(subparsers)` already wires the `contribute`
command; the new actions (`purposes`, `grant`, `withdraw`, `receipts`,
`impact-digest`, `quarantine-status`, `methodology`) and the `--purpose`
flag are implemented inside `contribute.py` itself. No cli.py edit is
required — verify `veto contribute purposes` lists the four purposes.

Optional UX follow-up (sweep owner): surface quarantine-lock state in
the `veto contribute` help epilog.

## 3. webui.py — GOVERN: contribute section (~line 782)

### 3a. Purpose-aware preview/submit handlers

Replace `_h_contrib_preview` and `_contrib_submit_confirmed` bodies to
thread the purpose through (default keeps current behavior):

```python
def _h_contrib_preview(params):
    import contribute
    _require(params, "session_ids")
    purpose = params.get("purpose", "persona_improvements")
    return contribute.preview_contribution(list(params["session_ids"]),
                                           purpose=purpose)


def _contrib_submit_confirmed(params):
    import contribute
    purpose = params.get("purpose", "persona_improvements")
    return contribute.submit_contribution(list(params["session_ids"]),
                                          confirmed=True, purpose=purpose)
```

And in `_contrib_preview_canonical`, include the purpose in the
canonical string so the submit gate binds purpose:

```python
canonical = json.dumps(
    {"session_ids": sorted(str(s) for s in session_ids),
     "purpose": params.get("purpose", "persona_improvements"),
     "bundle_hash": result["bundle_hash"]},
    sort_keys=True,
)
```

### 3b. New handlers (add below `_h_contrib_toggle`)

```python
def _h_contrib_purposes(_params):
    import contribute
    from initiatives.i08 import purposes as _purposes
    from pathlib import Path
    base = Path(contribute.CONTRIB_DIR).parent
    return {"purposes": _purposes.purpose_definitions(),
            "consent": _purposes.consent_summary(base)}


def _h_contrib_grant(params):
    import contribute
    from initiatives.i08 import purposes as _purposes
    from pathlib import Path
    _require(params, "purpose")
    return _purposes.grant_consent(params["purpose"],
                                   Path(contribute.CONTRIB_DIR).parent)


def _h_contrib_withdraw(params):
    import contribute
    from initiatives.i08 import purposes as _purposes
    from pathlib import Path
    _require(params, "purpose")
    return _purposes.withdraw_consent(params["purpose"],
                                      Path(contribute.CONTRIB_DIR).parent)


def _h_contrib_receipts(_params):
    from initiatives.i08 import receipts as _receipts
    return _receipts.list_receipts()


def _h_contrib_impact_digest(_params):
    from initiatives.i08 import impact as _impact
    return _impact.impact_digest()


def _h_contrib_quarantine_status(_params):
    from initiatives.i08 import quarantine as _quarantine
    allowed, reason = _quarantine.sending_allowed()
    return {"sending_allowed": allowed, "reason": reason,
            "incidents": _quarantine.incident_summary()}


def _h_contrib_methodology(_params):
    from initiatives.i08 import methodology as _methodology
    return {"version": _methodology.METHODOLOGY_VERSION,
            "methodology": _methodology.generate()}
```

### 3c. Catalog entries (webui.py ~line 1374, inside the contribute actions list)

```python
_a("purposes", "Show the four contribution purposes and consent state.",
   _h_contrib_purposes, []),
_a("grant", "Grant standing consent for a purpose.",
   _h_contrib_grant, [_p("purpose", "string", True)]),
_a("withdraw", "Withdraw standing consent for a purpose.",
   _h_contrib_withdraw, [_p("purpose", "string", True)]),
_a("receipts", "List local contribution receipts.",
   _h_contrib_receipts, []),
_a("impact_digest", "Which product changes your contributions informed.",
   _h_contrib_impact_digest, []),
_a("quarantine_status", "Contribution send-lock and incident summary.",
   _h_contrib_quarantine_status, []),
_a("methodology", "Public contribution methodology.",
   _h_contrib_methodology, []),
```

Also update the existing `preview`/`submit` action param lists to accept
an optional `purpose` string param.

## 4. dashboard.py — `wf_contribute` (~line 1195)

Extend the preview-only workflow to show purpose + ruleset version +
quarantine state. Insert after the bundle-hash print:

```python
    from initiatives.i08 import quarantine as _i08_quarantine
    allowed, lock_reason = _i08_quarantine.sending_allowed()
    print(f"  Purpose: {bundle.get('contribution_purpose', '?')} "
          f"(v{bundle.get('purpose_version', '?')}) | "
          f"Scrub ruleset: v{bundle.get('scrub_ruleset', '?')}")
    if not allowed:
        print(f"  SENDING DISABLED: {lock_reason}")
```

And in the session loop, receipts are available after submit via
`initiatives.i08.receipts.list_receipts()` — the dashboard stays
preview-only; submitting remains the contribute module's confirm flow.

## 5. Contract both sides build against

Cross-initiative consumers (e.g. Initiative 12's consent-based
analytics) import from `initiatives.i08.contracts`:

```python
from initiatives.i08 import contracts as i08
i08.SCRUB_RULESET_VERSION  # "2"
i08.MIN_COHORT_K           # 25
i08.PURPOSES               # {purpose_id: {version, title, requires_standing_grant}}
i08.CLEARING_ROLES         # frozenset of specialist role ids (see quarantine.py)
i08.BUNDLE_SCHEMA          # "veto-contribution/1"
```

Bundle shapes per purpose (see `initiatives/i08/bundles.py`): the persona
purpose stages `bundle_kind: persona_excerpts` (scrubbed excerpts);
diagnostics, provider health, and research stage
`bundle_kind: aggregate_counters` (counters only — the builder rejects
content fields, so a UI must never offer transcript review for those
purposes; show the aggregate counters instead).

Stability promise: frozen for Q2; additive changes only.

## 6. Verification for the sweep owner

- `python3 tests/run.py` — full suite green (baseline 955 passed at
  workstream start; i08 adds new suites).
- `veto contribute purposes` → four purposes, all OFF by default.
- `veto contribute preview --session-ids <id> --purpose research` →
  bundle tagged `contribution_purpose: research`, ruleset v2.
- `veto contribute quarantine-status` → sending_allowed true, zero incidents.
- Methodology doc: generated on demand by `veto contribute methodology`
  into `contributions/methodology.md` (regenerate after any
  purpose/ruleset/decision change).
