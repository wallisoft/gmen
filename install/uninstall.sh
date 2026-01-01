#!/bin/bash
# GMen Uninstaller

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}GMen Uninstaller${NC}"
echo ""

# Check what's installed
INSTALLED=0

if [ -f "$HOME/.local/bin/gmen" ]; then
    INSTALLED=1
    PREFIX="$HOME/.local"
elif [ -f "/usr/local/bin/gmen" ]; then
    INSTALLED=2
    PREFIX="/usr/local"
fi

if [ $INSTALLED -eq 0 ]; then
    echo "GMen not found in standard locations."
    exit 0
fi

echo "Found GMen installed in: $PREFIX"
echo ""
echo "This will remove:"
echo "  • $PREFIX/bin/gmen"
echo "  • $PREFIX/bin/gmen-editor"
echo "  • $PREFIX/share/gmen/"
echo "  • ~/.config/gmen/"
echo "  • ~/.config/autostart/gmen.desktop"
echo ""
echo -n "Continue uninstall? [y/N]: "
read -r response

if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "Removing GMen..."
    
    # Remove binaries
    rm -f "$PREFIX/bin/gmen" "$PREFIX/bin/gmen-editor"
    
    # Remove share files
    rm -rf "$PREFIX/share/gmen"
    
    # Remove user configs
    rm -rf "$HOME/.config/gmen"
    rm -f "$HOME/.config/autostart/gmen.desktop"
    
    echo "GMen has been removed."
    echo "Note: Configuration backups in ~/.config/startmenu/ were kept."
else
    echo "Uninstall cancelled."
fi
