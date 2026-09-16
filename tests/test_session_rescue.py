#!/usr/bin/env python3
"""Tests for Initiative 09 epic 5: session rescue.

All browser interaction is faked; no Playwright, no network. Asserts the
pause-and-hand-off behavior and — critically — that CAPTCHA is never
bypassed: this module contains no solve/click-through path, and every
detector outcome is a pause, never a bypass.

Test strategies (Rule 2):
* FakePage detector unit tests (the bulk of this file) trade away
  real-browser fidelity — no Playwright, no real DOM, canned page
  answers — to get fast, hermetic, deterministic detector-level
  assertions.
* Faked-playwright end-to-end tests (PreSubmitRescueTests,
  EasyApplyScreenshotListTests) trade away detector-level granularity —
  the page is a scripted fake whose query_selector/content answers are
  canned — to get coverage of the consumers' real call paths
  (browser_apply / easy_apply) and their pause-before-submit wiring.
"""

import inspect
import sys
import types
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from providers import session_rescue
from providers.session_rescue import (
    RescueHandoff,
    assess_field_ambiguity,
    check,
    detect_auth_loss,
    detect_captcha,
)


class FakePage:
    """Duck-typed stand-in for a Playwright page."""

    def __init__(self, url="https://example.com/apply", html="",
                 selectors=None):
        self.url = url
        self._html = html
        self._selectors = set(selectors or ())

    def query_selector(self, selector):
        return object() if selector in self._selectors else None

    def content(self):
        return self._html


class _DeadPage:
    """A closed/dead page: every page access raises.

    Guards the fail-closed invariant one layer below check(): if any
    detector swallowed page-access failures, this fake would slip
    through every detector and check() would return a silent None.
    """


    @property
    def url(self):
        raise RuntimeError("page is closed")

    def query_selector(self, selector):
        raise RuntimeError("page is closed")

    def content(self):
        raise RuntimeError("page is closed")


def _field(name, label="", ftype="text"):
    return {"name": name, "label": label, "type": ftype,
            "selector": f"input[name='{name}']"}


class CaptchaDetectionTests(unittest.TestCase):
    def test_recaptcha_iframe_detected(self):
        page = FakePage(selectors={'iframe[src*="recaptcha"]'})
        hit = detect_captcha(page)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["reason"], "captcha")

    def test_turnstile_detected(self):
        page = FakePage(selectors={".cf-turnstile"})
        self.assertIsNotNone(detect_captcha(page))

    def test_text_marker_detected(self):
        page = FakePage(html="<div>Please verify you are human</div>")
        hit = detect_captcha(page)
        self.assertIsNotNone(hit)
        self.assertIn("verify you are human", hit["evidence"])

    def test_clean_page_has_no_captcha(self):
        page = FakePage(html="<form><input name='q'></form>")
        self.assertIsNone(detect_captcha(page))


