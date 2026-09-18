# Veto history identity rewrite PLAN (Gmail scrub)

**Status:** PLAN ONLY — DRAFT documentation.  
**HOLD:** Do **not** execute `git filter-repo`, force-push, or any history rewrite until
**Adv rematch** completes **and** an explicit **operator GO** is recorded.

This document is a technical plan. It does not change repository history.

---

## 1. Goal

Remove personal Gmail and local machine identities from git **author**, **committer**,
and `Co-authored-by` trailers so public history attributes work to GitHub noreply
identities only.

**Keep** tree content that is copyright/NOTICE text (e.g. `NOTICE`, `LICENSE`
copyright lines). This rewrite touches **commit metadata / message trailers only**,
not file contents, unless a future execute pass explicitly adds message-body
replacements for `Co-authored-by` lines (still not NOTICE/LICENSE file rewrites).

---

## 2. Measurement baseline (pre-execute)

Measured against `origin/main` tip at plan authoring:

| Field | Value |
|---|---|
| **main tip SHA** | `f6f6c4b97bc2ea0a76a6d19bf85a5893f50a06d3` |
| **tip author** | `Paul Thorson <655797+paulthorson@users.noreply.github.com>` |
| **Gmail author commits on main** | **20** (`paul.thorson@gmail.com`) |
| **Gmail committer commits on main** | **20** (same set) |
| **Local authors on main** | 1× `pugsley@local`, 1× `pugsleyjr@local` |
| **`Co-authored-by: …gmail…` (all refs)** | **6** (on Cursor agent branches; not on main tip lineage as author) |

Author email histogram on `main` (at tip above):

| Count | Email |
|---:|---|
| 131 | `paulthorson@users.noreply.github.com` |
| 20 | `paul.thorson@gmail.com` |
| 2 | `655797+paulthorson@users.noreply.github.com` |
| 2 | `noreply@agenticgovernance.app` |
| 1 | `pugsley@local` |
| 1 | `pugsleyjr@local` |

Re-measure before any execute (counts may drift):

```bash
git fetch origin main
git rev-parse origin/main
git log origin/main --format='%ae' | grep -c 'paul.thorson@gmail.com' || true
git log origin/main --format='%ce' | grep -c 'paul.thorson@gmail.com' || true
git log --all --format='%B' | grep -ci 'Co-authored-by:.*gmail.com' || true
```

Optional inventory helper (print-only): `scripts/history-identity-rewrite-dry-run.sh`.

---

## 3. Scope — refs to rewrite

### In scope (must rewrite or retire)

