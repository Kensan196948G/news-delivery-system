#!/bin/bash
# Install News Delivery Scheduler as System Service
# システムサービスとしてスケジューラーをインストール

echo "================================================"
echo "📦 News Delivery Scheduler Service Installation"
echo "================================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root (use sudo)"
    exit 1
fi

# Set variables
SERVICE_NAME="news-delivery-scheduler"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
WORKING_DIR="/mnt/e/news-delivery-system"

echo "🔧 Installing scheduler service..."

# Copy service file
if [ -f "${WORKING_DIR}/system/systemd/${SERVICE_NAME}.service" ]; then
    cp "${WORKING_DIR}/system/systemd/${SERVICE_NAME}.service" "$SERVICE_FILE"
    echo "✅ Service file copied to $SERVICE_FILE"
else
    echo "❌ Service file not found: ${WORKING_DIR}/system/systemd/${SERVICE_NAME}.service"
    exit 1
fi

# Set correct permissions
chmod 644 "$SERVICE_FILE"
echo "✅ Service file permissions set"

# Reload systemd
systemctl daemon-reload
echo "✅ Systemd daemon reloaded"

# Enable service (start on boot)
systemctl enable "$SERVICE_NAME"
echo "✅ Service enabled for automatic startup"

echo ""
echo "================================================"
echo "🎉 Installation completed!"
echo "================================================"
echo ""
echo "📋 Service Management Commands:"
echo "   Start service:    sudo systemctl start $SERVICE_NAME"
echo "   Stop service:     sudo systemctl stop $SERVICE_NAME"
echo "   Restart service:  sudo systemctl restart $SERVICE_NAME"
echo "   Service status:   sudo systemctl status $SERVICE_NAME"
echo "   View logs:        sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "⚠️  Important Notes:"
echo "   - Make sure your .env file is properly configured"
echo "   - Ensure virtual environment is activated and dependencies installed"
echo "   - Check file permissions for the working directory"
echo ""
echo "🚀 To start the service now:"
echo "   sudo systemctl start $SERVICE_NAME"
echo ""
