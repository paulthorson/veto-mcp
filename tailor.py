#!/usr/bin/env python3
"""Per-job application tailoring: keyword-matched resume + cover letter.

Pure local string logic — no LLM calls, no network.

Honesty contract (hard rule): this module NEVER invents experience,
titles, companies, dates, or skills. It only rephrases, reorders, and
selects from what already exists in the applicant's profile. Skills the
job asks for but the profile lacks are reported in ``missing_skills``
and are NOT added to the resume.
"""

from __future__ import annotations

import logging
import re
from typing import Any

log = logging.getLogger("job-apply-mcp.tailor")

# Built-in vocabulary for keyword extraction. The profile's own skills are
# always added to this set, so niche skills still get matched.
_SKILL_VOCABULARY = {
    # languages / runtimes
    "python", "java", "javascript", "typescript", "go", "golang", "rust",
    "c++", "c#", "ruby", "php", "swift", "kotlin", "scala", "sql",
    # web / frontend
    "react", "angular", "vue", "next.js", "node.js", "nodejs", "html",
    "css", "django", "flask", "fastapi", "spring", "rails",
    # data / ml
    "machine learning", "deep learning", "pandas", "numpy", "spark",
    "tensorflow", "pytorch", "nlp", "etl", "airflow", "dbt", "tableau",
    "power bi", "excel",
    # infra / devops
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
    "jenkins", "github actions", "ci/cd", "linux", "nginx",
    # practices
    "agile", "scrum", "rest", "graphql", "microservices", "tdd",
    "a/b testing", "system design", "distributed systems",
    # general professional
    "leadership", "mentoring", "communication", "stakeholder",
    "project management", "product management",
}


def _profile_skills(profile: dict[str, Any]) -> list[str]:
    raw = profile.get("skills", []) or []
    skills: list[str] = []
    for item in raw:
        if isinstance(item, dict):
            name = item.get("name") or item.get("skill")
        else:
            name = item
        if name:
            skills.append(str(name).strip())
    # De-dupe case-insensitively, keep first-seen casing.
    seen: set[str] = set()
    out: list[str] = []
    for s in skills:
        if s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out


def _profile_text_blob(profile: dict[str, Any]) -> str:
    """All profile text, used to verify a claim really exists in it."""
    parts: list[str] = []
    for key in ("summary", "headline"):
        if profile.get(key):
            parts.append(str(profile[key]))
    for exp in profile.get("experience", []) or []:
        if isinstance(exp, dict):
            parts.append(" ".join(str(exp.get(k, "") or "") for k in ("title", "company", "dates")))
            parts.extend(str(b) for b in exp.get("bullets", []) or [])
    for edu in profile.get("education", []) or []:
        if isinstance(edu, dict):
            parts.append(" ".join(str(edu.get(k, "") or "") for k in ("degree", "school", "dates")))
    return "\n".join(parts)


def extract_job_keywords(
    job_details: dict[str, Any], profile: dict[str, Any]
) -> dict[str, list[str]]:
    """Split job-description keywords into matched vs missing skills.

    Returns {"matched": [...], "missing": [...]} ordered by frequency in
    the posting. A skill counts as matched only if it appears in the
    profile's own skill list (case-insensitive).
    """
    text = " ".join(
        str(job_details.get(k, "") or "")
        for k in ("title", "description", "requirements", "snippet")
    ).lower()
    vocab = set(_SKILL_VOCABULARY) | {s.lower() for s in _profile_skills(profile)}
    profile_skill_set = {s.lower() for s in _profile_skills(profile)}

    counts: dict[str, int] = {}
    for term in vocab:
        # Word-boundary match so "go" doesn't match "going".
        hits = len(re.findall(r"(?<![a-z0-9+#])" + re.escape(term) + r"(?![a-z0-9+#])", text))
        if hits:
            counts[term] = hits

    # Restore the profile's original casing for matched skills.
    casing = {s.lower(): s for s in _profile_skills(profile)}
    matched = sorted(
        (casing.get(t, t) for t in counts if t in profile_skill_set),
        key=lambda t: -counts[t.lower()],
    )
    missing = sorted(
        (t for t in counts if t not in profile_skill_set),
        key=lambda t: -counts[t],
    )
    return {"matched": matched, "missing": missing}


def _bullet_score(bullet: str, keywords: list[str]) -> int:
    low = bullet.lower()
    return sum(1 for kw in keywords if kw.lower() in low)


