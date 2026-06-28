"""
ATS Resume Builder API
Endpoints:
  POST /generate  — full pipeline: score before, inject keywords, compile PDF, score after
  POST /save      — write JD.txt + Resume.pdf to D:/My_Applications/Applies/{company}_{role}/
  GET  /health    — sanity check
"""
import base64
import re
import threading
import tempfile
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import asyncio
from api import doc_loader, ats_scorer, keyword_extractor, latex_builder, pdf_gen, resume_parser, cost_tracker, resume_verifier
from api import config


def _prewarm_tectonic():
    try:
        tectonic = pdf_gen._find_tectonic()
        minimal = r"\documentclass{article}\begin{document}ok\end{document}"
        with tempfile.TemporaryDirectory() as tmp:
            tex = Path(tmp) / "test.tex"
            tex.write_text(minimal)
            subprocess.run([tectonic, "--outdir", tmp, str(tex)],
                           capture_output=True, timeout=600)
        print("[pdf_gen] tectonic pre-warm done")
    except Exception as e:
        print(f"[pdf_gen] tectonic pre-warm failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    doc_loader.load_docs()
    threading.Thread(target=_prewarm_tectonic, daemon=True).start()
    yield


app = FastAPI(title="ATS Resume Builder", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class JDRequest(BaseModel):
    jd_text: str


class SaveRequest(BaseModel):
    company: str
    role: str
    jd_text: str
    pdf_b64: str


def _ats_to_dict(r: ats_scorer.ATSResult) -> dict:
    return {
        "overall": r.overall,
        "keyword_coverage": r.keyword_coverage,
        "skills_match": r.skills_match,
        "experience_match": r.experience_match,
        "education_match": r.education_match,
        "keywords_matched": r.keywords_matched,
        "keywords_missing": r.keywords_missing,
        "humanization": r.humanization,
        "resume_skills": r.resume_skills,
        "jd_skills": r.jd_skills,
        "interview_chance":   r.interview_chance,
        "interview_strength": r.interview_strength,
        "interview_concern":  r.interview_concern,
        "interview_summary":  r.interview_summary,
    }


def _safe_folder_name(text: str) -> str:
    return re.sub(r"[^\w\-]", "_", text.strip())[:60]


@app.post("/upload-docs")
async def upload_docs(
    resume: UploadFile = File(None),
    portfolio: UploadFile = File(None),
):
    """
    Upload resume and/or portfolio.
    Resume uploads are gated by an identity verification agent — the uploaded
    resume must belong to the same person as the currently authorized resume.
    """
    docs_dir = config.DOCS_DIR
    docs_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    verification: dict | None = None

    if resume and resume.filename:
        resume_bytes = await resume.read()

        # Run identity verification agent
        verification = await resume_verifier.verify(resume.filename, resume_bytes)

        if not verification["approved"]:
            raise HTTPException(
                status_code=403,
                detail={
                    "error":             "identity_mismatch",
                    "authorized_name":   verification["authorized_name"],
                    "uploaded_name":     verification["uploaded_name"],
                    "matched_fields":    verification["matched_fields"],
                    "mismatched_fields": verification["mismatched_fields"],
                    "message":           verification["message"],
                },
            )

        # Verified — save the new resume
        ext = Path(resume.filename).suffix or ".docx"
        dest = docs_dir / f"resume{ext}"
        dest.write_bytes(resume_bytes)
        saved.append(dest.name)

    if portfolio and portfolio.filename:
        dest = docs_dir / portfolio.filename
        dest.write_bytes(await portfolio.read())
        saved.append(dest.name)

    if saved:
        doc_loader.load_docs()

    return {
        "saved":        saved,
        "docs_dir":     str(docs_dir),
        "verification": verification,
    }


@app.get("/stats")
def stats():
    return cost_tracker.get_stats()


@app.get("/health")
def health():
    doc_loader.load_docs()
    return {
        "status": "ok",
        "resume_chars": len(doc_loader.get_resume_text()),
        "projects": list(doc_loader.get_projects().keys()),
    }


@app.get("/docs-status")
def docs_status():
    docs_dir = config.DOCS_DIR
    files = []
    if docs_dir.exists():
        for f in docs_dir.iterdir():
            try:
                files.append({"name": f.name, "size_bytes": f.stat().st_size})
            except Exception:
                pass
    doc_loader.load_docs()
    return {
        "docs_dir": str(docs_dir),
        "files": files,
        "resume_chars": len(doc_loader.get_resume_text()),
        "projects": list(doc_loader.get_projects().keys()),
    }


@app.post("/generate")
async def generate(req: JDRequest):
    # Always reload from disk so uploads are reflected immediately
    doc_loader.load_docs()
    resume_text = doc_loader.get_resume_text()
    if not resume_text:
        raise HTTPException(400, "No resume found in docs/. Add resume.pdf or resume.docx.")

    cost_before = cost_tracker.snapshot_cost()

    # Step 1 — LLM: score before + extract keywords in parallel
    # keyword_extractor now reads resume+JD together so it can infer skills intelligently
    before_task = asyncio.create_task(ats_scorer.score(resume_text, req.jd_text))
    extraction_task = asyncio.create_task(keyword_extractor.extract(req.jd_text, resume_text))
    before, extraction = await asyncio.gather(before_task, extraction_task)

    # Step 3 — parse resume.docx → structured dict, then build LaTeX (no LLM)
    docs_dir = config.DOCS_DIR
    docx_path = next(
        (docs_dir / f"resume{ext}" for ext in (".docx", ".doc") if (docs_dir / f"resume{ext}").exists()),
        None
    )
    if docx_path is None:
        raise HTTPException(400, "resume.docx not found in docs/. PDF generation requires the .docx file.")
    parsed = resume_parser.parse(docx_path)
    latex_source, change_log = latex_builder.build(parsed, extraction["tagged_add"])

    # Step 4 — compile to PDF
    try:
        pdf_bytes = pdf_gen.latex_to_pdf(latex_source)
    except RuntimeError as e:
        raise HTTPException(500, f"PDF compilation failed: {e}")

    # Step 5 — after score based on what was physically added to the resume
    actually_added = [item["skill"] for item in change_log["added"]]
    after = ats_scorer.compute_after_score(before, actually_added)

    generation_cost = round(cost_tracker.snapshot_cost() - cost_before, 6)
    cost_tracker.record_application()

    return {
        "company":           extraction["company"],
        "job_title":         extraction["job_title"],
        "change_log":        change_log,
        "already_present":   extraction["already_present"],
        "rejected_keywords": extraction["rejected_keywords"],
        "latex_source": latex_source,
        "pdf_b64": base64.b64encode(pdf_bytes).decode(),
        "before_metrics": _ats_to_dict(before),
        "after_metrics": _ats_to_dict(after),
        "generation_cost_usd": generation_cost,
        "session_stats": cost_tracker.get_stats(),
    }


@app.post("/save")
async def save(req: SaveRequest):
    folder = f"{_safe_folder_name(req.company)}_{_safe_folder_name(req.role)}"
    target = config.APPLIES_DIR / folder
    target.mkdir(parents=True, exist_ok=True)
    (target / "JD.txt").write_text(req.jd_text, encoding="utf-8")
    (target / "Resume.pdf").write_bytes(base64.b64decode(req.pdf_b64))
    return {"saved_to": str(target)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=config.API_PORT, reload=True)
