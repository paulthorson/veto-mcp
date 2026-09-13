#!/usr/bin/env python3
"""Encrypted backup and restore for Veto (Epic 3).

``create_backup(data_dir, out_path, passphrase)``
    Collects ONLY the named stable schemas (see ``schemas.py``), builds a
    manifest with SHA-256 checksums and record counts, then encrypts the
    whole bundle with Fernet (AES-128-CBC + HMAC, key from scrypt).
    The file header (magic + version + created_at + schema versions +
    record counts) is plaintext; ALL user content is ciphertext.

``verify_backup(path, passphrase)``
    Decrypts and recomputes every checksum. Returns an integrity report;
    ``checksum_match_pct == 100.0`` is the release-candidate bar.

``restore(path, passphrase, data_dir, selective=None)``
    ``selective`` is a list of schema names (e.g. ``["outcome-event"]``)
    to restore only those datasets; default restores everything.

``drill(data_dir, passphrase)``
    Disaster-recovery drill: backup → snapshot the live store → restore
    into a scratch directory → verify 100% checksum match → confirm no
    unrecoverable record gap (per-record id sets compared). Returns a
    drill report dict.

Audit: every action appends one line to ``backup_audit.jsonl`` next to the
data dir with timestamp, action, schema versions, file/record counts,
and the manifest checksum — never user content.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import shutil
import sys
import tarfile
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import schemas

MAGIC = b"VETOBKP1"
AUDIT_NAME = "backup_audit.jsonl"
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1


def _crypto():
    try:
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    except ImportError as exc:
        raise RuntimeError(
            "The 'cryptography' package is required for encrypted backup. "
            "Install it with: pip install cryptography"
        ) from exc
    return Fernet, Scrypt, hashes


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    Fernet, Scrypt, hashes = _crypto()
    kdf = Scrypt(salt=salt, length=32, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _collect_datasets(data_dir: Path) -> dict[str, list[Path]]:
    """{schema_name: [existing files]} for every stable schema."""
    data_dir = Path(data_dir)
    collected: dict[str, list[Path]] = {}
    for name, schema in schemas.SCHEMA_REGISTRY.items():
        files = [data_dir / rel for rel in schema.files if (data_dir / rel).exists()]
        # Also pick up any extra profile files under profiles/ (named profiles).
        if name == "profile":
            extra = sorted((data_dir / "profiles").glob("*.json"))
            files = sorted(set(files) | set(extra))
        if files:
            collected[name] = sorted(files)
    return collected


def _record_count(path: Path) -> int:
    """Count records: JSONL = non-blank lines; JSON = 1."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return 0
    if path.suffix == ".jsonl":
        return sum(1 for line in text.splitlines() if line.strip())
    return 1


def _audit(data_dir: Path, action: str, detail: dict) -> None:
    audit_path = Path(data_dir) / AUDIT_NAME
    entry = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "action": action, **detail}
    with audit_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------


@dataclass
class BackupReport:
    path: str
    schema_versions: dict[str, str]
    files: int
    records: int
    manifest_sha256: str
    created_at: str


def create_backup(
    data_dir: str | Path, out_path: str | Path, passphrase: str
) -> BackupReport:
    if not passphrase or len(passphrase) < 8:
        raise ValueError("Passphrase must be at least 8 characters.")
    data_dir = Path(data_dir)
    out_path = Path(out_path)

    datasets = _collect_datasets(data_dir)
    manifest: dict[str, Any] = {"schema_versions": schemas.schema_versions(), "files": {}}
    total_records = 0
    tar_buf = io.BytesIO()
    with tarfile.open(fileobj=tar_buf, mode="w") as tar:
        for schema_name, files in datasets.items():
            for path in files:
                rel = str(path.relative_to(data_dir))
                checksum = _sha256_file(path)
                records = _record_count(path)
                manifest["files"][rel] = {
                    "schema": schema_name,
                    "sha256": checksum,
                    "records": records,
                    "bytes": path.stat().st_size,
                }
                total_records += records
                tar.add(str(path), arcname=rel)
    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()

    Fernet, _, _ = _crypto()
    salt = os.urandom(16)
    token = Fernet(_derive_key(passphrase, salt)).encrypt(tar_buf.getvalue())

    created_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    header = {
        "magic": "VETOBKP1",
        "created_at": created_at,
        "schema_versions": manifest["schema_versions"],
        "files": len(manifest["files"]),
        "records": total_records,
        "manifest_sha256": manifest_sha,
        "salt_b64": base64.b64encode(salt).decode("ascii"),
    }
    header_bytes = json.dumps(header, sort_keys=True).encode("utf-8")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as fh:
        fh.write(MAGIC)
        fh.write(len(header_bytes).to_bytes(4, "big"))
        fh.write(header_bytes)
        fh.write(len(manifest_bytes).to_bytes(4, "big"))
        fh.write(manifest_bytes)
        fh.write(token)

    report = BackupReport(
        path=str(out_path),
        schema_versions=manifest["schema_versions"],
        files=len(manifest["files"]),
        records=total_records,
        manifest_sha256=manifest_sha,
        created_at=created_at,
    )
    _audit(
        data_dir,
        "backup_created",
        {
            "files": report.files,
            "records": report.records,
            "manifest_sha256": manifest_sha,
            "schema_versions": report.schema_versions,
        },
    )
    return report


