#!/bin/bash
set -e

# -----------------------------
# CONFIG (change only if needed)
# -----------------------------
APP_DIR="/home/deployer/Go_explorer_clear"
VENV_DIR="$APP_DIR/venv"
PROJECT_WSGI="goexplorer.wsgi:application"
GUNICORN_SERVICE="/etc/systemd/system/gunicorn.service"
PYTHON_BIN="/usr/bin/python3"

echo "🚀 Starting GoExplorer deployment (safe & repeatable)..."

# -----------------------------
# 1. Go to app directory
# -----------------------------
cd "$APP_DIR"

# -----------------------------
# 2. Create virtualenv if missing
# -----------------------------
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "🐍 Creating virtual environment..."
    $PYTHON_BIN -m venv venv
fi

echo "✅ Virtualenv ready"

# -----------------------------
# 3. Activate venv & install deps
# -----------------------------
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

# -----------------------------
# 4. Django prep
# -----------------------------
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# -----------------------------
# 5. Create / Fix Gunicorn systemd service
# -----------------------------
if [ ! -f "$GUNICORN_SERVICE" ]; then
    echo "⚙️ Creating gunicorn systemd service..."
    sudo tee "$GUNICORN_SERVICE" > /dev/null <<EOF
[Unit]
Description=Gunicorn daemon for GoExplorer
After=network.target

[Service]
User=deployer
Group=www-data
WorkingDirectory=$APP_DIR
ExecStart=$VENV_DIR/bin/gunicorn \
          --workers 3 \
          --threads 2 \
          --timeout 120 \
          --bind 127.0.0.1:8000 \
          $PROJECT_WSGI

Restart=always

[Install]
WantedBy=multi-user.target
EOF
else
    echo "ℹ️ Gunicorn service already exists"
fi

# -----------------------------
# 6. Reload & restart services
# -----------------------------
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl restart gunicorn
sudo systemctl reload nginx || true

# -----------------------------
# 7. Final status
# -----------------------------
echo "✅ Deployment complete"
sudo systemctl status gunicorn --no-pager

