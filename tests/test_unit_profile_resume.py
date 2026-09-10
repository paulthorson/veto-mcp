"""Unit tests for the onboarding wizard + resume builder (no network).

Builds a tiny fake LinkedIn data-export ZIP, runs it through
wizard.parse_linkedin_export_zip / merge_profile, and checks
resume_builder output. Interactive wizard input is simulated via
unittest.mock, writing to a temp dir (never the real profile).
"""

from __future__ import annotations

import csv
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import resume_builder  # noqa: E402
import wizard  # noqa: E402


def make_linkedin_zip(path: Path) -> None:
    """Write a minimal but realistic LinkedIn export ZIP."""
    def csv_text(rows):
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue()

    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("Profile.csv", csv_text([{
            "First Name": "Ada", "Last Name": "Lovelace",
            "Headline": "Software Engineer",
            "Summary": "Pioneer of computing.",
            "Geo Location": "London, UK",
        }]))
        zf.writestr("Positions.csv", csv_text([
            {"Title": "Analyst", "Company Name": "Charles Babbage & Co",
             "Location": "London", "Started On": "January 1840",
             "Finished On": "December 1852",
             "Description": "Wrote the first algorithm."},
            {"Title": "Consultant", "Company Name": "Babbage & Co",
             "Location": "London", "Started On": "March 1853",
             "Finished On": "Present", "Description": ""},
        ]))
        zf.writestr("Education.csv", csv_text([{
            "School Name": "University of London", "Degree Name": "BSc",
            "Field of Study": "Mathematics",
            "Start Date": "1835", "End Date": "1839",
        }]))
        zf.writestr("Skills.csv", csv_text([
            {"Name": "Analytical Engines"},
            {"Name": "Mathematics"},
            {"Name": "mathematics"},  # duplicate (case) -> deduped
        ]))


SAMPLE_PROFILE = {
    "full_name": "Ada Lovelace",
    "first_name": "Ada",
    "last_name": "Lovelace",
    "email": "ada@example.com",
    "phone": "+1 555-0100",
    "location": "New York, NY",
    "linkedin_url": "https://www.linkedin.com/in/adalovelace",
    "website": "https://adalovelace.dev",
    "cover_letter": "",
    "summary": "Pioneer of computing.",
    "target_titles": ["Software Engineer"],
    "preferred_locations": ["Remote"],
    "remote_preference": "remote",
    "minimum_salary": "",
    "years_experience": "10",
    "skills": ["Python", "Algorithms"],
    "work_authorization": "US citizen",
    "experience": [{
        "title": "Analyst", "company": "Charles Babbage & Co",
        "location": "London", "start": "1840-01", "end": "1852-12",
        "description": "Wrote the first algorithm.",
    }],
    "education": [{
        "school": "University of London", "degree": "BSc",
        "field": "Mathematics", "start": "1835", "end": "1839",
    }],
}


