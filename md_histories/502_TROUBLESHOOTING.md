# 502 Bad Gateway - IMMEDIATE TROUBLESHOOTING

## Quick Fix (Run on Server)

```bash
# SSH into server
ssh deployer@goexplorer-dev.cloud

# Option 1: Run comprehensive diagnostic (RECOMMENDED)
bash diagnose_502_remote.sh

# Option 2: Manual quick restart
sudo systemctl stop gunicorn-goexplorer
sudo rm -rf /run/gunicorn-goexplorer
sudo systemctl start gunicorn-goexplorer
sleep 3
sudo systemctl reload nginx

# Check if fixed
curl http://localhost/
# Should show HTML, not 502
```

---

## Step-by-Step Manual Diagnosis

### 1. Check Gunicorn is Running
```bash
sudo systemctl status gunicorn-goexplorer
# Should say "active (running)"

# If not running:
sudo systemctl start gunicorn-goexplorer
```

### 2. Check Socket Exists
```bash
ls -la /run/gunicorn-goexplorer/goexplorer.sock
# Should show socket file with permissions like: srw-rw----

# If missing:
sudo systemctl restart gunicorn-goexplorer
sleep 3
ls -la /run/gunicorn-goexplorer/goexplorer.sock
```

### 3. Check Nginx Config
```bash
sudo nginx -t
# Should say "successful"

# If error, check config:
cat /etc/nginx/sites-available/goexplorer-dev | grep -A 5 "upstream\|proxy_pass"
```

### 4. Check Nginx is Running
```bash
sudo systemctl status nginx
# Should say "active (running)"

# If not:
sudo systemctl start nginx
```

### 5. View Error Logs
```bash
# Gunicorn errors:
sudo journalctl -u gunicorn-goexplorer -n 50

# Nginx errors:
sudo tail -f /var/log/nginx/error.log

# Django errors (if exists):
tail -f /home/deployer/goexplorer/logs/error.log
```

### 6. Test Connectivity
```bash
# Local test (bypasses DNS)
curl -I http://localhost/

# Via domain (after fixing)
curl -I http://goexplorer-dev.cloud/
```

---

## Common 502 Causes & Fixes

| Issue | Symptom | Fix |
|-------|---------|-----|
| **Socket doesn't exist** | `connect() failed (2: No such file or directory)` in logs | `sudo systemctl restart gunicorn-goexplorer` |
| **Permission denied** | `connect() failed (13: Permission denied)` | Check socket permissions: `ls -la /run/gunicorn-goexplorer/` |
| **Port in use** | Gunicorn fails to start | `sudo lsof -i :8000` find PID, `sudo kill -9 PID` |
| **Django errors** | Gunicorn exits immediately | Check: `python manage.py check` |
| **Nginx not configured** | No upstream block | Verify `/etc/nginx/sites-available/goexplorer-dev` has `upstream goexplorer_app` |
| **Timeout** | Request hangs then 504 | Increase proxy timeouts in Nginx |

---

## Full Restart Procedure

```bash
# 1. Stop both services
sudo systemctl stop gunicorn-goexplorer
sudo systemctl stop nginx

# 2. Clean up
sudo rm -rf /run/gunicorn-goexplorer

# 3. Start Gunicorn and wait
sudo systemctl start gunicorn-goexplorer
sleep 5

# 4. Verify socket
ls -la /run/gunicorn-goexplorer/goexplorer.sock
# Must exist before starting Nginx

# 5. Start Nginx
sudo systemctl start nginx

# 6. Test
curl http://localhost/
```

---

## Deployment from GitHub

If code changes were made:

```bash
cd /home/deployer/goexplorer
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check

# Then restart
sudo systemctl restart gunicorn-goexplorer
sleep 3
sudo systemctl reload nginx
```

---

## Useful Commands

```bash
# Monitor in real-time
sudo journalctl -u gunicorn-goexplorer -f

# Check all systemd services
sudo systemctl list-units --type=service | grep -E "nginx|gunicorn"

# View Nginx config
sudo nginx -T | grep -E "upstream|proxy_pass"

# Check listening ports
sudo netstat -tulpn | grep -E "nginx|gunicorn"
```

---

## When to Escalate

If after running `diagnose_502_remote.sh` and applying fixes the 502 persists:

1. **Check Python/Django issues:**
   ```bash
   cd /home/deployer/goexplorer
   source .venv/bin/activate
   python manage.py check
   ```

2. **Check database:**
   ```bash
   python manage.py dbshell
   SELECT 1;
   ```

3. **View full Gunicorn logs:**
   ```bash
   sudo journalctl -u gunicorn-goexplorer -n 100
   ```

4. **Manually test Gunicorn:**
   ```bash
   cd /home/deployer/goexplorer
   source .venv/bin/activate
   gunicorn --bind 127.0.0.1:8000 goexplorer.wsgi:application
   # Then test: curl http://127.0.0.1:8000/
   ```
