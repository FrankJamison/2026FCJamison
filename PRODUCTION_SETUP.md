# Production setup for fcjamison.com

This project is a Flask site intended to run behind a reverse proxy (recommended: Nginx) with a production WSGI server (recommended here: **Waitress**, because it works on both Linux and Windows).

> If you are on a Linux VPS, the most common setup is: **Nginx (public)** → **Waitress (localhost:8000)**.

## 1) Server prerequisites

- DNS A/AAAA for `fcjamison.com` pointing to your server
- Ports open:
  - 80/tcp (HTTP)
  - 443/tcp (HTTPS)
- Ubuntu/Debian packages:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx
```

## 2) Put the app on disk

Example:

```bash
sudo mkdir -p /var/www/fcjamison
sudo chown -R $USER:$USER /var/www/fcjamison
# upload your files into /var/www/fcjamison
```

## 3) Python venv + install deps

```bash
cd /var/www/fcjamison
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 4) Configure environment variables

Create a file only readable by root:

```bash
sudo nano /etc/fcjamison.env
sudo chmod 600 /etc/fcjamison.env
```

Example contents:

```ini
# Flask
ENV=production
FLASK_ENV=production
FLASK_DEBUG=0

# SMTP (required for contact + blog replies)
SMTP_HOST=mail.fcjamison.com
SMTP_PORT=465
SMTP_USER=frank@fcjamison.com
SMTP_PASSWORD=REPLACE_ME
SMTP_FROM=frank@fcjamison.com
SMTP_TO=frank@fcjamison.com
SMTP_USE_SSL=1
SMTP_USE_TLS=0

# IMPORTANT: do not enable this in production
SMTP_ALLOW_INVALID_CERT=0
```

## 5) Run Waitress via systemd

Create a service:

```bash
sudo nano /etc/systemd/system/fcjamison.service
```

Paste:

```ini
[Unit]
Description=fcjamison.com Flask site (Waitress)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/fcjamison
EnvironmentFile=/etc/fcjamison.env

# Waitress listens only on localhost; Nginx is the public entry
ExecStart=/var/www/fcjamison/.venv/bin/python -m waitress --listen=127.0.0.1:8000 wsgi:application

Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Enable + start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now fcjamison
sudo systemctl status fcjamison --no-pager
```

Logs:

```bash
sudo journalctl -u fcjamison -f
```

## 6) Nginx reverse proxy for fcjamison.com

Create:

```bash
sudo nano /etc/nginx/sites-available/fcjamison.com
```

Paste:

```nginx
server {
    listen 80;
    server_name fcjamison.com www.fcjamison.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable + reload:

```bash
sudo ln -s /etc/nginx/sites-available/fcjamison.com /etc/nginx/sites-enabled/fcjamison.com
sudo nginx -t
sudo systemctl reload nginx
```

## 7) HTTPS (Let’s Encrypt)

If you want a standard cert:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d fcjamison.com -d www.fcjamison.com
```

Certbot will update Nginx and set up renewals.

## 8) Quick production smoke tests

- Visit `https://fcjamison.com/`
- Submit the Contact form
- Submit a Blog “Leave a Reply” form

If Contact/Reply fails, check:

```bash
sudo journalctl -u fcjamison -n 200 --no-pager
```

## Notes

- The project includes `wsgi.py` so you can also run under Apache `mod_wsgi` if your host requires it.
- This app expects to be run as a WSGI app in production; do not use `python app.py` for production traffic.
