"""
Tracks all modifications for batch save
"""

class ChangeTracker:
    """Tracks changes to menu items for batch saving"""
    
    def __init__(self):
        # Item modifications: {item_id: {field: new_value}}
        self.modified_items = {}
        
        # New items: list of dicts with temp_id, data
        self.new_items = []
        
        # Deleted items: set of item_ids
        self.deleted_items = set()
        
        # Window state changes: {item_id: window_state_dict}
        self.window_state_changes = {}
        
        # Menu metadata changes
        self.menu_modified = False
        self.new_menu_name = None
        self.new_default_status = None
    
    def mark_item_modified(self, item_id, field=None, value=None):
        """Mark an item as modified"""
        if item_id not in self.modified_items:
            self.modified_items[item_id] = {}
        
        if field and value is not None:
            self.modified_items[item_id][field] = value
    
    def add_new_item(self, temp_id, data):
        """Track a new item"""
        self.new_items.append({
            'temp_id': temp_id,
            'data': data,
            'real_id': None  # Will be filled when saved
        })
    
    def mark_item_deleted(self, item_id):
        """Mark an item for deletion"""
        self.deleted_items.add(item_id)
    
    def update_window_state(self, item_id, window_state):
        """Update window state for an item"""
        self.window_state_changes[item_id] = window_state
    
    def mark_menu_modified(self, name=None, is_default=None):
        """Mark menu metadata as modified"""
        self.menu_modified = True
        if name:
            self.new_menu_name = name
        if is_default is not None:
            self.new_default_status = is_default
    
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
    
    def get_change_summary(self):
        """Get summary of changes"""
        return {
            'modified': len(self.modified_items),
            'new': len(self.new_items),
            'deleted': len(self.deleted_items),
            'window_states': len(self.window_state_changes),
            'menu_modified': self.menu_modified
        }
