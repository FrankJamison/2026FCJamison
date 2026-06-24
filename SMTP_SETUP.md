# SMTP Setup

This document defines a secure and operationally sound SMTP setup for form notifications used by:

- POST /contact
- POST /leave-reply

The implementation is in homeViews.py and sends mail through SMTP with TLS.

## 1. Runtime Behavior (Source of Truth)

The app resolves SMTP settings as follows:

- SMTP_PORT defaults to 465
- SMTP_USE_SSL defaults to 1 (implicit TLS, SMTPS)
- SMTP_USE_TLS defaults to 0 (STARTTLS disabled unless enabled)
- SMTP_FROM defaults to SMTP_USER
- SMTP_TO defaults to SMTP_USER
- SMTP_ALLOW_INVALID_CERT defaults to 0 (certificate validation ON)
- SMTP_CA_FILE optional custom trust bundle path

Validation requirements in code:

- SMTP_HOST must be set
- SMTP_FROM must resolve to non-empty
- SMTP_TO must resolve to non-empty
- SMTP_PORT must be numeric

If SMTP_USER is set, authentication login is attempted.

## 2. Required and Optional Variables

### Required for production

- SMTP_HOST: SMTP server hostname
- SMTP_PORT: 465 (SMTPS) or 587 (STARTTLS)
- SMTP_FROM: sender envelope/header address
- SMTP_TO: notification recipient address

### Usually required (authenticated providers)

- SMTP_USER: SMTP username
- SMTP_PASSWORD: SMTP password or API key

### Optional

- SMTP_USE_SSL: 1 for SMTPS (port 465), 0 otherwise
- SMTP_USE_TLS: 1 for STARTTLS (port 587), 0 otherwise
- SMTP_CA_FILE: custom CA bundle path for private/self-signed chains
- SMTP_ALLOW_INVALID_CERT: dev-only escape hatch; never enable in production

## 3. Recommended Secure Modes

Choose exactly one transport mode:

### Mode A (recommended default): SMTPS

- SMTP_PORT=465
- SMTP_USE_SSL=1
- SMTP_USE_TLS=0

### Mode B: STARTTLS

- SMTP_PORT=587
- SMTP_USE_SSL=0
- SMTP_USE_TLS=1

Do not enable both SMTP_USE_SSL and SMTP_USE_TLS at the same time.

## 4. Production Environment Examples

### 4.1 Linux systemd service (recommended)

Create or edit your unit override:

```bash
sudo systemctl edit fcjamison
```

Add:

```ini
[Service]
Environment="SMTP_HOST=smtp.sendgrid.net"
Environment="SMTP_PORT=465"
Environment="SMTP_USER=apikey"
Environment="SMTP_PASSWORD=REPLACE_WITH_SECRET"
Environment="SMTP_FROM=no-reply@fcjamison.com"
Environment="SMTP_TO=frank@fcjamison.com"
Environment="SMTP_USE_SSL=1"
Environment="SMTP_USE_TLS=0"
Environment="SMTP_ALLOW_INVALID_CERT=0"
```

