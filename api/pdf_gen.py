"""
Converts LaTeX source to PDF using tectonic (installed via conda-forge).
Returns raw PDF bytes.
"""
import subprocess
import tempfile
import shutil
from pathlib import Path


def _find_tectonic() -> str:
    import os
    candidates = [
        # Linux / Docker
        "/usr/local/bin/tectonic",
        "/usr/bin/tectonic",
        os.path.expanduser("~/.cargo/bin/tectonic"),   # cargo / drop.tectonic.works install
        os.path.expanduser("~/.local/bin/tectonic"),
        # Windows — conda LLM_GPU env
        r"C:\Users\akhil\anaconda3\envs\LLM_GPU\Library\bin\tectonic.exe",
        r"C:\Users\akhil\anaconda3\envs\LLM_GPU\Scripts\tectonic.exe",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    result = shutil.which("tectonic")
    if result:
        return result
    raise RuntimeError(
        "tectonic not found. "
        "Linux: curl --proto '=https' --tlsv1.2 -fsSL https://drop.tectonic.works | sh  "
        "Windows: conda install -c conda-forge tectonic"
    )


def latex_to_pdf(latex_source: str) -> bytes:
    """Compile LaTeX string to PDF bytes."""
    tectonic = _find_tectonic()

    with tempfile.TemporaryDirectory() as tmp:
        tex_path = Path(tmp) / "resume.tex"
        tex_path.write_text(latex_source, encoding="utf-8")

        result = subprocess.run(
            [tectonic, "--outdir", tmp, str(tex_path)],
            capture_output=True,
            text=True,
            timeout=300,  # 5 min for first run — tectonic downloads packages on demand
        )

        if result.returncode != 0:
            raise RuntimeError(f"tectonic error:\n{result.stderr}")

        pdf_path = Path(tmp) / "resume.pdf"
        if not pdf_path.exists():
            raise RuntimeError("tectonic ran but no PDF produced")

        return pdf_path.read_bytes()
