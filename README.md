# FCJamison.com — Flask Portfolio Site

Live site: https://www.fcjamison.com

Developer-focused Flask + Jinja2 portfolio site. The homepage is server-rendered, static assets live under `static/`, and the Contact / Blog Reply forms submit via AJAX and send notification email via SMTP.

## Quick start (Windows + VS Code)

1. Ensure you have a local venv with deps installed (see **Manual setup** below).

2. Run the VS Code task `Dev: Flask + Open Browser`

- Starts the dev server (`Flask: Run (dev server)`) and opens the browser

3. Open:

- http://fcjamison.comv2026.localhost:5000/

Note: `*.localhost` typically resolves to `127.0.0.1` without editing hosts files.

## Manual setup

### Prereqs

- Python 3.x

### Create venv + install deps

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Run the app

```powershell
$env:FLASK_DEBUG='1'
$env:HOST='127.0.0.1'
$env:PORT='5000'
& .\.venv\Scripts\python.exe .\app.py
```

Then open http://127.0.0.1:5000/ (or http://fcjamison.comv2026.localhost:5000/).

## Configuration

### `.env` (local/dev)

Local development supports a repo-root `.env` file (loaded by `python-dotenv`) as long as you are not in production mode (`ENV`/`FLASK_ENV` != `production`).

### Flask

- `HOST` (default: `127.0.0.1`)
- `PORT` (default: `5000`)
- `FLASK_DEBUG` (`1`/`0`)

### SEO / multi-site

These settings let you reuse the same codebase across multiple sites by configuring branding/metadata via env vars (no template edits required).

- `SITE_URL` (recommended in production) — absolute public root URL like `https://example.com` (used for sitemap/robots when behind a proxy).
- `SITE_NAME` — site name (used for OpenGraph + JSON-LD).
- `SITE_OWNER_NAME` — author/owner name.
- `SITE_OWNER_EMAIL` — optional (used in JSON-LD as `mailto:`).
- `SITE_DEFAULT_TITLE` — default `<title>` when a page doesn’t override `headTitle`.
- `SITE_TITLE_SUFFIX` — appended to the title (set to empty to disable).
- `SITE_DEFAULT_DESCRIPTION` — default meta description when a page doesn’t override `headDescription`.
- `SITE_LOGO_PATH` — static path for logo (relative to `static/`), default `images/logo/logo.png`.
- `SITE_OG_IMAGE_URL` — optional absolute URL to use for `og:image`/`twitter:image`.
- `SITE_TWITTER_HANDLE` — optional, `@handle`.

Sitemap controls:

- `SITEMAP_INCLUDE_PROJECTS` — `1`/`0` (default: `1`).
- `SITEMAP_PATHS` — extra on-site paths to include (comma or newline separated), e.g. `/about,/contact`.
- `SITEMAP_URLS` — extra absolute URLs to include (comma or newline separated).

### SMTP (required for forms)

Forms:

- `POST /contact`
- `POST /leave-reply`

SMTP env vars are documented in [SMTP_SETUP.md](SMTP_SETUP.md). The important ones are:

- `SMTP_HOST`, `SMTP_PORT`
- `SMTP_USER`, `SMTP_PASSWORD`
- `SMTP_FROM`, `SMTP_TO` (defaults to `SMTP_USER`)
- `SMTP_USE_SSL` (default: `1`) / `SMTP_USE_TLS` (default: `0`)

## Project layout

- `__init__.py` — creates the Flask app and loads `.env` in dev
- `app.py` — dev entrypoint (`app.run(...)`)
- `homeViews.py` — routes, validation, CSV persistence, SMTP send
- `wsgi.py` — production WSGI entrypoint (`application`)
- `templates/` — Jinja templates (pages + partials)
- `static/` — CSS/JS/images/fonts + portfolio archives under `static/portfolio/`

## Routes & behavior

### Home

- `GET /` renders `templates/home/index.html`

### Projects

- `GET /projects/<project_slug>`

Resolution order:

1. If `static/portfolio/<project_slug>/index.html` exists, the app redirects to that static file.
2. Otherwise, if the slug is a known hosted project (see the `hosted = {...}` map in `homeViews.py`), it redirects to the corresponding `*.fcjamison.com` URL.
3. Otherwise it redirects to `https://github.com/<GITHUB_ORG>/<project_slug>` (default `GITHUB_ORG=FrankJamison`).

### Contact / Leave Reply

- Both endpoints persist submissions to `data/*.csv` and attempt to send a notification email.
- Both endpoints include a simple honeypot field (`hp`) for bot reduction.

## Production

- Install production deps from `requirements-prod.txt`.
- Prefer running behind a reverse proxy (Nginx/Apache) with a real WSGI server (Gunicorn/etc).
- This repo includes a Linux-oriented walkthrough in [PRODUCTION_SETUP.md](PRODUCTION_SETUP.md).

Example (Gunicorn):

```bash
gunicorn --workers 2 --bind 127.0.0.1:8000 wsgi:application
```

Note: `/contact` and `/leave-reply` write CSV files under `data/`, so ensure the process user can write to that directory in production.

## Troubleshooting

- **Forms return `{ ok: false }`**: SMTP env vars are missing or failing; see [SMTP_SETUP.md](SMTP_SETUP.md) and check server logs.
- **TLS/cert errors locally**: some antivirus tools intercept SMTP TLS; `SMTP_ALLOW_INVALID_CERT=1` is available for dev only.
