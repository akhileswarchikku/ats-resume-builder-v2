"""
Parses resume.docx into structured sections using python-docx.
Splits on:
  1. <w:br> manual line breaks
  2. Bold "Category:" runs that start a new skill line within a merged paragraph
Parses Projects like Experience — bold title + bullet list.
"""
import re
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn

_LATEX_ESCAPE = str.maketrans({
    # Standard LaTeX special chars
    "&":  r"\&",
    "%":  r"\%",
    "$":  r"\$",
    "#":  r"\#",
    "_":  r"\_",
    "^":  r"\^{}",
    "~":  r"\~{}",
    "{":  r"\{",
    "}":  r"\}",
    "\\": r"\textbackslash{}",
    # Arrows & math symbols (common in ML resumes: 320ms → 190ms, ±2%, etc.)
    "→":  r"$\rightarrow$",
    "←":  r"$\leftarrow$",
    "↑":  r"$\uparrow$",
    "↓":  r"$\downarrow$",
    "↔":  r"$\leftrightarrow$",
    "⇒":  r"$\Rightarrow$",
    "≥":  r"$\geq$",
    "≤":  r"$\leq$",
    "≠":  r"$\neq$",
    "×":  r"$\times$",
    "÷":  r"$\div$",
    "±":  r"$\pm$",
    "°":  r"$^\circ$",
    "∞":  r"$\infty$",
    # Quotes & dashes
    "‘": r"`",   # left single quote '
    "’": r"'",   # right single quote '
    "“": r"``",  # left double quote "
    "”": r"''",  # right double quote "
    "–": r"--",  # en dash –
    "—": r"---", # em dash —
    # Other
    " ": r"~",   # non-breaking space
    "•": r"\textbullet{}",  # bullet •
    "…": r"\ldots{}",       # ellipsis …
    "®": r"\textregistered{}",
    "©": r"\textcopyright{}",
    "™": r"\texttrademark{}",
})


def _esc(text: str) -> str:
    return text.translate(_LATEX_ESCAPE)


_EMAIL_RE = re.compile(r'\b[\w.+%-]+@[\w.-]+\.[a-zA-Z]{2,}\b')


def _contact_para_to_latex(para) -> str:
    """
    Convert a header/contact paragraph to LaTeX.
    - <w:hyperlink> elements → \\href{url}{text}  (LinkedIn, website, mailto:)
    - Plain email addresses in runs → \\href{mailto:email}{email}
    - Everything else → _esc(text)
    URLs are passed through verbatim (not LaTeX-escaped) so they remain valid.
    """
    parts: list[str] = []

    for child in para._element:
        tag = child.tag

        if tag == qn("w:hyperlink"):
            # Relationship ID lives in the r: namespace
            r_id = child.get(qn("r:id"))
            # Collect display text from all w:r children
            display = "".join(
                t.text or ""
                for r in child.findall(qn("w:r"))
                for t in r.findall(qn("w:t"))
            ).strip()
            url = None
            if r_id:
                try:
                    url = para.part.rels[r_id].target_ref
                except (KeyError, AttributeError):
                    pass
            if url and display:
                parts.append(rf"\href{{{url}}}{{{_esc(display)}}}")
            elif display:
                parts.append(_esc(display))

        elif tag == qn("w:r"):
            raw = "".join(t.text or "" for t in child.findall(qn("w:t")))
            if not raw:
                continue
            # Auto-wrap bare email addresses in \href{mailto:...}
            out: list[str] = []
            last = 0
            for m in _EMAIL_RE.finditer(raw):
                if m.start() > last:
                    out.append(_esc(raw[last:m.start()]))
                email = m.group(0)
                out.append(rf"\href{{mailto:{email}}}{{{_esc(email)}}}")
                last = m.end()
            if last < len(raw):
                out.append(_esc(raw[last:]))
            parts.append("".join(out))

    return "".join(parts).strip()


