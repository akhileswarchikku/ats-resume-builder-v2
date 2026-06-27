const BASE = "http://localhost:8001";

export async function getResumeSections() {
  const res = await fetch(`${BASE}/resume-sections`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function analyzeJD(jdText) {
  const res = await fetch(`${BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jd_text: jdText }),
  });
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
