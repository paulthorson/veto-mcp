#!/usr/bin/env bash
#
# veto-uninstall.sh — clean Veto uninstall.
#
# Usage:
#   bash scripts/veto-uninstall.sh              # keeps data
#   bash scripts/veto-uninstall.sh --purge-data # deletes data too
#
# --purge-data prints the EXACT absolute data directory and requires the
# typed confirmation "PURGE MY DATA <that exact path>". Nothing is deleted
# until the confirmation and the installer's safety checks pass
# (validate-first): a refused purge leaves the install 100% intact.
#
# Pre-purge backup: if VETO_BACKUP_PASSPHRASE is exported, the installer
# takes an encrypted backup of the data directory before deleting it
# (kept under ~/.local/share/veto/backups/). Otherwise NO BACKUP IS TAKEN
# — the deletion is permanent and unrecoverable. Export
# VETO_BACKUP_PASSPHRASE first if you want a safety copy.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_RECORD="$HOME/.local/share/veto/install.json"

if [ "${1:-}" = "--purge-data" ]; then
  if [ ! -f "$INSTALL_RECORD" ]; then
    echo "ERROR: no install record at $INSTALL_RECORD — cannot locate the data directory." >&2
    exit 1
  fi
  ABS_DATA_DIR="$(python3 -c 'import json,sys; from pathlib import Path; print(Path(json.load(open(sys.argv[1]))["data_dir"]).expanduser().resolve())' "$INSTALL_RECORD")"
  if [ -n "${VETO_BACKUP_PASSPHRASE:-}" ]; then
    BACKUP_NOTE="An encrypted pre-purge backup WILL be taken automatically (kept under ~/.local/share/veto/backups/)."
  else
    BACKUP_NOTE="NO BACKUP WILL BE TAKEN. This cannot be undone."
  fi
  cat <<EOF
WARNING: this will PERMANENTLY DELETE your Veto data directory:

    $ABS_DATA_DIR

$BACKUP_NOTE

To confirm, type exactly (the path is echoed so you can see what will be deleted):

    PURGE MY DATA $ABS_DATA_DIR
EOF
  read -rp "> " CONFIRM
  # Trim accidental trailing whitespace; the path itself is matched exactly.
  CONFIRM="$(printf '%s' "$CONFIRM" | sed 's/[[:space:]]*$//')"
  exec python3 "$REPO_DIR/initiatives/i10/installer.py" uninstall --purge-data --confirm "$CONFIRM" --no-backup-ack
else
  exec python3 "$REPO_DIR/initiatives/i10/installer.py" uninstall
fi
