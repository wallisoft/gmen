#!/usr/bin/env python3
"""
GMen Editor v4.0 - UI-First with Batch Saves
Smooth editing experience with immediate visual feedback
"""

import gi
import subprocess
import sys
from pathlib import Path

# Add our modules to path
sys.path.insert(0, str(Path(__file__).parent))

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk

from storage.database import Database
from utils.config import ConfigManager
from core.menu.builder import MenuBuilder, MenuItem


class GMenEditor:
    def __init__(self):
        # Initialize systems
        config_dir = Path.home() / ".config" / "gmen"
        self.db = Database(config_dir)
        self.config = ConfigManager(config_dir)
        
        self.current_menu_id = None
        self.selected_item_id = None
        self.unsaved_changes = False
        
        # Track changes for batch save
        self.dirty_items = set()  # IDs of modified items
        self.new_items = []       # New items to insert (dicts)
        self.deleted_items = set()  # IDs of deleted items
        
        # Load or create default menu
        default_menu = self.db.fetch_one("""
            SELECT id, name FROM menus WHERE is_default = 1 LIMIT 1
        """)
        
        if default_menu:
            self.current_menu_id = default_menu['id']
            self.current_menu_name = default_menu['name']
        else:
            # Create default menu
            self.db.execute("""
                INSERT INTO menus (name, is_default) 
                VALUES (?, 1)
            """, ("Default Menu",))
            result = self.db.fetch_one("SELECT last_insert_rowid() AS id")
            self.current_menu_id = result['id']
            self.current_menu_name = "Default Menu"
        
        # Create main window
        self.window = Gtk.Window(title=f"🎯 GMen Editor - {self.current_menu_name}")
        self.window.set_default_size(1000, 600)
        self.window.connect("destroy", self.on_window_close)
        
        # Build UI
        main_box = self.create_layout()
        self.window.add(main_box)
        
        # Load menu items
        self.load_menu_to_ui()
        
        self.window.show_all()
    
    def create_layout(self):
        """Create the main UI layout"""
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox.set_margin_top(5)
        vbox.set_margin_bottom(5)
        vbox.set_margin_start(5)
        vbox.set_margin_end(5)
        
        # 1. Top bar - Menu controls
        vbox.pack_start(self.create_top_bar(), False, False, 0)
        
        # 2. Main content area
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox.set_margin_top(10)
        
        # Left - Navigation panel
        hbox.pack_start(self.create_nav_panel(), True, True, 0)
        
        # Right - Properties panel
        hbox.pack_start(self.create_props_panel(), False, False, 0)
        
        vbox.pack_start(hbox, True, True, 0)
        
        # 3. Bottom toolbar
        vbox.pack_start(self.create_toolbar(), False, False, 0)
        
        return vbox
    
    def create_top_bar(self):
        """Create top bar with menu controls"""
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        # Menu name
        name_label = Gtk.Label(label="Menu Name:")
        self.menu_name_entry = Gtk.Entry()
        self.menu_name_entry.set_text(self.current_menu_name)
        self.menu_name_entry.set_width_chars(30)
        self.menu_name_entry.connect("changed", self.on_menu_name_changed)
        
        # Set as default checkbox
        self.default_check = Gtk.CheckButton.new_with_label("Default menu")
        self.default_check.set_active(True)
        self.default_check.connect("toggled", self.on_default_toggled)
        
        # Save button
        self.save_btn = Gtk.Button(label="💾 Save")
        self.save_btn.connect("clicked", self.on_save)
        
        # Unsaved changes indicator
        self.unsaved_label = Gtk.Label()
        self.unsaved_label.set_markup("<span foreground='orange'>●</span>")
        self.unsaved_label.set_no_show_all(True)
        self.unsaved_label.hide()
        
        hbox.pack_start(name_label, False, False, 0)
        hbox.pack_start(self.menu_name_entry, True, True, 0)
        hbox.pack_start(self.default_check, False, False, 0)
        hbox.pack_start(self.save_btn, False, False, 0)
        hbox.pack_start(self.unsaved_label, False, False, 5)
        
        return hbox
    
    def create_nav_panel(self):
        """Create navigation panel (left side)"""
        frame = Gtk.Frame(label="📂 Menu Items")
        frame.set_shadow_type(Gtk.ShadowType.IN)
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox.set_margin_top(5)
        vbox.set_margin_bottom(5)
        vbox.set_margin_start(5)
        vbox.set_margin_end(5)
        
        # Scrolled window for item list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        # TreeView for hierarchical display
        self.list_store = Gtk.TreeStore(str, int, int, int, bool, int, bool)
        self.treeview = Gtk.TreeView(model=self.list_store)
        
        # Column 1: Item text
        text_renderer = Gtk.CellRendererText()
        text_column = Gtk.TreeViewColumn("Items", text_renderer, text=0)
        text_column.set_expand(True)
        self.treeview.append_column(text_column)
        
        # Selection
        self.selection = self.treeview.get_selection()
        self.selection.connect("changed", self.on_selection_changed)
        
        scrolled.add(self.treeview)
        vbox.pack_start(scrolled, True, True, 0)
        
        # Navigation buttons
        self.btn_box = self.create_nav_buttons()
        vbox.pack_start(self.btn_box, False, False, 0)
        
        frame.add(vbox)
        return frame
    
    def create_nav_buttons(self):
        """Create navigation buttons"""
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        
        self.add_btn = Gtk.Button(label="⊕ Add")
        self.add_btn.set_tooltip_text("Add item at same level")
        self.add_btn.connect("clicked", self.on_add)
        
        self.submenu_btn = Gtk.Button(label="📁 Sub-Menu")
        self.submenu_btn.set_tooltip_text("Add subitem (indented)")
        self.submenu_btn.connect("clicked", self.on_submenu)
        
        self.remove_btn = Gtk.Button(label="⊖ Remove")
        self.remove_btn.set_tooltip_text("Remove selected item")
        self.remove_btn.connect("clicked", self.on_remove)
        
        self.up_btn = Gtk.Button(label="↑ Up")
        self.up_btn.set_tooltip_text("Move item up in order")
        self.up_btn.connect("clicked", self.on_up)
        
        self.down_btn = Gtk.Button(label="↓ Down")
        self.down_btn.set_tooltip_text("Move item down in order")
        self.down_btn.connect("clicked", self.on_down)
        
        hbox.pack_start(self.add_btn, True, True, 0)
        hbox.pack_start(self.submenu_btn, True, True, 0)
        hbox.pack_start(self.remove_btn, True, True, 0)
        hbox.pack_start(self.up_btn, True, True, 0)
        hbox.pack_start(self.down_btn, True, True, 0)
        
        return hbox
    
    def create_props_panel(self):
        """Create properties panel (right side)"""
        frame = Gtk.Frame(label="✏️ Properties")
        frame.set_shadow_type(Gtk.ShadowType.IN)
        frame.set_size_request(350, -1)
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        
        # Title
        vbox.pack_start(Gtk.Label(label="Title:"), False, False, 0)
        self.title_entry = Gtk.Entry()
        self.title_entry.connect("changed", self.on_title_changed)
        vbox.pack_start(self.title_entry, False, False, 0)
        
        # Command/Script Selection
        vbox.pack_start(Gtk.Label(label="Type:"), False, False, 0)
        
        type_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        self.cmd_radio = Gtk.RadioButton.new_with_label(None, "Command")
        self.cmd_radio.connect("toggled", self.on_type_changed)
        type_box.pack_start(self.cmd_radio, False, False, 0)
        
        self.script_radio = Gtk.RadioButton.new_with_label_from_widget(self.cmd_radio, "Script")
        self.script_radio.connect("toggled", self.on_type_changed)
        type_box.pack_start(self.script_radio, False, False, 0)
        
        vbox.pack_start(type_box, False, False, 0)
        
        # Command Entry
        self.cmd_label = Gtk.Label(label="Command:")
        vbox.pack_start(self.cmd_label, False, False, 0)
        self.cmd_entry = Gtk.Entry()
        self.cmd_entry.connect("changed", self.on_cmd_changed)
        vbox.pack_start(self.cmd_entry, False, False, 0)
        
        # Script Selection
        self.script_label = Gtk.Label(label="Script:")
        vbox.pack_start(self.script_label, False, False, 0)
        
        self.script_combo = Gtk.ComboBoxText()
        self.script_combo.append_text("-- Select Script --")
        self.script_combo.set_active(0)
        self.script_combo.connect("changed", self.on_script_changed)
        vbox.pack_start(self.script_combo, False, False, 0)
        
        # Icon
        vbox.pack_start(Gtk.Label(label="Icon (optional):"), False, False, 0)
        self.icon_entry = Gtk.Entry()
        self.icon_entry.set_placeholder_text("terminal, firefox, etc.")
        self.icon_entry.connect("changed", self.on_icon_changed)
        vbox.pack_start(self.icon_entry, False, False, 0)
        
        # Window State Controls
        window_frame = Gtk.Frame(label="🪟 Window State")
        window_frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        
        window_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        window_vbox.set_margin_start(10)
        window_vbox.set_margin_end(10)
        window_vbox.set_margin_top(10)
        window_vbox.set_margin_bottom(10)
        
        # Enable checkbox
        self.window_enable_check = Gtk.CheckButton.new_with_label("Remember position/size")
        self.window_enable_check.connect("toggled", self.on_window_enable_toggled)
        window_vbox.pack_start(self.window_enable_check, False, False, 0)
        
        # Geometry grid
        window_grid = Gtk.Grid()
        window_grid.set_column_spacing(10)
        window_grid.set_row_spacing(5)
        
        # Create entries
        self.x_entry = Gtk.Entry()
        self.x_entry.set_placeholder_text("100")
        self.x_entry.set_width_chars(8)
        
        self.y_entry = Gtk.Entry()
        self.y_entry.set_placeholder_text("200")
        self.y_entry.set_width_chars(8)
        
        self.width_entry = Gtk.Entry()
        self.width_entry.set_placeholder_text("800")
        self.width_entry.set_width_chars(8)
        
        self.height_entry = Gtk.Entry()
        self.height_entry.set_placeholder_text("600")
        self.height_entry.set_width_chars(8)
        
        self.monitor_entry = Gtk.Entry()
        self.monitor_entry.set_placeholder_text("0")
        self.monitor_entry.set_width_chars(8)
        
        # Connect change events
        entries = [self.x_entry, self.y_entry, self.width_entry, 
                  self.height_entry, self.monitor_entry]
        for entry in entries:
            entry.connect("changed", self.on_window_state_changed)
        
        # Layout grid
        window_grid.attach(Gtk.Label(label="X:"), 0, 0, 1, 1)
        window_grid.attach(self.x_entry, 1, 0, 1, 1)
        window_grid.attach(Gtk.Label(label="Y:"), 2, 0, 1, 1)
        window_grid.attach(self.y_entry, 3, 0, 1, 1)
        
        window_grid.attach(Gtk.Label(label="Width:"), 0, 1, 1, 1)
        window_grid.attach(self.width_entry, 1, 1, 1, 1)
        window_grid.attach(Gtk.Label(label="Height:"), 2, 1, 1, 1)
        window_grid.attach(self.height_entry, 3, 1, 1, 1)
        
        window_grid.attach(Gtk.Label(label="Monitor:"), 0, 2, 1, 1)
        window_grid.attach(self.monitor_entry, 1, 2, 1, 1)
        
        window_vbox.pack_start(window_grid, False, False, 5)
        window_frame.add(window_vbox)
        vbox.pack_start(window_frame, False, False, 10)
        
        # Initially disable window state entries
        self.on_window_enable_toggled(self.window_enable_check)
        
        # Initially hide script controls
        self.script_label.hide()
        self.script_combo.hide()
        
        # Separator
        vbox.pack_start(Gtk.Separator(), False, False, 10)
        
        # Info label
        self.info_label = Gtk.Label()
        self.info_label.set_line_wrap(True)
        vbox.pack_start(self.info_label, True, True, 0)
        
        frame.add(vbox)
        return frame
    
    def create_toolbar(self):
        """Create bottom toolbar"""
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        buttons = [
            ("🔄 Reload", self.on_reload),
            ("💾 Backup DB", self.on_backup),
            ("📜 Script Editor", self.open_script_editor),
            ("▶️ Test", self.on_test),
            ("🚪 Quit", self.on_quit),
        ]
        
        for label, callback in buttons:
            btn = Gtk.Button(label=label)
            btn.connect("clicked", callback)
            hbox.pack_start(btn, False, False, 0)
        
        return hbox
    
    def load_menu_to_ui(self):
        """Load menu items from database and display in tree"""
        self.list_store.clear()
        self.selected_item_id = None
        self.dirty_items.clear()
        self.new_items.clear()
        self.deleted_items.clear()
        
        # Build menu hierarchy from database
        builder = MenuBuilder(self.db)
        menu_root = builder.build_menu(self.current_menu_id)
        
        # Check if menu is empty
        if not menu_root or len(menu_root.children) == 0:
            self.info_label.set_text("Menu is empty. Click 'Add' to create first item.")
            print("📭 Menu is empty - ready for first item")
            self.update_button_states()
            self.update_unsaved_indicator()
            return
        
        # Helper to add items recursively to TreeStore
        def add_children(parent_iter, menu_item):
            for child in menu_item.children:
                has_children = len(child.children) > 0
                
                # Get sort order from database
                sort_info = self.db.fetch_one(
                    "SELECT sort_order, parent_id FROM menu_items WHERE id = ?",
                    (child.id,)
                )
                sort_order = sort_info['sort_order'] if sort_info else 0
                parent_id = sort_info['parent_id'] if sort_info else None
                
                # Add to tree
                child_iter = self.list_store.append(
                    parent_iter,
                    [child.title, child.depth, child.id, parent_id, has_children, sort_order, False]
                )
                
                # Add grandchildren recursively
                if has_children:
                    add_children(child_iter, child)
        
        # Add top-level items
        add_children(None, menu_root)
        
        print(f"📋 Loaded menu into UI")
        self.update_button_states()
        self.update_unsaved_indicator()
    
    # ===== TREE MANIPULATION METHODS =====
    
    def get_tree_iter_by_id(self, item_id, parent_iter=None):
        """Find a tree iter by item ID"""
        it = self.list_store.iter_children(parent_iter) if parent_iter else self.list_store.get_iter_first()
        
        while it:
            current_id = self.list_store.get_value(it, 2)
            if current_id == item_id:
                return it
            
            # Check children
            has_children = self.list_store.get_value(it, 4)
            if has_children:
                child_result = self.get_tree_iter_by_id(item_id, it)
                if child_result:
                    return child_result
            
            # Move to next sibling
            it = self.list_store.iter_next(it)
        
        return None
    
    def move_item_up(self, item_id):
        """Move item up in the UI tree"""
        iter = self.get_tree_iter_by_id(item_id)
        if not iter:
            return False
        
        # Get parent
        parent_iter = self.list_store.iter_parent(iter)
        
        # Get the path to find position
        path = self.list_store.get_path(iter)
        position = path.get_indices()[-1]
        
        if position == 0:
            return False  # Already at top
        
        # Get previous sibling iter
        prev_path = list(path)
        prev_path[-1] = position - 1
        prev_path = tuple(prev_path)
        prev_iter = self.list_store.get_iter(prev_path)
        
        if not prev_iter:
            return False
        
        # Actually swap positions in the tree store
        # Get all data from current item
        title = self.list_store.get_value(iter, 0)
        depth = self.list_store.get_value(iter, 1)
        item_id_val = self.list_store.get_value(iter, 2)
        parent_id = self.list_store.get_value(iter, 3)
        has_children = self.list_store.get_value(iter, 4)
        sort_order = self.list_store.get_value(iter, 5)
        is_new = self.list_store.get_value(iter, 6)
        
        # Get all data from previous item
        prev_title = self.list_store.get_value(prev_iter, 0)
        prev_depth = self.list_store.get_value(prev_iter, 1)
        prev_item_id = self.list_store.get_value(prev_iter, 2)
        prev_parent_id = self.list_store.get_value(prev_iter, 3)
        prev_has_children = self.list_store.get_value(prev_iter, 4)
        prev_sort_order = self.list_store.get_value(prev_iter, 5)
        prev_is_new = self.list_store.get_value(prev_iter, 6)
        
        # Swap the values
        self.list_store.set(iter,
            0, prev_title,
            1, prev_depth,
            2, prev_item_id,
            3, prev_parent_id,
            4, prev_has_children,
            5, prev_sort_order,
            6, prev_is_new
        )
        
        self.list_store.set(prev_iter,
            0, title,
            1, depth,
            2, item_id_val,
            3, parent_id,
            4, has_children,
            5, sort_order,
            6, is_new
        )
        
        # Update sort orders to match new positions
        self.update_sort_order_for_level(parent_iter)
        
        # Mark both as dirty if they have database IDs
        if not is_new and item_id_val > 0:
            self.dirty_items.add(item_id_val)
        if not prev_is_new and prev_item_id > 0:
            self.dirty_items.add(prev_item_id)
        
        # Keep the moved item selected
        self.selection.select_iter(prev_iter)
        self.selected_item_id = item_id_val
        
        self.mark_unsaved_changes()
        return True
    
    def move_item_down(self, item_id):
        """Move item down in the UI tree"""
        iter = self.get_tree_iter_by_id(item_id)
        if not iter:
            return False
        
        # Get parent
        parent_iter = self.list_store.iter_parent(iter)
        
        # Get the path to find position
        path = self.list_store.get_path(iter)
        position = path.get_indices()[-1]
        
        # Check if there's a next sibling
        next_path = list(path)
        next_path[-1] = position + 1
        next_path = tuple(next_path)
        next_iter = self.list_store.get_iter(next_path)
        
        if not next_iter:
            return False  # Already at bottom
        
        # Get all data from current item
        title = self.list_store.get_value(iter, 0)
        depth = self.list_store.get_value(iter, 1)
        item_id_val = self.list_store.get_value(iter, 2)
        parent_id = self.list_store.get_value(iter, 3)
        has_children = self.list_store.get_value(iter, 4)
        sort_order = self.list_store.get_value(iter, 5)
        is_new = self.list_store.get_value(iter, 6)
        
        # Get all data from next item
        next_title = self.list_store.get_value(next_iter, 0)
        next_depth = self.list_store.get_value(next_iter, 1)
        next_item_id = self.list_store.get_value(next_iter, 2)
        next_parent_id = self.list_store.get_value(next_iter, 3)
        next_has_children = self.list_store.get_value(next_iter, 4)
        next_sort_order = self.list_store.get_value(next_iter, 5)
        next_is_new = self.list_store.get_value(next_iter, 6)
        
        # Swap the values
        self.list_store.set(iter,
            0, next_title,
            1, next_depth,
            2, next_item_id,
            3, next_parent_id,
            4, next_has_children,
            5, next_sort_order,
            6, next_is_new
        )
        
        self.list_store.set(next_iter,
            0, title,
            1, depth,
            2, item_id_val,
            3, parent_id,
            4, has_children,
            5, sort_order,
            6, is_new
        )
        
        # Update sort orders to match new positions
        self.update_sort_order_for_level(parent_iter)
        
        # Mark both as dirty if they have database IDs
        if not is_new and item_id_val > 0:
            self.dirty_items.add(item_id_val)
        if not next_is_new and next_item_id > 0:
            self.dirty_items.add(next_item_id)
        
        # Keep the moved item selected
        self.selection.select_iter(next_iter)
        self.selected_item_id = item_id_val
        
        self.mark_unsaved_changes()
        return True
    
    def update_sort_order_for_level(self, parent_iter):
        """Update sort_order values for all items at a level"""
        index = 1
        it = self.list_store.iter_children(parent_iter) if parent_iter else self.list_store.get_iter_first()
        
        while it:
            # Update sort order
            self.list_store.set_value(it, 5, index)
            
            # Mark as dirty if it has a database ID and isn't new
            item_id = self.list_store.get_value(it, 2)
            is_new = self.list_store.get_value(it, 6)
            if item_id > 0 and not is_new:
                self.dirty_items.add(item_id)
            elif item_id < 0 and is_new:
                # Update sort order in new_items list
                for new_item in self.new_items:
                    if new_item.get('temp_id') == item_id:
                        new_item['sort_order'] = index
                        break
            
            index += 1
            it = self.list_store.iter_next(it)
    
    def get_next_sort_order(self, parent_iter):
        """Get next available sort order for a level"""
        max_order = 0
        
        if parent_iter is None:
            # Top level
            it = self.list_store.get_iter_first()
        else:
            # Child level
            it = self.list_store.iter_children(parent_iter)
        
        # Iterate through all siblings
        while it:
            order = self.list_store.get_value(it, 5)
            if order > max_order:
                max_order = order
            it = self.list_store.iter_next(it)
        
        return max_order + 1
    
    # ===== EVENT HANDLERS =====
    
    def on_window_close(self, window):
        """Handle window close"""
        if self.unsaved_changes:
            dialog = Gtk.MessageDialog(
                transient_for=self.window,
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO_CANCEL,
                text="Unsaved Changes"
            )
            dialog.format_secondary_text(
                f"You have {len(self.dirty_items)} modified item(s), "
                f"{len(self.new_items)} new item(s), and "
                f"{len(self.deleted_items)} deleted item(s).\n"
                "Save before closing?"
            )
            
            response = dialog.run()
            dialog.destroy()
            
            if response == Gtk.ResponseType.YES:
                if not self.save_menu():
                    return
            elif response == Gtk.ResponseType.CANCEL:
                return
        
        Gtk.main_quit()
    
    def on_menu_name_changed(self, entry):
        """When menu name changes"""
        new_name = entry.get_text().strip()
        if new_name != self.current_menu_name:
            self.current_menu_name = new_name
            self.window.set_title(f"🎯 GMen Editor - {new_name}")
            self.mark_unsaved_changes()
    
    def on_default_toggled(self, check):
        """When default checkbox toggled"""
        self.mark_unsaved_changes()
    
    def on_save(self, button):
        """Save button handler"""
        self.save_menu()
    
    def save_menu(self):
        """Save all changes to database"""
        if not self.unsaved_changes:
            self.show_message("No changes to save", Gtk.MessageType.INFO)
            return True
        
        try:
            with self.db.transaction():
                # 1. Update menu name and default status
                self.db.execute("""
                    UPDATE menus 
                    SET name = ?, is_default = ?
                    WHERE id = ?
                """, (
                    self.current_menu_name,
                    1 if self.default_check.get_active() else 0,
                    self.current_menu_id
                ))
                
                # Clear other menus' default status if this is default
                if self.default_check.get_active():
                    self.db.execute("""
                        UPDATE menus 
                        SET is_default = 0 
                        WHERE id != ?
                    """, (self.current_menu_id,))
                
                # 2. Update modified items (including properties)
                for item_id in self.dirty_items:
                    # Get the tree iter to get current values
                    iter = self.get_tree_iter_by_id(item_id)
                    if iter:
                        title = self.list_store.get_value(iter, 0)
                        sort_order = self.list_store.get_value(iter, 5)
                        parent_id = self.list_store.get_value(iter, 3)
                        
                        # Get properties from UI (they should be loaded when item was selected)
                        # For now, we'll just update title, sort_order, and parent_id
                        # In a real app, you'd also update command, icon, etc.
                        self.db.execute("""
                            UPDATE menu_items 
                            SET title = ?, sort_order = ?, parent_id = ?
                            WHERE id = ?
                        """, (title, sort_order, parent_id, item_id))
                
                # 3. Insert new items
                for new_item in self.new_items:
                    self.db.execute("""
                        INSERT INTO menu_items 
                        (menu_id, title, command, icon, depth, parent_id, sort_order)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        self.current_menu_id,
                        new_item.get('title', 'New Item'),
                        new_item.get('command', ''),
                        new_item.get('icon', ''),
                        new_item.get('depth', 0),
                        new_item.get('parent_id'),
                        new_item.get('sort_order', 0)
                    ))
                    
                    # Get the real ID and update the tree
                    result = self.db.fetch_one("SELECT last_insert_rowid() AS id")
                    real_id = result['id']
                    
                    # Find and update the tree item
                    iter = self.get_tree_iter_by_id(new_item.get('temp_id'))
                    if iter:
                        self.list_store.set_value(iter, 2, real_id)
                        self.list_store.set_value(iter, 6, False)  # Not new anymore
                
                # 4. Delete removed items
                for item_id in self.deleted_items:
                    self.db.execute("DELETE FROM menu_items WHERE id = ?", (item_id,))
                    self.db.execute("DELETE FROM window_states WHERE menu_item_id = ?", (item_id,))
            
            # Clear all change tracking
            self.dirty_items.clear()
            self.new_items = []
            self.deleted_items.clear()
            self.unsaved_changes = False
            self.update_unsaved_indicator()
            
            self.show_message("💾 All changes saved to database")
            print(f"✅ Menu '{self.current_menu_name}' saved to database")
            return True
            
        except Exception as e:
            print(f"❌ Save failed: {e}")
            self.show_message(f"Save failed: {e}", Gtk.MessageType.ERROR)
            return False
    
    def on_selection_changed(self, selection):
        """When tree selection changes"""
        model, treeiter = selection.get_selected()
        if treeiter:
            title, depth, item_id, parent_id, has_children, sort_order, is_new = model[treeiter]
            self.selected_item_id = item_id
            
            # Load item details
            if not is_new and item_id > 0:
                item = self.db.fetch_one("""
                    SELECT title, command, icon, script_id FROM menu_items 
                    WHERE id = ?
                """, (item_id,))
                
                if item:
                    self.title_entry.set_text(item['title'])
                    self.icon_entry.set_text(item['icon'] if item['icon'] else "")
                    self.cmd_entry.set_text(item['command'] if item['command'] else "")
                    
                    # Check if it's a command or script
                    if item['script_id']:
                        self.script_radio.set_active(True)
                        self.on_type_changed()
                        self.script_combo.set_active(0)  # Placeholder
                    else:
                        self.cmd_radio.set_active(True)
                        self.on_type_changed()
                
                # Load window state
                window_state = self.db.fetch_one("""
                    SELECT x, y, width, height, monitor, remember 
                    FROM window_states 
                    WHERE menu_item_id = ? AND is_active = 1
                """, (item_id,))
                
                if window_state:
                    self.window_enable_check.set_active(True)
                    self.x_entry.set_text(str(window_state['x']))
                    self.y_entry.set_text(str(window_state['y']))
                    self.width_entry.set_text(str(window_state['width']))
                    self.height_entry.set_text(str(window_state['height']))
                    self.monitor_entry.set_text(str(window_state['monitor']))
                else:
                    self.window_enable_check.set_active(False)
                    self.x_entry.set_text("")
                    self.y_entry.set_text("")
                    self.width_entry.set_text("")
                    self.height_entry.set_text("")
                    self.monitor_entry.set_text("")
            else:
                # For new items
                self.title_entry.set_text(title)
                self.icon_entry.set_text("")
                self.cmd_radio.set_active(True)
                self.on_type_changed()
                self.cmd_entry.set_text("")
                self.script_combo.set_active(0)
                self.window_enable_check.set_active(False)
            
            # Update info
            self.info_label.set_text(f"Item ID: {item_id}{' (NEW)' if is_new else ''}, Depth: {depth}, Sort: {sort_order}")
        else:
            self.selected_item_id = None
            self.clear_properties()
        
        self.update_button_states()
    
    def on_type_changed(self, *args):
        """When command/script type changes"""
        is_script = self.script_radio.get_active()
        
        if is_script:
            self.cmd_label.hide()
            self.cmd_entry.hide()
            self.script_label.show()
            self.script_combo.show()
        else:
            self.cmd_label.show()
            self.cmd_entry.show()
            self.script_label.hide()
            self.script_combo.hide()
        
        self.mark_unsaved_changes()
    
    def on_title_changed(self, entry):
        if self.selected_item_id:
            title = entry.get_text().strip()
            
            # Update UI tree
            iter = self.get_tree_iter_by_id(self.selected_item_id)
            if iter:
                self.list_store.set_value(iter, 0, title)
                
                # Mark as dirty if it exists in DB
                is_new = self.list_store.get_value(iter, 6)
                if not is_new:
                    self.dirty_items.add(self.selected_item_id)
                else:
                    # Update in new_items list
                    for new_item in self.new_items:
                        if new_item.get('temp_id') == self.selected_item_id:
                            new_item['title'] = title
                            break
                
                self.mark_unsaved_changes()
    
    def on_cmd_changed(self, entry):
        if self.selected_item_id:
            command = entry.get_text().strip()
            # We'll track command changes in the save method
            self.mark_unsaved_changes()
    
    def on_script_changed(self, combo):
        self.mark_unsaved_changes()
    
    def on_icon_changed(self, entry):
        if self.selected_item_id:
            self.mark_unsaved_changes()
    
    def on_window_enable_toggled(self, check):
        """Enable/disable window state entries"""
        enabled = check.get_active()
        for entry in [self.x_entry, self.y_entry, self.width_entry, 
                     self.height_entry, self.monitor_entry]:
            entry.set_sensitive(enabled)
        
        if self.selected_item_id:
            self.mark_unsaved_changes()
    
    def on_window_state_changed(self, entry):
        """Update window state"""
        if self.selected_item_id:
            self.mark_unsaved_changes()
    
    # ===== ITEM OPERATIONS =====
    
    def on_add(self, button):
        """Add new item at current level"""
        parent_id = None
        depth = 0
        parent_iter = None
        
        if self.selected_item_id:
            # Get selected item's info
            iter = self.get_tree_iter_by_id(self.selected_item_id)
            if iter:
                depth = self.list_store.get_value(iter, 1)
                parent_id = self.selected_item_id if depth > 0 else None
                parent_iter = self.list_store.iter_parent(iter)
        
        # Generate temporary ID
        temp_id = -len(self.new_items) - 1
        
        # Create new item in UI tree
        if parent_iter:
            new_iter = self.list_store.append(parent_iter)
        else:
            new_iter = self.list_store.append(None)
        
        # Calculate sort order
        sort_order = self.get_next_sort_order(parent_iter)
        
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
        
        # Track new item
        self.new_items.append({
            'temp_id': temp_id,
            'title': 'New Item',
            'depth': depth,
            'parent_id': parent_id,
            'sort_order': sort_order
        })
        
        # Clear the "empty menu" message
        self.info_label.set_text("")
        
        # Select the new item
        path = self.list_store.get_path(new_iter)
        self.treeview.scroll_to_cell(path, None, False, 0, 0)
        self.selection.select_iter(new_iter)
        
        # Update sort orders
        self.update_sort_order_for_level(parent_iter)
        
        self.mark_unsaved_changes()
        print(f"➕ Added new item (temp ID: {temp_id})")
    
    def on_submenu(self, button):
        """Add subitem under selected item"""
        if not self.selected_item_id:
            return
        
        iter = self.get_tree_iter_by_id(self.selected_item_id)
        if not iter:
            return
        
        depth = self.list_store.get_value(iter, 1) + 1
        parent_id = self.selected_item_id
        
        # Generate temporary ID
        temp_id = -len(self.new_items) - 1
        
        # Create new item as child in UI tree
        new_iter = self.list_store.append(iter)
        
        # Calculate sort order
        sort_order = self.get_next_sort_order(iter)
        
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
        
        # Track new item
        self.new_items.append({
            'temp_id': temp_id,
            'title': 'Sub-Menu',
            'depth': depth,
            'parent_id': parent_id,
            'sort_order': sort_order
        })
        
        # Expand parent to show child
        path = self.list_store.get_path(iter)
        self.treeview.expand_row(path, False)
        
        # Select the new item
        child_path = self.list_store.get_path(new_iter)
        self.treeview.scroll_to_cell(child_path, None, False, 0, 0)
        self.selection.select_iter(new_iter)
        
        self.mark_unsaved_changes()
        print(f"📁 Added submenu (temp ID: {temp_id})")
    
    def on_remove(self, button):
        """Remove selected item and its children"""
        if not self.selected_item_id:
            return
        
        iter = self.get_tree_iter_by_id(self.selected_item_id)
        if not iter:
            return
        
        item_id = self.selected_item_id
        is_new = self.list_store.get_value(iter, 6)
        
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Delete Item"
        )
        dialog.format_secondary_text("Delete this item and all its sub-items?")
        
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES:
            # Remove from UI tree
            parent_iter = self.list_store.iter_parent(iter)
            self.list_store.remove(iter)
            
            # Update parent's has_children if needed
            if parent_iter:
                has_children = self.list_store.iter_has_child(parent_iter)
                self.list_store.set_value(parent_iter, 4, has_children)
            
            # Track deletion
            if not is_new:
                self.deleted_items.add(item_id)
            else:
                # Remove from new_items list
                self.new_items = [item for item in self.new_items 
                                if item.get('temp_id') != item_id]
            
            self.selected_item_id = None
            self.mark_unsaved_changes()
            
            # Update sort orders
            self.update_sort_order_for_level(parent_iter)
            
            print(f"🗑️ Removed item {item_id}")
    
    def on_up(self, button):
        """Move item up in UI"""
        if not self.selected_item_id:
            return
        
        if self.move_item_up(self.selected_item_id):
            print(f"⬆️  Moved item {self.selected_item_id} up")
        else:
            self.show_message("Already at the top!", Gtk.MessageType.INFO)
    
    def on_down(self, button):
        """Move item down in UI"""
        if not self.selected_item_id:
            return
        
        if self.move_item_down(self.selected_item_id):
            print(f"⬇️  Moved item {self.selected_item_id} down")
        else:
            self.show_message("Already at the bottom!", Gtk.MessageType.INFO)
    
    def mark_unsaved_changes(self):
        """Mark that there are unsaved changes"""
        self.unsaved_changes = True
        self.update_unsaved_indicator()
    
    def update_unsaved_indicator(self):
        """Update the unsaved changes indicator"""
        if self.unsaved_changes:
            count = len(self.dirty_items) + len(self.new_items) + len(self.deleted_items)
            self.unsaved_label.set_markup(f"<span foreground='orange' weight='bold'>{count} unsaved</span>")
            self.unsaved_label.show()
            self.save_btn.set_sensitive(True)
        else:
            self.unsaved_label.hide()
            self.save_btn.set_sensitive(False)
    
    def clear_properties(self):
        """Clear property fields"""
        self.title_entry.set_text("")
        self.cmd_radio.set_active(True)
        self.on_type_changed()
        self.cmd_entry.set_text("")
        self.script_combo.set_active(0)
        self.icon_entry.set_text("")
        self.window_enable_check.set_active(False)
        self.x_entry.set_text("")
        self.y_entry.set_text("")
        self.width_entry.set_text("")
        self.height_entry.set_text("")
        self.monitor_entry.set_text("")
        self.info_label.set_text("Select an item to edit")
    
    def update_button_states(self):
        """Update button enabled/disabled states"""
        has_selection = self.selected_item_id is not None
        self.add_btn.set_sensitive(True)
        self.submenu_btn.set_sensitive(has_selection)
        self.remove_btn.set_sensitive(has_selection)
        self.up_btn.set_sensitive(has_selection)
        self.down_btn.set_sensitive(has_selection)
    
    def on_reload(self, button):
        """Reload from database"""
        if self.unsaved_changes:
            dialog = Gtk.MessageDialog(
                transient_for=self.window,
                flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.YES_NO,
                text="Discard Unsaved Changes?"
            )
            dialog.format_secondary_text(
                f"You have {len(self.dirty_items) + len(self.new_items) + len(self.deleted_items)} "
                "unsaved change(s). Reloading will lose these changes."
            )
            
            response = dialog.run()
            dialog.destroy()
            
            if response != Gtk.ResponseType.YES:
                return
        
        self.load_menu_to_ui()
        self.show_message("🔄 Reloaded from database")
    
    def on_backup(self, button):
        """Create database backup"""
        backup_path = self.db.backup()
        self.show_message(f"💾 Backup created: {backup_path.name}")
        print(f"✅ Backup saved to: {backup_path}")
    
    def open_script_editor(self, button):
        """Open the script editor"""
        try:
            editor_path = Path.cwd() / "gmen_script_editor.py"
            if editor_path.exists():
                subprocess.Popen([sys.executable, str(editor_path)])
            else:
                self.show_message("Script editor not found", Gtk.MessageType.WARNING)
        except Exception as e:
            print(f"❌ Could not launch script editor: {e}")
    
    def on_test(self, button):
        """Test launch GMen"""
        if self.unsaved_changes:
            if not self.save_menu():
                self.show_message("Please save changes before testing", Gtk.MessageType.WARNING)
                return
        
        try:
            gmen_path = Path.cwd() / "gmen.py"
            if gmen_path.exists():
                subprocess.Popen([sys.executable, str(gmen_path)], cwd=Path.cwd())
                self.show_message("🚀 GMen launched in test mode!")
            else:
                self.show_message("⚠️ GMen executable not found")
        except Exception as e:
            self.show_message(f"❌ Failed to launch: {e}")
    
    def on_quit(self, button):
        """Quit button handler"""
        self.on_window_close(self.window)
    
    def show_message(self, text, msg_type=Gtk.MessageType.INFO, duration=3000):
        """Show a temporary message"""
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            flags=0,
            message_type=msg_type,
            buttons=Gtk.ButtonsType.OK,
            text=text
        )
        
        GLib.timeout_add(duration, dialog.destroy)
        dialog.run()
    
    def run(self):
        """Start the application"""
        Gtk.main()


# ===== MAIN =====
if __name__ == "__main__":
    print("🎯 GMen Editor v4.0 - UI-First Architecture")
    print("📁 Database: ~/.config/gmen/gmen.db")
    print("💡 Changes are saved only when you click 'Save'")
    
    editor = GMenEditor()
    editor.run()