class CaptchaFamilyCoverageTests(unittest.TestCase):
    """Policy test: every known CAPTCHA family is covered by
    CAPTCHA_SELECTORS, as the comment on the data claims."""

    EXPECTED_FAMILIES = {
        "recaptcha", "hcaptcha", "turnstile", "arkose", "aws_waf",
        "datadome", "perimeterx", "geetest", "generic",
    }

    def test_family_names_are_the_known_set(self):
        self.assertEqual(set(session_rescue.CAPTCHA_FAMILIES), self.EXPECTED_FAMILIES)

    def test_every_family_contributes_selectors_to_the_flat_tuple(self):
        for family, selectors in session_rescue.CAPTCHA_FAMILIES.items():
            self.assertTrue(selectors, f"family {family!r} has no selectors")
            for s in selectors:
                self.assertIn(
                    s, session_rescue.CAPTCHA_SELECTORS,
                    f"{family!r} selector {s!r} missing from CAPTCHA_SELECTORS",
                )

    def test_no_orphan_selectors_outside_families(self):
        known = {
            s
            for selectors in session_rescue.CAPTCHA_FAMILIES.values()
            for s in selectors
        }
        for s in session_rescue.CAPTCHA_SELECTORS:
            self.assertIn(s, known, f"selector {s!r} belongs to no family")

    def test_each_selector_belongs_to_exactly_one_family(self):
        # The comment on CAPTCHA_FAMILIES claims EXACTLY ONE family per
        # selector; membership (>=1) is not enough to pin that down.
        owners: dict[str, list[str]] = {}
        for family, selectors in session_rescue.CAPTCHA_FAMILIES.items():
            for s in selectors:
                owners.setdefault(s, []).append(family)
        for s in session_rescue.CAPTCHA_SELECTORS:
            self.assertIn(s, owners)
            self.assertEqual(
                len(owners[s]), 1,
                f"selector {s!r} belongs to {len(owners[s])} families: {owners[s]}",
            )

    def test_each_family_detects(self):
        probes = {
            "recaptcha": 'iframe[src*="recaptcha"]',
            "hcaptcha": ".h-captcha",
            "turnstile": 'iframe[src*="challenges.cloudflare.com"]',
            "arkose": 'iframe[src*="arkoselabs.com"]',
            "aws_waf": 'iframe[src*="captcha-delivery.com"]',
            "datadome": 'iframe[src*="datadome"]',
            "perimeterx": "#px-captcha",
            "geetest": ".geetest_holder",
            "generic": 'iframe[src*="captcha"]',
        }
        self.assertEqual(set(probes), self.EXPECTED_FAMILIES)
        for family, selector in probes.items():
            with self.subTest(family=family):
                page = FakePage(selectors={selector})
                hit = detect_captcha(page)
                self.assertIsNotNone(hit, f"family {family!r} not detected")
                self.assertEqual(hit["reason"], "captcha")
                self.assertIn(selector, hit["evidence"])

    def test_arkose_funcaptcha_element_variant_detects(self):
        page = FakePage(selectors={"#FunCaptcha"})
        hit = detect_captcha(page)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["reason"], "captcha")


class AuthLossDetectionTests(unittest.TestCase):
    def test_login_redirect_detected(self):
        page = FakePage(url="https://www.linkedin.com/login?from=jobs")
        hit = detect_auth_loss(page, board="linkedin")
        self.assertIsNotNone(hit)
        self.assertEqual(hit["reason"], "auth_loss")

    def test_session_expired_text_detected(self):
        page = FakePage(html="<p>Your session has expired</p>")
        self.assertIsNotNone(detect_auth_loss(page))

    def test_clean_page_has_no_auth_loss(self):
        page = FakePage(url="https://boards.greenhouse.io/acme/jobs/1",
                        html="<form></form>")
        self.assertIsNone(detect_auth_loss(page))


class FieldAmbiguityTests(unittest.TestCase):
    def test_unlabeled_synthetic_field_triggers(self):
        fields = [_field("field_3")]  # synthesized name, no label
        hit = assess_field_ambiguity(fields)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["reason"], "field_ambiguity")

    def test_realistic_field_prefix_name_does_not_trigger(self):
        # 'field_of_study' is a real application field name, not a
        # synthesized field_N fallback — no numeric suffix, no trigger.
        fields = [_field("field_of_study", ftype="text")]
        self.assertIsNone(assess_field_ambiguity(fields))

    def test_synthetic_field_with_label_does_not_trigger(self):
        # A labeled field is never "unlabeled", even with a numeric name.
        fields = [_field("field_7", label="Phone", ftype="text")]
        self.assertIsNone(assess_field_ambiguity(fields))

    def test_duplicate_labels_trigger(self):
        fields = [_field("a", label="Name"), _field("b", label="Name")]
        hit = assess_field_ambiguity(fields)
        self.assertIsNotNone(hit)
        self.assertIn("duplicate", hit["evidence"])

    def test_duplicate_labels_trigger_for_email_and_password(self):
        # Duplicate-label detection covers all text-like input types,
        # including email and password fields.
        fields = [
            _field("email_1", label="Email", ftype="email"),
            _field("email_2", label="Email", ftype="email"),
        ]
        hit = assess_field_ambiguity(fields)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["reason"], "field_ambiguity")

        fields = [
            _field("pw1", label="Password", ftype="password"),
            _field("pw2", label="Password", ftype="password"),
        ]
        hit = assess_field_ambiguity(fields)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["reason"], "field_ambiguity")

    def test_clean_fields_pass(self):
        fields = [
            _field("first_name", label="First name"),
            _field("email", label="Email", ftype="email"),
        ]
        self.assertIsNone(assess_field_ambiguity(fields))

    def test_empty_fields_pass(self):
        self.assertIsNone(assess_field_ambiguity([]))

    def test_duplicate_labels_trigger_for_tel_textarea_select(self):
        # M3: duplicate-label detection covers tel, textarea, and select,
        # not just text/textbox/email/password.
        for ftype in ("tel", "textarea", "select"):
            with self.subTest(ftype=ftype):
                fields = [
                    _field("p1", label="Phone", ftype=ftype),
                    _field("p2", label="Phone", ftype=ftype),
                ]
                hit = assess_field_ambiguity(fields)
                self.assertIsNotNone(hit, f"duplicate {ftype} labels missed")
                self.assertEqual(hit["reason"], "field_ambiguity")
                self.assertIn("duplicate", hit["evidence"])

    def test_genuinely_anonymous_field_triggers(self):
        # M4: name="", no label/placeholder/aria-label — Veto would be
        # guessing what this field is.
        fields = [{
            "name": "", "label": "", "type": "text", "selector": "input#anon",
            "placeholder": "", "aria_label": "",
        }]
        hit = assess_field_ambiguity(fields)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["reason"], "field_ambiguity")
        self.assertIn("unlabeled", hit["evidence"])

    def test_field_identified_by_placeholder_only_does_not_trigger(self):
        fields = [{
            "name": "", "label": "", "type": "text", "selector": "input#e",
            "placeholder": "Email address",
        }]
        self.assertIsNone(assess_field_ambiguity(fields))

    def test_hidden_anonymous_field_does_not_trigger(self):
        # Hidden inputs are never user-filled; flagging them would
        # false-positive.
        fields = [{"name": "", "label": "", "type": "hidden"}]
        self.assertIsNone(assess_field_ambiguity(fields))


