# Initiative 10 — integration notes (for the later wiring sweep)

The i10 modules are self-contained under `initiatives/i10/`. They do NOT
touch `cli.py`, `webui.py`, or `dashboard.py`. Paste the snippets below
into those files during the integration sweep. `server.py` is in i10's
file scope — the MCP registration snippet is provided but NOT applied,
so the sweep can land it together with the CLI wiring.

Conventions used below: `DATA_DIR` resolves to the installed data dir
(`~/.local/share/veto/data`, or `install.json`'s `data_dir`).

---

## 1. `cli.py` — new subcommands

Add after the existing `doctor` registration (or wherever subcommands
are wired):

```python
# --- Initiative 10: packaging, backup & secure sync ---
from initiatives.i10 import installer as i10_installer
from initiatives.i10 import schema_migrate as i10_migrate
from initiatives.i10 import backup as i10_backup
from initiatives.i10 import sync as i10_sync
from initiatives.i10 import channels as i10_channels

def _i10_data_dir(args):
    if getattr(args, "data_dir", ""):
        return args.data_dir
    from pathlib import Path
    import json
    rec = Path.home() / ".local" / "share" / "veto" / "install.json"
    if rec.exists():
        try:
            return json.loads(rec.read_text())["data_dir"]
        except (KeyError, ValueError):
            pass
    return "."

p = sub.add_parser("install", help="Install Veto (env checks, deps, onboarding)")
p.add_argument("--yes", action="store_true"); p.add_argument("--with-browser", action="store_true")
p.set_defaults(func=lambda a: i10_installer.main(["install"] + (["--yes"] if a.yes else []) + (["--with-browser"] if a.with_browser else [])))

p = sub.add_parser("uninstall", help="Remove Veto (data kept unless --purge-data)")
p.add_argument("--purge-data", action="store_true")
p.set_defaults(func=lambda a: i10_installer.main(["uninstall"] + (["--purge-data"] if a.purge_data else [])))

p = sub.add_parser("migrate", help="Apply pending schema migrations")
p.add_argument("--data-dir", default=""); p.add_argument("--dry-run", action="store_true")
p.set_defaults(func=lambda a: i10_migrate.main(["--data-dir", _i10_data_dir(a), "migrate"] + (["--dry-run"] if a.dry_run else [])))

p = sub.add_parser("backup", help="Encrypted backup / verify / restore / drill")
p.add_argument("op", choices=["create", "verify", "restore", "drill"])
p.add_argument("--data-dir", default=""); p.add_argument("--file", default="")
p.add_argument("--selective", default="")
p.set_defaults(func=lambda a: i10_backup.main(_i10_backup_args(a)))

p = sub.add_parser("sync", help="Opt-in encrypted device sync (local-only default)")
p.add_argument("op", choices=["enable", "disable", "status", "run"])
p.add_argument("--data-dir", default=""); p.add_argument("--vault", default="")
p.set_defaults(func=lambda a: i10_sync.main(_i10_sync_args(a)))

p = sub.add_parser("channel", help="Release channels: versions / check / promote")
p.add_argument("op", choices=["versions", "check", "promote", "notes"])
p.add_argument("--data-dir", default="")
p.set_defaults(func=lambda a: i10_channels.main(_i10_channel_args(a)))
```

`_i10_backup_args`, `_i10_sync_args`, `_i10_channel_args` translate the
parsed args into the module argv lists; passphrases must come from
`getpass.getpass()` or `$VETO_BACKUP_PASSPHRASE` — never from argv.

---

## 2. `webui.py` — serve the PWA bundle + wiring

Mount the i10 PWA bundle at the web root (new static routes; no changes
to existing routes):

```python
from initiatives.i10 import pwa as i10_pwa
PWA_DIR = i10_pwa.PWA_DIR  # initiatives/i10/pwa/

# Serve (exact framework depends on webui.py's server):
#   /manifest.webmanifest -> PWA_DIR/"manifest.webmanifest"  (application/manifest+json)
#   /service-worker.js    -> PWA_DIR/"service-worker.js"     (application/javascript, Serve from ROOT scope)
#   /deferred-queue.js    -> PWA_DIR/"deferred-queue.js"
#   /offline.html         -> PWA_DIR/"offline.html"
#   /icons/icon-192.png, /icons/icon-512.png -> served from webui static icons dir
```

In `index.html` `<head>`:

```html
<link rel="manifest" href="/manifest.webmanifest">
<meta name="theme-color" content="#0d1117">
```

Before `</body>` (after `app.js`):

```html
<script src="/deferred-queue.js"></script>
<script>
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/service-worker.js");
}
</script>
```

Read views served by the existing dashboard API are offline-safe via the
service worker's network-first-with-cache-fallback strategy; mutations
should go through `VetoQueue.submit(method, url, body)` so they defer
when offline. Add a queue badge element with
`data-veto-queue-count` anywhere in the nav.

---

## 3. `dashboard.py` — terminal dashboard

No changes required. Optional: surface backup freshness in the terminal
dashboard via `initiatives.i10.backup`'s audit log
(`<data-dir>/backup_audit.jsonl`, last `backup_created` entry) — a
one-line "last backup: <date>" indicator. Left to the dashboard team's
discretion.

---

## 4. `server.py` — MCP tool registration (i10 file scope; NOT yet applied)

```python
from initiatives.i10 import backup as i10_backup
from initiatives.i10 import sync as i10_sync
from initiatives.i10 import schema_migrate as i10_migrate
from initiatives.i10 import channels as i10_channels

@mcp.tool()
def veto_backup_create(data_dir: str, out_path: str) -> dict:
    """Create an encrypted backup. Passphrase comes from the secure vault,
    never from the tool call."""
    raise NotImplementedError("wire passphrase via secure vault in the sweep")

@mcp.tool()
def veto_backup_verify(backup_path: str) -> dict: ...
@mcp.tool()
def veto_drill(data_dir: str) -> dict:
    """Run the disaster-recovery drill (backup → restore to scratch →
    100% checksum verification). Live data untouched."""
@mcp.tool()
def veto_migrate_status(data_dir: str) -> dict: ...
@mcp.tool()
def veto_sync_status(data_dir: str) -> dict:
    """Sync is local-only unless the user opted in; this tool only reports."""
```

Passphrase handling for MCP tools MUST go through the Secure Vault
capture flow — never a plaintext tool argument. The sweep owns this.

---

## 5. Assumptions the wiring sweep should know

- `outcome-event` (`outcome-min-v0`) is the published frozen contract.
  `profile` (`profile-v1`) and `evidence-store` (`evidence-v0`) are
  i10-defined interfaces; when Initiative 01 publishes the real
  contracts, update `initiatives/i10/schemas.py` registry entries (status
  → `published`) and add migrations — the framework handles the rest.
- Legacy `applications.json` is deliberately NOT a named stable schema;
  backup/sync exclude it. If the capture team promotes it (or an
  equivalent) to a stable schema, add a registry entry.
- `cryptography` is a new runtime dependency (added to
  `requirements.txt`); the Docker image needs a rebuild.
