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


def _env_str(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None:
        return default
    value = str(value).strip()
    return value if value else default


# ****************************
# Site/SEO defaults (override per site via env vars).
# ****************************
app.config["SITE_NAME"] = _env_str("SITE_NAME", "FCJamison.com")
app.config["SITE_OWNER_NAME"] = _env_str("SITE_OWNER_NAME", "Frank Jamison")
app.config["SITE_OWNER_EMAIL"] = _env_str(
    "SITE_OWNER_EMAIL", "frank@fcjamison.com")
app.config["SITE_DEFAULT_TITLE"] = _env_str(
    "SITE_DEFAULT_TITLE", app.config["SITE_NAME"])
app.config["SITE_TITLE_SUFFIX"] = _env_str(
    "SITE_TITLE_SUFFIX",
    "Frank Jamison's Professional Portfolio",
)
app.config["SITE_DEFAULT_DESCRIPTION"] = _env_str(
    "SITE_DEFAULT_DESCRIPTION",
    "Frank Jamison — web designer and developer. Portfolio projects, blog posts, and contact.",
)

# Relative to /static
app.config["SITE_LOGO_PATH"] = _env_str(
    "SITE_LOGO_PATH", "images/logo/logo.png")

# Absolute URL override for og/twitter image (optional)
app.config["SITE_OG_IMAGE_URL"] = _env_str("SITE_OG_IMAGE_URL", "")

# Optional, e.g. "@example" or "example"
app.config["SITE_TWITTER_HANDLE"] = _env_str("SITE_TWITTER_HANDLE", "")


@app.context_processor
def inject_current_year():
    return {
        "current_year": datetime.now().year,
    }


@app.context_processor
def inject_site_defaults():
    return {
        "site_name": app.config.get("SITE_NAME", ""),
        "site_owner_name": app.config.get("SITE_OWNER_NAME", ""),
        "site_owner_email": app.config.get("SITE_OWNER_EMAIL", ""),
        "site_default_title": app.config.get("SITE_DEFAULT_TITLE", ""),
        "site_title_suffix": app.config.get("SITE_TITLE_SUFFIX", ""),
        "site_default_description": app.config.get("SITE_DEFAULT_DESCRIPTION", ""),
        "site_logo_path": app.config.get("SITE_LOGO_PATH", ""),
        "site_og_image_url": app.config.get("SITE_OG_IMAGE_URL", ""),
        "site_twitter_handle": app.config.get("SITE_TWITTER_HANDLE", ""),
    }


# ****************************
# Register routes so `flask run` sees them without executing app.py.
# ****************************
import homeViews  # noqa: E402,F401
