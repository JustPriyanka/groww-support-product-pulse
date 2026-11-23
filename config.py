import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# LLM
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_FAST_MODEL = os.getenv("GROQ_FAST_MODEL", "openai/gpt-oss-20b")

# Static data (committed)
CORPUS_DIR = BASE_DIR / "data" / "corpus"
REVIEWS_CSV = BASE_DIR / "data" / "reviews" / "groww_reviews.csv"

# Mutable state (Railway volume)
DATA_DIR = Path(os.getenv("DATA_DIR", "data/state"))
if not DATA_DIR.is_absolute():
    DATA_DIR = BASE_DIR / DATA_DIR
DATA_DIR.mkdir(parents=True, exist_ok=True)
APP_DB = DATA_DIR / "app.db"
WORKSPACE_DB = DATA_DIR / "workspace.db"
LOG_FILE = DATA_DIR / "app.log"
REVIEWS_LIVE_CSV = DATA_DIR / "groww_reviews_live.csv"  # refreshed copy (weekly loop)

APPROVAL_SECRET = os.getenv("APPROVAL_SECRET", "dev-only-secret")
PULSE_CRON = os.getenv("PULSE_CRON", "0 9 * * mon")
PULSE_WINDOW_DAYS = int(os.getenv("PULSE_WINDOW_DAYS", "7"))
REFRESH_REVIEWS_ON_RUN = os.getenv("REFRESH_REVIEWS_ON_RUN", "true").lower() == "true"
REVIEWER_PASSCODE = os.getenv("REVIEWER_PASSCODE", "")
ENABLE_EVAL_HOOKS = os.getenv("ENABLE_EVAL_HOOKS", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Limits (problem statement)
MAX_REPLY_SENTENCES = 3
MAX_PULSE_WORDS = 250
MAX_EXPLAINER_BULLETS = 6
MAX_REFINEMENT_ROUNDS = 5
MAX_THEMES = 5
SIGNAL_THRESHOLD = 5  # same intent N times in one week -> pulse signal
