#!/usr/bin/env python3
"""Append-only extension audit log. Host-only writes.

Every extension action the host brokers — data reads, drafts, network
calls, confirmation requests, grants, denials, sandbox violations — is
appended here as one JSON object per line. Extension code is NEVER given
a write handle to this log; the ``ExtensionAudit`` instance lives in the
host and is not exposed through the extension context.

Integrity: each entry chains to the previous entry's hash
(``prev_hash``), so tampering with history breaks the chain. ``verify()``
recomputes the chain; a broken chain is a program-level incident.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ExtensionAudit:
    def __init__(self, log_path: str | Path) -> None:
        self._path = Path(log_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("", encoding="utf-8")

    def _last_hash(self) -> str:
        last = "GENESIS"
        try:
            with self._path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    last = entry.get("entry_hash", last)
        except OSError:
            pass
        return last

    def append(self, ext_id: str, event: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
        """Append one audit entry. Host-only; never raises."""
        entry = {
            "ts": _utcnow(),
            "extension": ext_id,
            "event": event,
            "detail": detail or {},
            "prev_hash": self._last_hash(),
        }
        body = json.dumps(entry, sort_keys=True, separators=(",", ":"))
        entry["entry_hash"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
        try:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, sort_keys=True) + "\n")
        except OSError:
            pass  # audit write failure must not break the action it records
        return entry

    def verify(self) -> dict[str, Any]:
        """Recompute the hash chain. Returns {ok, entries, error}."""
        prev = "GENESIS"
        count = 0
        try:
            with self._path.open("r", encoding="utf-8") as fh:
                for lineno, line in enumerate(fh, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError as exc:
                        return {"ok": False, "entries": count,
                                "error": f"line {lineno}: invalid JSON: {exc}"}
                    if entry.get("prev_hash") != prev:
                        return {"ok": False, "entries": count,
                                "error": f"line {lineno}: hash chain broken "
                                         "(history was tampered with)"}
                    check = dict(entry)
                    claimed = check.pop("entry_hash", None)
                    body = json.dumps(check, sort_keys=True,
                                      separators=(",", ":"))
                    if hashlib.sha256(body.encode("utf-8")).hexdigest() != claimed:
                        return {"ok": False, "entries": count,
                                "error": f"line {lineno}: entry hash mismatch"}
                    prev = claimed
                    count += 1
        except OSError as exc:
            return {"ok": False, "entries": count, "error": str(exc)}
        return {"ok": True, "entries": count, "error": None}

    def entries_for(self, ext_id: str, limit: int = 200) -> list[dict[str, Any]]:
        """Read-only view. The host may share an extension's own entries
        with it; the extension can never modify them."""
        out: list[dict[str, Any]] = []
        try:
            with self._path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if entry.get("extension") == ext_id:
                        out.append(entry)
        except OSError:
            pass
        return out[-limit:]

    @property
    def path(self) -> Path:
        return self._path