class CheckPriorityTests(unittest.TestCase):
    def test_captcha_beats_auth_loss(self):
        page = FakePage(
            url="https://example.com/login",
            selectors={".g-recaptcha"},
        )
        handoff = check(page, board="x")
        self.assertIsNotNone(handoff)
        self.assertEqual(handoff.reason, "captcha")

    def test_handoff_carries_guidance_and_token(self):
        page = FakePage(selectors={"#captcha"})
        handoff = check(page, board="greenhouse",
                        screenshot_path="/tmp/shot.png")
        self.assertIsInstance(handoff, RescueHandoff)
        self.assertTrue(handoff.resume_token)
        self.assertTrue(handoff.what_user_should_do)
        self.assertIn("never solve", handoff.what_user_should_do.lower())
        bundle = handoff.to_dict()
        self.assertEqual(bundle["reason"], "captcha")
        self.assertEqual(bundle["board"], "greenhouse")


class DetectorFailureTests(unittest.TestCase):
    """FAIL-CLOSED (B3): any detector or handoff-path exception must produce
    a loud RescueHandoff with reason "detector_failure" — never a silent
    None that downstream would read as "no CAPTCHA found"."""

    def test_detector_raise_produces_loud_handoff_not_none(self):
        # B3: a detector that raises must FAIL CLOSED — a RescueHandoff
        # with reason "detector_failure", never a silent None.
        page = FakePage()
        with mock.patch.object(
            session_rescue, "detect_captcha", side_effect=RuntimeError("detector boom")
        ):
            handoff = check(page, board="greenhouse")
        self.assertIsInstance(handoff, RescueHandoff)
        self.assertEqual(handoff.reason, "detector_failure")
        self.assertIn("verify manually", handoff.evidence.lower())
        self.assertTrue(handoff.what_user_should_do)
        self.assertTrue(handoff.detected_at)

    def test_auth_detector_raise_produces_loud_handoff(self):
        page = FakePage()
        with mock.patch.object(
            session_rescue, "detect_auth_loss", side_effect=RuntimeError("auth boom")
        ):
            handoff = check(page, board="x")
        self.assertIsInstance(handoff, RescueHandoff)
        self.assertEqual(handoff.reason, "detector_failure")

    def test_malformed_detector_hit_fails_closed_on_handoff_path(self):
        # M2: the detector "succeeded" but returned garbage — the handoff
        # path raises (KeyError) and must still pause loudly, never None.
        page = FakePage()
        with mock.patch.object(
            session_rescue, "detect_captcha", return_value={"bogus": 1}
        ):
            handoff = check(page, board="x")
        self.assertIsInstance(handoff, RescueHandoff)
        self.assertEqual(handoff.reason, "detector_failure")
        self.assertIn("verify manually", handoff.evidence.lower())

    def test_detector_failure_guidance_is_actionable(self):
        page = FakePage()
        with mock.patch.object(
            session_rescue, "detect_captcha", side_effect=RuntimeError("boom")
        ):
            handoff = check(page, board="x")
        guidance = handoff.what_user_should_do
        self.assertIn("python cli.py apply", guidance)
        self.assertIn("screenshots", guidance)
        self.assertIn("Nothing was submitted", guidance)

    def test_none_page_fails_closed_never_none(self):
        # B1-R3 (veto still open one layer down): check(None) used to
        # return a silent None — AttributeError was swallowed at every
        # page access. It must now be a loud detector_failure handoff.
        handoff = check(None, board="x")
        self.assertIsInstance(handoff, RescueHandoff)
        self.assertEqual(handoff.reason, "detector_failure")
        self.assertIn("verify manually", handoff.evidence.lower())

    def test_dead_page_fails_closed_never_none(self):
        # Every page access raises (closed/dead page). No detector may
        # swallow this into a clean bill of health.
        handoff = check(_DeadPage(), board="x")
        self.assertIsInstance(handoff, RescueHandoff)
        self.assertEqual(handoff.reason, "detector_failure")
        self.assertIn("verify manually", handoff.evidence.lower())

    def test_dead_page_direct_detectors_raise(self):
        # The detectors themselves must not swallow page-access
        # failures: they raise, and check() converts the raise into the
        # loud handoff (the layering above).
        with self.assertRaises(RuntimeError):
            detect_captcha(_DeadPage())
        with self.assertRaises(RuntimeError):
            detect_auth_loss(_DeadPage())


