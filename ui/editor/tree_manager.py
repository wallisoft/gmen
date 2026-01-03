"""
Tree manager - Works directly with MenuModel for immediate updates
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
from typing import Optional, List, Dict, Tuple
import time


class TreeManager:
    """Manages tree view synchronized with MenuModel"""
    
    def __init__(self, db, menu_model):
        self.db = db
        self.model = menu_model
        
        # Callbacks
        self.on_selection_changed = None
        self.on_item_modified = None
        
        # Track expanded rows
        self.expanded_rows = set()
        
        # Tree store: title, item_id, has_children, is_new
        self.list_store = Gtk.TreeStore(str, str, bool, bool)
        
        # Tree view
        self.treeview = Gtk.TreeView(model=self.list_store)
        self.treeview.connect("row-expanded", self._on_row_expanded)
        self.treeview.connect("row-collapsed", self._on_row_collapsed)
        
        text_renderer = Gtk.CellRendererText()
        text_column = Gtk.TreeViewColumn("Menu Items", text_renderer, text=0)
        text_column.set_expand(True)
        self.treeview.append_column(text_column)
        
        # Selection
        self.selection = self.treeview.get_selection()
        self.selection.set_mode(Gtk.SelectionMode.SINGLE)
        self.selection.connect("changed", self._on_selection_changed)
        
        # Track last rebuild time to avoid rapid refreshes
        self.last_rebuild_time = 0
    
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
    
    def rebuild_tree(self, preserve_expansion: bool = True):
        """Rebuild entire tree from model while preserving expansion"""
        current_time = time.time()
        if current_time - self.last_rebuild_time < 0.1:  # Debounce
            return
        self.last_rebuild_time = current_time
        
        print("🌳 Rebuilding tree from model...")
        
        # Save current selection and expansion
        selected_id = self._get_selected_item_id()
        saved_expanded = self.expanded_rows.copy()
        
        self.list_store.clear()
        
        # Add root items recursively
        for item in self.model.root_items:
            if not item.is_deleted:
                self._add_item_to_tree(None, item)
        
        # Restore expansion
        if preserve_expansion:
            self._restore_expansion(saved_expanded)
        
        # Restore selection if possible
        if selected_id:
            GLib.timeout_add(50, self._delayed_select_item, selected_id)
        
        print(f"✅ Tree rebuilt with {len(self.model.get_all_items())} items")
    
    def _add_item_to_tree(self, parent_iter, item):
        """Add item and its children to tree"""
        has_children = len(item.children) > 0
        
        iter = self.list_store.append(
            parent_iter,
            [item.title, item.id, has_children, item.is_new]
        )
        
        # Add children (sorted by sort_order)
        for child in sorted(item.children, key=lambda x: x.sort_order):
            if not child.is_deleted:
                self._add_item_to_tree(iter, child)
    
    def _restore_expansion(self, expanded_ids: set):
        """Restore expanded rows after rebuild"""
        for item_id in expanded_ids:
            tree_iter = self._find_iter_by_id(item_id)
            if tree_iter:
                path = self.list_store.get_path(tree_iter)
                self.treeview.expand_row(path, False)
    
    def refresh_item(self, item_id: str, update_children: bool = False) -> bool:
        """Update a single item in tree WITHOUT affecting expansion"""
        print(f"🔍 refresh_item looking for {item_id}")
        
        tree_iter = self._find_iter_by_id(item_id)
        if not tree_iter:
            print(f"❌ Could not find item {item_id} in tree")
            return False
        
        item = self.model.get_item(item_id)
        if not item or item.is_deleted:
            # Item was deleted, remove from tree
            self.list_store.remove(tree_iter)
            print(f"✅ Removed deleted item {item_id} from tree")
            return True
        
        # Check if this row is currently expanded
        path = self.list_store.get_path(tree_iter)
        was_expanded = self.treeview.row_expanded(path)
        
        # Update values
        old_title = self.list_store.get_value(tree_iter, 0)
        self.list_store.set_value(tree_iter, 0, item.title)
        self.list_store.set_value(tree_iter, 2, len(item.children) > 0)
        self.list_store.set_value(tree_iter, 3, item.is_new)
        
        # If updating children is needed AND item was expanded
        if update_children and was_expanded:
            self._rebuild_subtree(tree_iter, item)
            # Re-expand after rebuild
            self.treeview.expand_row(path, False)
        
        # Force redraw only this row
        rect = self.treeview.get_cell_area(path, self.treeview.get_column(0))
        if rect:
            self.treeview.queue_draw_area(rect.x, rect.y, rect.width, rect.height)
        
        print(f"✅ Refreshed item {item_id}: '{old_title}' → '{item.title}'")
        return True
    
    def _rebuild_subtree(self, parent_iter, parent_item):
        """Rebuild a specific subtree"""
        # Remove all current children
        child = self.list_store.iter_children(parent_iter)
        while child:
            next_child = self.list_store.iter_next(child)
            self.list_store.remove(child)
            child = next_child
        
        # Add updated children
        for child_item in sorted(parent_item.children, key=lambda x: x.sort_order):
            if not child_item.is_deleted:
                self._add_item_to_tree(parent_iter, child_item)
    
    def update_item_title(self, item_id: str, new_title: str) -> bool:
        """Update item title in tree IMMEDIATELY"""
        print(f"🌳 TreeManager.update_item_title({item_id}, '{new_title}')")
        
        # First, update the tree view IMMEDIATELY
        tree_iter = self._find_iter_by_id(item_id)
        if tree_iter:
            self.list_store.set_value(tree_iter, 0, new_title)
            # Force immediate redraw
            path = self.list_store.get_path(tree_iter)
            rect = self.treeview.get_cell_area(path, self.treeview.get_column(0))
            if rect:
                self.treeview.queue_draw_area(rect.x, rect.y, rect.width, rect.height)
            print(f"✅ Tree updated immediately for {item_id}")
        
        # Then update model
        if self.model.update_item(item_id, title=new_title):
            # Ensure tree is synced
            success = self.refresh_item(item_id)
            
            # Notify editor
            if success and self.on_item_modified:
                self.on_item_modified(item_id, 'title', new_title)
            
            return success
        
        return False
    
    def _on_row_expanded(self, treeview, treeiter, treepath):
        """Track expanded rows"""
        item_id = self.list_store.get_value(treeiter, 1)
        self.expanded_rows.add(item_id)
    
    def _on_row_collapsed(self, treeview, treeiter, treepath):
        """Track collapsed rows"""
        item_id = self.list_store.get_value(treeiter, 1)
        if item_id in self.expanded_rows:
            self.expanded_rows.remove(item_id)
    
    # ===== Event Handlers =====
    
    def _on_selection_changed(self, selection):
        """Handle tree selection change"""
        model, treeiter = selection.get_selected()
        if treeiter and self.on_selection_changed:
            item_id = model[treeiter][1]
            self.on_selection_changed(item_id)
    
    def on_add(self, button):
        """Add new item at current level"""
        selected_id = self._get_selected_item_id()
        parent_id = None
        
        if selected_id:
            item = self.model.get_item(selected_id)
            if item:
                parent_id = item.parent_id
        
        # Save expanded state before adding
        save_expanded = self.expanded_rows.copy()
        
        # Add to model
        new_item = self.model.add_item("New Item", parent_id)
        
        # Rebuild tree but preserve expansion
        self.rebuild_tree(preserve_expansion=True)
        
        # Select the new item
        self._select_item(new_item.id, scroll=True)
        
        # Notify editor
        if self.on_item_modified:
            self.on_item_modified(new_item.id, 'title', 'New Item')
    
    def on_submenu(self, button):
        """Add subitem under selected item"""
        selected_id = self._get_selected_item_id()
        if not selected_id:
            return
        
        # Save that we want this parent expanded
        self.expanded_rows.add(selected_id)
        
        # Add to model
        new_item = self.model.add_item("Sub-Menu", selected_id)
        
        # Rebuild tree preserving expansion
        self.rebuild_tree(preserve_expansion=True)
        
        # Ensure parent is expanded
        parent_iter = self._find_iter_by_id(selected_id)
        if parent_iter:
            path = self.list_store.get_path(parent_iter)
            self.treeview.expand_row(path, False)
        
        # Select new item and scroll to it
        self._select_item(new_item.id, scroll=True)
        
        # Notify editor
        if self.on_item_modified:
            self.on_item_modified(new_item.id, 'title', 'Sub-Menu')
    
    def on_remove(self, button):
        """Remove selected item"""
        selected_id = self._get_selected_item_id()
        if not selected_id:
            return
        
        # Get parent before deletion
        item = self.model.get_item(selected_id)
        parent_id = item.parent_id if item else None
        
        # Delete from model
        if self.model.delete_item(selected_id):
            # Rebuild the parent subtree if exists
            if parent_id:
                parent_iter = self._find_iter_by_id(parent_id)
                if parent_iter:
                    parent_item = self.model.get_item(parent_id)
                    self._rebuild_subtree(parent_iter, parent_item)
            else:
                # Rebuild root
                self.rebuild_tree(preserve_expansion=True)
            
            # Clear selection
            self.selection.unselect_all()
            
            # Notify editor
            if self.on_item_modified:
                self.on_item_modified(selected_id, 'deleted', True)
    
    def on_up(self, button):
        """Move item up without full rebuild"""
        selected_id = self._get_selected_item_id()
        if not selected_id:
            return
        
        # Get item and its parent before moving
        item = self.model.get_item(selected_id)
        if not item:
            return
        
        parent_id = item.parent_id
        save_expanded = self.expanded_rows.copy()  # Save current expansion
        
        if self.model.move_item(selected_id, 'up'):
            if parent_id:
                # Just rebuild the parent's subtree
                self._rebuild_parent_subtree(parent_id, save_expanded)
            else:
                # For root items, just rebuild the tree but preserve expansion
                self.rebuild_tree(preserve_expansion=True)
            
            # Keep selection and ensure visible
            GLib.idle_add(self._delayed_select_and_scroll, selected_id)
        
        # Notify editor
        if self.on_item_modified:
            self.on_item_modified(selected_id, 'moved', 'up')
    
    def on_down(self, button):
        """Move item down without full rebuild"""
        selected_id = self._get_selected_item_id()
        if not selected_id:
            return
        
        # Get item and its parent before moving
        item = self.model.get_item(selected_id)
        if not item:
            return
        
        parent_id = item.parent_id
        save_expanded = self.expanded_rows.copy()  # Save current expansion
        
        if self.model.move_item(selected_id, 'down'):
            if parent_id:
                # Just rebuild the parent's subtree
                self._rebuild_parent_subtree(parent_id, save_expanded)
            else:
                # For root items, just rebuild the tree but preserve expansion
                self.rebuild_tree(preserve_expansion=True)
            
            # Keep selection and ensure visible
            GLib.idle_add(self._delayed_select_and_scroll, selected_id)
        
        # Notify editor
        if self.on_item_modified:
            self.on_item_modified(selected_id, 'moved', 'down')
    
    def _rebuild_parent_subtree(self, parent_id: str, save_expanded: set):
        """Rebuild only a parent's subtree, preserving expansion"""
        parent_iter = self._find_iter_by_id(parent_id)
        if not parent_iter:
            return
        
        parent_item = self.model.get_item(parent_id)
        if not parent_item:
            return
        
        # Remove all children
        child = self.list_store.iter_children(parent_iter)
        while child:
            next_child = self.list_store.iter_next(child)
            self.list_store.remove(child)
            child = next_child
        
        # Add updated children (sorted)
        for child_item in sorted(parent_item.children, key=lambda x: x.sort_order):
            if not child_item.is_deleted:
                self._add_item_to_tree(parent_iter, child_item)
        
        # Restore expansion for this parent's children
        for item_id in save_expanded:
            # Only restore if it's a child of this parent
            item = self.model.get_item(item_id)
            if item and item.parent_id == parent_id:
                tree_iter = self._find_iter_by_id(item_id)
                if tree_iter:
                    path = self.list_store.get_path(tree_iter)
                    self.treeview.expand_row(path, False)
    
    # ===== Helper Methods =====
    
    def _get_selected_item_id(self) -> Optional[str]:
        """Get ID of currently selected item"""
        model, treeiter = self.selection.get_selected()
        if treeiter:
            return model[treeiter][1]
        return None
    
    def _find_iter_by_id(self, item_id: str, parent_iter=None):
        """Find tree iter by item ID"""
        it = self.list_store.iter_children(parent_iter) if parent_iter else self.list_store.get_iter_first()
        
        while it:
            current_id = self.list_store.get_value(it, 1)
            if current_id == item_id:
                return it
            
            # Check children
            child_iter = self.list_store.iter_children(it)
            if child_iter:
                result = self._find_iter_by_id(item_id, child_iter)
                if result:
                    return result
            
            it = self.list_store.iter_next(it)
        
        return None
    
    def _select_item(self, item_id: str, scroll: bool = True):
        """Select item in tree"""
        tree_iter = self._find_iter_by_id(item_id)
        if tree_iter:
            self.selection.select_iter(tree_iter)
            if scroll:
                path = self.list_store.get_path(tree_iter)
                self.treeview.scroll_to_cell(path, None, False, 0, 0)
                # Ensure visible
                self.treeview.set_cursor(path)
    
    def _delayed_select_item(self, item_id: str):
        """Select item after a short delay (for after rebuild)"""
        self._select_item(item_id, scroll=True)
        return False  # Don't repeat
    
    def _delayed_select_and_scroll(self, item_id: str):
        """Select and scroll to item after a delay"""
        self._select_item(item_id, scroll=True)
        return False  # Don't repeat
