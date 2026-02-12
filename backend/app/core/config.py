import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{(DATA_DIR / 'infra_change_risk_engine.db').as_posix()}"
SAMPLE_DIR = ROOT_DIR.parent / "samples"
API_PREFIX = "/api/v1"
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
WORKER_POLL_INTERVAL_SECONDS = 1.5

# LLM configuration — set OPENAI_API_KEY to enable the fix-generation agent.
# Works with OpenAI, Azure OpenAI, or any OpenAI-compatible API (e.g. Ollama).
LLM_API_KEY: str | None = os.environ.get("OPENAI_API_KEY")
LLM_BASE_URL: str | None = os.environ.get("OPENAI_BASE_URL")  # None → uses OpenAI default
LLM_MODEL: str = os.environ.get("LLM_MODEL", "gpt-4o-mini")

