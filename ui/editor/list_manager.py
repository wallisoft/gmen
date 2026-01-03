"""
List Manager - Simple, linear display of hierarchical menu items
Replaces complex TreeManager with clean ListBox approach
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
from typing import Optional, List
import time


class ListManager:
    """Simple list-based manager for menu items with hierarchy display"""
    
    def __init__(self, db, menu_model):
        self.db = db
        self.model = menu_model
        
        # Callbacks (same interface as TreeManager)
        self.on_selection_changed = None
        self.on_item_modified = None
        
        # List store: display_text, item_id, depth
        self.list_store = Gtk.ListStore(str, str, int)
        
        # ListBox for display
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect("row-selected", self._on_row_selected)
        
        # Create ListBox with custom row renderer
        self._setup_listbox()
        
        # Track last refresh for debouncing
        self.last_refresh_time = 0
    
    def _setup_listbox(self):
        """Setup ListBox with custom row renderer"""
        # Create a custom row with indentation support
        self.listbox.set_header_func(None)
        
        # Connect to model
        self.listbox.bind_model(self.list_store, self._create_listbox_row)
    
    def _create_listbox_row(self, item):
        """Create a ListBoxRow for an item in the list store"""
        row = Gtk.ListBoxRow()
        
        # Create horizontal box for indentation + label
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        hbox.set_margin_start(5)
        hbox.set_margin_end(5)
        hbox.set_margin_top(3)
        hbox.set_margin_bottom(3)
        
        # Add indentation based on depth
        depth = item[2]
        if depth > 0:
            indent_label = Gtk.Label(label="    " * depth)
            indent_label.set_xalign(0)
            hbox.pack_start(indent_label, False, False, 0)
        
        # Add the actual item label
        label = Gtk.Label(label=item[0])
        label.set_xalign(0)
        label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        hbox.pack_start(label, True, True, 0)
        
        # Add indicator for folders
        if len(self.model.get_item(item[1]).children) > 0:
            folder_label = Gtk.Label(label="📁")
            folder_label.set_margin_start(5)
            hbox.pack_start(folder_label, False, False, 0)
        
        row.add(hbox)
        return row
    
    def create_nav_panel(self):
        """Create navigation panel with list and buttons"""
        frame = Gtk.Frame(label="📂 Menu Items")
        frame.set_shadow_type(Gtk.ShadowType.IN)
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox.set_margin_top(5)
        vbox.set_margin_bottom(5)
        vbox.set_margin_start(5)
        vbox.set_margin_end(5)
        
        # Scrolled window for list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.listbox)
        vbox.pack_start(scrolled, True, True, 0)
        
        # Navigation buttons
        vbox.pack_start(self._create_nav_buttons(), False, False, 0)
        
        frame.add(vbox)
        return frame
    
    def _create_nav_buttons(self):
        """Create navigation buttons"""
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        
        self.add_btn = Gtk.Button(label="⊕ Add")
        self.add_btn.set_tooltip_text("Add item below selected")
        self.add_btn.connect("clicked", self.on_add)
        
        self.submenu_btn = Gtk.Button(label="📁 Sub-Menu")
        self.submenu_btn.set_tooltip_text("Add subitem")
        self.submenu_btn.connect("clicked", self.on_submenu)
        
        self.remove_btn = Gtk.Button(label="⊖ Remove")
        self.remove_btn.set_tooltip_text("Remove selected")
        self.remove_btn.connect("clicked", self.on_remove)
        
        self.up_btn = Gtk.Button(label="↑ Up")
        self.up_btn.set_tooltip_text("Move item up")
        self.up_btn.connect("clicked", self.on_up)
        
        self.down_btn = Gtk.Button(label="↓ Down")
        self.down_btn.set_tooltip_text("Move item down")
        self.down_btn.connect("clicked", self.on_down)
        
        hbox.pack_start(self.add_btn, True, True, 0)
        hbox.pack_start(self.submenu_btn, True, True, 0)
        hbox.pack_start(self.remove_btn, True, True, 0)
        hbox.pack_start(self.up_btn, True, True, 0)
        hbox.pack_start(self.down_btn, True, True, 0)
        
        return hbox
    
    def rebuild_list(self):
        """Rebuild entire list from model - SIMPLE LINEAR FLATTENING"""
        current_time = time.time()
        if current_time - self.last_refresh_time < 0.1:  # Debounce
            return
        self.last_refresh_time = current_time
        
        print("📋 Rebuilding list from model...")
        
        # Save current selection
        selected_id = self._get_selected_item_id()
        
        # Clear and rebuild - SIMPLE!
        self.list_store.clear()
        self._add_items_recursive(self.model.root_items, 0)
        
        # Restore selection if possible
        if selected_id:
            GLib.timeout_add(50, self._select_by_id, selected_id)
        
        print(f"✅ List rebuilt with {len(self.list_store)} items")
    
    def _add_items_recursive(self, items, depth):
        """Add items recursively with indentation"""
        for item in sorted(items, key=lambda x: x.sort_order):
            if not item.is_deleted:
                # Add to list store
                self.list_store.append([item.title, item.id, depth])
                
                # Add children with increased depth
                if item.children:
                    self._add_items_recursive(item.children, depth + 1)
    
    def refresh_item(self, item_id: str) -> bool:
        """Update a single item in list"""
        print(f"🔍 refresh_item looking for '{item_id}'")
        
        # Find the item in list store
        for i, row in enumerate(self.list_store):
            if row[1] == item_id:
                # Get updated item from model
                item = self.model.get_item(item_id)
                if not item or item.is_deleted:
                    # Remove from list
                    self.list_store.remove(row.iter)
                    print(f"✅ Removed deleted item")
                    return True
                
                # Update the row
                old_title = row[0]
                if old_title != item.title:
                    self.list_store.set_value(row.iter, 0, item.title)
                    print(f"✅ Updated item '{old_title}' → '{item.title}'")
                return True
        
        # Item not found - might need full rebuild
        print(f"⚠️ Item {item_id} not found in list, rebuilding...")
        self.rebuild_list()
        return False
    
    def update_item_title(self, item_id: str, new_title: str) -> bool:
        """Update item title in list IMMEDIATELY"""
        print(f"📝 ListManager.update_item_title({item_id}, '{new_title}')")
        
        # First update the list IMMEDIATELY
        for row in self.list_store:
            if row[1] == item_id:
                self.list_store.set_value(row.iter, 0, new_title)
                print(f"✅ List updated immediately")
                break
        
        # Then update model
        if self.model.update_item(item_id, title=new_title):
            # Ensure list is synced
            success = self.refresh_item(item_id)
            
            # Notify editor
            if success and self.on_item_modified:
                self.on_item_modified(item_id, 'title', new_title)
            
            return success
        
        return False
    
    # ===== Event Handlers =====
    
    def _on_row_selected(self, listbox, row):
        """Handle list selection change"""
        if row and self.on_selection_changed:
            # Get the model row for this ListBoxRow
            index = row.get_index()
            if index >= 0:
                list_store_row = self.list_store[index]
                item_id = list_store_row[1]
                self.on_selection_changed(item_id)
    
    def on_add(self, button):
        """Add new item below selected item"""
        selected_id = self._get_selected_item_id()
        
        parent_id = None
        insert_after_id = None
        
        if selected_id:
            selected_item = self.model.get_item(selected_id)
            if selected_item:
                # Insert at SAME LEVEL as selected item
                parent_id = selected_item.parent_id
                insert_after_id = selected_id
        
        print(f"➕ Adding item at level {parent_id}, after {insert_after_id}")
        
        # Add to model
        new_item = self.model.add_item("New Item", parent_id, insert_after_id)
        
        # Rebuild list
        self.rebuild_list()
        
        # Select new item
        GLib.idle_add(self._select_by_id, new_item.id)
        
        # Notify editor
        if self.on_item_modified:
            self.on_item_modified(new_item.id, 'title', 'New Item')
    
    def on_submenu(self, button):
        """Add subitem under selected item"""
        selected_id = self._get_selected_item_id()
        if not selected_id:
            return
        
        # Add subitem
        new_item = self.model.add_item("Sub-Menu", selected_id)
        
        # Rebuild list
        self.rebuild_list()
        
        # Select new item
        GLib.idle_add(self._select_by_id, new_item.id)
        
        # Notify editor
        if self.on_item_modified:
            self.on_item_modified(new_item.id, 'title', 'Sub-Menu')
    
    def on_remove(self, button):
        """Remove selected item"""
        selected_id = self._get_selected_item_id()
        if not selected_id:
            return
        
        # Delete from model
        if self.model.delete_item(selected_id):
            # Rebuild list
            self.rebuild_list()
            
            # Clear selection
            self.listbox.unselect_all()
            
            # Notify editor
            if self.on_item_modified:
                self.on_item_modified(selected_id, 'deleted', True)
    
    def on_up(self, button):
        """Move item up"""
        selected_id = self._get_selected_item_id()
        if not selected_id:
            return
        
        # Move in model
        if self.model.move_item(selected_id, 'up'):
            # Rebuild list
            self.rebuild_list()
            
            # Keep selection
            GLib.idle_add(self._select_by_id, selected_id)
        
        # Notify editor
        if self.on_item_modified:
            self.on_item_modified(selected_id, 'moved', 'up')
    
    def on_down(self, button):
        """Move item down"""
        selected_id = self._get_selected_item_id()
        if not selected_id:
            return
        
        # Move in model
        if self.model.move_item(selected_id, 'down'):
            # Rebuild list
            self.rebuild_list()
            
            # Keep selection
            GLib.idle_add(self._select_by_id, selected_id)
        
        # Notify editor
        if self.on_item_modified:
            self.on_item_modified(selected_id, 'moved', 'down')
    
    # ===== Helper Methods =====
    
    def _get_selected_item_id(self) -> Optional[str]:
        """Get ID of currently selected item"""
        row = self.listbox.get_selected_row()
        if row:
            index = row.get_index()
            if index >= 0:
                return self.list_store[index][1]
        return None
    
    def _select_by_id(self, item_id: str):
        """Select item by ID"""
        for i, row in enumerate(self.list_store):
            if row[1] == item_id:
                listbox_row = self.listbox.get_row_at_index(i)
                if listbox_row:
                    self.listbox.select_row(listbox_row)
                    # Scroll to make visible
                    self.listbox.scroll_to_row(listbox_row)
                return True
        return False