def tailor_resume(
    profile: dict[str, Any], job_details: dict[str, Any]
) -> dict[str, Any]:
    """Build a keyword-tuned resume + cover letter from the profile.

    Reorders (never rewrites the facts of) experience bullets so bullets
    mentioning the job's matched keywords come first. Returns
    {"resume_md", "cover_letter", "matched_skills", "missing_skills"}.
    """
    keywords = extract_job_keywords(job_details, profile)
    matched = keywords["matched"]

    name = str(profile.get("full_name") or profile.get("name") or "").strip()
    contact_bits = [
        str(profile.get(k, "") or "").strip()
        for k in ("email", "phone", "location")
    ]
    contact_bits = [b for b in contact_bits if b]
    linkedin = str(profile.get("linkedin_url") or "").strip()

    lines: list[str] = [f"# {name}" if name else "# Resume"]
    if contact_bits:
        lines.append(" | ".join(contact_bits))
    if linkedin:
        lines.append(linkedin)
    lines.append("")

    summary = str(profile.get("summary") or "").strip()
    if not summary:
        titles = profile.get("target_titles") or profile.get("target_roles") or []
        years = profile.get("years_experience") or profile.get("years_of_experience")
        bits = []
        if years:
            bits.append(f"{years} years of experience")
        if titles:
            t = titles[0] if isinstance(titles, list) else titles
            bits.append(f"targeting {t} roles")
        if matched:
            bits.append(f"skilled in {', '.join(matched[:5])}")
        summary = ("Professional with " + ", ".join(bits) + ".") if bits else ""
    if summary:
        lines += ["## Summary", summary, ""]

    lines.append("## Experience")
    for exp in profile.get("experience", []) or []:
        if not isinstance(exp, dict):
            continue
        header = " — ".join(
            p for p in (exp.get("title"), exp.get("company")) if p
        )
        dates = str(exp.get("dates") or "").strip()
        lines.append(f"### {header}" + (f"  \n*{dates}*" if dates else ""))
        bullets = [str(b) for b in exp.get("bullets", []) or [] if b]
        # Front-load bullets that mention the job's matched keywords.
        # Facts are untouched; only ordering changes.
        bullets.sort(key=lambda b: -_bullet_score(b, matched))
        for b in bullets:
            lines.append(f"- {b}")
        lines.append("")

    education = profile.get("education", []) or []
    if education:
        lines.append("## Education")
        for edu in education:
            if isinstance(edu, dict):
                deg = " — ".join(p for p in (edu.get("degree"), edu.get("school")) if p)
                dates = str(edu.get("dates") or "").strip()
                lines.append(f"- {deg}" + (f" ({dates})" if dates else ""))
            else:
                lines.append(f"- {edu}")
        lines.append("")

    if matched:
        lines += ["## Skills", ", ".join(matched), ""]

    resume_md = "\n".join(lines).strip() + "\n"

    # --- cover letter: 3 paragraphs, profile facts only ---
    company = str(job_details.get("company") or "").strip()
    title = str(job_details.get("title") or "").strip()
    first_name = name.split()[0] if name else "there"
    top_exp: dict[str, Any] = {}
    for exp in profile.get("experience", []) or []:
        if isinstance(exp, dict) and exp.get("title"):
            top_exp = exp
            break
    top_title = str(top_exp.get("title", "") or "")
    top_company = str(top_exp.get("company", "") or "")

    p1_bits = []
    if top_title:
        p1_bits.append(f"as a {top_title}" + (f" at {top_company}" if top_company else ""))
    if matched:
        p1_bits.append(f"with hands-on experience in {', '.join(matched[:4])}")
    p1 = (
        f"I'm excited to apply for the {title} role"
        + (f" at {company}" if company else "")
        + (", bringing " + " ".join(p1_bits) if p1_bits else "")
        + "."
    )
    p2 = (
        f"What draws me to this opportunity is the focus on "
        f"{', '.join(matched[:3]) if matched else 'the core responsibilities described'}"
        + (f" at {company}" if company else "")
        + ", which aligns closely with the work I've been doing."
    )
    p3 = (
        f"I'd welcome the chance to discuss how I can contribute. "
        f"Thank you for your consideration — {name}."
        if name
        else "I'd welcome the chance to discuss how I can contribute. Thank you for your consideration."
    )
    cover_letter = "\n\n".join(
        [f"Dear Hiring Manager,", p1, p2, p3]
    )

    return {
        "resume_md": resume_md,
        "cover_letter": cover_letter,
        "matched_skills": matched,
        "missing_skills": keywords["missing"],
    }
