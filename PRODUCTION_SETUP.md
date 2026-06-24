# Production Deployment Runbook

This guide describes a production-grade deployment for this Flask application using:

# Production Setup Runbook (Flask + Gunicorn + Nginx)

This guide provides a production-grade deployment path for this repository on Linux.

Recommended topology:

- Nginx (public edge, TLS termination)
- Gunicorn (local app server bound to 127.0.0.1)
- Flask app entrypoint: wsgi:application

This app is server-rendered and writes operational data to CSV under data/:

- data/contact_messages.csv
- data/leave_reply.csv
- data/analytics_events.csv

Ensure your service user has write permissions to data/.

## 1. Production Architecture

Traffic flow:

Internet -> Nginx:443 -> Gunicorn:127.0.0.1:8000 -> Flask (wsgi.py)

Operational responsibilities:

- Nginx: TLS, security headers, request routing
- Gunicorn: Python worker lifecycle and concurrency
- Flask app: routing, templates, SMTP notifications, CSV persistence

## 2. Prerequisites

### Infrastructure

- Linux server (Ubuntu 22.04/24.04 or Debian 12 recommended)
- DNS A/AAAA records for your domain
- Open firewall ports: 80/tcp and 443/tcp
- Non-root deploy user with sudo privileges

### Packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx curl git openssl
```

## 3. Deploy Application Code

Example target path:

```bash
sudo mkdir -p /var/www/fcjamison
sudo chown -R "$USER":"$USER" /var/www/fcjamison
cd /var/www/fcjamison
git clone <your-repo-url> .
```

If you deploy via archive/scp instead of git, ensure file ownership is consistent.

## 4. Python Environment and Dependencies

```bash
cd /var/www/fcjamison
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-prod.txt
```

Validate Gunicorn import path:

```bash
.venv/bin/python -c "from wsgi import application; print('WSGI import OK')"
```

## 5. Environment Configuration (Production)

Create a root-owned env file consumed by systemd:

```bash
sudo install -m 600 -o root -g root /dev/null /etc/fcjamison.env
sudo nano /etc/fcjamison.env
```

Recommended baseline:

```ini
# Core environment
ENV=production
FLASK_ENV=production
FLASK_DEBUG=0

# Optional; app runs behind reverse proxy and gunicorn bind controls host/port
HOST=127.0.0.1
PORT=5000

# Site / SEO
SITE_URL=https://www.fcjamison.com
SITE_NAME=FCJamison.com
SITE_OWNER_NAME=Frank Jamison
SITE_OWNER_EMAIL=frank@fcjamison.com
SITE_DEFAULT_TITLE=Full-Stack Web Developer
SITE_TITLE_SUFFIX=Frank Jamison | Python, Flask, React
SITE_DEFAULT_DESCRIPTION=Full-stack web developer specializing in Python, Flask, and React.
SITE_LOGO_PATH=images/logo/logo.png

# Sitemap / projects
SITEMAP_INCLUDE_PROJECTS=1
GITHUB_ORG=FrankJamison

# SMTP (required for /contact and /leave-reply)
SMTP_HOST=smtp.example.com
SMTP_PORT=465
SMTP_USER=mailer@example.com
SMTP_PASSWORD=REPLACE_WITH_SECRET
SMTP_FROM=no-reply@example.com
SMTP_TO=frank@fcjamison.com
SMTP_USE_SSL=1
SMTP_USE_TLS=0
SMTP_ALLOW_INVALID_CERT=0

# Analytics
ANALYTICS_EVENTS_PATH=/var/www/fcjamison/data/analytics_events.csv
ANALYTICS_RETENTION_DAYS=180
ANALYTICS_MAX_ROWS=200000
ANALYTICS_PRUNE_MIN_INTERVAL_SEC=900
ANALYTICS_ADMIN_TOKEN=REPLACE_WITH_LONG_RANDOM_TOKEN
```

Secrets guidance:

- Never commit /etc/fcjamison.env.
- Use long random values for ANALYTICS_ADMIN_TOKEN.
- Rotate SMTP credentials on schedule.

## 6. Filesystem Permissions and Data Durability

The app auto-creates CSV directories/files, but the process user must be able to write.

```bash
sudo mkdir -p /var/www/fcjamison/data
sudo chown -R www-data:www-data /var/www/fcjamison/data
sudo chmod 750 /var/www/fcjamison/data
```

If code is owned by a deploy user, keep code read-only for www-data and writable only where needed (data/).

Backup recommendation:

- Include /var/www/fcjamison/data in daily backups.
- Validate restore by opening CSV files after restore.

## 7. systemd Service (Gunicorn)

Create service:

```bash
sudo tee /etc/systemd/system/fcjamison.service > /dev/null << 'EOF'
[Unit]
Description=FCJamison Flask app (Gunicorn)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/fcjamison
EnvironmentFile=/etc/fcjamison.env

