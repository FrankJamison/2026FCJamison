# QuestKeeper (PHP) on Webuzo Apache — Production Runbook

This is the exact, QuestKeeper-specific procedure that got:

- `https://questkeeper.fcjamison.com/`

working on this server.

It assumes:

- Webuzo-managed Apache is the live webserver
- QuestKeeper code is deployed at:
  - `/home/frankjamison/public_html/fcjamison.com/projects/2018Questkeeper`

---

## 0) Identify the real Apache

On this host, the active Apache is **Webuzo’s Apache**, not systemd `httpd`:

```bash
/usr/local/apps/apache2/bin/httpd -v
ss -ltnp | egrep ':80|:443' || true
pgrep -a httpd || true
```

Do **not** try to edit `/usr/sbin/httpd` configs or manage `httpd.service` for this site.

---

## 1) Create a dedicated vhost that beats Webuzo’s wildcard

Webuzo generates vhosts into:

- `/usr/local/apps/apache2/etc/conf.d/webuzoVH.conf` (**DO NOT EDIT**)

That file contains wildcard vhosts (e.g. `ServerAlias *.fcjamison.com`) which can capture new subdomains and redirect them to `https://fcjamison.com/`.

The fix: create a custom vhost file that loads **earlier**.

### Create `/usr/local/apps/apache2/etc/conf.d/00-questkeeper.fcjamison.com.conf`

```bash
cat > /usr/local/apps/apache2/etc/conf.d/00-questkeeper.fcjamison.com.conf <<'CONF'
# Custom QuestKeeper vhost override
# Loads before webuzoVH.conf to avoid wildcard ServerAlias capturing this subdomain.

<VirtualHost *:80>
    ServerName questkeeper.fcjamison.com

    DocumentRoot "/home/frankjamison/public_html/fcjamison.com/projects/2018Questkeeper"

    <Directory "/home/frankjamison/public_html/fcjamison.com/projects/2018Questkeeper">
        AllowOverride All
        Require all granted
        Options FollowSymLinks
    </Directory>

    # ACME HTTP-01 mapping (keep it inside this vhost so it wins)
    Alias /.well-known/acme-challenge/ "/var/www/letsencrypt/.well-known/acme-challenge/"
    <Directory "/var/www/letsencrypt/.well-known/acme-challenge/">
        AllowOverride None
        Require all granted
    </Directory>

    ErrorLog "/usr/local/apps/apache2/logs/questkeeper.fcjamison.com.error.log"
    CustomLog "/usr/local/apps/apache2/logs/questkeeper.fcjamison.com.access.log" combined

    # PHP via Webuzo PHP 8.3 socket
    <FilesMatch \.php$>
        SetHandler "proxy:unix:/usr/local/apps/php83/var/fpm-frankjamison.sock|fcgi://localhost"
    </FilesMatch>
</VirtualHost>

<VirtualHost *:443>
    ServerName questkeeper.fcjamison.com

    DocumentRoot "/home/frankjamison/public_html/fcjamison.com/projects/2018Questkeeper"

    <Directory "/home/frankjamison/public_html/fcjamison.com/projects/2018Questkeeper">
        AllowOverride All
        Require all granted
        Options FollowSymLinks
    </Directory>

    SSLEngine on

    # Must point at the QuestKeeper combined PEM (created in Step 4)
    SSLCertificateFile "/var/webuzo/users/frankjamison/ssl/questkeeper.fcjamison.com-combined.pem"

    ErrorLog "/usr/local/apps/apache2/logs/questkeeper.fcjamison.com.ssl.error.log"
    CustomLog "/usr/local/apps/apache2/logs/questkeeper.fcjamison.com.ssl.access.log" combined

    <FilesMatch \.php$>
        SetHandler "proxy:unix:/usr/local/apps/php83/var/fpm-frankjamison.sock|fcgi://localhost"
    </FilesMatch>
</VirtualHost>
CONF

/usr/local/apps/apache2/bin/httpd -t && /usr/local/apps/apache2/bin/httpd -k graceful
```

