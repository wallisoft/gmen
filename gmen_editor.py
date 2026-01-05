#!/usr/bin/env python3
"""
Three Panel Editor - Left/Middle/Right menus
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage.database import Database
from ui.editor.three_panel_window import ThreePanelWindow


def main():
    print("🚀 Starting Three Panel Editor")
    print("🖱️  Left Click Menu")
    print("🖱️  Middle Click Menu") 
    print("🖱️  Right Click Menu")
    print("⚙️  Configurable for X11 (Ctrl/Alt/Shift+click)")
    
    config_dir = Path.home() / ".config" / "gmen"
    db = Database(config_dir)
    
    try:
        editor = ThreePanelWindow(db)
        editor.run()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        db.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