def _get_para_lines(para) -> list[str]:
    """
    Convert a docx paragraph to one or more LaTeX strings.
    Splits on:
      - <w:br> elements (manual line breaks)
      - Bold runs that end with ':' and already have preceding content
        (e.g. "Cloud Platforms: ... Databases & Storage: ..." → 2 separate items)
    Preserves bold/italic run formatting.
    Tab characters (<w:tab/>) mid-line → \\hfill (pushes date to right margin).
    When normal (non-bold, non-italic) text follows \\hfill, a forced line-break
    (\\\\) is inserted so institution/location names drop to the next line.
    """
    lines: list[str] = []
    current: list[str] = []
    has_hfill: bool = False   # True after we emit \hfill in the current line

    for child in para._element:
        tag = child.tag

        if tag == qn("w:r"):
            is_bold = False
            is_italic = False
            texts: list[str] = []

            for rc in child:
                rtag = rc.tag
                if rtag == qn("w:rPr"):
                    is_bold   = rc.find(qn("w:b"))  is not None
                    is_italic = rc.find(qn("w:i"))  is not None
                elif rtag == qn("w:t"):
                    texts.append(rc.text or "")
                elif rtag == qn("w:tab"):
                    # Flush pending text, then emit \hfill for mid-line tabs.
                    t = _esc("".join(texts))
                    if t:
                        current.append(_wrap(t, is_bold, is_italic))
                    texts = []
                    if "".join(current).strip():   # mid-line tab → right-align remainder
                        current.append("\\hfill ")
                        has_hfill = True
                elif rtag == qn("w:br"):
                    # Manual line break — flush text, start new line, reset hfill state.
                    t = _esc("".join(texts))
                    if t:
                        t = _wrap(t, is_bold, is_italic)
                        current.append(t)
                    texts = []
                    lines.append("".join(current))
                    current = []
                    has_hfill = False

            raw = "".join(texts)
            t = _esc(raw)

            # Split on a bold "Category:" run ONLY when the existing content already
            # contains real skill items (2+ commas).
            # Before flushing, trim any trailing partial category label (e.g. "\textbf{Databases} \&")
            # so it becomes the START of the new line rather than the END of the old one.
            joined = "".join(current)
            if is_bold and raw.strip().endswith(":") and joined.count(",") >= 2:
                # Scan `current` from the right to rescue any trailing partial category
                # label items (e.g. \textbf{Databases} \textbf{\&}) that belong to the
                # NEXT line, not the current one.
                # Stop when we hit plain-text content or a \textbf{...:} complete label.
                _BOLD_NO_COLON = re.compile(r'^\\textbf\{([^}:]*)\}$')
                split_at = len(current)
                for k in range(len(current) - 1, -1, -1):
                    item = current[k]
                    if not item.strip():                          # whitespace run → keep scanning
                        continue
                    if _BOLD_NO_COLON.match(item.strip()):       # \textbf{Word} no colon → partial
                        split_at = k
                    else:                                         # content or complete label → stop
                        break
                lines.append("".join(current[:split_at]).rstrip())
                current = list(current[split_at:])

            if t:
                # After \hfill, a plain (non-bold, non-italic) run is an institution /
                # location name that belongs on the next visual line.
                if has_hfill and not is_bold and not is_italic and raw.strip():
                    current.append("\\\\\n" + _wrap(t, is_bold, is_italic))
                    has_hfill = False
                else:
                    current.append(_wrap(t, is_bold, is_italic))

        elif tag == qn("w:br"):
            lines.append("".join(current))
            current = []
            has_hfill = False

    if current:
        lines.append("".join(current))

    return [l for l in lines if l.strip()]


def _wrap(t: str, bold: bool, italic: bool) -> str:
    if bold and italic:
        return f"\\textbf{{\\textit{{{t}}}}}"
    if bold:
        return f"\\textbf{{{t}}}"
    if italic:
        return f"\\textit{{{t}}}"
    return t


_ADJ_BOLD_PARA = re.compile(r'\\textbf\{([^}]*)\}(\s*)\\textbf\{')

def _para_to_latex(para) -> str:
    s = "".join(_get_para_lines(para))
    # Merge adjacent \textbf{} blocks: \textbf{AI/ML} \textbf{Engineer} → \textbf{AI/ML Engineer}
    prev = None
    while prev != s:
        prev = s
        s = _ADJ_BOLD_PARA.sub(lambda m: f'\\textbf{{{m.group(1)}{m.group(2)}', s)
    return s


_SECTION_HEADERS = {
    "PROFESSIONAL SUMMARY", "SUMMARY",
    "TECHNICAL SKILLS", "SKILLS",
    "PROFESSIONAL EXPERIENCE", "EXPERIENCE", "WORK EXPERIENCE",
    "PROJECTS", "PERSONAL PROJECTS",
    "EDUCATION",
    "CERTIFICATIONS", "CERTIFICATIONS & ACHIEVEMENTS", "ACHIEVEMENTS",
    "PUBLICATIONS", "AWARDS",
}


def _is_section_header(text: str) -> bool:
    t = text.strip().upper()
    return t in _SECTION_HEADERS or any(t.startswith(h) for h in _SECTION_HEADERS)


def _parse_titled_section(paragraphs: list) -> list[dict]:
    """
    Parse a section that alternates between title paragraphs and bullet paragraphs.
    Returns [{"header_latex": str, "bullets": [str]}].
    Used for both Experience and Projects.
    """
    items = []
    current = None
    for p in paragraphs:
        t = p.text.strip()
        if not t:
            continue
        latex = _para_to_latex(p)
        is_bullet = (
            any(p.style.name.lower().startswith(x) for x in ("list", "bullet"))
            or t.startswith("•")
        )
        # Short non-bullet paragraph = title/header
        if not is_bullet and len(t) < 160:
            if current:
                items.append(current)
            current = {"header_latex": latex, "bullets": []}
        elif current is not None:
            clean = latex.lstrip("•\\item ").strip()
            if clean:
                current["bullets"].append(clean)
    if current:
        items.append(current)
    return items


