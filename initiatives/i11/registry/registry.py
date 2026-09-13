#!/usr/bin/env python3
"""Curated registry: publish only extensions that pass all four reviews.

Gates (each recorded with reviewer, verdict, date, notes):
  1. compatibility — manifest validates; entrypoint loads; declared
     actions resolve; policy-kit suite passes.
  2. security      — import scan clean; no network exfiltration path;
     package signature verifies; PII handling matches the declared mode.
  3. ux            — web card renders required states (empty/loading/
     blocked/error); confirmation prompts use plain language; docs exist.
  4. governance    — adversarial suite fully blocked; audit chain
     verifies; confirm-required actions re-prompt through the host.

An extension is installable from the registry only when all four gates
record ``pass``. The registry is a local JSON file by default (local-first);
a remote index is a distribution concern for Initiative 10.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ..manifest.schema import load_manifest, manifest_summary
from ..policy_kit.attacks import run_adversarial_suite
from ..policy_kit.checks import run_policy_suite
from ..sandbox.host import scan_imports
from ..signing.sign import verify_package
from ..signing.sign import RevocationList

GATES = ("compatibility", "security", "ux", "governance")


@dataclass
class GateReview:
    gate: str
    verdict: str  # "pass" | "fail"
    reviewer: str
    date: str
    notes: str = ""


@dataclass
class RegistryEntry:
    ext_id: str
    version: str
    package_sha256: str
    publisher: str
    publisher_pubkey: str = ""
    source_path: str = ""
    capabilities: dict[str, Any] = field(default_factory=dict)
    gates: dict[str, dict[str, Any]] = field(default_factory=dict)
    published_at: int = 0

    def gate_status(self) -> dict[str, str]:
        return {g: self.gates.get(g, {}).get("verdict", "pending")
                for g in GATES}

    def publishable(self) -> bool:
        return all(self.gate_status()[g] == "pass" for g in GATES)


class Registry:
    def __init__(self, path: str | Path,
                 revocations: RevocationList | None = None) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._revocations = revocations

    # -- storage ---------------------------------------------------------------
    def _read_all(self) -> dict[str, dict[str, Any]]:
        if not self._path.is_file():
            return {}
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_all(self, data: dict[str, dict[str, Any]]) -> None:
        self._path.write_text(json.dumps(data, indent=2, sort_keys=True),
                              encoding="utf-8")

    def _entry(self, ext_id: str) -> RegistryEntry | None:
        raw = self._read_all().get(ext_id)
        if raw is None:
            return None
        return RegistryEntry(**raw)

    def _save(self, entry: RegistryEntry) -> None:
        data = self._read_all()
        data[entry.ext_id] = asdict(entry)
        self._write_all(data)

    # -- submission ---------------------------------------------------------------
    def submit(self, ext_dir: str | Path, *, publisher: str,
               publisher_pubkey: str = "") -> dict[str, Any]:
        """Submit an extension for review. Runs the automated gates
        (compatibility, security); ux and governance need human reviewers
        and stay pending until recorded.

        ``publisher_pubkey`` pins the publisher's Ed25519 public key: the
        signature is verified against the PINNED key (real provenance).
        Without it, verification falls back to the sidecar's embedded
        pubkey (self-asserted — integrity only).
        """
        ext_dir = Path(ext_dir)
        try:
            manifest = load_manifest(ext_dir)
        except Exception as exc:
            return {"ok": False, "error": f"manifest invalid: {exc}"}
        if self._revocations and self._revocations.is_revoked(
                manifest["id"], manifest["version"]):
            return {"ok": False,
                    "error": "this version was revoked; cannot submit"}

        gates: dict[str, dict[str, Any]] = {}

        # Compatibility: loads + policy suite passes.
        suite = run_policy_suite(ext_dir)
        gates["compatibility"] = asdict(GateReview(
            gate="compatibility",
            verdict="pass" if suite["failed"] == 0 else "fail",
            reviewer="policy-kit (automated)",
            date=time.strftime("%Y-%m-%d"),
            notes=(f"{suite['passed']}/{suite['passed'] + suite['failed']} "
                   f"policy checks passed"),
        ))

        # Security: import scan + signature + adversarial suite.
        scan = scan_imports(ext_dir)
        sig = verify_package(
            ext_dir, public_key=publisher_pubkey or None)
        adv = run_adversarial_suite()
        sec_notes = []
        sec_ok = True
        if not scan["ok"]:
            sec_ok = False
            sec_notes.append(f"banned imports: {scan['violations']}")
        if not sig["ok"]:
            sec_ok = False
            sec_notes.append(f"signature: {sig['error']}")
        if adv["breached"]:
            sec_ok = False
            sec_notes.append(f"adversarial breaches: {adv['breached']}")
        gates["security"] = asdict(GateReview(
            gate="security",
            verdict="pass" if sec_ok else "fail",
            reviewer="policy-kit + signature check (automated)",
            date=time.strftime("%Y-%m-%d"),
            notes="; ".join(sec_notes) or
                  f"import scan clean, signature ok, "
                  f"{adv['blocked']}/{adv['attacks']} attacks blocked",
        ))

        for gate in ("ux", "governance"):
            gates[gate] = asdict(GateReview(
                gate=gate, verdict="pending", reviewer="",
                date="", notes="awaiting human review"))

        entry = RegistryEntry(
            ext_id=manifest["id"], version=manifest["version"],
            package_sha256=sig.get("package_sha256", ""),
            publisher=publisher,
            publisher_pubkey=(publisher_pubkey
                              or str(sig.get("pubkey", ""))),
            source_path=str(ext_dir.resolve()),
            capabilities=manifest_summary(manifest), gates=gates,
            published_at=int(time.time()),
        )
        self._save(entry)
        return {"ok": True, "entry": asdict(entry),
                "publishable": entry.publishable(),
                "note": "ux and governance gates require human review "
                        "before this extension is installable"}

    def record_gate(self, ext_id: str, gate: str, *, verdict: str,
                    reviewer: str, notes: str = "") -> dict[str, Any]:
        """Record a human review verdict for the ux or governance gate."""
        if gate not in GATES:
            return {"ok": False, "error": f"unknown gate {gate!r}"}
        if verdict not in ("pass", "fail"):
            return {"ok": False, "error": "verdict must be 'pass' or 'fail'"}
        entry = self._entry(ext_id)
        if entry is None:
            return {"ok": False, "error": f"{ext_id!r} not submitted"}
        entry.gates[gate] = asdict(GateReview(
            gate=gate, verdict=verdict, reviewer=reviewer,
            date=time.strftime("%Y-%m-%d"), notes=notes))
        self._save(entry)
        return {"ok": True, "publishable": entry.publishable(),
                "gates": entry.gate_status()}

    # -- install ---------------------------------------------------------------------
    def installable(self, ext_id: str) -> dict[str, Any]:
        entry = self._entry(ext_id)
        if entry is None:
            return {"ok": False, "error": f"{ext_id!r} not in registry"}
        if self._revocations and self._revocations.is_revoked(
                entry.ext_id, entry.version):
            return {"ok": False, "error": "this version was revoked"}
        if not entry.publishable():
            pending = [g for g, v in entry.gate_status().items()
                       if v != "pass"]
            return {"ok": False,
                    "error": f"gates not passed: {pending}; "
                             "curated registry publishes only fully-reviewed "
                             "extensions"}
        return {"ok": True, "source_path": entry.source_path,
                "version": entry.version,
                "package_sha256": entry.package_sha256,
                "publisher_pubkey": entry.publisher_pubkey}

    def list(self) -> list[dict[str, Any]]:
        out = []
        for raw in self._read_all().values():
            entry = RegistryEntry(**raw)
            out.append({"ext_id": entry.ext_id, "version": entry.version,
                        "publisher": entry.publisher,
                        "gates": entry.gate_status(),
                        "publishable": entry.publishable()})
        return sorted(out, key=lambda e: e["ext_id"])
