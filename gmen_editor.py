#!/usr/bin/env python3
"""
GMen Editor - Clean entry point with in-memory model
"""

import sys
import os
import traceback
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage.database import Database
from core.editor.menu_model import MenuModel
from core.editor.save_handler import SaveHandler
from core.editor.change_tracker import ChangeTracker
from ui.editor.main_window import EditorMainWindow


def get_or_create_menu(db, requested_id=None):
    """
    Get existing menu or create new one if none exists.
    Returns (menu_id, menu_name)
    """
    # Check for menus
    menus = db.fetch_all("SELECT id, name, is_default FROM menus ORDER BY id")
    
    if not menus:
        # No menus exist - create default
        print("📭 Database is empty, creating default menu...")
        db.execute("INSERT INTO menus (name, is_default) VALUES ('Main Menu', 1)")
        result = db.fetch_one("SELECT last_insert_rowid() AS id")
        menu_id = result['id']
        menu_name = "Main Menu"
        print(f"✅ Created default menu: {menu_name} (ID: {menu_id})")
        return menu_id, menu_name
    
    # Menus exist
    if requested_id:
        # Find requested menu
        for menu in menus:
            if menu['id'] == requested_id:
                return menu['id'], menu['name']
        print(f"⚠️ Menu {requested_id} not found, using default")
    
    # Find default menu
    for menu in menus:
        if menu['is_default']:
            return menu['id'], menu['name']
    
    # Use first menu
    return menus[0]['id'], menus[0]['name']


def main():
    """Main entry point"""
    print("🚀 GMen Editor starting...")
    print(f"Python: {sys.version}")
    
    try:
        # Setup database
        config_dir = Path.home() / ".config" / "gmen"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        db = Database(config_dir)
        print(f"📊 Database: {db.db_path}")
        
        # Get menu ID from args if provided
        requested_id = None
        if len(sys.argv) > 1:
            try:
                requested_id = int(sys.argv[1])
            except ValueError:
                print(f"⚠️ Invalid menu ID: {sys.argv[1]}, ignoring")
        
        # Get or create menu
        menu_id, menu_name = get_or_create_menu(db, requested_id)
        print(f"📋 Editing: '{menu_name}' (ID: {menu_id})")
        
        # Create in-memory model
        menu_model = MenuModel(menu_id, menu_name)
        menu_model.load_from_db(db)
        
        # Create handlers
        save_handler = SaveHandler(db)
        change_tracker = ChangeTracker(menu_model)
        
        print(f"✅ Loaded {len(menu_model.items)} items into memory")
        
        # Print debug info
        menu_model.print_debug()
        
        # Create and run editor
        print("🖥️ Launching editor...")
        editor = EditorMainWindow(db, menu_model, save_handler, change_tracker)
        
        # Set current menu in toolbar
        if hasattr(editor.toolbar, 'set_current_menu'):
            editor.toolbar.set_current_menu(menu_id, menu_name)
        else:
            print("⚠️ Toolbar doesn't have set_current_menu method")
        
        print("🎬 Running editor...")
        editor.run()
        
        print("👋 Editor exiting")
        
    except Exception as e:
        print(f"💥 ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
