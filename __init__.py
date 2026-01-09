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


@app.context_processor
def inject_current_year():
    return {"current_year": datetime.now().year}
