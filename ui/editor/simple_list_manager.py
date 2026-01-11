"""
Simple List Manager - manages items with instances
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import uuid


class SimpleListManager:
    def __init__(self, db, menu_id):
        self.db = db
        self.menu_id = menu_id
        self.items = []  # Structure:
        # {
        #   'id': 'uuid',           # temporary ID
        #   'db_id': None,          # database ID after save
        #   'title': 'Item Title',
        #   'depth': 0,
        #   'parent_db_id': None,
        #   'instances': [          # List of instances
        #     {
        #       'id': 'inst_uuid',  # temporary instance ID
        #       'db_id': None,      # database instance ID after save
        #       'command': 'firefox',
        #       'icon': 'firefox',
        #       'window_state': {'x': 100, 'y': 100, 'width': 800, 'height': 600, 'state': 'normal'},
        #       'is_default': True
        #     }
        #   ]
        # }
        self.selected_id = None
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        
        self._handler_id = None
        
        # Load initial data
        self._load()
    
    def _load(self):
        """Load menu items from database with their instances"""
        self.items = []
        
        # Get items from database (title/hierarchy only)
        db_items = self.db.get_menu_items(self.menu_id, active_only=True)
        
        for db_item in db_items:
            # Create item dict
            item = {
                'id': str(db_item['id']),  # Use DB ID as temporary ID
                'db_id': db_item['id'],
                'title': db_item['title'],
                'depth': db_item['depth'],
                'parent_db_id': db_item['parent_id'],
                'instances': []
            }
            
            # Load instances for this item
            instances = self.db.get_item_instances(db_item['id'])
            
            for inst in instances:
                # Create window state dict if window data exists
                window_state = None
                if any([inst.get('x'), inst.get('y'), inst.get('width'), inst.get('height')]):
                    window_state = {
                        'x': inst.get('x'),
                        'y': inst.get('y'),
                        'width': inst.get('width'),
                        'height': inst.get('height'),
                        'state': inst.get('state', 'normal')
                    }
                
                instance_data = {
                    'id': str(inst['id']),
                    'db_id': inst['id'],
                    'command': inst['command'] or '',
                    'icon': inst['icon'] or '',
                    'window_state': window_state,
                    'is_default': bool(inst['is_default'])
                }
                item['instances'].append(instance_data)
            
            # Ensure at least one instance exists
            if not item['instances']:
                item['instances'].append({
                    'id': f"inst_{uuid.uuid4().hex[:8]}",
                    'db_id': None,
                    'command': '',
                    'icon': '',
                    'window_state': None,
                    'is_default': True
                })
            
            self.items.append(item)
        
        self._refresh_listbox()
        print(f"📥 Loaded {len(self.items)} items with instances for menu {self.menu_id}")
    
    def add_item(self, title="New Item"):
        """Add a new item with a default instance"""
        new_id = str(uuid.uuid4())[:8]
        
        # Create new item with default instance
        new_item = {
            'id': new_id,
            'db_id': None,
            'title': title,
            'depth': 0,
            'parent_db_id': None,
            'instances': [{
                'id': f"inst_{uuid.uuid4().hex[:8]}",
                'db_id': None,
                'command': '',
                'icon': '',
                'window_state': None,
                'is_default': True
            }]
        }
        
        self.items.append(new_item)
        self._refresh_listbox()
        
        # Select the new item
        self.selected_id = new_id
        
        print(f"📝 Added new item: {title} with default instance")
        return new_item
    
    def update_item(self, item_id, **kwargs):
        """Update an item's properties or its instances"""
        for item in self.items:
            if item['id'] == item_id:
                # Update basic item properties
                if 'title' in kwargs:
                    item['title'] = kwargs['title']
                    print(f"📦 Updated title for item {item_id}: {kwargs['title']}")
                
                # Handle instance updates
                if 'instance_idx' in kwargs:
                    instance_idx = kwargs['instance_idx']
                    
                    if 0 <= instance_idx < len(item['instances']):
                        instance = item['instances'][instance_idx]
                        
                        if 'command' in kwargs:
                            instance['command'] = kwargs['command']
                            print(f"📦 Updated command for item {item_id} instance {instance_idx}: {kwargs['command']}")
                        
                        if 'icon' in kwargs:
                            instance['icon'] = kwargs['icon']
                            print(f"📦 Updated icon for item {item_id} instance {instance_idx}: {kwargs['icon']}")
                        
                        if 'window_state' in kwargs:
                            state = kwargs['window_state']
                            if state:
                                instance['window_state'] = state
                                print(f"📦 Updated window state for item {item_id} instance {instance_idx}")
                            else:
                                instance['window_state'] = None
                                print(f"📦 Cleared window state for item {item_id} instance {instance_idx}")
                
                # Handle instance management
                if 'add_instance' in kwargs:
                    # Add new instance
                    new_instance = {
                        'id': f"inst_{uuid.uuid4().hex[:8]}",
                        'db_id': None,
                        'command': '',
                        'icon': '',
                        'window_state': None,
                        'is_default': False
                    }
                    item['instances'].append(new_instance)
                    print(f"➕ Added instance {len(item['instances'])} to item {item_id}")
                
                if 'remove_instance' in kwargs:
                    removed_idx = kwargs['remove_instance']
                    if 0 <= removed_idx < len(item['instances']):
                        # Don't remove the last instance
                        if len(item['instances']) > 1:
                            removed = item['instances'].pop(removed_idx)
                            print(f"➖ Removed instance {removed_idx} from item {item_id}")
                            
                            # If we removed the default, make first instance default
                            if removed.get('is_default'):
                                item['instances'][0]['is_default'] = True
                                print(f"🔀 Made instance 0 default for item {item_id}")
                
                self._refresh_listbox()
                return True
        return False
    
    def delete_item(self):
        """Delete selected item"""
        if not self.selected_id:
            return False
        
        # Find and remove the item
        for i, item in enumerate(self.items):
            if item['id'] == self.selected_id:
                removed = self.items.pop(i)
                self.selected_id = None
                self._refresh_listbox()
                print(f"🗑️ Deleted item: {removed['title']}")
                return True
        
        return False
    
    def get_item_by_id(self, item_id):
        """Get item by ID with its instances"""
        for item in self.items:
            if item['id'] == item_id:
                return item
        return None
    
    def get_selected_item(self):
        """Get currently selected item with its instances"""
        if not self.selected_id:
            return None
        
        return self.get_item_by_id(self.selected_id)
    
    def get_instance_for_item(self, item_id, instance_idx=0):
        """Get specific instance for an item"""
        item = self.get_item_by_id(item_id)
        if item and 0 <= instance_idx < len(item['instances']):
            return item['instances'][instance_idx]
        return None
    
    def move_up(self):
        """Move selected item up"""
        if not self.selected_id:
            return
        
        for i, item in enumerate(self.items):
            if item['id'] == self.selected_id and i > 0:
                # Swap with item above
                self.items[i], self.items[i-1] = self.items[i-1], self.items[i]
                self._refresh_listbox()
                print(f"⬆️ Moved item up: {item['title']}")
                return
    
    def move_down(self):
        """Move selected item down"""
        if not self.selected_id:
            return
        
        for i, item in enumerate(self.items):
            if item['id'] == self.selected_id and i < len(self.items) - 1:
                # Swap with item below
                self.items[i], self.items[i+1] = self.items[i+1], self.items[i]
                self._refresh_listbox()
                print(f"⬇️ Moved item down: {item['title']}")
                return
    
    def indent(self):
        """Increase depth (make child of previous item)"""
        if not self.selected_id:
            return
        
        for i, item in enumerate(self.items):
            if item['id'] == self.selected_id and i > 0:
                item['depth'] = min(self.items[i-1]['depth'] + 1, 4)
                item['parent_db_id'] = self.items[i-1].get('db_id')
                self._refresh_listbox()
                print(f"↪️ Indented item: {item['title']} (depth: {item['depth']})")
                return
    
    def outdent(self):
        """Decrease depth (make sibling of parent)"""
        if not self.selected_id:
            return
        
        for i, item in enumerate(self.items):
            if item['id'] == self.selected_id and item['depth'] > 0:
                item['depth'] = max(item['depth'] - 1, 0)
                # Find new parent (nearest item with lower depth)
                for j in range(i-1, -1, -1):
                    if self.items[j]['depth'] == item['depth']:
                        item['parent_db_id'] = self.items[j].get('db_id')
                        break
                    elif self.items[j]['depth'] < item['depth']:
                        item['parent_db_id'] = None
                        break
                self._refresh_listbox()
                print(f"↩️ Outdented item: {item['title']} (depth: {item['depth']})")
                return

    def unselect_all(self):
        """Clear all selection states"""
        self.selected_id = None
        # GTK listbox will handle visual unselection    

    def save(self):
        """Save items and their instances to database"""
        print(f"💾 Saving {len(self.items)} items with instances to menu {self.menu_id}...")
        
        try:
            # Use a transaction
            with self.db.transaction():
                # Save each item
                for item_index, item in enumerate(self.items):
                    item_data = {
                        'title': item['title'],
                        'parent_id': item['parent_db_id'],
                        'depth': item['depth'],
                        'sort_order': item_index * 10  # Simple ordering
                    }
                    
                    if item['db_id']:
                        # Update existing item
                        item_data['id'] = item['db_id']
                        self.db.update_menu_item(item['db_id'], **item_data)
                        item_id = item['db_id']
                        print(f"  📝 Updated item: {item['title']} (ID: {item_id})")
                    else:
                        # Insert new item
                        item_id = self.db.create_menu_item(
                            self.menu_id,
                            item['title'],
                            item['parent_db_id'],
                            item['depth']
                        )
                        item['db_id'] = item_id
                        print(f"  📝 Created item: {item['title']} (ID: {item_id})")
                    
                    # Save instances for this item
                    for inst_index, instance in enumerate(item['instances']):
                        instance_data = {
                            'item_id': item_id,
                            'instance_name': f'Instance {inst_index + 1}',
                            'command': instance['command'],
                            'icon': instance['icon'],
                            'is_default': instance.get('is_default', inst_index == 0)
                        }
                        
                        # Add window state if exists
                        if instance.get('window_state'):
                            ws = instance['window_state']
                            instance_data.update({
                                'x': ws.get('x'),
                                'y': ws.get('y'),
                                'width': ws.get('width'),
                                'height': ws.get('height'),
                                'state': ws.get('state', 'normal')
                            })
                        
                        # Update or insert
                        if instance.get('db_id'):
                            instance_data['id'] = instance['db_id']
                            self.db.save_item_instance(instance_data)
                            print(f"    🔄 Updated instance {inst_index + 1}")
                        else:
                            new_inst_id = self.db.save_item_instance(instance_data)
                            instance['db_id'] = new_inst_id
                            print(f"    ➕ Created instance {inst_index + 1} (ID: {new_inst_id})")
            
            print(f"✅ Saved {len(self.items)} items successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Save failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _refresh_listbox(self):
        """Refresh the listbox display"""
        # Clear current rows
        for row in self.listbox.get_children():
            self.listbox.remove(row)
        
        # Add rows for each item
        for item in self.items:
            row = Gtk.ListBoxRow()
            
            # Create content with indentation
            content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            
            # Add indentation based on depth
            indent_label = Gtk.Label(label="  " * item['depth'])
            content.pack_start(indent_label, False, False, 0)
            
            # Item title with instance count
            instance_count = len(item['instances'])
            title_text = f"{item['title']}"
            if instance_count > 1:
                title_text += f" ({instance_count} instances)"
            
            title_label = Gtk.Label(label=title_text)
            title_label.set_xalign(0)
            content.pack_start(title_label, True, True, 0)
            
            row.add(content)
            row.item_id = item['id']  # Store item ID on row
            
            # Highlight if selected
            if item['id'] == self.selected_id:
                row.set_state_flags(Gtk.StateFlags.SELECTED, False)
            
            self.listbox.add(row)
        
        self.listbox.show_all()