def parse(docx_path: Path) -> dict:
    doc = Document(docx_path)
    paras = list(doc.paragraphs)

    # ---- Header (name, title, contact) ----
    # Store paragraphs so contact lines can be processed with the link-aware parser.
    header_paras = []
    first_section_idx = 0
    for i, p in enumerate(paras):
        t = p.text.strip()
        if not t:
            continue
        if _is_section_header(t):
            first_section_idx = i
            break
        header_paras.append(p)

    name  = header_paras[0].text.strip() if len(header_paras) > 0 else ""
    title = header_paras[1].text.strip() if len(header_paras) > 1 else ""
    # Contact paragraph(s): use link-aware parser to get \href for email + LinkedIn.
    # Multiple contact paras are joined with " | "; a single para keeps its own " | " separators.
    contact_parts = [_contact_para_to_latex(p) for p in header_paras[2:]]
    contact = " | ".join(p for p in contact_parts if p)

    # ---- Section grouping ----
    sections: dict[str, list] = {}
    section_order: list[str] = []
    current_section = None

    for p in paras[first_section_idx:]:
        t = p.text.strip()
        if not t:
            continue
        if _is_section_header(t):
            current_section = t.upper()
            if current_section not in sections:
                sections[current_section] = []
                section_order.append(current_section)
        elif current_section is not None:
            sections[current_section].append(p)

    # ---- Summary (always LaTeX-escaped) ----
    summary_key = next((k for k in section_order if "SUMMARY" in k), None)
    summary = " ".join(
        _esc(p.text.strip())
        for p in sections.get(summary_key, [])
        if p.text.strip()
    )

    # ---- Skills — split on w:br AND bold category boundaries ----
    skills_key = next((k for k in section_order if "SKILL" in k), None)
    skills: list[str] = []
    for p in sections.get(skills_key, []):
        for line in _get_para_lines(p):
            if line.strip():
                skills.append(line)

    # Post-process: if a skill line has no ":" it is a partial category label
    # (e.g. "Frameworks &" or "MLOps &") — merge it with the following line.
    def _plain(s: str) -> str:
        return re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", s)

    merged: list[str] = []
    i = 0
    while i < len(skills):
        plain = _plain(skills[i])
        if ":" not in plain and i + 1 < len(skills):
            merged.append(skills[i].rstrip() + skills[i + 1])
            i += 2
        else:
            merged.append(skills[i])
            i += 1
    skills = merged

    # Merge adjacent \textbf{} blocks on the same line into one.
    # e.g. \textbf{Databases} \textbf{\&} \textbf{Storage:} → \textbf{Databases \& Storage:}
    # Run repeatedly until stable (handles chains of 3+ blocks).
    _ADJ_BOLD = re.compile(r'\\textbf\{([^}]*)\}(\s*)\\textbf\{')
    def _merge_adj_bold(s: str) -> str:
        prev = None
        while prev != s:
            prev = s
            s = _ADJ_BOLD.sub(lambda m: f'\\textbf{{{m.group(1)}{m.group(2)}', s)
        return s
    skills = [_merge_adj_bold(s) for s in skills]

    # ---- Experience ----
    exp_key = next((k for k in section_order if "EXPERIENCE" in k), None)
    experience = _parse_titled_section(sections.get(exp_key, []))

    # ---- Projects ----
    proj_key = next((k for k in section_order if "PROJECT" in k), None)
    projects = _parse_titled_section(sections.get(proj_key, []))

    # ---- Education ----
    edu_key = next((k for k in section_order if "EDUCATION" in k), None)
    education = [
        _para_to_latex(p)
        for p in sections.get(edu_key, [])
        if p.text.strip()
    ]

    # ---- Certifications ----
    cert_key = next(
        (k for k in section_order if "CERT" in k or "ACHIEVE" in k), None
    )
    certifications = [
        _para_to_latex(p)
        for p in sections.get(cert_key, [])
        if p.text.strip()
    ]

    # ---- Other sections (anything not handled above) ----
    known = {summary_key, skills_key, exp_key, proj_key, edu_key, cert_key}
    extra_sections = []
    for k in section_order:
        if k not in known and sections.get(k):
            extra_sections.append({
                "title": k.title(),
                "lines": [_para_to_latex(p) for p in sections[k] if p.text.strip()],
            })

    return {
        "name": name, "title": title, "contact": contact,
        "summary": summary,
        "skills": skills,
        "experience": experience,
        "projects": projects,
        "education": education,
        "certifications": certifications,
        "extra_sections": extra_sections,
    }
