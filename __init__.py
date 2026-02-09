import os
from datetime import datetime
from pathlib import Path

from flask import Flask

# ****************************
# Load .env in local/dev; production should rely on host-provided env vars.
# ****************************
try:
    from dotenv import load_dotenv

    env_name = (os.getenv("FLASK_ENV") or os.getenv(
        "ENV") or "").strip().lower()
    if env_name != "production" and Path(".env").exists():
        # ****************************
        # Prefer the repo's .env to avoid stale system env vars in dev.
        # ****************************
        load_dotenv(override=True)
except Exception:
    pass


app = Flask(__name__)


@app.context_processor
def inject_current_year():
    return {
        "current_year": datetime.now().year,
    }


# ****************************
# Register routes so `flask run` sees them without executing app.py.
# ****************************
import homeViews  # noqa: E402,F401
