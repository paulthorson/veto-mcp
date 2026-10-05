#!/usr/bin/env python3
"""Automated UAT acceptance journey for Initiative 11 (governed extension platform).

User journey: "A contributor scaffolds an extension, installs it, and the
platform proves the extension cannot bypass confirmation or governance
gates."

PROCESS MODEL (what this journey actually models)
------------------------------------------------
Every ``extension`` CLI command runs in a REAL separate OS process. The
test process itself never calls ``cli.main()`` and no ``Host`` is ever
shared between commands: one CLI invocation = one terminal invocation =
one process.

Install persists across processes: ``extension install`` records the
install (id, version, package hash, source path) in the install store,
and a later process's ``request``/``run`` auto-loads that exact install
— after fail-closed checks (not revoked, source dir still present,
package hash unchanged). This is the product lifecycle under test:
install once in process A, then ``request`` in process B,
``pending``/``confirm`` in process C, ``run --token`` in process D, and
a token replay in a fresh process E is refused. The confirmation
broker's pending approvals and used-token nonces cross process
boundaries ONLY through the persisted state file
(``$VETO_EXTENSIONS_CONFIRMATIONS``).

HERMETICITY
-----------
Every state file (confirmations, audit log, host key, install store,
revocation list, registry) lives under the per-test temp dir, routed by
explicit ``VETO_EXTENSIONS_CONFIRMATIONS`` / ``VETO_EXTENSIONS_AUDIT`` /
``VETO_HOST_KEY_FILE`` / ``VETO_EXTENSIONS_INSTALLED`` /
``VETO_EXTENSIONS_REVOCATIONS`` env vars on every subprocess. The repo
tree and real user data are never touched.

COULD NOT BE AUTOMATED (documented gaps, not faked)
---------------------------------------------------
- The 15-minute pending/token TTL: honestly testing it through the CLI
  would mean waiting 15 minutes. Broker-level expiry IS unit-tested
  (``tests/test_ext_sandbox.py::test_expired_pending_cannot_mint``).
- A live governance veto: the veto screen genuinely runs on every
  confirmed action — its notes land on the ``action.confirmed`` audit
  entry, which this journey asserts — but no hermetic CLI flow forces a
  veto to fire, and this journey will not fake one. If the framework ever
  does veto the synthetic action, the journey asserts the
  ``action.vetoed`` audit path instead of the success path.
- The registry has no CLI surface, so the registry checks (provenance,
  key substitution, downgrade, revocation) drive the real ``Registry``
  class in-process against temp-dir stores. No mocks; there is simply no
  terminal command to model.

There are no per-story acceptance criteria in the repo, so every
assertion traces to the roadmap epic text, the Proof of value, the Q3
exit gate, or the i11 README hard rules (see EPIC_MAP).
"""

from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path

from tests.uat.harness import JourneyCase

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from initiatives.i11.registry.registry import Registry  # noqa: E402
from initiatives.i11.signing.sign import (  # noqa: E402
    InstallStore,
    RevocationList,
    generate_keypair,
    sign_package,
    sign_revocation,
    verify_package,
)


