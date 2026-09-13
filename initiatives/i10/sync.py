#!/usr/bin/env python3
"""Opt-in end-to-end encrypted device sync (Epic 4).

Local-only is the default and stays the default. Sync does nothing until
the user explicitly runs ``enable`` with a passphrase. When enabled:

* Every sync payload is an opaque encrypted envelope (Fernet, key from
  scrypt over the user's sync passphrase). The sync vault — a directory
  the user points at a shared folder, NAS, or USB stick — ever sees
  ciphertext only.
* Both devices derive the SAME key from the SAME passphrase; a 6-word
  pairing code (derived from the key fingerprint) is shown on each device
  so the user can confirm they typed the same passphrase.
* Merge is deterministic and offline-safe:
  - ``outcome-event`` / ``evidence-store`` (append-only JSONL): union by
    record id (``event_id`` / ``record_id``), never duplicated.
  - ``profile`` files: last-writer-wins by embedded ``updated_at``.
* Sync moves ONLY the named stable schemas from ``schemas.py``.

Transport is a pluggable :class:`Vault` — the built-in
:class:`DirectoryVault` reads/writes envelopes in a local directory.
A network transport can be added later behind the same interface; the
envelope format does not change.

Audit: ``sync_audit.jsonl`` records counts and hashes only — never user
content, never the passphrase.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import backup as _backup
from . import schemas

CONFIG_NAME = "sync_config.json"
AUDIT_NAME = "sync_audit.jsonl"
ENVELOPE_MAGIC = b"VETOSYNC1"
# The KDF salt is shared through the vault (plaintext salt file) so every
# device that knows the passphrase derives the SAME key. The salt is not
# secret; the passphrase is. First device to enable generates it.
VAULT_SALT_NAME = "sync-salt.b64"

_WORDS = (
    "amber bronze cedar dawn ember frost grove harbor iris jade kelp lumen "
    "maple north opal pine quartz ridge stone timber umber vale willow xenon "
    "yarrow zephyr"
).split()


# ---------------------------------------------------------------------------
# Crypto helpers (same KDF construction as backup)
# ---------------------------------------------------------------------------


def _crypto():
    try:
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    except ImportError as exc:
        raise RuntimeError(
            "The 'cryptography' package is required for sync. "
            "Install it with: pip install cryptography"
        ) from exc
    return Fernet, Scrypt


def derive_sync_key(passphrase: str, salt: bytes) -> bytes:
    Fernet, Scrypt = _crypto()
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))


def key_fingerprint(key: bytes) -> str:
    return hashlib.sha256(key).hexdigest()[:16]


def pairing_code(key: bytes) -> str:
    """6-word code derived from the key fingerprint. Both devices show the
    same code only if the passphrases match — the user confirms out of
    band before trusting a sync peer."""
    digest = hashlib.sha256(b"veto-pairing:" + key).digest()
    return "-".join(_WORDS[b % len(_WORDS)] for b in digest[:6])


# ---------------------------------------------------------------------------
# Config (opt-in state)
# ---------------------------------------------------------------------------


def _config_path(data_dir: Path) -> Path:
    return data_dir / CONFIG_NAME


def load_config(data_dir: str | Path) -> dict:
    path = _config_path(Path(data_dir))
    if not path.exists():
        return {"enabled": False}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_config(data_dir: Path, config: dict) -> None:
    _config_path(data_dir).write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def _audit(data_dir: Path, action: str, detail: dict) -> None:
    with (data_dir / AUDIT_NAME).open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "action": action, **detail},
                sort_keys=True,
            )
            + "\n"
        )


def _vault_salt(vault_path: Path) -> bytes:
    """Return the shared KDF salt, generating and publishing it on first
    enable. Stored plaintext in the vault — salts are not secret."""
    salt_path = vault_path / VAULT_SALT_NAME
    if salt_path.exists():
        return base64.b64decode(salt_path.read_text(encoding="utf-8").strip())
    salt = os.urandom(16)
    salt_path.write_text(base64.b64encode(salt).decode("ascii"), encoding="utf-8")
    return salt


def enable(data_dir: str | Path, passphrase: str, vault_path: str) -> dict:
    """Opt IN to sync. Explicit, reversible, local-only until the user
    points the vault at shared storage themselves.

    The first device to enable generates the shared KDF salt and publishes
    it (plaintext) in the vault; joining devices reuse it, so the same
    passphrase always derives the same key on every device. Confirm the
    6-word pairing code matches on both devices before trusting a peer.
    """
    if not passphrase or len(passphrase) < 8:
        raise ValueError("Sync passphrase must be at least 8 characters.")
    data_dir = Path(data_dir)
    vault_dir = Path(vault_path).expanduser()
    vault_dir.mkdir(parents=True, exist_ok=True)
    salt = _vault_salt(vault_dir)
    key = derive_sync_key(passphrase, salt)
    config = {
        "enabled": True,
        "device_id": uuid.uuid4().hex[:12],
        "salt_b64": base64.b64encode(salt).decode("ascii"),
        "key_fingerprint": key_fingerprint(key),
        "vault_path": str(Path(vault_path).expanduser()),
        "enabled_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "sequence": 0,
    }
    _save_config(data_dir, config)
    Path(config["vault_path"]).mkdir(parents=True, exist_ok=True)
    _audit(data_dir, "sync_enabled", {"device_id": config["device_id"]})
    return {
        "enabled": True,
        "device_id": config["device_id"],
        "pairing_code": pairing_code(key),
        "key_fingerprint": config["key_fingerprint"],
    }


def disable(data_dir: str | Path) -> dict:
    data_dir = Path(data_dir)
    cfg = load_config(data_dir)
    cfg["enabled"] = False
    _save_config(data_dir, cfg)
    _audit(data_dir, "sync_disabled", {})
    return {"enabled": False}


# ---------------------------------------------------------------------------
# Envelope format
# ---------------------------------------------------------------------------


@dataclass
class Envelope:
    device_id: str
    sequence: int
    created_at: str
    schema_versions: dict[str, str]
    datasets: dict[str, Any]  # schema_name -> {rel_path: [records] | {doc}}

    def to_bytes(self, key: bytes) -> bytes:
        Fernet, _ = _crypto()
        body = json.dumps(
            {
                "device_id": self.device_id,
                "sequence": self.sequence,
                "created_at": self.created_at,
                "schema_versions": self.schema_versions,
                "datasets": self.datasets,
            },
            sort_keys=True,
        ).encode("utf-8")
        token = Fernet(key).encrypt(body)
        header = json.dumps(
            {"magic": "VETOSYNC1", "created_at": self.created_at},
            sort_keys=True,
        ).encode("utf-8")
        return (
            ENVELOPE_MAGIC
            + len(header).to_bytes(4, "big")
            + header
            + token
        )

    @staticmethod
    def from_bytes(raw: bytes, key: bytes) -> "Envelope":
        if raw[:9] != ENVELOPE_MAGIC:
            raise ValueError("Not a Veto sync envelope.")
        hlen = int.from_bytes(raw[9:13], "big")
        token = raw[13 + hlen :]
        Fernet, _ = _crypto()
        try:
            body = json.loads(Fernet(key).decrypt(token))
        except Exception as exc:
            raise ValueError(
                "Envelope decryption failed: wrong sync passphrase."
            ) from exc
        return Envelope(
            device_id=body["device_id"],
            sequence=body["sequence"],
            created_at=body["created_at"],
            schema_versions=body["schema_versions"],
            datasets=body["datasets"],
        )


def _read_records(path: Path) -> Any:
    """JSONL -> list of records; JSON -> the document."""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        out = []
        for line in text.splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return out
    return json.loads(text)


def build_envelope(data_dir: str | Path, key: bytes, device_id: str, sequence: int) -> Envelope:
    data_dir = Path(data_dir)
    datasets: dict[str, Any] = {}
    for name, schema in schemas.SCHEMA_REGISTRY.items():
        files: dict[str, Any] = {}
        rels = list(schema.files)
        if name == "profile":
            rels += sorted(
                str(p.relative_to(data_dir))
                for p in (data_dir / "profiles").glob("*.json")
                if str(p.relative_to(data_dir)) not in rels
            )
        for rel in rels:
            path = data_dir / rel
            if path.exists():
                files[rel] = _read_records(path)
        if files:
            datasets[name] = files
    return Envelope(
        device_id=device_id,
        sequence=sequence,
        created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        schema_versions=schemas.schema_versions(),
        datasets=datasets,
    )


# ---------------------------------------------------------------------------
# Merge (deterministic, offline-safe)
# ---------------------------------------------------------------------------


def _merge_append_only(
    local: list[dict], remote: list[dict], key: str
) -> tuple[list[dict], int, int]:
    """Union by record key; remote wins on key collision for correctable
    fields only when it carries a newer ``recorded_at``/``created_at``."""
    by_key: dict[str, dict] = {}
    for rec in local:
        if isinstance(rec, dict) and rec.get(key):
            by_key[str(rec[key])] = rec
    added = 0
    updated = 0
    for rec in remote:
        if not isinstance(rec, dict) or not rec.get(key):
            continue
        k = str(rec[key])
        if k not in by_key:
            by_key[k] = rec
            added += 1
        else:
            old, new = by_key[k], rec
            old_ts = str(old.get("recorded_at") or old.get("created_at") or "")
            new_ts = str(new.get("recorded_at") or new.get("created_at") or "")
            if new_ts > old_ts:
                by_key[k] = new
                updated += 1
    return list(by_key.values()), added, updated


def merge_envelope(data_dir: str | Path, envelope: Envelope, own_device_id: str) -> dict:
    """Merge a peer envelope into the local data dir. Never deletes local
    records; returns a merge report with counts only."""
    if envelope.device_id == own_device_id:
        return {"merged": False, "reason": "own envelope"}
    data_dir = Path(data_dir)
    report: dict[str, Any] = {"merged": True, "peer": envelope.device_id[:8], "datasets": {}}
    for name, files in envelope.datasets.items():
        schema = schemas.get_schema(name)
        ds_report: dict[str, Any] = {}
        for rel, payload in files.items():
            dest = data_dir / rel
            # Path-traversal guard.
            if not str(dest.resolve()).startswith(str(data_dir.resolve())):
                raise ValueError(f"Refusing to write outside data dir: {rel}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(payload, list) and schema.record_key:
                local = _read_records(dest) if dest.exists() else []
                if not isinstance(local, list):
                    local = []
                merged, added, updated = _merge_append_only(local, payload, schema.record_key)
                # Re-validate merged records against the stable schema.
                merged = [
                    r for r in merged if not schema.validator(r)
                ]
                dest.write_text(
                    "\n".join(json.dumps(r, sort_keys=True) for r in merged) + "\n",
                    encoding="utf-8",
                )
                ds_report[rel] = {"added": added, "updated": updated, "total": len(merged)}
            elif isinstance(payload, dict):
                # Profiles: last-writer-wins by updated_at.
                local = _read_records(dest) if dest.exists() else {}
                if not isinstance(local, dict):
                    local = {}
                lts = str(local.get("updated_at") or "")
                rts = str(payload.get("updated_at") or "")
                if rts >= lts and schema.validator(payload) == []:
                    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
                    ds_report[rel] = {"replaced": True}
                else:
                    ds_report[rel] = {"replaced": False}
        report["datasets"][name] = ds_report
    _audit(data_dir, "sync_merged", {"peer": envelope.device_id[:8]})
    return report


# ---------------------------------------------------------------------------
# Vault transport (pluggable; DirectoryVault built in)
# ---------------------------------------------------------------------------


class DirectoryVault:
    """The vault is a directory the user controls (shared folder, NAS,
    USB). It stores opaque ciphertext envelopes only — the host learns
    nothing about content."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)

    def publish(self, envelope_bytes: bytes, device_id: str, sequence: int) -> str:
        name = f"envelope-{device_id}-{sequence:06d}.vetosync"
        (self.path / name).write_bytes(envelope_bytes)
        return name

    def list(self, own_device_id: str = "") -> list[Path]:
        return sorted(
            p
            for p in self.path.glob("*.vetosync")
            if own_device_id not in p.name
        )

    def fetch(self, path: Path) -> bytes:
        return path.read_bytes()


