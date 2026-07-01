"""Central configuration for VisionIQ.

Keeping constants in one module prevents hard-coded values from spreading
across UI, database, and service layers. The values here are intentionally
simple Python constants so Streamlit can reload them predictably.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load local environment variables before reading optional API defaults.
load_dotenv()

# Resolve paths from the VisionIQ project root, not from the process working
# directory. This keeps database and generated file paths stable.
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "visioniq.db"

APP_NAME = "VisionIQ"
APP_TAGLINE = "Batch Multiple-Choice Extraction"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_KEYS_URL = "https://console.groq.com/keys"
MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct"

MAX_IMAGES = 30
DELAY_SECONDS = 3

# Default Groq on-demand limits used for the UI usage monitor. Keeping them in
# config makes the dashboard easy to update if account limits change.
RPM_LIMIT = 30
RPD_LIMIT = 1000
TPM_LIMIT = 30000
TPD_LIMIT = 500000

DEFAULT_PDF_NAME = "VisionIQ_Extracted_Questions"
PDF_THEMES = ["Light", "Dark"]
