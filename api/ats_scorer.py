"""
LLM-based ATS scorer — Gemini 2.5 Flash via OpenRouter.

Three analysis agents run in PARALLEL via asyncio.gather():
  1. Main ATS Agent  — skills matched/missing, YOE, degree
  2. Skills Depth Agent — are required skills *demonstrated* with evidence, or just listed?
  3. Role Fit Agent  — career trajectory, seniority, domain alignment

Their outputs feed a 4th Synthesis Agent that issues the final interview verdict
with a specific strength, concern, and 2-sentence summary.

Humanization score stays rule-based (pure text analysis).
"""
import asyncio
import re
from typing import NamedTuple


class ATSResult(NamedTuple):
    overall: float
    keyword_coverage: float
    skills_match: float
    experience_match: float
    education_match: float
    keywords_matched: list[str]
    keywords_missing: list[str]
    humanization: float
    resume_skills: list[str]
    jd_skills: list[str]
    interview_chance: str       # "Yes" | "No"
    interview_strength: str     # strongest reason to shortlist
    interview_concern: str      # biggest red flag / gap
    interview_summary: str      # 2-sentence recruiter assessment


# ---------------------------------------------------------------------------
# Agent 1 — Main ATS scoring
# ---------------------------------------------------------------------------
_SCORE_PROMPT = """You are an ATS analyzer. Compare the resume against the job description.

Return JSON with EXACTLY these keys:
{{
  "resume_skills": ["all technical skills, tools, frameworks in the RESUME"],
  "jd_skills":     ["all technical skills, tools, frameworks required or preferred by the JD"],
  "skills_matched": ["jd_skills present in the resume — include semantic matches"],
  "skills_missing": ["jd_skills NOT present in the resume"],
  "resume_yoe": <integer, total years of professional experience>,
  "jd_required_yoe": <integer, years required by JD, 0 if not stated>,
  "resume_degree": "<bachelor | master | phd | none>",
  "jd_required_degree": "<bachelor | master | phd | none>"
}}

Rules:
- Skills lists: technical only — no soft skills, no company names, no certifications
- Semantic matches count: "ML" = "machine learning", "GenAI" = "generative AI", "RAG" = "retrieval augmented generation"
- Each skill once, lowercase

RESUME:
{resume}

JOB DESCRIPTION:
{jd}
"""

# ---------------------------------------------------------------------------
# Agent 2 — Skills Depth (are skills proven with evidence, or just listed?)
# ---------------------------------------------------------------------------
_SKILLS_DEPTH_PROMPT = """You are a technical recruiter evaluating DEPTH of skills, not just presence.

For each required skill in the JD, assess whether the resume:
  - DEMONSTRATES it (projects, metrics, real outcomes) → "strong evidence"
  - MENTIONS it (listed in skills section, no proof of use) → "surface mention"
  - MISSING entirely → "absent"

Return JSON:
{{
  "depth_score": <0-100, where 100 = every required skill demonstrated with strong evidence>,
  "demonstrated_well": ["skills shown with strong project evidence or quantified impact"],
  "surface_only": ["skills listed but not backed by project work or metrics"],
  "critical_gap": "<the single most important JD requirement that is absent or too shallow>"
}}

RESUME:
{resume}

JOB DESCRIPTION:
{jd}
"""

# ---------------------------------------------------------------------------
# Agent 3 — Role Fit (trajectory, seniority, domain alignment)
# ---------------------------------------------------------------------------
_ROLE_FIT_PROMPT = """You are a senior recruiter evaluating fit BEYOND keyword matching.
Assess career trajectory, seniority level, industry/domain alignment, and whether
the candidate's past responsibilities match what this role actually expects day-to-day.

Return JSON:
{{
  "role_fit_score": <0-100>,
  "strongest_fit": "<the single most compelling reason this candidate fits this specific role>",
  "main_concern":  "<the single most significant mismatch between this candidate and this role>",
  "seniority_match": "<too_junior | good_match | too_senior>",
  "domain_match":    "<strong | partial | weak>"
}}

RESUME:
{resume}

JOB DESCRIPTION:
{jd}
"""