class DecisionRecordTests(unittest.TestCase):
    """D1 must pass the constitution's mechanical checks (B1): explicit
    ``scope_driven:`` (Rule 3) and ``product_goal:`` (Rule 4) fields, a
    correct rule citation, and the Trades away / To get sentences."""

    def test_d1_carries_scope_driven_and_product_goal(self):
        doc = session_rescue.__doc__ or ""
        self.assertIn("scope_driven:", doc)
        self.assertIn("product_goal:", doc)

    def test_d1_cites_rules_3_and_4_not_rule_2(self):
        doc = session_rescue.__doc__ or ""
        self.assertIn("Rule 3", doc)
        self.assertIn("Rule 4", doc)
        # Decision logs are not Rule 2 — Rule 2 is test strategies. "Rule 2"
        # may only appear inside the Rule-citation note paragraph, which
        # exists precisely to say Rule 2 does NOT apply to decision logs.
        lines = doc.splitlines()
        note_start = next(i for i, l in enumerate(lines)
                          if "Rule-citation note:" in l)
        for i, line in enumerate(lines):
            if "Rule 2" in line:
                self.assertGreaterEqual(
                    i, note_start,
                    f"'Rule 2' cited outside the Rule-citation note: "
                    f"{line.strip()[:80]}",
                )
        # Alternate phrasings of a Rule 2 citation must not appear either —
        # the note's own phrasing is "cited Rule 2, which was wrong".
        for phrase in ("(Rule 2)", "Rule 2:", "per Rule 2", "under Rule 2",
                       "citing Rule 2", "Rule-2"):
            self.assertNotIn(phrase, doc,
                             f"alternate Rule 2 citation phrasing: {phrase!r}")

    def test_d1_keeps_tradeoff_sentences(self):
        doc = session_rescue.__doc__ or ""
        self.assertIn("Trades away:", doc)
        self.assertIn("To get:", doc)


class CheckEndToEndTests(unittest.TestCase):
    """M1: end-to-end check() with ambiguous fields -> RescueHandoff."""

    def test_check_with_ambiguous_fields_returns_handoff(self):
        page = FakePage(url="https://boards.greenhouse.io/acme/jobs/1",
                        html="<form><input name='email'></form>")
        fields = [
            {"name": "field_2", "label": "", "type": "text", "selector": "#f2"},
            {"name": "field_9", "label": "", "type": "text", "selector": "#f9"},
        ]
        handoff = check(page, board="greenhouse", fields=fields)
        self.assertIsInstance(handoff, RescueHandoff)
        self.assertEqual(handoff.reason, "field_ambiguity")
        self.assertIn("unlabeled", handoff.evidence)
        self.assertEqual(len(handoff.fields_summary), 2)
        bundle = handoff.to_dict()
        self.assertEqual(bundle["reason"], "field_ambiguity")

    def test_check_clean_page_and_fields_returns_none(self):
        page = FakePage(url="https://boards.greenhouse.io/acme/jobs/1",
                        html="<form></form>")
        fields = [_field("email", label="Email", ftype="email")]
        self.assertIsNone(check(page, board="greenhouse", fields=fields))


