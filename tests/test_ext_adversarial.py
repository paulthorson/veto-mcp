#!/usr/bin/env python3
"""Adversarial tests (Initiative 11): bypass attempts must fail, and the
harness must be honest about it.

These tests ARE the proof-of-value evidence: a new extension can prove
what it accesses and CANNOT bypass the core confirmation or governance
gates. Each attack below is a real hostile extension run through the
real Host.

Honesty rules enforced here:

- ``TestAdversarialSuite``: every attack in ``ALL_ATTACKS`` must report
  ``blocked=True`` — genuinely attempted and genuinely refused. If any
  reports ``blocked=False``, the design is wrong — do not ship.
- ``TestCanaryNegativeControl``: the NEGATIVE CONTROL. The synthetic
  plumbing canary MUST report ``blocked=False`` — it proves the harness
  can actually detect failure instead of passing vacuously. If the
  canary ever holds, ``run_canary_suite`` raises instead of reporting
  green.
- Crash / harness-failure handling is inverted: a broken harness fails
  the suite loudly (``blocked=False`` + ``harness_error=True``), never
  as a pass.
- ``TestPowerFixturePolicy``: the policy suite also runs against a
  fixture that declares confirm-required actions, network destinations,
  and profile:read — every check must be exercised for real there
  (``applicable=True`` on all 10). ``TestReferenceExtensionPolicy``
  pins the reference fixture's honest shape: 4 genuinely passed, 6 not
  applicable, 0 failed — never "blocked" for checks that ran on nothing.
"""

import unittest
from unittest import mock

from initiatives.i11.policy_kit import attacks as attacks_mod
from initiatives.i11.policy_kit.attacks import (
    ALL_ATTACKS,
    CANARY_ATTACKS,
    AttackHarnessError,
    _canary_plumbing_control,
    attempt_ctx_host_traversal,
    run_adversarial_suite,
    run_canary_suite,
)
from initiatives.i11.policy_kit.checks import run_policy_suite
from initiatives.i11.sandbox.host import Host

REF_EXT = "initiatives/i11/reference/role-radar-digest"
POWER_EXT = "initiatives/i11/reference/apply-pilot"


