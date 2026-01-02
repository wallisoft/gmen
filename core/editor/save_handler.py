"""
Save handler for editor changes
"""

import json
import logging

logger = logging.getLogger(__name__)


class SaveHandler:
    """Handles saving tracked changes to database"""
    
    def __init__(self, db):
        self.db = db
    
    def save_all(self, menu_id, change_tracker):
        """Save all tracked changes to database"""
        try:
            print(f"💾 SaveHandler: Starting save for menu {menu_id}")
            print(f"   Change summary: {change_tracker.get_change_summary()}")
            
            with self.db.transaction():
                # 1. Save menu metadata
                if change_tracker.menu_modified:
                    self._save_menu_metadata(menu_id, change_tracker)
                
                # 2. First pass: Save all new items and build temp→real ID map
                temp_to_real_map = {}
                
                # We need to save parents before children
                # Sort new items by depth (0 = top level, 1 = children, 2 = grandchildren, etc.)
                new_items_by_depth = {}
                for temp_id, data in change_tracker.new_items.items():
                    depth = data.get('depth', 0)
                    if depth not in new_items_by_depth:
                        new_items_by_depth[depth] = []
                    new_items_by_depth[depth].append({'temp_id': temp_id, 'data': data})
                
                print(f"💾 SaveHandler: New items by depth: {new_items_by_depth}")
                
                # Process from shallowest to deepest
                for depth in sorted(new_items_by_depth.keys()):
                    print(f"💾 SaveHandler: Processing depth {depth}...")
                    for new_item in new_items_by_depth[depth]:
                        real_id = self._save_new_item(menu_id, new_item, temp_to_real_map)
                        temp_id = new_item['temp_id']
                        temp_to_real_map[temp_id] = real_id
                        
                        # Update change tracker mapping
                        print(f"💾 SaveHandler: Calling update_temp_id_mapping({temp_id}, {real_id})")
                        change_tracker.update_temp_id_mapping(temp_id, real_id)
                
                print(f"💾 SaveHandler: Temp→Real map after new items: {temp_to_real_map}")
                
                # 3. Save modified items (update any temp parent references)
                print(f"💾 SaveHandler: Saving {len(change_tracker.modified_items)} modified items...")
                for item_id, changes in change_tracker.modified_items.items():
                    print(f"💾 SaveHandler: Processing item {item_id} changes: {changes}")
                    
                    # Fix temp parent IDs in modifications
                    if 'parent_id' in changes and changes['parent_id'] is not None:
                        parent_id = changes['parent_id']
                        if parent_id < 0:  # It's a temp ID
                            if parent_id in temp_to_real_map:
                                changes['parent_id'] = temp_to_real_map[parent_id]
                                print(f"💾 SaveHandler: Mapped parent temp {parent_id} → real {changes['parent_id']}")
                            else:
                                print(f"⚠️ Modified item {item_id} references unknown temp parent {parent_id}")
                                changes['parent_id'] = None
                    
                    self._save_item_changes(item_id, changes)
                
                # 4. Process window state changes
                if change_tracker.window_state_changes:
                    print(f"💾 SaveHandler: Saving {len(change_tracker.window_state_changes)} window states...")
                    for item_id, state in change_tracker.window_state_changes.items():
                        self._update_window_state(item_id, state)
                
                # 5. Process deletions
                if change_tracker.deleted_items:
                    print(f"💾 SaveHandler: Deleting {len(change_tracker.deleted_items)} items...")
                    for item_id in change_tracker.deleted_items:
                        self._delete_item(item_id)
            
            print(f"💾 SaveHandler: Save completed successfully for menu {menu_id}")
            return True, "Changes saved"
            
        except Exception as e:
            print(f"❌ SaveHandler: Save failed: {e}")
            import traceback
            traceback.print_exc()
            return False, str(e)
    
    def _save_menu_metadata(self, menu_id, change_tracker):
        """Save menu name and default status"""
        updates = []
        params = []
        
        if change_tracker.new_menu_name is not None:
            updates.append("name = ?")
            params.append(change_tracker.new_menu_name)
        
        if change_tracker.new_default_status is not None:
            # If setting this as default, first clear any existing default
            if change_tracker.new_default_status:
                self.db.execute("UPDATE menus SET is_default = 0 WHERE is_default = 1")
            
            updates.append("is_default = ?")
            params.append(1 if change_tracker.new_default_status else 0)
        
        if updates:
            params.append(menu_id)
            query = f"UPDATE menus SET {', '.join(updates)} WHERE id = ?"
            self.db.execute(query, tuple(params))
            print(f"💾 SaveHandler: Updated menu {menu_id} metadata")
    
    def _save_item_changes(self, item_id, changes):
        """Save modifications to an existing item"""
        if not changes:
            return
        
        updates = []
        params = []
        
        for field, value in changes.items():
            if field == 'window_state':
                # Window state is handled separately
                continue
            elif field == 'icon' and not value:
                # Empty icon should be NULL
                updates.append("icon = NULL")
            else:
                updates.append(f"{field} = ?")
                params.append(value)
        
        if not updates:
            return
        
        params.append(item_id)
        query = f"UPDATE menu_items SET {', '.join(updates)} WHERE id = ?"
        self.db.execute(query, tuple(params))
        print(f"💾 SaveHandler: Updated item {item_id}: {changes}")
    
    def _save_new_item(self, menu_id, new_item, temp_to_real_map=None):
        """Save a new item and return its real ID - FIXED for temp parent IDs"""
        temp_id = new_item['temp_id']
        data = new_item['data']
        
        print(f"💾 SaveHandler: Saving new item temp {temp_id}: {data}")
        
        # Handle temp parent IDs
        parent_id = data.get('parent_id')
        if parent_id is not None and parent_id < 0 and temp_to_real_map:
            # It's a temp ID, try to map it
            if parent_id in temp_to_real_map:
                parent_id = temp_to_real_map[parent_id]
                print(f"💾 SaveHandler: Mapped parent temp {new_item['data'].get('parent_id')} → real {parent_id}")
            else:
                print(f"⚠️ New item temp {temp_id} has temp parent ID {parent_id} not in map")
                print(f"   Temp→Real map: {temp_to_real_map}")
                # If we're at depth > 0 but parent not found, something's wrong
                if data.get('depth', 0) > 0:
                    print(f"   ⚠️ Item at depth {data.get('depth')} will be orphaned!")
                parent_id = None
        
        # Insert the new item
        self.db.execute("""
            INSERT INTO menu_items 
            (menu_id, parent_id, title, command, icon, sort_order, depth)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            menu_id,
            parent_id,
            data.get('title', 'New Item'),
            data.get('command', ''),
            data.get('icon'),
            data.get('sort_order', 1),
            data.get('depth', 0)
        ))
        
        result = self.db.fetch_one("SELECT last_insert_rowid() AS id")
        real_id = result['id']
        
        print(f"💾 SaveHandler: New item temp {temp_id} → real ID {real_id}")
        return real_id
    
    def _update_window_state(self, item_id, window_state):
        """Save window state for an item"""
        # First, delete any existing window state
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
            json.dumps(window_state.get('state', {})),
            window_state.get('display', 0)
        ))
        
        print(f"💾 SaveHandler: Updated window state for item {item_id}")
    
    def _delete_item(self, item_id):
        """Delete an item and its window states"""
        # Delete window states first (foreign key constraint)
        self.db.execute("DELETE FROM window_states WHERE item_id = ?", (item_id,))
        
        # Delete the item
        self.db.execute("DELETE FROM menu_items WHERE id = ?", (item_id,))
        
        print(f"💾 SaveHandler: Deleted item {item_id}")
