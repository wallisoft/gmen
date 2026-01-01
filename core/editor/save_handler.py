"""
Handles saving changes to database
"""

class SaveHandler:
    """Manages saving editor changes to database"""
    
    def __init__(self, db):
        self.db = db
    
    def save_all(self, menu_id, change_tracker):
        """Save all tracked changes to database"""
        try:
            with self.db.transaction():
                # 1. Save menu metadata
                if change_tracker.menu_modified:
                    self._save_menu_metadata(menu_id, change_tracker)
                
                # 2. Save modified items
                for item_id, changes in change_tracker.modified_items.items():
                    self._save_item_changes(item_id, changes)
                
                # 3. Save new items
                for new_item in change_tracker.new_items:
                    real_id = self._save_new_item(menu_id, new_item)
                    new_item['real_id'] = real_id
                
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
            # Build update query dynamically
            updates = []
            params = []
            
            if change_tracker.new_menu_name:
                updates.append("name = ?")
                params.append(change_tracker.new_menu_name)
            
            if change_tracker.new_default_status is not None:
                updates.append("is_default = ?")
                params.append(change_tracker.new_default_status)
            
            # Add menu_id to params
            params.append(menu_id)
            
            query = f"UPDATE menus SET {', '.join(updates)} WHERE id = ?"
            self.db.execute(query, tuple(params))
            
            # If this menu is now default, clear others
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
    
    def _save_new_item(self, menu_id, new_item):
        """Save a new item and return its real ID"""
        data = new_item['data']
        
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
            data.get('parent_id'),
            data.get('sort_order', 0)
        ))
        
        result = self.db.fetch_one("SELECT last_insert_rowid() AS id")
        return result['id']
    
    def _delete_item(self, item_id):
        """Delete an item and its window states"""
        self.db.execute("DELETE FROM menu_items WHERE id = ?", (item_id,))
        self.db.execute("DELETE FROM window_states WHERE menu_item_id = ?", (item_id,))
    
    def _save_window_state(self, item_id, window_state):
        """Save window state for an item"""
        if not window_state.get('enabled', False):
            # Remove window state if disabled
            self.db.execute(
                "DELETE FROM window_states WHERE menu_item_id = ?",
                (item_id,)
            )
            return
        
        # Get app name from command if available
        app_name = "unknown"
        if 'command' in window_state:
            cmd = window_state['command']
            if cmd and cmd.strip():
                app_name = cmd.split()[0].lower()
        
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