class TestAdversarialSuite(unittest.TestCase):
    def test_all_attacks_blocked(self):
        report = run_adversarial_suite()
        self.assertEqual(report["breached"], [],
                         f"BREACHES: {report['results']}")
        self.assertEqual(report["harness_errors"], [],
                         f"HARNESS ERRORS: {report['results']}")
        self.assertEqual(report["verdict"], "HOLD")
        self.assertEqual(report["blocked"], len(ALL_ATTACKS))

    def test_each_attack_individually(self):
        for name, fn in ALL_ATTACKS:
            with self.subTest(attack=name):
                blocked, evidence = fn()
                self.assertTrue(blocked, f"attack {name!r} succeeded: {evidence}")

    def test_traversal_attack_attempts_real_vectors(self):
        """C1 regression: the traversal attack must genuinely attempt the
        reviewer's demonstrated vector classes — public-surface
        enumeration, private-attribute reachability, the traceback
        frame-locals walk, and the __globals__ registry walk — and say
        so in its evidence. A 'blocked' with no vector enumeration is
        the theater the review KICK_BACK'd."""
        blocked, evidence = attempt_ctx_host_traversal()
        self.assertTrue(blocked, f"traversal attack breached: {evidence}")
        for vector in ("[V1]", "[V2]", "[V3]", "[V4]"):
            self.assertIn(vector, evidence,
                          f"evidence does not enumerate vector {vector}: "
                          f"{evidence[:300]}")
        self.assertIn("__globals__", evidence)
        self.assertIn("traceback", evidence)

    def test_v1_public_surface_detects_live_broker_in_audit_view(self):
        """V1 regression (blind re-review KICK_BACK): the public-surface
        check must genuinely inspect enumerated values, not just their
        keys. Poison ExtensionAudit.entries_for so the public
        ctx.audit_view(limit=1) returns an entry containing a LIVE
        Broker instance (the reviewer's demonstration) — the traversal
        attack must then report blocked=False with [V1] breach
        evidence, instead of the old vacuous 'no host/broker/mint/
        token/registry reachable' pass."""
        from initiatives.i11.sandbox import audit as audit_mod
        from initiatives.i11.sandbox.broker import Broker

        def poisoned(self, ext_id, limit=200):
            return [{"event": "audit.poisoned",
                     "broker": Broker(binding=0, ext_id=ext_id)}]

        with mock.patch.object(audit_mod.ExtensionAudit, "entries_for",
                               poisoned):
            blocked, evidence = attempt_ctx_host_traversal()
        self.assertFalse(
            blocked,
            "V1 MISSED A LIVE BROKER in ctx.audit_view(): the "
            f"public-surface check is vacuous. Evidence: {evidence[:400]}")
        self.assertIn("[V1]", evidence)
        self.assertIn("Broker", evidence)

    def test_broken_host_fails_suite_loudly(self):
        """C2 regression: if Host.load_extension always raises (broken
        host), the suite must NOT report HOLD — every attack becomes a
        loud harness error."""
        with mock.patch.object(Host, "load_extension",
                               side_effect=RuntimeError("simulated host failure")):
            report = run_adversarial_suite()
        self.assertNotEqual(report["verdict"], "HOLD",
                            "suite reported HOLD with a broken host")
        self.assertEqual(report["blocked"], 0)
        self.assertEqual(len(report["harness_errors"]), len(ALL_ATTACKS))
        for result in report["results"]:
            with self.subTest(attack=result["attack"]):
                self.assertFalse(result["blocked"])
                self.assertTrue(result["harness_error"])

    def test_attack_crash_fails_loudly_not_as_blocked(self):
        """C2 regression: an attack function that itself crashes is
        recorded as a harness error (blocked=False), never as blocked."""
        def _boom():
            raise RuntimeError("simulated attack crash")

        original = attacks_mod.ALL_ATTACKS
        attacks_mod.ALL_ATTACKS = [("boom-attack", _boom)]
        try:
            report = run_adversarial_suite()
        finally:
            attacks_mod.ALL_ATTACKS = original
        self.assertNotEqual(report["verdict"], "HOLD")
        self.assertEqual(len(report["results"]), 1)
        result = report["results"][0]
        self.assertFalse(result["blocked"])
        self.assertTrue(result["harness_error"])
        self.assertIn("simulated attack crash", result["evidence"])


class TestCanaryNegativeControl(unittest.TestCase):
    """The canary proves the harness can say 'breach'.

    ``_canary_plumbing_control`` is a SYNTHETIC control: it reports
    ``blocked=False`` by construction. Its job is to prove the suite
    runner can report a non-HOLD verdict, so a green
    ``run_adversarial_suite()`` is evidence, not theater.

    History (why the canary is synthetic now): the previous canary,
    ``attempt_self_mint_introspection``, demonstrated a REAL end-to-end
    self-mint breach (``ctx._broker`` → ``ctx._broker._token`` →
    ``__globals__['_BROKER_HOSTS'][token]`` → ``confirmations.mint`` →
    confirm-required action executed, no human) until the sandbox rework
    closed the path. When the rework landed, the canary flipped to
    ``blocked=True`` — the designed signal — and its vector class moved
    into ``attempt_ctx_host_traversal`` (V3/V4), which probes the same
    vectors for real instead of probing a dead attribute path. Do NOT
    "fix" this control to return ``blocked=True``: a canary that cannot
    say "breach" is a dead control, and ``run_canary_suite`` raises
    loudly if it ever holds.
    """

    def test_canary_reports_breach_by_construction(self):
        blocked, evidence = _canary_plumbing_control()
        self.assertFalse(blocked,
                         "CANARY HELD: the negative control must report "
                         f"breach; the harness failure path is broken. {evidence}")
        self.assertIn("canary", evidence.lower())

    def test_canary_suite_reports_expected_breach(self):
        report = run_canary_suite()
        self.assertEqual(report["attacks"], len(CANARY_ATTACKS))
        self.assertEqual(report["breached"], ["canary-breach-plumbing"])
        self.assertEqual(report["verdict"],
                         "CANARY BREACH (expected — harness self-test)")
        # The canary never leaks into the HOLD verdict.
        suite = run_adversarial_suite()
        self.assertEqual(suite["verdict"], "HOLD")

    def test_held_canary_errors_instead_of_reporting_green(self):
        """If the canary ever holds, the suite must error, not report green."""
        original = attacks_mod.CANARY_ATTACKS
        attacks_mod.CANARY_ATTACKS = [("held-canary", lambda: (True, "held"))]
        try:
            with self.assertRaises(AttackHarnessError):
                run_canary_suite()
        finally:
            attacks_mod.CANARY_ATTACKS = original


