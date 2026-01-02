# GMen v4 - System Tray Launcher with Network Clipboard Sync

🎯 **Database-first menu system with zero-config clipboard sharing across machines**

## ✨ Features

### Core Features
- **Database-first menu management** - All items stored in SQLite
- **Cross-platform** - Linux (X11/Wayland), Windows 11, macOS planned
- **Window management** - Position, tile, and organize windows
- **Lua scripting** - Automate tasks with embedded Lua engine
- **GTK3 tray menu** - Clean, native system integration

### Network Features (NEW!)
- **Zero-config clipboard sync** - Copy on one machine, paste on another
- **Auto-discovery** - Finds other GMen instances on LAN automatically
- **Device selection** - Choose which devices to sync with
- **Lightweight HTTP API** - Simple REST interface for clipboard exchange
- **Works through firewalls** - Auto-configures for local networks

## 🚀 Quick Start

### Installation (Ubuntu/Debian)
```bash
# Run the installer
./install_ubuntu.sh

# Or manually
sudo apt install python3 python3-pip python3-gi gir1.2-gtk-3.0 gir1.2-appindicator3-0.1
pip3 install --user pyperclip requests
python3 gmen.py

Using Network Clipboard Sync

    On Machine A:
    bash

python3 gmen.py --remote

On Machine B (same network):
bash

python3 gmen.py --remote

    In GMen tray menu:

        Click "Configure GMen" → "Network"

        Enable "Sync Clipboard"

        Select devices to sync with

        Copy text on Machine A, paste on Machine B!

🏗️ Architecture
text

GMen Core
├── Database (SQLite) - Menu storage
├── Window Manager - Position/tile windows
├── Script Engine (Lua) - Automation
└── Network Layer
    ├── Discovery (UDP broadcast)
    ├── Clipboard API (HTTP)
    └── Sync Service

📁 Project Structure
text

gmen/
├── gmen.py              # Main launcher
├── gmen_editor.py       # Menu editor GUI
├── gmen_script_editor.py # Lua script editor
├── configs/             # JSON menu configurations
├── core/                # Core logic
│   ├── editor/         # Change tracking
│   ├── menu/           # Menu building
│   └── clipboard_sync.py # NEW: Clipboard sync
├── network/            # NEW: Network modules
│   ├── discovery.py    # LAN auto-discovery
│   └── clipboard_api.py # HTTP API server
├── storage/            # Database layer
├── ui/                 # User interface
└── window_management/  # Window positioning

🔧 Configuration
Menu Editor
bash

python3 gmen_editor.py

    Add/remove menu items

    Set window positions

    Configure scripts

    Import/export JSON configs

Script Editor
bash

python3 gmen_script_editor.py

    Write Lua scripts

    Test automation

    Bind to menu items

🌐 Network Protocol
Discovery

    Port: 8720 (UDP broadcast)

    Frequency: Every 30 seconds

    Message: JSON with device info

Clipboard API

    Port: 8721 (HTTP)

    GET /clipboard - Get current clipboard

    POST /clipboard - Set clipboard

    GET /devices - List discovered devices

Security

    Local network only by default

    Optional HTTPS/TLS planned

    Device filtering by user/hostname

🐛 Troubleshooting
Clipboard Sync Not Working

    Check if pyperclip is installed:
    bash

pip3 install --user pyperclip

Verify network connectivity:
bash

# Check if ports are open
ss -tuln | grep 8721

Check firewall:
bash

sudo ufw allow 8721/tcp
sudo ufw allow 8720/udp

Windows 11 Issues

    Requires Python 3.8+

    Install GTK3 for Windows

    Run as administrator for window management

Wayland Support

    Basic clipboard sync works

    Window management limited

    Use X11 session for full features

📈 Roadmap
v4.1 (Next Release)

    Encrypted clipboard sync

    Internet relay (STUN/TURN)

    File transfer between devices

    Input sharing (mouse/keyboard)

v4.2

    Mobile app companion

    Cloud backup

    Shared workspaces

    Plugin system

🤝 Contributing

    Fork the repository

    Create feature branch

    Commit changes

    Push to branch

    Create Pull Request

📄 License

MIT License - See LICENSE file
🙏 Acknowledgements

    GTK3 for the UI framework

    SQLite for lightweight database

    Lua for embedded scripting

    pyperclip for cross-platform clipboard

Made with ❤️ by the GMen team

💬 Need help? Open an issue on GitHub
🐛 Found a bug? Report it with steps to reproduce
💡 Have an idea? We'd love to hear it!
