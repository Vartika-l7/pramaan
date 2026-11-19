"""Configuration module for PRAMAAN."""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = BASE_DIR / "backend"
APP_DIR = BACKEND_DIR / "app"
CASE_DATA_DIR = BACKEND_DIR / "case_data"
EVIDENCE_STORE_DIR = BACKEND_DIR / "evidence_store"
KEYS_DIR = BACKEND_DIR / "keys"

# Ensure runtime directories exist
CASE_DATA_DIR.mkdir(parents=True, exist_ok=True)
EVIDENCE_STORE_DIR.mkdir(parents=True, exist_ok=True)
KEYS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_CASE_ID = os.getenv("DEFAULT_CASE_ID", "PRM-2026-0042")
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "Asia/Kolkata")
MAX_UPLOAD_SIZE_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(1024 * 1024 * 500)))  # Default 500MB limit

# AI / Ollama configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "llama3.2")
CHALLENGER_MODEL = os.getenv("CHALLENGER_MODEL", "mistral")
USE_INDIC_NER = os.getenv("USE_INDIC_NER", "0") == "1"

# Forensic thresholds
CHAT_GAP_MINUTES_MIN = int(os.getenv("CHAT_GAP_MINUTES_MIN", "120"))  # 2 hours
MULE_FUNNEL_WINDOW_HOURS = int(os.getenv("MULE_FUNNEL_WINDOW_HOURS", "24"))
MULE_FORWARD_RATIO_MIN = float(os.getenv("MULE_FORWARD_RATIO_MIN", "0.75"))
ELA_HOTSPOT_THRESHOLD = float(os.getenv("ELA_HOTSPOT_THRESHOLD", "0.08"))
PHASH_MAX_DISTANCE = int(os.getenv("PHASH_MAX_DISTANCE", "5"))

