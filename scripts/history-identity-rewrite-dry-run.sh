#!/usr/bin/env bash
#
# history-identity-rewrite-dry-run.sh — PRINT-ONLY inventory for the Gmail /
# local-author identity scrub planned in
# docs/history-identity-rewrite-plan-2026-09-18.md.
#
# This script NEVER runs git filter-repo, NEVER rewrites history, and NEVER
# force-pushes. It only lists what a future execute pass would change.
#
# Usage:
#   bash scripts/history-identity-rewrite-dry-run.sh
#   bash scripts/history-identity-rewrite-dry-run.sh origin/main
#
set -euo pipefail

REF="${1:-HEAD}"

TARGET_EMAIL='655797+paulthorson@users.noreply.github.com'

map_from=(
  'paul.thorson@gmail.com'
  'pugsley@local'
  'pugsleyjr@local'
)

echo "=== history-identity-rewrite DRY RUN (print only) ==="
echo "ref:            ${REF}"
echo "resolved:       $(git rev-parse "${REF}")"
echo "target email:   ${TARGET_EMAIL}"
echo "NOTICE/LICENSE: KEEP (this script does not touch tree files)"
echo
echo "HOLD: no filter-repo, no force-push, no rewrite from this script."
echo

echo "=== tip identity ==="
git log -1 --format='SHA  %H%nAuthor  %an <%ae>%nCommitter  %cn <%ce>%nSubject  %s' "${REF}"
echo

echo "=== author email histogram (${REF}) ==="
git log "${REF}" --format='%ae' | sort | uniq -c | sort -rn
echo

echo "=== committer email histogram (${REF}) ==="
git log "${REF}" --format='%ce' | sort | uniq -c | sort -rn
echo

echo "=== mapped author emails — commits that WOULD be remapped ==="
total_author=0
for email in "${map_from[@]}"; do
  count="$(git log "${REF}" --format='%H' --author="${email}" | wc -l | tr -d ' ')"
  total_author=$((total_author + count))
  echo "--- author ${email} -> ${TARGET_EMAIL}  (count=${count}) ---"
  if [[ "${count}" != "0" ]]; then
    git log "${REF}" --format='%h %ad %an <%ae> %s' --date=short --author="${email}"
  fi
  echo
done
echo "total author commits matching map on ${REF}: ${total_author}"
echo

echo "=== mapped committer emails — commits that WOULD be remapped ==="
total_committer=0
for email in "${map_from[@]}"; do
  count="$(git log "${REF}" --format='%H' --committer="${email}" | wc -l | tr -d ' ')"
  total_committer=$((total_committer + count))
  echo "--- committer ${email} -> ${TARGET_EMAIL}  (count=${count}) ---"
  if [[ "${count}" != "0" ]]; then
    git log "${REF}" --format='%h %ad %cn <%ce> %s' --date=short --committer="${email}"
  fi
  echo
done
echo "total committer commits matching map on ${REF}: ${total_committer}"
echo

echo "=== Gmail author count on ${REF} (success after execute = 0) ==="
gmail_author="$(git log "${REF}" --format='%ae' | grep -c 'gmail.com' || true)"
gmail_committer="$(git log "${REF}" --format='%ce' | grep -c 'gmail.com' || true)"
echo "gmail author lines:    ${gmail_author}"
echo "gmail committer lines: ${gmail_committer}"
echo

echo "=== Co-authored-by Gmail trailers (all refs; would rewrite message bodies) ==="
# Print commit SHA + matching trailer lines only.
git log --all --format='COMMIT %H%n%B' | awk '
  /^COMMIT / { sha=$2; next }
  tolower($0) ~ /co-authored-by:.*gmail\.com/ { print sha ": " $0 }
'
coauthor_count="$(git log --all --format='%B' | grep -ci 'Co-authored-by:.*gmail.com' || true)"
echo "trailer hit count: ${coauthor_count}"
echo "planned replacement:"
echo "  Co-authored-by: Paul Thorson <paul.thorson@gmail.com>"
echo "  => Co-authored-by: Paul Thorson <${TARGET_EMAIL}>"
echo

echo "=== remote refs with Gmail authors (incl. shared history) ==="
while read -r b; do
  [[ -z "${b}" ]] && continue
  n="$(git rev-list --count "${b}" --author='paul.thorson@gmail.com' 2>/dev/null || echo 0)"
  if [[ "${n}" != "0" ]]; then
    echo "${n}  ${b}"
  fi
done < <(git branch -r | sed 's/^[* ]*//' | grep -v 'HEAD')
echo

echo "=== DONE (dry run only; nothing rewritten) ==="
