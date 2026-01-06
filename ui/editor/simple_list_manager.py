"""
SIMPLE List Manager - Just works
GTK-safe version - BACK TO BASICS
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import uuid


class SimpleListManager:
    def __init__(self, db, menu_id):
        self.db = db
        self.menu_id = menu_id
        
        self.items = []  # Simple list: [{id, title, depth, command, icon, db_id}]
        self.selected_id = None
        
        # Create UI
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect("row-selected", self._on_row_selected)
        
        # Load data
        self._load()
    
    def _load(self):
        """Load from database - simple flatten"""
        self.items = []
        
        # Get all active items
        db_items = self.db.get_menu_items(self.menu_id, active_only=True)
        
        # Build parent-child map
        children = {}
        for item in db_items:
            parent_id = item.get('parent_id')
            if parent_id:
                if parent_id not in children:
                    children[parent_id] = []
                children[parent_id].append(item)
        
        # Find roots
        roots = []
        items_by_id = {item['id']: item for item in db_items}
        for item in db_items:
            parent_id = item.get('parent_id')
            if not parent_id or parent_id not in items_by_id:
                roots.append(item)
        
        # Flatten
        def add_items(items, depth):
            for item in sorted(items, key=lambda x: x.get('sort_order', 0)):
                self.items.append({
                    'id': str(uuid.uuid4())[:8],  # Temp ID for UI
                    'db_id': item['id'],  # Real DB ID
                    'title': item['title'],
                    'depth': depth,
                    'command': item.get('command', ''),
                    'icon': item.get('icon', ''),
                    'parent_db_id': item.get('parent_id')
                })
                
                # Add children
                if item['id'] in children:
                    add_items(children[item['id']], depth + 1)
        
        add_items(roots, 0)
        GLib.idle_add(self._refresh_listbox)
    
    def _refresh_listbox(self):
        """GTK-safe listbox refresh - SIMPLE VERSION"""
        if not self.listbox:
            return False
        
        # Store the handler ID to block signals
        handler_id = getattr(self, '_handler_id', None)
        if handler_id:
            self.listbox.handler_block(handler_id)
        
        # Clear
        for row in list(self.listbox.get_children()):
            self.listbox.remove(row)
        
        # Add items
        for item in self.items:
            row = Gtk.ListBoxRow()
            row.item_id = item['id']
            
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            hbox.set_margin_start(5 + (item['depth'] * 20))
            hbox.set_margin_top(2)
            hbox.set_margin_bottom(2)
            
            label = Gtk.Label(label=item['title'])
            label.set_xalign(0)
            hbox.pack_start(label, True, True, 0)
            
            row.add(hbox)
            self.listbox.add(row)
        
        self.listbox.show_all()
        
        # Restore selection CAREFULLY
        if self.selected_id:
            found = False
            for row in self.listbox.get_children():
                if hasattr(row, 'item_id') and row.item_id == self.selected_id:
                    self.listbox.select_row(row)
                    found = True
                    break
            
            # If not found, clear selection
            if not found:
                self.selected_id = None
        
        # Unblock signals
        if handler_id:
            self.listbox.handler_unblock(handler_id)
        
        return False
    
    def _on_row_selected(self, listbox, row):
        """Handle row selection - IGNORE EMPTY CLICKS COMPLETELY"""
        # Only update if we actually clicked a row
        if row and hasattr(row, 'item_id'):
            self.selected_id = row.item_id
            print(f"📋 ListManager: User selected {row.item_id}")
    
    def create_panel(self):
        """Create the panel with buttons"""
        frame = Gtk.Frame(label="Menu Items")
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox.set_margin_top(5)
        vbox.set_margin_bottom(5)
        vbox.set_margin_start(5)
        vbox.set_margin_end(5)
        
        # List in scroll
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.listbox)
        vbox.pack_start(scrolled, True, True, 0)
        
        # Buttons
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        
        for label, callback in [
            ("Add", self.add_item),
            ("Del", self.delete_item),
            ("Up", self.move_up),
            ("Down", self.move_down),
            (">", self.indent),
            ("<", self.outdent)
        ]:
            btn = Gtk.Button(label=label)
            btn.connect("clicked", callback)
            buttons.pack_start(btn, True, True, 0)
        
        vbox.pack_start(buttons, False, False, 0)
        frame.add(vbox)
        return frame
    
    def add_item(self, button=None):
        """Add new item after selected - SELECT THE NEW ITEM"""
        new_id = str(uuid.uuid4())[:8]
        depth = 0
        insert_index = len(self.items)  # Default: append at end
        
        if self.selected_id:
            for i, item in enumerate(self.items):
                if item['id'] == self.selected_id:
                    depth = item['depth']
                    insert_index = i + 1
                    break
        
        new_item = {
            'id': new_id,
            'db_id': None,
            'title': "New Item",
            'depth': depth,
            'command': "",
            'icon': "",
            'parent_db_id': None
        }
        
        self.items.insert(insert_index, new_item)
        self.selected_id = new_id  # SELECT THE NEW ITEM
        self._refresh_listbox()
        return new_item
    
    def delete_item(self, button=None):
        """Delete selected item and children - SELECT ITEM ABOVE"""
        if not self.selected_id:
            return
        
        for i, item in enumerate(self.items):
            if item['id'] == self.selected_id:
                # Find children
                delete_start = i
                delete_end = i + 1
                current_depth = item['depth']
                
                for j in range(i + 1, len(self.items)):
                    if self.items[j]['depth'] <= current_depth:
                        break
                    delete_end = j + 1
                
                # Delete
                del self.items[delete_start:delete_end]
                
                # Update selection: select item above, or first if at top
                if delete_start > 0:
                    # Select the item above the deleted range
                    self.selected_id = self.items[delete_start - 1]['id']
                elif len(self.items) > 0:
                    # Select first item
                    self.selected_id = self.items[0]['id']
                else:
                    # No items left
                    self.selected_id = None
                
                self._refresh_listbox()
                break
    
    def move_up(self, button=None):
        """Move item up - KEEP SAME ITEM SELECTED (it moves up)"""
        if not self.selected_id:
            return
        
        for i, item in enumerate(self.items):
            if item['id'] == self.selected_id and i > 0:
                # Swap items
                self.items[i], self.items[i-1] = self.items[i-1], self.items[i]
                # selected_id stays the same (item moves)
                self._refresh_listbox()
                break
    
    def move_down(self, button=None):
        """Move item down - KEEP SAME ITEM SELECTED (it moves down)"""
        if not self.selected_id:
            return
        
        for i, item in enumerate(self.items):
            if item['id'] == self.selected_id and i < len(self.items) - 1:
                # Swap items
                self.items[i], self.items[i+1] = self.items[i+1], self.items[i]
                # selected_id stays the same (item moves)
                self._refresh_listbox()
                break
    
    def indent(self, button=None):
        """Indent item - KEEP SAME ITEM SELECTED"""
        if not self.selected_id:
            return
        
        for i, item in enumerate(self.items):
            if item['id'] == self.selected_id and i > 0:
                item['depth'] += 1
                # selected_id stays the same
                self._refresh_listbox()
                break
    
    def outdent(self, button=None):
        """Outdent item - KEEP SAME ITEM SELECTED"""
        if not self.selected_id:
            return
        
        for i, item in enumerate(self.items):
            if item['id'] == self.selected_id and item['depth'] > 0:
                item['depth'] -= 1
                # selected_id stays the same
                self._refresh_listbox()
                break

    def get_selected_item(self):
        """Get selected item"""
        if self.selected_id:
            for item in self.items:
                if item['id'] == self.selected_id:
                    return item
        return None
    
    def update_item(self, item_id, **kwargs):
        """Update item properties"""
        for item in self.items:
            if item['id'] == item_id:
                for key, value in kwargs.items():
                    if key in item:
                        item[key] = value
                
                # Only refresh listbox if title changed
                if 'title' in kwargs:
                    # Update label directly instead of full refresh
                    for row in self.listbox.get_children():
                        if hasattr(row, 'item_id') and row.item_id == item_id:
                            hbox = row.get_child()
                            label = hbox.get_children()[0]
                            label.set_text(kwargs['title'])
                            break
                return True
        return False
        
        def save(self):
            """Save to database - simple replace"""
        with self.db.transaction():
            # Mark all as inactive
            self.db.execute(
                "UPDATE menu_items SET is_active = 0 WHERE menu_id = ?",
                (self.menu_id,)
            )
            
            # Rebuild tree from flat list
            stack = []  # (depth, parent_db_id)
            sort_order = 0
            
            for item in self.items:
                sort_order += 10
                
                # Find parent
                while stack and stack[-1][0] >= item['depth']:
                    stack.pop()
                
                parent_id = stack[-1][1] if stack else None
                
                # Insert or update
                if item.get('db_id'):
                    # Update
                    self.db.update_menu_item(
                        item['db_id'],
                        title=item['title'],
                        command=item['command'],
                        icon=item['icon'],
                        parent_id=parent_id,
                        sort_order=sort_order,
                        is_active=True
                    )
                    new_db_id = item['db_id']
                else:
                    # Insert
                    new_db_id = self.db.add_menu_item(
                        menu_id=self.menu_id,
                        title=item['title'],
                        command=item['command'],
                        icon=item['icon'],
                        parent_id=parent_id,
                        sort_order=sort_order
                    )
                    item['db_id'] = new_db_id
                
                stack.append((item['depth'], new_db_id))
            
            return True
