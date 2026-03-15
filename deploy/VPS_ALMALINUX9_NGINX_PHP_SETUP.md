# AlmaLinux 9.x VPS deployment (Nginx + Flask + PHP-FPM + MariaDB + HTTPS)

Target:

- `https://fcjamison.com` → Flask app (Gunicorn on localhost)
- `https://globebank.fcjamison.com` → GlobeBank PHP app (PHP-FPM)
- MariaDB (MySQL-compatible) on the same VPS

## 0) DNS

Create `A` records pointing to your VPS IP:

- `fcjamison.com`
- `www.fcjamison.com`
- `globebank.fcjamison.com`

## 1) Install packages (AlmaLinux 9)

```bash
sudo dnf -y update

# Core web + python
sudo dnf -y install nginx python3 python3-pip python3-virtualenv

# PHP + MySQL driver (mysqli)
sudo dnf -y install php php-fpm php-mysqlnd

# Database
sudo dnf -y install mariadb-server

# Certbot (EPEL)
sudo dnf -y install epel-release
sudo dnf -y install certbot python3-certbot-nginx
```

Notes:

- `php-mysqlnd` is the key package that provides `mysqli`.
- AlmaLinux 9 ships a supported PHP via AppStream (often 8.1). That’s fine for GlobeBank.

## 2) Enable and start services

```bash
sudo systemctl enable --now nginx
sudo systemctl enable --now php-fpm
sudo systemctl enable --now mariadb
```

### If port 80/443 is already in use

If this VPS is already hosting other sites, you likely already have a web server bound to `:80`/`:443`.
In that case, **do not try to run a second Nginx**. Instead, add new virtual hosts to the existing web server.

Most common on AlmaLinux hosting is Apache (`httpd`). You can use the included templates:

- Flask (reverse proxy): [deploy/apache/fcjamison.com.conf](deploy/apache/fcjamison.com.conf)
- GlobeBank (PHP-FPM): [deploy/apache/globebank.fcjamison.com.conf](deploy/apache/globebank.fcjamison.com.conf)

Copy them to `/etc/httpd/conf.d/`, then reload Apache:

```bash
sudo cp deploy/apache/fcjamison.com.conf /etc/httpd/conf.d/fcjamison.com.conf
sudo cp deploy/apache/globebank.fcjamison.com.conf /etc/httpd/conf.d/globebank.fcjamison.com.conf

sudo httpd -t
sudo systemctl reload httpd
```

Then run certbot for Apache:

```bash
sudo dnf -y install certbot python3-certbot-apache
sudo certbot --apache -d fcjamison.com -d www.fcjamison.com -d globebank.fcjamison.com
```

If `nginx` fails to start with `bind() to 0.0.0.0:80 failed (98: Address already in use)`, another service is already listening on port 80.

Find the process (note: `grep -E` does **not** support `\s`):

```bash
sudo ss -ltnp | grep -E ':(80|443)\b'
sudo lsof -nP -iTCP:80 -sTCP:LISTEN
```

Common fix (if Apache/httpd is installed):

```bash
sudo systemctl disable --now httpd
```

## 3) Firewall (firewalld)

```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

## 4) SELinux (important on AlmaLinux)

Allow Nginx to proxy to your Flask upstream on localhost:

```bash
sudo setsebool -P httpd_can_network_connect 1
```

If you deploy code under `/var/www`, ensure correct SELinux contexts:

```bash
# Flask site files (read)
sudo semanage fcontext -a -t httpd_sys_content_t "/var/www/fcjamison(/.*)?"
sudo restorecon -Rv /var/www/fcjamison

# GlobeBank public files (read)
sudo semanage fcontext -a -t httpd_sys_content_t "/var/www/globebank(/.*)?"
sudo restorecon -Rv /var/www/globebank
```

If `semanage` is missing:

```bash
sudo dnf -y install policycoreutils-python-utils
```

## 5) Deploy files

Suggested layout:

- Flask site repo: `/var/www/fcjamison`
- GlobeBank app: `/var/www/globebank` (copy `projects/2007GlobeBank/*` here)

```bash
sudo mkdir -p /var/www/fcjamison /var/www/globebank
sudo chown -R $USER:$USER /var/www/fcjamison /var/www/globebank
```

## 6) Flask: venv + deps

```bash
cd /var/www/fcjamison
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 7) Flask: environment file

```bash
sudo nano /etc/fcjamison.env
sudo chmod 600 /etc/fcjamison.env
```

Example:

```ini
ENV=production
FLASK_ENV=production
FLASK_DEBUG=0

# Portfolio button target in production
GLOBEBANK_URL=https://globebank.fcjamison.com/

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

## 8) Flask: systemd service

Copy `deploy/systemd/fcjamison.service` to `/etc/systemd/system/fcjamison.service`.

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now fcjamison
sudo systemctl status fcjamison --no-pager
```

Logs:

```bash
sudo journalctl -u fcjamison -f
```

## 9) GlobeBank: database setup (MariaDB)

```bash
sudo mysql
```

In the MariaDB shell:

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

Update GlobeBank credentials:

- `/var/www/globebank/private/db_credentials.php`

## 10) Nginx configs

Copy:

- `deploy/nginx/fcjamison.com.conf` → `/etc/nginx/conf.d/fcjamison.com.conf`
- `deploy/nginx/globebank.fcjamison.com.conf` → `/etc/nginx/conf.d/globebank.fcjamison.com.conf`

Test + reload:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 11) HTTPS (Let’s Encrypt)

```bash
sudo certbot --nginx -d fcjamison.com -d www.fcjamison.com -d globebank.fcjamison.com
```

## 12) Smoke tests

- `https://fcjamison.com/`
- `https://globebank.fcjamison.com/`

If GlobeBank errors:

- `sudo tail -n 200 /var/log/nginx/error.log`
- `sudo journalctl -u php-fpm -n 200 --no-pager`

Quick PHP module check:

```bash
php -m | grep -i mysqli
```
