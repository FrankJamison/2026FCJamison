import os
import smtplib
import socket
import ssl
import atexit
import subprocess
import threading
import time
import shutil
import re
from typing import Optional
from email.message import EmailMessage

import requests
from flask import Response, abort, jsonify, redirect, render_template, request, send_from_directory, url_for
from app import app


PROJECTS_ROOT = os.path.abspath(
    os.getenv(
        "PROJECTS_ROOT",
        os.path.join(os.path.dirname(__file__), "projects"),
    )
)


_globebank_php_proc: Optional[subprocess.Popen] = None
_globebank_lock = threading.Lock()
_globebank_php_port: Optional[int] = None


def _find_php_executable() -> Optional[str]:
    php = shutil.which('php')
    if php:
        return php

    # WinGet installs often land here even if PATH isn't refreshed.
    local_appdata = os.getenv('LOCALAPPDATA')
    if not local_appdata:
        return None
    winget_packages = os.path.join(
        local_appdata, 'Microsoft', 'WinGet', 'Packages')
    if not os.path.isdir(winget_packages):
        return None

    for root, _, files in os.walk(winget_packages):
        if 'php.exe' in files and 'PHP.PHP.' in root.replace('\\', '/'):
            return os.path.join(root, 'php.exe')
    return None


def _is_port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.25):
            return True
    except OSError:
        return False


def _php_server_has_mysqli(host: str, port: int) -> bool:
    """Best-effort check to see if the running PHP server has mysqli enabled."""
    try:
        resp = requests.get(
            f'http://{host}:{port}/diagnostic.php', timeout=1.5)
        if resp.status_code != 200:
            return False
        body = resp.text
        return ('mysqli: Installed' in body) or ('mysqli: installed' in body)
    except Exception:
        return False


def _pick_free_port(host: str, preferred_port: int, *, max_tries: int = 25) -> int:
    port = preferred_port
    for _ in range(max_tries):
        if not _is_port_open(host, port):
            return port
        port += 1
    raise RuntimeError('No free port found for PHP server.')


def _ensure_globebank_php_server() -> tuple[str, int]:
    """Ensure a PHP built-in server is running for GlobeBank.

    Returns (host, port) for the PHP server.
    """
    host = (os.getenv('PHP_GLOBEBANK_HOST')
            or '127.0.0.1').strip() or '127.0.0.1'
    preferred_port = int((os.getenv('PHP_GLOBEBANK_PORT')
                         or '8007').strip() or '8007')

    global _globebank_php_port
    if _globebank_php_port is not None and _is_port_open(host, _globebank_php_port):
        return host, _globebank_php_port

    # If something is already listening on the preferred port (e.g. VS Code task),
    # only reuse it if it has mysqli enabled.
    if _is_port_open(host, preferred_port) and _php_server_has_mysqli(host, preferred_port):
        _globebank_php_port = preferred_port
        return host, preferred_port

    php_exe = _find_php_executable()
    if not php_exe:
        raise RuntimeError(
            "PHP is not installed or not on PATH. "
            "Install PHP (recommended: winget install -e --id PHP.PHP.8.4) and restart VS Code terminals."
        )

    project_dir = _project_dir('2007GlobeBank')
    public_dir = os.path.join(project_dir, 'public')
    if not os.path.isdir(public_dir):
        raise RuntimeError('GlobeBank public/ directory is missing.')

    php_dir = os.path.dirname(php_exe)
    php_ext_dir = os.path.join(php_dir, 'ext')

    with _globebank_lock:
        global _globebank_php_proc

        port = _pick_free_port(host, preferred_port)
        _globebank_php_port = port

        if _is_port_open(host, port):
            return host, port

        if _globebank_php_proc is not None and _globebank_php_proc.poll() is None:
            # Process exists but port isn't reachable yet; give it a moment.
            pass
        else:
            php_args = [php_exe]
            if os.path.isdir(php_ext_dir):
                php_args += ['-d',
                             f'extension_dir={php_ext_dir}', '-d', 'extension=mysqli']
            php_args += ['-S', f'{host}:{port}', '-t', public_dir]
            _globebank_php_proc = subprocess.Popen(
                php_args,
                cwd=public_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=(
                    subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0),
            )

        # Wait briefly for the server to come up.
        deadline = time.time() + 3.0
        while time.time() < deadline:
            if _is_port_open(host, port) and _php_server_has_mysqli(host, port):
                return host, port
            time.sleep(0.05)

        raise RuntimeError('PHP server failed to start for GlobeBank.')


@atexit.register
def _stop_globebank_php_server() -> None:
    global _globebank_php_proc
    proc = _globebank_php_proc
    _globebank_php_proc = None
    if proc is None:
        return
    try:
        if proc.poll() is None:
            proc.terminate()
    except Exception:
        pass


_HOP_BY_HOP_HEADERS = {
    'connection',
    'keep-alive',
    'proxy-authenticate',
    'proxy-authorization',
    'te',
    'trailers',
    'transfer-encoding',
    'upgrade',
}


