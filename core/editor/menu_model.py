"""
Clean in-memory menu model - Single source of truth
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import uuid


@dataclass
class MenuItem:
    """In-memory menu item representation"""
    id: str  # UUID for in-memory, maps to DB ID on save
    title: str
    command: str = ""
    icon: str = ""
    depth: int = 0
    parent_id: Optional[str] = None
    sort_order: int = 0
    children: List['MenuItem'] = field(default_factory=list)
    
    # Window state (for GMen main app)
    window_state: Optional[Dict] = None
    
    # DB mapping and change tracking
    db_id: Optional[int] = None
    is_new: bool = False
    is_modified: bool = False
    is_deleted: bool = False
    
    def is_script(self) -> bool:
        """Check if this item executes a script"""
        return self.command.startswith('@') if self.command else False
    
    def get_script_name(self) -> Optional[str]:
        """Get script name if command is @script"""
        if self.is_script():
            return self.command[1:]  # Remove @
        return None


class MenuModel:
    """Complete in-memory menu with hierarchy"""
    
    def __init__(self, menu_id: int, name: str):
        self.id = menu_id
        self.name = name
        self.items: Dict[str, MenuItem] = {}  # id -> MenuItem
        self.root_items: List[MenuItem] = []  # Items with no parent
        
        # Change tracking
        self.is_modified = False
        self.name_modified = False
    
    def load_from_db(self, db) -> None:
        """Load entire menu structure from database including window states"""
        self.items.clear()
        self.root_items.clear()
        
        # Load all items for this menu
        rows = db.fetch_all("""
            SELECT id, title, command, icon, depth, parent_id, sort_order
            FROM menu_items 
            WHERE menu_id = ?
            ORDER BY sort_order
        """, (self.id,))
        
        # Create all items
        for row in rows:
            item = MenuItem(
                id=str(row['id']),  # Use DB ID as string ID
                title=row['title'],
                command=row['command'] or '',
                icon=row['icon'] or '',
                depth=row['depth'],
                parent_id=str(row['parent_id']) if row['parent_id'] else None,
                sort_order=row['sort_order'],
                db_id=row['id']
            )
            self.items[item.id] = item
        
        # Load window states
        window_states = db.fetch_all("""
            SELECT item_id, x, y, width, height, state, display
            FROM window_states 
            WHERE item_id IN (SELECT id FROM menu_items WHERE menu_id = ?)
        """, (self.id,))
        
        for ws in window_states:
            item_id = str(ws['item_id'])
            if item_id in self.items:
                self.items[item_id].window_state = {
                    'x': ws['x'],
                    'y': ws['y'],
                    'width': ws['width'],
                    'height': ws['height'],
                    'state': ws['state'],
                    'display': ws['display']
                }
        
        # Build parent-child relationships
        for item in self.items.values():
            if item.parent_id and item.parent_id in self.items:
                parent = self.items[item.parent_id]
                parent.children.append(item)
                # Keep children sorted
                parent.children.sort(key=lambda x: x.sort_order)
            elif item.parent_id is None:
                self.root_items.append(item)
        
        # Sort root items
        self.root_items.sort(key=lambda x: x.sort_order)
        
        self.is_modified = False
        print(f"📦 MenuModel loaded {len(self.items)} items with window states")
    
    def add_item(self, title: str, parent_id: Optional[str] = None) -> MenuItem:
        """Add new item to model (returns immediately)"""
        new_id = f"temp_{uuid.uuid4().hex[:8]}"
        
        # Calculate depth
        depth = 0
        if parent_id and parent_id in self.items:
            parent = self.items[parent_id]
            depth = parent.depth + 1
        
        # Calculate sort order (append to end)
        siblings = self._get_siblings(parent_id)
        sort_order = len(siblings)
        
        # Create item
        item = MenuItem(
            id=new_id,
            title=title,
            depth=depth,
            parent_id=parent_id,
            sort_order=sort_order,
            is_new=True
        )
        
        # Add to model
        self.items[new_id] = item
        
        # Update parent
        if parent_id and parent_id in self.items:
            parent = self.items[parent_id]
            parent.children.append(item)
            parent.children.sort(key=lambda x: x.sort_order)
        else:
            self.root_items.append(item)
            self.root_items.sort(key=lambda x: x.sort_order)
        
        self.is_modified = True
        print(f"➕ Added item {new_id} (parent: {parent_id})")
        return item
    
    def update_item(self, item_id: str, **kwargs) -> bool:
        """Update item properties (returns immediately)"""
        if item_id not in self.items:
            return False
        
        item = self.items[item_id]
        changed = False
        
        for key, value in kwargs.items():
            if hasattr(item, key):
                old_value = getattr(item, key)
                if old_value != value:
                    setattr(item, key, value)
                    item.is_modified = True
                    changed = True
                    print(f"✏️ Updated {item_id}.{key}: {old_value} → {value}")
        
        if changed:
            self.is_modified = True
        
        return changed
    
    def delete_item(self, item_id: str) -> bool:
        """Mark item for deletion (soft delete in model)"""
        if item_id not in self.items:
            return False
        
        item = self.items[item_id]
        item.is_deleted = True
        self.is_modified = True
        
        # Remove from parent's children list
        if item.parent_id and item.parent_id in self.items:
            parent = self.items[item.parent_id]
            parent.children = [c for c in parent.children if c.id != item_id]
        elif item.parent_id is None:
            self.root_items = [i for i in self.root_items if i.id != item_id]
        
        print(f"🗑️ Marked {item_id} for deletion")
        return True
    
    def move_item(self, item_id: str, direction: str) -> bool:
        """Move item up or down within its siblings"""
        if item_id not in self.items:
            return False
        
        item = self.items[item_id]
        siblings = self._get_siblings(item.parent_id)
        
        # Find current position
        current_idx = next((i for i, sib in enumerate(siblings) if sib.id == item_id), -1)
        if current_idx == -1:
            return False
        
        # Determine new position
        if direction == 'up' and current_idx > 0:
            new_idx = current_idx - 1
        elif direction == 'down' and current_idx < len(siblings) - 1:
            new_idx = current_idx + 1
        else:
            return False
        
        # Swap positions
        siblings[current_idx], siblings[new_idx] = siblings[new_idx], siblings[current_idx]
        
        # Update sort orders
        for i, sibling in enumerate(siblings):
            if sibling.sort_order != i:
                sibling.sort_order = i
                sibling.is_modified = True
        
        self.is_modified = True
        print(f"↕️ Moved {item_id} {direction}")
        return True
    
    def get_item(self, item_id: str) -> Optional[MenuItem]:
        """Get item by ID"""
        return self.items.get(item_id)
    
    def get_all_items(self) -> List[MenuItem]:
        """Get all items in depth-first order (for tree display)"""
        result = []
        
        def add_items(items: List[MenuItem]):
            for item in items:
                if not item.is_deleted:
                    result.append(item)
                    add_items(item.children)
        
        add_items(self.root_items)
        return result
    
    def get_items_for_save(self) -> Dict:
        """Get all changes for saving to database"""
        return {
            'new': [item for item in self.items.values() if item.is_new and not item.is_deleted],
            'modified': [item for item in self.items.values() if item.is_modified and not item.is_deleted and not item.is_new],
            'deleted': [item for item in self.items.values() if item.is_deleted and item.db_id],
            'menu_modified': self.is_modified,
            'name_modified': self.name_modified
        }
    
    def has_changes(self) -> bool:
        """Check if model has any pending changes"""
        if not self.is_modified:
            return False
        
        for item in self.items.values():
            if item.is_new or item.is_modified or item.is_deleted:
                return True
        
        return False
    
    def _get_siblings(self, parent_id: Optional[str] = None) -> List[MenuItem]:
        """Get all items at same level"""
        if parent_id and parent_id in self.items:
            return self.items[parent_id].children
        return self.root_items
    
    def print_debug(self) -> None:
        """Print debug information"""
        print(f"\n=== MenuModel Debug ===")
        print(f"Menu: {self.name} (ID: {self.id})")
        print(f"Total items: {len(self.items)}")
        print(f"Root items: {len(self.root_items)}")
        print(f"Has changes: {self.has_changes()}")
        
        changes = self.get_items_for_save()
        print(f"Changes: {len(changes['new'])} new, {len(changes['modified'])} modified, {len(changes['deleted'])} deleted")
        
        if self.items:
            print("\nItems (depth-first):")
            def print_item(item: MenuItem, indent: int = 0):
                prefix = "  " * indent
                status = []
                if item.is_new: status.append("NEW")
                if item.is_modified: status.append("MOD")
                if item.is_deleted: status.append("DEL")
                status_str = f" [{', '.join(status)}]" if status else ""
                
                item_type = "folder" if not item.command else ("script" if item.is_script() else "command")
                win_state = ""
                if item.window_state:
                    win_state = f" win:{item.window_state.get('x', 0)},{item.window_state.get('y', 0)}"
                print(f"{prefix}- {item.title} ({item_type}, id:{item.id[:8]}, db:{item.db_id}){status_str}{win_state}")
                
                for child in sorted(item.children, key=lambda x: x.sort_order):
                    print_item(child, indent + 1)
            
            for item in sorted(self.root_items, key=lambda x: x.sort_order):
                print_item(item)
