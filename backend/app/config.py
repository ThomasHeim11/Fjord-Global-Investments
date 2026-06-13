"""Central configuration. Paths are resolved relative to the repo layout so the
app runs the same way from any working directory."""
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent

load_dotenv(BACKEND_DIR / ".env")

# Source data shipped with the case assignment
DATA_DIR = REPO_DIR / "data"
SUBSIDIARIES_CSV = DATA_DIR / "subsidiaries.csv"
BOARD_UPDATES_JSON = DATA_DIR / "board_updates.json"
LETTERS_DIR = DATA_DIR / "letters"

# Derived storage (rebuilt from source data — never committed)
STORAGE_DIR = BACKEND_DIR / "storage"
DB_PATH = STORAGE_DIR / "fgi.db"
FAISS_INDEX_PATH = STORAGE_DIR / "chunks.faiss"

# Embeddings: local model — zero API cost, works offline during the demo.
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# LLM — provider-agnostic by design ("any provider or open-source model").
# Groq serves open models with a free tier; Anthropic is the premium option.
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY") or os.environ.get("qroq_api", "")

# Ordered chain of free Groq models. Each model has its own daily token
# budget, so when one is exhausted (HTTP 429) the pipeline falls through to
# the next — effectively summing every free model's quota. Override the order
# with the GROQ_FALLBACK_MODELS env var (comma-separated).
# Instruct models that reliably emit clean JSON in Groq's JSON mode are listed
# first; reasoning models (which emit a thinking preamble and can fail JSON
# validation) are intentionally excluded from the default chain.
GROQ_FALLBACK_MODELS = [
    m.strip() for m in os.environ.get("GROQ_FALLBACK_MODELS", "").split(",") if m.strip()
] or [
    "meta-llama/llama-4-scout-17b-16e-instruct",  # 500k tokens/day
    "llama-3.1-8b-instant",                        # 500k, fast
    "llama-3.3-70b-versatile",                     # 100k, strong
    "openai/gpt-oss-120b",                         # 200k
    "openai/gpt-oss-20b",                          # 200k
]
GROQ_MODEL = os.environ.get("GROQ_MODEL", GROQ_FALLBACK_MODELS[0])
# Preferred starting model for the hardest pass (letter reconciliation); it
# still falls through the chain if rate-limited.
GROQ_REASONING_MODEL = os.environ.get("GROQ_REASONING_MODEL", "openai/gpt-oss-120b")

# Burst control for the free tier. The daily token budget is rarely the
# problem; the per-minute request/token limit is. Pace calls so a review
# doesn't fire a burst that trips every model at once, and when the whole
# chain IS momentarily limited, wait the suggested time and retry instead of
# giving up.
GROQ_MIN_INTERVAL = float(os.environ.get("GROQ_MIN_INTERVAL", "4"))     # seconds between calls (wider = fewer per-minute rate limits, slower run)
GROQ_RETRY_ROUNDS = int(os.environ.get("GROQ_RETRY_ROUNDS", "4"))       # chain passes before giving up
GROQ_MAX_BACKOFF = float(os.environ.get("GROQ_MAX_BACKOFF", "30"))      # cap on a single wait

# Ollama — a local, OpenAI-compatible model server. No token limits, fully
# offline. Used as the unlimited final fallback after the Groq chain, or as
# the sole provider when LLM_PROVIDER=ollama. Set OLLAMA_MODEL to your exact
# `ollama list` tag.
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma4:e4b")
USE_OLLAMA_FALLBACK = os.environ.get("USE_OLLAMA_FALLBACK", "true").lower() == "true"

# Provider: groq (default if key set), ollama (local, unlimited), or anthropic.
LLM_PROVIDER = os.environ.get("LLM_PROVIDER") or ("groq" if GROQ_API_KEY else "anthropic")
LLM_MODEL = {
    "groq": GROQ_MODEL,
    "ollama": OLLAMA_MODEL,
}.get(LLM_PROVIDER, ANTHROPIC_MODEL)

# "Today" for expiry/overdue calculations. Defaults to the real current date
# (production-correct). Set REFERENCE_DATE to pin it for reproducible tests or a
# frozen-snapshot demo (the case data is built around early June 2026).
REFERENCE_DATE = os.environ.get("REFERENCE_DATE") or date.today().isoformat()

STORAGE_DIR.mkdir(exist_ok=True)
