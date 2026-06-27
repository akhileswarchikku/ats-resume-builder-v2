"""
Loads resume + project docs from docs/ at startup. Cached in memory.
Re-parses only if a file's mtime changes.
"""
import pdfplumber
from pathlib import Path
from docx import Document
from api import config

_cache: dict[Path, tuple[float, str]] = {}  # path -> (mtime, text)

_resume_text: str = ""
_projects_text: dict[str, str] = {}  # filename -> text
_all_text: str = ""  # resume + all projects combined


def _read_file(path: Path) -> str:
    mtime = path.stat().st_mtime
    if path in _cache and _cache[path][0] == mtime:
        return _cache[path][1]

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        with pdfplumber.open(path) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    elif suffix in (".docx", ".doc"):
        doc = Document(path)
        text = "\n".join(p.text for p in doc.paragraphs)
    elif suffix in (".md", ".txt"):
        text = path.read_text(encoding="utf-8")
    else:
        text = ""

    _cache[path] = (mtime, text)
    return text


def load_docs() -> None:
    global _resume_text, _projects_text, _all_text

    docs_dir = config.DOCS_DIR
    resume_text = ""

    SUPPORTED = (".pdf", ".docx", ".md", ".txt")

    # Load resume text — prefer PDF (richer Unicode, e.g. → arrows) over DOCX when both exist.
    # The DOCX is still used separately by resume_parser.py for LaTeX structure.
    resume_text = ""
    for ext in (".pdf", ".docx", ".doc", ".md", ".txt"):
        resume_path = docs_dir / f"resume{ext}"
        if resume_path.exists():
            resume_text = _read_file(resume_path)
            break

    # Load all project docs — docs/projects/ AND any extra files in docs/ root
    projects: dict[str, str] = {}
    projects_dir = docs_dir / "projects"
    if projects_dir.exists():
        for f in projects_dir.iterdir():
            if f.suffix.lower() in SUPPORTED:
                projects[f.name] = _read_file(f)

    # Pick up any extra docs in root (e.g. Project_Portfolio_*.docx) — skip resume files
    for f in docs_dir.iterdir():
        if f.suffix.lower() in SUPPORTED and not f.stem.lower().startswith("resume") and f.name not in projects:
            projects[f.name] = _read_file(f)

    _resume_text = resume_text
    _projects_text = projects
    _all_text = resume_text + "\n\n" + "\n\n".join(projects.values())

    print(f"[doc_loader] Loaded resume ({len(resume_text)} chars) + {len(projects)} project docs")


def get_resume_text() -> str:
    return _resume_text


def get_all_text() -> str:
    return _all_text


def get_projects() -> dict[str, str]:
    return _projects_text
