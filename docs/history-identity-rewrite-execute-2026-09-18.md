# History identity rewrite — EXECUTE record (2026-09-18)

**Status:** REWRITE COMPLETE LOCALLY — **`main` force-push BLOCKED** by repository
ruleset **Basic** (`id=23635716`) rule `pull_request` on `~DEFAULT_BRANCH`.
Operator GO + Adv rematch PASS were in effect; `non_fast_forward` was already
absent from the live ruleset, but direct pushes to `main` are still rejected with
*Changes must be made through a pull request.*

**Cos action required:** temporarily disable Basic ruleset enforcement **or**
remove the `pull_request` rule (keep `non_fast_forward` / `required_signatures`
lifted). After force-push succeeds, **Cos must restore** the ruleset. This agent
cannot update rulesets (`current_user_can_bypass: never`; API 403).

---

## 1. Pre-execute baseline (re-measured before rewrite)

| Field | Value |
|---|---|
| **Pre-rewrite `main` tip** | `9d4c5f521e5ad1449330ca59e27a8c822d7fccb3` |
| **Plan merge** | #18 @ `9d4c5f5` |
| **Gmail author on main** | **20** (`655797+paulthorson@users.noreply.github.com`) |
| **Gmail committer on main** | **20** |
| **`655797+paulthorson@users.noreply.github.com` author** | 1 |
| **`655797+paulthorson@users.noreply.github.com` author** | 1 |
| **`Co-authored-by` Gmail (all refs)** | **6** |

Author histogram on pre-rewrite `main`:

| Count | Email |
|---:|---|
| 131 | `paulthorson@users.noreply.github.com` |
| 20 | `655797+paulthorson@users.noreply.github.com` |
| 3 | `655797+paulthorson@users.noreply.github.com` |
| 2 | `noreply@agenticgovernance.app` |
| 1 | `655797+paulthorson@users.noreply.github.com` |
| 1 | `655797+paulthorson@users.noreply.github.com` |

`NOTICE` / `LICENSE` sha256 (kept unchanged through rewrite):

- NOTICE `e36cb006999f2871842ae9a363635e6d54cc53595f9d322e83be809660ff286f`
- LICENSE `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4`

---

## 2. Backup (§8) — recoverable path (no secrets)

Cloud Agent artifact directory:

`/opt/cursor/artifacts/history-identity-rewrite-2026-09-18/`

| Artifact | Purpose |
|---|---|
| `veto-pre-identity-rewrite.bundle` | `git bundle --all` of pre-rewrite refs |
| `veto-mcp-pre-identity-rewrite.git` | Bare mirror of pre-rewrite remote |
| `veto-post-identity-rewrite.bundle` | Bundle of rewritten local history |
| `BASELINE.txt` / dry-run capture | Pre-measure numbers |
| `local-rewrite-verify.txt` | Local post-rewrite gmail=0 proof |

Rollback: restore from pre-rewrite bundle/mirror and force-push saved refs
(operator-only; coordinate open PRs).

---

## 3. Rewrite method

Tool: `git filter-repo` 2.47.0

Email map (author **and** committer; no extra remaps):

| From | To |
|---|---|
| `655797+paulthorson@users.noreply.github.com` | `655797+paulthorson@users.noreply.github.com` |
| `655797+paulthorson@users.noreply.github.com` | `655797+paulthorson@users.noreply.github.com` |
| `655797+paulthorson@users.noreply.github.com` | `655797+paulthorson@users.noreply.github.com` |

Message trailer:

`Co-authored-by: Paul Thorson <655797+paulthorson@users.noreply.github.com>`
→ `Co-authored-by: Paul Thorson <655797+paulthorson@users.noreply.github.com>`

**Not remapped:** short-form `paulthorson@users.noreply.github.com`, already-clean
ID-form noreply, `noreply@agenticgovernance.app`. Tree files (`NOTICE`/`LICENSE`)
untouched.

