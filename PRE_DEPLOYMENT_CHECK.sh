#!/bin/bash
# Final Pre-Deployment Checklist

echo "═══════════════════════════════════════════════════════════"
echo "  GoExplorer Final Pre-Deployment Validation"
echo "═══════════════════════════════════════════════════════════"
echo ""

PASS=0
FAIL=0

check_file() {
    if [ -f "$1" ]; then
        echo "✓ $1 EXISTS"
        ((PASS++))
    else
        echo "✗ $1 MISSING"
        ((FAIL++))
    fi
}

check_string() {
    if grep -q "$2" "$1" 2>/dev/null; then
        echo "✓ $1 contains '$2'"
        ((PASS++))
    else
        echo "✗ $1 missing '$2'"
        ((FAIL++))
    fi
}

echo "Checking Critical Files..."
echo "───────────────────────────"
check_file "users/views.py"
check_file "users/urls.py"
check_file "buses/views.py"
check_file "templates/users/login.html"
check_file "templates/users/password_reset.html"
check_file "templates/buses/bus_list.html"
check_file "templates/bookings/confirmation.html"
check_file "templates/users/profile.html"
check_file "core/management/commands/create_e2e_test_data.py"
check_file "verify_production.py"

echo ""
echo "Checking Critical Implementations..."
echo "───────────────────────────────────"
check_string "users/views.py" "login_failed"
check_string "users/views.py" "@require_http_methods.*GET.*POST"
check_string "users/urls.py" "password.reset"
check_string "templates/users/login.html" "Forgot Password"
check_string "templates/buses/bus_list.html" "No buses found"
check_string "templates/bookings/confirmation.html" "Booking not found"
check_string "core/management/commands/create_e2e_test_data.py" "get_or_create"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "Results: $PASS passed, $FAIL failed"
echo "═══════════════════════════════════════════════════════════"
echo ""

if [ $FAIL -eq 0 ]; then
    echo "✓ All checks passed! Ready for deployment."
    exit 0
else
    echo "✗ Some checks failed. Please review above."
    exit 1
fi