Apply and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart fcjamison
sudo systemctl status fcjamison --no-pager
```

### 4.2 .env file (single-host deployments)

Use only where filesystem access is controlled and backups are encrypted.

```dotenv
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=465
SMTP_USER=apikey
SMTP_PASSWORD=REPLACE_WITH_SECRET
SMTP_FROM=no-reply@fcjamison.com
SMTP_TO=frank@fcjamison.com
SMTP_USE_SSL=1
SMTP_USE_TLS=0
SMTP_ALLOW_INVALID_CERT=0
```

File permissions:

```bash
chmod 600 .env
chown <app_user>:<app_group> .env
```

## 5. Provider Blueprints

### SendGrid

- SMTP_HOST=smtp.sendgrid.net
- SMTP_PORT=465 (or 587)
- SMTP_USER=apikey
- SMTP_PASSWORD=<SendGrid API key>

### Mailgun

- SMTP_HOST=smtp.mailgun.org
- SMTP_PORT=465 (or 587)
- SMTP_USER=postmaster@<your-domain>
- SMTP_PASSWORD=<Mailgun SMTP password>

### Office 365

- SMTP_HOST=smtp.office365.com
- SMTP_PORT=587
- SMTP_USE_SSL=0
- SMTP_USE_TLS=1
- SMTP_USER=<mailbox>
- SMTP_PASSWORD=<app password or policy-compliant credential>

### Gmail Workspace

- SMTP_HOST=smtp.gmail.com
- SMTP_PORT=587
- SMTP_USE_SSL=0
- SMTP_USE_TLS=1
- SMTP_USER=<mailbox>
- SMTP_PASSWORD=<app password>

## 6. Operational Hardening

### Secrets management

- Do not commit credentials to git.
- Prefer environment injection from secret stores (Vault, AWS SSM, Azure Key Vault, Doppler, 1Password Connect).
- Rotate SMTP_PASSWORD/API keys on a schedule (at least every 90 days).

### Identity and deliverability

- Ensure SMTP_FROM is a verified sender/domain in your provider.
- Configure SPF, DKIM, and DMARC for your sending domain.
- Keep SMTP_FROM aligned with your authenticated domain to avoid rejection/spam scoring.

### TLS and trust

- Keep SMTP_ALLOW_INVALID_CERT=0 in production.
- Use SMTP_CA_FILE only when a private CA is required.
- Monitor certificate expiry for private mail infrastructure.

## 7. Verification and Smoke Testing

### App-level validation

1. Restart the app after setting environment variables.
2. Submit /contact with a real reachable email in the form.
3. Confirm:
   - HTTP response is ok: true
   - a CSV row is written under data/
   - notification email arrives in SMTP_TO mailbox

### Connectivity check from host

SMTPS 465:

```bash
openssl s_client -connect <SMTP_HOST>:465 -servername <SMTP_HOST> -brief
```

STARTTLS 587:

```bash
openssl s_client -starttls smtp -connect <SMTP_HOST>:587 -servername <SMTP_HOST> -brief
```

## 8. Troubleshooting Playbook

### Authentication failed

Symptoms:

- Email send failed: authentication failed / invalid login

Actions:

1. Verify SMTP_USER and SMTP_PASSWORD
2. Confirm provider requires API key format (for example, SendGrid uses SMTP_USER=apikey)
3. Validate account policy (MFA/app password requirements)

### TLS handshake or certificate errors

Symptoms:

- certificate verify failed
- hostname mismatch

Actions:

1. Verify host and port pair are correct
2. Ensure the server cert chain is valid for the configured hostname
3. If private CA is used, set SMTP_CA_FILE
4. Do not use SMTP_ALLOW_INVALID_CERT in production

### Timeouts or connection refused

Actions:

1. Confirm outbound firewall rules allow SMTP_HOST:SMTP_PORT
2. Confirm provider is reachable from server network
3. Increase network observability (host firewall logs, provider status page)

### Emails not delivered (but send succeeds)

Actions:

1. Check spam/quarantine inboxes
2. Verify SPF, DKIM, DMARC
3. Review provider suppression/bounce lists
4. Ensure SMTP_FROM domain is verified and permitted

## 9. Production Checklist

- SMTP_HOST set
- SMTP_PORT set correctly for selected mode
- SMTP_USE_SSL / SMTP_USE_TLS configured as one valid pair
- SMTP_USER and SMTP_PASSWORD set (if provider requires auth)
- SMTP_FROM and SMTP_TO set explicitly
- SMTP_ALLOW_INVALID_CERT=0
- SPF, DKIM, DMARC configured
- Secrets managed outside git
- Form submission smoke test passed
- Delivery verified in target mailbox

## 10. Notes for This Repository

- The app writes form payloads to CSV and then attempts SMTP delivery.
- Reply-To is set to the visitor email when provided, allowing direct response.
- SMTP errors are returned from server-side send attempts and should be monitored in application logs.
