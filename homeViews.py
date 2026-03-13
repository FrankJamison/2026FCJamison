import csv
import os
import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urljoin

from flask import Response, abort, jsonify, redirect, render_template, request, url_for

from __init__ import app


PROJECT_HOSTED = {
    "2026SpacePortfolio": "https://spaceportfolio.fcjamison.com/",
    "2026HackerNews": "https://hackernews.fcjamison.com/",
    "2025PasswordCheck": "https://passwordcheck.fcjamison.com/",
    "2020CharacterVault": "https://charactervault.fcjamison.com/",
    "2018Questkeeper": "https://questkeeper.fcjamison.com/",
    "2018FrankJamison": "https://frankjamison2018.fcjamison.com/",
    "2018FranksClassicCars": "https://classiccars.fcjamison.com/",
    "2007GlobeBank": "https://globebank.fcjamison.com/",
}


def _get_local_portfolio_slugs() -> list[str]:
    static_root = Path(app.static_folder or "static")
    portfolio_root = static_root / "portfolio"
    if not portfolio_root.exists() or not portfolio_root.is_dir():
        return []

    slugs: list[str] = []
    for child in portfolio_root.iterdir():
        if not child.is_dir():
            continue
        if (child / "index.html").exists():
            slugs.append(child.name)
    return sorted(set(slugs))


def _site_url_root() -> str:
    configured = (os.getenv("SITE_URL") or "").strip()
    if configured:
        return configured.rstrip("/") + "/"
    return request.url_root


def _parse_env_list(name: str) -> list[str]:
    raw = os.getenv(name)
    if not raw:
        return []
    parts: list[str] = []
    for line in raw.replace(",", "\n").splitlines():
        item = line.strip()
        if not item:
            continue
        parts.append(item)
    return parts


def _truthy_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _clean(value: Optional[str], *, max_len: int = 5000) -> str:
    if value is None:
        return ""
    value = str(value).strip()
    if len(value) > max_len:
        value = value[:max_len]
    return value


def _append_csv(path: Path, headers: list[str], row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists()

    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if not file_exists:
            writer.writeheader()
        writer.writerow({h: row.get(h, "") for h in headers})


def _smtp_context() -> ssl.SSLContext:
    allow_invalid = _truthy_env("SMTP_ALLOW_INVALID_CERT", False)
    ca_file = _clean(os.getenv("SMTP_CA_FILE"), max_len=2000)

    if allow_invalid:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    if ca_file:
        return ssl.create_default_context(cafile=ca_file)

    return ssl.create_default_context()


def _send_email(*, subject: str, body: str, reply_to: Optional[str] = None) -> Tuple[bool, str]:
    host = _clean(os.getenv("SMTP_HOST"), max_len=255)
    port_raw = _clean(os.getenv("SMTP_PORT"), max_len=20) or "465"
    user = _clean(os.getenv("SMTP_USER"), max_len=255)
    password = os.getenv("SMTP_PASSWORD") or ""

    from_addr = _clean(os.getenv("SMTP_FROM"), max_len=255) or user
    to_addr = _clean(os.getenv("SMTP_TO"), max_len=255) or user

    use_ssl = _truthy_env("SMTP_USE_SSL", True)
    use_tls = _truthy_env("SMTP_USE_TLS", False)

    if not host or not to_addr or not from_addr:
        return False, "Email is not configured (missing SMTP_HOST/SMTP_FROM/SMTP_TO)."

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(body)

    try:
        port = int(port_raw)
    except ValueError:
        return False, "Email is misconfigured (SMTP_PORT must be a number)."

    ctx = _smtp_context()

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, context=ctx, timeout=20) as server:
                if user:
                    server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=20) as server:
                server.ehlo()
                if use_tls:
                    server.starttls(context=ctx)
                    server.ehlo()
                if user:
                    server.login(user, password)
                server.send_message(msg)
        return True, ""
    except Exception as e:
        return False, f"Email send failed: {e}"


@app.get("/")
def index():
    return render_template("home/index.html")


@app.get("/robots.txt")
def robots_txt():
    site_root = _site_url_root().rstrip("/")
    body = "\n".join(
        [
            "User-agent: *",
            "Disallow:",
            f"Sitemap: {site_root}/sitemap.xml",
            "",
        ]
    )
    return Response(body, mimetype="text/plain")


@app.get("/sitemap.xml")
def sitemap_xml():
    today = datetime.now(timezone.utc).date().isoformat()
    urls: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add_url(loc: str) -> None:
        loc = (loc or "").strip()
        if not loc or loc in seen:
            return
        seen.add(loc)
        urls.append((loc, today))

    add_url(url_for("index", _external=True))

    for path in _parse_env_list("SITEMAP_PATHS"):
        if path.startswith("http://") or path.startswith("https://"):
            add_url(path)
            continue
        normalized = path if path.startswith("/") else f"/{path}"
        add_url(urljoin(_site_url_root(), normalized.lstrip("/")))

    for abs_url in _parse_env_list("SITEMAP_URLS"):
        add_url(abs_url)

    include_projects = _truthy_env("SITEMAP_INCLUDE_PROJECTS", True)
    if include_projects:
        project_slugs = sorted(set(PROJECT_HOSTED.keys())
                               | set(_get_local_portfolio_slugs()))
        for slug in project_slugs:
            add_url(url_for("project_index", project_slug=slug, _external=True))

    lines: list[str] = [
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
        "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">",
    ]
    for loc, lastmod in urls:
        lines.extend(
            [
                "  <url>",
                f"    <loc>{loc}</loc>",
                f"    <lastmod>{lastmod}</lastmod>",
                "  </url>",
            ]
        )
    lines.append("</urlset>")

    return Response("\n".join(lines) + "\n", mimetype="application/xml")