# ---------------------------------------------------------------------------
# Sync round
# ---------------------------------------------------------------------------


def sync_round(data_dir: str | Path, passphrase: str) -> dict:
    """One sync round: publish our envelope, fetch and merge every peer
    envelope. Returns a report with counts only."""
    data_dir = Path(data_dir)
    cfg = load_config(data_dir)
    if not cfg.get("enabled"):
        raise RuntimeError("Sync is not enabled (local-only default). Run enable first.")
    salt = base64.b64decode(cfg["salt_b64"])
    key = derive_sync_key(passphrase, salt)
    if key_fingerprint(key) != cfg["key_fingerprint"]:
        raise ValueError("Wrong sync passphrase.")

    device_id = cfg["device_id"]
    sequence = int(cfg.get("sequence", 0)) + 1
    vault = DirectoryVault(cfg["vault_path"])

    envelope = build_envelope(data_dir, key, device_id, sequence)
    published = vault.publish(envelope.to_bytes(key), device_id, sequence)
    cfg["sequence"] = sequence
    _save_config(data_dir, cfg)

    merged_reports = []
    for path in vault.list(own_device_id=device_id):
        peer = Envelope.from_bytes(vault.fetch(path), key)
        merged_reports.append(merge_envelope(data_dir, peer, device_id))

    _audit(
        data_dir,
        "sync_round",
        {"published": published, "peers_merged": len(merged_reports), "sequence": sequence},
    )
    return {
        "published": published,
        "sequence": sequence,
        "peers_merged": len(merged_reports),
        "merges": merged_reports,
        "pairing_code": pairing_code(key),
    }


