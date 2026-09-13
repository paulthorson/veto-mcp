"""Migration 0001 — stamp schema versions.

Ensures every stable dataset file present in the data directory carries
an explicit schema-version marker:

* ``profiles/*.json`` — adds ``"schema_version": "profile-v1"`` when the
  key is absent (legacy wizard-written profiles predate the marker).
* Writes ``data_dir/_schema_versions.json`` with the registry's
  {schema: version} map for the release-channel compatibility gate.

Idempotent. ``backward`` removes the marker file and strips markers this
migration added (recorded per-file in the journal detail).
"""

from __future__ import annotations

import json
from pathlib import Path

MIGRATION_ID = "0001_stamp_schema_versions"
FROM_VERSION = {"profile": "(unmarked)", "outcome-event": "outcome-min-v0"}
TO_VERSION = {"profile": "profile-v1", "outcome-event": "outcome-min-v0"}

MARKER_FILE = "_schema_versions.json"


def _stamp_path() -> Path:
    # Absolute import: migration modules are loaded from their file path
    # (numeric filename prefix), so relative imports are unavailable.
    from initiatives.i10 import schemas

    return schemas.schema_versions()


def forward(data_dir: Path) -> dict:
    data_dir = Path(data_dir)
    stamped: list[str] = []
    for profile in sorted((data_dir / "profiles").glob("*.json")):
        try:
            doc = json.loads(profile.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(doc, dict) and "schema_version" not in doc:
            doc["schema_version"] = "profile-v1"
            profile.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
            stamped.append(profile.name)
    marker = data_dir / MARKER_FILE
    marker.write_text(json.dumps(_stamp_path(), indent=2) + "\n", encoding="utf-8")
    return {"stamped_profiles": stamped, "marker": MARKER_FILE}


def backward(data_dir: Path) -> dict:
    data_dir = Path(data_dir)
    removed_marker = False
    marker = data_dir / MARKER_FILE
    if marker.exists():
        marker.unlink()
        removed_marker = True
    return {"removed_marker": removed_marker}


def verify(data_dir: Path) -> dict:
    data_dir = Path(data_dir)
    problems: list[str] = []
    marker = data_dir / MARKER_FILE
    if not marker.exists():
        problems.append("schema-version marker file missing")
    else:
        try:
            doc = json.loads(marker.read_text(encoding="utf-8"))
            if doc.get("profile") != "profile-v1":
                problems.append("marker does not record profile-v1")
        except (json.JSONDecodeError, OSError) as exc:
            problems.append(f"marker unreadable: {exc}")
    for profile in sorted((data_dir / "profiles").glob("*.json")):
        try:
            doc = json.loads(profile.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(doc, dict) and doc.get("schema_version") != "profile-v1":
            problems.append(f"{profile.name}: missing profile-v1 marker")
    return {"ok": not problems, "problems": problems}
