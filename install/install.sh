#!/bin/bash
# GMen Installer for Linux
# Copyright (c) 2024 Steve Wallis (wallisoft@gmail.com)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[*]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

# Check if running as root
check_root() {
    if [ "$EUID" -eq 0 ]; then 
        print_warning "Installing as root. User configs will be installed to /etc/skel"
        AS_ROOT=1
    else
        AS_ROOT=0
    fi
}

# Check and install dependencies
check_dependencies() {
    print_status "Checking dependencies..."
    
    local missing_packages=()
    
    # Check for system packages
    if ! command -v python3 &> /dev/null; then
        missing_packages+=("python3")
    fi
    
    # Check for X11 window management tools
    if ! command -v wmctrl &> /dev/null; then
        print_warning "wmctrl not found (needed for window positioning)"
        missing_packages+=("wmctrl")
    fi
    
    if ! command -v xdotool &> /dev/null; then
        print_warning "xdotool not found (helpful for window positioning)"
        missing_packages+=("xdotool")
    fi
    
    # Check for GTK dependencies
    if ! python3 -c "import gi; gi.require_version('Gtk', '3.0')" &> /dev/null; then
        print_warning "Python GTK3 bindings not found"
        if [ -f /etc/debian_version ]; then
            missing_packages+=("python3-gi" "python3-gi-cairo" "gir1.2-gtk-3.0")
        elif [ -f /etc/fedora-release ]; then
            missing_packages+=("python3-gobject" "gtk3")
        elif [ -f /etc/arch-release ]; then
            missing_packages+=("python-gobject" "gtk3")
        fi
    fi
    
    # Check for AppIndicator
    if ! python3 -c "import gi; gi.require_version('AppIndicator3', '0.1')" &> /dev/null; then
        print_warning "AppIndicator3 not found"
        if [ -f /etc/debian_version ]; then
            missing_packages+=("gir1.2-appindicator3-0.1")
        elif [ -f /etc/fedora-release ]; then
            missing_packages+=("libappindicator-gtk3")
        elif [ -f /etc/arch-release ]; then
            missing_packages+=("libappindicator-gtk3")
        fi
    fi
    
    # Install missing packages if any
    if [ ${#missing_packages[@]} -ne 0 ]; then
        print_warning "Missing system packages: ${missing_packages[*]}"
        
        # Detect package manager
        if command -v apt-get &> /dev/null; then
            print_status "Detected Debian/Ubuntu based system"
            echo -n "Install missing packages automatically? [Y/n]: "
            read -r response
            if [[ ! "$response" =~ ^([nN][oO]?)?$ ]]; then
                sudo apt-get update
                sudo apt-get install -y "${missing_packages[@]}"
                print_status "System packages installed successfully"
            else
                print_error "Please install dependencies manually and run again"
                exit 1
            fi
        elif command -v dnf &> /dev/null; then
            print_status "Detected Fedora/RHEL based system"
            echo -n "Install missing packages automatically? [Y/n]: "
            read -r response
            if [[ ! "$response" =~ ^([nN][oO]?)?$ ]]; then
                sudo dnf install -y "${missing_packages[@]}"
                print_status "System packages installed successfully"
            else
                print_error "Please install dependencies manually and run again"
                exit 1
            fi
        elif command -v pacman &> /dev/null; then
            print_status "Detected Arch based system"
            echo -n "Install missing packages automatically? [Y/n]: "
            read -r response
            if [[ ! "$response" =~ ^([nN][oO]?)?$ ]]; then
                sudo pacman -S --noconfirm "${missing_packages[@]}"
                print_status "System packages installed successfully"
            else
                print_error "Please install dependencies manually and run again"
                exit 1
            fi
        else
            print_error "Unsupported package manager. Please install manually:"
            printf '  %s\n' "${missing_packages[@]}"
            exit 1
        fi
    fi
}

# Verify source files exist
verify_source_files() {
    print_status "Verifying source files..."
    
    local required_files=(
        "src/gmen"
        "src/gmen-editor"
    )
    
    local optional_files=(
        "src/window_manager.py"
        "src/database.py"
    )
    
    local missing_files=()
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -ne 0 ]; then
        print_error "Missing required files:"
        printf '  %s\n' "${missing_files[@]}"
        exit 1
    fi
    
    # Check optional files
    for file in "${optional_files[@]}"; do
        if [ ! -f "$file" ]; then
            print_warning "Optional file not found: $file"
            print_warning "Window positioning features may be limited"
        fi
    done
    
    print_status "Source files verified"
}

# Install GMen files for local user
install_local() {
    local INSTALL_PREFIX="$HOME/.local"
    local BIN_DIR="$INSTALL_PREFIX/bin"
    local SHARE_DIR="$INSTALL_PREFIX/share/gmen"
    local CONFIG_DIR="$HOME/.config/gmen"
    
    print_status "Installing GMen to $INSTALL_PREFIX (local user)..."
    
    # Create directories
    mkdir -p "$BIN_DIR"
    mkdir -p "$SHARE_DIR"
    mkdir -p "$CONFIG_DIR"
    
    # Install executables
    print_status "Installing executables..."
    cp -f src/gmen src/gmen-editor "$BIN_DIR/"
    chmod +x "$BIN_DIR"/gmen "$BIN_DIR"/gmen-editor
    
    # Install Python modules if they exist
    print_status "Installing Python modules..."
    if [ -f "src/window_manager.py" ]; then
        cp -f src/window_manager.py "$BIN_DIR/"
    fi
    
    if [ -f "src/database.py" ]; then
        cp -f src/database.py "$BIN_DIR/"
    fi
    
    # Install default configs from configs/ directory if it exists
    if [ -d "configs" ]; then
        print_status "Installing default configurations..."
        cp -rf configs/* "$SHARE_DIR/" 2>/dev/null || true
    else
        print_warning "No configs/ directory found. Creating basic defaults..."
        create_basic_configs "$SHARE_DIR"
    fi
    
    # Create sample config if none exists
    if [ ! -f "$CONFIG_DIR/current.json" ] && [ -f "$SHARE_DIR/Windows11.json" ]; then
        print_status "Creating initial user configuration..."
        cp "$SHARE_DIR/Windows11.json" "$CONFIG_DIR/current.json"
    fi
    
    # Create autostart entry
    print_status "Setting up autostart..."
    mkdir -p "$HOME/.config/autostart"
    cat > "$HOME/.config/autostart/gmen.desktop" << EOF
[Desktop Entry]
Type=Application
Name=GMen Start Menu
Comment=Windows 11 style start menu for Linux
Exec=$BIN_DIR/gmen
Icon=application-x-executable
Categories=Utility;
StartupNotify=false
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
    
    print_status "Local installation complete!"
    print_info "Executables: $BIN_DIR/"
    print_info "Configurations: $CONFIG_DIR/"
    print_info "Shared data: $SHARE_DIR/"
}

# Create basic configs if configs/ directory doesn't exist
create_basic_configs() {
    local SHARE_DIR="$1"
    
    mkdir -p "$SHARE_DIR"
    
    # Create minimal Windows11.json
    cat > "$SHARE_DIR/Windows11.json" << 'EOF'
{
  "theme": "windows11",
  "show_recent": false,
  "windows11_items": [
    {
      "title": "Terminal",
      "command": "gnome-terminal",
      "icon": "utilities-terminal",
      "window_state": {
        "enabled": true,
        "x": 100,
        "y": 100,
        "width": 800,
        "height": 600,
        "monitor": null
      }
    },
    {
      "title": "Edit Menu",
      "command": "gmen-editor",
      "icon": "accessories-text-editor"
    }
  ],
  "quick_launch": [],
  "categories": {},
  "power": []
}
EOF
    
    print_status "Basic configuration created in $SHARE_DIR"
}

# Install GMen files system-wide
install_system() {
    local INSTALL_PREFIX="/usr/local"
    local BIN_DIR="$INSTALL_PREFIX/bin"
    local SHARE_DIR="$INSTALL_PREFIX/share/gmen"
    local CONFIG_SKEL="/etc/skel/.config/gmen"
    
    print_status "Installing GMen system-wide to $INSTALL_PREFIX..."
    
    # Create directories
    sudo mkdir -p "$BIN_DIR"
    sudo mkdir -p "$SHARE_DIR"
    sudo mkdir -p "$CONFIG_SKEL"
    
    # Install executables
    print_status "Installing executables..."
    sudo cp -f src/gmen src/gmen-editor "$BIN_DIR/"
    sudo chmod +x "$BIN_DIR"/gmen "$BIN_DIR"/gmen-editor
    
    # Install Python modules if they exist
    print_status "Installing Python modules..."
    if [ -f "src/window_manager.py" ]; then
        sudo cp -f src/window_manager.py "$BIN_DIR/"
    fi
    
    if [ -f "src/database.py" ]; then
        sudo cp -f src/database.py "$BIN_DIR/"
    fi
    
    # Install default configs from configs/ directory
    if [ -d "configs" ]; then
        print_status "Installing default configurations..."
        sudo cp -rf configs/* "$SHARE_DIR/" 2>/dev/null || true
    else
        print_warning "No configs/ directory found. Creating basic defaults..."
        create_basic_configs_system "$SHARE_DIR"
    fi
    
    # Create sample config in /etc/skel for new users
    if [ -f "$SHARE_DIR/Windows11.json" ]; then
        print_status "Creating user template configuration..."
        sudo cp "$SHARE_DIR/Windows11.json" "$CONFIG_SKEL/current.json"
    fi
    
    # Create system autostart for new users
    print_status "Setting up autostart for new users..."
    sudo mkdir -p /etc/skel/.config/autostart
    sudo cat > /etc/skel/.config/autostart/gmen.desktop << EOF
[Desktop Entry]
Type=Application
Name=GMen Start Menu
Comment=Windows 11 style start menu for Linux
Exec=gmen
Icon=application-x-executable
Categories=Utility;
StartupNotify=false
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
    
    print_status "System-wide installation complete!"
    print_info "Installed to: $INSTALL_PREFIX"
    print_info "New users will get GMen automatically"
}

# System version of create_basic_configs
create_basic_configs_system() {
    local SHARE_DIR="$1"
    
    sudo mkdir -p "$SHARE_DIR"
    
    sudo tee "$SHARE_DIR/Windows11.json" > /dev/null << 'EOF'
{
  "theme": "windows11",
  "show_recent": false,
  "windows11_items": [
    {
      "title": "Terminal",
      "command": "gnome-terminal",
      "icon": "utilities-terminal",
      "window_state": {
        "enabled": true,
        "x": 100,
        "y": 100,
        "width": 800,
        "height": 600,
        "monitor": null
      }
    },
    {
      "title": "Edit Menu",
      "command": "gmen-editor",
      "icon": "accessories-text-editor"
    }
  ],
  "quick_launch": [],
  "categories": {},
  "power": []
}
EOF
    
    print_status "Basic system configuration created"
}

# Setup environment
setup_environment() {
    local BIN_DIR="$HOME/.local/bin"
    
    # Add ~/.local/bin to PATH if not already
    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        print_status "Adding $BIN_DIR to PATH..."
        
        # Detect shell
        local shell_rc
        if [ -n "$ZSH_VERSION" ]; then
            shell_rc="$HOME/.zshrc"
        elif [ -n "$BASH_VERSION" ]; then
            shell_rc="$HOME/.bashrc"
        else
            shell_rc="$HOME/.profile"
        fi
        
        # Check if already added
        if ! grep -q "$BIN_DIR" "$shell_rc" 2>/dev/null; then
            {
                echo ""
                echo "# Added by GMen installer"
                echo 'export PATH="$HOME/.local/bin:$PATH"'
            } >> "$shell_rc"
            
            print_warning "Added $BIN_DIR to PATH in $shell_rc"
            print_warning "Run 'source $shell_rc' or restart your terminal"
        fi
    fi
    
    # Test if commands are available
    if command -v gmen &> /dev/null; then
        print_status "GMen command is available in PATH"
    else
        print_warning "GMen command not in PATH. You can run it from: $BIN_DIR/gmen"
    fi
}

# Post-install steps
post_install() {
    print_status "Installation complete!"
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║             GMen Installation Complete                 ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    if [ "$AS_ROOT" -eq 0 ]; then
        echo -e "${BLUE}QUICK START:${NC}"
        echo "1. Start GMen now:      gmen"
        echo "2. Edit menu:           gmen-editor"
        echo "3. Look for the GMen icon in your system tray!"
        echo ""
        echo -e "${YELLOW}FEATURES:${NC}"
        echo "• Windows 11 style menu"
        echo "• Window position memory (if window_manager.py installed)"
        echo "• SQLite database backend (if database.py installed)"
        echo "• Fully customizable"
        echo ""
        echo -e "${BLUE}AUTOSTART:${NC}"
        echo "GMen will auto-start on next login."
        echo "To run now: gmen &"
        echo ""
        
        # Show where everything is
        echo -e "${BLUE}INSTALLED TO:${NC}"
        echo "Executables:    $HOME/.local/bin/"
        echo "Config:         $HOME/.config/gmen/"
        echo "Shared data:    $HOME/.local/share/gmen/"
        echo ""
        
        # Ask to start now
        echo -n "Start GMen now? [Y/n]: "
        read -r response
        if [[ ! "$response" =~ ^([nN][oO]?)?$ ]]; then
            print_status "Starting GMen..."
            if command -v gmen &> /dev/null; then
                gmen &
            else
                "$HOME/.local/bin/gmen" &
            fi
            sleep 3
            print_status "GMen should now appear in your system tray!"
            print_status "Right-click the icon to access the menu."
        fi
    else
        echo -e "${BLUE}SYSTEM INSTALLATION COMPLETE${NC}"
        echo ""
        echo "Users can now run:"
        echo "  gmen           # Start the menu"
        echo "  gmen-editor    # Edit configuration"
        echo ""
        echo "New users will have:"
        echo "• GMen in autostart"
        echo "• Default configuration"
        echo ""
        echo "Existing users: Run 'gmen-editor' to set up."
    fi
    
    echo ""
    echo -e "${GREEN}Thank you for installing GMen!${NC}"
}

# Create project structure
create_project_structure() {
    print_status "Creating project structure..."
    
    # Create directories
    mkdir -p src
    mkdir -p configs
    mkdir -p docs
    
    print_status "Project structure created"
}

# Main installation
main() {
    clear
    echo -e "${GREEN}"
    cat << "EOF"
     ╔══════════════════════════════════════════╗
     ║            GMen Installer                ║
     ║  Windows 11 Menu + Window Positioning    ║
     ║               for Linux                  ║
     ╚══════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    echo ""
    
    # Check if we're in the right directory
    if [ ! -d "src" ]; then
        print_warning "Not in project root. Creating project structure..."
        create_project_structure
    fi
    
    verify_source_files
    check_root
    check_dependencies
    
    # Choose installation type
    if [ "$AS_ROOT" -eq 1 ]; then
        print_status "Performing SYSTEM-WIDE installation"
        install_system
    else
        print_status "Performing LOCAL USER installation"
        install_local
        setup_environment
    fi
    
    post_install
}

# Handle command line arguments
case "${1:-}" in
    "--help"|"-h")
        echo "GMen Installer"
        echo "Usage: $0 [OPTION]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help"
        echo "  --local        Install for current user only"
        echo "  --system       Install system-wide (requires sudo)"
        echo "  --check        Check dependencies only"
        echo ""
        exit 0
        ;;
    "--local")
        AS_ROOT=0
        verify_source_files
        check_dependencies
        install_local
        setup_environment
        post_install
        ;;
    "--system")
        AS_ROOT=1
        verify_source_files
        check_dependencies
        install_system
        post_install
        ;;
    "--check")
        check_dependencies
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
