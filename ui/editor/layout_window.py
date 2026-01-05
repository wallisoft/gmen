"""
Window Positioning Tool
For editing window states and workspaces
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import json


class LayoutWindow:
    def __init__(self, db):
        self.db = db
        self.window = None
        self.save_button = None
        self.workspace_combo = None
        self.script_combo = None
        self.current_workspace = None
        
        self._create_ui()
        self._load_workspaces()
        self._load_scripts()
    
    def _create_ui(self):
        self.window = Gtk.Window()
        self.window.set_title("Window Positioning Tool")
        self.window.set_default_size(800, 600)
        self.window.connect("destroy", self._on_close)
        
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        main_vbox.set_margin_top(10)
        main_vbox.set_margin_bottom(10)
        main_vbox.set_margin_start(10)
        main_vbox.set_margin_end(10)
        self.window.add(main_vbox)
        
        # === TOOLBAR ===
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        # Workspace selector
        toolbar.pack_start(Gtk.Label(label="Workspace:"), False, False, 0)
        self.workspace_combo = Gtk.ComboBoxText()
        self.workspace_combo.set_size_request(200, -1)
        self.workspace_combo.connect("changed", self._on_workspace_changed)
        toolbar.pack_start(self.workspace_combo, False, False, 0)
        
        # New workspace button
        new_btn = Gtk.Button(label="New")
        new_btn.connect("clicked", self._on_new_workspace)
        toolbar.pack_start(new_btn, False, False, 0)
        
        # Save button (starts red, goes green when saved)
        self.save_button = Gtk.Button(label="💾 Save")
        self.save_button.get_style_context().add_class("suggested-action")
        self.save_button.connect("clicked", self._on_save)
        toolbar.pack_end(self.save_button, False, False, 0)
        
        main_vbox.pack_start(toolbar, False, False, 0)
        
        # === COMMAND TOOLBAR ===
        cmd_toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        cmd_toolbar.set_margin_top(10)
        cmd_toolbar.set_margin_bottom(10)
        
        cmd_toolbar.pack_start(Gtk.Label(label="Command:"), False, False, 0)
        
        # Command entry
        self.cmd_entry = Gtk.Entry()
        self.cmd_entry.set_placeholder_text("Enter command or select script...")
        cmd_toolbar.pack_start(self.cmd_entry, True, True, 0)
        
        # Script picker
        cmd_toolbar.pack_start(Gtk.Label(label="Script:"), False, False, 0)
        self.script_combo = Gtk.ComboBoxText()
        self.script_combo.set_size_request(150, -1)
        self.script_combo.append("", "None")
        self.script_combo.connect("changed", self._on_script_changed)
        cmd_toolbar.pack_start(self.script_combo, False, False, 0)
        
        # Edit script button
        edit_script_btn = Gtk.Button(label="Edit Script")
        edit_script_btn.connect("clicked", self._on_edit_script)
        cmd_toolbar.pack_start(edit_script_btn, False, False, 0)
        
        main_vbox.pack_start(cmd_toolbar, False, False, 0)
        
        # === WINDOW PROPERTIES GRID ===
        grid_frame = Gtk.Frame(label="Window Position & Size")
        grid_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        grid_vbox.set_margin_top(10)
        grid_vbox.set_margin_bottom(10)
        grid_vbox.set_margin_start(10)
        grid_vbox.set_margin_end(10)
        
        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        
        # X position
        grid.attach(Gtk.Label(label="X:"), 0, 0, 1, 1)
        self.x_spin = Gtk.SpinButton.new_with_range(0, 10000, 1)
        self.x_spin.set_value(100)
        grid.attach(self.x_spin, 1, 0, 1, 1)
        
        # Y position
        grid.attach(Gtk.Label(label="Y:"), 2, 0, 1, 1)
        self.y_spin = Gtk.SpinButton.new_with_range(0, 10000, 1)
        self.y_spin.set_value(100)
        grid.attach(self.y_spin, 3, 0, 1, 1)
        
        # Width
        grid.attach(Gtk.Label(label="Width:"), 0, 1, 1, 1)
        self.width_spin = Gtk.SpinButton.new_with_range(100, 5000, 1)
        self.width_spin.set_value(800)
        grid.attach(self.width_spin, 1, 1, 1, 1)
        
        # Height
        grid.attach(Gtk.Label(label="Height:"), 2, 1, 1, 1)
        self.height_spin = Gtk.SpinButton.new_with_range(100, 5000, 1)
        self.height_spin.set_value(600)
        grid.attach(self.height_spin, 3, 1, 1, 1)
        
        # Display
        grid.attach(Gtk.Label(label="Display:"), 0, 2, 1, 1)
        self.display_spin = Gtk.SpinButton.new_with_range(0, 10, 1)
        self.display_spin.set_value(0)
        grid.attach(self.display_spin, 1, 2, 1, 1)
        
        # State
        grid.attach(Gtk.Label(label="State:"), 2, 2, 1, 1)
        self.state_combo = Gtk.ComboBoxText()
        for state in ["", "normal", "maximized", "minimized", "fullscreen"]:
            self.state_combo.append(state, state)
        self.state_combo.set_active(0)
        grid.attach(self.state_combo, 3, 2, 1, 1)
        
        grid_vbox.pack_start(grid, False, False, 0)
        grid_frame.add(grid_vbox)
        main_vbox.pack_start(grid_frame, False, False, 0)
        
        # === WINDOW LIST ===
        list_frame = Gtk.Frame(label="Saved Window Positions")
        list_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        list_vbox.set_margin_top(10)
        list_vbox.set_margin_bottom(10)
        list_vbox.set_margin_start(10)
        list_vbox.set_margin_end(10)
        
        # List of window states
        self.window_list = Gtk.ListBox()
        self.window_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.window_list.connect("row-selected", self._on_window_selected)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.window_list)
        list_vbox.pack_start(scrolled, True, True, 0)
        
        # Add/Delete buttons
        list_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        add_btn = Gtk.Button(label="Add Window")
        add_btn.connect("clicked", self._on_add_window)
        list_buttons.pack_start(add_btn, True, True, 0)
        
        delete_btn = Gtk.Button(label="Delete Selected")
        delete_btn.connect("clicked", self._on_delete_window)
        list_buttons.pack_start(delete_btn, True, True, 0)
        
        list_vbox.pack_start(list_buttons, False, False, 0)
        list_frame.add(list_vbox)
        
        main_vbox.pack_start(list_frame, True, True, 0)
        
        self.window.show_all()
        
        # Load CSS
        self._load_css()
    
    def _load_css(self):
        css = """
        .suggested-action {
            background-color: #26a269;
            color: white;
        }
        .saved-action {
            background-color: #2ec27e;
            color: white;
        }
        """
        try:
            provider = Gtk.CssProvider()
            provider.load_from_data(css.encode())
            from gi.repository import Gdk
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(),
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        except:
            pass
    
    def _load_workspaces(self):
        """Load workspaces from database"""
        self.workspace_combo.remove_all()
        
        workspaces = self.db.fetch_all("SELECT id, name FROM workspaces ORDER BY name")
        for ws in workspaces:
            self.workspace_combo.append(str(ws['id']), ws['name'])
        
        if workspaces:
            self.workspace_combo.set_active(0)
            self.current_workspace = workspaces[0]['id']
            self._load_workspace_data()
        else:
            # Create default workspace
            self._create_default_workspace()
    
    def _create_default_workspace(self):
        """Create a default workspace"""
        cursor = self.db._get_connection().cursor()
        cursor.execute(
            "INSERT INTO workspaces (name, description) VALUES (?, ?)",
            ("Default Workspace", "Auto-created default workspace")
        )
        self.db._get_connection().commit()
        workspace_id = cursor.lastrowid
        
        self.workspace_combo.append(str(workspace_id), "Default Workspace")
        self.workspace_combo.set_active(0)
        self.current_workspace = workspace_id
    
    def _load_workspace_data(self):
        """Load window states for current workspace"""
        # Clear list
        for child in self.window_list.get_children():
            self.window_list.remove(child)
        
        if not self.current_workspace:
            return
        
        # Get window states for this workspace
        # Note: This assumes window_states table has workspace_id field
        # If not, we need to modify database schema
        
        # For now, just get all window states
        window_states = self.db.fetch_all("""
            SELECT ws.*, mi.title 
            FROM window_states ws
            LEFT JOIN menu_items mi ON ws.item_id = mi.id
            WHERE ws.is_active = 1
            ORDER BY mi.title
        """)
        
        for ws in window_states:
            row = Gtk.ListBoxRow()
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            hbox.set_margin_start(5)
            hbox.set_margin_end(5)
            hbox.set_margin_top(5)
            hbox.set_margin_bottom(5)
            
            title = ws['title'] or f"Window {ws['id']}"
            label = Gtk.Label(label=f"{title} - {ws['x']},{ws['y']} {ws['width']}x{ws['height']}")
            label.set_xalign(0)
            hbox.pack_start(label, True, True, 0)
            
            row.add(hbox)
            self.window_list.add(row)
        
        self.window_list.show_all()
    
    def _load_scripts(self):
        """Load scripts from database"""
        self.script_combo.remove_all()
        self.script_combo.append("", "None")
        
        scripts = self.db.fetch_all("SELECT id, name FROM scripts ORDER BY name")
        for script in scripts:
            self.script_combo.append(str(script['id']), script['name'])
    
    def _on_workspace_changed(self, combo):
        """Handle workspace selection change"""
        active_id = combo.get_active_id()
        if active_id:
            self.current_workspace = int(active_id)
            self._load_workspace_data()
            self._mark_unsaved()
    
    def _on_new_workspace(self, button):
        """Create new workspace"""
        dialog = Gtk.Dialog(
            title="New Workspace",
            transient_for=self.window,
            flags=0
        )
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Create", Gtk.ResponseType.OK)
        
        content = dialog.get_content_area()
        content.set_spacing(10)
        content.set_margin_top(10)
        content.set_margin_bottom(10)
        content.set_margin_start(10)
        content.set_margin_end(10)
        
        name_entry = Gtk.Entry()
        name_entry.set_placeholder_text("Workspace name")
        content.pack_start(name_entry, False, False, 0)
        
        dialog.show_all()
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK and name_entry.get_text():
            cursor = self.db._get_connection().cursor()
            cursor.execute(
                "INSERT INTO workspaces (name, description) VALUES (?, ?)",
                (name_entry.get_text(), "New workspace")
            )
            self.db._get_connection().commit()
            
            # Reload workspaces
            self._load_workspaces()
        
        dialog.destroy()
    
    def _on_script_changed(self, combo):
        """Handle script selection"""
        script_id = combo.get_active_id()
        if script_id:
            script = self.db.fetch_one("SELECT content FROM scripts WHERE id = ?", (int(script_id),))
            if script:
                self.cmd_entry.set_text(script['content'])
        else:
            self.cmd_entry.set_text("")
    
    def _on_edit_script(self, button):
        """Open script editor"""
        print("📜 Opening script editor...")
        # TODO: Open script editor window
        # For now, just show message
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Script Editor"
        )
        dialog.format_secondary_text("Script editor will be implemented soon.")
        dialog.run()
        dialog.destroy()
    
    def _on_add_window(self, button):
        """Add new window position"""
        # Create list item
        row = Gtk.ListBoxRow()
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox.set_margin_start(5)
        hbox.set_margin_end(5)
        hbox.set_margin_top(5)
        hbox.set_margin_bottom(5)
        
        # Get values from form
        x = int(self.x_spin.get_value())
        y = int(self.y_spin.get_value())
        width = int(self.width_spin.get_value())
        height = int(self.height_spin.get_value())
        command = self.cmd_entry.get_text()
        
        label_text = f"{command or 'New Window'} - {x},{y} {width}x{height}"
        label = Gtk.Label(label=label_text)
        label.set_xalign(0)
        hbox.pack_start(label, True, True, 0)
        
        row.add(hbox)
        self.window_list.add(row)
        self.window_list.show_all()
        
        self._mark_unsaved()
    
    def _on_delete_window(self, button):
        """Delete selected window"""
        row = self.window_list.get_selected_row()
        if row:
            self.window_list.remove(row)
            self._mark_unsaved()
    
    def _on_window_selected(self, listbox, row):
        """Load selected window into form"""
        if row:
            # TODO: Load window data into form
            pass
    
    def _on_save(self, button):
        """Save workspace and window positions"""
        print("💾 Saving workspace...")
        
        # Get all window positions from list
        window_data = []
        for row in self.window_list.get_children():
            # Extract data from row label
            # TODO: Actually store proper data
            pass
        
        # Save to database
        try:
            if self.current_workspace:
                # Update workspace with window data
                window_json = json.dumps(window_data)
                cursor = self.db._get_connection().cursor()
                cursor.execute(
                    "UPDATE workspaces SET window_data = ? WHERE id = ?",
                    (window_json, self.current_workspace)
                )
                self.db._get_connection().commit()
            
            # Mark as saved
            self._mark_saved()
            print("✅ Workspace saved")
            
        except Exception as e:
            print(f"❌ Save failed: {e}")
    
    def _mark_unsaved(self):
        """Mark workspace as unsaved"""
        self.save_button.set_label("💾 Save")
        self.save_button.get_style_context().remove_class("saved-action")
        self.save_button.get_style_context().add_class("suggested-action")
    
    def _mark_saved(self):
        """Mark workspace as saved"""
        self.save_button.set_label("✅ Saved")
        self.save_button.get_style_context().remove_class("suggested-action")
        self.save_button.get_style_context().add_class("saved-action")
    
    def _on_close(self, window):
        """Handle window close"""
        self.window = None
    
    def run(self):
        """Run the window (modal)"""
        if self.window:
            self.window.show_all()
            Gtk.main()