class GuidanceActionabilityTests(unittest.TestCase):
    """M5: the handoff must be ACTIONABLE for non-technical users —
    what happened, where the screenshot was saved (concrete directory),
    the exact re-run command, and no bare code identifiers."""

    def _guidance(self, **kwargs):
        page = FakePage(selectors={"#captcha"})
        return check(page, board="greenhouse", **kwargs).what_user_should_do

    def test_guidance_states_what_happened(self):
        guidance = self._guidance().lower()
        self.assertIn("puzzle", guidance)  # plain words for CAPTCHA
        self.assertIn("nothing was submitted", guidance)

    def test_guidance_gives_concrete_screenshot_directory(self):
        guidance = self._guidance()  # no screenshot_path passed
        expected_dir = str(
            Path(session_rescue.__file__).resolve().parent.parent / "screenshots"
        )
        self.assertIn(expected_dir, guidance)

    def test_guidance_gives_exact_screenshot_file_when_known(self):
        guidance = self._guidance(screenshot_path="/tmp/shot.png")
        self.assertIn("/tmp/shot.png", guidance)

    def test_guidance_gives_exact_rerun_command(self):
        self.assertIn("python cli.py apply <job-id> --confirm", self._guidance())

    def test_guidance_has_no_bare_code_identifiers(self):
        guidance = self._guidance()
        for ident in ("browser_apply.", "RescueHandoff", "page.url", "login_session"):
            self.assertNotIn(ident, guidance,
                             f"bare code identifier leaked into user guidance: {ident}")


class I18nMarkerTests(unittest.TestCase):
    """M6: text markers cover German, French, Spanish, Portuguese
    (English-only scope is documented honestly in the module docstring)."""

    def test_german_captcha_marker_detected(self):
        page = FakePage(html="<p>Ich bin kein Roboter</p>")
        hit = detect_captcha(page)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["reason"], "captcha")

    def test_german_auth_loss_marker_detected(self):
        page = FakePage(
            html="<p>Ihre Sitzung ist abgelaufen. Bitte melden Sie sich an.</p>")
        hit = detect_auth_loss(page)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["reason"], "auth_loss")

    def test_french_captcha_marker_detected(self):
        page = FakePage(html="<p>Je ne suis pas un robot</p>")
        hit = detect_captcha(page)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["reason"], "captcha")

    def test_spanish_auth_loss_marker_detected(self):
        page = FakePage(html="<p>Inicia sesión para continuar.</p>")
        hit = detect_auth_loss(page)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["reason"], "auth_loss")

    def test_portuguese_captcha_marker_detected(self):
        page = FakePage(html="<p>Não sou um robô</p>")
        hit = detect_captcha(page)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["reason"], "captcha")


