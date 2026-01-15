# Webuzo Apache: Add a PHP Subdomain + Let’s Encrypt (Webroot)

This is the **minimal, reproducible** procedure that got `questkeeper.fcjamison.com` working under **Webuzo-managed Apache**.

It applies to any new `*.fcjamison.com` PHP site hosted in:

- `/home/frankjamison/public_html/fcjamison.com/projects/<project>`

## Why this is needed (one-time context)

On this server, the active webserver is **Webuzo Apache**:

- `/usr/local/apps/apache2/bin/httpd`

Webuzo generates vhosts into:

- `/usr/local/apps/apache2/etc/conf.d/webuzoVH.conf` (**DO NOT EDIT**) 

That generated file contains wildcard vhosts like `ServerAlias *.fcjamison.com` which can “catch” new subdomains and redirect them to `https://fcjamison.com/`.

So the fix is to add a **separate vhost file** that loads earlier than the wildcard vhost.

---

## Variables you must choose

Set these mentally before you start:

- `SUBDOMAIN`: `questkeeper.fcjamison.com`
- `PROJECT_DIR`: `/home/frankjamison/public_html/fcjamison.com/projects/2018Questkeeper`
- `EMAIL`: your Let’s Encrypt email (e.g., `you@fcjamison.com`)

---

## Step 0 — Verify you’re touching the right Apache

SSH as root, then:

```bash
/usr/local/apps/apache2/bin/httpd -v

# Confirm it’s actually listening on :80/:443
ss -ltnp | egrep ':80|:443' || true
pgrep -a httpd || true
```

If `httpd.service` fails to start due to “address already in use”, that is expected and **not** part of this setup.

---

## Step 1 — Create a vhost file that loads before Webuzo’s wildcard

Create:

- `/usr/local/apps/apache2/etc/conf.d/00-questkeeper.fcjamison.com.conf`

Copy/paste (adjust `ServerName` + `DocumentRoot` if you’re doing a different subdomain/project):

```bash
cat > /usr/local/apps/apache2/etc/conf.d/00-questkeeper.fcjamison.com.conf <<'CONF'
# Custom vhost override (loads before webuzoVH.conf)
# Purpose: prevent wildcard *.fcjamison.com vhost from capturing this subdomain.

<VirtualHost *:80>
    ServerName questkeeper.fcjamison.com

    DocumentRoot "/home/frankjamison/public_html/fcjamison.com/projects/2018Questkeeper"

    <Directory "/home/frankjamison/public_html/fcjamison.com/projects/2018Questkeeper">
        AllowOverride All
        Require all granted
        Options FollowSymLinks
    </Directory>

    # ACME (HTTP-01) webroot mapping — keep this inside the vhost
    Alias /.well-known/acme-challenge/ "/var/www/letsencrypt/.well-known/acme-challenge/"
    <Directory "/var/www/letsencrypt/.well-known/acme-challenge/">
        AllowOverride None
        Require all granted
    </Directory>

    ErrorLog "/usr/local/apps/apache2/logs/questkeeper.fcjamison.com.error.log"
    CustomLog "/usr/local/apps/apache2/logs/questkeeper.fcjamison.com.access.log" combined

    # PHP-FPM via Webuzo PHP 8.3 socket (match the server’s working pattern)
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

    # IMPORTANT:
    # This must be replaced with a questkeeper-specific combined PEM after certbot succeeds.
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

Sanity check the vhost order:

```bash
/usr/local/apps/apache2/bin/httpd -S | egrep -i 'questkeeper|namevhost' | head -200
```

---

## Step 2 — Prepare an ACME webroot folder (HTTP-01)

This server setup used **webroot** challenges (not the Apache plugin).

```bash
mkdir -p /var/www/letsencrypt/.well-known/acme-challenge
chown -R root:root /var/www/letsencrypt
chmod -R 755 /var/www/letsencrypt

