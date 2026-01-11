#!/bin/bash
#
# SERVER DEPLOYMENT SCRIPT - STRICT DATA DISCIPLINE
# Execute on goexplorer-dev.cloud after SSH login
#
# Prerequisites:
# - SSH: ssh deployer@goexplorer-dev.cloud (password: Thepowerof@9)
# - This script must be run from the project directory
#
# Usage: bash deploy_strict_discipline.sh
#

set -e  # Exit on any error

echo "============================================================"
echo "GOEXPLORER - STRICT DATA DISCIPLINE DEPLOYMENT"
echo "Server: goexplorer-dev.cloud"
echo "Date: $(date)"
echo "============================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Verify current directory
echo "Step 1: Verify project directory..."
if [ ! -f "manage.py" ]; then
    echo -e "${RED}ERROR: manage.py not found. Are you in the project directory?${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Project directory verified${NC}"
echo ""

# Step 2: Pull latest code
echo "Step 2: Pull latest code from git..."
git fetch origin
git pull origin main
echo -e "${GREEN}✓ Code updated${NC}"
echo ""

# Step 3: Activate virtual environment
echo "Step 3: Activate virtual environment..."
if [ -d "venv" ]; then
    source venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
elif [ -d ".venv" ]; then
    source .venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
else
    echo -e "${RED}ERROR: No virtual environment found (venv or .venv)${NC}"
    exit 1
fi
echo ""

# Step 4: Install/Update dependencies
echo "Step 4: Install/Update dependencies..."
pip install -r requirements.txt --quiet
echo -e "${GREEN}✓ Dependencies updated${NC}"
echo ""

# Step 5: Apply database migrations
echo "Step 5: Apply database migrations..."
python manage.py migrate --noinput
echo -e "${GREEN}✓ Migrations applied${NC}"
echo ""

# Step 6: CRITICAL - Flush database
echo "Step 6: FLUSH DATABASE (delete all data)..."
echo -e "${YELLOW}⚠️  WARNING: This will DELETE ALL existing data!${NC}"
echo -e "${YELLOW}⚠️  Press Ctrl+C within 5 seconds to abort...${NC}"
sleep 5
python manage.py flush --noinput
echo -e "${GREEN}✓ Database flushed${NC}"
echo ""

# Step 7: Seed fresh data
echo "Step 7: Seed fresh data (seed_all)..."
python manage.py seed_all --env=local
echo -e "${GREEN}✓ Data seeded${NC}"
echo ""

# Step 8: MANDATORY - Validate seed parity
echo "Step 8: Validate seed parity..."
python manage.py validate_seed
VALIDATE_EXIT_CODE=$?

if [ $VALIDATE_EXIT_CODE -ne 0 ]; then
    echo -e "${RED}✗ SEED VALIDATION FAILED!${NC}"
    echo -e "${RED}Deployment aborted. Fix issues and redeploy.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Seed parity validated${NC}"
echo ""

# Step 9: Run E2E verification
echo "Step 9: Run E2E verification (33 tests)..."
python verify_e2e.py
E2E_EXIT_CODE=$?

if [ $E2E_EXIT_CODE -ne 0 ]; then
    echo -e "${RED}✗ E2E VERIFICATION FAILED!${NC}"
    echo -e "${RED}Deployment aborted. Fix issues and redeploy.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ E2E verification passed (33/33 tests)${NC}"
echo ""

# Step 10: Collect static files
echo "Step 10: Collect static files..."
python manage.py collectstatic --noinput
echo -e "${GREEN}✓ Static files collected${NC}"
echo ""

# Step 11: Restart services
echo "Step 11: Restart services..."
echo "Restarting Gunicorn..."
sudo systemctl restart gunicorn || echo -e "${YELLOW}⚠️  Manual restart may be required${NC}"

echo "Restarting Nginx..."
sudo systemctl restart nginx || echo -e "${YELLOW}⚠️  Manual restart may be required${NC}"

echo -e "${GREEN}✓ Services restarted${NC}"
echo ""

# Step 12: Start background worker (optional)
echo "Step 12: Start background worker (optional)..."
echo "For auto-expire task, run manually:"
echo "  python manage.py rqworker default &"
echo "Or configure systemd service for production."
echo ""

# Final verification
echo "============================================================"
echo -e "${GREEN}✓ DEPLOYMENT COMPLETE${NC}"
echo "============================================================"
echo ""
echo "POST-DEPLOYMENT VERIFICATION:"
echo "1. Visit: https://goexplorer-dev.cloud/admin/"
echo "2. Login with superuser credentials"
echo "3. Verify data counts:"
echo "   - Hotels: 16"
echo "   - Packages: 5"
echo "   - Buses: 2"
echo "   - Bus Operators: 2"
echo "   - Wallets: 1 (testuser)"
echo "4. Test booking flow:"
echo "   - Login as testuser/testpass123"
echo "   - Create booking (should be RESERVED)"
echo "   - Complete payment (should become CONFIRMED)"
echo "   - Check wallet balance (should decrease)"
echo ""
echo "MONITOR LOGS:"
echo "  tail -f /var/log/gunicorn/error.log"
echo "  tail -f /var/log/nginx/error.log"
echo ""
echo "If any issues, check DEPLOYMENT_READINESS.md for troubleshooting."
echo ""
