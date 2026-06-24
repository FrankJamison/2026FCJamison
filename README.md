# FCJamison.com — Flask Portfolio Site

Live site: https://www.fcjamison.com

Developer-focused Flask + Jinja2 portfolio site. The homepage is server-rendered, static assets live under `static/`, and the Contact / Blog Reply forms submit via AJAX and send notification email via SMTP.

## Quick start (local development)

1. Create a virtual environment and install dependencies (see **Manual setup** below).
2. Start the app with `python app.py`.
3. Open `http://127.0.0.1:5000/` in your browser.

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

Then open http://127.0.0.1:5000/.

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

### Analytics (events + admin)

Analytics endpoints:

- `POST /analytics/event` (ingest)
- `GET /analytics/summary?days=30` (JSON metrics)

Protected admin:

- `GET /analytics/admin?token=...&days=30`
- `GET /analytics/prune?token=...`
- `GET /analytics/export.csv?token=...&days=30` (daily aggregates)
- `GET /analytics/export-raw.csv?token=...&days=30` (raw events)
- `GET /analytics/export-bundle.zip?token=...&days=30` (aggregate + raw CSV in one zip)

Bundle contents:

- `README.txt` (generation timestamp, day window, and file/column notes)
- `analytics-<days>d.csv`
- `analytics-raw-<days>d.csv`

Analytics environment variables:

- `ANALYTICS_EVENTS_PATH` (default: `data/analytics_events.csv`)
- `ANALYTICS_RETENTION_DAYS` (default: `180`, min `7`, max `3650`)
- `ANALYTICS_MAX_ROWS` (default: `200000`, min `1000`)
- `ANALYTICS_PRUNE_MIN_INTERVAL_SEC` (default: `900`)
- `ANALYTICS_ADMIN_TOKEN` (required to enable `/analytics/admin` and `/analytics/prune`)

Notes:

- Unknown events and probable bot/noise requests are ignored at ingest.
- Pruning runs automatically during event ingest and can be triggered manually from the admin route.

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

## Accessibility / WCAG

This project is intended to be WCAG-aligned (target: WCAG 2.2 AA). For a repeatable checklist (automated + manual verification), see [ACCESSIBILITY.md](ACCESSIBILITY.md).

Quick regression check:

```bash
python3 tools/a11y_sanity_check.py
```

## Image optimization (portfolio WebP)

### Current strategy

The portfolio section uses **WebP-only images** for all 50+ project thumbnails and featured project cards. All PNG source files have been deleted from `static/images/portfolio/`, and only `.webp` files remain. This approach:

- Reduces disk space by ~50% per image (PNG → WebP compression)
- Eliminates browser fallback logic, simplifying template code
- Targets modern browsers only (all major browsers support WebP as of 2024)

**Browser support:** WebP is supported in Chrome, Edge, Firefox, Safari 16+, and modern mobile browsers. Older browsers (IE 11, pre-2018 Safari, older Android) will not display portfolio images.

### Templates updated

The following templates reference portfolio images exclusively via WebP:

- `templates/partials/portfolioBody.html` — all 45 project modals
- `templates/partials/portfolioCard.html` — grid card macro
- `templates/partials/featuredProjects.html` — featured project cards (6 featured projects)

All `src` and `srcset` attributes now reference `.webp` files only.

### Historical: Image conversion

If regenerating WebP files from source images is ever needed:

```bash
python3 tools/convert_portfolio_images_to_webp.py
```

This tool generates `.webp` sibling files from any source images present. (Currently archived for reference; not actively used after PNG-only migration.)

## Challenges and Improvements

### Migration to WebP-only (June 2026)

**Objective:** Delete all redundant PNG files from `static/images/portfolio/` and update templates to reference WebP exclusively, reducing storage and simplifying image handling logic.

**Challenges encountered:**

1. **Template caching during development** — After updating 45+ image references in `portfolioBody.html`, the Flask development server continued serving old template output. Templates are cached in Flask's Jinja2 engine; simply reloading the browser cache wasn't sufficient. **Solution:** Restart the Flask dev server (`FLASK_DEBUG=1` doesn't auto-reload Jinja2 template changes in all cases).

2. **Large batch replacements** — Replacing 45+ nearly-identical lines across multiple files risked syntax errors or missed items. **Solution:** Broke replacements into 5 sequential batches (covering items 045→001) with explicit verification between batches to ensure accuracy.

3. **Multiple template contexts** — Portfolio images appear in three separate template contexts:
   - Modal detail views (`portfolioBody.html`)
   - Grid cards (`portfolioCard.html`)
   - Featured project showcase (`featuredProjects.html`)

   Each context had different markup patterns (direct `src`, picture/srcset, macro parameters), requiring context-aware search-and-replace strategies.

4. **Distinguishing portfolio vs. blog images** — The blog folder (`static/images/blog/`) contains PNG-only images with no WebP equivalents (intentional for blog authoring flexibility). During cleanup, it was critical not to accidentally delete or convert blog images. **Solution:** Worked exclusively in the portfolio folder with explicit file paths.

5. **Terminal-based regex challenges in WSL** — Initial attempts to use `sed` commands in WSL via terminal tools produced inconsistent results. **Solution:** Shifted to file-based tools (multi_replace_string_in_file) which proved more reliable for batch operations.

### Lessons learned & recommendations

1. **Plan template changes holistically** — When updating many similar references across multiple templates, map out all contexts first (search for all uses) before implementing changes.

2. **Verify file existence before deletion** — Before committing to deletion of 50 files, explicitly confirm that WebP equivalents exist for all items.

3. **Monitor resource loading** — After template updates, use browser DevTools or Playwright's network inspection to confirm all expected resources load (no 404s).

4. **Document image strategy** — Clearly state in README which folders use which formats (portfolio = WebP-only, blog = PNG-only) to prevent confusion during future maintenance.

5. **Batch operations efficiency** — For large-scale replacements, the multi_replace_string_in_file tool with 5–17 replacements per batch proved faster and more reliable than terminal-based regex or sequential single-file edits.

### Future improvements

1. **Lazy-loaded image placeholders** — Implement blur-up or LQIP (Low Quality Image Placeholders) for portfolio images to improve perceived performance while WebP files load.

2. **Responsive image variants** — Generate smaller WebP variants for mobile screens (e.g., 320px, 640px) to reduce bandwidth and load times.

3. **Automated image validation in CI/CD** — Add a pre-commit or pre-deploy check that verifies all template image references correspond to actual files on disk, catching broken references early.

4. **Image metadata tagging** — Extend the portfolio schema to include dimensions, alt-text consistency checks, and a manifest file listing all expected images.

5. **Progressive enhancement for unsupported browsers** — If future requirements demand support for older browsers, add a server-side image format negotiation header (`Accept: image/webp`) and serve PNG fallbacks dynamically.
