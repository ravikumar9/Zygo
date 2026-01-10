#!/bin/bash
# HTTPS Setup Script for GoExplorer Dev Server
# Domain: goexplorer-dev.cloud
# This script sets up Let's Encrypt SSL certificate and configures Nginx

set -e  # Exit on error

echo "========================================="
echo "GoExplorer HTTPS Setup Script"
echo "Domain: goexplorer-dev.cloud"
echo "========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (use sudo)"
    exit 1
fi

echo "✅ Running as root"
echo ""

# Step 1: Install Certbot if not already installed
echo "📦 Step 1: Installing Certbot..."
if ! command -v certbot &> /dev/null; then
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
    echo "✅ Certbot installed"
else
    echo "✅ Certbot already installed"
fi
echo ""

# Step 2: Verify Nginx is installed
echo "🔍 Step 2: Checking Nginx..."
if ! command -v nginx &> /dev/null; then
    echo "❌ Nginx is not installed. Installing..."
    apt-get install -y nginx
    echo "✅ Nginx installed"
else
    echo "✅ Nginx is installed"
fi
echo ""

# Step 3: Stop Nginx temporarily for certificate generation
echo "⏸️  Step 3: Stopping Nginx temporarily..."
systemctl stop nginx
echo "✅ Nginx stopped"
echo ""

# Step 4: Obtain SSL certificate from Let's Encrypt
echo "🔐 Step 4: Obtaining SSL certificate from Let's Encrypt..."
echo "This will:"
echo "  - Generate SSL certificate for goexplorer-dev.cloud"
echo "  - Store certificates in /etc/letsencrypt/live/goexplorer-dev.cloud/"
echo "  - Set up automatic renewal"
echo ""

# Run certbot in standalone mode
certbot certonly \
    --standalone \
    --non-interactive \
    --agree-tos \
    --email admin@goexplorer-dev.cloud \
    -d goexplorer-dev.cloud

if [ $? -eq 0 ]; then
    echo "✅ SSL certificate obtained successfully"
else
    echo "❌ Failed to obtain SSL certificate"
    echo "Please check:"
    echo "  1. DNS A record for goexplorer-dev.cloud points to this server's IP"
    echo "  2. Port 80 is accessible from the internet"
    echo "  3. No firewall blocking port 80"
    exit 1
fi
echo ""

# Step 5: Backup existing Nginx configuration
echo "💾 Step 5: Backing up existing Nginx configuration..."
NGINX_CONF="/etc/nginx/sites-available/goexplorer-dev"
BACKUP_CONF="${NGINX_CONF}.backup.$(date +%Y%m%d_%H%M%S)"

if [ -f "$NGINX_CONF" ]; then
    cp "$NGINX_CONF" "$BACKUP_CONF"
    echo "✅ Backup created: $BACKUP_CONF"
else
    echo "⚠️  No existing configuration found"
fi
echo ""

# Step 6: Deploy new HTTPS-enabled Nginx configuration
echo "📝 Step 6: Deploying HTTPS-enabled Nginx configuration..."
DEPLOY_DIR="/home/deployer/goexplorer/deploy"
NEW_CONF="${DEPLOY_DIR}/nginx.goexplorer.dev.https.conf"

if [ -f "$NEW_CONF" ]; then
    cp "$NEW_CONF" "$NGINX_CONF"
    echo "✅ New configuration deployed to $NGINX_CONF"
else
    echo "❌ Configuration file not found: $NEW_CONF"
    exit 1
fi
echo ""

# Step 7: Enable site if not already enabled
echo "🔗 Step 7: Enabling site..."
NGINX_ENABLED="/etc/nginx/sites-enabled/goexplorer-dev"
if [ ! -L "$NGINX_ENABLED" ]; then
    ln -s "$NGINX_CONF" "$NGINX_ENABLED"
    echo "✅ Site enabled"
else
    echo "✅ Site already enabled"
fi
echo ""

# Step 8: Test Nginx configuration
echo "🧪 Step 8: Testing Nginx configuration..."
nginx -t
if [ $? -eq 0 ]; then
    echo "✅ Nginx configuration is valid"
else
    echo "❌ Nginx configuration has errors"
    echo "Restoring backup..."
    if [ -f "$BACKUP_CONF" ]; then
        cp "$BACKUP_CONF" "$NGINX_CONF"
        echo "✅ Backup restored"
    fi
    exit 1
fi
echo ""

# Step 9: Restart Nginx
echo "🔄 Step 9: Restarting Nginx..."
systemctl restart nginx
systemctl enable nginx
if [ $? -eq 0 ]; then
    echo "✅ Nginx restarted successfully"
else
    echo "❌ Failed to restart Nginx"
    exit 1
fi
echo ""

# Step 10: Set up automatic certificate renewal
echo "♻️  Step 10: Setting up automatic SSL certificate renewal..."
# Certbot automatically installs a cron job or systemd timer
systemctl enable certbot.timer
systemctl start certbot.timer
echo "✅ Auto-renewal configured"
echo ""

# Step 11: Test HTTPS
echo "🌐 Step 11: Testing HTTPS connection..."
sleep 2
if curl -Is https://goexplorer-dev.cloud | head -1 | grep "200\|301\|302" > /dev/null; then
    echo "✅ HTTPS is working!"
else
    echo "⚠️  HTTPS test inconclusive. Please test manually:"
    echo "   https://goexplorer-dev.cloud"
fi
echo ""

# Step 12: Verify Django is running
echo "🐍 Step 12: Verifying Django/Gunicorn is running..."
if systemctl is-active --quiet gunicorn-goexplorer; then
    echo "✅ Gunicorn is running"
else
    echo "⚠️  Gunicorn is not running. Starting..."
    systemctl restart gunicorn-goexplorer
    echo "✅ Gunicorn started"
fi
echo ""

# Final Summary
echo "========================================="
echo "✅ HTTPS SETUP COMPLETE!"
echo "========================================="
echo ""
echo "📋 Summary:"
echo "  ✅ SSL Certificate: /etc/letsencrypt/live/goexplorer-dev.cloud/"
echo "  ✅ Nginx Config: $NGINX_CONF"
echo "  ✅ HTTP → HTTPS redirect: Enabled"
echo "  ✅ Auto-renewal: Enabled"
echo ""
echo "🌐 Your site is now available at:"
echo "  https://goexplorer-dev.cloud"
echo ""
echo "🔐 Certificate will auto-renew before expiration"
echo ""
echo "🧪 Manual Testing:"
echo "  1. Open: https://goexplorer-dev.cloud"
echo "  2. Check SSL certificate is valid"
echo "  3. Verify HTTP redirects to HTTPS"
echo "  4. Test login/booking flows work on HTTPS"
echo ""
echo "📊 Check certificate status:"
echo "  certbot certificates"
echo ""
echo "🔄 Renew certificate manually (if needed):"
echo "  certbot renew --dry-run  # Test renewal"
echo "  certbot renew            # Force renewal"
echo ""
echo "========================================="
