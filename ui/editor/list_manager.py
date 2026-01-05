import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import uuid


class ListManager:
    def __init__(self, db, menu_model):
        self.db = db
        self.model = menu_model
        
        self.on_selection_changed = None
        self.on_item_modified = None
        
        self.items = []
        self.selected_id = None
        
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect("row-selected", self._row_selected)
        self._refresh_pending = False 
        
        self._load_from_model()
    
    def _row_selected(self, listbox, row):
        if row and hasattr(row, 'item_id'):
            self.selected_id = row.item_id
            if self.on_selection_changed:
                GLib.idle_add(lambda: self.on_selection_changed(row.item_id))
    
    def _load_from_model(self):
        self.items.clear()
        self._flatten_tree(self.model.root_items, 0)
        self._refresh_listbox()
    
    def _flatten_tree(self, items, depth):
        for item in sorted(items, key=lambda x: x.sort_order):
            if not item.is_deleted:
                flat_item = {
                    'id': item.id,
                    'db_id': item.db_id,
                    'title': item.title,
                    'depth': depth,
                    'command': item.command or "",
                    'icon': item.icon or "",
                    'window_state': item.window_state,
                    'sort_order': item.sort_order
                }
                self.items.append(flat_item)
                
                if item.children:
                    self._flatten_tree(item.children, depth + 1)
    
    def _refresh_listbox(self):
        # If a refresh is already pending, skip
        if self._refresh_pending:
            return
        
        self._refresh_pending = True
        
        # Only refresh if listbox exists
        if not self.listbox:
            self._refresh_pending = False
            return
        
        # Destroy all current rows
        children = list(self.listbox.get_children())
        for child in children:
            child.destroy()
        
        # Add new rows
        for item in self.items:
            row = self._create_row(item)
            self.listbox.add(row)
        
        # Show all at once
        self.listbox.show_all()
        
        # Restore selection on idle
        if self.selected_id:
            def restore_and_clear():
                self._restore_selection()
                self._refresh_pending = False
                return False
            GLib.idle_add(restore_and_clear)
        else:
            self._refresh_pending = False

    def _restore_selection(self):
        if not self.selected_id:
            return False  # Run once
        
        for row in self.listbox.get_children():
            if hasattr(row, 'item_id') and row.item_id == self.selected_id:
                self.listbox.select_row(row)
                break
        
        return False  

    
    def _create_row(self, item):
        row = Gtk.ListBoxRow()
        row.item_id = item['id']
        
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        hbox.set_margin_start(5 + (item['depth'] * 20))
        hbox.set_margin_end(5)
        hbox.set_margin_top(2)
        hbox.set_margin_bottom(2)
        
        label = Gtk.Label(label=item['title'])
        label.set_xalign(0)
        hbox.pack_start(label, True, True, 0)
        
        row.add(hbox)
        return row
    
    def create_nav_panel(self):
        frame = Gtk.Frame(label="Menu Items")
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox.set_margin_top(5)
        vbox.set_margin_bottom(5)
        vbox.set_margin_start(5)
        vbox.set_margin_end(5)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.listbox)
        vbox.pack_start(scrolled, True, True, 0)
        
        vbox.pack_start(self._create_buttons(), False, False, 0)
        
        frame.add(vbox)
        return frame
    
    def _create_buttons(self):
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        
        buttons = [
            ("Add", self._add_item),
            ("Del", self._delete_item),
            ("Up", self._move_up),
            ("Down", self._move_down),
            (">", self._indent),
            ("<", self._outdent),
        ]
        
        for text, callback in buttons:
            btn = Gtk.Button(label=text)
            btn.connect("clicked", callback)
            hbox.pack_start(btn, True, True, 0)
        
        return hbox
    
    def _add_item(self, button):
        if not self.selected_id and self.items:
            self.selected_id = self.items[0]['id']
        
        insert_at = len(self.items)
        depth = 0
        
        if self.selected_id:
            for i, item in enumerate(self.items):
                if item['id'] == self.selected_id:
                    insert_at = i + 1
                    depth = item['depth']
                    break
        
        new_id = str(uuid.uuid4())[:8]
        new_item = {
            'id': new_id,
            'db_id': None,
            'title': 'New Item',
            'depth': depth,
            'command': '',
            'icon': '',
            'window_state': None,
            'sort_order': insert_at * 10
        }
        
        self.items.insert(insert_at, new_item)
        
        for i, item in enumerate(self.items):
            item['sort_order'] = i * 10
        
        self.selected_id = new_id
        self._refresh_listbox()
        
        if self.on_item_modified:
            GLib.idle_add(lambda: self.on_item_modified(new_id, 'added', True))
    
    def _delete_item(self, button):
        if not self.selected_id:
            return
        
        for i, item in enumerate(self.items):
            if item['id'] == self.selected_id:
                delete_start = i
                delete_end = i + 1
                
                current_depth = item['depth']
                for j in range(i + 1, len(self.items)):
                    if self.items[j]['depth'] <= current_depth:
                        break
                    delete_end = j + 1
                
                deleted_items = self.items[delete_start:delete_end]
                del self.items[delete_start:delete_end]
                
                if delete_start < len(self.items):
                    self.selected_id = self.items[delete_start]['id']
                elif delete_start > 0:
                    self.selected_id = self.items[delete_start - 1]['id']
                else:
                    self.selected_id = None
                
                for i, item in enumerate(self.items):
                    item['sort_order'] = i * 10
                
                self._refresh_listbox()
                
                if self.on_item_modified:
                    for deleted_item in deleted_items:
                        GLib.idle_add(lambda i=deleted_item['id']: self.on_item_modified(i, 'deleted', True))
                break
    
    def _move_up(self, button):
        if not self.selected_id:
            return
        
        for i, item in enumerate(self.items):
            if item['id'] == self.selected_id and i > 0:
                self.items[i], self.items[i-1] = self.items[i-1], self.items[i]
                
                for j, it in enumerate(self.items):
                    it['sort_order'] = j * 10
                
                # Schedule ONE refresh
                GLib.idle_add(self._refresh_listbox)
                
                if self.on_item_modified:
                    GLib.idle_add(lambda: self.on_item_modified(item['id'], 'moved', 'up'))
                break
    
    def _move_down(self, button):
        if not self.selected_id:
            return
        
        for i, item in enumerate(self.items):
            if item['id'] == self.selected_id and i < len(self.items) - 1:
                self.items[i], self.items[i+1] = self.items[i+1], self.items[i]
                
                for j, it in enumerate(self.items):
                    it['sort_order'] = j * 10
                
                self._refresh_listbox()
                
                if self.on_item_modified:
                    GLib.idle_add(lambda: self.on_item_modified(item['id'], 'moved', 'down'))
                break
    
    def _indent(self, button):
        if not self.selected_id:
            return
        
        for i, item in enumerate(self.items):
            if item['id'] == self.selected_id and i > 0:
                item['depth'] += 1
                self._refresh_listbox()
                
                if self.on_item_modified:
                    GLib.idle_add(lambda: self.on_item_modified(item['id'], 'indent', item['depth']))
                break
    
    def _outdent(self, button):
        if not self.selected_id:
            return
        
        for i, item in enumerate(self.items):
            if item['id'] == self.selected_id and item['depth'] > 0:
                item['depth'] -= 1
                self._refresh_listbox()
                
                if self.on_item_modified:
                    GLib.idle_add(lambda: self.on_item_modified(item['id'], 'outdent', item['depth']))
                break
    
    def update_item_title(self, item_id, new_title):
        for item in self.items:
            if item['id'] == item_id:
                item['title'] = new_title
                self._refresh_listbox()
                return True
        return False
    
    def get_selected_item(self):
        if self.selected_id:
            for item in self.items:
                if item['id'] == self.selected_id:
                    return item
        return None
    
    def get_item_properties(self, item_id):
        for item in self.items:
            if item['id'] == item_id:
                return {
                    'title': item['title'],
                    'command': item['command'],
                    'icon': item['icon'],
                    'window_state': item['window_state']
                }
        return None
    
    def update_item_properties(self, item_id, **kwargs):
        for item in self.items:
            if item['id'] == item_id:
                for key, value in kwargs.items():
                    if key in item:
                        item[key] = value
                self._refresh_listbox()
                return True
        return False
    
    def rebuild_list(self):
        self._load_from_model()
    
    def save_to_model(self, model):
        """Simple: Just mark model as modified"""
        print("✅ List saved to model (marked as modified)")
        model.is_modified = True
        return True
    
    @property
    def display_items(self):
        return self.items
