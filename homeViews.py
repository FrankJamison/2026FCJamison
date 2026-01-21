import csv
import os
import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Optional, Tuple

from flask import abort, jsonify, redirect, render_template, request, url_for

from __init__ import app


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


@app.get("/projects/<project_slug>")
@app.get("/projects/<project_slug>/")
def project_index(project_slug: str):
    project_slug = _clean(project_slug, max_len=200)
    if not project_slug or not all(ch.isalnum() or ch in {"-", "_"} for ch in project_slug):
        abort(404)

    # If a static build exists locally, prefer it.
    static_root = Path(app.static_folder or "static")
    local_index = static_root / "portfolio" / project_slug / "index.html"
    if local_index.exists():
        return redirect(url_for("static", filename=f"portfolio/{project_slug}/index.html"))

    hosted = {
        "2026SpacePortfolio": "https://spaceportfolio.fcjamison.com/",
        "2026HackerNews": "https://hackernews.fcjamison.com/",
        "2025PasswordCheck": "https://passwordcheck.fcjamison.com/",
        "2020CharacterVault": "https://charactervault.fcjamison.com/",
        "2018Questkeeper": "https://questkeeper.fcjamison.com/",
        "2018FrankJamison": "https://frankjamison2018.fcjamison.com/",
        "2018FranksClassicCars": "https://classiccars.fcjamison.com/",
        "2007GlobeBank": "https://globebank.fcjamison.com/",
    }
    if project_slug in hosted:
        return redirect(hosted[project_slug])

    # Minimal fallback: project repos follow the slug name.
    github_org = _clean(os.getenv("GITHUB_ORG"), max_len=100) or "FrankJamison"
    return redirect(f"https://github.com/{github_org}/{project_slug}")


@app.post("/leave-reply")
def leave_reply():
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

    _append_csv(
        Path("data/leave_reply.csv"),
        headers=["timestamp", "name", "email", "website", "blog_title", "page_url", "comment"],
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

    ok, err = _send_email(subject=subject, body=body, reply_to=email)
    if not ok:
        return jsonify({"ok": False, "error": err})

    return jsonify({"ok": True})


@app.post("/contact")
def contact_message():
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

    _append_csv(
        Path("data/contact_messages.csv"),
        headers=["timestamp", "name", "email", "phone", "subject", "page_url", "message"],
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

    ok, err = _send_email(subject=mail_subject, body=body, reply_to=email)
    if not ok:
        return jsonify({"ok": False, "error": err})

    return jsonify({"ok": True})
