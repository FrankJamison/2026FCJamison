# VPS deployment (Nginx + Flask + PHP-FPM + MySQL + HTTPS)

Goal:
- `https://fcjamison.com` → Flask app (Waitress on localhost)
- `https://globebank.fcjamison.com` → GlobeBank PHP app (PHP-FPM)
- `https://classiccars.fcjamison.com` → Frank's Classic Cars PHP app (PHP-FPM)
- MySQL/MariaDB runs on the same VPS

This avoids the dev-only Flask→PHP proxy and runs GlobeBank as a real PHP app in production.

## 0) DNS

Create an `A` record:
- `fcjamison.com` → your VPS IP
- `www.fcjamison.com` → your VPS IP
- `globebank.fcjamison.com` → your VPS IP
- `classiccars.fcjamison.com` → your VPS IP

## 1) Install packages (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y nginx python3 python3-venv python3-pip \
  mariadb-server \
  php-fpm php-mysql
```

If your distro asks for a specific PHP version (e.g. `php8.3-fpm`), install that version.

## 2) Deploy files

Suggested layout:

- Flask site:
  - `/var/www/fcjamison` (this repo root)
- GlobeBank:
  - `/var/www/globebank` (copy `projects/2007GlobeBank/*` here)
- Frank's Classic Cars:
  - `/var/www/classiccars` (copy `projects/2018FranksClassicCars/*` here)

Example:

```bash
sudo mkdir -p /var/www/fcjamison /var/www/globebank /var/www/classiccars
sudo chown -R $USER:$USER /var/www/fcjamison /var/www/globebank /var/www/classiccars
```

## 3) Flask: venv + deps

```bash
cd /var/www/fcjamison
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 4) Flask: environment file

```bash
sudo nano /etc/fcjamison.env
sudo chmod 600 /etc/fcjamison.env
```

Example:

```ini
ENV=production
FLASK_ENV=production
FLASK_DEBUG=0

# Where the portfolio button should point in production
GLOBEBANK_URL=https://globebank.fcjamison.com/
FRANKSCLASSICCARS_URL=https://classiccars.fcjamison.com/

# SMTP settings...
SMTP_HOST=mail.fcjamison.com
SMTP_PORT=465
SMTP_USER=frank@fcjamison.com
SMTP_PASSWORD=REPLACE_ME
SMTP_FROM=frank@fcjamison.com
SMTP_TO=frank@fcjamison.com
SMTP_USE_SSL=1
SMTP_USE_TLS=0
SMTP_ALLOW_INVALID_CERT=0
```

## 5) Flask: systemd (Waitress)

Copy `deploy/systemd/fcjamison.service` to `/etc/systemd/system/fcjamison.service`, then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now fcjamison
sudo systemctl status fcjamison --no-pager
```

## 6) GlobeBank: PHP deployment notes

- Ensure GlobeBank’s document root is `/var/www/globebank/public`.
- Ensure `private/` is **not** web-accessible (it sits outside `public/`, so that’s good).

### Configure DB credentials

Edit:
- `/var/www/globebank/private/db_credentials.php`

Point it at your local MySQL/MariaDB and set a strong password.

## 7) MySQL/MariaDB setup

```bash
sudo systemctl enable --now mariadb
sudo mysql
```

Inside MySQL:

```sql
CREATE DATABASE frankjamison_globe_bank CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'frankjamison_globe_bank_user'@'localhost' IDENTIFIED BY 'REPLACE_ME_STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON frankjamison_globe_bank.* TO 'frankjamison_globe_bank_user'@'localhost';
FLUSH PRIVILEGES;
```

Import schema/data:

```bash
mysql -u frankjamison_globe_bank_user -p frankjamison_globe_bank < /var/www/globebank/setup_database_production.sql
```

## 8) Nginx sites

Copy:
- `deploy/nginx/fcjamison.com.conf` → `/etc/nginx/sites-available/fcjamison.com`
- `deploy/nginx/globebank.fcjamison.com.conf` → `/etc/nginx/sites-available/globebank.fcjamison.com`
- `deploy/nginx/classiccars.fcjamison.com.conf` → `/etc/nginx/sites-available/classiccars.fcjamison.com`

Enable:

```bash
sudo ln -s /etc/nginx/sites-available/fcjamison.com /etc/nginx/sites-enabled/fcjamison.com
sudo ln -s /etc/nginx/sites-available/globebank.fcjamison.com /etc/nginx/sites-enabled/globebank.fcjamison.com
sudo ln -s /etc/nginx/sites-available/classiccars.fcjamison.com /etc/nginx/sites-enabled/classiccars.fcjamison.com
sudo nginx -t
sudo systemctl reload nginx
```

## 9) HTTPS (Let’s Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d fcjamison.com -d www.fcjamison.com -d globebank.fcjamison.com -d classiccars.fcjamison.com
```

## 10) Smoke tests

- `https://fcjamison.com/`
- `https://globebank.fcjamison.com/`
- `https://classiccars.fcjamison.com/`
- If GlobeBank errors, check PHP-FPM logs and Nginx error logs.

## Notes

- The Flask→PHP proxy is intended for local development only. In production we serve GlobeBank directly via PHP-FPM.
- You may need to adjust `fastcgi_pass` socket path depending on installed PHP version.