Confirm the vhost is recognized:

```bash
/usr/local/apps/apache2/bin/httpd -S | egrep -i 'questkeeper|namevhost|default server' | head -200
```

---

## 2) Set up ACME webroot and confirm it serves correctly

This setup uses certbot **webroot** challenges.

```bash
mkdir -p /var/www/letsencrypt/.well-known/acme-challenge
chown -R root:root /var/www/letsencrypt
chmod -R 755 /var/www/letsencrypt

stamp=$(date +%s)
echo "acme-ok-$stamp" > /var/www/letsencrypt/.well-known/acme-challenge/test.txt

curl -sS http://questkeeper.fcjamison.com/.well-known/acme-challenge/test.txt
```

If that curl does not return `acme-ok-<timestamp>` exactly, stop and fix the vhost mapping first.

---

## 3) Issue Let’s Encrypt cert for QuestKeeper (webroot)

```bash
certbot certonly --webroot \
  -w /var/www/letsencrypt \
  -d questkeeper.fcjamison.com \
  --email "YOUR_EMAIL_HERE" \
  --agree-tos \
  --no-eff-email

ls -la /etc/letsencrypt/live/questkeeper.fcjamison.com/
```

---

## 4) Build the Webuzo “combined PEM” and reload Apache

Webuzo expects a combined PEM in:

- `/var/webuzo/users/frankjamison/ssl/`

```bash
cat /etc/letsencrypt/live/questkeeper.fcjamison.com/fullchain.pem \
    /etc/letsencrypt/live/questkeeper.fcjamison.com/privkey.pem \
  > /var/webuzo/users/frankjamison/ssl/questkeeper.fcjamison.com-combined.pem

chmod 600 /var/webuzo/users/frankjamison/ssl/questkeeper.fcjamison.com-combined.pem

/usr/local/apps/apache2/bin/httpd -t && /usr/local/apps/apache2/bin/httpd -k graceful
```

---

## 5) Verify the site end-to-end

### PHP pipeline test (proves Apache → PHP-FPM is working)

```bash
cat > /home/frankjamison/public_html/fcjamison.com/projects/2018Questkeeper/php-test.php <<'PHP'
<?php http_response_code(200); header('Content-Type: text/plain'); echo "php-ok\n";
PHP

curl -sS -i https://questkeeper.fcjamison.com/php-test.php | head -30
```

Expected: `HTTP/1.1 200 OK` and `php-ok`.

### QuestKeeper homepage

```bash
curl -sS -i https://questkeeper.fcjamison.com/ | head -30
```

Expected: `HTTP/1.1 200 OK` and HTML.

---

## 6) If you ever see `HTTP 500` again

### A) Check Apache vhost logs

```bash
tail -n 200 /usr/local/apps/apache2/logs/questkeeper.fcjamison.com.error.log 2>/dev/null || true
tail -n 200 /usr/local/apps/apache2/logs/questkeeper.fcjamison.com.ssl.error.log 2>/dev/null || true
```

### B) Check PHP-FPM logs

```bash
ls -la /usr/local/apps/php83/var/log 2>/dev/null || true
tail -n 200 /usr/local/apps/php83/var/log/php-fpm.log | tail -200
```

If you see `server reached max_children setting`, QuestKeeper might intermittently 500 under bursts; increase the pool limits for the relevant PHP-FPM pool and reload PHP-FPM.

### C) Quick DB sanity (QuestKeeper schema)

```bash
mysql -e "USE frankjamison_questkeeper; SHOW TABLES;"
mysql -e "SHOW GRANTS FOR 'frankjamison_questkeeper_user'@'localhost';"
```

---

## Notes

- Avoid putting secrets (DB passwords) into shell history or docs.
- SSL stapling warnings (`AH02218` / `AH02604`) are usually not fatal for page loads.
