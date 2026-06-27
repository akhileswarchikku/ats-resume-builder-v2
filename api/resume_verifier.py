"""
Identity verification agent.

When a resume is uploaded, this agent reads it, extracts identity markers
(name, email, phone, LinkedIn, location), compares them against the currently
authorized resume on the server, and grants or denies the upload.

Bootstrap rule: if no authorized resume exists yet (first run), the first
upload is automatically approved so the server can be seeded.
"""
import io
import json
import re

from docx import Document
import pdfplumber

from api import llm_client, doc_loader


_VERIFY_PROMPT = """\
You are an identity verification agent for a private, single-user ATS resume tool.

Your job: decide if the UPLOADED resume belongs to the SAME person as the AUTHORIZED resume.

Compare ONLY these identity markers from the contact/header section:
- Full name
- Email address
- Phone number
- LinkedIn / GitHub / personal website URL
- City or location

AUTHORIZED RESUME (ground truth — extract identity from this):
{authorized_text}

UPLOADED RESUME (verify this):
{uploaded_text}

Decision rules:
1. If the name AND at least one contact field (email / phone / LinkedIn) clearly match → same_person: true
2. Minor spelling variations of the same name are acceptable (e.g. "Akhil" vs "Akhileswar")
3. If the authorized resume text is empty → same_person: true  (first-time bootstrap)
4. When uncertain, err toward rejection (false)

Respond with a JSON object only — no markdown fences, no extra text:
{{
  "same_person": true,
  "confidence": "high",
  "authorized_name": "name extracted from authorized resume",
  "uploaded_name": "name extracted from uploaded resume",
  "matched_fields": ["name", "email"],
  "mismatched_fields": [],
  "message": "One clear sentence explaining the decision."
}}
"""


def _extract_text(filename: str, data: bytes) -> str:
    """Extract plain text from file bytes — no disk write needed."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    try:
        if ext in ("docx", "doc"):
            doc = Document(io.BytesIO(data))
            return "\n".join(p.text for p in doc.paragraphs)
        elif ext == "pdf":
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                return "\n".join(p.extract_text() or "" for p in pdf.pages)
    except Exception:
        pass
    return data.decode("utf-8", errors="ignore")


async def verify(filename: str, uploaded_bytes: bytes) -> dict:
    """
    Run the identity verification agent.

    Returns a dict:
      {
        "approved":   bool,
        "confidence": "high" | "medium" | "low",
        "authorized_name": str,
        "uploaded_name":   str,
        "matched_fields":    list[str],
        "mismatched_fields": list[str],
        "message":    str,
      }
    Never raises — any error becomes an approved=False result.
    """
    uploaded_text  = _extract_text(filename, uploaded_bytes)
    authorized_text = doc_loader.get_resume_text()

    # Bootstrap: no authorized resume yet → allow first upload
    if not authorized_text.strip():
        return {
            "approved":          True,
            "confidence":        "high",
            "authorized_name":   "",
            "uploaded_name":     "",
            "matched_fields":    [],
            "mismatched_fields": [],
            "message":           "No existing resume on file — first-time setup approved.",
        }

    messages = [
        {
            "role": "system",
            "content": "You are a strict identity verification agent. Respond with valid JSON only.",
        },
        {
            "role": "user",
            "content": _VERIFY_PROMPT.format(
                authorized_text=authorized_text[:3000],
                uploaded_text=uploaded_text[:3000],
            ),
        },
    ]

    try:
        result = await llm_client.chat_json(messages, max_tokens=512)
        return {
            "approved":          bool(result.get("same_person", False)),
            "confidence":        result.get("confidence", "low"),
            "authorized_name":   result.get("authorized_name", ""),
            "uploaded_name":     result.get("uploaded_name", ""),
            "matched_fields":    result.get("matched_fields", []),
            "mismatched_fields": result.get("mismatched_fields", []),
            "message":           result.get("message", "Verification failed."),
        }
    except Exception as e:
        return {
            "approved":          False,
            "confidence":        "low",
            "authorized_name":   "",
            "uploaded_name":     "",
            "matched_fields":    [],
            "mismatched_fields": [],
            "message":           f"Verification agent error: {e}",
        }