class TestReferenceExtensionPolicy(unittest.TestCase):
    def test_reference_passes_full_policy_suite(self):
        report = run_policy_suite(REF_EXT)
        failures = [r for r in report["results"] if not r["passed"]]
        self.assertEqual(failures, [], f"policy failures: {failures}")
        self.assertEqual(report["failed"], 0)

    def test_reference_reports_honest_applicability(self):
        # The reference fixture declares no confirm-required actions, no
        # network destinations, and no profile:read: 4 checks genuinely
        # pass, 6 are not applicable — never "blocked" for a check that
        # ran on nothing.
        report = run_policy_suite(REF_EXT)
        self.assertEqual(report["applicable"], 4)
        self.assertEqual(report["passed"], 4)
        self.assertEqual(report["failed"], 0)
        self.assertEqual(report["not_applicable"], 6)
        for result in report["results"]:
            with self.subTest(check=result["id"]):
                if result["applicable"]:
                    self.assertTrue(result["passed"])
                else:
                    self.assertIn("not applicable",
                                  result["detail"].lower())
                    self.assertNotIn("vacuously",
                                     result["detail"].lower())

    def test_reference_cannot_send_or_submit(self):
        # The reference extension declares no confirm-required actions and
        # no network destinations: there is no code path to submission.
        from initiatives.i11.manifest.schema import load_manifest
        manifest = load_manifest(REF_EXT)
        kinds = {a["kind"] for a in manifest["permissions"]["actions"]}
        self.assertNotIn("confirm-required", kinds)
        self.assertEqual(manifest["permissions"]["network"]["destinations"], [])


class TestPowerFixturePolicy(unittest.TestCase):
    """The full policy suite against a NON-VACUOUS fixture.

    apply-pilot declares a confirm-required action, a network
    destination, and profile:read — every check must be exercised for
    real here. A 'vacuously holds' detail on this fixture is a test
    failure: it would mean the check never ran against a capable
    extension.
    """

    def test_power_fixture_passes_full_policy_suite(self):
        report = run_policy_suite(POWER_EXT)
        failures = [r for r in report["results"] if not r["passed"]]
        self.assertEqual(failures, [], f"policy failures: {failures}")
        self.assertEqual(report["failed"], 0)
        self.assertEqual(report["passed"], 10)

    def test_power_fixture_exercises_every_check_non_vacuously(self):
        report = run_policy_suite(POWER_EXT)
        not_applicable = [r for r in report["results"]
                          if not r["applicable"]]
        self.assertEqual(not_applicable, [],
                         f"checks not exercised on the power fixture: "
                         f"{not_applicable}")
        vacuous = [r for r in report["results"]
                   if "vacuously" in r["detail"].lower()]
        self.assertEqual(vacuous, [],
                         f"checks passed vacuously on the power fixture: {vacuous}")
        self.assertEqual(report["not_applicable"], 0)

    def test_power_fixture_declares_full_surface(self):
        from initiatives.i11.manifest.schema import load_manifest
        manifest = load_manifest(POWER_EXT)
        perms = manifest["permissions"]
        kinds = {a["kind"] for a in perms["actions"]}
        self.assertIn("confirm-required", kinds)
        self.assertTrue(perms["network"]["destinations"])
        self.assertIn("profile:read", perms["data"])


if __name__ == "__main__":
    unittest.main()
