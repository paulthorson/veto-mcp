#!/usr/bin/env python3
"""Signed packages: provenance, version pinning, upgrade review, revocation.

Threat model: a signed package proves *who published what bytes* and
*which version is installed*. It does not make code trustworthy by
itself — the registry's four review gates (registry/) do that. Signing
makes substitution, downgrade, and silent-upgrade attacks detectable.

Mechanics:
- ``package_hash(ext_dir)``: deterministic sha256 over the extension's
  files (sorted relative paths + bytes), excluding ``.data/`` and
  signature sidecars.
- ``sign_package`` / ``verify_package``: Ed25519 over the package hash.
  Asymmetric signatures give real publisher provenance: anyone can
  verify with the publisher's public key, and only the private-key
  holder can sign. The registry pins each publisher's public key, so
  install-time verification is against the PINNED key, not a
  self-asserted one.
- ``InstallRecord``: what is installed where, pinned to an exact
  version + hash. Upgrades require a review record (upgrade review).
- ``RevocationList``: append-only; revoked (id, version) pairs refuse to
  install or load.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey)

SIGNATURE_FILE = ".veto-signature.json"
SIGNING_ALG = "ed25519-v1"

_EXCLUDE_DIRS = {".data", "__pycache__", ".git"}
_EXCLUDE_FILES = {SIGNATURE_FILE}


def package_hash(ext_dir: str | Path) -> str:
    """Deterministic sha256 over extension file bytes (sorted paths)."""
    ext_dir = Path(ext_dir)
    digest = hashlib.sha256()
    files = sorted(
        p for p in ext_dir.rglob("*")
        if p.is_file()
        and p.name not in _EXCLUDE_FILES
        and not any(part in _EXCLUDE_DIRS for part in p.relative_to(ext_dir).parts)
    )
    for path in files:
        rel = str(path.relative_to(ext_dir)).encode("utf-8")
        digest.update(len(rel).to_bytes(4, "big") + rel)
        content = path.read_bytes()
        digest.update(len(content).to_bytes(8, "big") + content)
    return digest.hexdigest()


def generate_keypair() -> tuple[str, str]:
    """Generate an Ed25519 publisher keypair.

    Returns (private_pem, public_hex). The private PEM is for the
    publisher's secure storage; the public hex is published/pinned in
    the registry.
    """
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    private_pem = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()).decode("ascii")
    public_hex = public.public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw).hex()
    return private_pem, public_hex


def _load_private(pem_or_key: str | Ed25519PrivateKey) -> Ed25519PrivateKey:
    if isinstance(pem_or_key, Ed25519PrivateKey):
        return pem_or_key
    return serialization.load_pem_private_key(
        pem_or_key.encode("ascii"), password=None)


def _load_public(hex_or_key: str | Ed25519PublicKey) -> Ed25519PublicKey:
    if isinstance(hex_or_key, Ed25519PublicKey):
        return hex_or_key
    return Ed25519PublicKey.from_public_bytes(bytes.fromhex(hex_or_key))


def _dev_private_key() -> Ed25519PrivateKey:
    """Local-dev publisher key. Production publishers use managed keys;
    the registry pins each publisher's public key."""
    key_file = Path.home() / ".veto" / "publisher_ed25519.pem"
    try:
        if key_file.is_file():
            return serialization.load_pem_private_key(
                key_file.read_bytes(), password=None)
    except OSError:
        pass
    private = Ed25519PrivateKey.generate()
    try:
        key_file.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(key_file), os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                     0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(private.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption()))
    except OSError:
        pass
    return private


def sign_package(ext_dir: str | Path, *, publisher: str,
                 private_key: str | Ed25519PrivateKey | None = None
                 ) -> dict[str, Any]:
    """Hash the package and write the Ed25519 signature sidecar."""
    ext_dir = Path(ext_dir)
    pkg_hash = package_hash(ext_dir)
    private = (_load_private(private_key) if private_key is not None
               else _dev_private_key())
    sig = private.sign(bytes.fromhex(pkg_hash)).hex()
    pubkey_hex = private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    envelope = {
        "alg": SIGNING_ALG,
        "package_sha256": pkg_hash,
        "publisher": publisher,
        "pubkey": pubkey_hex,
        "signed_at": int(time.time()),
        "sig": sig,
    }
    (ext_dir / SIGNATURE_FILE).write_text(
        json.dumps(envelope, indent=2, sort_keys=True), encoding="utf-8")
    return envelope


