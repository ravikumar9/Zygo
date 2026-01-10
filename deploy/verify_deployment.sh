#!/bin/bash
# Post-Deployment Verification Script
# Verifies JavaScript fixes and HTTPS configuration

echo "╔════════════════════════════════════════════════════╗"
echo "║   GoExplorer Post-Deployment Verification          ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

ERRORS=0
WARNINGS=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Check Django templates for problematic JS patterns
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 Test 1: Checking templates for JavaScript issues"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

TEMPLATE_PATH="/home/deployer/goexplorer/templates"

if grep -r "const .* = {{" "$TEMPLATE_PATH" 2>/dev/null; then
    echo -e "${RED}❌ FAIL: Found direct Django variable in JavaScript${NC}"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✅ PASS: No direct Django variables in JavaScript${NC}"
fi

if grep -r "var .* = {{" "$TEMPLATE_PATH" 2>/dev/null; then
    echo -e "${RED}❌ FAIL: Found direct Django variable in JavaScript${NC}"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✅ PASS: No var assignments with Django variables${NC}"
fi

if grep -r "json_script" "$TEMPLATE_PATH/buses/bus_detail.html" "$TEMPLATE_PATH/hotels/hotel_detail.html" >/dev/null 2>&1; then
    echo -e "${GREEN}✅ PASS: json_script filter is being used${NC}"
else
    echo -e "${YELLOW}⚠️  WARNING: json_script not found in templates${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

echo ""

# Test 2: Check HTTPS configuration
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔐 Test 2: Checking HTTPS Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if certificate exists
if [ -d "/etc/letsencrypt/live/goexplorer-dev.cloud" ]; then
    echo -e "${GREEN}✅ PASS: SSL certificate directory exists${NC}"
    
    # Check certificate files
    if [ -f "/etc/letsencrypt/live/goexplorer-dev.cloud/fullchain.pem" ]; then
        echo -e "${GREEN}✅ PASS: Certificate file found${NC}"
        
        # Check certificate expiry
        EXPIRY=$(openssl x509 -enddate -noout -in /etc/letsencrypt/live/goexplorer-dev.cloud/fullchain.pem 2>/dev/null | cut -d= -f2)
        if [ -n "$EXPIRY" ]; then
            echo -e "${GREEN}✅ PASS: Certificate expires: $EXPIRY${NC}"
        fi
    else
        echo -e "${RED}❌ FAIL: Certificate file not found${NC}"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${RED}❌ FAIL: SSL certificate directory not found${NC}"
    echo "   Run: sudo ./deploy/setup_https.sh"
    ERRORS=$((ERRORS + 1))
fi

# Check Nginx configuration
if [ -f "/etc/nginx/sites-available/goexplorer-dev" ]; then
    echo -e "${GREEN}✅ PASS: Nginx configuration exists${NC}"
    
    # Check if HTTPS is configured
    if grep -q "listen 443 ssl" "/etc/nginx/sites-available/goexplorer-dev"; then
        echo -e "${GREEN}✅ PASS: HTTPS (443) configured in Nginx${NC}"
    else
        echo -e "${RED}❌ FAIL: HTTPS not configured in Nginx${NC}"
        ERRORS=$((ERRORS + 1))
    fi
    
    # Check if HTTP redirect is configured
    if grep -q "return 301 https" "/etc/nginx/sites-available/goexplorer-dev"; then
        echo -e "${GREEN}✅ PASS: HTTP → HTTPS redirect configured${NC}"
    else
        echo -e "${YELLOW}⚠️  WARNING: HTTP redirect not found${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "${RED}❌ FAIL: Nginx configuration not found${NC}"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# Test 3: Check Django security settings
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐍 Test 3: Checking Django Security Settings"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

SETTINGS_FILE="/home/deployer/goexplorer/goexplorer/settings.py"

