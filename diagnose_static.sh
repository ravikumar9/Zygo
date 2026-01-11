#!/bin/bash
# STATIC FILES DIAGNOSTIC SCRIPT
# Run this on your server to identify the exact issue

echo "======================================"
echo "STATIC FILES DIAGNOSTIC"
echo "======================================"
echo ""

# Get project root
PROJECT_ROOT=$(pwd)
echo "Project root: $PROJECT_ROOT"
echo ""

# Step 1: Check Django settings
echo "1. Checking Django settings..."
python manage.py diffsettings | grep -E "STATIC_ROOT|STATIC_URL|STATICFILES_DIRS"
echo ""

# Step 2: Check if collectstatic was run
echo "2. Checking if staticfiles directory exists..."
if [ -d "staticfiles" ]; then
    echo "✓ staticfiles/ directory exists"
    echo "  Files count: $(find staticfiles -type f | wc -l)"
else
    echo "✗ staticfiles/ directory NOT FOUND"
    echo "  → Run: python manage.py collectstatic --noinput"
fi
echo ""

# Step 3: Check critical static files
echo "3. Checking critical static files..."
FILES=(
    "staticfiles/admin/css/base.css"
    "staticfiles/admin/js/theme.js"
    "staticfiles/css/booking-styles.css"
    "static/css/booking-styles.css"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file exists"
    else
        echo "✗ $file MISSING"
    fi
done
echo ""

# Step 4: Check permissions
echo "4. Checking permissions on staticfiles/..."
if [ -d "staticfiles" ]; then
    ls -ld staticfiles/
    ls -l staticfiles/admin/css/base.css 2>/dev/null || echo "  (admin CSS not found)"
else
    echo "  (directory not found)"
fi
echo ""

# Step 5: Find nginx config
echo "5. Searching for nginx config..."
NGINX_CONFIGS=$(find /etc/nginx -name "*.conf" -o -name "goexplorer*" 2>/dev/null)
if [ -n "$NGINX_CONFIGS" ]; then
    echo "Found configs:"
    echo "$NGINX_CONFIGS"
else
    echo "No nginx configs found (may need sudo)"
fi
echo ""

# Step 6: Check nginx static location
echo "6. Checking nginx /static/ configuration..."
echo "Run this command to view your nginx config:"
echo "  sudo cat /etc/nginx/sites-enabled/goexplorer"
echo "  (or wherever your nginx config is)"
echo ""
echo "Look for:"
echo "  location /static/ {"
echo "      alias /ABSOLUTE/PATH/TO/staticfiles/;"
echo "  }"
echo ""

# Step 7: Test static file accessibility
echo "7. Testing if nginx user can read static files..."
if [ -f "staticfiles/admin/css/base.css" ]; then
    sudo -u www-data test -r staticfiles/admin/css/base.css && echo "✓ www-data can read static files" || echo "✗ www-data CANNOT read static files (permissions issue)"
else
    echo "  (static files not collected yet)"
fi
echo ""

# Step 8: Summary and next steps
echo "======================================"
echo "NEXT STEPS:"
echo "======================================"
echo ""

if [ ! -d "staticfiles" ]; then
    echo "🔴 CRITICAL: staticfiles/ directory missing"
    echo "   Run: python manage.py collectstatic --noinput --clear"
    echo ""
fi

if [ -d "staticfiles" ] && [ ! -f "staticfiles/admin/css/base.css" ]; then
    echo "🔴 CRITICAL: collectstatic incomplete or failed"
    echo "   Run: python manage.py collectstatic --noinput --clear"
    echo ""
fi

echo "Then check nginx config:"
echo "  sudo nginx -t"
echo "  sudo cat /etc/nginx/sites-enabled/goexplorer | grep -A 5 'location /static'"
echo ""
echo "Fix nginx location /static/ to point to:"
echo "  $PROJECT_ROOT/staticfiles/"
echo ""
echo "After fixing:"
echo "  sudo systemctl reload nginx"
echo "  sudo systemctl restart gunicorn"