class TestLinkedInZipParsing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.zip_path = Path(self.tmp.name) / "linkedin_export.zip"
        make_linkedin_zip(self.zip_path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_parse_profile(self):
        data = wizard.parse_linkedin_export_zip(self.zip_path)
        self.assertEqual(data["full_name"], "Ada Lovelace")
        self.assertEqual(data["first_name"], "Ada")
        self.assertEqual(data["last_name"], "Lovelace")
        self.assertEqual(data["headline"], "Software Engineer")
        self.assertEqual(data["location"], "London, UK")

    def test_parse_positions(self):
        data = wizard.parse_linkedin_export_zip(self.zip_path)
        self.assertEqual(len(data["experience"]), 2)
        first = data["experience"][0]
        self.assertEqual(first["title"], "Analyst")
        self.assertEqual(first["company"], "Charles Babbage & Co")
        self.assertEqual(first["start"], "1840-01")
        self.assertEqual(first["end"], "1852-12")
        # "Present" end date -> "" (current role)
        self.assertEqual(data["experience"][1]["end"], "")

    def test_parse_education(self):
        data = wizard.parse_linkedin_export_zip(self.zip_path)
        self.assertEqual(len(data["education"]), 1)
        self.assertEqual(data["education"][0]["school"],
                         "University of London")

    def test_parse_skills_deduped(self):
        data = wizard.parse_linkedin_export_zip(self.zip_path)
        self.assertEqual(data["skills"], ["Analytical Engines", "Mathematics"])

    def test_missing_zip_raises(self):
        with self.assertRaises(FileNotFoundError):
            wizard.parse_linkedin_export_zip("/tmp/no-such-export.zip")

    def test_missing_csvs_yield_empties(self):
        empty_zip = Path(self.tmp.name) / "empty.zip"
        with zipfile.ZipFile(empty_zip, "w") as zf:
            zf.writestr("readme.txt", "nothing here")
        data = wizard.parse_linkedin_export_zip(empty_zip)
        self.assertEqual(data["experience"], [])
        self.assertEqual(data["skills"], [])


class TestMergeProfile(unittest.TestCase):
    def test_scalars_only_fill_blanks(self):
        base = wizard.blank_profile()
        base["full_name"] = "Custom Name"
        merged = wizard.merge_profile(base, {
            "full_name": "Ada Lovelace", "headline": "Engineer",
            "summary": "", "location": "London",
            "experience": [], "education": [], "skills": ["Go"],
        })
        self.assertEqual(merged["full_name"], "Custom Name")  # not overwritten
        self.assertEqual(merged["headline"], "Engineer")      # filled in
        self.assertIn("Go", merged["skills"])

    def test_experience_deduped(self):
        base = wizard.blank_profile()
        base["experience"] = [{"title": "Analyst",
                               "company": "Charles Babbage & Co"}]
        merged = wizard.merge_profile(base, {
            "full_name": "", "headline": "", "summary": "", "location": "",
            "experience": [
                {"title": "Analyst", "company": "Charles Babbage & Co"},
                {"title": "Consultant", "company": "Babbage & Co"},
            ],
            "education": [], "skills": [],
        })
        titles = [e["title"] for e in merged["experience"]]
        self.assertEqual(titles, ["Analyst", "Consultant"])

    def test_blank_profile_has_browser_hook_keys(self):
        profile = wizard.blank_profile()
        for key in ("full_name", "first_name", "last_name", "email", "phone",
                    "location", "linkedin_url", "website", "cover_letter"):
            self.assertIn(key, profile)


class TestWizardInteractive(unittest.TestCase):
    """Simulate the Q&A via mocked input; write to a temp dir only."""

    ANSWERS = [
        # collect_basics
        "Ada Lovelace",      # full name
        "",                  # first name (default)
        "",                  # last name (default)
        "ada@example.com",   # email
        "+1 555-0100",       # phone
        "",                  # location (default New York, NY)
        "https://www.linkedin.com/in/adalovelace",
        "",                  # website
        "Software Engineer", # target titles
        "",                  # preferred locations (default Remote)
        "",                  # remote preference (default any)
        "",                  # minimum salary
        "10",                # years of experience
        "Python, Algorithms",
        "",                  # work authorization (default US citizen)
        "Pioneer of computing.",
        # linkedin_ingestion
        "3",                 # skip
    ]

    def test_main_writes_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with mock.patch("builtins.input", side_effect=list(self.ANSWERS)), \
                 mock.patch.object(wizard, "PROFILES_DIR", tmp_path), \
                 mock.patch.object(wizard, "PROFILE_PATH",
                                   tmp_path / "profile.json"):
                rc = wizard.main()
            self.assertEqual(rc, 0)
            profile = json.loads((tmp_path / "profile.json").read_text())
            self.assertEqual(profile["full_name"], "Ada Lovelace")
            self.assertEqual(profile["first_name"], "Ada")
            self.assertEqual(profile["last_name"], "Lovelace")
            self.assertEqual(profile["email"], "ada@example.com")
            self.assertEqual(profile["location"], "New York, NY")
            self.assertEqual(profile["target_titles"], ["Software Engineer"])
            self.assertEqual(profile["skills"], ["Python", "Algorithms"])


class TestResumeBuilder(unittest.TestCase):
    def test_markdown(self):
        md = resume_builder.build_markdown(SAMPLE_PROFILE)
        self.assertIn("# Ada Lovelace", md)
        self.assertIn("ada@example.com", md)
        self.assertIn("## Experience", md)
        self.assertIn("Charles Babbage & Co", md)
        self.assertIn("## Education", md)
        self.assertIn("University of London", md)
        self.assertIn("## Skills", md)
        self.assertIn("Python, Algorithms", md)

    def test_html_escapes(self):
        profile = dict(SAMPLE_PROFILE, full_name="<Ada & Co>")
        html_text = resume_builder.build_html(profile)
        self.assertIn("&lt;Ada &amp; Co&gt;", html_text)
        self.assertNotIn("<Ada & Co>", html_text)

    def test_html_structure(self):
        html_text = resume_builder.build_html(SAMPLE_PROFILE)
        self.assertIn("<h2>Experience</h2>", html_text)
        self.assertIn("linkedin.com/in/adalovelace", html_text)

    def test_main_writes_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp) / "profile.json"
            profile_path.write_text(json.dumps(SAMPLE_PROFILE))
            with mock.patch.object(resume_builder, "DEFAULT_PROFILE",
                                   profile_path):
                rc = resume_builder.main(["resume_builder.py",
                                          str(profile_path)])
            self.assertEqual(rc, 0)
            self.assertTrue((Path(tmp) / "resume.md").is_file())
            self.assertTrue((Path(tmp) / "resume.html").is_file())
            md = (Path(tmp) / "resume.md").read_text()
            self.assertIn("Ada Lovelace", md)


if __name__ == "__main__":
    unittest.main()