def verify_package(ext_dir: str | Path, *,
                   public_key: str | Ed25519PublicKey | None = None
                   ) -> dict[str, Any]:
    """Verify the signature sidecar against current file bytes.

    If ``public_key`` is given, the signature must verify against that
    PINNED key (registry install path — real provenance). If omitted,
    the sidecar's embedded pubkey is used (self-asserted: proves the
    bytes are unchanged since signing, but not who signed).
    """
    ext_dir = Path(ext_dir)
    sidecar = ext_dir / SIGNATURE_FILE
    if not sidecar.is_file():
        return {"ok": False, "error": "no signature sidecar; package unsigned"}
    try:
        envelope = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": f"unreadable signature: {exc}"}
    if envelope.get("alg") != SIGNING_ALG:
        return {"ok": False,
                "error": f"unsupported signing alg {envelope.get('alg')!r}"}
    current = package_hash(ext_dir)
    if current != str(envelope.get("package_sha256", "")):
        return {"ok": False, "error": "package bytes changed after signing"}
    key_hex = public_key if public_key is not None else envelope.get("pubkey")
    if not key_hex:
        return {"ok": False, "error": "no public key to verify against"}
    try:
        public = _load_public(key_hex)
        public.verify(bytes.fromhex(str(envelope.get("sig", ""))),
                      bytes.fromhex(current))
    except Exception as exc:
        return {"ok": False,
                "error": f"signature invalid: {exc}"}
    shown_pubkey = (key_hex if isinstance(key_hex, str)
                    else public.public_bytes(
                        serialization.Encoding.Raw,
                        serialization.PublicFormat.Raw).hex())
    return {"ok": True, "publisher": envelope.get("publisher"),
            "package_sha256": current,
            "pubkey": shown_pubkey,
            "pinned": public_key is not None,
            "signed_at": envelope.get("signed_at")}


# ---------------------------------------------------------------------------
# Install records: version pinning + upgrade review
# ---------------------------------------------------------------------------

@dataclass
class InstallRecord:
    ext_id: str
    version: str
    package_sha256: str
    publisher: str
    installed_at: int
    upgraded_from: str | None = None
    upgrade_review: dict[str, Any] = field(default_factory=dict)


class InstallStore:
    """Pin installed extensions to exact (version, hash)."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

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

    def record_install(self, rec: InstallRecord) -> None:
        data = self._read_all()
        data[rec.ext_id] = asdict(rec)
        self._write_all(data)

    def get(self, ext_id: str) -> dict[str, Any] | None:
        return self._read_all().get(ext_id)

    def record_upgrade(self, ext_id: str, new_version: str,
                       new_hash: str, review: dict[str, Any]) -> dict[str, Any]:
        """Upgrades require a review record: {reviewer, verdict, date,
        notes}. A missing/failed review refuses the upgrade."""
        if not review or review.get("verdict") != "pass":
            return {"ok": False,
                    "error": "upgrade requires a passing review record "
                             "{reviewer, verdict: 'pass', date, notes}"}
        current = self.get(ext_id)
        if current is None:
            return {"ok": False,
                    "error": f"{ext_id!r} is not installed; use install, not upgrade"}
        rec = InstallRecord(
            ext_id=ext_id, version=new_version, package_sha256=new_hash,
            publisher=current.get("publisher", ""),
            installed_at=int(time.time()),
            upgraded_from=current.get("version"),
            upgrade_review=review,
        )
        self.record_install(rec)
        return {"ok": True, "from": current.get("version"), "to": new_version}


# ---------------------------------------------------------------------------
# Revocation
# ---------------------------------------------------------------------------

class RevocationList:
    """Append-only revocation list. Revoked (id, version) pairs refuse to
    install or load. Only the publisher key holder (or Paul, per the
    roadmap's human-only clearing rule) appends entries."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _read_all(self) -> list[dict[str, Any]]:
        if not self._path.is_file():
            return []
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def revoke(self, ext_id: str, version: str, reason: str,
               revoked_by: str) -> dict[str, Any]:
        entries = self._read_all()
        entry = {"ext_id": ext_id, "version": version, "reason": reason,
                 "revoked_by": revoked_by, "revoked_at": int(time.time())}
        entries.append(entry)
        self._path.write_text(json.dumps(entries, indent=2, sort_keys=True),
                              encoding="utf-8")
        return entry

    def is_revoked(self, ext_id: str, version: str) -> bool:
        return any(e.get("ext_id") == ext_id and e.get("version") == version
                   for e in self._read_all())

    def list(self) -> list[dict[str, Any]]:
        return self._read_all()
