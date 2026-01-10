# 2026FCJamison — Flask Portfolio Site

Personal portfolio site built with **Flask + Jinja2** and a modern front-end theme. It includes a portfolio section, blog UI, and two working email-backed forms.

## Highlights

- **Flask-friendly links**: templates use `url_for(...)` for internal navigation and static assets.
- **Portfolio modals that actually navigate**: “View Project” links work reliably even with slider/modal scripts.
- **Email-backed forms**:
  - Blog “Leave a Reply” sends an email notification (AJAX POST).
  - Contact form sends an email (AJAX POST).
- **Production-ready entrypoint**: includes `wsgi.py` for WSGI servers.

## Tech stack

- Python / Flask
- Jinja2 templates
- Bootstrap + jQuery
- Slick carousel
- SMTP via Python `smtplib`

## Project structure

- `app.py` — local/dev entrypoint
- `wsgi.py` — WSGI entrypoint (`application`)
- `homeViews.py` — routes + SMTP email logic
- `templates/` — site templates + partials
- `static/` — CSS/JS/images/fonts

## Run locally

### Using VS Code tasks (Windows)

This repo includes VS Code tasks for setting up a venv and starting the app.

### GlobeBank (PHP project)

GlobeBank is a PHP app, but this repo will run it from the Flask site by automatically starting a local PHP server and reverse-proxying it.

- Open `http://2026fcjamison.localhost:5000/projects/2007GlobeBank/`
- Requires PHP installed (recommended: `winget install -e --id PHP.PHP.8.4`)

Optional (manual PHP server):

- Run the VS Code task `PHP: Run GlobeBank (dev server :8007)`
- Open `http://2026fcjamison.localhost:8007/`

Or run the combined task `Dev: Flask + GlobeBank PHP + Open`.

### Manual

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Then open the URL printed in the console (default is `http://127.0.0.1:5000/`).

## Configuration

### Flask

- `HOST` (default: `127.0.0.1`)
- `PORT` (default: `5000`)
- `FLASK_DEBUG` (`1`/`0`)

### SMTP

See [SMTP_SETUP.md](SMTP_SETUP.md) for the full list and examples. The app uses SMTP for:

- `POST /leave-reply`
- `POST /contact`

## Deployment notes

- `wsgi.py` is provided for production WSGI servers.
- If you deploy behind Apache as a reverse proxy, the upstream WSGI server (e.g., Waitress) typically listens on localhost.

If you’re using the included production notes, see [PRODUCTION_SETUP.md](PRODUCTION_SETUP.md).
