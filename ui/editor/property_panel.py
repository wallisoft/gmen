"""
Property panel with script dialog, window controls, and instance management
Cleaned up - no exit button
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GLib
import os
import subprocess
from typing import Optional


class PropertyPanel:
    """Enhanced property panel with script dialog, window controls, and instance management"""
    
    def __init__(self, db=None):
        self.db = db
        self.on_property_changed = None
        self.current_item_id = None
        self.current_instance_id = None
        
        # Flag to prevent event loops
        self._is_loading = False
        
        # UI widgets
        self.title_entry = None
        self.command_entry = None
        self.command_button = None
        self.icon_entry = None
        self.icon_button = None
        self.icon_preview = None
        
        # Window controls
        self.remember_window_cb = None
        self.window_x_entry = None
        self.window_y_entry = None
        self.window_width_entry = None
        self.window_height_entry = None
        self.window_state_combo = None
        
        # Instance management
        self.instance_combo = None
        self.instance_plus_btn = None
        self.instance_minus_btn = None
        
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
        
        self.command_button = Gtk.Button(label="📝 Script")
        self.command_button.set_tooltip_text("Select or edit scripts")
        self.command_button.set_size_request(100, -1)
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
        
        # Window positioning checkbox - no text, inline with label
        self.remember_window_cb = Gtk.CheckButton()
        self.remember_window_cb.set_tooltip_text("Remember window position")
        self.remember_window_cb.connect("toggled", self._on_window_remember_toggled)
        
        # Window positioning header with checkbox inline
        window_header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        window_label = Gtk.Label()
        window_label.set_markup("<b>Window Position</b>")
        window_label.set_xalign(0)
        window_header_box.pack_start(window_label, False, False, 0)
        window_header_box.pack_start(self.remember_window_cb, False, False, 0)
        window_header_box.pack_start(Gtk.Label(), True, True, 0)  # Spacer
        
        self.window_header_container = window_header_box
        
        # Window positioning controls
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
        
        # Instance management - compact 2-char combo
        self.instance_combo = Gtk.ComboBoxText()
        self.instance_combo.set_tooltip_text("Window instance")
        self.instance_combo.set_size_request(30, -1)
        self.instance_combo.connect("changed", self._on_instance_changed)
        
        self.instance_plus_btn = Gtk.Button.new_with_label("+")
        self.instance_plus_btn.set_tooltip_text("Add instance")
        self.instance_plus_btn.set_size_request(25, -1)
        self.instance_plus_btn.connect("clicked", self._on_add_instance)
        
        self.instance_minus_btn = Gtk.Button.new_with_label("-")
        self.instance_minus_btn.set_tooltip_text("Delete current instance")
        self.instance_minus_btn.set_size_request(25, -1)
        self.instance_minus_btn.connect("clicked", self._on_remove_instance)
    
    # === PROPERTY HANDLERS ===
    
    def _on_title_changed(self, entry):
        """Handle title change"""
        if not self._is_loading and self.current_item_id and self.on_property_changed:
            new_title = entry.get_text()
            self.on_property_changed(self.current_item_id, 'title', new_title)
    
    def _on_command_changed(self, entry):
        """Handle command change"""
        if not self._is_loading and self.current_item_id and self.on_property_changed:
            new_command = entry.get_text()
            self.on_property_changed(self.current_item_id, 'command', new_command)
    
    def _on_icon_changed(self, entry):
        """Handle icon change"""
        if not self._is_loading and self.current_item_id and self.on_property_changed:
            new_icon = entry.get_text()
            self.on_property_changed(self.current_item_id, 'icon', new_icon)
            self._update_icon_preview(new_icon)
    
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
    
    def _on_window_remember_toggled(self, checkbox):
        """Handle window position remembering toggle"""
        enabled = checkbox.get_active()
        
        # Enable/disable window controls
        self.window_x_entry.set_sensitive(enabled)
        self.window_y_entry.set_sensitive(enabled)
        self.window_width_entry.set_sensitive(enabled)
        self.window_height_entry.set_sensitive(enabled)
        self.window_state_combo.set_sensitive(enabled)
        
        if not self._is_loading and self.current_item_id and self.on_property_changed:
            if not enabled:
                # Clear window state when checkbox is unchecked
                self.on_property_changed(self.current_item_id, 'window_state', None, 
                                       instance_idx=self.instance_combo.get_active())
    
    def _on_window_changed(self, widget):
        """Handle window control changes"""
        if self._is_loading or not self.current_item_id or not self.on_property_changed:
            return
        
        # Only send updates if checkbox is checked
        if not self.remember_window_cb.get_active():
            return
        
        try:
            window_state = {
                'x': int(self.window_x_entry.get_text()) if self.window_x_entry.get_text() else None,
                'y': int(self.window_y_entry.get_text()) if self.window_y_entry.get_text() else None,
                'width': int(self.window_width_entry.get_text()) if self.window_width_entry.get_text() else None,
                'height': int(self.window_height_entry.get_text()) if self.window_height_entry.get_text() else None,
                'state': self.window_state_combo.get_active_text().lower()
            }
            
            # Get instance number from combo
            instance_idx = self.instance_combo.get_active()
            if instance_idx >= 0:
                self.on_property_changed(self.current_item_id, 'window_state', window_state, 
                                       instance_idx=instance_idx)
        except ValueError:
            pass  # Ignore invalid numbers
    
    # === INSTANCE HANDLERS ===
    
    def _on_instance_changed(self, combo):
        """Handle instance selection change"""
        if self._is_loading:
            return
        
        # For now, just clear fields when switching instances
        self._clear_window_fields()
        
        idx = self.instance_combo.get_active()
        if idx >= 0:
            print(f"🔄 Switched to instance {idx + 1}")
    
    def _on_add_instance(self, button):
        """Add new instance below current - UI only"""
        current_count = self.instance_combo.get_model().iter_n_children(None)
        
        if current_count == 0:
            # First time
            self.instance_combo.remove_all()
            self.instance_combo.append_text("1")
            self.instance_combo.append_text("2")
            self.instance_combo.set_active(1)
            print("➕ Added instance 2")
        else:
            # Add next number
            next_num = current_count + 1
            self.instance_combo.append_text(f"{next_num}")
            self.instance_combo.set_active(next_num - 1)
            print(f"➕ Added instance {next_num}")
        
        self._clear_window_fields()
        if self.current_item_id and self.on_property_changed:
            self.on_property_changed(self.current_item_id, 'add_instance', None)
    
    def _on_remove_instance(self, button):
        """Remove current instance and renumber"""
        active_idx = self.instance_combo.get_active()
        if active_idx < 0:
            return
        
        # Get all current texts
        model = self.instance_combo.get_model()
        texts = []
        it = model.get_iter_first()
        while it:
            texts.append(model.get_value(it, 0))
            it = model.iter_next(it)
        
        print(f"📊 Before remove: {texts}, active_idx: {active_idx}")
        
        # Remove the selected one
        if active_idx < len(texts):
            removed_text = texts.pop(active_idx)
            print(f"🗑️  Removing: {removed_text}")
        
        print(f"📊 After remove: {texts}")
        
        # Clear and re-add renumbered
        self.instance_combo.remove_all()
        for i in range(len(texts)):
            self.instance_combo.append_text(f"{i + 1}")
        
        # Select appropriate one
        if texts:
            new_idx = min(active_idx, len(texts) - 1)
            self.instance_combo.set_active(new_idx)
            print(f"✅ Removed instance {active_idx + 1}, {len(texts)} remaining (renumbered 1-{len(texts)})")
        else:
            # All gone, add "1" back
            self.instance_combo.append_text("1")
            self.instance_combo.set_active(0)
            print("🔄 Reset to instance 1")
        
        self._clear_window_fields()
        if self.current_item_id and self.on_property_changed:
            self.on_property_changed(self.current_item_id, 'remove_instance', active_idx)
    
    def _clear_window_fields(self):
        """Clear window position fields"""
        self.window_x_entry.set_text("")
        self.window_y_entry.set_text("")
        self.window_width_entry.set_text("")
        self.window_height_entry.set_text("")
        self.window_state_combo.set_active(0)
        self.remember_window_cb.set_active(False)
    
    # === DIALOG METHODS ===
    
    def _on_script_dialog(self, button):
        """Open script selection AND editor"""
        if not self.db:
            return
        
        # First get list of scripts
        scripts = self.db.get_all_scripts()
        
        # Create dialog with buttons for both actions
        dialog = Gtk.Dialog(
            title="Scripts",
            parent=None,
            flags=0
        )
        dialog.add_buttons(
            "Cancel", Gtk.ResponseType.CANCEL,
            "Select", Gtk.ResponseType.OK,
            "Edit/Create", 100  # Custom response
        )
        
        dialog.set_default_size(500, 400)
        
        # Create list of scripts
        list_store = Gtk.ListStore(str, str)  # name, id
        for script in scripts:
            list_store.append([script['name'], str(script['id'])])
        
        # Add "New Script..." option
        list_store.append(["➕ Create New Script...", "-1"])
        
        tree_view = Gtk.TreeView(model=list_store)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Script Name", renderer, text=0)
        tree_view.append_column(column)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(tree_view)
        
        content = dialog.get_content_area()
        content.pack_start(scrolled, True, True, 0)
        
        dialog.show_all()
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            # Select existing script
            selection = tree_view.get_selection()
            model, treeiter = selection.get_selected()
            if treeiter:
                script_name = model[treeiter][0]
                script_id = model[treeiter][1]
                
                if script_id == "-1":  # Create new
                    # Launch script editor
                    self._launch_script_editor()
                else:
                    self.command_entry.set_text(f"@{script_name}")
                    self._on_command_changed(self.command_entry)
        
        elif response == 100:  # Edit/Create
            # Launch script editor
            self._launch_script_editor()
        
        dialog.destroy()
    
    def _launch_script_editor(self):
        """Launch the script editor"""
        try:
            script_path = "gmen_script_editor.py"
            if os.path.exists(script_path):
                subprocess.Popen(["python3", script_path])
            else:
                print(f"⚠️ Script editor not found: {script_path}")
        except Exception as e:
            print(f"❌ Failed to launch script editor: {e}")
    
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
    
    def _on_positioning_tool(self, button):
        """Open positioning tool window"""
        print("🪟 Positioning Tool clicked - would open positioning window")
        # TODO: Implement positioning tool window
    
    # === UI CREATION ===
    
    def create_panel(self):
        """Create the property panel frame - clean and compact"""
        frame = Gtk.Frame(label="⚙️ Properties")
        frame.set_shadow_type(Gtk.ShadowType.IN)
        frame.set_size_request(350, -1)
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_margin_top(8)
        vbox.set_margin_bottom(8)
        vbox.set_margin_start(8)
        vbox.set_margin_end(8)
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
        
        # Window positioning with inline checkbox
        vbox.pack_start(self.window_header_container, False, False, 10)
        vbox.pack_start(self.window_container, False, False, 0)
        
        # Action buttons: Instances + Tile on same line
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        # Instance controls
        instance_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        instance_box.pack_start(self.instance_combo, False, False, 0)
        instance_box.pack_start(self.instance_plus_btn, False, False, 0)
        instance_box.pack_start(self.instance_minus_btn, False, False, 0)
        
        # Positioning Tool button
        tile_btn = Gtk.Button.new_with_label("Positioning Tool")
        tile_btn.set_tooltip_text("Open window positioning tool")
        tile_btn.connect("clicked", self._on_positioning_tool)
        
        action_box.pack_start(instance_box, False, False, 0)
        action_box.pack_start(tile_btn, True, True, 0)
        
        vbox.pack_start(self._create_label("Actions"), False, False, 10)
        vbox.pack_start(action_box, False, False, 0)
        
        # Expand
        vbox.pack_start(Gtk.Label(), True, True, 0)
        
        return frame
    
    def _create_label(self, text):
        """Create a section label"""
        label = Gtk.Label(label=f"<b>{text}</b>")
        label.set_use_markup(True)
        label.set_xalign(0)
        return label
    
    def load_item(self, item):
        """Load item with its current instance data"""
        self._is_loading = True
        self.current_item_id = item['id'] if isinstance(item, dict) else item.id
        self.current_item = item  # Store the item object
        
        # Load basic item properties (title is same for all instances)
        title = item['title'] if isinstance(item, dict) else item.title
        self.title_entry.set_text(title)
        
        # Get instances from item
        instances = []
        if isinstance(item, dict) and 'instances' in item:
            instances = item['instances']
        elif hasattr(item, 'instances'):
            instances = item.instances
        
        # Load FIRST instance's data by default
        if instances:
            instance = instances[0]
            self.command_entry.set_text(instance.get('command', ''))
            self.icon_entry.set_text(instance.get('icon', ''))
            
            # Load window state if exists
            if instance.get('window_state'):
                ws = instance['window_state']
                self.window_x_entry.set_text(str(ws.get('x', '')))
                self.window_y_entry.set_text(str(ws.get('y', '')))
                self.window_width_entry.set_text(str(ws.get('width', '')))
                self.window_height_entry.set_text(str(ws.get('height', '')))
                
                state_val = ws.get('state', 'normal').lower()
                if state_val == 'maximized':
                    self.window_state_combo.set_active(1)
                elif state_val == 'minimized':
                    self.window_state_combo.set_active(2)
                elif state_val == 'fullscreen':
                    self.window_state_combo.set_active(3)
                else:
                    self.window_state_combo.set_active(0)
                
                self.remember_window_cb.set_active(True)
            else:
                self._clear_window_fields()
        else:
            # No instances yet
            self.command_entry.set_text('')
            self.icon_entry.set_text('')
            self._clear_window_fields()
        
        self._update_icon_preview(self.icon_entry.get_text())
        
        # Update instance combo based on number of instances
        self.instance_combo.remove_all()
        num_instances = len(instances) if instances else 1
        for i in range(num_instances):
            self.instance_combo.append_text(f"{i + 1}")
        
        self.instance_combo.set_active(0)
        
        self._is_loading = False
        print(f"📋 PropertyPanel loaded item '{title}' with {num_instances} instances")

    def _load_window_state_for_current_instance(self):
        """Load window state for currently selected instance"""
        if not hasattr(self, 'current_item') or not self.current_item:
            self._clear_window_fields()
            return
        
        idx = self.instance_combo.get_active()
        if idx < 0:
            self._clear_window_fields()
            return
        
        # Get instances from item
        instances = []
        if isinstance(self.current_item, dict) and 'instances' in self.current_item:
            instances = self.current_item['instances']
        elif hasattr(self.current_item, 'instances'):
            instances = self.current_item.instances
        
        if idx < len(instances):
            instance = instances[idx]
            
            if instance.get('window_state'):
                ws = instance['window_state']
                self.window_x_entry.set_text(str(ws.get('x', '')))
                self.window_y_entry.set_text(str(ws.get('y', '')))
                self.window_width_entry.set_text(str(ws.get('width', '')))
                self.window_height_entry.set_text(str(ws.get('height', '')))
                
                state_val = ws.get('state', 'normal').lower()
                if state_val == 'maximized':
                    self.window_state_combo.set_active(1)
                elif state_val == 'minimized':
                    self.window_state_combo.set_active(2)
                elif state_val == 'fullscreen':
                    self.window_state_combo.set_active(3)
                else:
                    self.window_state_combo.set_active(0)
                
                self.remember_window_cb.set_active(True)
                print(f"📤 Loaded window state for instance {idx + 1}")
            else:
                self._clear_window_fields()
                print(f"📭 No window state saved for instance {idx + 1}")
        else:
            self._clear_window_fields()

    def _on_instance_changed(self, combo):
        """Handle instance selection change - load that instance's window state"""
        if self._is_loading:
            return
        
        idx = self.instance_combo.get_active()
        if idx >= 0 and hasattr(self, 'current_item'):
            print(f"🔄 Switching to instance {idx + 1}")
            self._load_window_state_for_current_instance()
    
    def clear(self):
        """Clear the panel"""
        self._is_loading = True
        self.current_item_id = None
        
        self.title_entry.set_text("")
        self.command_entry.set_text("")
        self.icon_entry.set_text("")
        self.icon_preview.clear()
        
        self.instance_combo.remove_all()
        self._clear_window_fields()
        
        self._is_loading = False
    
    def create_panel_contents(self):
        """Create just the contents (for external framing) - simplified"""
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_margin_top(8)
        vbox.set_margin_bottom(8)
        vbox.set_margin_start(8)
        vbox.set_margin_end(8)
        
        vbox.pack_start(self._create_label("Title"), False, False, 0)
        vbox.pack_start(self.title_entry, False, False, 0)
        vbox.pack_start(self._create_label("Command"), False, False, 5)
        vbox.pack_start(self.command_container, False, False, 0)
        vbox.pack_start(self._create_label("Icon"), False, False, 5)
        vbox.pack_start(self.icon_container, False, False, 0)
        vbox.pack_start(self.window_header_container, False, False, 10)
        vbox.pack_start(self.window_container, False, False, 0)
        
        # Action buttons row
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        instance_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        instance_box.pack_start(self.instance_combo, False, False, 0)
        instance_box.pack_start(self.instance_plus_btn, False, False, 0)
        instance_box.pack_start(self.instance_minus_btn, False, False, 0)
        
        tile_btn = Gtk.Button.new_with_label("Positioning Tool")
        tile_btn.connect("clicked", self._on_positioning_tool)
        
        action_box.pack_start(instance_box, False, False, 0)
        action_box.pack_start(tile_btn, True, True, 0)
        
        vbox.pack_start(self._create_label("Actions"), False, False, 10)
        vbox.pack_start(action_box, False, False, 0)
        vbox.pack_start(Gtk.Box(), True, True, 0)
    
        return vbox
