import os
from pathlib import Path
from dotenv import load_dotenv

# Load local .env file if available
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Candidate Profile Settings
CANDIDATE_NAME = "Saurao Dalvi"
CANDIDATE_EMAIL = "sauraodalvi97@gmail.com"
CANDIDATE_TITLE = "AI Product Manager / Associate Product Manager"

_local_resume = Path(__file__).parent / "Saurao_Dalvi_Resume.pdf"
CANDIDATE_RESUME_PATH = os.getenv(
    "CANDIDATE_RESUME_PATH",
    str(_local_resume if _local_resume.exists() else Path(r"C:\Users\Saurao\Downloads\Resume\Compact\Saurao Dalvi.pdf"))
)

CANDIDATE_LINKEDIN = "https://www.linkedin.com/in/saurao-dalvi/"
CANDIDATE_PORTFOLIO = "https://sauraodalvi.netlify.app/"

# Targeted Roles & Locations
TARGET_ROLES = ["Product Manager", "Associate Product Manager", "APM", "AI Product Manager"]
TARGET_LOCATIONS = ["Pune", "European Union", "EU", "Germany", "Netherlands", "Japan", "Singapore", "Indonesia", "Remote"]

# Blacklisted Companies (Never apply or send outreach)
BLACKLIST_COMPANIES = ["FlytBase", "Flytbase"]

# API Keys & Auth Credentials
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")
EMAIL_USER = os.getenv("EMAIL_USER", CANDIDATE_EMAIL)
EMAIL_PASS = os.getenv("EMAIL_PASS", "")

# Server Settings
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

# Model Configuration
LLM_MODEL = os.getenv("LLM_MODEL", "openrouter/google/gemma-4-31b-it:free")

# Logic Parameters
DAYS_BETWEEN_FOLLOWUP = int(os.getenv("DAYS_BETWEEN_FOLLOWUP", "3"))
MAX_FOLLOWUPS = int(os.getenv("MAX_FOLLOWUPS", "2"))
MAX_DAILY_PITCHES = int(os.getenv("MAX_DAILY_PITCHES", "5"))
MAX_JOB_AGE_DAYS = int(os.getenv("MAX_JOB_AGE_DAYS", "7"))

# Database path
TRACKER_FILE = Path(__file__).parent / "tracker.json"
