import os
from datetime import datetime
from pathlib import Path

from flask import Flask

# Load environment variables from .env for local development.
# In production, real environment variables should be set by the host.
try:
    from dotenv import load_dotenv

    env_name = (os.getenv("FLASK_ENV") or os.getenv(
        "ENV") or "").strip().lower()
    if env_name != "production" and Path(".env").exists():
        # In dev, it's common to have stale system env vars; prefer the repo's .env.
        load_dotenv(override=True)
except Exception:
    pass


app = Flask(__name__)


def _globebank_url() -> str:
    url_override = (os.getenv("GLOBEBANK_URL") or "").strip()
    if url_override:
        return url_override

    # In production, prefer the dedicated subdomain.
    env_name = (os.getenv("FLASK_ENV") or os.getenv(
        "ENV") or "").strip().lower()
    if env_name == "production":
        return "https://globebank.fcjamison.com/"

    # In dev, default to the public HTTPS site (override with GLOBEBANK_URL
    # if you want to use the Flask-mounted dev proxy instead).
    return "https://globebank.fcjamison.com/"


@app.context_processor
def inject_current_year():
    return {
        "current_year": datetime.now().year,
        "globebank_url": _globebank_url(),
    }