@app.get("/projects/<project_slug>")
@app.get("/projects/<project_slug>/")
def project_index(project_slug: str):
    project_slug = _clean(project_slug, max_len=200)
    if not project_slug or not all(ch.isalnum() or ch in {"-", "_"} for ch in project_slug):
        abort(404)

    # ****************************
    # If a static build exists locally, prefer it.
    # ****************************
    static_root = Path(app.static_folder or "static")
    local_index = static_root / "portfolio" / project_slug / "index.html"
    if local_index.exists():
        return redirect(url_for("static", filename=f"portfolio/{project_slug}/index.html"))

    if project_slug in PROJECT_HOSTED:
        return redirect(PROJECT_HOSTED[project_slug])

    # ****************************
    # Minimal fallback: project repos follow the slug name.
    # ****************************
    github_org = _clean(os.getenv("GITHUB_ORG"), max_len=100) or "FrankJamison"
    return redirect(f"https://github.com/{github_org}/{project_slug}")


@app.post("/leave-reply")
def leave_reply():
    # ****************************
    # Honeypot field: if filled, treat as bot submission.
    # ****************************
    hp = _clean(request.form.get("hp"), max_len=200)
    if hp:
        return jsonify({"ok": True})

    name = _clean(request.form.get("name"), max_len=200)
    email = _clean(request.form.get("email"), max_len=254)
    website = _clean(request.form.get("website"), max_len=500)
    comment = _clean(request.form.get("comment"), max_len=5000)
    blog_title = _clean(request.form.get("blog_title"), max_len=300)
    page_url = _clean(request.form.get("page_url"), max_len=2000)

    if not name or not email or not comment:
        return jsonify({"ok": False, "error": "Name, email, and comment are required."})

    now = datetime.now(timezone.utc).isoformat()

    # ****************************
    # Persist submissions locally for quick review/backup.
    # ****************************
    _append_csv(
        Path("data/leave_reply.csv"),
        headers=["timestamp", "name", "email", "website",
                 "blog_title", "page_url", "comment"],
        row={
            "timestamp": now,
            "name": name,
            "email": email,
            "website": website,
            "blog_title": blog_title,
            "page_url": page_url,
            "comment": comment,
        },
    )

    subject = f"Portfolio blog reply: {blog_title or 'Leave a Reply'}"
    body = "\n".join(
        [
            "New blog reply submitted:",
            f"Time (UTC): {now}",
            f"Name: {name}",
            f"Email: {email}",
            f"Website: {website}",
            f"Blog title: {blog_title}",
            f"Page: {page_url}",
            "",
            "Comment:",
            comment,
        ]
    )

    # ****************************
    # Send notification email with Reply-To set to the visitor.
    # ****************************
    ok, err = _send_email(subject=subject, body=body, reply_to=email)
    if not ok:
        return jsonify({"ok": False, "error": err})

    return jsonify({"ok": True})


@app.post("/contact")
def contact_message():
    # ****************************
    # Honeypot field: if filled, treat as bot submission.
    # ****************************
    hp = _clean(request.form.get("hp"), max_len=200)
    if hp:
        return jsonify({"ok": True})

    name = _clean(request.form.get("name"), max_len=200)
    phone = _clean(request.form.get("phone"), max_len=50)
    email = _clean(request.form.get("email"), max_len=254)
    subject = _clean(request.form.get("subject"), max_len=300)
    message = _clean(request.form.get("message"), max_len=8000)
    page_url = _clean(request.form.get("page_url"), max_len=2000)

    if not name or not email or not subject or not message:
        return jsonify({"ok": False, "error": "Name, email, subject, and message are required."})

    now = datetime.now(timezone.utc).isoformat()

    # ****************************
    # Persist submissions locally for quick review/backup.
    # ****************************
    _append_csv(
        Path("data/contact_messages.csv"),
        headers=["timestamp", "name", "email",
                 "phone", "subject", "page_url", "message"],
        row={
            "timestamp": now,
            "name": name,
            "email": email,
            "phone": phone,
            "subject": subject,
            "page_url": page_url,
            "message": message,
        },
    )

    mail_subject = f"Portfolio contact: {subject}"
    body = "\n".join(
        [
            "New contact message submitted:",
            f"Time (UTC): {now}",
            f"Name: {name}",
            f"Email: {email}",
            f"Phone: {phone}",
            f"Page: {page_url}",
            "",
            "Message:",
            message,
        ]
    )

    # ****************************
    # Send notification email with Reply-To set to the visitor.
    # ****************************
    ok, err = _send_email(subject=mail_subject, body=body, reply_to=email)
    if not ok:
        return jsonify({"ok": False, "error": err})

    return jsonify({"ok": True})
