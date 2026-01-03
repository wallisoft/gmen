"""
Property panel with script dialog and window controls
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GLib
import os
from typing import Optional


class PropertyPanel:
    """Enhanced property panel with script dialog and window controls"""
    
    def __init__(self, db=None):
        self.db = db
        self.on_property_changed = None
        self.current_item_id = None
        
        # UI widgets
        self.title_entry = None
        self.command_entry = None
        self.command_button = None  # CHANGED: from combo to button
        self.icon_entry = None
        self.icon_button = None
        self.icon_preview = None
        
        # Window controls (NEW)
        self.window_x_entry = None
        self.window_y_entry = None
        self.window_width_entry = None
        self.window_height_entry = None
        self.window_state_combo = None
        
        self._init_widgets()
    
    def _init_widgets(self):
        """Initialize enhanced widgets"""
        # Title entry
        self.title_entry = Gtk.Entry()
        self.title_entry.set_placeholder_text("Menu Item Title")
        self.title_entry.connect("changed", self._on_title_changed)
        
        # Command field with script button
        command_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        self.command_entry = Gtk.Entry()
        self.command_entry.set_placeholder_text("Command or @scriptname")
        self.command_entry.connect("changed", self._on_command_changed)
        
        self.command_button = Gtk.Button(label="...")
        self.command_button.set_tooltip_text("Select script")
        self.command_button.set_size_request(40, -1)
        self.command_button.connect("clicked", self._on_script_dialog)
        
        command_box.pack_start(self.command_entry, True, True, 0)
        command_box.pack_start(self.command_button, False, False, 0)
        
        self.command_container = command_box
        
        # Icon field with picker button and preview
        icon_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        self.icon_entry = Gtk.Entry()
        self.icon_entry.set_placeholder_text("icon-name or /path/to/icon")
        self.icon_entry.connect("changed", self._on_icon_changed)
        
        self.icon_button = Gtk.Button(label="...")
        self.icon_button.set_tooltip_text("Browse for icon")
        self.icon_button.set_size_request(40, -1)
        self.icon_button.connect("clicked", self._on_pick_icon)
        
        self.icon_preview = Gtk.Image()
        self.icon_preview.set_size_request(24, 24)
        
        icon_box.pack_start(self.icon_entry, True, True, 0)
        icon_box.pack_start(self.icon_button, False, False, 0)
        icon_box.pack_start(self.icon_preview, False, False, 5)
        
        self.icon_container = icon_box
        
        # Window positioning controls (NEW)
        window_box = Gtk.Grid()
        window_box.set_column_spacing(5)
        window_box.set_row_spacing(5)
        
        # X, Y position
        window_box.attach(Gtk.Label(label="X:"), 0, 0, 1, 1)
        self.window_x_entry = Gtk.Entry()
        self.window_x_entry.set_placeholder_text("0")
        self.window_x_entry.set_width_chars(6)
        self.window_x_entry.connect("changed", self._on_window_changed)
        window_box.attach(self.window_x_entry, 1, 0, 1, 1)
        
        window_box.attach(Gtk.Label(label="Y:"), 2, 0, 1, 1)
        self.window_y_entry = Gtk.Entry()
        self.window_y_entry.set_placeholder_text("0")
        self.window_y_entry.set_width_chars(6)
        self.window_y_entry.connect("changed", self._on_window_changed)
        window_box.attach(self.window_y_entry, 3, 0, 1, 1)
        
        # Width, Height
        window_box.attach(Gtk.Label(label="W:"), 0, 1, 1, 1)
        self.window_width_entry = Gtk.Entry()
        self.window_width_entry.set_placeholder_text("800")
        self.window_width_entry.set_width_chars(6)
        self.window_width_entry.connect("changed", self._on_window_changed)
        window_box.attach(self.window_width_entry, 1, 1, 1, 1)
        
        window_box.attach(Gtk.Label(label="H:"), 2, 1, 1, 1)
        self.window_height_entry = Gtk.Entry()
        self.window_height_entry.set_placeholder_text("600")
        self.window_height_entry.set_width_chars(6)
        self.window_height_entry.connect("changed", self._on_window_changed)
        window_box.attach(self.window_height_entry, 3, 1, 1, 1)
        
        # Window state
        window_box.attach(Gtk.Label(label="State:"), 0, 2, 1, 1)
        self.window_state_combo = Gtk.ComboBoxText()
        self.window_state_combo.append_text("Normal")
        self.window_state_combo.append_text("Maximized")
        self.window_state_combo.append_text("Minimized")
        self.window_state_combo.append_text("Fullscreen")
        self.window_state_combo.set_active(0)
        self.window_state_combo.connect("changed", self._on_window_changed)
        window_box.attach(self.window_state_combo, 1, 2, 3, 1)
        
        self.window_container = window_box
        
        # Info labels
        self.id_label = Gtk.Label(label="ID: --")
        self.depth_label = Gtk.Label(label="Depth: --")
        self.type_label = Gtk.Label(label="Type: --")
    
    def create_panel(self):
        """Create the property panel frame"""
        frame = Gtk.Frame(label="⚙️ Properties")
        frame.set_shadow_type(Gtk.ShadowType.IN)
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(12)
        vbox.set_margin_bottom(12)
        vbox.set_margin_start(12)
        vbox.set_margin_end(12)
        frame.add(vbox)
        
        # Title
        vbox.pack_start(self._create_label("Title"), False, False, 0)
        vbox.pack_start(self.title_entry, False, False, 0)
        
        # Command
        vbox.pack_start(self._create_label("Command"), False, False, 5)
        vbox.pack_start(self.command_container, False, False, 0)
        
        # Icon
        vbox.pack_start(self._create_label("Icon"), False, False, 5)
        vbox.pack_start(self.icon_container, False, False, 0)
        
        # Window positioning (NEW)
        vbox.pack_start(self._create_label("Window Position"), False, False, 10)
        vbox.pack_start(self.window_container, False, False, 0)

        # Tile button (NEW)
        tile_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        tile_btn = Gtk.Button.new_with_label("⎔ Tile Alongside")
        tile_btn.set_tooltip_text("Position this window next to the last positioned window")
        tile_btn.connect("clicked", self._on_tile_clicked)
        tile_box.pack_start(tile_btn, False, False, 0)

        vbox.pack_start(tile_box, False, False, 5)
        
        # Separator
        vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 10)
        
        # Info grid
        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(6)
        
        grid.attach(self._create_info_label("ID:"), 0, 0, 1, 1)
        grid.attach(self.id_label, 1, 0, 1, 1)
        
        grid.attach(self._create_info_label("Depth:"), 0, 1, 1, 1)
        grid.attach(self.depth_label, 1, 1, 1, 1)
        
        grid.attach(self._create_info_label("Type:"), 0, 2, 1, 1)
        grid.attach(self.type_label, 1, 2, 1, 1)
        
        vbox.pack_start(grid, False, False, 0)
        
        # Expand
        vbox.pack_start(Gtk.Label(), True, True, 0)
        
        return frame
    
    def _create_label(self, text):
        """Create a section label"""
        label = Gtk.Label(label=f"<b>{text}</b>")
        label.set_use_markup(True)
        label.set_xalign(0)
        return label
    
    def _create_info_label(self, text):
        """Create an info label"""
        label = Gtk.Label(label=f"<small>{text}</small>")
        label.set_use_markup(True)
        label.set_xalign(1)
        return label
    
    def load_item(self, item):
        """Load item properties including window state"""
        self.current_item_id = item.id
        
        # Update fields
        self.title_entry.set_text(item.title)
        self.command_entry.set_text(item.command or "")
        self.icon_entry.set_text(item.icon or "")
        
        # Update icon preview
        self._update_icon_preview(item.icon or "")
        
        # Load window state (NEW)
        if item.window_state:
            self.window_x_entry.set_text(str(item.window_state.get('x', '')))
            self.window_y_entry.set_text(str(item.window_state.get('y', '')))
            self.window_width_entry.set_text(str(item.window_state.get('width', '')))
            self.window_height_entry.set_text(str(item.window_state.get('height', '')))
            
            state = item.window_state.get('state', 'Normal')
            if state == 'maximized':
                self.window_state_combo.set_active(1)
            elif state == 'minimized':
                self.window_state_combo.set_active(2)
            elif state == 'fullscreen':
                self.window_state_combo.set_active(3)
            else:
                self.window_state_combo.set_active(0)
        else:
            self.window_x_entry.set_text("")
            self.window_y_entry.set_text("")
            self.window_width_entry.set_text("")
            self.window_height_entry.set_text("")
            self.window_state_combo.set_active(0)
        
        # Update info labels
        db_id = f"DB:{item.db_id}" if item.db_id else f"Temp:{item.id[:8]}"
        self.id_label.set_text(db_id)
        self.depth_label.set_text(str(item.depth))
        
        # Determine type
        item_type = "Folder"
        if item.command:
            if item.is_script():
                item_type = "Script"
            else:
                item_type = "Command"
        self.type_label.set_text(item_type)
        
        print(f"📋 PropertyPanel loaded item {item.id}")
    
    def clear(self):
        """Clear the panel"""
        self.current_item_id = None
        self.title_entry.set_text("")
        self.command_entry.set_text("")
        self.icon_entry.set_text("")
        self.icon_preview.clear()
        
        # Clear window controls
        self.window_x_entry.set_text("")
        self.window_y_entry.set_text("")
        self.window_width_entry.set_text("")
        self.window_height_entry.set_text("")
        self.window_state_combo.set_active(0)
        
        self.id_label.set_text("ID: --")
        self.depth_label.set_text("Depth: --")
        self.type_label.set_text("Type: --")
    
    def _update_icon_preview(self, icon_text):
        """Update icon preview image"""
        if not icon_text:
            self.icon_preview.clear()
            return
        
        try:
            theme = Gtk.IconTheme.get_default()
            if theme.has_icon(icon_text):
                self.icon_preview.set_from_icon_name(icon_text, Gtk.IconSize.BUTTON)
                return
        except:
            pass
        
        if os.path.exists(icon_text):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon_text, 24, 24)
                self.icon_preview.set_from_pixbuf(pixbuf)
            except:
                self.icon_preview.clear()
        else:
            self.icon_preview.clear()

    # In property_panel.py, modify the _on_title_changed method:
    def _on_title_changed(self, entry):
        """Handle title change"""
        if self.current_item_id and self.on_property_changed:
            new_title = entry.get_text()
            # Notify immediately
            self.on_property_changed(self.current_item_id, 'title', new_title)

    def _on_command_changed(self, entry):
        """Handle command change"""
        if self.current_item_id and self.on_property_changed:
            new_command = entry.get_text()
            self.on_property_changed(self.current_item_id, 'command', new_command)
            
            # Update type label
            if new_command.startswith('@'):
                self.type_label.set_text("Script")
            elif new_command:
                self.type_label.set_text("Command")
            else:
                self.type_label.set_text("Folder")
    
    def _on_icon_changed(self, entry):
        """Handle icon change"""
        if self.current_item_id and self.on_property_changed:
            new_icon = entry.get_text()
            self.on_property_changed(self.current_item_id, 'icon', new_icon)
            self._update_icon_preview(new_icon)
    
    def _on_window_changed(self, widget):
        """Handle window control changes (NEW)"""
        if not self.current_item_id or not self.on_property_changed:
            return
        
        try:
            window_state = {
                'x': int(self.window_x_entry.get_text()) if self.window_x_entry.get_text() else None,
                'y': int(self.window_y_entry.get_text()) if self.window_y_entry.get_text() else None,
                'width': int(self.window_width_entry.get_text()) if self.window_width_entry.get_text() else None,
                'height': int(self.window_height_entry.get_text()) if self.window_height_entry.get_text() else None,
                'state': self.window_state_combo.get_active_text().lower()
            }
            
            self.on_property_changed(self.current_item_id, 'window_state', window_state)
        except ValueError:
            pass  # Ignore invalid numbers
    
    def _on_script_dialog(self, button):
        """Open script selection dialog (NEW)"""
        if not self.db:
            return
        
        # Create dialog
        dialog = Gtk.Dialog(
            title="Select Script",
            parent=None,
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            "Select", Gtk.ResponseType.OK
        )
        
        dialog.set_default_size(400, 300)
        
        # Create list store
        list_store = Gtk.ListStore(str, str)  # name, id
        scripts = self.db.get_all_scripts()
        for script in scripts:
            list_store.append([script['name'], str(script['id'])])
        
        # Create tree view
        tree_view = Gtk.TreeView(model=list_store)
        
        # Add column
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Script Name", renderer, text=0)
        tree_view.append_column(column)
        
        # Add to scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(tree_view)
        
        content = dialog.get_content_area()
        content.pack_start(scrolled, True, True, 0)
        
        dialog.show_all()
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            selection = tree_view.get_selection()
            model, treeiter = selection.get_selected()
            if treeiter:
                script_name = model[treeiter][0]
                self.command_entry.set_text(f"@{script_name}")
                self._on_command_changed(self.command_entry)
        
        dialog.destroy()
    
    def _on_pick_icon(self, button):
        """Open file chooser for icon selection"""
        dialog = Gtk.FileChooserDialog(
            title="Select Icon",
            parent=None,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        
        # Add image filters
        filter_img = Gtk.FileFilter()
        filter_img.set_name("Image files")
        filter_img.add_mime_type("image/png")
        filter_img.add_mime_type("image/jpeg")
        filter_img.add_mime_type("image/svg+xml")
        filter_img.add_mime_type("image/x-icon")
        filter_img.add_pattern("*.png")
        filter_img.add_pattern("*.jpg")
        filter_img.add_pattern("*.jpeg")
        filter_img.add_pattern("*.svg")
        filter_img.add_pattern("*.ico")
        dialog.add_filter(filter_img)
        
        filter_all = Gtk.FileFilter()
        filter_all.set_name("All files")
        filter_all.add_pattern("*")
        dialog.add_filter(filter_all)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            self.icon_entry.set_text(filename)
            self._on_icon_changed(self.icon_entry)
        
        dialog.destroy()

    def _on_tile_clicked(self, button):
        """Tile window alongside the last positioned window"""
        if not self.current_item_id or not self.on_property_changed:
            return

        # This would need access to the model to find last positioned window
        # For now, just show a message - real implementation is in debug window
        print("⎔ Tile feature available in Debug window")
        # In practice, we'd need to pass model reference to property panel