# Verify Apache actually serves this path from the filesystem
stamp=$(date +%s)
echo "acme-ok-$stamp" > /var/www/letsencrypt/.well-known/acme-challenge/test.txt
curl -sS http://questkeeper.fcjamison.com/.well-known/acme-challenge/test.txt
```

The curl output must exactly match `acme-ok-<timestamp>`. If it doesn’t, ACME will fail.

---

## Step 3 — Obtain the Let’s Encrypt cert (webroot)

Install certbot if needed, then run:

```bash
# Example webroot issuance
certbot certonly --webroot \
  -w /var/www/letsencrypt \
  -d questkeeper.fcjamison.com \
  --email "YOUR_EMAIL_HERE" \
  --agree-tos \
  --no-eff-email

ls -la /etc/letsencrypt/live/questkeeper.fcjamison.com/
```

---

## Step 4 — Build Webuzo “combined pem” and reload Apache

Webuzo expects a “combined pem” file under:

- `/var/webuzo/users/frankjamison/ssl/`

Create it:

```bash
cat /etc/letsencrypt/live/questkeeper.fcjamison.com/fullchain.pem \
    /etc/letsencrypt/live/questkeeper.fcjamison.com/privkey.pem \
  > /var/webuzo/users/frankjamison/ssl/questkeeper.fcjamison.com-combined.pem

chmod 600 /var/webuzo/users/frankjamison/ssl/questkeeper.fcjamison.com-combined.pem

/usr/local/apps/apache2/bin/httpd -t && /usr/local/apps/apache2/bin/httpd -k graceful
```

---

## Step 5 — Verify the site

Quick functional checks:

```bash
# 1) PHP pipeline check (should be 200)
cat > /home/frankjamison/public_html/fcjamison.com/projects/2018Questkeeper/php-test.php <<'PHP'
<?php http_response_code(200); header('Content-Type: text/plain'); echo "php-ok\n";
PHP

curl -sS -i https://questkeeper.fcjamison.com/php-test.php | head -30

# 2) App homepage check
curl -sS -i https://questkeeper.fcjamison.com/ | head -30
```

---

## Troubleshooting

### A) Still redirects to `fcjamison.com`

- Your vhost is being captured by the wildcard vhost.
- Ensure your file is named with a leading `00-` and lives in:
  - `/usr/local/apps/apache2/etc/conf.d/`

Then:

```bash
/usr/local/apps/apache2/bin/httpd -S | egrep -i 'questkeeper|fcjamison|default server|namevhost' | head -200
```

### B) Cert mismatch (browser shows `fcjamison.com` cert)

- The vhost is pointing at the wrong `SSLCertificateFile`.
- Fix by rebuilding the combined PEM and ensuring the vhost uses:
  - `/var/webuzo/users/frankjamison/ssl/questkeeper.fcjamison.com-combined.pem`

### C) `HTTP 500` from the app

1) Prove PHP works at all:

```bash
curl -sS -i https://questkeeper.fcjamison.com/php-test.php | head -30
```

2) If PHP works but the app 500s, inspect logs:

```bash
tail -n 200 /usr/local/apps/apache2/logs/questkeeper.fcjamison.com.error.log 2>/dev/null || true
tail -n 200 /usr/local/apps/apache2/logs/questkeeper.fcjamison.com.ssl.error.log 2>/dev/null || true

# PHP-FPM logs
ls -la /usr/local/apps/php83/var/log 2>/dev/null || true
tail -n 200 /usr/local/apps/php83/var/log/php-fpm.log | tail -200
```

3) If you see `server reached max_children setting`, you may need to raise the PHP-FPM pool limit.

### D) SSL stapling warnings

You may see errors like `AH02218` / `AH02604` about OCSP stapling. These typically **do not** break page loads and are not the cause of an app-level 500.

---

## Notes (security)

- Do not paste DB passwords into shell history or public docs.
- Prefer using least-privilege DB users (as you did with `frankjamison_questkeeper_user`).