def _read_bundle(path: Path) -> tuple[dict, dict, bytes]:
    raw = path.read_bytes()
    if raw[:8] != MAGIC:
        raise ValueError(f"{path} is not a Veto backup file (bad magic).")
    off = 8
    hlen = int.from_bytes(raw[off : off + 4], "big")
    off += 4
    header = json.loads(raw[off : off + hlen])
    off += hlen
    mlen = int.from_bytes(raw[off : off + 4], "big")
    off += 4
    manifest = json.loads(raw[off : off + mlen])
    off += mlen
    return header, manifest, raw[off:]


@dataclass
class IntegrityReport:
    ok: bool
    files_checked: int
    files_ok: int
    checksum_match_pct: float
    mismatches: list[str] = field(default_factory=list)


def verify_backup(path: str | Path, passphrase: str) -> IntegrityReport:
    """Decrypt the bundle and recompute every checksum in the manifest."""
    path = Path(path)
    header, manifest, token = _read_bundle(path)
    Fernet, _, _ = _crypto()
    salt = base64.b64decode(header["salt_b64"])
    try:
        payload = Fernet(_derive_key(passphrase, salt)).decrypt(token)
    except Exception as exc:
        raise ValueError("Decryption failed: wrong passphrase or corrupt file.") from exc

    tar_buf = io.BytesIO(payload)
    on_disk: dict[str, bytes] = {}
    with tarfile.open(fileobj=tar_buf, mode="r") as tar:
        for member in tar.getmembers():
            if member.isfile():
                fh = tar.extractfile(member)
                if fh:
                    on_disk[member.name] = fh.read()

    mismatches: list[str] = []
    ok_count = 0
    for rel, meta in manifest["files"].items():
        blob = on_disk.get(rel)
        if blob is None:
            mismatches.append(f"{rel}: missing from bundle")
            continue
        if hashlib.sha256(blob).hexdigest() != meta["sha256"]:
            mismatches.append(f"{rel}: checksum mismatch")
        else:
            ok_count += 1

    total = len(manifest["files"])
    pct = (ok_count / total * 100.0) if total else 100.0
    return IntegrityReport(
        ok=not mismatches,
        files_checked=total,
        files_ok=ok_count,
        checksum_match_pct=pct,
        mismatches=mismatches,
    )


# ---------------------------------------------------------------------------
# Restore
# ---------------------------------------------------------------------------


@dataclass
class RestoreReport:
    data_dir: str
    files_restored: int
    records_restored: int
    selective: list[str]
    verify: IntegrityReport


