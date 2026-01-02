"""
Change tracking for editor
"""


class ChangeTracker:
    """Tracks changes made in editor for saving"""
    
    def __init__(self):
        # Item modifications: {item_id: {field: new_value}}
        self.modified_items = {}
        
        # New items: dict {temp_id: data}
        self.new_items = {}
        
        # Deleted items: set of item_ids
        self.deleted_items = set()
        
        # Window state changes: {item_id: window_state_dict}
        self.window_state_changes = {}
        
        # Menu metadata changes
        self.menu_modified = False
        self.new_menu_name = None
        self.new_default_status = None
        
        # Temp to real ID mapping
        self.temp_to_real_id_map = {}
    
    def mark_item_modified(self, item_id, field, value=None):
        """Track modification to an item property"""
        # Check if this is a temp ID that's been mapped
        real_id = self.temp_to_real_id_map.get(item_id, item_id)
        
        if real_id not in self.modified_items:
            self.modified_items[real_id] = {}
        
        if field and value is not None:
            self.modified_items[real_id][field] = value
            print(f"📝 ChangeTracker: Marked item {real_id} ({field}='{value}')")
    
    def add_new_item(self, temp_id, data):
        """Track a new item"""
        self.new_items[temp_id] = data
        print(f"📝 ChangeTracker: Added temp item {temp_id}: {data}")
    
    def mark_item_deleted(self, item_id):
        """Mark an item for deletion"""
        self.deleted_items.add(item_id)
        print(f"📝 ChangeTracker: Marked item {item_id} for deletion")
    
    def update_window_state(self, item_id, window_state):
        """Track window state changes"""
        self.window_state_changes[item_id] = window_state
        print(f"📝 ChangeTracker: Updated window state for item {item_id}")
    
    def mark_menu_modified(self, name=None, is_default=None):
        """Track menu metadata changes"""
        self.menu_modified = True
        if name is not None:
            self.new_menu_name = name
        if is_default is not None:
            self.new_default_status = is_default
        print(f"📝 ChangeTracker: Menu modified (name={name}, default={is_default})")
    
    def update_temp_id_mapping(self, temp_id, real_id):
        """Update mapping when temp item gets real database ID"""
        print(f"🔄 ChangeTracker: Mapping temp {temp_id} → real {real_id}")
        print(f"   Modified items before: {self.modified_items}")
        
        self.temp_to_real_id_map[temp_id] = real_id
        
        # Transfer any changes from temp_id to real_id
        if temp_id in self.modified_items:
            print(f"   Transferring changes from temp {temp_id} to real {real_id}")
            if real_id not in self.modified_items:
                self.modified_items[real_id] = {}
            self.modified_items[real_id].update(self.modified_items[temp_id])
            del self.modified_items[temp_id]
        
        print(f"   Modified items after: {self.modified_items}")
        print(f"   Temp→Real map: {self.temp_to_real_id_map}")
    
    def has_changes(self):
        """Check if any changes pending"""
        return (self.modified_items or self.new_items or 
                self.deleted_items or self.window_state_changes or
                self.menu_modified)
    
    def clear(self):
        """Clear all tracked changes"""
        self.modified_items.clear()
        self.new_items.clear()
        self.deleted_items.clear()
        self.window_state_changes.clear()
        self.menu_modified = False
        self.new_menu_name = None
        self.new_default_status = None
        self.temp_to_real_id_map.clear()
        print("🧹 ChangeTracker: Cleared all changes")
    
    def get_change_summary(self):
        """Get summary of changes"""
        return {
            'modified': len(self.modified_items),
            'new': len(self.new_items),
            'deleted': len(self.deleted_items),
            'window_states': len(self.window_state_changes),
            'menu_modified': self.menu_modified
        }
