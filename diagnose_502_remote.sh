#!/bin/bash
# ============================================================================
# COMPREHENSIVE 502 DIAGNOSTIC - RUN ON SERVER VIA SSH
# Usage: ssh deployer@goexplorer-dev.cloud 'bash -s' < diagnose_502_remote.sh
# Or copy to server and: bash diagnose_502_remote.sh
# ============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

clear

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     COMPREHENSIVE 502 DIAGNOSTIC & AUTO-FIX                ║${NC}"
echo -e "${BLUE}║     GoExplorer Production Debug                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"

PROJECT_PATH="/home/deployer/goexplorer"
SOCKET_PATH="/run/gunicorn-goexplorer/goexplorer.sock"

# ============================================================================
# SECTION 1: ENVIRONMENT CHECK
# ============================================================================
echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}[1/10] ENVIRONMENT & PERMISSIONS${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo "Current user: $(whoami)"
echo "Project path: $PROJECT_PATH"
echo "Socket path: $SOCKET_PATH"
echo ""

if [ -d "$PROJECT_PATH" ]; then
    echo -e "${GREEN}✓ Project directory exists${NC}"
    ls -ld "$PROJECT_PATH"
else
    echo -e "${RED}✗ Project directory NOT found!${NC}"
    exit 1
fi

echo ""
echo "Project ownership and permissions:"
ls -ld "$PROJECT_PATH"
ls -la "$PROJECT_PATH/.venv" 2>/dev/null | head -3 || echo "  ⚠️  .venv not found"

# ============================================================================
# SECTION 2: GUNICORN SERVICE STATUS
# ============================================================================
echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}[2/10] GUNICORN SERVICE STATUS${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if systemctl is-active --quiet gunicorn-goexplorer; then
    echo -e "${GREEN}✓ Service is ACTIVE${NC}"
else
    echo -e "${RED}✗ Service is INACTIVE${NC}"
fi

echo ""
echo "Full status:"
sudo systemctl status gunicorn-goexplorer --no-pager || true

echo ""
echo "Process info:"
ps aux | grep -E "gunicorn|goexplorer" | grep -v grep || echo "  No gunicorn process found!"

# ============================================================================
# SECTION 3: SOCKET STATUS
# ============================================================================
echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}[3/10] SOCKET STATUS${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

SOCKET_DIR=$(dirname "$SOCKET_PATH")

echo "Socket directory: $SOCKET_DIR"
if [ -d "$SOCKET_DIR" ]; then
    echo -e "${GREEN}✓ Directory exists${NC}"
    ls -ld "$SOCKET_DIR"
    echo ""
    echo "Contents:"
    ls -la "$SOCKET_DIR"
else
    echo -e "${RED}✗ Directory DOES NOT EXIST${NC}"
fi

echo ""
echo "Socket file: $SOCKET_PATH"
if [ -S "$SOCKET_PATH" ]; then
    echo -e "${GREEN}✓ Socket EXISTS${NC}"
    ls -la "$SOCKET_PATH"
    stat "$SOCKET_PATH"
else
    echo -e "${RED}✗ Socket DOES NOT EXIST${NC}"
fi

# ============================================================================
# SECTION 4: NGINX STATUS & CONFIG
# ============================================================================
echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}[4/10] NGINX STATUS & CONFIG${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✓ Nginx is ACTIVE${NC}"
else
    echo -e "${RED}✗ Nginx is INACTIVE${NC}"
fi

echo ""
echo "Nginx status:"
sudo systemctl status nginx --no-pager | head -7

echo ""
echo "Nginx config syntax check:"
sudo nginx -t 2>&1 || echo "  Config has errors!"

echo ""
echo "Active Nginx config files:"
ls -la /etc/nginx/sites-enabled/goexplorer-dev 2>/dev/null || echo "  /etc/nginx/sites-enabled/goexplorer-dev NOT found"
echo ""

if [ -f "/etc/nginx/sites-available/goexplorer-dev" ]; then
    echo "Nginx upstream config:"
    grep -A 2 "upstream" /etc/nginx/sites-available/goexplorer-dev || echo "  No upstream block found"
    echo ""
    echo "Proxy pass lines:"
    grep -E "proxy_pass|proxy_set_header" /etc/nginx/sites-available/goexplorer-dev | head -10
fi

# ============================================================================
# SECTION 5: DJANGO CHECK
# ============================================================================
echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}[5/10] DJANGO SYSTEM CHECK${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

cd "$PROJECT_PATH"
source .venv/bin/activate 2>/dev/null || source /opt/goexplorer-venv/bin/activate || {
    echo -e "${RED}✗ Cannot activate venv!${NC}"
    exit 1
}

echo "Python: $(python --version)"
echo "Django: $(python -c 'import django; print(django.get_version())')"
echo ""

echo "Running django check..."
python manage.py check 2>&1 | head -20

# ============================================================================
# SECTION 6: DATABASE CONNECTION
# ============================================================================
echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}[6/10] DATABASE CONNECTION${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

python manage.py dbshell <<EOF
SELECT 1;
EOF
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database connection OK${NC}"
else
    echo -e "${RED}✗ Database connection FAILED${NC}"
fi

# ============================================================================
# SECTION 7: LOG FILES
# ============================================================================
echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}[7/10] RECENT ERROR LOGS${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo "Gunicorn journalctl (last 30 lines):"
echo "─────────────────────────────────────"
journalctl -u gunicorn-goexplorer -n 30 --no-pager 2>/dev/null | tail -15 || echo "  No logs available"

echo ""
echo "Nginx error log (last 20 lines):"
echo "─────────────────────────────────────"
sudo tail -20 /var/log/nginx/error.log 2>/dev/null || echo "  Cannot read nginx error log"

echo ""
echo "Django error log (if exists):"
echo "─────────────────────────────────────"
tail -20 "$PROJECT_PATH/logs/error.log" 2>/dev/null || echo "  No Django error log found"

# ============================================================================
# SECTION 8: CONNECTIVITY TEST
# ============================================================================
echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}[8/10] CONNECTIVITY TESTS${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo "Test 1: Localhost:8000 (direct)"
curl -s -I http://localhost:8000/ 2>&1 | head -5 || echo "  Connection failed"

echo ""
echo "Test 2: Localhost:80 (nginx proxy)"
curl -s -I http://localhost/ 2>&1 | head -5 || echo "  Connection failed"

echo ""
echo "Test 3: Domain via Nginx"
curl -s -I http://goexplorer-dev.cloud/ 2>&1 | head -5 || echo "  Connection failed"

# ============================================================================
# SECTION 9: SUMMARY & RECOMMENDATIONS
# ============================================================================
echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}[9/10] DIAGNOSIS SUMMARY${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

ISSUES=0

if ! systemctl is-active --quiet gunicorn-goexplorer; then
    echo -e "${RED}✗ Issue 1: Gunicorn is NOT running${NC}"
    ISSUES=$((ISSUES + 1))
fi

if [ ! -S "$SOCKET_PATH" ]; then
    echo -e "${RED}✗ Issue 2: Socket does not exist${NC}"
    ISSUES=$((ISSUES + 1))
fi

if ! sudo nginx -t >/dev/null 2>&1; then
    echo -e "${RED}✗ Issue 3: Nginx config has errors${NC}"
    ISSUES=$((ISSUES + 1))
fi

if ! systemctl is-active --quiet nginx; then
    echo -e "${RED}✗ Issue 4: Nginx is not running${NC}"
    ISSUES=$((ISSUES + 1))
fi

if [ $ISSUES -eq 0 ]; then
    echo -e "${GREEN}✓ No obvious issues found (socket exists, services running)${NC}"
    echo "  Check logs for silent errors"
else
    echo -e "${YELLOW}Found $ISSUES issue(s) - see below for fixes${NC}"
fi

# ============================================================================
# SECTION 10: AUTO-FIX OPTIONS
# ============================================================================
echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}[10/10] AUTO-FIX PROCEDURE${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

read -p "Do you want to apply automatic fixes? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Applying fixes..."
    
    echo "1. Stopping Gunicorn..."
    sudo systemctl stop gunicorn-goexplorer || true
    sleep 1
    
    echo "2. Cleaning socket..."
    sudo rm -rf /run/gunicorn-goexplorer 2>/dev/null || true
    
    echo "3. Starting Gunicorn..."
    sudo systemctl start gunicorn-goexplorer
    
    echo "4. Waiting for socket..."
    for i in {1..10}; do
        if [ -S "$SOCKET_PATH" ]; then
            echo -e "${GREEN}✓ Socket created${NC}"
            break
        fi
        echo "  Waiting... ($i/10)"
        sleep 1
    done
    
    echo "5. Reloading Nginx..."
    sudo systemctl reload nginx
    
    sleep 2
    
    echo ""
    echo "Testing..."
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/ 2>/dev/null || echo "000")
    
    if [ "$RESPONSE" = "200" ] || [ "$RESPONSE" = "301" ]; then
        echo -e "${GREEN}✓ Fixed! Response: HTTP $RESPONSE${NC}"
    else
        echo -e "${RED}✗ Still getting HTTP $RESPONSE${NC}"
        echo "Check logs: journalctl -u gunicorn-goexplorer -f"
    fi
fi

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          DIAGNOSTIC COMPLETE                              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
