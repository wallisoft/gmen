# GMen v3.5 - Database-First System Tray Launcher with Scripting

GMen is a powerful system tray application launcher that stores everything in SQLite and now supports Lua scripting!

## New Features in v3.5

### 1. Thread-Safe Database
- Fixed "SQLite objects created in a thread" error
- Each thread gets its own database connection
- Thread-safe window manager

### 2. Lua Scripting Support
- Integrated LuaPure interpreter (pure Python, no dependencies)
- Full GMen Lua API:
  - `gmen.launch(command)` - Launch applications
  - `gmen.notify(message)` - Show notifications
  - `gmen.sleep(seconds)` - Pause execution
  - `gmen.set_window(pid, x, y, width, height)` - Position windows
  - `gmen.run_script(name)` - Chain scripts together

### 3. Script Editor
- Multi-language support (Lua, Python, Shell)
- Syntax highlighting
- Code editor with line numbers
- API reference browser
- Example scripts

### 4. Enhanced Editor UI
- Command vs Script selection
- Script browser in menu editor
- Edit scripts directly from menu editor

## Installation

```bash
# Clone or copy all files
chmod +x gmen.py gmen_editor.py gmen_script_editor.py

# First run will create database in ~/.config/gmen/gmen.db
python3 gmen.pymarkdown

# 🎯 GMen - Windows 11 Style Menu for Linux

A minimal, elegant Windows 11 style start menu for Linux with a powerful visual editor.

![GMen Screenshot](https://via.placeholder.com/800x500.png?text=GMen+Windows+11+Style+Menu+for+Linux)

## ✨ Features

- **Windows 11 Style Menu**: Clean, modern interface inspired by Windows 11
- **Visual Editor**: Intuitive drag-and-drop menu configuration
- **Hierarchical Menus**: Nested submenus with proper indentation
- **Icon Browser**: Built-in icon selector with search functionality
- **Window State Management**: Remember window positions and sizes
- **Live Preview**: Test menus instantly
- **Multiple Configs**: Save and load different menu configurations
- **System Tray Integration**: Runs as a lightweight system tray app

## 🏗️ Architecture

- **Core Menu System**: `gmen.py` - Main application with system tray integration
- **Visual Editor**: `gmen-editor.py` - Full-featured GTK3 editor for menu configuration
- **Configuration**: JSON-based with hierarchical structure support
- **Dependencies**: Python 3 + GTK3 + AppIndicator3

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/wallisoft/gmen.git
cd gmen

# Install dependencies (Ubuntu/Debian)
sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-appindicator3-0.1

# Run the editor
./gmen-editor

# Run the menu
./gmen

Using the Editor

    Launch ./gmen-editor

    Add items with ⊕ Add (same level) or 📁 Sub-Menu (indented)

    Configure properties: Title, Command, Icon

    Use ↑/↓ to rearrange items

    Save as named configuration or set as default

    Test with ▶️ Test button

Using the Menu

    Look for the GMen icon in your system tray

    Click to open the Windows 11 style menu

    Right-click for options

    Menu automatically reloads when configuration changes

📁 Project Structure
text

gmen/
├── gmen.py              # Main menu application
├── gmen-editor.py       # Visual configuration editor
├── README.md            # This file
├── LICENSE              # MIT License
├── .gitignore           # Git ignore file
└── config/             # Configuration examples (optional)

🛠️ Development
Code Architecture

    Flat List Hierarchy: Items displayed with indentation for clear parent-child relationships

    Event-Driven UI: GTK3 signals for responsive editing

    JSON Serialization: Human-readable configuration format

    Modular Design: Separated UI, logic, and data layers

Key Design Decisions

    Flat Navigation: All items shown in single scrollable list with indentation

    Context-Aware Editing: Add/Remove behavior depends on selection context

    Live Updates: Changes reflect immediately in both editor and menu

    Error Resilience: Fallbacks for missing icons/configs

    User Experience: Arrow key navigation, focus management, unsaved changes protection

🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

    Fork the repository

    Create a feature branch (git checkout -b feature/amazing-feature)

    Commit your changes (git commit -m 'Add amazing feature')

    Push to the branch (git push origin feature/amazing-feature)

    Open a Pull Request

📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
👥 Credits
Lead Developer & Architect

    DeepSeek AI - Full implementation, code architecture, and development

        Email: assistant@deepseek.com

        GitHub: deepseek-ai

Project Architect & Vision

    Steve Walli - Project concept, UI/UX design, and requirements

        GitHub: wallisoft

        Role: Non-programming architect and visionary

Special Thanks

    GTK3 and Python communities for excellent libraries

    Linux desktop environment developers

    Open source contributors everywhere

🌟 Why GMen?

GMen bridges the gap between Windows usability and Linux flexibility. It provides:

    Familiarity: Windows users feel at home on Linux

    Customization: Fully configurable to match your workflow

    Performance: Lightweight Python/GTK implementation

    Integration: Works with any Linux desktop environment

    Open Source: Free to use, modify, and distribute

📞 Support

    Issues: GitHub Issues

    Discussions: GitHub Discussions

🎯 Roadmap

    Plugin system for custom menu items

    Theme support (light/dark mode)

    Keyboard shortcuts in menu

    Export/import configurations

    Internationalization (i18n)

    Advanced search in menu

    Mobile/tablet optimized version

Made with ❤️ for the Linux community
