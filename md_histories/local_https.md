# Local HTTPS Development Setup

**Purpose:** Run GoExplorer with HTTPS on your local machine for development and testing.

**Environment:** Windows with Python venv

---

## Prerequisites

- Python 3.9+
- Virtual environment activated: `.venv-1\Scripts\Activate.ps1`
- Django project running locally

---

## Step 1: Install mkcert

`mkcert` generates locally-trusted development certificates.

### On Windows (PowerShell as Administrator)

```powershell
# Using Chocolatey (if installed)
choco install mkcert

# OR download manually from:
# https://github.com/FiloSottile/mkcert/releases
# (Pick mkcert-v*-windows-amd64.exe)

# Verify installation
mkcert --version
```

---

## Step 2: Create Local CA and Certificates

```powershell
# Create a local Certificate Authority (one-time)
mkcert -install

# Generate certificate for localhost
cd C:\Users\ravi9\Downloads\cgpt\Go_explorer_clear
mkcert localhost 127.0.0.1 ::1
```

This creates:
- `localhost+2-key.pem` — Private key
- `localhost+2.pem` — Certificate

---

## Step 3: Install django-extensions and pyopenssl

```powershell
# Activate venv
.\.venv-1\Scripts\Activate.ps1

# Install packages
pip install django-extensions pyopenssl
```

---

## Step 4: Run Django with HTTPS

### Using runserver_plus (Recommended)

```powershell
# From project root
python manage.py runserver_plus \
  --cert-file localhost+2.pem \
  --key-file localhost+2-key.pem \
  0.0.0.0:8000
```

Or on Windows:

```powershell
python manage.py runserver_plus `
  --cert-file localhost+2.pem `
  --key-file localhost+2-key.pem `
  0.0.0.0:8000
```

---

## Step 5: Access via HTTPS

Open browser to:

- **https://localhost:8000** — Standard localhost
- **https://127.0.0.1:8000** — IP loopback

Both will show a green padlock 🔒 (browser trusts the certificate).

---

## Troubleshooting

### Certificate Not Trusted

**Error:** Browser shows "Your connection is not private"

**Fix:**
```powershell
# Reinstall CA
mkcert -install

# Clear browser cache and try again
```

### Port Already in Use

**Error:** `Address already in use`

**Fix:**
```powershell
# Find process using port 8000
Get-NetTCPConnection -LocalPort 8000

# Kill it if needed (e.g., Python.exe)
# Or use a different port:
python manage.py runserver_plus \
  --cert-file localhost+2.pem \
  --key-file localhost+2-key.pem \
  0.0.0.0:8001
```

### File Not Found Errors

**Error:** `FileNotFoundError: localhost+2.pem`

**Fix:**
- Ensure .pem files are in project root
- Specify full path if needed:

```powershell
python manage.py runserver_plus \
  --cert-file C:\Users\ravi9\Downloads\cgpt\Go_explorer_clear\localhost+2.pem \
  --key-file C:\Users\ravi9\Downloads\cgpt\Go_explorer_clear\localhost+2-key.pem \
  0.0.0.0:8000
```

---

## Testing HTTPS Locally

### Test HTTP → HTTPS Redirect (Disabled Locally)
Local Django does NOT redirect HTTP → HTTPS (only on production when `DEBUG=False`).

To test redirects locally:

```python
# Temporarily in settings.py for testing:
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

Then access http://localhost:8000 → should redirect to https://localhost:8000

**Remember to remove after testing!**

### Test Booking Flow on HTTPS

1. **Start Django on HTTPS**
2. **Login:** https://localhost:8000/users/login
3. **Browse buses:** https://localhost:8000/buses/
4. **Book a bus:** Select seats → confirm
5. **Check JS console:** No errors

### Verify Certificate

```powershell
# View cert details
openssl x509 -in localhost+2.pem -text -noout
```

---

## Key Files

| File | Purpose |
|------|---------|
| `localhost+2.pem` | Public certificate |
| `localhost+2-key.pem` | Private key |
| `.venv-1/` | Virtual environment |
| `goexplorer/settings.py` | Django config (no HTTPS forcing locally) |

---

## Common Tasks

### Stop HTTPS Server
```powershell
# Press Ctrl+C in terminal
```

### Uninstall mkcert CA (Optional)
```powershell
mkcert -uninstall
```

### Regenerate Certificates
```powershell
# Remove old ones
Remove-Item localhost+2.pem, localhost+2-key.pem

# Generate new
mkcert localhost 127.0.0.1 ::1
```

---

## Notes

- **Local HTTPS is NOT enforced** — Django `settings.py` has redirects disabled when `DEBUG=True`
- **Certificates valid for 10 years** (mkcert default)
- **Browser will trust** because mkcert installed a local CA
- **Never commit** .pem files to git
- **Only for development** — Production uses Let's Encrypt via Certbot
