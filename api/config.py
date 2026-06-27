import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]
OPENROUTER_APP_TITLE = os.getenv("OPENROUTER_APP_TITLE", "ATS Resume Builder")
OPENROUTER_HTTP_REFERER = os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost:8001")
LLM_MODEL = os.getenv("LLM_MODEL", "google/gemini-2.5-flash")

DOCS_DIR = Path(os.getenv("DOCS_DIR", "./docs")).resolve()
APPLIES_DIR = Path(os.getenv("APPLIES_DIR", "D:/My_Applications/Applies"))
API_PORT = int(os.getenv("API_PORT", "8001"))
