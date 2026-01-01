#!/usr/bin/env python3
"""
GMen Editor - Main entry point
"""

import sys
from pathlib import Path

# Add our modules to path
sys.path.insert(0, str(Path(__file__).parent))

from storage.database import Database
from utils.config import ConfigManager
from ui.editor.main_window import EditorMainWindow


def main():
    print("🎯 GMen Editor - Modular Architecture")
    print("📁 Database: ~/.config/gmen/gmen.db")
    
    # Initialize
    config_dir = Path.home() / ".config" / "gmen"
    db = Database(config_dir)
    config = ConfigManager(config_dir)
    
    # Create and run editor
    editor = EditorMainWindow(db, config)
    editor.run()


if __name__ == "__main__":
    main()