| Ref | Why |
|---|---|
| `main` | **20** commits with Gmail author/committer; plus 2 local `pugsley*` authors |
| `dependabot/pip/cryptography-gte-50.0.1` | Contains **17** Gmail commits via shared history (open PR #14) |
| `dependabot/pip/mcp-gte-2.2.0` | Contains **17** Gmail commits via shared history (open PR #13) |
| `cursor/fit-score-demo-polish-5a6f` | `Co-authored-by` Gmail trailers (open draft PR #9) |
| `cursor/setup-dev-environment-5a6f` | `Co-authored-by` Gmail trailers (open draft PR #8) |

### Out of scope for Gmail scrub (no Gmail author commits today)

| Ref | Notes |
|---|---|
| `proof/initiative-01-outcomes-lifecycle` | 0 Gmail authors; open PR #10 onto `main` — **will need rematch** after `main` force-push |
| `proof/initiative-02-adaptive-fit-engine` | 0 Gmail; stacked proof PR #11 |
| `proof/initiative-03-daily-operating-loop` | 0 Gmail; stacked proof PR #12 |
| Other open Dependabot Action/Docker bumps | 0 Gmail authors today; still **break** if based on pre-rewrite `main` SHAs — rematch or recreate after rewrite |

**Stale-branch policy at execute time:** either (a) include every remote branch that
still contains mapped emails / Gmail trailers in the same `filter-repo` run, or
(b) close/delete the branch + PR and recreate from post-rewrite `main`. Do not leave
half-rewritten remotes.

---

## 4. Exact email / identity map

**Canonical target (preferred):** GitHub ID-form noreply already used on recent tip commits:

```text
655797+paulthorson@users.noreply.github.com
```

GitHub user id `655797` / login `paulthorson` confirmed via API at plan time.

**Also valid (repo-established short form):** `paulthorson@users.noreply.github.com`
(131 commits on main). Do **not** mass-normalize short→ID in this scrub unless
operator explicitly expands scope — that would rewrite nearly all history.

### Author / committer email replacements

| From | To |
|---|---|
| `paul.thorson@gmail.com` | `655797+paulthorson@users.noreply.github.com` |
| `pugsley@local` | `655797+paulthorson@users.noreply.github.com` |
| `pugsleyjr@local` | `655797+paulthorson@users.noreply.github.com` |

**Display names:** leave as-is (`Paul Thorson`, `Pugsley Jr`, etc.) unless operator
requests a name map. Email scrub is the success criterion.

**Do not remap:**

- `paulthorson@users.noreply.github.com` (already clean)
- `655797+paulthorson@users.noreply.github.com` (already clean)
- `noreply@agenticgovernance.app` (non-Gmail; out of scope unless GO expands)
- Dependabot / `noreply@github.com` / `cursoragent@cursor.com`

### Message trailer replacements (`Co-authored-by`)

| From (substring / line) | To |
|---|---|
| `Co-authored-by: Paul Thorson <paul.thorson@gmail.com>` | `Co-authored-by: Paul Thorson <655797+paulthorson@users.noreply.github.com>` |

Case-sensitive exact line preferred; verify no other Gmail co-author spellings remain.

### KEEP (do not rewrite as “identity scrub”)

- `NOTICE` file contents (`Copyright 2026 Paul Thorson`, etc.)
- `LICENSE` Apache header / copyright notices in tree
- Any other in-tree copyright strings

---

## 5. Tool

Use **`git filter-repo`** (same family of tool as the 2026-09-14 UA history rewrites
recorded in `governance/LEDGER.md`).

Typical identity flags (execute pass — **not** run by this PR):

```bash
# EXAMPLE ONLY — DO NOT RUN until Adv rematch + operator GO
git filter-repo \
  --email-callback '
old = email
replacements = {
  b"paul.thorson@gmail.com": b"655797+paulthorson@users.noreply.github.com",
  b"pugsley@local": b"655797+paulthorson@users.noreply.github.com",
  b"pugsleyjr@local": b"655797+paulthorson@users.noreply.github.com",
}
return replacements.get(email, email)
' \
  --replace-message <(printf '%s\n' \
    'Co-authored-by: Paul Thorson <paul.thorson@gmail.com>==>Co-authored-by: Paul Thorson <655797+paulthorson@users.noreply.github.com>')
```

Operators may equivalently use `--mailmap` if a checked-in mailmap is preferred at
execute time. Prefer one mechanism; document the chosen command in the execute
ledger entry.

Install note (from prior rewrite ops): if `pip install` is blocked (PEP 668), use
the standalone `git-filter-repo` script.

---

## 6. Dry-run steps (safe — print / inventory only)

1. Fresh clone or clean worktree of `paulthorson/veto-mcp`.
2. `git fetch --all --prune`.
3. Record tip: `git rev-parse origin/main`.
4. Run `bash scripts/history-identity-rewrite-dry-run.sh` (or the verify commands in §7).
5. Confirm mapped emails / Gmail trailer hits match expectations.
6. **Stop.** Do not invoke `filter-repo` rewrite. Do not `git push --force`.

---

## 7. Verify commands (success = Gmail author count 0)

After a future execute + force-push (not this PR):

```bash
# Must be 0 on main
git log origin/main --format='%ae' | grep -c 'gmail.com' || true
git log origin/main --format='%ce' | grep -c 'gmail.com' || true

# Must be 0 across rewritten refs
git log --all --format='%ae' | grep -c 'gmail.com' || true
git log --all --format='%ce' | grep -c 'gmail.com' || true
git log --all --format='%ae' | grep -cE 'pugsley@local|pugsleyjr@local' || true
git log --all --format='%B' | grep -ci 'Co-authored-by:.*gmail.com' || true

# Spot-check target identity present
git log origin/main --format='%ae' | sort | uniq -c | sort -rn
```

**Pass criterion:** Gmail author count on `main` = **0**; Gmail committer = **0**;
no `Co-authored-by` Gmail trailers on retained refs; no `pugsley@local` /
`pugsleyjr@local` authors/committers on retained refs. `NOTICE` / `LICENSE`
unchanged from pre-rewrite tree for copyright text.

---

## 8. Rollback

1. Before execute: tag or note pre-rewrite tip  
   `PRE_IDENTITY_REWRITE=$(git rev-parse origin/main)` and keep a mirror bundle  
   `git bundle create veto-pre-identity-rewrite.bundle --all`.
2. If rewrite is wrong and force-push already happened: restore from bundle / local
   mirror and force-push the saved refs (operator-only; coordinate with open PRs).
3. If rewrite not yet pushed: discard the rewritten clone; keep the untouched remote.

---

## 9. Risks

| Risk | Impact |
|---|---|
| **Force-push `main`** | Rewrites public SHAs; all clones must reset |
| **Open PR breakage** | PRs #3–#14 (and any new) lose merge base; need rematch, recreate, or close |
| **Dependabot branches with shared Gmail history** | #13 / #14 currently embed 17 Gmail commits — rewrite or replace |
| **Cursor draft PRs** | #8 / #9 carry Gmail `Co-authored-by` trailers |
| **Proof stack** | #10–#12 have 0 Gmail authors today but still rematch after `main` moves |
| **CI / branch protections** | May block force-push; need admin bypass |
| **Signed commits** | Signatures invalidate if any were signed (verify before execute) |
| **Scope creep** | Normalizing 131 short-form noreply → ID-form is a larger rewrite — not required for Gmail scrub |

---

## 10. HOLD — explicit non-execute gate

**Do not run `git filter-repo` rewrite.**  
**Do not force-push.**  

Execute is blocked until **both**:

1. **Adv rematch** is complete, and  
2. An **operator GO** is explicitly given for this identity scrub.

This PR ships **docs + optional dry-run inventory script only**.

---

## 11. Suggested execute sequence (future; after GO)

1. Announce freeze on merges to `main`.
2. Bundle / mirror backup (§8).
3. Close or snapshot open PRs that will break.
4. Run `filter-repo` with the map in §4 on all in-scope refs (§3).
5. Force-push rewritten refs (`main` + retained branches).
6. Run verify commands (§7); confirm Gmail counts = 0.
7. Rematch / recreate open PRs (Adv rematch + Dependabot / proof / Cursor drafts).
8. Ledger entry under `governance/LEDGER.md` (method, map, pre/post SHAs).

---

## 12. Deliverables in this DRAFT PR

- [x] `docs/history-identity-rewrite-plan-2026-09-18.md` (this file)
- [x] `scripts/history-identity-rewrite-dry-run.sh` (print-only inventory)
- [ ] Execute rewrite — **HOLD**
- [ ] Force-push — **HOLD**
