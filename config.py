"""
Configuration module for ResumRank AI
=====================================

Loads environment variables and defines application constants.
No API keys required — this app uses local spaCy NLP for all text processing.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# =========== App Settings ===========
APP_NAME = "ResumRank AI"
APP_ENV = os.getenv("APP_ENV", "development")  # "development" or "production"
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
DEBUG = APP_ENV == "development"


def is_heroku() -> bool:
    """Check whether the app is running on Heroku runtime."""
    return bool(os.getenv("DYNO"))


def _get_storage_root() -> str:
    """Return writable runtime storage root for current environment."""
    explicit_root = os.getenv("STORAGE_ROOT")
    if explicit_root:
        return explicit_root

    # On Linux runtimes (Heroku, Docker, serverless), /tmp is writable.
    if os.path.isdir("/tmp"):
        return "/tmp/resumrank"

    # Local development fallback.
    return "."

# =========== NLP Configuration ===========
SPACY_MODEL = "en_core_web_sm"      # spaCy language model
NLP_MODE = "local"                   # "local" = spaCy, future: "api" = Gemini
MAX_RESUME_WORDS = 4000             # Truncate resumes longer than this

# =========== Scoring Weights ===========
SKILL_WEIGHT = 0.7          # 70% of final score from skill match
EXPERIENCE_WEIGHT = 0.3     # 30% of final score from experience level

# =========== File Handling ===========
MAX_UPLOAD_SIZE_MB = 10
# On Heroku, ephemeral filesystem resets on dyno restart; use /tmp for runtime storage.
_STORAGE_ROOT = _get_storage_root()
UPLOAD_FOLDER = os.path.join(_STORAGE_ROOT, "uploads")
RESULTS_FOLDER = os.path.join(_STORAGE_ROOT, "results")
SESSIONS_FOLDER = os.path.join(_STORAGE_ROOT, "sessions")
ALLOWED_EXTENSIONS = {"pdf"}

# =========== Processing ===========
MAX_BATCH_SIZE = 10         # Max resumes to process at once
# NOTE: No API_CALL_DELAY needed — local NLP has no rate limits

# =========== Rate Limiting ===========
RATE_LIMIT_REQUESTS = 5     # Per IP per minute
RATE_LIMIT_WINDOW = 60      # Seconds

# =========== Session ===========
PROGRESS_CLEANUP_HOURS = 1
SESSION_CLEANUP_HOURS = 2

# =========== Deployment ===========
PORT = int(os.getenv("PORT", 5000))
HOST = os.getenv("HOST", "0.0.0.0")


def is_allowed_file(filename: str) -> bool:
    """
    Check if a file extension is allowed.
    
    Args:
        filename (str): The filename to check
        
    Returns:
        bool: True if file extension is in ALLOWED_EXTENSIONS, False otherwise
    """
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def is_production() -> bool:
    """
    Check whether the app is running in production mode.
    
    Returns:
        bool: True if APP_ENV is "production", False otherwise
    """
    return APP_ENV == "production"


# =========== Example .env file content ===========
# Create a .env file in the project root with this content:
#
# # ResumRank AI Configuration
# APP_ENV=production
# SECRET_KEY=your-random-secret-key-here
# PORT=5000