def status(data_dir: str | Path) -> dict:
    cfg = load_config(data_dir)
    return {
        "enabled": bool(cfg.get("enabled")),
        "device_id": cfg.get("device_id"),
        "vault_path": cfg.get("vault_path"),
        "sequence": cfg.get("sequence", 0),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="veto-sync", description=__doc__)
    parser.add_argument("--data-dir", required=True)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("enable", help="Opt in to encrypted sync")
    p.add_argument("--passphrase", required=True)
    p.add_argument("--vault", required=True, help="Vault directory (shared folder/NAS/USB)")

    sub.add_parser("disable", help="Opt out (local-only)")
    sub.add_parser("status", help="Show sync status")
    p = sub.add_parser("sync", help="Run one sync round")
    p.add_argument("--passphrase", required=True)
    p = sub.add_parser("pairing-code", help="Show the pairing code for this device")
    p.add_argument("--passphrase", required=True)

    args = parser.parse_args(argv)
    if args.command == "enable":
        print(json.dumps(enable(args.data_dir, args.passphrase, args.vault), indent=2))
    elif args.command == "disable":
        print(json.dumps(disable(args.data_dir), indent=2))
    elif args.command == "status":
        print(json.dumps(status(args.data_dir), indent=2))
    elif args.command == "sync":
        print(json.dumps(sync_round(args.data_dir, args.passphrase), indent=2, default=str))
    elif args.command == "pairing-code":
        cfg = load_config(args.data_dir)
        key = derive_sync_key(args.passphrase, base64.b64decode(cfg["salt_b64"]))
        print(pairing_code(key))
    return 0


if __name__ == "__main__":
    sys.exit(main())