class FalsePositiveTests(unittest.TestCase):
    """M7: word-boundary text matching and tightened URL markers."""

    def test_login_help_url_does_not_match_login_marker(self):
        page = FakePage(url="https://jobs.example.com/login-help",
                        html="<form><input name='q'></form>")
        self.assertIsNone(detect_auth_loss(page))

    def test_login_path_still_matches(self):
        page = FakePage(url="https://jobs.example.com/login/")
        self.assertIsNotNone(detect_auth_loss(page))

    def test_login_subdomain_still_matches(self):
        page = FakePage(url="https://login.example.com/")
        self.assertIsNotNone(detect_auth_loss(page))

    def test_longer_hostname_does_not_match_login_dot(self):
        page = FakePage(url="https://mylogin.example.com/",
                        html="<form></form>")
        self.assertIsNone(detect_auth_loss(page))

    def test_text_marker_word_boundary_blocks_trafficker(self):
        page = FakePage(
            html="<p>Customs seized the unusual trafficker at dawn.</p>")
        self.assertIsNone(detect_captcha(page))

    def test_text_marker_word_boundary_blocks_accesses(self):
        page = FakePage(html="<p>Semi-automated accesses are logged here.</p>")
        self.assertIsNone(detect_captcha(page))

    def test_text_marker_still_matches_with_punctuation(self):
        page = FakePage(
            html="<p>Unusual traffic detected — complete the security check!</p>")
        hit = detect_captcha(page)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["reason"], "captcha")

    def test_checkpoint_in_job_slug_does_not_match(self):
        # Bare word markers are boundary-guarded like the others: a job
        # slug containing "checkpoint" must not cause a needless pause.
        page = FakePage(
            url="https://jobs.example.com/jobs/checkpoint-analyst-123",
            html="<form></form>")
        self.assertIsNone(detect_auth_loss(page))

    def test_checkpoint_path_still_matches(self):
        page = FakePage(url="https://example.com/checkpoint?x=1",
                        html="<form></form>")
        hit = detect_auth_loss(page)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["reason"], "auth_loss")
        self.assertIn("checkpoint", hit["evidence"])

    def test_authwall_subdomain_path_still_matches(self):
        page = FakePage(url="https://auth.example.com/authwall/",
                        html="<form></form>")
        self.assertIsNotNone(detect_auth_loss(page))


class NeverBypassTests(unittest.TestCase):
    def test_no_bypass_function_exists(self):
        names = [n.lower() for n, _ in inspect.getmembers(session_rescue)]
        for forbidden in ("bypass", "solve_captcha", "defeat", "click_through"):
            self.assertFalse(
                any(forbidden in n for n in names),
                f"forbidden bypass-adjacent member: {forbidden}",
            )

    def test_source_contains_no_bypass_implementation(self):
        import pathlib
        src = pathlib.Path(session_rescue.__file__).read_text()
        # "bypass" may only appear in refusal/policy prose, never as code.
        for i, line in enumerate(src.splitlines(), 1):
            stripped = line.strip()
            if "bypass" in stripped.lower() and not stripped.startswith(("#", '"""', '"')):
                # Allow only the refusal_note string and docstring prose.
                self.assertTrue(
                    'NEVER' in line or 'never' in line.lower(),
                    f"line {i}: suspicious bypass reference: {line.strip()[:80]}",
                )

    def test_refusal_note_states_policy(self):
        note = session_rescue.refusal_note()
        self.assertIn("never", note.lower())
        self.assertIn("handed to you", note.lower())


class DetectedAtTests(unittest.TestCase):
    def test_detected_at_is_timezone_aware_utc(self):
        page = FakePage(selectors={"#captcha"})
        handoff = check(page, board="greenhouse")
        stamp = datetime.fromisoformat(handoff.detected_at)
        self.assertIsNotNone(stamp.tzinfo, "detected_at must be tz-aware")
        self.assertEqual(stamp.utcoffset(), timedelta(0))
        self.assertIn("+00:00", handoff.detected_at)


def _install_fake_playwright(page):
    """Inject a fake ``playwright.sync_api`` module into sys.modules."""
    entered = mock.MagicMock()
    entered.__enter__.return_value = entered
    entered.__exit__.return_value = False
    fake_browser = mock.MagicMock()
    fake_context = mock.MagicMock()
    fake_context.new_page.return_value = page
    fake_browser.new_context.return_value = fake_context
    entered.chromium.launch.return_value = fake_browser
    sync_api = types.ModuleType("playwright.sync_api")
    sync_api.sync_playwright = lambda: entered
    pw = types.ModuleType("playwright")
    pw.sync_api = sync_api
    old = {n: sys.modules.get(n) for n in ("playwright", "playwright.sync_api")}
    sys.modules["playwright"] = pw
    sys.modules["playwright.sync_api"] = sync_api
    return old, fake_browser


