#!/usr/bin/env python3
"""
GMen Editor v3.5 - Database-First with Scripting Support
"""

import gi
import subprocess
import sys
from pathlib import Path

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk

from database import get_database

class GMenEditor:
    def __init__(self):
        self.db = get_database()
        self.current_menu_id = None
        self.selected_item_id = None
        self.unsaved_changes = False
        
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
        # Main vertical box
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
        save_btn = Gtk.Button(label="💾 Save")
        save_btn.connect("clicked", self.on_save)
        
        hbox.pack_start(name_label, False, False, 0)
        hbox.pack_start(self.menu_name_entry, True, True, 0)
        hbox.pack_start(self.default_check, False, False, 0)
        hbox.pack_start(save_btn, False, False, 0)
        
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
        
        # ListStore for items: display_text, depth, item_id, has_children
        self.list_store = Gtk.ListStore(str, int, int, bool)
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
        self.load_scripts_to_combo()
        self.script_combo.connect("changed", self.on_script_changed)
        vbox.pack_start(self.script_combo, False, False, 0)
        
        # Edit Script button
        self.edit_script_btn = Gtk.Button(label="✏️ Edit Script")
        self.edit_script_btn.connect("clicked", self.on_edit_script)
        vbox.pack_start(self.edit_script_btn, False, False, 0)
        
        # Icon (optional)
        vbox.pack_start(Gtk.Label(label="Icon (optional):"), False, False, 0)
        self.icon_entry = Gtk.Entry()
        self.icon_entry.set_placeholder_text("terminal, firefox, etc.")
        self.icon_entry.connect("changed", self.on_icon_changed)
        vbox.pack_start(self.icon_entry, False, False, 0)
        
        # ===== WINDOW STATE CONTROLS =====
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
        self.edit_script_btn.hide()
        
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
    
    def load_scripts_to_combo(self):
        """Load scripts into combo box"""
        scripts = self.db.fetch("SELECT id, name FROM scripts ORDER BY name")
        self.script_combo.remove_all()
        self.script_combo.append_text("-- Select Script --")
        for script in scripts:
            self.script_combo.append_text(f"{script['name']} (ID: {script['id']})")
        self.script_combo.set_active(0)
    
    def load_menu_to_ui(self):
        """Load menu items from database and display in tree"""
        self.list_store.clear()
        self.selected_item_id = None
        
        # Get all items for this menu
        items = self.db.fetch("""
            SELECT id, title, depth, parent_id,
                   (SELECT COUNT(*) FROM menu_items c WHERE c.parent_id = m.id) as child_count
            FROM menu_items m
            WHERE menu_id = ?
            ORDER BY depth, sort_order
        """, (self.current_menu_id,))
        
        for item in items:
            indent = "    " * item['depth']
            display_text = f"{indent}{item['title']}"
            has_children = item['child_count'] > 0
            
            self.list_store.append([
                display_text,
                item['depth'],
                item['id'],
                has_children
            ])
        
        print(f"📋 Loaded {len(items)} items into UI")
        self.update_button_states()
    
    # ===== EVENT HANDLERS =====
    
    def on_window_close(self, window):
        """Handle window close"""
        if self.unsaved_changes:
            dialog = Gtk.MessageDialog(
                transient_for=self.window,
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO,
                text="Unsaved Changes"
            )
            dialog.format_secondary_text("You have unsaved changes. Save before closing?")
            
            response = dialog.run()
            dialog.destroy()
            
            if response == Gtk.ResponseType.YES:
                self.save_menu()
        
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
        """Save current menu to database"""
        # Update menu name and default status
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
        
        self.unsaved_changes = False
        self.show_message("💾 Menu saved to database")
        print(f"✅ Menu '{self.current_menu_name}' saved to database")
    
    def on_selection_changed(self, selection):
        """When tree selection changes"""
        model, treeiter = selection.get_selected()
        if treeiter:
            display_text, depth, item_id, has_children = model[treeiter]
            self.selected_item_id = item_id
            
            # Load item details from database
            item = self.db.fetch_one("""
                SELECT title, command, icon, script_id FROM menu_items 
                WHERE id = ?
            """, (item_id,))
            
            if item:
                self.title_entry.set_text(item['title'])
                self.icon_entry.set_text(item['icon'] if item['icon'] else "")
                
                # Check if it's a command or script
                if item['script_id']:
                    self.script_radio.set_active(True)
                    self.on_type_changed()
                    
                    # Find and select the script in combo
                    script = self.db.fetch_one("SELECT name FROM scripts WHERE id = ?", (item['script_id'],))
                    if script:
                        for i in range(self.script_combo.get_model().get_n_items()):
                            text = self.script_combo.get_model().get_string(i)
                            if script['name'] in text:
                                self.script_combo.set_active(i)
                                break
                    
                    self.cmd_entry.set_text("")
                else:
                    self.cmd_radio.set_active(True)
                    self.on_type_changed()
                    self.cmd_entry.set_text(item['command'] if item['command'] else "")
                    self.script_combo.set_active(0)
            
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
            
            # Update info
            self.info_label.set_text(f"Item ID: {item_id}, Depth: {depth}" + 
                                   (f", Has children: {has_children}" if has_children else ""))
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
            self.edit_script_btn.show()
        else:
            self.cmd_label.show()
            self.cmd_entry.show()
            self.script_label.hide()
            self.script_combo.hide()
            self.edit_script_btn.hide()
        
        self.mark_unsaved_changes()
    
    def on_title_changed(self, entry):
        if self.selected_item_id:
            title = entry.get_text().strip()
            self.db.execute("""
                UPDATE menu_items SET title = ? WHERE id = ?
            """, (title, self.selected_item_id))
            
            # Update UI display
            self.update_item_in_list(self.selected_item_id, title)
            self.mark_unsaved_changes()
    
    def on_cmd_changed(self, entry):
        if self.selected_item_id and self.cmd_radio.get_active():
            self.db.execute("""
                UPDATE menu_items SET command = ?, script_id = NULL WHERE id = ?
            """, (entry.get_text(), self.selected_item_id))
            self.mark_unsaved_changes()
    
    def on_script_changed(self, combo):
        if self.selected_item_id and self.script_radio.get_active():
            active_text = combo.get_active_text()
            if active_text and active_text != "-- Select Script --":
                # Extract script ID from text like "script_name (ID: 1)"
                import re
                match = re.search(r'ID:\s*(\d+)', active_text)
                if match:
                    script_id = int(match.group(1))
                    self.db.execute("""
                        UPDATE menu_items SET script_id = ?, command = '' WHERE id = ?
                    """, (script_id, self.selected_item_id))
                    self.mark_unsaved_changes()
    
    def on_edit_script(self, button):
        """Edit the selected script"""
        if self.selected_item_id and self.script_radio.get_active():
            # Get the script ID
            item = self.db.fetch_one("SELECT script_id FROM menu_items WHERE id = ?", (self.selected_item_id,))
            if item and item['script_id']:
                try:
                    editor_path = Path.cwd() / "gmen_script_editor.py"
                    if editor_path.exists():
                        subprocess.Popen([sys.executable, str(editor_path), f"--script={item['script_id']}"])
                    else:
                        self.show_message("Script editor not found", Gtk.MessageType.WARNING)
                except Exception as e:
                    print(f"❌ Could not launch script editor: {e}")
    
    def on_icon_changed(self, entry):
        if self.selected_item_id:
            self.db.execute("""
                UPDATE menu_items SET icon = ? WHERE id = ?
            """, (entry.get_text(), self.selected_item_id))
            self.mark_unsaved_changes()
    
    def on_window_enable_toggled(self, check):
        """Enable/disable window state entries"""
        enabled = check.get_active()
        for entry in [self.x_entry, self.y_entry, self.width_entry, 
                     self.height_entry, self.monitor_entry]:
            entry.set_sensitive(enabled)
        
        if self.selected_item_id:
            if not enabled:
                # Remove window state
                self.db.execute("""
                    DELETE FROM window_states WHERE menu_item_id = ?
                """, (self.selected_item_id,))
            self.mark_unsaved_changes()
    
    def on_window_state_changed(self, entry):
        """Update window state in database"""
        if self.selected_item_id and self.window_enable_check.get_active():
            # Get values
            x = self.get_int_or_none(self.x_entry.get_text())
            y = self.get_int_or_none(self.y_entry.get_text())
            width = self.get_int_or_none(self.width_entry.get_text())
            height = self.get_int_or_none(self.height_entry.get_text())
            monitor = self.get_int_or_none(self.monitor_entry.get_text())
            
            # Get app name from command or script
            command = self.db.fetch_one("""
                SELECT command FROM menu_items WHERE id = ?
            """, (self.selected_item_id,))
            
            app_name = ""
            if command and command['command']:
                app_name = command['command'].split()[0].lower()
            
            if app_name:
                self.db.execute("""
                    INSERT OR REPLACE INTO window_states 
                    (menu_item_id, app_name, x, y, width, height, monitor, remember, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1)
                """, (
                    self.selected_item_id,
                    app_name,
                    x or 100,
                    y or 100,
                    width or 800,
                    height or 600,
                    monitor or 0
                ))
                self.mark_unsaved_changes()
    
    def get_int_or_none(self, text):
        """Convert text to int or return None"""
        text = str(text).strip()
        if text and text.replace('-', '', 1).isdigit():
            return int(text)
        return None
    
    def update_item_in_list(self, item_id, new_title):
        """Update item title in the list display"""
        for i, row in enumerate(self.list_store):
            if row[2] == item_id:  # Compare item_id
                depth = row[1]
                indent = "    " * depth
                display_text = f"{indent}{new_title}"
                self.list_store[i][0] = display_text
                break
    
    def mark_unsaved_changes(self):
        """Mark that there are unsaved changes"""
        self.unsaved_changes = True
    
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
        self.add_btn.set_sensitive(True)  # Can always add
        self.submenu_btn.set_sensitive(has_selection)
        self.remove_btn.set_sensitive(has_selection)
        self.up_btn.set_sensitive(has_selection)
        self.down_btn.set_sensitive(has_selection)
    
    def on_add(self, button):
        """Add new item at current level"""
        if self.selected_item_id:
            # Get selected item's depth and parent
            selected = self.db.fetch_one("""
                SELECT depth, parent_id FROM menu_items WHERE id = ?
            """, (self.selected_item_id,))
            
            depth = selected['depth']
            parent_id = selected['parent_id']
        else:
            # Add top-level item
            depth = 0
            parent_id = None
        
        # Insert new item
        self.db.execute("""
            INSERT INTO menu_items 
            (menu_id, title, command, depth, parent_id, sort_order)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            self.current_menu_id,
            "New Item",
            "",
            depth,
            parent_id,
            999  # Will be sorted last
        ))
        
        new_id = self.db.fetch_one("SELECT last_insert_rowid() AS id")['id']
        self.mark_unsaved_changes()
        self.load_menu_to_ui()
        
        print(f"➕ Added item ID: {new_id}")
    
    def on_submenu(self, button):
        """Add subitem under selected item"""
        if not self.selected_item_id:
            return
        
        # Get selected item's depth
        selected = self.db.fetch_one("""
            SELECT depth FROM menu_items WHERE id = ?
        """, (self.selected_item_id,))
        
        new_depth = selected['depth'] + 1
        
        # Insert as child of selected item
        self.db.execute("""
            INSERT INTO menu_items 
            (menu_id, title, command, depth, parent_id, sort_order)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            self.current_menu_id,
            "Sub-Menu",
            "",
            new_depth,
            self.selected_item_id,
            0
        ))
        
        new_id = self.db.fetch_one("SELECT last_insert_rowid() AS id")['id']
        self.mark_unsaved_changes()
        self.load_menu_to_ui()
        
        print(f"📁 Added submenu ID: {new_id}")
    
    def on_remove(self, button):
        """Remove selected item and its children"""
        if not self.selected_item_id:
            return
        
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
            # Delete item and all children (cascade delete in SQL)
            self.db.execute("""
                DELETE FROM menu_items WHERE id = ? OR parent_id = ?
            """, (self.selected_item_id, self.selected_item_id))
            
            # Also delete window states
            self.db.execute("""
                DELETE FROM window_states WHERE menu_item_id = ?
            """, (self.selected_item_id,))
            
            self.selected_item_id = None
            self.mark_unsaved_changes()
            self.load_menu_to_ui()
            print(f"🗑️ Removed item ID: {self.selected_item_id}")
    
    def on_up(self, button):
        """Move item up in sort order"""
        if self.selected_item_id:
            # Get current sort order and sibling above
            current = self.db.fetch_one("""
                SELECT sort_order, parent_id FROM menu_items WHERE id = ?
            """, (self.selected_item_id,))
            
            sibling = self.db.fetch_one("""
                SELECT id, sort_order FROM menu_items 
                WHERE menu_id = ? AND parent_id = ? AND sort_order < ?
                ORDER BY sort_order DESC LIMIT 1
            """, (self.current_menu_id, current['parent_id'], current['sort_order']))
            
            if sibling:
                # Swap sort orders
                self.db.execute("""
                    UPDATE menu_items SET sort_order = ? WHERE id = ?
                """, (sibling['sort_order'], self.selected_item_id))
                
                self.db.execute("""
                    UPDATE menu_items SET sort_order = ? WHERE id = ?
                """, (current['sort_order'], sibling['id']))
                
                self.mark_unsaved_changes()
                self.load_menu_to_ui()
    
    def on_down(self, button):
        """Move item down in sort order"""
        if self.selected_item_id:
            # Get current sort order and sibling below
            current = self.db.fetch_one("""
                SELECT sort_order, parent_id FROM menu_items WHERE id = ?
            """, (self.selected_item_id,))
            
            sibling = self.db.fetch_one("""
                SELECT id, sort_order FROM menu_items 
                WHERE menu_id = ? AND parent_id = ? AND sort_order > ?
                ORDER BY sort_order ASC LIMIT 1
            """, (self.current_menu_id, current['parent_id'], current['sort_order']))
            
            if sibling:
                # Swap sort orders
                self.db.execute("""
                    UPDATE menu_items SET sort_order = ? WHERE id = ?
                """, (sibling['sort_order'], self.selected_item_id))
                
                self.db.execute("""
                    UPDATE menu_items SET sort_order = ? WHERE id = ?
                """, (current['sort_order'], sibling['id']))
                
                self.mark_unsaved_changes()
                self.load_menu_to_ui()
    
    def on_reload(self, button):
        """Reload from database"""
        self.load_menu_to_ui()
        self.load_scripts_to_combo()
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
        """Test launch GMen with current menu"""
        # First save any changes
        if self.unsaved_changes:
            self.save_menu()
        
        # Try to launch GMen
        try:
            # Look for gmen in current directory
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
    
    def show_message(self, text, duration=3000):
        """Show a temporary message"""
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=text
        )
        
        # Auto-close after duration
        GLib.timeout_add(duration, dialog.destroy)
        dialog.run()
    
    def run(self):
        """Start the application"""
        Gtk.main()


# ===== MAIN =====
if __name__ == "__main__":
    print("🎯 GMen Editor - Database-First with Scripting")
    print("📁 Database: ~/.config/gmen/gmen.db")
    
    editor = GMenEditor()
    editor.run()
