// VITE_API_URL is set in frontend/.env (local) or in Vercel env vars (production)
const BASE = import.meta.env.VITE_API_URL || "http://localhost:8001";

export async function uploadDocs(resumeFile, portfolioFile) {
  const form = new FormData();
  if (resumeFile)   form.append("resume",    resumeFile);
  if (portfolioFile) form.append("portfolio", portfolioFile);
  const res = await fetch(`${BASE}/upload-docs`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function generateResume(jdText) {
  const res = await fetch(`${BASE}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jd_text: jdText }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function saveApplication(company, role, jdText, pdfB64) {
  const res = await fetch(`${BASE}/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ company, role, jd_text: jdText, pdf_b64: pdfB64 }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function healthCheck() {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
