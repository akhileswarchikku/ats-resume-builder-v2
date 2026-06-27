"""
Converts LaTeX source to PDF using tectonic (installed via conda-forge).
Returns raw PDF bytes.
"""
import subprocess
import tempfile
import shutil
from pathlib import Path


def _find_tectonic() -> str:
    # tectonic installed via conda-forge lands here on Windows
    candidates = [
        r"C:\Users\akhil\anaconda3\envs\LLM_GPU\Library\bin\tectonic.exe",
        r"C:\Users\akhil\anaconda3\envs\LLM_GPU\Scripts\tectonic.exe",
        "tectonic",  # if on PATH
    ]
    for c in candidates:
        path = Path(c)
        if path.exists():
            return str(path)
    result = shutil.which("tectonic")
    if result:
        return result
    raise RuntimeError("tectonic not found. Install with: conda install -c conda-forge tectonic")


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