# Gunicorn process
ExecStart=/var/www/fcjamison/.venv/bin/gunicorn \
  --workers 3 \
  --worker-class sync \
  --bind 127.0.0.1:8000 \
  --timeout 60 \
  --access-logfile - \
  --error-logfile - \
  wsgi:application

Restart=always
RestartSec=3
KillSignal=SIGTERM
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now fcjamison
sudo systemctl status fcjamison --no-pager
```

Logs:

```bash
sudo journalctl -u fcjamison -f
```

## 8. Nginx Reverse Proxy Configuration

Create Nginx site:

```bash
sudo tee /etc/nginx/sites-available/fcjamison.com > /dev/null << 'EOF'
server {
  listen 80;
  listen [::]:80;
  server_name fcjamison.com www.fcjamison.com;

  location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 90;
  }
}
EOF
```

Enable and validate:

```bash
sudo ln -sf /etc/nginx/sites-available/fcjamison.com /etc/nginx/sites-enabled/fcjamison.com
sudo nginx -t
sudo systemctl reload nginx
```

## 9. TLS with Let’s Encrypt

Install certbot plugin:

```bash
sudo apt install -y certbot python3-certbot-nginx
```

Issue certificate:

```bash
sudo certbot --nginx -d fcjamison.com -d www.fcjamison.com
```

Verify auto-renew timer:

```bash
systemctl list-timers | grep certbot
```

## 10. Security Hardening (Recommended)

Add security headers and HSTS in TLS server block after certbot provisions HTTPS:

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

Optional rate limiting for form endpoints:

```nginx
limit_req_zone $binary_remote_addr zone=form_rate:10m rate=5r/m;

location = /contact {
  limit_req zone=form_rate burst=10 nodelay;
  proxy_pass http://127.0.0.1:8000;
}

location = /leave-reply {
  limit_req zone=form_rate burst=10 nodelay;
  proxy_pass http://127.0.0.1:8000;
}
```

## 11. Validation and Smoke Tests

### Service and HTTP checks

```bash
curl -I http://127.0.0.1:8000/
curl -I https://fcjamison.com/
```

Expected:

- 200 or 301/302 from public URL (depending on redirects)
- No 5xx from Gunicorn endpoint

### Functional checks

1. Load homepage and project modals.
2. Submit contact form.
3. Submit leave-reply form.
4. Confirm:
   - CSV rows written in data/contact_messages.csv and data/leave_reply.csv
   - SMTP notification received

### Analytics checks

```bash
curl "https://fcjamison.com/analytics/summary?days=7"
curl "https://fcjamison.com/analytics/admin?token=<ANALYTICS_ADMIN_TOKEN>&days=7"
```

## 12. Operations Runbook

### Deploy updates

```bash
cd /var/www/fcjamison
git pull
source .venv/bin/activate
python -m pip install -r requirements-prod.txt
sudo systemctl restart fcjamison
sudo systemctl status fcjamison --no-pager
```

### Rollback

1. Checkout previous commit/tag.
2. Restart service.
3. Validate smoke tests.

### Log triage

```bash
sudo journalctl -u fcjamison -n 200 --no-pager
sudo journalctl -u fcjamison -f
sudo tail -n 200 /var/log/nginx/error.log
```

## 13. Common Failure Modes

### Contact or reply returns ok:false

Likely SMTP misconfiguration.

Actions:

1. Verify SMTP variables in /etc/fcjamison.env.
2. Restart service after changes.
3. Review logs for Email send failed errors.
4. See SMTP_SETUP.md for provider-level troubleshooting.

### Permission denied writing CSV files

Actions:

1. Confirm /var/www/fcjamison/data ownership is www-data:www-data.
2. Ensure service user matches configured ownership.

### 502 Bad Gateway from Nginx

Actions:

1. Check gunicorn service status.
2. Confirm bind target is 127.0.0.1:8000.
3. Validate Nginx proxy_pass target.

## 14. Alternative Hosting Notes

- Apache/mod_wsgi is possible via wsgi.py if required by host panel.
- Managed platforms can also run gunicorn wsgi:application directly.
- Do not use python app.py for production traffic.

## 15. Production Checklist

- DNS records resolve correctly.
- Nginx serves HTTPS with valid certificate.
- Gunicorn service enabled and healthy.
- /etc/fcjamison.env present and secured (0600).
- SMTP verified with successful form submissions.
- data/ directory writable and backed up.
- ANALYTICS_ADMIN_TOKEN set and kept secret.
- Smoke tests completed after each deployment.
  sudo nano /etc/nginx/sites-available/fcjamison

````

Use this template (replace example.com):

```nginx
limit_req_zone $binary_remote_addr zone=form_limit:10m rate=5r/m;

