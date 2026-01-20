# 🔧 Cron Job Setup Instructions

## Expire Old Bookings (Inventory Release)

**Command:** `python manage.py expire_old_bookings`  
**Frequency:** Every 5 minutes  
**Purpose:** Auto-expire bookings past 10-minute deadline, release inventory

### On Linux/Unix Server:

```bash
# Edit crontab
crontab -e

# Add this line:
*/5 * * * * cd /path/to/goexplorer && /path/to/venv/bin/python manage.py expire_old_bookings >> /var/log/goexplorer-expire.log 2>&1
```

### On Windows (using Task Scheduler):

```powershell
# Create a batch file: C:\scripts\expire-bookings.bat
@echo off
cd C:\Users\ravi9\Downloads\cgpt\Go_explorer_clear
C:\Users\ravi9\Downloads\cgpt\Go_explorer_clear\.venv-1\Scripts\python.exe manage.py expire_old_bookings >> C:\logs\expire-bookings.log 2>&1
```

Then create a Task Scheduler task:
- Trigger: Repeat every 5 minutes
- Action: Run `C:\scripts\expire-bookings.bat`

### Verification:

```bash
# Test with dry-run (shows what would expire)
python manage.py expire_old_bookings --dry-run

# Monitor logs
tail -f /var/log/goexplorer-expire.log
```

**Expected Log Output:**
```
[BOOKING_EXPIRED] booking=abc123 user=test@example.com reserved_at=... deadline=...
Expired: abc123 (user: test@example.com)
```

