FROM python:3.11-slim

WORKDIR /app

# ── System packages ───────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    fontconfig \
    fonts-crosextra-caladea \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*

# ── Tectonic (statically-linked musl binary) ──────────────────────────────────
ENV TECTONIC_VERSION=0.16.9
RUN curl -fsSL \
    "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%40${TECTONIC_VERSION}/tectonic-${TECTONIC_VERSION}-x86_64-unknown-linux-musl.tar.gz" \
    | tar xz -C /usr/local/bin/ \
    && chmod +x /usr/local/bin/tectonic

# ── Python dependencies ───────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application source ────────────────────────────────────────────────────────
COPY api/ ./api/

# ── Tectonic pre-warm ─────────────────────────────────────────────────────────
# Download all TeX packages used by the app during build so the first
# PDF generation at runtime is fast (no package downloads needed).
RUN printf '\
\\documentclass[10pt,letterpaper]{article}\n\
\\usepackage[top=0.5in,bottom=0.5in,left=0.7in,right=0.7in]{geometry}\n\
\\usepackage{fontspec}\n\
\\setmainfont{Caladea}\n\
\\usepackage{enumitem}\n\
\\usepackage{hyperref}\n\
\\usepackage{titlesec}\n\
\\usepackage{parskip}\n\
\\begin{document}warmup\\end{document}' > /tmp/warm.tex \
    && tectonic /tmp/warm.tex --outdir /tmp \
    && rm -f /tmp/warm.tex /tmp/warm.pdf

# ── Runtime setup ─────────────────────────────────────────────────────────────
RUN mkdir -p docs outputs

ENV PYTHONUNBUFFERED=1
ENV DOCS_DIR=/app/docs
ENV APPLIES_DIR=/app/outputs

EXPOSE 8001
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8001"]
