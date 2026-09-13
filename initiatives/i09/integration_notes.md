# Initiative 09 — integration notes (for the later integration sweep)

**Do not edit cli.py, webui.py, dashboard.py, or server.py in this
initiative.** The snippets below are exact, copy-paste-ready wiring for the
integration sweep. Each snippet names its target file, insertion point, and
the import it needs. All of them are additive: no existing behavior changes.

Conventions used below: `BASE_DIR` is the repo root (already defined in
each target module).

---

## 1. server.py — MCP tools

### 1a. Connector manifests + conformance (read-only tools)

Insert after the existing provider tool registrations (near the other
`register_tools` calls):

```python
from providers import _contract as _i09_contract

@mcp.tool()
def connector_manifest(connector: str) -> dict:
    """Return the proof-of-value declaration for a connector.

    Every connector declares: what it can do, why it may be blocked,
    what data it sends, and which actions require confirmation.
    """
    manifest = _i09_contract.manifest_for(connector)
    if manifest is None:
        return {"ok": False, "error": f"unknown connector {connector!r}",
                "known": sorted(_i09_contract.PROVIDER_MANIFESTS)}
    return {"ok": True, "manifest": manifest.to_dict()}

@mcp.tool()
def connector_conformance(connector: str) -> dict:
    """Run the Q2 capability-contract checks for one provider (no network)."""
    from providers import ashby, greenhouse, lever
    makers = {"greenhouse": greenhouse.GreenhouseProvider,
              "lever": lever.LeverProvider, "ashby": ashby.AshbyProvider}
    maker = makers.get(connector)
    if maker is None:
        return {"ok": False, "error": f"no conformance harness for {connector!r}"}
    results = _i09_contract.conformance_suite(maker(tokens=[]))
    return {"ok": True, "passed": _i09_contract.suite_passed(results),
            "checks": results}
```

### 1b. Reliability scorecard (read-only tool)

```python
from providers import scorecard as _i09_scorecard

@mcp.tool()
def provider_scorecard(format: str = "json") -> str:
    """Reliability scorecard: freshness, error state, last success, and
    capability label per provider. Local-first; reads the on-device health
    store only."""
    rows = _i09_scorecard.scoreboard()
    return _i09_scorecard.to_json(rows) if format == "json" \
        else _i09_scorecard.render_terminal(rows)
```

### 1c. ATS apply-path honesty (read-only tool)

```python
import ats_apply as _i09_ats

@mcp.tool()
def describe_apply_path(board: str) -> dict:
    """Honest apply-path declaration: direct-submit availability, why not,
    and the recommended path. Read-only."""
    return _i09_ats.describe_apply_path(board)
```

### 1d. Channel + calendar tools (consent-gated)

```python
from initiatives.i09.channels import registry as _i09_channels
from initiatives.i09 import calendar_handoff as _i09_cal

@mcp.tool()
def channel_enable(channel: str, confirm: bool = False) -> dict:
    """Enable a communication channel. Explicit opt-in only: without
    confirm=True nothing changes and the manifest is returned for review."""
    return _i09_channels.enable_channel(channel, confirm=confirm, via="mcp")

@mcp.tool()
def channel_disable(channel: str) -> dict:
    return _i09_channels.disable_channel(channel, via="mcp")

@mcp.tool()
def channel_status() -> dict:
    """Which channels are enabled + the consent audit trail."""
    return {"enabled": _i09_channels.enabled_channels(),
            "known": sorted(_i09_channels.CHANNELS),
            "audit": _i09_channels.consent_history()[-20:]}

@mcp.tool()
def calendar_propose(kind: str, application: dict, when: str = "",
                     days_after: int = 7) -> dict:
    """Draft (only) an interview-prep event or follow-up reminder."""
    if kind == "interview_prep":
        draft = _i09_cal.propose_interview_prep(application, interview_at=when or None)
    else:
        draft = _i09_cal.propose_followup_reminder(application, days_after=days_after)
    return {"ok": True, "draft": draft.to_dict(),
            "note": "Draft only — nothing written. Confirm via calendar_handoff."}

@mcp.tool()
def calendar_handoff(drafts: list, confirm: bool = False) -> dict:
    """Hand confirmed drafts to the connected calendar. Refuses without
    confirm=True. The wiring layer executes the returned payload through
    the google-calendar skill."""
    parsed = [_i09_cal.CalendarDraft(**d) for d in drafts]
    return _i09_cal.confirm_and_handoff(parsed, confirm=confirm)
```

### 1e. Record provider health on every fetch (one line per provider call)

Initiative 03's contract is `provider_health.py` (repo root). Providers
write DIRECTLY to it — there is exactly one write path:

```python
import provider_health

# after a provider search/detail attempt:
provider_health.record_fetch(board_name, ok,
                             note="429 on page 2" if not ok else "")
# on CAPTCHA observation (observation only — never bypassed):
provider_health.record_captcha(board_name, "challenged")  # or "blocked"
# on site pushback:
provider_health.cooldown(board_name, seconds, reason="http_429")
```

The scorecard (1b) reads through `providers/health_contract.py`, which
adapts 03's `provider_status()` rows onto `HealthSnapshot` — see
`snapshot_from_status` for the field mapping. If 03 renames fields,
update that one function. `health_contract.py` never edits
`provider_health.py` (another team's file).

---

## 2. cli.py — new commands (additive; new subparsers only)

```python
# in the CLI registration section:
from providers import scorecard as _i09_scorecard
from initiatives.i09.channels import registry as _i09_channels
from initiatives.i09 import calendar_handoff as _i09_cal
import ats_apply as _i09_ats

p = subparsers.add_parser("scorecard", help="Provider reliability scorecard.")
p.add_argument("--json", action="store_true")
p.set_defaults(func=lambda a: print(
    _i09_scorecard.to_json() if a.json
    else _i09_scorecard.render_terminal()))

p = subparsers.add_parser("connector", help="Connector manifest / conformance.")
p.add_argument("name")
p.add_argument("--conformance", action="store_true")
def _cli_connector(a):
    import json as _j
    from providers import _contract as _c
    if a.conformance:
        from providers import ashby, greenhouse, lever
        makers = {"greenhouse": greenhouse.GreenhouseProvider,
                  "lever": lever.LeverProvider, "ashby": ashby.AshbyProvider}
        results = _c.conformance_suite(makers[a.name](tokens=[]))
        print(_j.dumps({"passed": _c.suite_passed(results),
                        "checks": results}, indent=2))
    else:
        m = _c.manifest_for(a.name)
        print(_j.dumps(m.to_dict() if m else {"error": "unknown"}, indent=2))
p.set_defaults(func=_cli_connector)

p = subparsers.add_parser("channel", help="Explicit channel opt-in/out.")
p.add_argument("action", choices=["enable", "disable", "status"])
p.add_argument("name", nargs="?")
p.add_argument("--confirm", action="store_true")
def _cli_channel(a):
    import json as _j
    if a.action == "status":
        print(_j.dumps({"enabled": _i09_channels.enabled_channels()}, indent=2))
    elif a.action == "enable":
        print(_j.dumps(_i09_channels.enable_channel(
            a.name, confirm=a.confirm, via="cli"), indent=2))
    else:
        print(_j.dumps(_i09_channels.disable_channel(a.name, via="cli"), indent=2))
p.set_defaults(func=_cli_channel)

p = subparsers.add_parser("apply-path", help="Honest ATS apply-path declaration.")
p.add_argument("board")
p.set_defaults(func=lambda a: print(__import__("json").dumps(
    _i09_ats.describe_apply_path(a.board), indent=2)))
```

---

## 3. dashboard.py (terminal) — scorecard section

Add a "Providers" section to the terminal dashboard render, after the
existing queue/health sections:

```python
from providers import scorecard as _i09_scorecard

def render_provider_section() -> str:
    return "\nPROVIDERS\n" + _i09_scorecard.render_terminal() + "\n"
```

Call `render_provider_section()` in the main dashboard assembly. The
renderer is pure text and performs no network calls.

---

## 4. webui.py (local web) — scorecard card + connector cards

Add a `/api/scorecard` route returning `scorecard.to_json()` (the JSON
form is designed for the web/phone surfaces), and render one card per row
with columns: provider, status, freshness, error, last success,
capability, budget, cooldown, captcha, streak. Rows with
`"status": "no data"` render an explicit "no data yet" empty state —
never a fake healthy row.

Add a `/api/connector/<name>` route returning the manifest JSON, rendered
as four labeled sections (can do / may be blocked / data sent / needs
confirmation) on the connector detail card.

Session-rescue handoffs (`result["rescue"]` from browser fills) render as
a prominent paused-state card: reason, screenshot, what-to-do guidance,
resume token. The web UI must surface the "Veto never bypasses CAPTCHAs"
note verbatim from `session_rescue.refusal_note()`.

---

## 5. What NOT to wire (deliberate)

* WhatsApp/Discord/Messenger channels: declaration + registry only. No
  transport is wired until the corresponding skill is connected AND the
  user explicitly enables the channel. Do not add send paths for them in
  this sweep.
* `ats_direct` verified submits: the registry has no verified endpoints;
  `apply_direct` with confirm=True still returns "not available". Do not
  wire a submit button to it until an endpoint flips to "verified" with a
  field spec and passes review.
* Calendar writes: `confirm_and_handoff` returns a payload; the sweep must
  execute it through the google-calendar skill with the user's grant —
  never invent a direct API write.