def _install_fake_channels_registry():
    """Stub the interactive send-approval gate (``initiatives.i09.channels``).

    ``browser_apply`` refuses the submit click without a genuine approval
    record, so without this stub ``apply_via_browser`` returns early with
    an approval refusal and the pre-submit rescue re-check under test is
    never reached. The fake approves, letting the flow continue to the
    rescue check and the submit click.
    """
    approval = mock.MagicMock(name="fake_approval")
    registry = types.ModuleType("initiatives.i09.channels.registry")
    # Every authorize_send claim is recorded: the pre-submit rescue
    # test asserts the list stays empty on a CAPTCHA pause — a pause
    # must not mint or burn the single-use approval.
    registry.calls = []

    def _authorize_send(payload, channel=None, approval_id=None):
        registry.calls.append(
            {"payload": payload, "channel": channel, "approval_id": approval_id}
        )
        return approval, None

    registry.authorize_send = _authorize_send
    registry.consume_approval = lambda approval, channel=None: None
    mods = {
        "initiatives": types.ModuleType("initiatives"),
        "initiatives.i09": types.ModuleType("initiatives.i09"),
        "initiatives.i09.channels": types.ModuleType("initiatives.i09.channels"),
        "initiatives.i09.channels.registry": registry,
    }
    mods["initiatives"].i09 = mods["initiatives.i09"]
    mods["initiatives.i09"].channels = mods["initiatives.i09.channels"]
    mods["initiatives.i09.channels"].registry = registry
    old = {n: sys.modules.get(n) for n in mods}
    sys.modules.update(mods)
    return old, registry


def _restore_modules(old):
    for name, mod in old.items():
        if mod is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = mod


class _PlaywrightFakedTest(unittest.TestCase):
    """Base: fake playwright + stubbed browser_apply seams, restored on tearDown.

    Strategy trade-off (Rule 2): trades away detector-level granularity —
    the page is a scripted fake with canned answers — to get end-to-end
    coverage of the consumer's pause-before-submit wiring on the real
    call path.
    """

    def setUp(self):
        import browser_apply

        self.browser_apply = browser_apply
        self._patches = []
        self._pw_old = None
        self._channels_old = None

    def _start(self, target, new=mock.DEFAULT, **kwargs):
        patcher = mock.patch(target, new=new, **kwargs)
        self._patches.append(patcher)
        return patcher.start()

    def tearDown(self):
        for patcher in reversed(self._patches):
            patcher.stop()
        if self._pw_old is not None:
            _restore_modules(self._pw_old)
            self._pw_old = None
        if self._channels_old is not None:
            _restore_modules(self._channels_old)
            self._channels_old = None


class _FakeDelegatingCDPSession:
    """Emulates a Chromium CDP session whose isolated world is HONEST:
    it delegates to the fake page's own DOM model (the ``evaluate``
    dispatch). Models a benign page's isolated world — the values are
    the true DOM. Adapted from tests/test_email_sync.py's
    ``_FakeDelegatingCDPSession``.

    The ``veto:<marker>`` dispatch contract is shared with the page
    doubles: the marker identifies the probe, and the first CDP
    argument (the submitter reference) is forwarded so the page-side
    emulation sees the same input a real isolated world would."""

    def __init__(self, page):
        self._page = page

    def send(self, method, params=None):
        if method == "Page.getFrameTree":
            return {"frameTree": {"frame": {"id": "frame-1"}}}
        if method == "Page.createIsolatedWorld":
            return {"executionContextId": 7}
        if method == "Runtime.callFunctionOn":
            fn = (params or {}).get("functionDeclaration", "")
            args = (params or {}).get("arguments", [])
            arg = args[0].get("value") if args else None
            return {"result": {"value": self._page.evaluate(fn, arg)}}
        raise AssertionError(f"unexpected CDP method {method}")

    def detach(self):
        pass


class _FakeDelegatingCDPContext:
    """Fake Chromium browser context: exposes the CDP session factory,
    like a real Playwright ``BrowserContext`` on Chromium. Adapted from
    tests/test_email_sync.py's ``_FakeDelegatingCDPContext``."""

    def __init__(self, page):
        self._page = page

    def new_cdp_session(self, page):
        return _FakeDelegatingCDPSession(self._page)


class _FakeRescueLocator:
    """Discovery-only submit-button locator for
    ``_find_submit_button_with_pattern``. Production treats the locator
    as a discovery hint only — the round-9 submit targets the bound
    form itself via ``veto:submit-bound-form`` and never clicks it."""

    def __init__(self, page, selector):
        self._page = page
        self._selector = selector

    def count(self):
        return 1 if "submit" in self._selector else 0

    @property
    def first(self):
        return self

    def is_visible(self):
        return True

    def click(self, timeout=None):
        raise AssertionError(
            "the discovery-hint locator must never be clicked — the "
            "round-9 submit targets the bound form itself, with no "
            "click event dispatched"
        )


if __name__ == "__main__":
    unittest.main()
