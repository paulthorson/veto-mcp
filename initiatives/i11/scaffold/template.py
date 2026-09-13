#!/usr/bin/env python3
"""Developer scaffold: generate a complete extension from one template.

``scaffold_extension(...)`` writes a new extension directory containing:

- ``manifest.json``            declared capabilities (edit before shipping)
- ``extension.py``             entrypoint: ACTIONS map receiving ``ctx``
- ``tests/test_<id>.py``      policy-kit suite wired to the new extension
- ``docs/README.md``          capability disclosure for the comprehension check
- ``web_card.html``           dashboard card snippet (all required states)
- ``wizard_step.py``          guided-setup step for the onboarding wizard
- ``cli_snippet.py``          CLI command snippet for integration_notes.md
- ``mcp_snippet.py``          MCP tool snippet for integration_notes.md
- ``RETRO.md``                retro-entry template for governance/LEDGER.md

The scaffold proves its value two ways: it is machine-checked (the
generated tests run the policy suite), and the platform's own reference
extension (reference/role-radar-digest) was built with it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$")


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not _SLUG_RE.match(slug):
        raise ValueError(
            f"cannot derive a valid extension id from {name!r}; "
            "use lowercase letters, digits, and hyphens")
    return slug


def scaffold_extension(
    name: str,
    *,
    description: str = "",
    author: str = "",
    out_dir: str | Path,
    data_scopes: list[str] | None = None,
    action_kinds: list[str] | None = None,
    network_destinations: list[str] | None = None,
) -> dict[str, Any]:
    """Generate an extension project. Returns {ext_id, dir, files}."""
    ext_id = _slug(name)
    out = Path(out_dir) / ext_id
    if out.exists():
        raise FileExistsError(f"{out} already exists")
    (out / "tests").mkdir(parents=True)
    (out / "docs").mkdir(parents=True)

    data_scopes = data_scopes or ["jobs:read"]
    action_kinds = action_kinds or ["read"]
    network_destinations = network_destinations or []

    actions = [
        {"id": f"{ext_id}-{kind}",
         "kind": kind,
         "confirm_required": kind == "confirm-required",
         "description": f"TODO: describe what {ext_id}-{kind} does"}
        for kind in action_kinds
    ]

    manifest = {
        "manifest_version": 1,
        "id": ext_id,
        "version": "0.1.0",
        "name": name,
        "description": description or f"TODO: describe {name}",
        "author": author,
        "permissions": {
            "data": data_scopes,
            "network": {"destinations": network_destinations},
            "actions": actions,
            "pii": "redact",
            "sandbox": {"fs_roots": [], "rate_limit": {"calls_per_minute": 60}},
        },
    }
    files: dict[str, str] = {}

    files["manifest.json"] = json.dumps(manifest, indent=2, sort_keys=True) + "\n"

    action_map = ",\n    ".join(
        f"'{a['id']}': _{a['id'].replace('-', '_')}" for a in actions)
    action_fns = "\n\n".join(
        f"def _{a['id'].replace('-', '_')}(ctx, **params):\n"
        f"    \"\"\"TODO: implement {a['id']} ({a['kind']}).\n\n"
        f"    Available on ctx: data(scope), fs, http, draft_artifact(),\n"
        f"    queue_notification(), request_confirmation(), run_action().\n"
        f"    NEVER import veto core modules — the install scan rejects them.\n"
        f"    \"\"\"\n"
        f"    raise NotImplementedError('implement {a['id']}')"
        for a in actions)
    files["extension.py"] = f'''"""Extension entrypoint: {name}.

The host executes this module with exactly one object in scope: ``ctx``
(the ExtensionContext). Declare capabilities in manifest.json — code
that reaches beyond them is denied at runtime and rejected at install.
'''
    files["extension.py"] += '"""\n\n' + action_fns + (
        f"\n\nACTIONS = {{\n    {action_map},\n}}\n")

    test_id = ext_id.replace("-", "_")
    files[f"tests/test_{test_id}.py"] = f'''#!/usr/bin/env python3
"""Policy-kit suite for the {name} extension. Fails closed."""
import unittest
from pathlib import Path

