import os
import smtplib
import socket
import ssl
from typing import Optional
from email.message import EmailMessage

from flask import abort, jsonify, redirect, render_template, request, send_from_directory, url_for
from app import app


PROJECTS_ROOT = os.path.abspath(
    os.getenv(
        "PROJECTS_ROOT",
        os.path.join(os.path.dirname(__file__), "projects"),
    )
)


def _project_dir(project_slug: str) -> str:
    # Basic traversal hardening.
    if not project_slug or project_slug.startswith("."):
        abort(404)
    if any(sep in project_slug for sep in ("/", "\\")):
        abort(404)

    project_dir = os.path.join(PROJECTS_ROOT, project_slug)
    if not os.path.isdir(project_dir):
        abort(404)
    return project_dir


def _truthy_env(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _peek_tls_leaf_issuer(host: str, port: int) -> Optional[str]:
    """Best-effort helper to identify TLS interception appliances.

    Only used after a TLS verification failure, so it intentionally uses an
    unverified context and reads only the leaf certificate's issuer.
    """
    try:
        addrinfo = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        if not addrinfo:
            return None
        family, _, _, _, sockaddr = addrinfo[0]

        context = ssl._create_unverified_context()
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            sock.settimeout(5)
            sock.connect(sockaddr)
            with context.wrap_socket(sock, server_hostname=host) as tls_sock:
                der = tls_sock.getpeercert(binary_form=True)
                if not der:
                    return None

        pem = ssl.DER_cert_to_PEM_cert(der)
        import os
        import tempfile

        tmp = tempfile.NamedTemporaryFile("w", delete=False, suffix=".pem")
        try:
            tmp.write(pem)
            tmp.close()
            info = ssl._ssl._test_decode_cert(tmp.name)
        finally:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass

        issuer = info.get("issuer")
        return str(issuer) if issuer else None
    except Exception:
        return None


def _send_smtp_email(*, subject: str, body: str, reply_to: Optional[str] = None) -> None:
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587").strip() or "587")
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    smtp_from = os.getenv(
        "SMTP_FROM", "frank@fcjamison.com").strip() or "frank@fcjamison.com"
    smtp_to = os.getenv(
        "SMTP_TO", "frank@fcjamison.com").strip() or "frank@fcjamison.com"

    use_ssl = _truthy_env(os.getenv("SMTP_USE_SSL"))
    use_tls = _truthy_env(os.getenv("SMTP_USE_TLS", "1")) and not use_ssl

    if not smtp_host:
        raise RuntimeError("SMTP_HOST is not set")
    if not smtp_user or not smtp_password:
        raise RuntimeError("SMTP_USER/SMTP_PASSWORD are not set")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = smtp_from
    message["To"] = smtp_to
    if reply_to:
        message["Reply-To"] = reply_to
    message.set_content(body)

    context = ssl.create_default_context()

    ca_file = os.getenv("SMTP_CA_FILE", "").strip()
    if ca_file:
        context.load_verify_locations(cafile=ca_file)

    # Dev-only escape hatch. Do NOT use in production.
    if _truthy_env(os.getenv("SMTP_ALLOW_INVALID_CERT")):
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    if use_ssl:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
            server.login(smtp_user, smtp_password)
            server.send_message(message)
        return

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        if use_tls:
            server.starttls(context=context)
        server.login(smtp_user, smtp_password)
        server.send_message(message)


@app.post('/leave-reply')
def leave_reply():
    # Honeypot: bots often fill hidden fields
    if (request.form.get('hp') or '').strip():
        return jsonify(ok=True)

    name = (request.form.get('name') or '').strip()
    email = (request.form.get('email') or '').strip()
    website = (request.form.get('website') or '').strip()
    comment = (request.form.get('comment') or '').strip()
    blog_title = (request.form.get('blog_title') or '').strip()
    page_url = (request.form.get('page_url') or request.referrer or '').strip()

    if not name or not email or not comment:
        if request.accept_mimetypes.best == 'application/json':
            return jsonify(ok=False, error='Please provide name, email, and a comment.'), 400
        return redirect(request.form.get('next') or request.referrer or url_for('index'))

    if blog_title:
        subject = f"FCJamison Blog Reply: {blog_title} — {name}"
    else:
        subject = f"FCJamison Blog Reply from {name}"
    body_lines = [
        f"Name: {name}",
        f"Email: {email}",
    ]
    if blog_title:
        body_lines.append(f"Blog: {blog_title}")
    if website:
        body_lines.append(f"Website: {website}")
    if page_url:
        body_lines.append(f"Page: {page_url}")
    body_lines.append("")
    body_lines.append("Comment:")
    body_lines.append(comment)
    body = "\n".join(body_lines)

    try:
        # Send to frank@fcjamison.com from frank@fcjamison.com (configured via SMTP_FROM).
        _send_smtp_email(subject=subject, body=body, reply_to=email)
    except Exception as e:
        # Keep response safe: no secrets, but provide actionable diagnostics.
        print(f"leave_reply SMTP error: {type(e).__name__}: {e}")

        error_message = "Email service error."
        status_code = 500

        if isinstance(e, RuntimeError):
            error_message = str(e)
        elif isinstance(e, smtplib.SMTPAuthenticationError):
            error_message = "SMTP authentication failed (check SMTP_USER/SMTP_PASSWORD)."
        elif isinstance(e, smtplib.SMTPConnectError):
            error_message = "SMTP connection failed (host/port/firewall)."
        elif isinstance(e, smtplib.SMTPServerDisconnected):
            error_message = "SMTP server disconnected unexpectedly."
        elif isinstance(e, smtplib.SMTPException):
            error_message = "SMTP error (check server settings)."
        elif isinstance(e, ssl.SSLError):
            error_message = f"SSL/TLS handshake failed (check SMTP_USE_SSL/SMTP_PORT): {e}"
            if isinstance(e, ssl.SSLCertVerificationError):
                issuer_hint = _peek_tls_leaf_issuer(
                    os.getenv("SMTP_HOST", "").strip(),
                    int(os.getenv("SMTP_PORT", "465").strip() or "465"),
                )
                if issuer_hint and (
                    "Avast" in issuer_hint
                    or "Web/Mail Shield" in issuer_hint
                    or "SSL/TLS scanning" in issuer_hint
                ):
                    error_message = (
                        "SSL/TLS certificate verification failed. "
                        "It looks like your antivirus is intercepting SMTP TLS (e.g. Avast Web/Mail Shield). "
                        "Disable SSL/TLS scanning for this connection, or set SMTP_ALLOW_INVALID_CERT=1 for local development only."
                    )
        elif isinstance(e, socket.gaierror):
            error_message = "DNS lookup failed for SMTP_HOST."
        elif isinstance(e, TimeoutError):
            error_message = "SMTP connection timed out (host/port/firewall)."
        elif isinstance(e, ConnectionRefusedError):
            error_message = "SMTP connection refused (host/port)."
        elif isinstance(e, OSError):
            # Covers various networking errors.
            error_message = f"Network error: {type(e).__name__}: {e}"
        else:
            # Fallback: include exception type/message (no secrets should appear here).
            error_message = f"{type(e).__name__}: {e}"

        if request.accept_mimetypes.best == 'application/json':
            return jsonify(ok=False, error=error_message), status_code

        return redirect(request.form.get('next') or request.referrer or url_for('index'))

    if request.accept_mimetypes.best == 'application/json':
        return jsonify(ok=True)
    return redirect(request.form.get('next') or request.referrer or url_for('index'))


@app.post('/contact')
def contact_message():
    # Honeypot: bots often fill hidden fields
    if (request.form.get('hp') or '').strip():
        return jsonify(ok=True)

    name = (request.form.get('name') or '').strip()
    email = (request.form.get('email') or '').strip()
    phone = (request.form.get('phone') or '').strip()
    subject = (request.form.get('subject') or '').strip()
    message = (request.form.get('message') or '').strip()
    page_url = (request.form.get('page_url') or request.referrer or '').strip()

    if not name or not email or not subject or not message:
        if request.accept_mimetypes.best == 'application/json':
            return jsonify(ok=False, error='Please provide name, email, subject, and a message.'), 400
        return redirect(request.referrer or url_for('index'))

    mail_subject = f"FCJamison Contact: {subject}"
    body_lines = [
        f"Name: {name}",
        f"Email: {email}",
    ]
    if phone:
        body_lines.append(f"Phone: {phone}")
    if page_url:
        body_lines.append(f"Page: {page_url}")
    body_lines.append("")
    body_lines.append("Message:")
    body_lines.append(message)
    body = "\n".join(body_lines)

    try:
        _send_smtp_email(subject=mail_subject, body=body, reply_to=email)
    except Exception as e:
        print(f"contact_message SMTP error: {type(e).__name__}: {e}")

        error_message = "Email service error."
        status_code = 500

        if isinstance(e, RuntimeError):
            error_message = str(e)
        elif isinstance(e, smtplib.SMTPAuthenticationError):
            error_message = "SMTP authentication failed (check SMTP_USER/SMTP_PASSWORD)."
        elif isinstance(e, smtplib.SMTPConnectError):
            error_message = "SMTP connection failed (host/port/firewall)."
        elif isinstance(e, smtplib.SMTPServerDisconnected):
            error_message = "SMTP server disconnected unexpectedly."
        elif isinstance(e, smtplib.SMTPException):
            error_message = "SMTP error (check server settings)."
        elif isinstance(e, ssl.SSLError):
            error_message = f"SSL/TLS handshake failed (check SMTP_USE_SSL/SMTP_PORT): {e}"
            if isinstance(e, ssl.SSLCertVerificationError):
                issuer_hint = _peek_tls_leaf_issuer(
                    os.getenv("SMTP_HOST", "").strip(),
                    int(os.getenv("SMTP_PORT", "465").strip() or "465"),
                )
                if issuer_hint and (
                    "Avast" in issuer_hint
                    or "Web/Mail Shield" in issuer_hint
                    or "SSL/TLS scanning" in issuer_hint
                ):
                    error_message = (
                        "SSL/TLS certificate verification failed. "
                        "It looks like your antivirus is intercepting SMTP TLS (e.g. Avast Web/Mail Shield). "
                        "Disable SSL/TLS scanning for this connection, or set SMTP_ALLOW_INVALID_CERT=1 for local development only."
                    )
        elif isinstance(e, socket.gaierror):
            error_message = "DNS lookup failed for SMTP_HOST."
        elif isinstance(e, TimeoutError):
            error_message = "SMTP connection timed out (host/port/firewall)."
        elif isinstance(e, ConnectionRefusedError):
            error_message = "SMTP connection refused (host/port)."
        elif isinstance(e, OSError):
            error_message = f"Network error: {type(e).__name__}: {e}"
        else:
            error_message = f"{type(e).__name__}: {e}"

        if request.accept_mimetypes.best == 'application/json':
            return jsonify(ok=False, error=error_message), status_code
        return redirect(request.referrer or url_for('index'))

    if request.accept_mimetypes.best == 'application/json':
        return jsonify(ok=True)
    return redirect(request.referrer or url_for('index'))


@app.route('/')
@app.route('/index')
def index():
    data = {
        'headTitle': 'FCJamison.com',
    }
    return render_template("home/index.html", **data)


@app.get('/projects/<project_slug>/')
def project_index(project_slug: str):
    project_dir = _project_dir(project_slug)
    return send_from_directory(project_dir, 'index.html')


@app.get('/projects/<project_slug>/<path:filename>')
def project_file(project_slug: str, filename: str):
    project_dir = _project_dir(project_slug)
    return send_from_directory(project_dir, filename)
