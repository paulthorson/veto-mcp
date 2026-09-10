#!/usr/bin/env python3
"""Onboarding wizard for the job-apply MCP server.

Run interactively::

    python3 wizard.py

Answers can also be piped via stdin for scripted runs, e.g.::

    printf 'Jane Doe\\n...\\n3\\n' | python3 wizard.py

The wizard collects contact info, job-search preferences, and skills,
optionally ingests a LinkedIn data-export ZIP (or tries a public profile
URL), and writes the merged result to ``profiles/profile.json``.

The written profile includes at least the keys the browser-apply hook
needs: full_name (plus first_name/last_name), email, phone, location,
linkedin_url, website, and cover_letter (empty unless the user supplies
one later).
"""

from __future__ import annotations

import csv
import io
import json
import sys
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROFILES_DIR = BASE_DIR / "profiles"
PROFILE_PATH = PROFILES_DIR / "profile.json"

# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------


def ask(prompt: str, default: str = "") -> str:
    """Ask a question, showing the default. Enter accepts the default."""
    if default:
        answer = input(f"{prompt} [{default}]: ").strip()
        return answer if answer else default
    return input(f"{prompt}: ").strip()


def ask_list(prompt: str, default: str = "") -> list[str]:
    """Ask for a comma-separated list; returns a cleaned list."""
    raw = ask(prompt, default)
    return [part.strip() for part in raw.split(",") if part.strip()]


def dedupe(items: list[str]) -> list[str]:
    """Dedupe strings case-insensitively, preserving first-seen order."""
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item.strip())
    return out


# ---------------------------------------------------------------------------
# LinkedIn export ingestion
# ---------------------------------------------------------------------------


def _read_zip_csv(zf: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    """Read a CSV from the ZIP; return [] if missing or unreadable."""
    try:
        with zf.open(name) as fh:
            text = io.TextIOWrapper(fh, encoding="utf-8-sig").read()
    except KeyError:
        return []
    reader = csv.DictReader(io.StringIO(text))
    return [{k: (v or "").strip() for k, v in row.items()} for row in reader]


def _normalise_date(value: str) -> str:
    """Normalise a LinkedIn date like 'January 2020' to '2020-01'."""
    value = (value or "").strip()
    if not value:
        return ""
    months = {
        "january": "01", "february": "02", "march": "03", "april": "04",
        "may": "05", "june": "06", "july": "07", "august": "08",
        "september": "09", "october": "10", "november": "11", "december": "12",
    }
    parts = value.split()
    if len(parts) == 2 and parts[0].lower() in months and parts[1].isdigit():
        return f"{parts[1]}-{months[parts[0].lower()]}"
    if len(parts) == 1 and value.isdigit():
        return value
    return value  # keep as-is when it doesn't match a known pattern


def parse_linkedin_export_zip(zip_path: str | Path) -> dict:
    """Parse a LinkedIn data-export ZIP into profile fragments.

    Handles (case-insensitively) Profile.csv, Positions.csv,
    Education.csv and Skills.csv from the official export, returning a
    dict with keys: full_name, first_name, last_name, headline, summary,
    location, linkedin_url, experience (list), education (list), skills
    (list). Missing files just yield empty values.
    """
    zip_path = Path(zip_path).expanduser()
    if not zip_path.is_file():
        raise FileNotFoundError(f"LinkedIn export ZIP not found: {zip_path}")

    data: dict = {
        "full_name": "", "first_name": "", "last_name": "", "headline": "",
        "summary": "", "location": "", "linkedin_url": "",
        "experience": [], "education": [], "skills": [],
    }

    with zipfile.ZipFile(zip_path) as zf:
        names = {n.lower(): n for n in zf.namelist()}

        def get(name: str) -> list[dict[str, str]]:
            return _read_zip_csv(zf, names[name.lower()]) if name.lower() in names else []

        # --- Profile.csv: first/last name, headline, summary, location ---
        for row in get("Profile.csv"):
            keys = {k.lower(): k for k in row}
            getc = lambda *cands: next(
                (row[keys[c]] for c in cands if c in keys), ""
            )
            first = getc("first name", "firstname")
            last = getc("last name", "lastname")
            if not data["full_name"] and (first or last):
                data["first_name"] = first
                data["last_name"] = last
                data["full_name"] = f"{first} {last}".strip()
            data["headline"] = data["headline"] or getc("headline")
            data["summary"] = data["summary"] or getc("summary")
            data["location"] = data["location"] or getc(
                "geo location", "location", "geo_location"
            )

        # --- Positions.csv: title, company, start/end dates, description ---
        for row in get("Positions.csv"):
            keys = {k.lower(): k for k in row}
            getc = lambda *cands: next(
                (row[keys[c]] for c in cands if c in keys), ""
            )
            title = getc("title")
            company = getc("company name", "company")
            if not title and not company:
                continue
            start = _normalise_date(getc("started on", "startedon", "start date"))
            end_raw = getc("finished on", "finishedon", "end date")
            end = "" if end_raw.lower() in {"", "present"} else _normalise_date(end_raw)
            data["experience"].append({
                "title": title,
                "company": company,
                "location": getc("location"),
                "start": start,
                "end": end,  # "" means current role
                "description": getc("description"),
            })

        # --- Education.csv: school, degree, field of study, dates ---
        for row in get("Education.csv"):
            keys = {k.lower(): k for k in row}
            getc = lambda *cands: next(
                (row[keys[c]] for c in cands if c in keys), ""
            )
            school = getc("school name", "school")
            if not school:
                continue
            data["education"].append({
                "school": school,
                "degree": getc("degree name", "degree"),
                "field": getc("field of study", "field"),
                "start": _normalise_date(getc("start date", "started on")),
                "end": _normalise_date(getc("end date", "finished on")),
            })

        # --- Skills.csv: skill names ---
        for row in get("Skills.csv"):
            keys = {k.lower(): k for k in row}
            getc = lambda *cands: next(
                (row[keys[c]] for c in cands if c in keys), ""
            )
            skill = getc("name", "skill", "skills")
            if skill:
                data["skills"].append(skill)

    data["skills"] = dedupe(data["skills"])
    return data


def fetch_linkedin_public_profile(url: str) -> dict:
    """Best-effort fetch of a public LinkedIn profile URL.

    LinkedIn blocks most unauthenticated scraping, so this typically
    returns little. It is kept as a convenience fallback; the
    data-export ZIP (option 1) is far more reliable.
    """
    try:
        import httpx
        from bs4 import BeautifulSoup
    except ImportError as exc:  # pragma: no cover - dependency issue
        raise RuntimeError(
            "httpx and beautifulsoup4 are required for this option"
        ) from exc

    result: dict = {
        "full_name": "", "first_name": "", "last_name": "", "headline": "",
        "summary": "", "location": "", "linkedin_url": url,
        "experience": [], "education": [], "skills": [],
    }
    resp = httpx.get(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0 Safari/537.36"
            )
        },
        timeout=20,
        follow_redirects=True,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    # Public pages often embed "Name | LinkedIn" or similar in <title>.
    if title:
        name = title.split("|")[0].strip()
        if name:
            result["full_name"] = name
            parts = name.split()
            result["first_name"] = parts[0]
            result["last_name"] = parts[-1] if len(parts) > 1 else ""

    headline_el = soup.select_one("h2, .text-body-medium")
    if headline_el:
        result["headline"] = headline_el.get_text(" ", strip=True)

    for h in soup.select("h3, h4"):
        text = h.get_text(" ", strip=True)
        if text and len(text) > 8:
            result["experience"].append({
                "title": text, "company": "", "location": "",
                "start": "", "end": "", "description": "",
            })
    return result


