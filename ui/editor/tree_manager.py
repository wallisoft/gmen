"""
Tree manager - Works directly with MenuModel for immediate updates
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
from typing import Optional, List, Dict, Tuple, Set
import time


class TreeManager:
    """Manages tree view synchronized with MenuModel"""
    
    def __init__(self, db, menu_model):
        self.db = db
        self.model = menu_model
        
        # Callbacks
        self.on_selection_changed = None
        self.on_item_modified = None
        
        # Track expanded rows and selection path
        self.expanded_rows = set()
        self.selection_path = None  # Track selection as (action, target_id)
        
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
        self.add_btn.set_tooltip_text("Add item below selected item")
        self.add_btn.connect("clicked", self.on_add)
        
        self.submenu_btn = Gtk.Button(label="📁 Sub-Menu")
        self.submenu_btn.set_tooltip_text("Add subitem (will be selected)")
        self.submenu_btn.connect("clicked", self.on_submenu)
        
        self.remove_btn = Gtk.Button(label="⊖ Remove")
        self.remove_btn.set_tooltip_text("Remove selected item")
        self.remove_btn.connect("clicked", self.on_remove)
        
        self.up_btn = Gtk.Button(label="↑ Up")
        self.up_btn.set_tooltip_text("Move item up (keeps parent expanded)")
        self.up_btn.connect("clicked", self.on_up)
        
        self.down_btn = Gtk.Button(label="↓ Down")
        self.down_btn.set_tooltip_text("Move item down (keeps parent expanded)")
        self.down_btn.connect("clicked", self.on_down)
        
        hbox.pack_start(self.add_btn, True, True, 0)
        hbox.pack_start(self.submenu_btn, True, True, 0)
        hbox.pack_start(self.remove_btn, True, True, 0)
        hbox.pack_start(self.up_btn, True, True, 0)
        hbox.pack_start(self.down_btn, True, True, 0)
        
        return hbox
    
    def rebuild_tree(self, preserve_expansion: bool = True):
        """Rebuild entire tree from model while preserving expansion AND SELECTION"""
        current_time = time.time()
        if current_time - self.last_rebuild_time < 0.1:  # Debounce
            return
        self.last_rebuild_time = current_time
        
        print("🌳 Rebuilding tree from model...")
        
        # Save current selection and expansion
        selected_id = self._get_selected_item_id()
        saved_expanded = self.expanded_rows.copy()
        
        # Determine what to select after rebuild
        item_to_select = None
        
        if self.selection_path:
            # We have a specific selection path to restore
            action, target_id = self.selection_path
            print(f"   Selection path: {action} -> {target_id}")
            
            if action == 'add_child':
                # Find the newly added child
                parent_item = self.model.get_item(target_id)
                if parent_item and parent_item.children:
                    # Select the LAST child (newest)
                    item_to_select = parent_item.children[-1].id
                    print(f"   Will select new child: {item_to_select}")
            
            elif action == 'add_after':
                # Find item added after target
                target_item = self.model.get_item(target_id)
                if target_item:
                    # Find next sibling
                    siblings = self._get_siblings(target_item.parent_id)
                    for i, sibling in enumerate(siblings):
                        if sibling.id == target_id and i + 1 < len(siblings):
                            item_to_select = siblings[i + 1].id
                            print(f"   Will select next sibling: {item_to_select}")
                            break
            
            elif action == 'keep_selection':
                # Keep selection on same item
                item_to_select = target_id
                print(f"   Will keep selection on: {target_id}")
            
            self.selection_path = None  # Clear after use
        
        # If no specific path, try to restore original selection
        if not item_to_select and selected_id:
            item_to_select = selected_id
            print(f"   Will restore previous selection: {selected_id}")
        
        self.list_store.clear()
        
        # Add root items recursively
        for item in self.model.root_items:
            if not item.is_deleted:
                self._add_item_to_tree(None, item)
        
        # Restore expansion
        if preserve_expansion:
            self._restore_expansion(saved_expanded)
        
        # Restore selection if possible - with delay
        if item_to_select:
            # Check if item still exists
            item = self.model.get_item(item_to_select)
            if item and not item.is_deleted:
                GLib.timeout_add(150, self._delayed_select_item, item_to_select)
                print(f"   Will select: {item_to_select} ('{item.title}')")
            else:
                print(f"⚠️  Item to select no longer exists: {item_to_select}")
        
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
                print(f"   Re-expanded: {item_id}")
    
    def refresh_item(self, item_id: str, update_children: bool = False) -> bool:
        """Update a single item in tree - handles sub-items properly"""
        print(f"🔍 refresh_item looking for '{item_id}'")
        
        # Try to find the item by its current ID
        tree_iter = self._find_iter_by_id(item_id)
        
        if not tree_iter:
            # Item might have been saved and got a DB ID
            # Search through ALL items in model for match
            matching_item = None
            for model_item in self.model.items.values():
                # Check if this is the item we're looking for
                if (model_item.id == item_id or 
                    (model_item.db_id and str(model_item.db_id) == item_id)):
                    matching_item = model_item
                    break
            
            if matching_item:
                # Found it! Try to find by its CURRENT ID
                tree_iter = self._find_iter_by_id(matching_item.id)
                if not tree_iter:
                    print(f"❌ Item found in model but not in tree: {matching_item.id}")
                    return False
                # Update item_id to the current ID
                item_id = matching_item.id
            else:
                print(f"❌ Item {item_id} not found in model or tree")
                return False
        
        # Get item from model
        item = self.model.get_item(item_id)
        if not item or item.is_deleted:
            # Item was deleted, remove from tree
            self.list_store.remove(tree_iter)
            print(f"✅ Removed deleted item from tree")
            return True
        
        # Update ALL values
        old_title = self.list_store.get_value(tree_iter, 0)
        new_title = item.title
        
        # Only update if changed
        if old_title != new_title or self.list_store.get_value(tree_iter, 3) != item.is_new:
            self.list_store.set(tree_iter, 
                               (0, 1, 2, 3),
                               (new_title, item.id, len(item.children) > 0, item.is_new))
            
            # Force immediate redraw of this row
            path = self.list_store.get_path(tree_iter)
            self.treeview.queue_draw_area(path, 0, -1, -1)
            
            print(f"✅ Updated item '{old_title}' → '{new_title}'")
        
        # If this is a parent and needs children updated
        if update_children and len(item.children) > 0:
            # Check if this row is currently expanded
            path = self.list_store.get_path(tree_iter)
            if self.treeview.row_expanded(path):
                # Rebuild the subtree
                self._rebuild_subtree(tree_iter, item)
                # Re-expand
                self.treeview.expand_row(path, False)
        
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
            old_title = self.list_store.get_value(tree_iter, 0)
            if old_title != new_title:
                self.list_store.set_value(tree_iter, 0, new_title)
                # Force immediate redraw
                path = self.list_store.get_path(tree_iter)
                self.treeview.queue_draw_area(path, 0, -1, -1)
                print(f"✅ Tree updated immediately: '{old_title}' → '{new_title}'")
        
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
        """Add new item BELOW selected item - NEW ITEM IS SELECTED"""
        selected_id = self._get_selected_item_id()
        
        parent_id = None
        insert_after_id = None
        
        if selected_id:
            selected_item = self.model.get_item(selected_id)
            if selected_item:
                # Insert at SAME LEVEL as selected item
                parent_id = selected_item.parent_id
                insert_after_id = selected_id  # Insert AFTER selected item
                # Track that we're adding after this item
                self.selection_path = ('add_after', selected_id)
        
        print(f"➕ Adding item at level {parent_id}, after {insert_after_id}")
        
        # Add to model with position context
        new_item = self.model.add_item("New Item", parent_id, insert_after_id)
        print(f"   Created item: {new_item.id} ('{new_item.title}')")
        
        # Rebuild preserving expansion - selection will be restored by rebuild_tree
        self.rebuild_tree(preserve_expansion=True)
        
        # Notify editor
        if self.on_item_modified:
            self.on_item_modified(new_item.id, 'title', 'New Item')
    
    def on_submenu(self, button):
        """Add subitem under selected item - NEW ITEM IS SELECTED AND PARENT EXPANDED"""
        selected_id = self._get_selected_item_id()
        if not selected_id:
            return
        
        # Save selection path BEFORE adding
        self.selection_path = ('add_child', selected_id)
        
        # Save that we want this parent expanded
        self.expanded_rows.add(selected_id)
        
        # Add subitem (will be selected after)
        new_item = self.model.add_item("Sub-Menu", selected_id)
        print(f"📁 Created sub-item '{new_item.title}' under '{selected_id}'")
        
        # Rebuild preserving expansion - this will trigger selection restoration
        self.rebuild_tree(preserve_expansion=True)
        
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
            # Clear selection path
            self.selection_path = None
            
            # Rebuild the parent subtree if exists
            if parent_id:
                self._refresh_parent_subtree(parent_id)
            else:
                # Rebuild root
                self.rebuild_tree(preserve_expansion=True)
            
            # Clear selection
            self.selection.unselect_all()
            
            # Notify editor
            if self.on_item_modified:
                self.on_item_modified(selected_id, 'deleted', True)
    
    def on_up(self, button):
        """Move item up - KEEPS SELECTION ON MOVED ITEM"""
        selected_id = self._get_selected_item_id()
        if not selected_id:
            return
        
        # Track that we want to keep selection on this item
        self.selection_path = ('keep_selection', selected_id)
        
        # Get item and parent
        item = self.model.get_item(selected_id)
        if not item:
            return
        
        # Save expansion state
        save_expanded = self.expanded_rows.copy()
        
        # Move in model
        if self.model.move_item(selected_id, 'up'):
            # Rebuild affected subtree
            if item.parent_id:
                self._refresh_parent_subtree(item.parent_id, save_expanded)
            else:
                self.rebuild_tree(preserve_expansion=True)
        
        # Notify editor
        if self.on_item_modified:
            self.on_item_modified(selected_id, 'moved', 'up')
    
    def on_down(self, button):
        """Move item down - KEEPS SELECTION ON MOVED ITEM"""
        selected_id = self._get_selected_item_id()
        if not selected_id:
            return
        
        # Track that we want to keep selection on this item
        self.selection_path = ('keep_selection', selected_id)
        
        # Get item and parent
        item = self.model.get_item(selected_id)
        if not item:
            return
        
        # Save expansion state
        save_expanded = self.expanded_rows.copy()
        
        # Move in model
        if self.model.move_item(selected_id, 'down'):
            # Rebuild affected subtree
            if item.parent_id:
                self._refresh_parent_subtree(item.parent_id, save_expanded)
            else:
                self.rebuild_tree(preserve_expansion=True)
        
        # Notify editor
        if self.on_item_modified:
            self.on_item_modified(selected_id, 'moved', 'down')
    
    def _refresh_parent_subtree(self, parent_id: str, save_expanded: set = None):
        """Refresh just a parent's subtree - PRESERVES CHILD SELECTION"""
        parent_iter = self._find_iter_by_id(parent_id)
        if not parent_iter:
            return
        
        parent_item = self.model.get_item(parent_id)
        if not parent_item:
            return
        
        # Get current selection before refresh
        selected_id = self._get_selected_item_id()
        
        # Check if parent is currently expanded
        path = self.list_store.get_path(parent_iter)
        was_expanded = self.treeview.row_expanded(path)
        
        # Rebuild subtree
        self._rebuild_subtree(parent_iter, parent_item)
        
        # Re-expand if it was expanded
        if was_expanded:
            self.treeview.expand_row(path, False)
            
            # Also restore child expansions
            if save_expanded:
                for item_id in save_expanded:
                    if item_id != parent_id:  # Don't re-expand parent
                        child_iter = self._find_iter_by_id(item_id)
                        if child_iter:
                            child_path = self.list_store.get_path(child_iter)
                            self.treeview.expand_row(child_path, False)
        
        # Restore selection if it was a child of this parent
        if selected_id:
            item = self.model.get_item(selected_id)
            if item and item.parent_id == parent_id:
                # This was a child of the parent we just refreshed
                GLib.idle_add(self._delayed_select_item, selected_id)
    
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
    
    def _get_siblings(self, parent_id: Optional[str] = None) -> List:
        """Get all items at same level"""
        if parent_id:
            parent = self.model.get_item(parent_id)
            return parent.children if parent else []
        return self.model.root_items
    
    def _get_item_hierarchy(self, item_id: str) -> Tuple[str, int]:
        """Get item's hierarchy info: (parent_id, position_in_parent)"""
        item = self.model.get_item(item_id)
        if not item:
            return (None, -1)
        
        if item.parent_id:
            parent = self.model.get_item(item.parent_id)
            if parent:
                # Find position in parent's children
                for i, child in enumerate(parent.children):
                    if child.id == item_id:
                        return (item.parent_id, i)
        
        # Root item
        for i, root in enumerate(self.model.root_items):
            if root.id == item_id:
                return (None, i)
        
        return (None, -1)
