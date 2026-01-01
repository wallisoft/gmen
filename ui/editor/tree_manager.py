"""
Tree view management for the editor
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from core.menu.builder import MenuBuilder


class TreeManager:
    """Manages the tree view of menu items"""
    
    def __init__(self, db):
        self.db = db
        self.current_menu_id = None
        self.next_temp_id = -1
        
        # Callbacks
        self.on_selection_changed = None
        self.on_item_modified = None
        self.on_item_added = None
        self.on_item_deleted = None
        
        # Tree store: text, depth, item_id, parent_id, has_children, sort_order, is_new
        self.list_store = Gtk.TreeStore(str, int, int, int, bool, int, bool)
        
        # Tree view
        self.treeview = Gtk.TreeView(model=self.list_store)
        text_renderer = Gtk.CellRendererText()
        text_column = Gtk.TreeViewColumn("Items", text_renderer, text=0)
        text_column.set_expand(True)
        self.treeview.append_column(text_column)
        
        # Selection
        self.selection = self.treeview.get_selection()
        self.selection.connect("changed", self._on_selection_changed)
    
    def create_nav_panel(self):
        """Create navigation panel with tree and buttons"""
        frame = Gtk.Frame(label="📂 Menu Items")
        frame.set_shadow_type(Gtk.ShadowType.IN)
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox.set_margin_top(5)
        vbox.set_margin_bottom(5)
        vbox.set_margin_start(5)
        vbox.set_margin_end(5)
        
        # Scrolled window for tree
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.treeview)
        vbox.pack_start(scrolled, True, True, 0)
        
        # Navigation buttons
        vbox.pack_start(self._create_nav_buttons(), False, False, 0)
        
        frame.add(vbox)
        return frame
    
    def _create_nav_buttons(self):
        """Create navigation buttons"""
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        
        self.add_btn = Gtk.Button(label="⊕ Add")
        self.add_btn.set_tooltip_text("Add item at same level")
        self.add_btn.connect("clicked", self.on_add)
        
        self.submenu_btn = Gtk.Button(label="📁 Sub-Menu")
        self.submenu_btn.set_tooltip_text("Add subitem")
        self.submenu_btn.connect("clicked", self.on_submenu)
        
        self.remove_btn = Gtk.Button(label="⊖ Remove")
        self.remove_btn.set_tooltip_text("Remove selected item")
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
    
    def load_menu(self, menu_id):
        """Load menu items into tree"""
        self.current_menu_id = menu_id
        self.list_store.clear()
        self.next_temp_id = -1
        
        # Build menu hierarchy
        builder = MenuBuilder(self.db)
        menu_root = builder.build_menu(menu_id)
        
        # Check if menu is empty
        if not menu_root or len(menu_root.children) == 0:
            print("📭 Menu is empty")
            return
        
        # Helper to add items recursively
        def add_children(parent_iter, menu_item):
            for child in menu_item.children:
                has_children = len(child.children) > 0
                
                # Get database info
                db_info = self.db.fetch_one(
                    "SELECT sort_order, parent_id FROM menu_items WHERE id = ?",
                    (child.id,)
                )
                sort_order = db_info['sort_order'] if db_info else 0
                parent_id = db_info['parent_id'] if db_info else None
                
                # Add to tree
                child_iter = self.list_store.append(
                    parent_iter,
                    [child.title, child.depth, child.id, parent_id, has_children, sort_order, False]
                )
                
                # Add grandchildren
                if has_children:
                    add_children(child_iter, child)
        
        # Add top-level items
        add_children(None, menu_root)
        
        print(f"📋 Loaded menu into UI")
    
    def _on_selection_changed(self, selection):
        """Handle tree selection change"""
        model, treeiter = selection.get_selected()
        if treeiter and self.on_selection_changed:
            item_id = model[treeiter][2]
            self.on_selection_changed(item_id)
    
    def on_add(self, button):
        """Add new item at current level"""
        selected_id = self._get_selected_item_id()
        parent_id = None
        depth = 0
        parent_iter = None
        
        if selected_id:
            iter = self._get_iter_by_id(selected_id)
            if iter:
                depth = self.list_store.get_value(iter, 1)
                parent_id = selected_id if depth > 0 else None
                parent_iter = self.list_store.iter_parent(iter)
        
        # Generate temporary ID
        temp_id = self.next_temp_id
        self.next_temp_id -= 1
        
        # Create new item in tree
        if parent_iter:
            new_iter = self.list_store.append(parent_iter)
        else:
            new_iter = self.list_store.append(None)
        
        # Calculate sort order
        sort_order = self._get_next_sort_order(parent_iter)
        
        # Set values
        self.list_store.set(new_iter,
            0, "New Item",
            1, depth,
            2, temp_id,
            3, parent_id,
            4, False,
            5, sort_order,
            6, True
        )
        
        # Call callback
        if self.on_item_added:
            item_data = {
                'temp_id': temp_id,
                'title': 'New Item',
                'depth': depth,
                'parent_id': parent_id,
                'sort_order': sort_order
            }
            self.on_item_added(temp_id, item_data)
        
        # Select the new item
        path = self.list_store.get_path(new_iter)
        self.treeview.scroll_to_cell(path, None, False, 0, 0)
        self.selection.select_iter(new_iter)
        
        # Update sort orders
        self._update_sort_orders(parent_iter)
    
    def on_submenu(self, button):
        """Add subitem under selected item"""
        selected_id = self._get_selected_item_id()
        if not selected_id:
            return
        
        iter = self._get_iter_by_id(selected_id)
        if not iter:
            return
        
        depth = self.list_store.get_value(iter, 1) + 1
        parent_id = selected_id
        
        # Generate temporary ID
        temp_id = self.next_temp_id
        self.next_temp_id -= 1
        
        # Create new item as child
        new_iter = self.list_store.append(iter)
        
        # Calculate sort order
        sort_order = self._get_next_sort_order(iter)
        
        # Set values
        self.list_store.set(new_iter,
            0, "Sub-Menu",
            1, depth,
            2, temp_id,
            3, parent_id,
            4, False,
            5, sort_order,
            6, True
        )
        
        # Update parent's has_children flag
        self.list_store.set_value(iter, 4, True)
        
        # Call callback
        if self.on_item_added:
            item_data = {
                'temp_id': temp_id,
                'title': 'Sub-Menu',
                'depth': depth,
                'parent_id': parent_id,
                'sort_order': sort_order
            }
            self.on_item_added(temp_id, item_data)
        
        # Expand parent
        path = self.list_store.get_path(iter)
        self.treeview.expand_row(path, False)
        
        # Select new item
        child_path = self.list_store.get_path(new_iter)
        self.treeview.scroll_to_cell(child_path, None, False, 0, 0)
        self.selection.select_iter(new_iter)
    
    def on_remove(self, button):
        """Remove selected item"""
        selected_id = self._get_selected_item_id()
        if not selected_id:
            return
        
        iter = self._get_iter_by_id(selected_id)
        if not iter:
            return
        
        # Get parent before removing
        parent_iter = self.list_store.iter_parent(iter)
        
        # Remove from tree
        self.list_store.remove(iter)
        
        # Update parent's has_children if needed
        if parent_iter:
            has_children = self.list_store.iter_has_child(parent_iter)
            self.list_store.set_value(parent_iter, 4, has_children)
        
        # Call callback
        if self.on_item_deleted:
            self.on_item_deleted(selected_id)
        
        # Update sort orders
        self._update_sort_orders(parent_iter)
        
        # Clear selection
        self.selection.unselect_all()
    
    def on_up(self, button):
        """Move item up"""
        selected_id = self._get_selected_item_id()
        if not selected_id:
            return
        
        if self._move_item_up(selected_id) and self.on_item_modified:
            # Call callback for sort_order change
            self.on_item_modified(selected_id, 'sort_order', None)
    
    def on_down(self, button):
        """Move item down"""
        selected_id = self._get_selected_item_id()
        if not selected_id:
            return
        
        if self._move_item_down(selected_id) and self.on_item_modified:
            # Call callback for sort_order change
            self.on_item_modified(selected_id, 'sort_order', None)
    
    def update_item_title(self, item_id, new_title):
        """Update item title in tree"""
        iter = self._get_iter_by_id(item_id)
        if iter:
            self.list_store.set_value(iter, 0, new_title)
            if self.on_item_modified:
                self.on_item_modified(item_id, 'title', new_title)
    
    # ===== Helper Methods =====
    
    def _get_selected_item_id(self):
        """Get ID of currently selected item"""
        model, treeiter = self.selection.get_selected()
        if treeiter:
            return model[treeiter][2]
        return None
    
    def _get_iter_by_id(self, item_id, parent_iter=None):
        """Find tree iter by item ID"""
        it = self.list_store.iter_children(parent_iter) if parent_iter else self.list_store.get_iter_first()
        
        while it:
            current_id = self.list_store.get_value(it, 2)
            if current_id == item_id:
                return it
            
            # Check children
            has_children = self.list_store.get_value(it, 4)
            if has_children:
                child_result = self._get_iter_by_id(item_id, it)
                if child_result:
                    return child_result
            
            it = self.list_store.iter_next(it)
        
        return None
    
    def _get_next_sort_order(self, parent_iter):
        """Get next sort order for a level"""
        max_order = 0
        it = self.list_store.iter_children(parent_iter) if parent_iter else self.list_store.get_iter_first()
        
        while it:
            order = self.list_store.get_value(it, 5)
            if order > max_order:
                max_order = order
            it = self.list_store.iter_next(it)
        
        return max_order + 1
    
    def _update_sort_orders(self, parent_iter):
        """Update sort orders for all items at a level"""
        index = 1
        it = self.list_store.iter_children(parent_iter) if parent_iter else self.list_store.get_iter_first()
        
        while it:
            old_order = self.list_store.get_value(it, 5)
            if old_order != index:
                self.list_store.set_value(it, 5, index)
                
                # Call callback for sort_order change (only for real items)
                item_id = self.list_store.get_value(it, 2)
                if item_id > 0 and self.on_item_modified:  # Only for real items, not temp ones
                    self.on_item_modified(item_id, 'sort_order', index)
            
            index += 1
            it = self.list_store.iter_next(it)
    
    def _move_item_up(self, item_id):
        """Move item up in tree"""
        iter = self._get_iter_by_id(item_id)
        if not iter:
            return False
        
        parent_iter = self.list_store.iter_parent(iter)
        path = self.list_store.get_path(iter)
        position = path.get_indices()[-1]
        
        if position == 0:
            return False
        
        # Get previous sibling
        prev_path = list(path)
        prev_path[-1] = position - 1
        prev_path = tuple(prev_path)
        prev_iter = self.list_store.get_iter(prev_path)
        
        if not prev_iter:
            return False
        
        # Swap values
        self._swap_tree_items(iter, prev_iter)
        
        # Update sort orders
        self._update_sort_orders(parent_iter)
        
        # Keep selection on moved item
        self.selection.select_iter(prev_iter)
        
        return True
    
    def _move_item_down(self, item_id):
        """Move item down in tree"""
        iter = self._get_iter_by_id(item_id)
        if not iter:
            return False
        
        parent_iter = self.list_store.iter_parent(iter)
        path = self.list_store.get_path(iter)
        position = path.get_indices()[-1]
        
        # Get next sibling
        next_path = list(path)
        next_path[-1] = position + 1
        next_path = tuple(next_path)
        next_iter = self.list_store.get_iter(next_path)
        
        if not next_iter:
            return False
        
        # Swap values
        self._swap_tree_items(iter, next_iter)
        
        # Update sort orders
        self._update_sort_orders(parent_iter)
        
        # Keep selection on moved item
        self.selection.select_iter(next_iter)
        
        return True
    
    def _swap_tree_items(self, iter1, iter2):
        """Swap two items in the tree"""
        # Get all data
        data1 = [self.list_store.get_value(iter1, i) for i in range(7)]
        data2 = [self.list_store.get_value(iter2, i) for i in range(7)]
        
        # Swap
        for i in range(7):
            self.list_store.set_value(iter1, i, data2[i])
            self.list_store.set_value(iter2, i, data1[i])
