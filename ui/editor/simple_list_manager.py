"""
Simple List Manager - Minimal version with tree operations
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import uuid


class SimpleListManager:
    def __init__(self, db, menu_id):
        self.db = db
        self.menu_id = menu_id
        self.items = []  # Format: {id, db_id, title, depth, parent_db_id, instances[]}
        self.selected_id = None
        
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        
        self._load()
    
    def _load(self):
        """Load menu items with instances"""
        self.items = []
        db_items = self.db.get_menu_items(self.menu_id, active_only=True)
        
        for db_item in db_items:
            item = {
                'id': str(db_item['id']),  # Use DB ID as temp ID
                'db_id': db_item['id'],
                'title': db_item['title'],
                'depth': db_item['depth'],
                'parent_db_id': db_item['parent_id'],
                'instances': []
            }
            
            # Load instances
            instances = self.db.get_item_instances(db_item['id'])
            for inst in instances:
                instance_data = {
                    'id': str(inst['id']),
                    'db_id': inst['id'],
                    'command': inst.get('command', ''),
                    'icon': inst.get('icon', ''),
                    'workspace_id': inst.get('workspace_id'),
                    'enable_positioning': inst.get('enable_positioning', True),
                    'window_state': {
                        'x': inst.get('x'),
                        'y': inst.get('y'),
                        'width': inst.get('width'),
                        'height': inst.get('height'),
                        'display': inst.get('display', 0),
                        'state': inst.get('state', 'normal')
                    } if any([inst.get('x'), inst.get('y'), inst.get('width'), inst.get('height')]) else None
                }
                item['instances'].append(instance_data)
            
            # Ensure at least one instance
            if not item['instances']:
                item['instances'].append(self._create_default_instance())
            
            self.items.append(item)
        
        self._refresh_listbox()
    
    def _create_default_instance(self):
        """Create a default instance"""
        return {
            'id': f"inst_{uuid.uuid4().hex[:8]}",
            'db_id': None,
            'command': '',
            'icon': '',
            'workspace_id': None,
            'enable_positioning': True,
            'window_state': None
        }
    
    # === TREE OPERATIONS (KEEP THESE - THEY WORK) ===
    
    def add_item(self, title="New Item"):
        """Add new item with default instance"""
        new_id = str(uuid.uuid4())[:8]
        new_item = {
            'id': new_id,
            'db_id': None,
            'title': title,
            'depth': 0,
            'parent_db_id': None,
            'instances': [self._create_default_instance()]
        }
        
        self.items.append(new_item)
        self.selected_id = new_id
        self._refresh_listbox()
        return new_item
    
    def delete_item(self):
        """Delete selected item and its children"""
        if not self.selected_id:
            return False
        
        # Find the item
        for i, item in enumerate(self.items):
            if item['id'] == self.selected_id:
                # Remove item and all its children
                depth = item['depth']
                to_remove = [i]
                
                # Find children (items with greater depth until depth returns)
                for j in range(i + 1, len(self.items)):
                    if self.items[j]['depth'] > depth:
                        to_remove.append(j)
                    else:
                        break
                
                # Remove in reverse order
                for idx in sorted(to_remove, reverse=True):
                    self.items.pop(idx)
                
                self.selected_id = None
                self._refresh_listbox()
                return True
        
        return False
    
    def move_up(self):
        """Move selected item up"""
        if not self.selected_id:
            return
        
        for i, item in enumerate(self.items):
            if item['id'] == self.selected_id and i > 0:
                # Can't move above parent if we're a child
                if item['depth'] > self.items[i-1]['depth']:
                    return
                
                self.items[i], self.items[i-1] = self.items[i-1], self.items[i]
                self._refresh_listbox()
                return
    
    def move_down(self):
        """Move selected item down"""
        if not self.selected_id:
            return
        
        for i, item in enumerate(self.items):
            if item['id'] == self.selected_id and i < len(self.items) - 1:
                # Can't move below parent's sibling
                if item['depth'] > self.items[i+1]['depth']:
                    return
                
                self.items[i], self.items[i+1] = self.items[i+1], self.items[i]
                self._refresh_listbox()
                return
    
    def indent(self):
        """Increase depth (make child of previous item)"""
        if not self.selected_id:
            return
        
        for i, item in enumerate(self.items):
            if item['id'] == self.selected_id and i > 0:
                # Can indent if previous item is at same or higher level
                if item['depth'] <= self.items[i-1]['depth']:
                    item['depth'] = self.items[i-1]['depth'] + 1
                    item['parent_db_id'] = self.items[i-1].get('db_id')
                    self._refresh_listbox()
                return
    
    def outdent(self):
        """Decrease depth (make sibling of parent)"""
        if not self.selected_id:
            return
        
        for i, item in enumerate(self.items):
            if item['id'] == self.selected_id and item['depth'] > 0:
                item['depth'] = max(item['depth'] - 1, 0)
                # Find new parent
                for j in range(i-1, -1, -1):
                    if self.items[j]['depth'] == item['depth']:
                        item['parent_db_id'] = self.items[j].get('db_id')
                        break
                    elif self.items[j]['depth'] < item['depth']:
                        item['parent_db_id'] = None
                        break
                self._refresh_listbox()
                return
    
    # === INSTANCE MANAGEMENT ===
    
    def update_instance(self, item_id, instance_idx, **kwargs):
        """Update specific instance properties"""
        for item in self.items:
            if item['id'] == item_id and 0 <= instance_idx < len(item['instances']):
                instance = item['instances'][instance_idx]
                
                # Update properties
                for key, value in kwargs.items():
                    if key == 'window_state':
                        if value is None:
                            instance['window_state'] = None
                        else:
                            if instance['window_state'] is None:
                                instance['window_state'] = {}
                            instance['window_state'].update(value)
                    else:
                        instance[key] = value
                
                self._refresh_listbox()
                return True
        return False
    
    def add_instance(self, item_id):
        """Add new instance to item"""
        for item in self.items:
            if item['id'] == item_id:
                new_instance = self._create_default_instance()
                item['instances'].append(new_instance)
                self._refresh_listbox()
                return len(item['instances']) - 1
        return -1
    
    def remove_instance(self, item_id, instance_idx):
        """Remove instance from item (if not the last one)"""
        for item in self.items:
            if item['id'] == item_id and len(item['instances']) > 1:
                if 0 <= instance_idx < len(item['instances']):
                    item['instances'].pop(instance_idx)
                    self._refresh_listbox()
                    return True
        return False
    
    # === UTILITIES ===
    
    def get_selected_item(self):
        """Get currently selected item"""
        if not self.selected_id:
            return None
        for item in self.items:
            if item['id'] == self.selected_id:
                return item
        return None

    def _refresh_listbox(self):
        """Refresh the listbox display - NO AUTO-SELECTION"""
        # Store if we had a selection
        had_selection = self.selected_id is not None

        # Clear current rows
        for row in self.listbox.get_children():
            self.listbox.remove(row)

        # Add rows for each item
        for i, item in enumerate(self.items):
            row = Gtk.ListBoxRow()

            content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

            # Indentation
            indent_label = Gtk.Label(label="  " * item['depth'])
            content.pack_start(indent_label, False, False, 0)

            # Title with instance count
            title_text = item['title']
            if len(item['instances']) > 1:
                title_text += f" ({len(item['instances'])})"

            title_label = Gtk.Label(label=title_text)
            title_label.set_xalign(0)
            content.pack_start(title_label, True, True, 0)

            row.add(content)
            row.item_id = item['id']
            row.item_index = i

            # ONLY highlight if this is the selected item AND we want to keep selection
            if had_selection and item['id'] == self.selected_id:
                row.set_state_flags(Gtk.StateFlags.SELECTED, False)

            self.listbox.add(row)

        self.listbox.show_all()

    def clear_selection(self):
        """Clear all selection states"""
        self.selected_id = None
        self.listbox.unselect_all()
        self._refresh_listbox()

    def set_selected_by_id(self, item_id):
        """Set selection by item ID"""
        self.selected_id = item_id
        self._refresh_listbox()
        
    def save(self):
        """Save to database"""
        # TODO: Implement save (keep existing logic)
        print(f"💾 Would save {len(self.items)} items")
        return True
