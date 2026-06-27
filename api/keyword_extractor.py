"""
LLM-driven keyword extraction + smart skill inference.

Single LLM call reads BOTH the resume and JD together, then decides:
  - add_to_resume : JD skills the candidate can claim given their background
  - already_present: skills already in the resume (no re-add needed)
  - skip           : certifications, clearances, soft skills, degree requirements

No hardcoded taxonomy — the LLM understands the candidate's actual background.
"""
from api import llm_client
from api.doc_loader import get_resume_text, get_projects, get_all_text


_EXTRACT_PROMPT = """You are an expert ATS resume keyword optimizer.

CANDIDATE RESUME:
{resume}

JOB DESCRIPTION:
{jd}

Analyze both documents and return a JSON object with exactly these keys:

{{
  "company": "<company name, or 'Unknown' if not stated>",
  "job_title": "<exact job title from the JD>",
  "add_to_resume": ["skill1", "skill2", ...],
  "already_present": ["skill1", "skill2", ...],
  "skip": [{{"skill": "name", "reason": "exact reason"}}]
}}

RULES:

add_to_resume — JD skills NOT in the resume, but the candidate's background clearly supports them:
  - Candidate has AWS + GenAI experience → add AWS AI services like Bedrock, SageMaker, etc.
  - Candidate has deep learning projects → add CUDA, mixed precision, distributed training
  - Candidate completed CS/CE degree → add C++, algorithms, data structures
  - Candidate has RAG projects → add "retrieval augmented generation", "vector search"
  - Candidate has Python + ML → add pandas, numpy, scikit-learn if JD mentions them
  - Use EXACT JD phrasing so the ATS matches it precisely
  - Be GENEROUS — add any standard tool/technique a professional with this background would know
  - Maximum 20 items

already_present — skills clearly in the resume already (even with different phrasing):
  - "ML" in resume → "machine learning" in JD = already_present
  - "GenAI" → "generative AI" = already_present
  - "RAG" → "retrieval augmented generation" = already_present

skip — ONLY these categories (give specific reason):
  - Professional certifications: Security+, CompTIA, AWS Certified, Google Cloud cert, etc. → reason: "professional certification"
  - Security clearances: TS/SCI, Poly, Secret, etc. → reason: "security clearance requirement"
  - Degree requirements: PhD required, Masters required, etc. → reason: "academic degree requirement"
  - Soft skills: communication, leadership, teamwork, interpersonal → reason: "soft skill"
  - Patents, publications, awards → reason: "achievement/credential, not a skill"

All skill values must be lowercase. Return only technical skills in add_to_resume.
"""


async def extract(jd_text: str, resume_text: str | None = None) -> dict:
    """
    Smart skill extraction: LLM reads resume + JD together and decides what to add.
    Returns company, job_title, add_to_resume, already_present, rejected_keywords.
    """
    if resume_text is None:
        resume_text = get_resume_text()

    messages = [
        {"role": "user", "content": _EXTRACT_PROMPT.format(
            resume=resume_text[:4000],  # cap to avoid token blowout
            jd=jd_text,
        )}
    ]
    raw = await llm_client.chat_json(messages, max_tokens=1500)

    all_text   = get_all_text().lower()
    add_skills = raw.get("add_to_resume", [])
    already    = raw.get("already_present", [])
    skipped    = raw.get("skip", [])

    # Tag each skill-to-add with a source label based on where evidence comes from
    project_text = " ".join(get_projects().values()).lower()
    tagged: list[tuple[str, str]] = []
    for sk in add_skills:
        kl = sk.lower()
        if kl in all_text:
            tagged.append((sk, "Verified in your docs"))
        elif kl in project_text:
            tagged.append((sk, "Backed by your projects"))
        else:
            tagged.append((sk, "Inferred from your background"))

    # Normalise skip list — LLM sometimes returns strings instead of dicts
    rejected = []
    for item in skipped:
        if isinstance(item, dict):
            rejected.append({"skill": item.get("skill", ""), "reason": item.get("reason", "Skipped")})
        elif isinstance(item, str):
            rejected.append({"skill": item, "reason": "Skipped by LLM"})

    return {
        "company":            raw.get("company", "Unknown"),
        "job_title":          raw.get("job_title", ""),
        "tagged_add":         tagged,           # [(skill, source_label)]
        "already_present":    [s.lower() for s in already],
        "rejected_keywords":  rejected,
    }
