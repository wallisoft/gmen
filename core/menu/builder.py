"""
Menu Builder - Creates menu hierarchy from database
"""

from typing import Dict, List, Optional
from pathlib import Path


class MenuItem:
    """Represents a menu item"""
    
    def __init__(self, item_id: int, title: str, command: str = None,
                 script_id: int = None, icon: str = None):
        self.id = item_id
        self.title = title
        self.command = command
        self.script_id = script_id
        self.icon = icon
        self.children: List['MenuItem'] = []
        self.parent: Optional['MenuItem'] = None
        self.window_state: Optional[Dict] = None
        
    def add_child(self, child: 'MenuItem'):
        """Add child item"""
        child.parent = self
        self.children.append(child)
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'command': self.command,
            'script_id': self.script_id,
            'icon': self.icon,
            'children': [child.to_dict() for child in self.children],
            'window_state': self.window_state
        }
    
    def __repr__(self):
        indent = "  " * (self.depth if hasattr(self, 'depth') else 0)
        return f"{indent}MenuItem(id={self.id}, title='{self.title}')"


class MenuBuilder:
    """Builds menu hierarchy from database"""
    
    def __init__(self, database):
        self.db = database
    
    def build_default_menu(self) -> MenuItem:
        """Build the default menu"""
        default_menu = self.db.fetch_one("""
            SELECT id, name FROM menus WHERE is_default = 1 LIMIT 1
        """)
        
        if not default_menu:
            raise ValueError("No default menu found in database")
        
        return self.build_menu(default_menu['id'])
    
    def build_menu(self, menu_id: int) -> MenuItem:
        """Build menu hierarchy for given menu ID"""
        items = self.db.fetch("""
            SELECT mi.id, mi.title, mi.command, mi.icon, mi.depth,
                   mi.parent_id, mi.sort_order, mi.script_id,
                   ws.x, ws.y, ws.width, ws.height, ws.monitor
            FROM menu_items mi
            LEFT JOIN window_states ws ON mi.id = ws.menu_item_id AND ws.is_active = 1
            WHERE mi.menu_id = ?
            ORDER BY mi.depth, mi.sort_order
        """, (menu_id,))
        
        # Create lookup dictionary
        item_map = {}
        root_items = []
        
        # First pass: create all items
        for item_data in items:
            item = MenuItem(
                item_id=item_data['id'],
                title=item_data['title'],
                command=item_data['command'],
                script_id=item_data['script_id'],
                icon=item_data['icon']
            )
            
            # Add depth attribute for debugging
            item.depth = item_data['depth']
            
            # Add window state if available
            if item_data['x'] is not None:
                item.window_state = {
                    'enabled': True,
                    'x': item_data['x'],
                    'y': item_data['y'],
                    'width': item_data['width'],
                    'height': item_data['height'],
                    'monitor': item_data['monitor'] or 0
                }
            
            item_map[item.id] = item
        
        # Second pass: build hierarchy
        for item_data in items:
            item = item_map[item_data['id']]
            parent_id = item_data['parent_id']
            
            if parent_id and parent_id in item_map:
                item_map[parent_id].add_child(item)
            else:
                root_items.append(item)
        
        # Create a virtual root item
        root = MenuItem(item_id=0, title="Root")
        for item in root_items:
            root.add_child(item)
        
        return root
    
    def print_menu(self, item: MenuItem, depth: int = 0):
        """Print menu structure for debugging"""
        indent = "  " * depth
        print(f"{indent}{item.title} (ID: {item.id})")
        for child in item.children:
            self.print_menu(child, depth + 1)