def restore(
    path: str | Path,
    passphrase: str,
    data_dir: str | Path,
    selective: list[str] | None = None,
) -> RestoreReport:
    """Restore from an encrypted backup. ``selective`` limits restore to the
    named stable schemas (e.g. ``["outcome-event"]``); unknown names raise."""
    path = Path(path)
    data_dir = Path(data_dir)
    if selective:
        for name in selective:
            schemas.get_schema(name)  # raises KeyError on unknown names

    header, manifest, token = _read_bundle(path)
    Fernet, _, _ = _crypto()
    salt = base64.b64decode(header["salt_b64"])
    try:
        payload = Fernet(_derive_key(passphrase, salt)).decrypt(token)
    except Exception as exc:
        raise ValueError("Decryption failed: wrong passphrase or corrupt file.") from exc

    wanted = set(selective) if selective else None
    data_dir.mkdir(parents=True, exist_ok=True)
    restored = 0
    records = 0
    tar_buf = io.BytesIO(payload)
    with tarfile.open(fileobj=tar_buf, mode="r") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            meta = manifest["files"].get(member.name)
            if meta is None:
                continue
            if wanted is not None and meta["schema"] not in wanted:
                continue
            dest = data_dir / member.name
            # Path-traversal guard: stay inside the data dir.
            if not str(dest.resolve()).startswith(str(data_dir.resolve())):
                raise ValueError(f"Refusing to restore outside data dir: {member.name}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            fh = tar.extractfile(member)
            if fh:
                blob = fh.read()
                if hashlib.sha256(blob).hexdigest() != meta["sha256"]:
                    raise ValueError(f"Checksum mismatch on restore: {member.name}")
                dest.write_bytes(blob)
                restored += 1
                records += meta["records"]

    integrity = verify_backup(path, passphrase)
    _audit(
        data_dir,
        "restore",
        {
            "files": restored,
            "records": records,
            "selective": sorted(wanted) if wanted else [],
            "checksum_match_pct": integrity.checksum_match_pct,
        },
    )
    return RestoreReport(
        data_dir=str(data_dir),
        files_restored=restored,
        records_restored=records,
        selective=sorted(wanted) if wanted else [],
        verify=integrity,
    )


# ---------------------------------------------------------------------------
# Disaster-recovery drill
# ---------------------------------------------------------------------------


def _record_ids(data_dir: Path) -> dict[str, set[str]]:
    """{schema_name: set of record ids} for gap analysis."""
    ids: dict[str, set[str]] = {}
    for name, schema in schemas.SCHEMA_REGISTRY.items():
        if not schema.record_key:
            continue
        found: set[str] = set()
        for rel in schema.files:
            path = data_dir / rel
            if not path.exists():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = rec.get(schema.record_key)
                if key:
                    found.add(str(key))
        ids[name] = found
    return ids


@dataclass
class DrillReport:
    ok: bool
    checksum_match_pct: float
    record_gap: dict[str, int]
    detail: str


def drill(data_dir: str | Path, passphrase: str) -> DrillReport:
    """Full disaster-recovery drill with zero risk to live data:

    1. Create an encrypted backup of the live data dir.
    2. Snapshot live record ids per stable schema.
    3. Restore into a scratch directory (live store untouched).
    4. Verify 100% checksum match on the backup.
    5. Compare restored record ids against the snapshot — any missing id
       is an unrecoverable record gap.
    """
    data_dir = Path(data_dir)
    before = _record_ids(data_dir)
    with tempfile.TemporaryDirectory(prefix="veto-drill-") as tmp:
        backup_path = Path(tmp) / "drill.vetobackup"
        create_backup(data_dir, backup_path, passphrase)
        integrity = verify_backup(backup_path, passphrase)
        if not integrity.ok:
            return DrillReport(False, integrity.checksum_match_pct, {}, "backup integrity failed")
        scratch = Path(tmp) / "restored"
        restore(backup_path, passphrase, scratch)
        after = _record_ids(scratch)

    gap: dict[str, int] = {}
    for name, ids in before.items():
        missing = ids - after.get(name, set())
        gap[name] = len(missing)
    ok = integrity.checksum_match_pct == 100.0 and all(v == 0 for v in gap.values())
    _audit(
        data_dir,
        "drill",
        {
            "ok": ok,
            "checksum_match_pct": integrity.checksum_match_pct,
            "record_gap": gap,
        },
    )
    detail = (
        "PASS: 100% checksum match, no unrecoverable record gap"
        if ok
        else f"FAIL: checksum {integrity.checksum_match_pct}%, gap {gap}"
    )
    return DrillReport(ok, integrity.checksum_match_pct, gap, detail)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="veto-backup", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("create", help="Create an encrypted backup")
    p.add_argument("--data-dir", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--passphrase", required=True)

    p = sub.add_parser("verify", help="Verify backup integrity")
    p.add_argument("--in", dest="inp", required=True)
    p.add_argument("--passphrase", required=True)

    p = sub.add_parser("restore", help="Restore from a backup")
    p.add_argument("--in", dest="inp", required=True)
    p.add_argument("--passphrase", required=True)
    p.add_argument("--data-dir", required=True)
    p.add_argument("--selective", default="", help="Comma-separated schema names")

    p = sub.add_parser("drill", help="Run a disaster-recovery drill")
    p.add_argument("--data-dir", required=True)
    p.add_argument("--passphrase", required=True)

    args = parser.parse_args(argv)
    if args.command == "create":
        r = create_backup(args.data_dir, args.out, args.passphrase)
        print(json.dumps(r.__dict__, indent=2))
    elif args.command == "verify":
        r = verify_backup(args.inp, args.passphrase)
        print(json.dumps(r.__dict__, indent=2))
        return 0 if r.ok else 1
    elif args.command == "restore":
        sel = [s.strip() for s in args.selective.split(",") if s.strip()] or None
        r = restore(args.inp, args.passphrase, args.data_dir, sel)
        print(
            json.dumps(
                {**r.__dict__, "verify": r.verify.__dict__}, indent=2, default=str
            )
        )
    elif args.command == "drill":
        r = drill(args.data_dir, args.passphrase)
        print(json.dumps(r.__dict__, indent=2))
        return 0 if r.ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
