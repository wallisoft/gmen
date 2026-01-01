#!/usr/bin/env python3
"""
Migrate from JSON config to SQLite database
Run once to convert existing data
"""

import json
import sys
from pathlib import Path
from database import get_database

def import_json_menu(json_path: Path, menu_name: str = "Imported Menu"):
    """Import menu from JSON file to database"""
    db = get_database()
    
    print(f"📥 Importing from {json_path}")
    
    with open(json_path) as f:
        config = json.load(f)
    
    # Create menu
    db.execute("""
        INSERT OR REPLACE INTO menus (name, is_default) 
        VALUES (?, 1)
    """, (menu_name,))
    
    menu_id = db.fetch_one("SELECT last_insert_rowid() AS id")['id']
    print(f"  Created menu: {menu_name} (ID: {menu_id})")
    
    # Import items recursively
    def import_items(items, parent_id=None, depth=0, sort_base=0):
        for i, item in enumerate(items):
            # Insert menu item
            db.execute("""
                INSERT INTO menu_items 
                (menu_id, title, command, icon, depth, parent_id, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                menu_id,
                item.get('title', 'Untitled'),
                item.get('command', ''),
                item.get('icon', ''),
                depth,
                parent_id,
                sort_base + i
            ))
            
            item_id = db.fetch_one("SELECT last_insert_rowid() AS id")['id']
            
            # Import window state if exists
            window_state = item.get('window_state', {})
            if window_state.get('enabled', False):
                app_name = item.get('command', '').split()[0].lower() if item.get('command') else ''
                if app_name:
                    db.execute("""
                        INSERT OR REPLACE INTO window_states 
                        (menu_item_id, app_name, x, y, width, height, monitor, remember)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        item_id,
                        app_name,
                        window_state.get('x', 100),
                        window_state.get('y', 100),
                        window_state.get('width', 800),
                        window_state.get('height', 600),
                        window_state.get('monitor', 0),
                        window_state.get('remember', True)
                    ))
                    print(f"    • {item.get('title')}: Window state saved")
            
            # Recursively import children
            if 'children' in item and item['children']:
                import_items(item['children'], item_id, depth + 1, 0)
    
    # Start import
    items = config.get('windows11_items', [])
    import_items(items)
    
    item_count = db.fetch_one("SELECT COUNT(*) as count FROM menu_items WHERE menu_id = ?", (menu_id,))['count']
    print(f"✅ Imported {item_count} menu items")
    
    return menu_id

def main():
    """Command-line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate JSON menu to SQLite')
    parser.add_argument('json_file', help='JSON file to import')
    parser.add_argument('--name', default='Imported Menu', help='Menu name')
    parser.add_argument('--backup', action='store_true', help='Create backup before import')
    
    args = parser.parse_args()
    
    json_path = Path(args.json_file)
    if not json_path.exists():
        print(f"❌ File not found: {json_path}")
        sys.exit(1)
    
    # Backup existing database
    if args.backup:
        db = get_database()
        backup_path = db.backup()
        print(f"💾 Backup created: {backup_path}")
    
    # Import
    try:
        menu_id = import_json_menu(json_path, args.name)
        print(f"\n🎉 Migration complete!")
        print(f"   Menu ID: {menu_id}")
        print(f"   Database: ~/.config/gmen/gmen.db")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
