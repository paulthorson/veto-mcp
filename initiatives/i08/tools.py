#!/usr/bin/env python3
"""Initiative 08 — MCP tools.

Registered by the integration sweep (see ``integration_notes.md``);
server.py calls ``register_i08_tools(mcp)``. Thin wrappers over the
``purposes``, ``receipts``, ``impact``, ``quarantine``, ``methodology``,
and ``scrub`` modules. None of these tools transmit anything.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _base_dir() -> Path | None:
    return None  # default: contribute.CONTRIB_DIR via the i08 modules


def register_i08_tools(mcp: Any) -> None:
    """Register the Initiative 08 MCP tools on an MCP server instance."""
    from . import impact as _impact
    from . import methodology as _methodology
    from . import purposes as _purposes
    from . import quarantine as _quarantine
    from . import receipts as _receipts
    from . import scrub as _scrub

    @mcp.tool()
    def contribution_purposes() -> dict:
        """Show the four contribution purposes, their versioned definitions,
        and current consent state. Everything is OFF by default."""
        import contribute

        base = Path(contribute.CONTRIB_DIR).parent
        definitions = _purposes.purpose_definitions()
        states = {
            pid: _purposes.consent_state(pid, base) for pid in definitions
        }
        return {"purposes": definitions, "consent": states}

    @mcp.tool()
    def contribution_grant_consent(purpose: str) -> dict:
        """Grant standing consent for one contribution purpose
        (product_diagnostics | persona_improvements | provider_health |
        research). Records the versioned purpose definition you approved."""
        import contribute

        base = Path(contribute.CONTRIB_DIR).parent
        return _purposes.grant_consent(purpose, base)

    @mcp.tool()
    def contribution_withdraw_consent(purpose: str) -> dict:
        """Withdraw standing consent for one purpose. Stops FUTURE
        collection only; already-accepted data follows the receipt's
        removal path where possible."""
        import contribute

        base = Path(contribute.CONTRIB_DIR).parent
        return _purposes.withdraw_consent(purpose, base)

    @mcp.tool()
    def contribution_receipts() -> dict:
        """List your local contribution receipts (what was shared, why,
        when, how to request removal). Local-only; never transmitted."""
        return _receipts.list_receipts()

    @mcp.tool()
    def contribution_impact_digest() -> dict:
        """Show which product changes YOUR contributions informed, when
        traceable. Only bundles actually cited by maintainers are
        attributed — never invented."""
        return _impact.impact_digest()

    @mcp.tool()
    def contribution_quarantine_status() -> dict:
        """Show whether contribution sending is locked by quarantine, and
        the sanitized incident summary (counts/classes only)."""
        state = _quarantine.get_state()
        return {
            "sending_allowed": not state.get("locked"),
            "quarantine_state": state,
            "incidents": _quarantine.read_incident_log(),
        }

    @mcp.tool()
    def contribution_methodology() -> dict:
        """Show the public contribution methodology (schemas, exclusions,
        known bias, governance decisions). Public-safe by construction."""
        return {
            "version": _methodology.METHODOLOGY_VERSION,
            "methodology": _methodology.generate(),
        }

    @mcp.tool()
    def contribution_scrub_rules() -> dict:
        """Show the versioned PII scrub rule set applied to every
        contribution bundle before preview."""
        return {
            "ruleset_version": _scrub.SCRUB_RULESET_VERSION,
            "rules": _scrub.scrub_rules_report(),
        }