# ---------------------------------------------------------------------------
# Merging
# ---------------------------------------------------------------------------


def merge_profile(base: dict, linkedin: dict) -> dict:
    """Merge LinkedIn fragments into the wizard profile.

    Scalar fields are only filled when the wizard left them empty;
    experience/education are appended (skipping duplicates); skills are
    merged and deduped.
    """
    for key in ("full_name", "headline", "summary", "location"):
        if not base.get(key) and linkedin.get(key):
            base[key] = linkedin[key]
    if not base.get("first_name") and linkedin.get("first_name"):
        base["first_name"] = linkedin["first_name"]
    if not base.get("last_name") and linkedin.get("last_name"):
        base["last_name"] = linkedin["last_name"]

    seen_exp = {
        (e.get("title", "").lower(), e.get("company", "").lower())
        for e in base.get("experience", [])
    }
    for exp in linkedin.get("experience", []):
        key = (exp.get("title", "").lower(), exp.get("company", "").lower())
        if key not in seen_exp and any(exp.values()):
            base.setdefault("experience", []).append(exp)
            seen_exp.add(key)

    seen_edu = {e.get("school", "").lower() for e in base.get("education", [])}
    for edu in linkedin.get("education", []):
        if edu.get("school") and edu["school"].lower() not in seen_edu:
            base.setdefault("education", []).append(edu)
            seen_edu.add(edu["school"].lower())

    base["skills"] = dedupe(base.get("skills", []) + linkedin.get("skills", []))
    return base


def blank_profile() -> dict:
    """Return the profile skeleton with every schema key present."""
    return {
        "full_name": "",
        "first_name": "",
        "last_name": "",
        "email": "",
        "phone": "",
        "location": "",
        "linkedin_url": "",
        "website": "",
        "cover_letter": "",
        "summary": "",
        "target_titles": [],
        "preferred_locations": [],
        "remote_preference": "any",
        "minimum_salary": "",
        "years_experience": "",
        "skills": [],
        "work_authorization": "",
        "experience": [],
        "education": [],
    }


# ---------------------------------------------------------------------------
# Wizard flow
# ---------------------------------------------------------------------------