server {
  listen 80;
  server_name example.com www.example.com;

  location /.well-known/acme-challenge/ { root /var/www/html; }
  location / { return 301 https://$host$request_uri; }
}

server {
  listen 443 ssl http2;
  server_name example.com www.example.com;

  # Managed by certbot after certificate issuance
  ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

  # Security headers
  add_header X-Content-Type-Options nosniff always;
  add_header X-Frame-Options DENY always;
  add_header Referrer-Policy strict-origin-when-cross-origin always;

  client_max_body_size 10m;

  location /static/ {
    alias /srv/fcjamison/static/;
    expires 7d;
    access_log off;
  }

  # Optional protective throttling on form posts
  location = /contact {
    limit_req zone=form_limit burst=10 nodelay;
    proxy_pass http://127.0.0.1:8000;
    include /etc/nginx/proxy_params;
    proxy_set_header X-Forwarded-Proto https;
  }

  location = /leave-reply {
    limit_req zone=form_limit burst=10 nodelay;
    proxy_pass http://127.0.0.1:8000;
    include /etc/nginx/proxy_params;
    proxy_set_header X-Forwarded-Proto https;
  }

  location / {
    proxy_pass http://127.0.0.1:8000;
    include /etc/nginx/proxy_params;
    proxy_set_header X-Forwarded-Proto https;
    proxy_read_timeout 60s;
  }
}
````

Enable and validate:

```bash
sudo ln -sf /etc/nginx/sites-available/fcjamison /etc/nginx/sites-enabled/fcjamison
sudo nginx -t
sudo systemctl reload nginx
```

## 8. TLS certificates (Let's Encrypt)

Issue certificates:

```bash
sudo certbot --nginx -d example.com -d www.example.com
```

Verify renewal:

```bash
sudo certbot renew --dry-run
```

## 9. Smoke tests

Run these after every deploy:

```bash
curl -I https://example.com/
curl -I https://example.com/robots.txt
curl -I https://example.com/sitemap.xml
curl -s https://example.com/analytics/summary?days=7
```

Functional checks:

- Submit contact form and confirm email delivery.
- Submit leave-reply form and confirm email delivery.
- Confirm rows are appended under /srv/fcjamison/data/.

## 10. Logging, monitoring, and backups

Service logs:

```bash
sudo journalctl -u fcjamison -f
sudo journalctl -u fcjamison -n 200 --no-pager
```

Nginx logs:

```bash
sudo tail -f /var/log/nginx/access.log /var/log/nginx/error.log
```

Backup recommendation:

- Daily backup of /srv/fcjamison/data/
- Daily backup of /etc/fcjamison.env in encrypted secrets backup

## 11. Deployment workflow (repeatable)

```bash
cd /srv/fcjamison
sudo -u webapp git fetch --all
sudo -u webapp git checkout main
sudo -u webapp git pull --ff-only
sudo -u webapp ./.venv/bin/pip install -r requirements-prod.txt
sudo systemctl restart fcjamison
sudo systemctl status fcjamison --no-pager
sudo nginx -t && sudo systemctl reload nginx
```

## 12. Rollback workflow

```bash
cd /srv/fcjamison
sudo -u webapp git log --oneline -n 5
sudo -u webapp git checkout <known_good_commit>
sudo -u webapp ./.venv/bin/pip install -r requirements-prod.txt
sudo systemctl restart fcjamison
```

## 13. Common failures and fixes

### 502 Bad Gateway

- Check Gunicorn service status and logs.
- Ensure Gunicorn binds to 127.0.0.1:8000.
- Ensure Nginx proxy_pass points to same address.

### Contact/reply returns ok: false

- Validate SMTP\_\* values in /etc/fcjamison.env.
- Restart service after env changes.
- See SMTP_SETUP.md for provider-specific settings.

### Wrong canonical URLs in sitemap

- Set SITE_URL explicitly to public HTTPS URL.
- Ensure X-Forwarded-Proto is forwarded by Nginx.

### Permission errors writing CSV files

- Confirm service user has write access to /srv/fcjamison/data.
- Verify ReadWritePaths includes /srv/fcjamison/data in systemd service.

## 14. Security checklist

- Run as non-root service user.
- Keep secrets out of git.
- Enforce HTTPS and cert renewal.
- Keep SMTP_ALLOW_INVALID_CERT=0 in production.
- Set strong SECRET_KEY and ANALYTICS_ADMIN_TOKEN.
- Restrict firewall to SSH, 80, 443.
- Patch OS and Python dependencies regularly.

## 15. Related docs

- SMTP_SETUP.md
- ACCESSIBILITY.md
- README.md