# ---------------------------------------------------------------------------
# Agent 4 — Synthesis (sequential, after agents 1-3 complete)
# ---------------------------------------------------------------------------
_SYNTHESIS_PROMPT = """You are a hiring manager making a final shortlist decision.
You have results from three independent analyses below. Synthesize them into a final verdict.

── ATS Metrics ──────────────────────────────────────────
Overall match:    {overall}%
Skills match:     {skills_match}%
Experience match: {exp_match}%
Education match:  {edu_match}%
Missing skills:   {missing_skills}

── Skills Depth Analysis (depth_score: {depth_score}/100) ─
Demonstrated with evidence: {demonstrated_well}
Surface mentions only:      {surface_only}
Critical gap:               {critical_gap}

── Role Fit Analysis (role_fit_score: {role_fit_score}/100) ─
Strongest fit:    {strongest_fit}
Main concern:     {main_concern}
Seniority match:  {seniority_match}
Domain match:     {domain_match}

Return JSON:
{{
  "interview_chance": "<yes | no>",
  "strength":  "<one specific sentence — the most compelling reason to shortlist>",
  "concern":   "<one specific sentence — the most critical risk or gap>",
  "summary":   "<exactly 2 sentences — honest, specific recruiter-level assessment of this candidate's realistic chances>"
}}
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_FILLER_PHRASES = [
    "responsible for", "duties included", "helped with", "worked on",
    "assisted in", "was involved in", "tasked with", "participated in",
]
_PASSIVE = re.compile(r"\b(was|were|been|being|is|are)\s+\w+ed\b", re.IGNORECASE)
_DEGREE_RANK = {"none": 0, "bachelor": 1, "master": 2, "phd": 3}


def _humanization_score(text: str) -> float:
    sentences = [s.strip() for s in re.split(r"[.!?]", text) if len(s.strip()) > 10]
    if not sentences:
        return 0.0
    passive_ratio = len(_PASSIVE.findall(text)) / max(len(sentences), 1)
    filler_count = sum(1 for f in _FILLER_PHRASES if f in text.lower())
    lengths = [len(s.split()) for s in sentences]
    mean_len = sum(lengths) / len(lengths)
    variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
    words = text.lower().split()
    richness = len(set(words)) / max(len(words), 1)
    return round(
        (1 - min(passive_ratio, 1.0)) * 30
        + (1 - min(filler_count / 5, 1.0)) * 25
        + min(variance / 100, 1.0) * 25
        + richness * 20,
        1,
    )


def _fallback_verdict(overall: float, skills_match: float, missing_count: int) -> tuple[str, str, str, str]:
    if overall >= 65 and skills_match >= 60:
        return (
            "Yes",
            f"Strong overall ATS match of {overall:.0f}% with good skills alignment.",
            f"{missing_count} JD skills are missing — adding them would further strengthen the application.",
            f"This candidate has a solid foundation for the role with {overall:.0f}% overall match. "
            f"Addressing the {missing_count} missing skills before applying would improve shortlist odds.",
        )
    return (
        "No",
        "Candidate has relevant background that could be strengthened with better JD alignment.",
        f"Overall match of {overall:.0f}% is below typical ATS threshold; {missing_count} required skills are absent.",
        f"This candidate needs significant resume tailoring to pass ATS screening for this role. "
        f"Focus on closing the {missing_count} skill gaps and highlighting relevant project outcomes.",
    )


# ---------------------------------------------------------------------------
# Parallel agent calls
# ---------------------------------------------------------------------------
async def _call_agent(prompt: str) -> dict:
    from api import llm_client
    return await llm_client.chat_json(
        [{"role": "user", "content": prompt}],
        max_tokens=1000,
    )


async def _run_main_agent(resume: str, jd: str) -> dict:
    return await _call_agent(_SCORE_PROMPT.format(resume=resume, jd=jd))


async def _run_depth_agent(resume: str, jd: str) -> dict:
    return await _call_agent(_SKILLS_DEPTH_PROMPT.format(resume=resume, jd=jd))


async def _run_role_agent(resume: str, jd: str) -> dict:
    return await _call_agent(_ROLE_FIT_PROMPT.format(resume=resume, jd=jd))


async def _run_synthesis(
    overall: float, skills_match: float, exp_match: float, edu_match: float,
    missing: list[str], depth: dict, role: dict,
) -> dict:
    prompt = _SYNTHESIS_PROMPT.format(
        overall=overall,
        skills_match=skills_match,
        exp_match=exp_match,
        edu_match=edu_match,
        missing_skills=", ".join(missing[:10]) or "none",
        depth_score=depth.get("depth_score", "N/A"),
        demonstrated_well=", ".join(depth.get("demonstrated_well", [])[:5]) or "none identified",
        surface_only=", ".join(depth.get("surface_only", [])[:5]) or "none",
        critical_gap=depth.get("critical_gap", "N/A"),
        role_fit_score=role.get("role_fit_score", "N/A"),
        strongest_fit=role.get("strongest_fit", "N/A"),
        main_concern=role.get("main_concern", "N/A"),
        seniority_match=role.get("seniority_match", "N/A"),
        domain_match=role.get("domain_match", "N/A"),
    )
    return await _call_agent(prompt)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
async def score(resume_text: str, jd_text: str) -> ATSResult:
    """
    Runs 3 agents in parallel (main ATS + skills depth + role fit),
    then a synthesis agent for the interview verdict.
    """
    # --- Phase 1: parallel ---------------------------------------------------
    main_raw, depth_raw, role_raw = await asyncio.gather(
        _run_main_agent(resume_text, jd_text),
        _run_depth_agent(resume_text, jd_text),
        _run_role_agent(resume_text, jd_text),
    )

    # --- Extract main ATS metrics --------------------------------------------
    matched       = [s.lower().strip() for s in main_raw.get("skills_matched", []) if s.strip()]
    missing       = [s.lower().strip() for s in main_raw.get("skills_missing", []) if s.strip()]
    resume_skills = [s.lower().strip() for s in main_raw.get("resume_skills",  []) if s.strip()]
    jd_skills     = [s.lower().strip() for s in main_raw.get("jd_skills",      []) if s.strip()]

    total = len(matched) + len(missing)
    skills_match = round(len(matched) / max(total, 1) * 100, 1)

    resume_yoe = int(main_raw.get("resume_yoe", 0) or 0)
    jd_yoe     = int(main_raw.get("jd_required_yoe", 0) or 0)
    exp_match  = round(min(resume_yoe / jd_yoe, 1.0) * 100, 1) if jd_yoe > 0 else 100.0

    resume_deg  = main_raw.get("resume_degree", "none").lower().strip()
    jd_deg      = main_raw.get("jd_required_degree", "none").lower().strip()
    resume_rank = _DEGREE_RANK.get(resume_deg, 0)
    jd_rank     = _DEGREE_RANK.get(jd_deg, 0)
    edu_match   = 100.0 if resume_rank >= jd_rank else round(resume_rank / max(jd_rank, 1) * 100, 1)

    overall = round(skills_match * 0.5 + exp_match * 0.3 + edu_match * 0.2, 1)

    # --- Phase 2: synthesis (sequential, needs phase 1 results) --------------
    try:
        synth = await _run_synthesis(overall, skills_match, exp_match, edu_match, missing, depth_raw, role_raw)
        chance   = (synth.get("interview_chance") or "").lower().strip()
        strength = (synth.get("strength") or "").strip()
        concern  = (synth.get("concern")  or "").strip()
        summary  = (synth.get("summary")  or "").strip()
        if chance in ("yes", "no") and strength and concern and summary:
            interview_chance    = chance.capitalize()
            interview_strength  = strength
            interview_concern   = concern
            interview_summary   = summary
        else:
            interview_chance, interview_strength, interview_concern, interview_summary = \
                _fallback_verdict(overall, skills_match, len(missing))
    except Exception:
        interview_chance, interview_strength, interview_concern, interview_summary = \
            _fallback_verdict(overall, skills_match, len(missing))

    return ATSResult(
        overall=overall,
        keyword_coverage=skills_match,
        skills_match=skills_match,
        experience_match=exp_match,
        education_match=edu_match,
        keywords_matched=sorted(matched),
        keywords_missing=sorted(missing),
        humanization=_humanization_score(resume_text),
        resume_skills=sorted(resume_skills),
        jd_skills=sorted(jd_skills),
        interview_chance=interview_chance,
        interview_strength=interview_strength,
        interview_concern=interview_concern,
        interview_summary=interview_summary,
    )


def compute_after_score(before: ATSResult, approved_keywords: list[str]) -> ATSResult:
    """
    Re-scores after keyword injection — no LLM call needed.
    Moves approved keywords from missing → matched; verdict updates rule-based.
    """
    missing_set    = {k.lower() for k in before.keywords_missing}
    approved_lower = {k.lower() for k in approved_keywords}

    matched_after = sorted(set(before.keywords_matched) | (missing_set & approved_lower))
    missing_after = sorted(missing_set - approved_lower)

    total        = len(matched_after) + len(missing_after)
    skills_match = round(len(matched_after) / max(total, 1) * 100, 1)
    overall      = round(skills_match * 0.5 + before.experience_match * 0.3 + before.education_match * 0.2, 1)

    chance, strength, concern, summary = _fallback_verdict(overall, skills_match, len(missing_after))

    # Keep the deep-analysis strength/concern from before if overall improved
    if chance == "Yes" and before.interview_chance == "Yes":
        strength = before.interview_strength
        concern  = before.interview_concern

    return ATSResult(
        overall=overall,
        keyword_coverage=skills_match,
        skills_match=skills_match,
        experience_match=before.experience_match,
        education_match=before.education_match,
        keywords_matched=matched_after,
        keywords_missing=missing_after,
        humanization=before.humanization,
        resume_skills=before.resume_skills,
        jd_skills=before.jd_skills,
        interview_chance=chance,
        interview_strength=strength,
        interview_concern=concern,
        interview_summary=summary,
    )