def collect_basics() -> dict:
    """Interactive Q&A for the core profile fields."""
    profile = blank_profile()
    print("\n=== Job-Apply Onboarding Wizard ===\n")
    print("Press Enter to accept the [default] shown, or type your own.\n")

    print("--- Contact & identity ---")
    profile["full_name"] = ask("Full name")
    parts = profile["full_name"].split()
    profile["first_name"] = ask("First name", parts[0] if parts else "")
    profile["last_name"] = ask(
        "Last name", " ".join(parts[1:]) if len(parts) > 1 else ""
    )
    profile["email"] = ask("Email")
    profile["phone"] = ask("Phone")
    profile["location"] = ask("Location (city, state)", "New York, NY")
    profile["linkedin_url"] = ask("LinkedIn profile URL")
    profile["website"] = ask("Website / portfolio URL (optional)")

    print("\n--- Job search preferences ---")
    profile["target_titles"] = ask_list("Target job titles (comma-separated)")
    profile["preferred_locations"] = ask_list(
        "Preferred locations (comma-separated)", "Remote"
    )
    remote = ask("Remote preference", "any").lower()
    while remote not in {"remote", "hybrid", "onsite", "any"}:
        print("  Please choose one of: remote / hybrid / onsite / any")
        remote = ask("Remote preference", "any").lower()
    profile["remote_preference"] = remote
    profile["minimum_salary"] = ask("Minimum salary (optional)")
    profile["years_experience"] = ask("Years of experience")
    profile["skills"] = dedupe(ask_list("Top skills (comma-separated)"))
    profile["work_authorization"] = ask(
        "Work authorization status", "US citizen"
    )

    print("\n--- Professional summary ---")
    profile["summary"] = ask(
        "One-paragraph professional summary (optional)"
    )
    return profile


def linkedin_ingestion() -> dict | None:
    """Offer the three LinkedIn ingestion options; return fragments or None."""
    print("\n--- LinkedIn ingestion ---")
    print("  1. Path to LinkedIn data-export ZIP")
    print("     (Settings & Privacy > Data Privacy > Get a copy of your data)")
    print("  2. Public LinkedIn profile URL (best-effort; LinkedIn usually")
    print("     blocks unauthenticated scraping — option 1 is recommended)")
    print("  3. Skip")
    choice = ask("Choose an option", "3").strip()

    if choice == "1":
        zip_path = ask("Path to the LinkedIn export ZIP")
        try:
            data = parse_linkedin_export_zip(zip_path)
        except FileNotFoundError as exc:
            print(f"  !! {exc} — continuing without LinkedIn data.")
            return None
        except zipfile.BadZipFile:
            print("  !! That file is not a valid ZIP — continuing without "
                  "LinkedIn data.")
            return None
        print(f"  Parsed: {len(data['experience'])} position(s), "
              f"{len(data['education'])} education entr(y/ies), "
              f"{len(data['skills'])} skill(s).")
        return data

    if choice == "2":
        url = ask("Public LinkedIn profile URL")
        if not url:
            print("  No URL given — skipping.")
            return None
        try:
            data = fetch_linkedin_public_profile(url)
        except Exception as exc:  # LinkedIn usually blocks this
            print(f"  !! Could not fetch the profile ({exc}).")
            print("  Tip: use option 1 (data-export ZIP) instead.")
            return None
        print("  Best-effort fetch done. Check the parsed values below —")
        print("  LinkedIn usually blocks unauthenticated scraping, so")
        print("  expect limited results.")
        return data

    print("  Skipping LinkedIn ingestion.")
    return None


def print_summary(profile: dict) -> None:
    """Print a readable summary of the finished profile."""
    print("\n=== Profile summary ===")
    print(f"Name:       {profile['full_name']}")
    print(f"Email:      {profile['email']}")
    print(f"Phone:      {profile['phone']}")
    print(f"Location:   {profile['location']}")
    print(f"LinkedIn:   {profile['linkedin_url'] or '(not set)'}")
    print(f"Website:    {profile['website'] or '(not set)'}")
    print(f"Targets:    {', '.join(profile['target_titles']) or '(none)'}")
    print(f"Locations:  {', '.join(profile['preferred_locations'])}")
    print(f"Remote:     {profile['remote_preference']}")
    print(f"Min salary: {profile['minimum_salary'] or '(not set)'}")
    print(f"Experience: {profile['years_experience']} year(s), "
          f"{len(profile['experience'])} position(s) on file")
    print(f"Education:  {len(profile['education'])} entr(y/ies) on file")
    print(f"Skills:     {', '.join(profile['skills']) or '(none)'}")
    print(f"Work auth:  {profile['work_authorization']}")


def main() -> int:
    profile = collect_basics()
    linkedin_data = linkedin_ingestion()
    if linkedin_data:
        profile = merge_profile(profile, linkedin_data)

    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    with PROFILE_PATH.open("w", encoding="utf-8") as fh:
        json.dump(profile, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print_summary(profile)
    print(f"\nSaved profile to {PROFILE_PATH}")
    print("\nNext steps:")
    print("  1. Generate your resume:")
    print("       python3 resume_builder.py")
    print("  2. In the MCP server, use the get_profile / apply_to_job tools")
    print("     — they read this profile automatically, including the")
    print("     name/email/phone/location/LinkedIn/website/cover_letter")
    print("     fields the browser hook needs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