def _proxy_to_php_app(*, php_host: str, php_port: int, mount_path: str, subpath: str) -> Response:
    """Reverse proxy a request to a local PHP server.

    mount_path: e.g. '/projects/2007GlobeBank'
    subpath: path after mount, without leading slash
    """
    subpath = (subpath or '').lstrip('/')
    upstream_base = f'http://{php_host}:{php_port}'
    upstream_url = f'{upstream_base}/{subpath}'

    upstream_headers: dict[str, str] = {}
    for k, v in request.headers.items():
        lk = k.lower()
        if lk in _HOP_BY_HOP_HEADERS or lk in {'host', 'content-length'}:
            continue
        upstream_headers[k] = v

    upstream_headers['X-Forwarded-Proto'] = request.scheme
    upstream_headers['X-Forwarded-Host'] = request.host
    upstream_headers['X-Forwarded-Prefix'] = mount_path

    resp = requests.request(
        method=request.method,
        url=upstream_url,
        params=request.args,
        data=request.get_data(),
        headers=upstream_headers,
        cookies=request.cookies,
        allow_redirects=False,
        timeout=10,
    )

    content_type = (resp.headers.get('Content-Type') or '').lower()
    body: bytes = resp.content

    # GlobeBank was originally built as a site-root PHP app, so it uses URLs like
    # href="/stylesheets/..." and src="/images/...". When mounted under
    # /projects/2007GlobeBank/, those URLs must be rewritten to keep assets loading.
    if any(ct in content_type for ct in ('text/html', 'text/css', 'application/javascript', 'text/javascript')):
        try:
            text = resp.text
            prefix = mount_path.lstrip('/') + '/'

            def _rewrite_attr(attr: str, s: str) -> str:
                # Rewrite href="/foo" -> href="/projects/2007GlobeBank/foo" (unless already prefixed)
                pattern = rf'{attr}=(?P<q>[\"\"])\/(?!{re.escape(prefix)})'
                return re.sub(pattern, rf'{attr}=\g<q>{mount_path}/', s)

            for a in ('href', 'src', 'action'):
                text = _rewrite_attr(a, text)

            # Rewrite CSS url(/images/...) and url("/images/...")
            text = re.sub(
                rf'url\((?P<q>[\"\"]?)\/(?!{re.escape(prefix)})',
                rf'url(\g<q>{mount_path}/',
                text,
            )

            body = text.encode(resp.encoding or 'utf-8', errors='replace')
        except Exception:
            # If decoding/rewriting fails, fall back to the original bytes.
            body = resp.content

    out_headers: list[tuple[str, str]] = []
    for k, v in resp.headers.items():
        lk = k.lower()
        if lk in _HOP_BY_HOP_HEADERS:
            continue

        if lk == 'location':
            # Rewrite redirects back through Flask mount path.
            location = v
            if location.startswith(upstream_base + '/'):
                location = mount_path + location[len(upstream_base):]
            elif location.startswith('/'):
                location = mount_path + location
            out_headers.append((k, location))
            continue

        # Content-Length may have changed after rewriting.
        if lk == 'content-length':
            continue
        out_headers.append((k, v))

    return Response(body, status=resp.status_code, headers=out_headers)


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


def _is_production_env() -> bool:
    env_name = (os.getenv('FLASK_ENV') or os.getenv(
        'ENV') or '').strip().lower()
    return env_name == 'production'


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


@app.route('/projects/2007GlobeBank/', defaults={'subpath': ''}, methods=[
    'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS',
])
@app.route('/projects/2007GlobeBank/<path:subpath>', methods=[
    'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS',
])
def globebank_proxy(subpath: str):
    if _is_production_env() and not _truthy_env(os.getenv('GLOBEBANK_PROXY_ENABLED')):
        # In production, GlobeBank should be served by PHP-FPM behind Nginx on a dedicated subdomain.
        return redirect((os.getenv('GLOBEBANK_URL') or 'https://globebank.fcjamison.com/').strip())

    # Avoid accidentally exposing internal diagnostics during normal browsing.
    # Enable explicitly with GLOBEBANK_DIAGNOSTIC_ENABLED=1.
    if (subpath or '').strip('/').lower() == 'diagnostic.php' and not _truthy_env(
        os.getenv('GLOBEBANK_DIAGNOSTIC_ENABLED')
    ):
        return redirect('/projects/2007GlobeBank/')

    try:
        php_host, php_port = _ensure_globebank_php_server()
    except Exception as e:
        return Response(
            f"GlobeBank PHP server not available: {type(e).__name__}: {e}\n",
            status=500,
            mimetype='text/plain',
        )

    return _proxy_to_php_app(
        php_host=php_host,
        php_port=php_port,
        mount_path='/projects/2007GlobeBank',
        subpath=subpath,
    )


@app.get('/projects/<project_slug>/')
def project_index(project_slug: str):
    project_dir = _project_dir(project_slug)

    index_html = os.path.join(project_dir, 'index.html')
    if os.path.isfile(index_html):
        return send_from_directory(project_dir, 'index.html')

    # Some archived projects are PHP apps; serve the entrypoint file.
    for candidate in ('public/index.php', 'index.php'):
        candidate_path = os.path.join(project_dir, *candidate.split('/'))
        if os.path.isfile(candidate_path):
            # Optional: redirect to a real PHP server (so PHP executes).
            if project_slug == '2007GlobeBank' and _truthy_env(os.getenv('PHP_GLOBEBANK_ENABLED')):
                php_url = (os.getenv('PHP_GLOBEBANK_URL') or '').strip()
                if php_url:
                    if not php_url.endswith('/'):
                        php_url += '/'
                    return redirect(php_url)
            return redirect(url_for('project_file', project_slug=project_slug, filename=candidate))

    abort(404)


@app.get('/projects/<project_slug>/<path:filename>')
def project_file(project_slug: str, filename: str):
    project_dir = _project_dir(project_slug)
    return send_from_directory(project_dir, filename)
