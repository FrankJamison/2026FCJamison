# SMTP setup (Leave a Reply)

The “Leave a Reply” form sends email using SMTP via these environment variables (read in `homeViews.py`).

## Required environment variables

- `SMTP_HOST` — SMTP server hostname (example: `smtp.office365.com`, `smtp.gmail.com`, etc)
- `SMTP_PORT` — usually `587` (STARTTLS) or `465` (SSL)
- `SMTP_USER` — SMTP username (usually `frank@fcjamison.com`)
- `SMTP_PASSWORD` — SMTP/app password

If you only have **IMAP** settings: those are for receiving mail, not sending. You still need the **SMTP** host/port for sending.

## Optional environment variables

- `SMTP_FROM` — defaults to `frank@fcjamison.com`
- `SMTP_TO` — defaults to `frank@fcjamison.com`
- `SMTP_USE_TLS` — defaults to `1` (STARTTLS). Set to `0` to disable.
- `SMTP_USE_SSL` — defaults to `0`. Set to `1` if your provider requires SSL on connect (usually port `465`).
- `SMTP_CA_FILE` — path to a CA bundle file to trust (use this if your mail server uses a private/self-signed CA).
- `SMTP_ALLOW_INVALID_CERT` — dev-only escape hatch to disable certificate verification (`1` to enable). Do not use in production.

## Local dev on Windows

### Option A: PowerShell (current terminal session only)

```powershell
$env:SMTP_HOST = "mail.fcjamison.com"
$env:SMTP_PORT = "465"
$env:SMTP_USER = "frank@fcjamison.com"
$env:SMTP_PASSWORD = "YOUR_PASSWORD_OR_APP_PASSWORD"
$env:SMTP_FROM = "frank@fcjamison.com"
$env:SMTP_TO = "frank@fcjamison.com"
$env:SMTP_USE_TLS = "0"
$env:SMTP_USE_SSL = "1"
```

Restart the Flask app after setting these.

### Option B: System/User environment variables

Set the same variables in Windows “Environment Variables”, then restart VS Code and Flask.

## Notes

- “From frank@fcjamison.com” requires the SMTP account/provider to allow sending as that address.
- The code sets `Reply-To` to the visitor’s email so you can reply easily.
- If you get TLS verification errors mentioning `Avast Web/Mail Shield` or “SSL/TLS scanning”, your local antivirus is intercepting the SMTP connection. Disable SSL/TLS scanning for SMTP (preferred) or set `SMTP_ALLOW_INVALID_CERT=1` for local development only.

## Common settings for `mail.fcjamison.com`

If your provider says “IMAP with SSL”, that often pairs with **SMTP over SSL**:

- `SMTP_HOST=mail.fcjamison.com`
- `SMTP_PORT=465`
- `SMTP_USE_SSL=1`
- `SMTP_USE_TLS=0`

If that doesn’t work, the other common option is STARTTLS:

- `SMTP_PORT=587`
- `SMTP_USE_TLS=1`
- `SMTP_USE_SSL=0`
