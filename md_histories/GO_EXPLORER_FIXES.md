## GoExplorer Fixes Snapshot

**Scope:** Concise reference of restoration work and JS/HTTPS fixes. Full details remain in RESTORATION_SUMMARY.md, JS_HTTPS_FIX_SUMMARY.md, and QUICK_FIX_REFERENCE.md at repo root.

### Restoration Highlights
- Rebuilt bus detail template (now complete seat layout, booking form, price calc, ladies-seat logic) and fixed URL/import issues to restore bus/package booking flows.
- Hotel flow intact; uses UUID booking redirect; list pages work without search and show graceful empty states.
- No model or URL pattern changes; core business logic untouched to avoid regressions.

### JS Safety Fixes
- Replaced inline Django variable injection in templates with json_script+JSON.parse to keep JS syntactically valid and avoid console/editor errors.
- Key files: templates/hotels/hotel_detail.html, templates/buses/bus_detail.html.

### HTTPS Enablement
- Added Nginx HTTPS config with 80→443 redirect, TLS 1.2/1.3, security headers, static/media proxying.
- Hardened Django settings for secure cookies, HSTS, and X-Forwarded-Proto trust when DEBUG is False.
- Added deploy/setup_https.sh for certbot-based certificate issuance and renewal; includes verification steps.

### Quick Pointers
- Booking redirects now consistently use booking-confirm.
- If editing templates, continue using json_script for server → JS data.
- Run deploy/setup_https.sh on the server after pulling to provision certificates and reload Nginx.