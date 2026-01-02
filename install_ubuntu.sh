#!/bin/bash
# GMen v4 Ubuntu Installer with Network Clipboard Sync

set -e

echo "🎯 GMen v4 Ubuntu Installer with Network Features"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    echo -e "${RED}Error: Do not run this script as root${NC}"
    echo "Run as regular user, sudo will be used when needed"
    exit 1
fi

# Check Ubuntu version
if ! command -v lsb_release &> /dev/null; then
    echo -e "${RED}Error: lsb_release not found. Are you on Ubuntu?${NC}"
    exit 1
fi

UBUNTU_VERSION=$(lsb_release -rs)
echo -e "${GREEN}Ubuntu $UBUNTU_VERSION detected${NC}"

# Create directories
echo -e "\n📁 Creating directories..."
mkdir -p ~/.config/gmen
mkdir -p ~/.local/share/gmen

# Install system dependencies
echo -e "\n📦 Installing system dependencies..."
sudo apt update
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-3.0 \
    gir1.2-appindicator3-0.1 \
    xdotool \
    wmctrl \
    git \
    sqlite3

# Install Python dependencies
echo -e "\n🐍 Installing Python dependencies..."
pip3 install --user \
    pyperclip \
    requests

# Clone or update GMen
echo -e "\n📥 Setting up GMen..."
if [ -d "gmen" ]; then
    echo "GMen directory exists, updating..."
    cd gmen
    git pull
else
    git clone https://github.com/steve/gmen.git
    cd gmen
fi

# Make scripts executable
echo -e "\n⚙️  Setting up permissions..."
chmod +x gmen.py
chmod +x gmen_editor.py
chmod +x gmen_script_editor.py

# Initialize database
echo -e "\n🗄️  Initializing database..."
python3 -c "
from storage.database import Database
from pathlib import Path
import sys
db = Database(Path.home() / '.config' / 'gmen')
print('Database initialized successfully')
"

# Create desktop entry
echo -e "\n🖥️  Creating desktop entry..."
cat > ~/.local/share/applications/gmen.desktop << DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=GMen
Comment=Database-First System Tray Launcher with Network Sync
Exec=$(which python3) $(pwd)/gmen.py
Icon=view-grid-symbolic
Terminal=false
Categories=Utility;
StartupNotify=false
X-GNOME-Autostart-enabled=true
DESKTOP

# Create autostart entry
echo -e "\n🔄 Setting up autostart..."
mkdir -p ~/.config/autostart
cp ~/.local/share/applications/gmen.desktop ~/.config/autostart/

# Create uninstall script
echo -e "\n🗑️  Creating uninstall script..."
cat > uninstall_gmen.sh << 'UNINSTALL'
#!/bin/bash
echo "Removing GMen..."
rm -rf ~/.config/gmen
rm -rf ~/.local/share/gmen
rm -f ~/.local/share/applications/gmen.desktop
rm -f ~/.config/autostart/gmen.desktop
echo "GMen removed. Source directory at $(pwd) remains."
UNINSTALL
chmod +x uninstall_gmen.sh

# Create launcher script
echo -e "\n🚀 Creating launcher script..."
cat > launch_gmen.sh << 'LAUNCHER'
#!/bin/bash
cd "$(dirname "$0")"
python3 gmen.py "\$@"
LAUNCHER
chmod +x launch_gmen.sh

echo -e "\n${GREEN}✅ Installation complete!${NC}"
echo -e "\n${YELLOW}📋 Quick start:${NC}"
echo "1. Start GMen:      ./launch_gmen.sh"
echo "2. With network:    ./launch_gmen.sh --remote"
echo "3. Edit menus:      ./gmen_editor.py"
echo "4. Auto-starts on login"
echo ""
echo -e "${YELLOW}🌐 Network Clipboard Sync:${NC}"
echo "- Run GMen with --remote flag on multiple machines"
echo "- Go to Configure GMen → Network"
echo "- Enable 'Sync Clipboard' and select devices"
echo "- Copy text on one machine, paste on another!"
echo ""
echo -e "${YELLOW}⚠️  Troubleshooting:${NC}"
echo "- If clipboard sync fails: pip3 install --user pyperclip"
echo "- If network not working: check firewall (port 8721)"
echo "- For Wayland issues: use X11 session for full features"
echo ""
echo -e "📚 Documentation: See README.md for detailed usage"
