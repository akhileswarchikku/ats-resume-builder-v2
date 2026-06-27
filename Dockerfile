FROM python:3.11-slim

WORKDIR /app

# ── System packages ──────────────────────────────────────────────────────────
# fontconfig + Caladea: metric-compatible free clone of Cambria
# curl: needed to download tectonic binary
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    fontconfig \
    fonts-crosextra-caladea \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*

# ── Tectonic ─────────────────────────────────────────────────────────────────
# Self-contained LaTeX compiler — downloads TeX packages on demand from the cloud.
# Using the statically-linked musl binary (no glibc dependency).
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

# Writable directories (docs uploaded at runtime via POST /upload-docs)
RUN mkdir -p docs outputs

ENV PYTHONUNBUFFERED=1
ENV DOCS_DIR=/app/docs
ENV APPLIES_DIR=/app/outputs

EXPOSE 8001
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8001"]
