"""
Save handler for MenuModel
"""

import json
from typing import Tuple, Dict, List, Optional


class SaveHandler:
    """Handles saving MenuModel to database including window states"""
    
    def __init__(self, db):
        self.db = db
    
    def save_model(self, menu_model) -> Tuple[bool, str]:
        """Save entire model to database including window states"""
        if not menu_model.has_changes():
            return True, "No changes to save"
        
        print(f"💾 Saving menu '{menu_model.name}' (ID: {menu_model.id})...")
        
        try:
            with self.db.transaction():
                changes = menu_model.get_items_for_save()
                
                # Update menu name if changed
                if changes['name_modified']:
                    self.db.execute(
                        "UPDATE menus SET name = ? WHERE id = ?",
                        (menu_model.name, menu_model.id)
                    )
                    print(f"✏️ Updated menu name to '{menu_model.name}'")
                
                # Track ID mapping for new items
                temp_to_real = {}
                
                # 1. Process deletions first
                for item in changes['deleted']:
                    self._delete_item(item.db_id)
                
                # 2. Process new items (need to handle parent references)
                # Sort by depth so parents are created before children
                new_items_by_depth = {}
                for item in changes['new']:
                    if item.depth not in new_items_by_depth:
                        new_items_by_depth[item.depth] = []
                    new_items_by_depth[item.depth].append(item)
                
                for depth in sorted(new_items_by_depth.keys()):
                    for item in new_items_by_depth[depth]:
                        real_id = self._save_new_item(menu_model.id, item, temp_to_real)
                        temp_to_real[item.id] = real_id
                        item.db_id = real_id
                        item.is_new = False
                        
                        # Save window state if exists
                        if item.window_state:
                            self._save_window_state(real_id, item.window_state)
                
                # 3. Process modified items
                for item in changes['modified']:
                    self._save_existing_item(item, temp_to_real)
                    
                    # Save window state if exists
                    if item.window_state:
                        self._save_window_state(item.db_id, item.window_state)
                
                # 4. Update parent references for items with temp parents
                for item in menu_model.items.values():
                    if not item.is_deleted and item.db_id and item.parent_id:
                        if item.parent_id.startswith('temp_'):
                            real_parent_id = temp_to_real.get(item.parent_id)
                            if real_parent_id:
                                self.db.execute(
                                    "UPDATE menu_items SET parent_id = ? WHERE id = ?",
                                    (real_parent_id, item.db_id)
                                )
                
                # Clear modification flags
                menu_model.is_modified = False
                menu_model.name_modified = False
                for item in menu_model.items.values():
                    item.is_modified = False
                    item.is_deleted = False
            
            total = len(changes['new']) + len(changes['modified']) + len(changes['deleted'])
            print(f"✅ Saved {total} changes successfully")
            return True, f"Saved {total} changes"
            
        except Exception as e:
            print(f"❌ Save failed: {e}")
            import traceback
            traceback.print_exc()
            return False, str(e)
    
    def _save_new_item(self, menu_id: int, item, temp_to_real: Dict) -> int:
        """Save new item and return its real DB ID"""
        parent_db_id = None
        if item.parent_id:
            # Check if parent is new (temp) or existing
            if item.parent_id.startswith('temp_'):
                parent_db_id = temp_to_real.get(item.parent_id)
            else:
                parent_db_id = int(item.parent_id) if item.parent_id.isdigit() else None
        
        self.db.execute("""
            INSERT INTO menu_items 
            (menu_id, title, command, icon, depth, parent_id, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            menu_id,
            item.title,
            item.command,
            item.icon or None,
            item.depth,
            parent_db_id,
            item.sort_order
        ))
        
        result = self.db.fetch_one("SELECT last_insert_rowid() AS id")
        real_id = result['id']
        
        print(f"➕ Saved new item: {item.title} → DB ID {real_id}")
        return real_id
    
    def _save_existing_item(self, item, temp_to_real: Dict) -> None:
        """Update existing item"""
        parent_db_id = None
        if item.parent_id:
            if item.parent_id.startswith('temp_'):
                parent_db_id = temp_to_real.get(item.parent_id)
            else:
                parent_db_id = int(item.parent_id) if item.parent_id.isdigit() else None
        
        self.db.execute("""
            UPDATE menu_items 
            SET title = ?, command = ?, icon = ?, 
                depth = ?, parent_id = ?, sort_order = ?
            WHERE id = ?
        """, (
            item.title,
            item.command,
            item.icon or None,
            item.depth,
            parent_db_id,
            item.sort_order,
            item.db_id
        ))
        
        print(f"✏️ Updated item: {item.title} (DB ID: {item.db_id})")
    
    def _delete_item(self, db_id: int) -> None:
        """Delete item from database including window states"""
        # Delete window states first (foreign key)
        self.db.execute("DELETE FROM window_states WHERE item_id = ?", (db_id,))
        # Delete item
        self.db.execute("DELETE FROM menu_items WHERE id = ?", (db_id,))
        print(f"🗑️ Deleted item DB ID: {db_id}")
    
    def _save_window_state(self, item_id: int, window_state: Dict) -> None:
        """Save window state for item"""
        # Delete existing window state
        self.db.execute("DELETE FROM window_states WHERE item_id = ?", (item_id,))
        
        # Insert new window state
        self.db.execute("""
            INSERT INTO window_states 
            (item_id, x, y, width, height, state, display)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            item_id,
            window_state.get('x'),
            window_state.get('y'),
            window_state.get('width'),
            window_state.get('height'),
            window_state.get('state'),
            window_state.get('display', 0)
        ))
        print(f"💾 Saved window state for item {item_id}")
    
    def export_menu(self, menu_id: int, export_path: str) -> bool:
        """Export menu to JSON file (stub implementation)"""
        print(f"📤 Exporting menu {menu_id} to {export_path}")
        # TODO: Implement JSON export
        return True
    
    def import_menu(self, import_path: str) -> Optional[int]:
        """Import menu from JSON file (stub implementation)"""
        print(f"📥 Importing menu from {import_path}")
        # TODO: Implement JSON import
        return None