class TestExtensionPlatformJourney(JourneyCase):
    """One test method per i11 epic (E1..E6)."""

    EPIC_MAP = {
        "test_plugin_manifest": (
            "E1", "Plugin manifest",
            "Roadmap i11 E1 epic text; i11 README hard rule 4"),
        "test_capability_sandbox": (
            "E2", "Capability sandbox",
            "Roadmap i11 E2 epic text; i11 README hard rule 2; "
            "Q3 exit gate"),
        "test_policy_test_kit": (
            "E3", "Policy test kit",
            "i11 Proof of value; i11 README hard rule 3; Q3 exit gate"),
        "test_developer_scaffold": (
            "E4", "Developer scaffold",
            "Roadmap i11 E4 epic text"),
        "test_signed_packages": (
            "E5", "Signed packages",
            "Roadmap i11 E5 epic text"),
        "test_curated_registry": (
            "E6", "Curated registry",
            "Roadmap i11 E6 epic text"),
    }

    # -- per-test hermetic world -----------------------------------------
    def setUp(self) -> None:
        super().setUp()
        # Every subprocess gets the same five state-file env vars, all
        # under the per-test temp dir. The host key file is created once
        # (0600) by the first process and reused, so every process in the
        # test shares one HMAC secret without the test ever handling it.
        self.env = {
            "VETO_EXTENSIONS_CONFIRMATIONS": str(
                self.workdir / "confirmations.json"),
            "VETO_EXTENSIONS_AUDIT": str(self.workdir / "audit.jsonl"),
            "VETO_HOST_KEY_FILE": str(self.workdir / "host.key"),
            "VETO_EXTENSIONS_INSTALLED": str(
                self.workdir / "installed.json"),
            "VETO_EXTENSIONS_REVOCATIONS": str(
                self.workdir / "revocations.json"),
        }
    # -- subprocess helpers ------------------------------------------------
    def ext_cli(self, *args: str) -> dict:
        """Run one real ``python cli.py extension ...`` subprocess.

        One CLI invocation = one terminal invocation = one process, with
        its own Host. Returns the parsed JSON payload.
        """
        proc = self.run_cli("extension", *args, env=self.env)
        self.assertEqual(
            proc.returncode, 0,
            f"extension {' '.join(args)} exited rc={proc.returncode}\n"
            f"--- stdout ---\n{proc.stdout}\n"
            f"--- stderr (tail) ---\n{proc.stderr[-3000:]}")
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            self.fail(f"extension {' '.join(args)} did not print JSON:\n"
                      f"{proc.stdout}\n--- stderr ---\n{proc.stderr[-2000:]}")

    def install_ext(self, ext_dir: Path) -> dict:
        """Install via one real CLI subprocess; the install persists.

        Later ``request``/``run`` commands in FRESH processes auto-load
        this install (fail-closed: revocation, source-dir, and hash
        re-checked at load). Returns the install payload, asserted ok.
        """
        installed = self.ext_cli("install", "--dir", str(ext_dir))
        self.assertTrue(installed["ok"], installed)
        return installed

    def run_action(self, ext_id: str, action_id: str, *,
                   token: str | None = None,
                   params: dict[str, str] | None = None) -> dict:
        """Run an action in a FRESH process (its own Host).

        The extension is auto-loaded from the persisted install record.
        The confirmation token travels on the command line — the
        documented human flow (``extension run --token``).
        """
        argv = ["run", "--ext-id", ext_id, "--action-id", action_id]
        for key, value in (params or {}).items():
            argv += ["--param", f"{key}={value}"]
        if token:
            argv += ["--token", token]
        return self.ext_cli(*argv)

    def scaffold(self, name: str, *,
                 kinds: str = "read,confirm-required",
                 scopes: str = "jobs:read") -> tuple[str, Path]:
        """Scaffold via the real CLI into the temp dir (own subprocess)."""
        out = self.ext_cli(
            "scaffold", "--name", name, "--description", "UAT fixture",
            "--author", "uat", "--out-dir", str(self.workdir / "scaffolded"),
            "--scopes", scopes, "--kinds", kinds)
        self.assertIn("ext_id", out, f"scaffold failed: {out}")
        return out["ext_id"], Path(out["dir"])

    def audit_entries(self) -> list[dict]:
        """Read the product-written audit log (no mocks; just the file)."""
        log = Path(self.env["VETO_EXTENSIONS_AUDIT"])
        if not log.is_file():
            return []
        return [json.loads(line)
                for line in log.read_text(encoding="utf-8").splitlines()
                if line.strip()]

    @staticmethod
    def implement_action(ext_dir: Path, ext_id: str, kind: str,
                         body: str) -> str:
        """Replace the scaffolded NotImplementedError stub with real code."""
        action_id = f"{ext_id}-{kind}"
        path = ext_dir / "extension.py"
        src = path.read_text(encoding="utf-8")
        stub = f"    raise NotImplementedError('implement {action_id}')"
        assert stub in src, f"scaffold stub for {action_id} not found"
        lines = [f"    {ln.strip()}" if ln.strip() else ln
                 for ln in body.strip().splitlines()]
        path.write_text(src.replace(stub, "\n".join(lines), 1),
                        encoding="utf-8")
        return action_id

    @staticmethod
    def add_probe_action(ext_dir: Path, ext_id: str, suffix: str,
                         body: str) -> str:
        """Declare an extra action in the manifest and define its function."""
        manifest_path = ext_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        action_id = f"{ext_id}-{suffix}"
        manifest["permissions"]["actions"].append({
            "id": action_id, "kind": "read", "confirm_required": False,
            "description": "UAT containment probe",
        })
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
        path = ext_dir / "extension.py"
        src = path.read_text(encoding="utf-8")
        fn_name = "_" + action_id.replace("-", "_")
        fn_src = (f"\ndef {fn_name}(ctx, **params):\n"
                  + "\n".join(f"    {ln.strip()}" if ln.strip() else ln
                              for ln in body.strip().splitlines()) + "\n")
        anchor = "ACTIONS = {"
        head, _, tail = src.partition(anchor)
        assert anchor in src
        path.write_text(
            head + fn_src + "\n" + anchor
            + f'\n    "{action_id}": {fn_name},' + tail,
            encoding="utf-8")
        return action_id

    # -- E1 ---------------------------------------------------------------
    def test_plugin_manifest(self):
        """A new extension must say up front everything it can touch — and a
        rule-breaking one is refused before it can install."""
        ext_id, ext_dir = self.scaffold("uat-manifest-demo")

        manifest = json.loads((ext_dir / "manifest.json").read_text())
        perms = manifest["permissions"]
        # The manifest is the declaration of powers: data scopes, network
        # destinations, actions, and which actions need human confirmation.
        self.assertEqual(manifest["id"], ext_id)
        self.assertIn("jobs:read", perms["data"])
        self.assertIsInstance(perms["network"]["destinations"], list)
        by_id = {a["id"]: a for a in perms["actions"]}
        self.assertIn(f"{ext_id}-read", by_id)
        self.assertIn(f"{ext_id}-confirm-required", by_id)
        self.assertFalse(by_id[f"{ext_id}-read"]["confirm_required"])
        self.assertTrue(
            by_id[f"{ext_id}-confirm-required"]["confirm_required"])
        self.assertIn("sandbox", perms)

        # A good manifest verifies cleanly (real CLI subprocess).
        verdict = self.ext_cli("verify", "--dir", str(ext_dir))
        self.assertTrue(verdict["ok"], verdict)
        self.assertEqual(verdict["manifest"]["id"], ext_id)

        # A manifest whose code imports a banned module is refused at the
        # verify-time import scan — before any of its code ever runs.
        bad = self.workdir / "bad-import"
        bad.mkdir()
        for name in ("manifest.json", "extension.py"):
            (bad / name).write_bytes((ext_dir / name).read_bytes())
        src = (bad / "extension.py").read_text(encoding="utf-8")
        (bad / "extension.py").write_text(
            "import socket  # banned: raw network primitive\n" + src,
            encoding="utf-8")
        bad_verdict = self.ext_cli("verify", "--dir", str(bad))
        self.assertFalse(bad_verdict["ok"])
        self.assertEqual(bad_verdict["stage"], "import-scan")

        # ... and the same hostile package is refused by `install` itself,
        # not only by `verify` (its own one-shot CLI process).
        bad_install = self.ext_cli("install", "--dir", str(bad))
        self.assertFalse(bad_install["ok"], bad_install)
        self.assertEqual(bad_install["stage"], "import-scan")

    # -- E2 ---------------------------------------------------------------
    def test_capability_sandbox(self):
        """An installed extension can only use the powers it declared —
        reaching beyond them is refused and recorded."""
        ext_id, ext_dir = self.scaffold("uat-sandbox-demo", kinds="read")
        # Declare one file area the extension may use, with content in it.
        manifest_path = ext_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["permissions"]["sandbox"]["fs_roots"] = ["data"]
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
        (ext_dir / ".data").mkdir()
        (ext_dir / ".data" / "notes.txt").write_text(
            "declared content", encoding="utf-8")
        self.implement_action(
            ext_dir, ext_id, "read",
            """note = ctx.fs.read_text("notes.txt")
               return {"note": note}""")
        probes = {
            "absolute path outside its area": self.add_probe_action(
                ext_dir, ext_id, "fs-abs",
                """ctx.fs.read_text("/etc/hostname")
                   return {"escaped": True}"""),
            "relative path escaping its area": self.add_probe_action(
                ext_dir, ext_id, "fs-dotdot",
                """ctx.fs.read_text("../manifest.json")
                   return {"escaped": True}"""),
            "network host it never declared": self.add_probe_action(
                ext_dir, ext_id, "net-escape",
                """ctx.http.get("https://unlisted.example/exfil")
                   return {"escaped": True}"""),
            "data scope it never declared": self.add_probe_action(
                ext_dir, ext_id, "scope-escape",
                """ctx.data("secrets:all")
                   return {"escaped": True}"""),
        }

        # Install once; every command below runs in its own fresh process
        # and auto-loads the persisted install.
        self.install_ext(ext_dir)

        # Declared powers work in a fresh process.
        ran = self.run_action(ext_id, f"{ext_id}-read")
        self.assertTrue(ran["ok"], ran)
        self.assertEqual(ran["result"]["note"], "declared content")

        # Everything beyond the declaration is refused — each probe in a
        # fresh process (its own Host).
        for label, probe in probes.items():
            run = self.run_action(ext_id, probe)
            self.assertFalse(run["ok"],
                             f"probe {label} ({probe}) was NOT refused")
            self.assertTrue(run.get("error"),
                            f"probe {label} gave no error text")

        # Refusals are written to the host's tamper-evident audit log.
        audit = self.ext_cli("audit-verify")
        self.assertTrue(audit["ok"], audit)
        self.assertGreater(audit["entries"], 0)
        events = {e["event"] for e in self.audit_entries()}
        self.assertTrue(events & {"action.denied", "action.error"},
                        f"no denial events in audit: {sorted(events)}")

    # -- E3 ---------------------------------------------------------------
    def test_policy_test_kit(self):
        """Attack-style extensions are all blocked, and a sensitive action
        cannot run without a real human approval — across real terminal
        processes."""
        ext_id, ext_dir = self.scaffold("uat-policy-demo")
        gated = f"{ext_id}-confirm-required"
        self.implement_action(ext_dir, ext_id, "read",
                              """return {"ran": True}""")
        self.implement_action(ext_dir, ext_id, "confirm-required",
                              """return {"approved": True}""")

        # The reusable policy test kit passes the clean extension.
        suite = self.ext_cli("policy-test", "--dir", str(ext_dir))
        self.assertEqual(suite["failed"], 0, suite)
        self.assertGreater(suite["passed"], 0)

        # The adversarial suite runs 14 hostile extensions through the real
        # host; every one must be blocked.
        adv = self.ext_cli("adversarial")
        self.assertEqual(adv["attacks"], 14, adv)
        self.assertEqual(adv["blocked"], adv["attacks"], adv)
        self.assertEqual(adv["breached"], [])
        self.assertEqual(adv["harness_errors"], [])

        # Install once; every command below is its own fresh process.
        self.install_ext(ext_dir)

        # A confirmation-required action cannot run with no token at all.
        run = self.run_action(ext_id, gated)
        self.assertFalse(run["ok"])
        self.assertIn("confirmation", run["error"].lower())

        # Process A: request approval in a fresh process. Requesting
        # creates a *pending request*, never a token — the extension
        # cannot mint its own approval.
        req = self.ext_cli("request", "--ext-id", ext_id,
                           "--action-id", gated)
        self.assertTrue(req["ok"], req)
        self.assertNotIn("confirmation_token", req,
                         "request must not hand out a token")
        pending_id = req["pending_id"]
        self.assertTrue(pending_id.startswith("pc_"), pending_id)

        # Process B (human terminal): `pending` SEES the pending id that
        # process A created — the cross-process read this journey exists
        # to prove. Structured assertion on the real id, not just ok:true.
        pending = self.ext_cli("pending")
        seen = [p["pending_id"] for p in pending["pending"]]
        self.assertIn(pending_id, seen,
                      f"pending id {pending_id} not visible cross-process: "
                      f"{seen}")

        # Process B (human terminal): only `confirm` mints the token.
        minted = self.ext_cli("confirm", "--pending-id", pending_id)
        self.assertTrue(minted["ok"], minted)
        token = minted["confirmation_token"]
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 32)

        # Process C: run with the token in a fresh process.
        run_out = self.run_action(ext_id, gated, token=token)
        if run_out["ok"]:
            self.assertTrue(run_out["result"]["approved"])
            # The governance veto screen ran on the confirmed action:
            # its notes are on the audit entry. (A live veto cannot be
            # triggered hermetically; the screen running is the honest
            # assertion. See the module docstring.)
            confirmed = [
                e for e in self.audit_entries()
                if e["event"] == "action.confirmed"
                and e["extension"] == ext_id
                and e["detail"].get("action") == gated
            ]
            self.assertTrue(confirmed,
                            "no action.confirmed audit entry for the run")
            notes = confirmed[-1]["detail"].get("governance_notes")
            self.assertIsInstance(notes, list,
                                  "governance screen did not record notes")
        else:
            # A live governance veto fired: assert the veto path honestly
            # instead of the success path. Not faked — the product refused.
            self.assertIn("governance veto", run_out["error"].lower())
            vetoed = [
                e for e in self.audit_entries()
                if e["event"] == "action.vetoed"
                and e["extension"] == ext_id
            ]
            self.assertTrue(vetoed, "no action.vetoed audit entry")

        # Process D (fresh agent session): the SAME token replays — and is
        # REFUSED. The used-token nonce crossed processes through the
        # persisted state file; single-use holds across terminals.
        replay_out = self.run_action(ext_id, gated, token=token)
        self.assertFalse(replay_out["ok"],
                         "replayed confirmation token was accepted")
        self.assertIn("replayed", replay_out["error"].lower())

        # A forged/self-made token is refused too.
        forged_out = self.run_action(ext_id, gated, token="self-minted-forgery")
        self.assertFalse(forged_out["ok"])

        # An action the manifest never declared is refused outright.
        undeclared_out = self.run_action(ext_id, "not-a-real-action")
        self.assertFalse(undeclared_out["ok"])
        self.assertIn("not declared", undeclared_out["error"])

        # Token parameter binding: minted for params A, run with params B
        # is refused — the token is bound to the exact payload.
        req2 = self.ext_cli("request", "--ext-id", ext_id,
                           "--action-id", gated,
                           "--param", "mode=fast")
        pid2 = req2["pending_id"]
        minted2 = self.ext_cli("confirm", "--pending-id", pid2)
        self.assertTrue(minted2["ok"], minted2)
        token2 = minted2["confirmation_token"]
        swapped_out = self.run_action(ext_id, gated, token=token2,
                                       params={"mode": "slow"})
        self.assertFalse(swapped_out["ok"],
                         "param-swapped token was accepted")
        self.assertIn("bound to a different payload",
                      swapped_out["error"])

        # Confirming a bogus pending id errors...
        bogus = self.ext_cli("confirm", "--pending-id", "pc_doesnotexist0")
        self.assertFalse(bogus["ok"])
        self.assertIn("unknown pending", bogus["error"])
        # ... and confirming an already-consumed id cannot mint twice.
        again = self.ext_cli("confirm", "--pending-id", pending_id)
        self.assertFalse(again["ok"])
        self.assertIn("unknown pending", again["error"])

    # -- E4 ---------------------------------------------------------------
    def test_developer_scaffold(self):
        """One command generates a complete, working extension project from
        the template."""
        ext_id, ext_dir = self.scaffold(
            "uat-scaffold-demo", kinds="read,confirm-required")

        # The template produces a full project: manifest, code, tests,
        # docs, integration snippets, web card, and retro entry.
        expected = [
            "manifest.json",
            "extension.py",
            f"tests/test_{ext_id.replace('-', '_')}.py",
            "docs/README.md",
            "RETRO.md",
            "cli_snippet.py",
            "mcp_snippet.py",
            "wizard_step.py",
            "web_card.html",
        ]
        for rel in expected:
            path = ext_dir / rel
            self.assertTrue(path.is_file(), f"scaffold missing {rel}")
            self.assertGreater(path.stat().st_size, 0,
                               f"scaffold generated empty {rel}")

        # The generated project is a working one: it verifies cleanly and
        # installs with the capabilities it declared (real CLI processes).
        verdict = self.ext_cli("verify", "--dir", str(ext_dir))
        self.assertTrue(verdict["ok"], verdict)
        installed = self.ext_cli("install", "--dir", str(ext_dir))
        self.assertTrue(installed["ok"], installed)
        self.assertEqual(installed["extension"], ext_id)
        declared = {a["id"] for a in installed["capabilities"]["actions"]}
        self.assertIn(f"{ext_id}-read", declared)
        self.assertIn(f"{ext_id}-confirm-required", declared)

        # `list` is process-local: a fresh process has no loaded
        # extensions. The install persists through the hermetic install
        # store, pinned to source directory, version, and package hash —
        # that is what `request`/`run` in fresh processes auto-load from.
        listed = self.ext_cli("list")
        self.assertEqual(listed["extensions"], [])
        rec = InstallStore(
            Path(self.env["VETO_EXTENSIONS_INSTALLED"])).get(ext_id)
        self.assertIsNotNone(rec, "install not recorded in the store")
        self.assertEqual(rec["version"], installed["version"])
        self.assertTrue(Path(rec["source_path"]).is_dir(),
                        "install record has no live source directory")
        self.assertTrue(rec.get("package_sha256"),
                        "install record has no package hash")

    # -- E5 ---------------------------------------------------------------
    def test_signed_packages(self):
        """Signed packages prove their origin — tampering or revocation
        stops them from installing."""
        priv, pub = generate_keypair()

        # Sign a clean package: the signature verifies against the key.
        _, good_dir = self.scaffold("uat-signing-demo", kinds="read")
        good_manifest = json.loads(
            (good_dir / "manifest.json").read_text(encoding="utf-8"))
        good_id = good_manifest["id"]
        self.implement_action(good_dir, good_id, "read",
                              """return {"ran": True}""")
        sign_package(good_dir, publisher="uat-test", private_key=priv)
        sig = verify_package(good_dir, public_key=pub)
        self.assertTrue(sig["ok"], sig)
        self.assertTrue(sig["pinned"])

        # Tampering with any file after signing invalidates the signature.
        with (good_dir / "extension.py").open("a", encoding="utf-8") as fh:
            fh.write("\n# tampered after signing\n")
        tampered = verify_package(good_dir, public_key=pub)
        self.assertFalse(tampered["ok"])

        # Revoking a version blocks its install — even though it verifies.
        # Revocations live in the hermetic temp-dir file routed by
        # VETO_EXTENSIONS_REVOCATIONS; the repo tree is never touched.
        _, rev_dir = self.scaffold("uat-revoked-demo", kinds="read")
        rev_manifest = json.loads(
            (rev_dir / "manifest.json").read_text(encoding="utf-8"))
        rev_id, rev_version = rev_manifest["id"], rev_manifest["version"]
        self.implement_action(rev_dir, rev_id, "read",
                              """return {"ran": True}""")
        sign_package(rev_dir, publisher="uat-test", private_key=priv)
        self.assertTrue(
            verify_package(rev_dir, public_key=pub)["ok"])
        rev_list = RevocationList(
            Path(self.env["VETO_EXTENSIONS_REVOCATIONS"]))
        rev_sig = sign_revocation(priv, rev_id, rev_version,
                                  "UAT revocation")
        revoked = rev_list.revoke(rev_id, rev_version, "UAT revocation",
                                  publisher_pubkey=pub,
                                  signature=rev_sig)
        self.assertTrue(revoked["ok"], revoked)
        refused = self.ext_cli("install", "--dir", str(rev_dir))
        self.assertFalse(refused["ok"])
        self.assertIn("revoked", refused["error"].lower())
        self.assertEqual(self.ext_cli("list")["extensions"], [])

    # -- E6 ---------------------------------------------------------------
    def test_curated_registry(self):
        """The registry only lists extensions that pass every gate —
        failing or revoked ones are refused. (The registry has no
        command-line interface, so this test drives the real registry
        code with temporary test folders.)"""
        priv, pub = generate_keypair()
        registry = Registry(self.workdir / "registry.json",
                            revocations=RevocationList(
                                self.workdir / "revocations.json"))

        def submit_clean(name: str, *,
                         key_priv=priv, key_pub=pub):
            ext_id, ext_dir = self.scaffold(name, kinds="read")
            manifest = json.loads(
                (ext_dir / "manifest.json").read_text(encoding="utf-8"))
            ext_id = manifest["id"]
            self.implement_action(ext_dir, ext_id, "read",
                                  """return {"ran": True}""")
            sign_package(ext_dir, publisher="uat-test",
                         private_key=key_priv)
            result = registry.submit(ext_dir, publisher="uat-test",
                                     publisher_pubkey=key_pub)
            self.assertTrue(result["ok"], result)
            return ext_id, ext_dir, manifest["version"]

        def entry_for(ext_id: str) -> dict:
            matches = [e for e in registry.list()
                       if e["ext_id"] == ext_id]
            self.assertEqual(len(matches), 1,
                             f"expected one registry entry for {ext_id}")
            return matches[0]

        # A clean, signed extension passes the automated gates
        # (compatibility, security) but waits on human review — so it is
        # not publishable yet.
        ext_id, ext_dir, version = submit_clean("uat-registry-demo")
        entry = entry_for(ext_id)
        self.assertEqual(entry["gates"]["compatibility"], "pass")
        self.assertEqual(entry["gates"]["security"], "pass")
        self.assertEqual(entry["gates"]["ux"], "pending")
        self.assertEqual(entry["gates"]["governance"], "pending")
        self.assertFalse(entry["publishable"])

        # Human reviewers pass the remaining gates: now it is publishable
        # and installable.
        for gate in ("ux", "governance"):
            recorded = registry.record_gate(
                ext_id, gate, verdict="pass", reviewer="uat-human",
                notes="UAT acceptance")
            self.assertTrue(recorded["ok"], recorded)
        self.assertTrue(entry_for(ext_id)["publishable"])
        installable = registry.installable(ext_id)
        self.assertTrue(installable["ok"], installable)

        # If the package bytes change after registration, install is
        # refused even though the gates passed.
        with (ext_dir / "extension.py").open("a", encoding="utf-8") as fh:
            fh.write("\n# changed after registration\n")
        changed = registry.installable(ext_id)
        self.assertFalse(changed["ok"])
        self.assertIn("changed after registration", changed["error"])

        # An extension that fails the security gate (banned import) can
        # never become publishable.
        bad_id, bad_dir, _ = submit_clean("uat-registry-bad")
        src = (bad_dir / "extension.py").read_text(encoding="utf-8")
        (bad_dir / "extension.py").write_text(
            "import socket  # banned\n" + src, encoding="utf-8")
        bad_submit = registry.submit(bad_dir, publisher="uat-test",
                                     publisher_pubkey=pub)
        self.assertTrue(bad_submit["ok"], bad_submit)
        bad_entry = entry_for(bad_id)
        self.assertEqual(bad_entry["gates"]["security"], "fail")
        self.assertFalse(bad_entry["publishable"])
        self.assertFalse(registry.installable(bad_id)["ok"])

        # Key substitution: the same ext_id resubmitted under a different
        # publisher key is rejected — the pin, once set, is the
        # publisher's identity.
        key_id, key_dir, _ = submit_clean("uat-registry-keysub")
        priv2, pub2 = generate_keypair()
        sign_package(key_dir, publisher="uat-test", private_key=priv2)
        sub = registry.submit(key_dir, publisher="uat-test",
                              publisher_pubkey=pub2)
        self.assertFalse(sub["ok"])
        self.assertIn("key substitution", sub["error"])

        # Downgrade: a newer version registers; resubmitting the older
        # version is rejected outright. Versions are derived from the
        # scaffolded manifest's real version so the upgrade is genuinely
        # newer than the base (a hardcoded literal silently becomes a
        # downgrade once the scaffold's default version is bumped).
        down_id, down_dir, down_base = submit_clean("uat-registry-downgrade")
        v1_copy = self.workdir / "downgrade-v1"
        shutil.copytree(down_dir, v1_copy)
        manifest = json.loads(
            (down_dir / "manifest.json").read_text(encoding="utf-8"))
        _base_parts = [int(p) if p.isdigit() else 0
                       for p in str(down_base).split(".")]
        while len(_base_parts) < 3:
            _base_parts.append(0)
        _base_parts[1] += 1
        down_newer = ".".join(str(p) for p in _base_parts)
        manifest["version"] = down_newer
        (down_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
        sign_package(down_dir, publisher="uat-test", private_key=priv)
        up = registry.submit(down_dir, publisher="uat-test",
                             publisher_pubkey=pub)
        self.assertTrue(up["ok"], up)
        self.assertEqual(up["entry"]["version"], down_newer)
        down = registry.submit(v1_copy, publisher="uat-test",
                               publisher_pubkey=pub)
        self.assertFalse(down["ok"])
        self.assertIn("downgrade", down["error"])

        # A revoked version is refused at submit and at install time.
        rev_id, rev_dir, rev_version = submit_clean("uat-registry-revoked")
        for gate in ("ux", "governance"):
            registry.record_gate(rev_id, gate, verdict="pass",
                                 reviewer="uat-human",
                                 notes="UAT acceptance")
        self.assertTrue(registry.installable(rev_id)["ok"])
        rev_sig = sign_revocation(priv, rev_id, rev_version,
                                  "UAT registry revocation")
        revoked = registry.revoke(rev_id, rev_version,
                                  "UAT registry revocation",
                                  signature=rev_sig)
        self.assertTrue(revoked["ok"], revoked)
        after_revoke = registry.installable(rev_id)
        self.assertFalse(after_revoke["ok"])
        self.assertIn("revoked", after_revoke["error"].lower())
        resubmit = registry.submit(rev_dir, publisher="uat-test",
                                   publisher_pubkey=pub)
        self.assertFalse(resubmit["ok"])
        self.assertIn("revoked", resubmit["error"].lower())


if __name__ == "__main__":
    unittest.main()
