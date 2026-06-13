"""Shared configuration for Hands-on #1.

Everything that the legacy app, the worker, and the orchestrator all need to
agree on lives here so we can tune the demo from one place (e.g. flip the
timeout off, change the target quarter, point at a different host).

Values come from environment variables when set; otherwise sensible defaults
kick in so a fresh checkout works without a .env file.
"""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass  # python-dotenv is optional; env vars from the shell still work


ROOT = Path(__file__).resolve().parent

# --- LegacyForms web app ------------------------------------------------------
LEGACY_HOST: str = os.environ.get("LEGACY_HOST", "127.0.0.1")
LEGACY_PORT: int = int(os.environ.get("LEGACY_PORT", "5000"))
BASE_URL: str = f"http://{LEGACY_HOST}:{LEGACY_PORT}"

# The one credential pair the agent is given. Treat as a scoped service account.
USERNAME: str = os.environ.get("LEGACY_USER", "analyst")
PASSWORD: str = os.environ.get("LEGACY_PASS", "legacy123")

# Inject one "Session Timeout" after this many session-protected requests.
# Default 3 lands the timeout on the Export click (login -> manifests -> query -> export).
# Set to 0 to disable the disruption entirely.
TIMEOUT_AFTER: int = int(os.environ.get("LEGACY_TIMEOUT_AFTER", "3"))

# A secret key for Flask sessions. Demo-only; do NOT reuse in real apps.
FLASK_SECRET: str = os.environ.get("FLASK_SECRET", "legacy-forms-demo-secret")

# --- The migration goal -------------------------------------------------------
TARGET_QUARTER: str = os.environ.get("TARGET_QUARTER", "Q3")
SUPPORTED_QUARTERS: tuple[str, ...] = ("Q1", "Q2", "Q3", "Q4")

# --- Paths --------------------------------------------------------------------
DATA_FILE: Path = ROOT / "legacy_app" / "data" / "manifests.csv"
CHECKPOINT_FILE: Path = ROOT / "checkpoints" / "state.json"
OUTPUT_DIR: Path = ROOT / "output"
DOWNLOAD_DIR: Path = OUTPUT_DIR / "downloads"
NORMALIZED_FILE: Path = OUTPUT_DIR / "manifests_23ai.csv"
RECONCILIATION_FILE: Path = OUTPUT_DIR / "reconciliation.txt"

# --- New (Oracle 23ai) target schema -----------------------------------------
# Legacy column name (the 8.3-ish style) -> new canonical column.
# This is the contract the Coder step transforms against.
SCHEMA_MAP: dict[str, str] = {
    "MANIFEST_NO": "manifest_id",
    "SHIP_DT": "ship_date",       # DD-MON-YY  ->  ISO YYYY-MM-DD
    "SUPP_CD": "supplier_code",
    "ITEM": "item_sku",
    "QTY": "quantity",
    "UOM": "unit",
    "AMT": "amount_usd",
}

# Columns that must be coerced from text to numeric in the new schema.
NUMERIC_COLUMNS: tuple[str, ...] = ("quantity", "amount_usd")

# Worker safety net: how many decide->act cycles a single worker invocation
# may take before we bail out. Prevents runaway loops if the policy is wrong.
MAX_WORKER_STEPS: int = int(os.environ.get("MAX_WORKER_STEPS", "30"))

# Orchestrator safety net: cap on how many EXTRACT retries we attempt.
MAX_EXTRACT_RETRIES: int = int(os.environ.get("MAX_EXTRACT_RETRIES", "3"))

# --- Anthropic / Live mode ----------------------------------------------------
ANTHROPIC_API_KEY: str | None = os.environ.get("ANTHROPIC_API_KEY") or None
LIVE_MODEL: str = os.environ.get("LIVE_MODEL", "claude-sonnet-4-6")


def ensure_dirs() -> None:
    """Create the runtime directories if they don't exist."""
    for d in (CHECKPOINT_FILE.parent, OUTPUT_DIR, DOWNLOAD_DIR):
        d.mkdir(parents=True, exist_ok=True)
