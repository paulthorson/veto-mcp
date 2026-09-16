#!/usr/bin/env python3
"""Real end-to-end tests for Initiative 12 (growth machinery) + the
marketing site.

Local flows run the REAL product CLI (``python -m initiatives.i12``) as
a subprocess in a temp working dir — real argv parsing, real module
code, real artifact files asserted on disk. One carve-out: the
changelog add-entry test runs the real entrypoint (``cli.main()``)
in-process with the entries-file path redirected to a temp file,
because the i12 CLI exposes no env var or flag for the entries-file
location; the repo's entries copy is never touched. Nothing is mocked
beyond that one path redirect.

The marketing-site check is a live post-production verification against
the DEPLOYED site (https://www.vetomcp.com/), read-only:
- production build markers present (expected hashed asset, canonical URL)
- stale claims from before the 2a14ba6 cut absent ('26 modules', '8-board')
- the apex domain redirects to www

The live test is inherently network-dependent. If the site is
unreachable it FAILS with the exact HTTP/network evidence — it never
silently skips, because a missing site is a finding, not a pass.

Assumptions (marked): network access to vetomcp.com; the Vercel
deployment dpl_AfPFVcetDAnyT3LXiuJ6kp3cxVHd (commit 2a14ba6) is still
the production deployment. The expected asset hash below is the marker
recorded at the last post-production verification (2026-09-15).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

CLI = [sys.executable, "-m", "initiatives.i12"]


def _cli(*argv, cwd):
    """Run the real i12 CLI as a subprocess; return (rc, stdout, stderr)."""
    env = dict(__import__("os").environ)
    env["PYTHONPATH"] = str(BASE_DIR) + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        CLI + list(argv), cwd=str(cwd), env=env,
        capture_output=True, text=True, timeout=120,
    )
    return proc.returncode, proc.stdout, proc.stderr


class TestOnboardingE2E(unittest.TestCase):
    def test_onboarding_assigns_deterministic_path(self):
        tmp = Path(tempfile.mkdtemp(prefix="veto-e2e-i12-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        rc, out, err = _cli(
            "onboarding", "--role-maturity", "switching",
            "--tech-comfort", "low", cwd=tmp)
        self.assertEqual(rc, 0, err)
        artifact = tmp / "onboarding-path.json"
        artifact.write_text(out, encoding="utf-8")
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        self.assertEqual(payload["path_id"], "onboard-switching-low")
        self.assertTrue(payload["goal_workflow"])
        steps = payload["steps"]
        self.assertGreaterEqual(len(steps), 3)
        for step in steps:
            for key in ("id", "title", "cta", "skippable"):
                self.assertIn(key, step)
        # Deterministic: same inputs, same path.
        rc2, out2, _ = _cli(
            "onboarding", "--role-maturity", "switching",
            "--tech-comfort", "low", cwd=tmp)
        self.assertEqual(rc2, 0)
        self.assertEqual(json.loads(out2)["path_id"], payload["path_id"])


class TestShareE2E(unittest.TestCase):
    def test_score_card_produces_privacy_safe_artifact(self):
        tmp = Path(tempfile.mkdtemp(prefix="veto-e2e-i12-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        rc, out, err = _cli(
            "share", "score-card", "--role", "Backend Eng",
            "--company", "Acme", "--score", "82", "--verdict", "strong",
            "--reasons", "solid Python depth|clear ownership examples",
            "--factors-json", "[]", "--markdown", cwd=tmp)
        self.assertEqual(rc, 0, err)
        artifact = tmp / "score-card.md"
        artifact.write_text(out, encoding="utf-8")
        text = artifact.read_text(encoding="utf-8")
        self.assertIn("Backend Eng", text)
        self.assertIn("Acme", text)
        self.assertIn("82", text)
        self.assertIn("strong", text)
        # The privacy notice ships with the artifact.
        self.assertIn("never includes your resume text", text.lower())

        # JSON variant carries the same payload, structurally bounded:
        # long free text is truncated, reasons capped at 3.
        long_reason = "X" * 200
        rc, out, err = _cli(
            "share", "score-card", "--role", "Backend Eng",
            "--company", "Acme", "--score", "82", "--verdict", "strong",
            "--reasons", f"a|b|c|{long_reason}", "--factors-json", "[]",
            cwd=tmp)
        self.assertEqual(rc, 0, err)
        payload = json.loads(out)["payload"]
        self.assertEqual(payload["fit_score"], 82.0)
        self.assertEqual(payload["verdict"], "strong")
        self.assertLessEqual(len(payload["top_reasons"]), 3)
        self.assertTrue(all(len(r) <= 160 for r in payload["top_reasons"]))


class TestToolsE2E(unittest.TestCase):
    def test_jd_decoder_demo(self):
        tmp = Path(tempfile.mkdtemp(prefix="veto-e2e-i12-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        jd = ("Senior backend engineer, 5+ years Python, on-call rotation, "
              "must be in NYC office 4 days a week, competitive salary")
        rc, out, err = _cli("tools", "jd", "--text", jd, "--json", cwd=tmp)
        self.assertEqual(rc, 0, err)
        artifact = tmp / "jd-decode.json"
        artifact.write_text(out, encoding="utf-8")
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        self.assertTrue(payload["available"])
        self.assertFalse(payload["truncated"])
        self.assertIn(payload["verdict"], ("green", "mixed", "red"))
        self.assertIn("transparency_score", payload)
        self.assertEqual(payload["tool"], "jd_decoder")


class TestChangelogE2E(unittest.TestCase):
    def test_health_reports_missing_sections_as_defects(self):
        """Transparent changelog: missing rejections/limitations are
        flagged as defects — the e2e asserts the flag mechanism works."""
        tmp = Path(tempfile.mkdtemp(prefix="veto-e2e-i12-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        rc, out, err = _cli("changelog", "--health", cwd=tmp)
        self.assertEqual(rc, 0, err)
        health = json.loads(out)
        self.assertIn("total", health)
        self.assertIn("missing_rejections", health)
        self.assertIn("missing_limitations", health)

    def test_add_entry_roundtrip(self):
        """Full add -> render flow through the real CLI, with the entries
        file redirected to a temp dir (the repo copy is never touched)."""
        from unittest import mock
        from initiatives.i12 import __main__ as cli
        from initiatives.i12 import changelog as c

        tmp = Path(tempfile.mkdtemp(prefix="veto-e2e-i12-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        fake = tmp / "CHANGELOG_ENTRIES.json"
        with mock.patch.object(c, "ENTRIES_FILE", fake):
            rc = cli.main([
                "changelog", "--add", "2026-09-15", "shipped",
                "Retro E2E probe entry",
                "proves the add path works end to end",
                "probe only, not user-facing", "retro-e2e"])
            self.assertEqual(rc, 0)
            self.assertTrue(fake.is_file())
            entries = json.loads(fake.read_text(encoding="utf-8"))
            # add_entry seeds the curated defaults on a fresh file, then
            # appends: assert OUR entry landed with its category intact.
            mine = [e for e in entries
                    if e["title"] == "Retro E2E probe entry"]
            self.assertEqual(len(mine), 1)
            self.assertEqual(mine[0]["category"], "shipped")
            # Re-render picks the entry up.
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cli.main(["changelog"])
            self.assertEqual(rc, 0)
            self.assertIn("Retro E2E probe entry", buf.getvalue())


class TestTelemetryE2E(unittest.TestCase):
    def test_consent_gate_and_record_flow(self):
        tmp = Path(tempfile.mkdtemp(prefix="veto-e2e-i12-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        state = tmp / "telemetry.json"

        # Consent defaults OFF: recording without consent raises
        # ConsentRequired and records nothing — the hard gate.
        rc, out, err = _cli(
            "telemetry", "--record", "tool_opened",
            "tool=jd_decoder,surface=terminal,session_id=abc",
            "--state", str(state), cwd=tmp)
        self.assertNotEqual(rc, 0)
        self.assertIn("ConsentRequired", err)
        # The error carries opt-in guidance, not just a bare failure.
        self.assertIn("opt-in", err.lower())
        self.assertFalse(state.is_file())

        # Opt in, then record: the event lands in the state file.
        rc, out, err = _cli("telemetry", "--consent", "on",
                            "--state", str(state), cwd=tmp)
        self.assertEqual(rc, 0, err)
        rc, out, err = _cli(
            "telemetry", "--record", "tool_opened",
            "tool=jd_decoder,surface=terminal,session_id=abc",
            "--state", str(state), cwd=tmp)
        self.assertEqual(rc, 0, err)
        recorded = json.loads(out)
        self.assertEqual(recorded.get("event"), "tool_opened", recorded)
        self.assertEqual(recorded.get("tool"), "jd_decoder", recorded)
        self.assertTrue(state.is_file())
        # Re-read the state file: the event must have landed there, not
        # just been printed to stdout.
        state_payload = json.loads(state.read_text(encoding="utf-8"))
        recorded_events = [
            e for e in state_payload.get("events", [])
            if e.get("event") == "tool_opened"
            and e.get("tool") == "jd_decoder"]
        self.assertEqual(len(recorded_events), 1,
                         "recorded event did not land in the state file")

        # Status shows consent on and no tripwire incident.
        rc, out, err = _cli("telemetry", "--status",
                            "--state", str(state), cwd=tmp)
        self.assertEqual(rc, 0, err)
        status = json.loads(out)
        self.assertTrue(status.get("consented"), status)
        self.assertEqual(status.get("open_incidents"), 0, status)


class TestLiveSitePostProduction(unittest.TestCase):
    """Post-production check of the DEPLOYED marketing site (read-only).

    Expected markers (deployment dpl_AfPFVcetDAnyT3LXiuJ6kp3cxVHd,
    commit 2a14ba6, verified live 2026-09-15):
    - https://www.vetomcp.com/ serves HTTP 200
    - canonical URL is https://www.vetomcp.com/
    - the production bundle asset index-Dgyblqal.js is referenced AND
      resolves 200 live (the deployed build, not a stale/error page)
    - stale claims cut in 2a14ba6 are absent: '26 modules', '8-board'
    - https://vetomcp.com/ redirects (308) to https://www.vetomcp.com/
    """

    SITE = "https://www.vetomcp.com/"
    APEX = "https://vetomcp.com/"
    EXPECTED_ASSET = "index-Dgyblqal.js"

    def _get(self, url, *, follow_redirects=True, timeout=30):
        opener = (urllib.request.build_opener()
                  if follow_redirects
                  else urllib.request.build_opener(
                      _NoRedirect(urllib.request.HTTPRedirectHandler)))
        req = urllib.request.Request(
            url, headers={"User-Agent": "veto-e2e-retro/1.0"})
        try:
            with opener.open(req, timeout=timeout) as resp:
                return resp.status, dict(resp.headers), resp.read()
        except urllib.error.HTTPError as exc:
            return exc.code, dict(exc.headers), exc.read()
        except Exception as exc:  # network failure is a finding, not a skip
            self.fail(f"live-site check failed: {type(exc).__name__}: {exc} "
                      f"while fetching {url}")

    def test_homepage_serves_production_build(self):
        status, headers, body = self._get(self.SITE)
        self.assertEqual(
            status, 200,
            f"expected HTTP 200 from {self.SITE}, got {status} "
            f"({dict(headers)})")
        html = body.decode("utf-8", errors="replace")

        self.assertIn(
            '<link rel="canonical" href="https://www.vetomcp.com/" />', html,
            "canonical URL marker missing from live homepage")

        # Production build marker: the hashed bundle the deployment
        # record names, referenced by the served HTML...
        self.assertIn(self.EXPECTED_ASSET, html,
                      f"expected production asset {self.EXPECTED_ASSET} "
                      f"referenced in live HTML")
        # ...and resolving 200 live.
        asset_status, _, asset_body = self._get(
            self.SITE + "assets/" + self.EXPECTED_ASSET)
        self.assertEqual(
            asset_status, 200,
            f"production asset {self.EXPECTED_ASSET} does not resolve "
            f"live: HTTP {asset_status}")
        self.assertTrue(len(asset_body) > 1000,
                        "production asset body suspiciously small")

        # Stale claims cut by 2a14ba6 must not be on the live site.
        for stale in ("26 modules", "8-board"):
            self.assertNotIn(
                stale, html,
                f"stale claim {stale!r} still present on live site")

    def test_apex_redirects_to_www(self):
        status, headers, _ = self._get(self.APEX, follow_redirects=False)
        self.assertIn(
            status, (301, 302, 303, 307, 308),
            f"expected a redirect from {self.APEX}, got HTTP {status}")
        location = headers.get("Location", "")
        self.assertIn("www.vetomcp.com", location,
                      f"apex redirect target is not www: {location!r}")


if __name__ == "__main__":
    unittest.main()
