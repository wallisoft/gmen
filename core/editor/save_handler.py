"""
Handles saving changes to database - FIXED VERSION
"""

class SaveHandler:
    """Manages saving editor changes to database - FIXED for temp parent IDs"""
    
    def __init__(self, db):
        self.db = db
    
    def save_all(self, menu_id, change_tracker):
        """Save all tracked changes to database - FIXED VERSION"""
        try:
            with self.db.transaction():
                # 1. Save menu metadata
                if change_tracker.menu_modified:
                    self._save_menu_metadata(menu_id, change_tracker)
                
                # 2. First pass: Save all new items and build temp→real ID map
                temp_to_real_map = {}
                saved_new_items = []
                
                # We need to save parents before children
                # Sort new items by depth (0 = top level, 1 = children, 2 = grandchildren, etc.)
                new_items_by_depth = {}
                for new_item in change_tracker.new_items:
                    depth = new_item['data'].get('depth', 0)
                    if depth not in new_items_by_depth:
                        new_items_by_depth[depth] = []
                    new_items_by_depth[depth].append(new_item)
                
                # Process from shallowest to deepest
                for depth in sorted(new_items_by_depth.keys()):
                    for new_item in new_items_by_depth[depth]:
                        real_id = self._save_new_item(menu_id, new_item, temp_to_real_map)
                        temp_id = new_item['temp_id']
                        temp_to_real_map[temp_id] = real_id
                        saved_new_items.append(new_item)
                
                # 3. Save modified items (update any temp parent references)
                for item_id, changes in change_tracker.modified_items.items():
                    # Fix temp parent IDs in modifications
                    if 'parent_id' in changes and changes['parent_id'] is not None:
                        parent_id = changes['parent_id']
                        if parent_id < 0:  # It's a temp ID
                            if parent_id in temp_to_real_map:
                                changes['parent_id'] = temp_to_real_map[parent_id]
                            else:
                                print(f"⚠️ Modified item {item_id} references unknown temp parent {parent_id}")
                                changes['parent_id'] = None
                    
                    self._save_item_changes(item_id, changes)
                
                # 4. Delete items
                for item_id in change_tracker.deleted_items:
                    self._delete_item(item_id)
                
                # 5. Save window states
                for item_id, window_state in change_tracker.window_state_changes.items():
                    self._save_window_state(item_id, window_state)
            
            return True, "Saved successfully"
            
        except Exception as e:
            return False, f"Save failed: {e}"
    
    def _save_menu_metadata(self, menu_id, change_tracker):
        """Save menu name and default status"""
        if change_tracker.new_menu_name or change_tracker.new_default_status is not None:
            updates = []
            params = []
            
            if change_tracker.new_menu_name:
                updates.append("name = ?")
                params.append(change_tracker.new_menu_name)
            
            if change_tracker.new_default_status is not None:
                updates.append("is_default = ?")
                params.append(change_tracker.new_default_status)
            
            params.append(menu_id)
            query = f"UPDATE menus SET {', '.join(updates)} WHERE id = ?"
            self.db.execute(query, tuple(params))
            
            if change_tracker.new_default_status:
                self.db.execute(
                    "UPDATE menus SET is_default = 0 WHERE id != ?",
                    (menu_id,)
                )
    
    def _save_item_changes(self, item_id, changes):
        """Save changes to an existing item"""
        if not changes:
            return
        
        updates = []
        params = []
        
        for field, value in changes.items():
            updates.append(f"{field} = ?")
            params.append(value)
        
        params.append(item_id)
        query = f"UPDATE menu_items SET {', '.join(updates)} WHERE id = ?"
        self.db.execute(query, tuple(params))
    
    def _save_new_item(self, menu_id, new_item, temp_to_real_map=None):
        """Save a new item and return its real ID - FIXED for temp parent IDs"""
        data = new_item['data']
        
        # Handle temp parent IDs
        parent_id = data.get('parent_id')
        if parent_id is not None and parent_id < 0 and temp_to_real_map:
            # It's a temp ID, try to map it
            if parent_id in temp_to_real_map:
                parent_id = temp_to_real_map[parent_id]
            else:
                print(f"⚠️ New item has temp parent ID {parent_id} not in map")
                print(f"   Temp→Real map: {temp_to_real_map}")
                # If we're at depth > 0 but parent not found, something's wrong
                if data.get('depth', 0) > 0:
                    print(f"   ⚠️ Item at depth {data.get('depth')} will be orphaned!")
                parent_id = None
        
        self.db.execute("""
            INSERT INTO menu_items 
            (menu_id, title, command, icon, depth, parent_id, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            menu_id,
            data.get('title', 'New Item'),
            data.get('command', ''),
            data.get('icon', ''),
            data.get('depth', 0),
            parent_id,  # Use resolved parent_id
            data.get('sort_order', 0)
        ))
        
        result = self.db.fetch_one("SELECT last_insert_rowid() AS id")
        real_id = result['id']
        
        new_item['real_id'] = real_id
        return real_id
    
    def _delete_item(self, item_id):
        """Delete an item and its window states"""
        self.db.execute("DELETE FROM menu_items WHERE id = ?", (item_id,))
        self.db.execute("DELETE FROM window_states WHERE menu_item_id = ?", (item_id,))
    
    def _save_window_state(self, item_id, window_state):
        """Save window state for an item"""
        if not window_state.get('enabled', False):
            self.db.execute(
                "DELETE FROM window_states WHERE menu_item_id = ?",
                (item_id,)
            )
            return
        
        # Get app name from command
        command = window_state.get('command', '')
        app_name = "unknown"
        if command and command.strip():
            app_name = command.split()[0].lower()
        
        self.db.execute("""
            INSERT OR REPLACE INTO window_states 
            (menu_item_id, app_name, x, y, width, height, monitor, remember, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1)
        """, (
            item_id,
            app_name,
            window_state.get('x', 100),
            window_state.get('y', 100),
            window_state.get('width', 800),
            window_state.get('height', 600),
            window_state.get('monitor', 0)
        ))
