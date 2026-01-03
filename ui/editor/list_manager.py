"""
SIMPLE List Manager - Fixed version without signal handler errors
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Pango, GLib
import uuid


class SimpleListItem:
    """Minimal list item - just what we need for display"""
    def __init__(self, title="New Item", depth=0):
        self.id = str(uuid.uuid4())[:8]  # Simple ID
        self.title = title
        self.depth = depth  # Visual indentation: 0=root, 1=child, 2=grandchild
        self.command = ""
        self.icon = ""
        self.window_state = None
        self.has_children = False  # Visual indicator only
        self.db_id = None  # Database ID if saved
    
    def __repr__(self):
        return f"SimpleListItem(id={self.id}, title='{self.title}', depth={self.depth})"


class ListManager:
    """SIMPLE list manager - ULTRA SIMPLE to prevent errors"""
    
    def __init__(self, db, menu_model):
        self.db = db
        self.model = menu_model
        
        # Callbacks
        self.on_selection_changed = None
        self.on_item_modified = None
        
        # Simple flat list of items for display
        self.display_items = []
        
        # Track selection with simple index
        self.selected_index = -1
        self.selected_id = None
        
        # ListBox
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect("row-selected", self._on_row_selected)
        
        # Initial load from model
        self._load_from_model()
        print(f"✅ ListManager initialized with {len(self.display_items)} items")
    
    def _on_row_selected(self, listbox, row):
        """Handle row selection - SIMPLE"""
        if row and hasattr(row, 'item_id'):
            self.selected_id = row.item_id
            # Find index
            for i, item in enumerate(self.display_items):
                if item.id == row.item_id:
                    self.selected_index = i
                    break
            
            print(f"📌 Row selected: index={self.selected_index}, id={row.item_id}")
            if self.on_selection_changed:
                self.on_selection_changed(row.item_id)
    
    def create_nav_panel(self):
        """Create navigation panel"""
        frame = Gtk.Frame(label="📂 Menu Items")
        frame.set_shadow_type(Gtk.ShadowType.IN)
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox.set_margin_top(5)
        vbox.set_margin_bottom(5)
        vbox.set_margin_start(5)
        vbox.set_margin_end(5)
        
        # Scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.listbox)
        vbox.pack_start(scrolled, True, True, 0)
        
        # Simple buttons
        vbox.pack_start(self._create_buttons(), False, False, 0)
        
        frame.add(vbox)
        return frame
    
    def _create_buttons(self):
        """Create SIMPLE button row"""
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        
        # Add/Delete
        add_btn = Gtk.Button(label="⊕ Add")
        add_btn.set_tooltip_text("Add item below selected")
        add_btn.connect("clicked", self.on_add)
        
        delete_btn = Gtk.Button(label="⊖ Delete")
        delete_btn.set_tooltip_text("Delete selected item")
        delete_btn.connect("clicked", self.on_delete)
        
        # Up/Down
        up_btn = Gtk.Button(label="↑")
        up_btn.set_tooltip_text("Move item up")
        up_btn.connect("clicked", self.on_up)
        
        down_btn = Gtk.Button(label="↓")
        down_btn.set_tooltip_text("Move item down")
        down_btn.connect("clicked", self.on_down)
        
        # Indent/Outdent (instead of sub-menu)
        indent_btn = Gtk.Button(label="→")
        indent_btn.set_tooltip_text("Indent (make subitem)")
        indent_btn.connect("clicked", self.on_indent)
        
        outdent_btn = Gtk.Button(label="←")
        outdent_btn.set_tooltip_text("Outdent (make parent)")
        outdent_btn.connect("clicked", self.on_outdent)
        
        hbox.pack_start(add_btn, True, True, 0)
        hbox.pack_start(delete_btn, True, True, 0)
        hbox.pack_start(up_btn, True, True, 0)
        hbox.pack_start(down_btn, True, True, 0)
        hbox.pack_start(indent_btn, True, True, 0)
        hbox.pack_start(outdent_btn, True, True, 0)
        
        return hbox
    
    def _load_from_model(self):
        """Load items from model into simple display list"""
        print("📥 Loading from model...")
        self.display_items.clear()
        self._add_items_recursive(self.model.root_items, 0)
        self._refresh_display()
        print(f"📊 Loaded {len(self.display_items)} display items")
    
    def _add_items_recursive(self, items, depth):
        """Convert hierarchical model to flat display list"""
        for item in sorted(items, key=lambda x: x.sort_order):
            if not item.is_deleted:
                # Create simple display item
                display_item = SimpleListItem(item.title, depth)
                display_item.id = item.id  # Keep original ID
                display_item.db_id = item.db_id
                display_item.command = item.command or ""
                display_item.icon = item.icon or ""
                display_item.window_state = item.window_state
                display_item.has_children = len(item.children) > 0
                
                self.display_items.append(display_item)
                
                # Add children with increased depth
                if item.children:
                    self._add_items_recursive(item.children, depth + 1)
    
    def _refresh_display(self):
        """Refresh the listbox display - ULTRA SIMPLE"""
        print(f"🔄 Refreshing display ({len(self.display_items)} items)")
        
        # Clear listbox
        children = list(self.listbox.get_children())  # Get copy
        for child in children:
            self.listbox.remove(child)
        
        # Add all items
        for item in self.display_items:
            row = self._create_row(item)
            self.listbox.add(row)
        
        # Show all
        self.listbox.show_all()
        
        # Restore selection if we have a selected ID
        if self.selected_id:
            # Try to find and select the row
            for row in self.listbox.get_children():
                if hasattr(row, 'item_id') and row.item_id == self.selected_id:
                    GLib.idle_add(lambda: self.listbox.select_row(row) or False)
                    break
    
    def _create_row(self, item):
        """Create a listbox row for an item"""
        row = Gtk.ListBoxRow()
        row.item_id = item.id
        
        # Horizontal box
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        hbox.set_margin_start(5)
        hbox.set_margin_end(5)
        hbox.set_margin_top(3)
        hbox.set_margin_bottom(3)
        
        # Indentation
        if item.depth > 0:
            indent = Gtk.Label(label="    " * item.depth)
            indent.set_xalign(0)
            hbox.pack_start(indent, False, False, 0)
        
        # Title
        title_label = Gtk.Label(label=item.title)
        title_label.set_xalign(0)
        title_label.set_ellipsize(Pango.EllipsizeMode.END)
        title_label.set_hexpand(True)
        hbox.pack_start(title_label, True, True, 0)
        
        # Folder icon if has children
        if item.has_children:
            folder = Gtk.Label(label="📁")
            folder.set_margin_start(5)
            hbox.pack_start(folder, False, False, 0)
        
        row.add(hbox)
        return row
    
    # ===== SIMPLE OPERATIONS =====
    
    def on_add(self, button):
        """Add item below selected"""
        print("➕ Adding new item...")
        
        if self.selected_index >= 0:
            # Insert after selected item
            insert_at = self.selected_index + 1
            # Copy depth from selected item
            depth = self.display_items[self.selected_index].depth
            print(f"   Inserting at index {insert_at}, depth {depth}")
        else:
            # Add at end
            insert_at = len(self.display_items)
            depth = 0
            print(f"   Inserting at end (index {insert_at})")
        
        # Create new item
        new_item = SimpleListItem("New Item", depth)
        print(f"   Created item: {new_item}")
        
        # Insert into display list
        self.display_items.insert(insert_at, new_item)
        
        # Select the new item
        self.selected_index = insert_at
        self.selected_id = new_item.id
        
        # Refresh display
        self._refresh_display()
        
        # Notify editor
        if self.on_item_modified:
            self.on_item_modified(new_item.id, 'added', True)
    
    def on_delete(self, button):
        """Delete selected item"""
        if 0 <= self.selected_index < len(self.display_items):
            item = self.display_items[self.selected_index]
            print(f"🗑️ Deleting item: {item}")
            
            # Remove from display
            del self.display_items[self.selected_index]
            
            # Adjust selection
            if self.selected_index >= len(self.display_items):
                self.selected_index = len(self.display_items) - 1
            
            # Update selected_id if possible
            if self.selected_index >= 0:
                self.selected_id = self.display_items[self.selected_index].id
            else:
                self.selected_id = None
            
            # Refresh
            self._refresh_display()
            
            # Notify editor
            if self.on_item_modified:
                self.on_item_modified(item.id, 'deleted', True)
        else:
            print("⚠️ No item to delete")
    
    def on_up(self, button):
        """Move item up - SIMPLE SWAP"""
        if self.selected_index > 0:
            item = self.display_items[self.selected_index]
            print(f"⬆️ Moving up: {item}")
            
            # Swap with item above
            self.display_items[self.selected_index], self.display_items[self.selected_index - 1] = \
                self.display_items[self.selected_index - 1], self.display_items[self.selected_index]
            
            # Move selection up
            self.selected_index -= 1
            self.selected_id = item.id  # Same item, different position
            
            # Refresh
            self._refresh_display()
            
            # Notify
            if self.on_item_modified:
                self.on_item_modified(item.id, 'moved', 'up')
        else:
            print("⚠️ Cannot move up (already at top)")
    
    def on_down(self, button):
        """Move item down - SIMPLE SWAP"""
        if self.selected_index < len(self.display_items) - 1:
            item = self.display_items[self.selected_index]
            print(f"⬇️ Moving down: {item}")
            
            # Swap with item below
            self.display_items[self.selected_index], self.display_items[self.selected_index + 1] = \
                self.display_items[self.selected_index + 1], self.display_items[self.selected_index]
            
            # Move selection down
            self.selected_index += 1
            self.selected_id = item.id  # Same item, different position
            
            # Refresh
            self._refresh_display()
            
            # Notify
            if self.on_item_modified:
                self.on_item_modified(item.id, 'moved', 'down')
        else:
            print("⚠️ Cannot move down (already at bottom)")
    
    def on_indent(self, button):
        """Indent item (make it a child)"""
        if self.selected_index > 0:
            item = self.display_items[self.selected_index]
            prev_item = self.display_items[self.selected_index - 1]
            
            print(f"→ Indenting: {item} (previous: {prev_item})")
            
            # Can only indent if previous item is at same or higher level
            if item.depth <= prev_item.depth:
                item.depth += 1
                # Mark previous item as having children (visually)
                prev_item.has_children = True
                
                print(f"   New depth: {item.depth}")
                
                # Refresh
                self._refresh_display()
                
                # Notify
                if self.on_item_modified:
                    self.on_item_modified(item.id, 'indent', item.depth)
            else:
                print(f"⚠️ Cannot indent: previous item depth {prev_item.depth} < current depth {item.depth}")
        else:
            print("⚠️ Cannot indent first item")
    
    def on_outdent(self, button):
        """Outdent item (make it a parent)"""
        if self.selected_index >= 0:
            item = self.display_items[self.selected_index]
            print(f"← Outdenting: {item}")
            
            # Can only outdent if not already at root
            if item.depth > 0:
                item.depth -= 1
                
                print(f"   New depth: {item.depth}")
                
                # Refresh
                self._refresh_display()
                
                # Notify
                if self.on_item_modified:
                    self.on_item_modified(item.id, 'outdent', item.depth)
            else:
                print("⚠️ Cannot outdent (already at root)")
        else:
            print("⚠️ No item selected to outdent")
    
    # ===== EDITOR INTEGRATION =====
    
    def update_item_title(self, item_id, new_title):
        """Update item title - SIMPLE"""
        print(f"📝 Updating title for {item_id} to '{new_title}'")
        
        for item in self.display_items:
            if item.id == item_id:
                old_title = item.title
                item.title = new_title
                self._refresh_display()
                print(f"✅ Updated: '{old_title}' → '{new_title}'")
                return True
        
        print(f"❌ Item {item_id} not found")
        return False
    
    def refresh_item(self, item_id):
        """Refresh item from model"""
        print(f"🔍 Refreshing item {item_id}")
        # Just refresh everything (simple!)
        self._load_from_model()
        return True
    
    def rebuild_list(self):
        """Rebuild from model"""
        print("🔨 Rebuilding list from model")
        self._load_from_model()
    
    def get_selected_item(self):
        """Get currently selected item"""
        if 0 <= self.selected_index < len(self.display_items):
            return self.display_items[self.selected_index]
        return None
    
    def get_item_properties(self, item_id):
        """Get properties for an item"""
        for item in self.display_items:
            if item.id == item_id:
                return {
                    'title': item.title,
                    'command': item.command,
                    'icon': item.icon,
                    'window_state': item.window_state
                }
        return None
    
    def update_item_properties(self, item_id, **kwargs):
        """Update item properties"""
        for item in self.display_items:
            if item.id == item_id:
                for key, value in kwargs.items():
                    if hasattr(item, key):
                        setattr(item, key, value)
                return True
        return False
    
    # ===== SAVE TO MODEL =====
    
    def save_to_model(self, menu_model):
        """Convert flat display list back to hierarchical model for saving"""
        print("💾 Converting display list to hierarchical model...")
        
        # Clear existing items in model
        menu_model.items.clear()
        menu_model.root_items.clear()
        
        # Track parents at each depth level
        stack = []
        
        # Sort order counter
        sort_order = 0
        
        for display_item in self.display_items:
            print(f"  Processing: '{display_item.title}' (depth: {display_item.depth})")
            
            # Find parent based on depth
            parent = None
            parent_id = None
            
            # Pop items from stack until we find the right parent depth
            while stack and stack[-1][1] >= display_item.depth:
                stack.pop()
            
            # The top of stack is now our parent (if any)
            if stack:
                parent_item, parent_depth = stack[-1]
                parent = parent_item
                parent_id = parent_item.id
                print(f"    Parent: '{parent.title}' (depth: {parent_depth})")
            
            # Create or update model item
            model_item = None
            
            # Check if item already exists in model
            if display_item.db_id:
                # Existing item - find and update it
                for existing_id, existing_item in menu_model.items.items():
                    if existing_item.db_id == display_item.db_id:
                        model_item = existing_item
                        break
            
            if not model_item:
                # New item - create it
                model_item = menu_model.add_item(display_item.title, parent_id)
                model_item.id = display_item.id  # Keep our display ID
            else:
                # Update existing item
                model_item.title = display_item.title
                model_item.parent_id = parent_id
                model_item.is_modified = True
            
            # Set properties
            model_item.command = display_item.command
            model_item.icon = display_item.icon
            model_item.window_state = display_item.window_state
            model_item.depth = display_item.depth
            model_item.sort_order = sort_order
            
            # Add to model
            menu_model.items[model_item.id] = model_item
            
            # Add to parent's children or root
            if parent:
                # Remove from any previous parent first
                if model_item.parent_id != parent_id and model_item.parent_id:
                    old_parent = menu_model.get_item(model_item.parent_id)
                    if old_parent and model_item in old_parent.children:
                        old_parent.children.remove(model_item)
                
                # Add to new parent
                if model_item not in parent.children:
                    parent.children.append(model_item)
            else:
                # Add to root
                if model_item not in menu_model.root_items:
                    menu_model.root_items.append(model_item)
            
            # Push this item onto stack if it might have children
            stack.append((model_item, display_item.depth))
            
            sort_order += 1
        
        # Clean up: ensure all children are properly sorted
        for item in menu_model.items.values():
            item.children.sort(key=lambda x: x.sort_order)
        
        # Sort root items
        menu_model.root_items.sort(key=lambda x: x.sort_order)
        
        menu_model.is_modified = True
        print(f"✅ Converted {len(self.display_items)} display items to hierarchical model")
        return True