Scope: full-repo rewrite of all heads present at execute time (avoids half-rewritten
remotes), including plan §3:

- `main`
- `dependabot/pip/cryptography-gte-50.0.1` (#14)
- `dependabot/pip/mcp-gte-2.2.0` (#13)
- `cursor/fit-score-demo-polish-5a6f` (#9)
- `cursor/setup-dev-environment-5a6f` (#8)

---

## 4. Local verify (success criteria met in rewritten clone)

| Check | Result |
|---|---|
| Gmail author on `main` | **0** |
| Gmail committer on `main` | **0** |
| Gmail author/committer all rewritten refs | **0** |
| `655797+paulthorson@users.noreply.github.com` / `655797+paulthorson@users.noreply.github.com` | **0** |
| `Co-authored-by` Gmail | **0** |
| NOTICE/LICENSE sha256 | **unchanged** |

**Rewritten `main` tip including this EXECUTE record:** `31025d9ad51f5767b3bfe43f51c283382fee01ac`

(filter-repo tip before this docs commit: `d1c5597e192069f82eebbea397dfbd98561700e4`)

Post-rewrite author histogram on `main`:

| Count | Email |
|---:|---|
| 131 | `paulthorson@users.noreply.github.com` |
| 25 | `655797+paulthorson@users.noreply.github.com` |
| 2 | `noreply@agenticgovernance.app` |

---

## 5. Force-push attempt / half-rewrite avoidance

1. Force-push of non-`main` rewritten refs **succeeded** briefly.
2. Force-push of `main` **rejected** (GH013 / `pull_request` ruleset).
3. To avoid a half-rewritten remote, those non-`main` refs were **restored** from
   the pre-rewrite mirror to their prior tips. Remote `main` remains `9d4c5f521e5ad1449330ca59e27a8c822d7fccb3`.
   Rewritten history is retained locally + in post-rewrite bundle + salvage branches.

| §3 ref | Disposition at this record |
|---|---|
| `main` | Rewritten locally (`31025d9ad51f5767b3bfe43f51c283382fee01ac`); **not** on `origin/main` yet |
| `dependabot/pip/cryptography-gte-50.0.1` | Rewritten locally; remote restored (re-push with main) |
| `dependabot/pip/mcp-gte-2.2.0` | same |
| `cursor/fit-score-demo-polish-5a6f` | same |
| `cursor/setup-dev-environment-5a6f` | same |

**None closed** — policy (a) include in same `filter-repo` run; close not required
once Cos lifts the ruleset and force-push completes.

Salvage refs (do not replace `main`):

- `rewrite/identity-scrub-ready-2026-09-18` → `31025d9ad51f5767b3bfe43f51c283382fee01ac`
- `cursor/history-identity-execute-record-7f06` → `31025d9ad51f5767b3bfe43f51c283382fee01ac`

---

## 6. Resume checklist (after Cos lifts `pull_request` on main)

```bash
# from rewritten clone / post-rewrite bundle (tip 31025d9ad51f5767b3bfe43f51c283382fee01ac)
git push --force --all origin
git fetch origin main
git log origin/main --format='%ae' | grep -c 'gmail.com' || true   # expect 0
git log origin/main --format='%ce' | grep -c 'gmail.com' || true   # expect 0
git log --all --format='%B' | grep -ci 'Co-authored-by:.*gmail.com' || true  # expect 0
git rev-parse origin/main   # expect 31025d9ad51f5767b3bfe43f51c283382fee01ac
```

Then Cos restores ruleset; rematch open PRs as needed.

---

## 7. Proof commands (local rewritten clone, captured at execute)

```
gmail author main: 0
gmail committer main: 0
gmail author all: 0
gmail committer all: 0
local-identity all: 0
coauthored gmail: 0
main tip: 31025d9ad51f5767b3bfe43f51c283382fee01ac
```
