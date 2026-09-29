#!/usr/bin/env bash
#
# veto-backup.sh — encrypted backup / verify / restore / drill.
#
# Usage:
#   bash scripts/veto-backup.sh create  <data-dir> <out.vetobackup>
#   bash scripts/veto-backup.sh verify  <backup.vetobackup>
#   bash scripts/veto-backup.sh restore <backup.vetobackup> <data-dir> [schema,...]
#   bash scripts/veto-backup.sh drill   <data-dir>
#
# Passphrase handoff (Rule 1 — i10-wide): the passphrase is read from
# $VETO_BACKUP_PASSPHRASE or prompted interactively, then handed to
# backup.py through the ENVIRONMENT — never on argv. That keeps it out of
# shell history, `ps` output, and process accounting. backup.py resolves
# the passphrase from $VETO_BACKUP_PASSPHRASE (no --passphrase argv flag).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Make `python3 -m initiatives.i10.backup` importable no matter which
# directory this script is invoked from (relative data-dir arguments still
# resolve against the caller's cwd).
export PYTHONPATH="$REPO_DIR${PYTHONPATH:+:$PYTHONPATH}"

CMD="${1:?usage: veto-backup.sh create|verify|restore|drill ...}"

if [ -z "${VETO_BACKUP_PASSPHRASE:-}" ]; then
  read -rsp "Backup passphrase: " VETO_BACKUP_PASSPHRASE; echo
fi
export VETO_BACKUP_PASSPHRASE
# Don't let the passphrase linger in this shell any longer than needed.
trap 'unset VETO_BACKUP_PASSPHRASE' EXIT

case "$CMD" in
  create)
    DATA_DIR="${2:?data dir required}"; OUT="${3:?output path required}"
    python3 -m initiatives.i10.backup create --data-dir "$DATA_DIR" --out "$OUT"
    ;;
  verify)
    IN="${2:?backup file required}"
    python3 -m initiatives.i10.backup verify --in "$IN"
    ;;
  restore)
    IN="${2:?backup file required}"; DATA_DIR="${3:?data dir required}"
    SELECTIVE="${4:-}"
    if [ -n "$SELECTIVE" ]; then
      python3 -m initiatives.i10.backup restore --in "$IN" --data-dir "$DATA_DIR" --selective "$SELECTIVE"
    else
      python3 -m initiatives.i10.backup restore --in "$IN" --data-dir "$DATA_DIR"
    fi
    ;;
  drill)
    DATA_DIR="${2:?data dir required}"
    python3 -m initiatives.i10.backup drill --data-dir "$DATA_DIR"
    ;;
  *)
    echo "unknown command: $CMD" >&2; exit 1 ;;
esac