from initiatives.i11.policy_kit.checks import run_policy_suite

EXT_DIR = Path(__file__).resolve().parent.parent


class TestPolicy(unittest.TestCase):
    def test_policy_suite_passes(self):
        report = run_policy_suite(EXT_DIR)
        failures = [r for r in report["results"] if not r["passed"]]
        self.assertEqual(failures, [],
                         f"policy failures: {{failures}}")


if __name__ == "__main__":
    unittest.main()
'''

    cap_lines = "\n".join(
        f"- data scope `{s}`" for s in data_scopes)
    net_lines = ("\n".join(f"- `{d}`" for d in network_destinations)
                 or "- none (no network access)")
    act_lines = "\n".join(
        f"- `{a['id']}` ({a['kind']})"
        + (" — **requires your confirmation every time it runs**"
           if a["kind"] == "confirm-required" else "")
        for a in actions)
    files["docs/README.md"] = f"""# {name}

{description or 'TODO: describe what this extension does and why.'}

## What this extension can access

{cap_lines}

### Network destinations

{net_lines}

### Actions

{act_lines}

> A new extension can prove what it accesses: everything above comes
> straight from its signed manifest, and the host refuses anything else.
> `confirm-required` actions always re-prompt you at execution time —
> the extension can never confirm on your behalf.
"""

    files["web_card.html"] = f"""<!-- Dashboard card snippet for {name}.
     Required states: empty / loading / blocked / error / ready.
     Wire via initiatives/i11/integration_notes.md (webui.py, dashboard.py).
-->
<section class="ext-card" data-ext-id="{ext_id}">
  <h3>{name}</h3>
  <p class="ext-capabilities" data-state="ready">
    Declared access: {", ".join(data_scopes) or "none"}.
    <a href="#" data-action="show-manifest">Why does it need this?</a>
  </p>
  <p data-state="empty">Nothing to show yet.</p>
  <p data-state="loading" aria-busy="true">Loading…</p>
  <p data-state="blocked">Blocked by policy: <span data-reason></span></p>
  <p data-state="error">Something went wrong: <span data-reason></span></p>
</section>
"""

    files["wizard_step.py"] = f'''"""Wizard step snippet for {name} (onboarding).

Append to the setup wizard per initiatives/i11/integration_notes.md.
"""


def wizard_step_{test_id}(wizard):
    """One guided step: show declared capabilities, ask to enable."""
    capabilities = {data_scopes!r}
    wizard.show_markdown(f"""### Enable {name}?

This extension declares access to: {{", ".join(capabilities) or "nothing"}}.
It cannot access anything else, and confirm-required actions always
ask you first.
""")
    return wizard.confirm("Enable this extension?", default=False)
'''

    files["cli_snippet.py"] = f'''# CLI snippet for {name} — see integration_notes.md.
# (cli.py owns the parser; this file documents the intended surface.)

def cmd_{test_id}(args):
    """`veto extension run {ext_id} <action>` — brokered, audited."""
    from initiatives.i11.sandbox.host import Host
    host = Host()
    host.load_extension("extensions/{ext_id}")
    print(host.run_extension_action("{ext_id}", args.action))
'''

    files["mcp_snippet.py"] = f'''# MCP snippet for {name} — see integration_notes.md.
# (server.py owns tool registration; this file documents the surface.)

# @mcp.tool()
# def {test_id}_run(action: str, params: dict | None = None) -> dict:
#     """Run a {name} action through the extension host broker."""
#     host = get_extension_host()  # integration_notes.md
#     return host.run_extension_action("{ext_id}", action, **(params or {{}}))
'''

    files["RETRO.md"] = f"""# Retro: {name} extension

- **Date:**
- **Effort:**
- **Shipped:**
- **What happened:**
- **Policy-kit result:** (paste run_policy_suite output)
- **Adversarial result:** (paste run_adversarial_suite output)
- **Learning:**
- **What changed:**
"""

    written = []
    for rel, content in files.items():
        path = out / rel
        path.write_text(content, encoding="utf-8")
        written.append(rel)
    return {"ext_id": ext_id, "dir": str(out), "files": sorted(written)}
