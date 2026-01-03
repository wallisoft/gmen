"""
Change tracker - Simplified to work with MenuModel
"""


class ChangeTracker:
    """Tracks changes (mostly handled by MenuModel now)"""
    
    def __init__(self, menu_model):
        self.model = menu_model
    
    def mark_item_modified(self, item_id: str, field: str, value=None) -> None:
        """Track item modification - passes to model"""
        print(f"📝 ChangeTracker: {item_id}.{field} = {value}")
        
        if field == 'deleted' and value is True:
            self.model.delete_item(item_id)
        elif field and value is not None:
            self.model.update_item(item_id, **{field: value})
    
    def add_new_item(self, temp_id: str, data: dict) -> None:
        """Add new item - handled by model directly"""
        print(f"📝 ChangeTracker.add_new_item({temp_id}, ...) - Model handles this")
    
    def mark_item_deleted(self, item_id: str) -> None:
        """Mark item for deletion"""
        self.model.delete_item(item_id)
    
    def update_window_state(self, item_id: str, window_state: dict) -> None:
        """Track window state changes"""
        self.model.update_item(item_id, window_state=window_state)
    
    def mark_menu_modified(self, name: str = None, is_default: bool = None) -> None:
        """Track menu metadata changes"""
        if name is not None:
            self.model.name = name
            self.model.name_modified = True
            self.model.is_modified = True
        print(f"📝 Menu modified: name={name}, default={is_default}")
    
    def has_changes(self) -> bool:
        """Check if any changes pending"""
        return self.model.has_changes()
    
    def clear(self) -> None:
        """Clear all tracked changes - reload from DB to truly clear"""
        print("🧹 ChangeTracker.clear() - Model keeps changes until saved")
    
    def get_change_summary(self) -> dict:
        """Get summary of changes"""
        changes = self.model.get_items_for_save()
        return {
            'modified': len(changes['modified']),
            'new': len(changes['new']),
            'deleted': len(changes['deleted']),
            'menu_modified': changes['menu_modified'],
            'total': len(changes['new']) + len(changes['modified']) + len(changes['deleted'])
        }
