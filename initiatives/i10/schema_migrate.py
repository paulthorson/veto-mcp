#!/usr/bin/env python3
"""Versioned schema migrations for Veto local data (Epic 2).

A migration is a small module under ``initiatives/i10/migrations/`` that
declares::

    MIGRATION_ID = "0002_outcome_types_v1"
    FROM_VERSION = {"outcome-event": "outcome-min-v0"}
    TO_VERSION   = {"outcome-event": "outcome-v1"}
    def forward(data_dir: Path) -> dict: ...
    def backward(data_dir: Path) -> dict: ...   # rollback
    def verify(data_dir: Path) -> dict: ...     # post-condition proof

The :class:`MigrationRunner` applies pending migrations in order and
records every action in an append-only journal
(``data_dir/_migrations.jsonl``): ``applied`` records and ``rolled_back``
records. Rollback never deletes history — it appends a rollback record
and runs the migration's ``backward`` step, so any migration can be
re-run after rollback.

Compatibility tests (``verify``) are first-class: ``migrate`` refuses to
mark a migration applied unless ``verify`` passes, and
``check_all`` re-runs every applied migration's ``verify`` to prove the
data directory is in a coherent state.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PACKAGE_DIR = Path(__file__).resolve().parent
MIGRATIONS_DIR = PACKAGE_DIR / "migrations"
JOURNAL_NAME = "_migrations.jsonl"


# ---------------------------------------------------------------------------
# Migration loading
# ---------------------------------------------------------------------------


@dataclass
class Migration:
    migration_id: str
    from_version: dict[str, str]
    to_version: dict[str, str]
    module: Any
    path: Path

    def forward(self, data_dir: Path) -> dict:
        return self.module.forward(data_dir)

    def backward(self, data_dir: Path) -> dict:
        return self.module.backward(data_dir)

    def verify(self, data_dir: Path) -> dict:
        return self.module.verify(data_dir)


def discover_migrations() -> list[Migration]:
    """Load every migration module in dependency order (by filename).

    Modules are loaded from their file path (not by dotted name) so
    migration filenames may start with a numeric ordering prefix such as
    ``0001_...``.
    """
    MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)
    migrations: list[Migration] = []
    for path in sorted(MIGRATIONS_DIR.glob("*.py")):
        if path.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(
            f"veto_migration_{path.stem}", path
        )
        if spec is None or spec.loader is None:
            raise ValueError(f"Cannot load migration {path.name}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for attr in ("MIGRATION_ID", "FROM_VERSION", "TO_VERSION", "forward", "backward", "verify"):
            if not hasattr(module, attr):
                raise ValueError(f"Migration {path.name} missing {attr!r}")
        migrations.append(
            Migration(
                migration_id=module.MIGRATION_ID,
                from_version=dict(module.FROM_VERSION),
                to_version=dict(module.TO_VERSION),
                module=module,
                path=path,
            )
        )
    return migrations


# ---------------------------------------------------------------------------
# Journal
# ---------------------------------------------------------------------------


def _journal_path(data_dir: Path) -> Path:
    return data_dir / JOURNAL_NAME


def journal_records(data_dir: Path) -> list[dict]:
    path = _journal_path(data_dir)
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def _append_journal(data_dir: Path, record: dict) -> None:
    path = _journal_path(data_dir)
    record = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), **record}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def applied_ids(data_dir: Path) -> list[str]:
    """Migration ids currently applied (applied minus rolled back, in order)."""
    applied: list[str] = []
    for rec in journal_records(data_dir):
        if rec.get("action") == "applied" and rec["migration_id"] not in applied:
            applied.append(rec["migration_id"])
        elif rec.get("action") == "rolled_back" and rec["migration_id"] in applied:
            applied.remove(rec["migration_id"])
    return applied


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class MigrationError(RuntimeError):
    pass


@dataclass
class MigrationRunner:
    data_dir: Path

    def __post_init__(self) -> None:
        self.data_dir = Path(self.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def pending(self) -> list[Migration]:
        done = set(applied_ids(self.data_dir))
        return [m for m in discover_migrations() if m.migration_id not in done]

    def migrate(self, *, dry_run: bool = False) -> list[dict]:
        """Apply every pending migration in order. Each migration is
        marked applied only after its ``verify`` passes."""
        results: list[dict] = []
        for mig in self.pending():
            detail = mig.forward(self.data_dir) if not dry_run else {"dry_run": True}
            verification = mig.verify(self.data_dir) if not dry_run else {"dry_run": True}
            ok = bool(verification.get("ok", dry_run))
            if not dry_run:
                if not ok:
                    raise MigrationError(
                        f"Migration {mig.migration_id} failed verify: {verification}"
                    )
                _append_journal(
                    self.data_dir,
                    {
                        "action": "applied",
                        "migration_id": mig.migration_id,
                        "from_version": mig.from_version,
                        "to_version": mig.to_version,
                        "detail": detail,
                    },
                )
            results.append(
                {
                    "migration_id": mig.migration_id,
                    "applied": ok and not dry_run,
                    "verify": verification,
                }
            )
        return results

    def rollback(self, migration_id: str) -> dict:
        """Roll back one applied migration. Appends a rollback record; the
        original ``applied`` record stays in the journal (audit trail)."""
        migs = {m.migration_id: m for m in discover_migrations()}
        if migration_id not in migs:
            raise MigrationError(f"Unknown migration {migration_id!r}")
        if migration_id not in applied_ids(self.data_dir):
            raise MigrationError(f"Migration {migration_id!r} is not applied")
        # Refuse to roll back a migration that a later applied migration
        # depends on (later = after it in discovery order).
        order = [m.migration_id for m in discover_migrations()]
        later_applied = [
            mid
            for mid in applied_ids(self.data_dir)
            if order.index(mid) > order.index(migration_id)
        ]
        if later_applied:
            raise MigrationError(
                f"Cannot roll back {migration_id!r}: later migrations still "
                f"applied: {later_applied}"
            )
        detail = migs[migration_id].backward(self.data_dir)
        _append_journal(
            self.data_dir, {"action": "rolled_back", "migration_id": migration_id, "detail": detail}
        )
        return {"migration_id": migration_id, "rolled_back": True, "detail": detail}

    def check_all(self) -> list[dict]:
        """Re-run every applied migration's ``verify`` — the compatibility
        test suite for the current data directory."""
        migs = {m.migration_id: m for m in discover_migrations()}
        results = []
        for mid in applied_ids(self.data_dir):
            verification = migs[mid].verify(self.data_dir)
            results.append(
                {"migration_id": mid, "ok": bool(verification.get("ok")), "verify": verification}
            )
        return results

    def status(self) -> dict:
        return {
            "data_dir": str(self.data_dir),
            "applied": applied_ids(self.data_dir),
            "pending": [m.migration_id for m in self.pending()],
            "journal_records": len(journal_records(self.data_dir)),
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="veto-migrate", description=__doc__)
    parser.add_argument("--data-dir", default="", help="Veto data directory")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("status", help="Show applied/pending migrations")
    p = sub.add_parser("migrate", help="Apply pending migrations")
    p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("rollback", help="Roll back one migration")
    p.add_argument("migration_id")
    p = sub.add_parser("check", help="Re-run verify for all applied migrations")

    args = parser.parse_args(argv)
    data_dir = Path(args.data_dir or _default_data_dir()).expanduser()
    runner = MigrationRunner(data_dir)

    if args.command == "status":
        print(json.dumps(runner.status(), indent=2))
    elif args.command == "migrate":
        for r in runner.migrate(dry_run=args.dry_run):
            print(json.dumps(r, indent=2))
    elif args.command == "rollback":
        print(json.dumps(runner.rollback(args.migration_id), indent=2))
    elif args.command == "check":
        results = runner.check_all()
        for r in results:
            mark = "✓" if r["ok"] else "✗"
            print(f"  [{mark}] {r['migration_id']}")
        if not all(r["ok"] for r in results):
            return 1
    return 0


def _default_data_dir() -> str:
    rec = Path.home() / ".local" / "share" / "veto" / "install.json"
    if rec.exists():
        try:
            return json.loads(rec.read_text(encoding="utf-8"))["data_dir"]
        except (KeyError, json.JSONDecodeError, ValueError):
            pass
    return str(Path.cwd())


if __name__ == "__main__":
    sys.exit(main())