if [ -f "$SETTINGS_FILE" ]; then
    if grep -q "SECURE_PROXY_SSL_HEADER" "$SETTINGS_FILE"; then
        echo -e "${GREEN}✅ PASS: SECURE_PROXY_SSL_HEADER configured${NC}"
    else
        echo -e "${RED}❌ FAIL: SECURE_PROXY_SSL_HEADER not set${NC}"
        ERRORS=$((ERRORS + 1))
    fi
    
    if grep -q "SECURE_SSL_REDIRECT = True" "$SETTINGS_FILE"; then
        echo -e "${GREEN}✅ PASS: SECURE_SSL_REDIRECT enabled${NC}"
    else
        echo -e "${YELLOW}⚠️  WARNING: SECURE_SSL_REDIRECT not enabled${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
    
    if grep -q "SESSION_COOKIE_SECURE = True" "$SETTINGS_FILE"; then
        echo -e "${GREEN}✅ PASS: SESSION_COOKIE_SECURE enabled${NC}"
    else
        echo -e "${YELLOW}⚠️  WARNING: SESSION_COOKIE_SECURE not enabled${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
    
    if grep -q "CSRF_COOKIE_SECURE = True" "$SETTINGS_FILE"; then
        echo -e "${GREEN}✅ PASS: CSRF_COOKIE_SECURE enabled${NC}"
    else
        echo -e "${YELLOW}⚠️  WARNING: CSRF_COOKIE_SECURE not enabled${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "${RED}❌ FAIL: Django settings file not found${NC}"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# Test 4: Live HTTPS test
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 Test 4: Live HTTPS Test"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test HTTPS
HTTPS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://goexplorer-dev.cloud 2>/dev/null || echo "000")
if [ "$HTTPS_STATUS" == "200" ] || [ "$HTTPS_STATUS" == "301" ] || [ "$HTTPS_STATUS" == "302" ]; then
    echo -e "${GREEN}✅ PASS: HTTPS responds (HTTP $HTTPS_STATUS)${NC}"
else
    echo -e "${RED}❌ FAIL: HTTPS not responding (HTTP $HTTPS_STATUS)${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Test HTTP redirect
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://goexplorer-dev.cloud 2>/dev/null || echo "000")
HTTP_LOCATION=$(curl -s -I http://goexplorer-dev.cloud 2>/dev/null | grep -i "location:" | grep -i "https" || echo "")

if [ "$HTTP_STATUS" == "301" ] || [ "$HTTP_STATUS" == "302" ]; then
    if [ -n "$HTTP_LOCATION" ]; then
        echo -e "${GREEN}✅ PASS: HTTP redirects to HTTPS (HTTP $HTTP_STATUS)${NC}"
    else
        echo -e "${YELLOW}⚠️  WARNING: HTTP redirects but not to HTTPS${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "${YELLOW}⚠️  WARNING: HTTP not redirecting (HTTP $HTTP_STATUS)${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

# Test SSL certificate
if command -v openssl >/dev/null 2>&1; then
    SSL_VERIFY=$(echo | openssl s_client -connect goexplorer-dev.cloud:443 -servername goexplorer-dev.cloud 2>/dev/null | grep "Verify return code: 0" || echo "")
    if [ -n "$SSL_VERIFY" ]; then
        echo -e "${GREEN}✅ PASS: SSL certificate is valid${NC}"
    else
        echo -e "${YELLOW}⚠️  WARNING: SSL certificate verification failed${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

echo ""

# Test 5: Service status
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 Test 5: Service Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✅ PASS: Nginx is running${NC}"
else
    echo -e "${RED}❌ FAIL: Nginx is not running${NC}"
    ERRORS=$((ERRORS + 1))
fi

if systemctl is-active --quiet gunicorn-goexplorer; then
    echo -e "${GREEN}✅ PASS: Gunicorn is running${NC}"
else
    echo -e "${RED}❌ FAIL: Gunicorn is not running${NC}"
    ERRORS=$((ERRORS + 1))
fi

if systemctl is-enabled --quiet certbot.timer 2>/dev/null; then
    echo -e "${GREEN}✅ PASS: Certbot auto-renewal enabled${NC}"
else
    echo -e "${YELLOW}⚠️  WARNING: Certbot auto-renewal not enabled${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED${NC}"
    echo ""
    echo "🎉 Deployment is successful!"
    echo "🌐 Site: https://goexplorer-dev.cloud"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  ALL TESTS PASSED WITH WARNINGS${NC}"
    echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
    echo ""
    echo "✅ Deployment is functional"
    echo "⚠️  Review warnings above"
    exit 0
else
    echo -e "${RED}❌ TESTS FAILED${NC}"
    echo -e "${RED}Errors: $ERRORS${NC}"
    echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
    echo ""
    echo "❌ Deployment has issues"
    echo "📋 Review errors above and fix before production"
    exit 1
fi
