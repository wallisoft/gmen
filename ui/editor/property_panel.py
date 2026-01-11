"""
Property Panel - Matching three-panel styling
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf
import os


class PropertyPanel:
    def __init__(self, db=None):
        self.db = db
        self.on_property_changed = None
        self.current_item_id = None
        self.current_instance_idx = 0
        
        self._is_loading = False
        self._create_widgets()
    
    def _create_widgets(self):
        """Create ALL property widgets with matching styling"""
        # Title (item-level)
        self.title_entry = Gtk.Entry()
        self.title_entry.set_placeholder_text("Menu Item Title")
        self.title_entry.connect("changed", self._on_title_changed)
        
        # Command with hamburger button
        command_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.command_entry = Gtk.Entry()
        self.command_entry.set_placeholder_text("Command or @scriptname")
        self.command_entry.connect("changed", self._on_command_changed)
        
        # Hamburger button for scripts
        self.script_btn = Gtk.Button.new_with_label("☰")
        self.script_btn.set_tooltip_text("Script Editor")
        self.script_btn.set_size_request(40, -1)
        self.script_btn.connect("clicked", self._on_script_clicked)
        
        command_box.pack_start(self.command_entry, True, True, 0)
        command_box.pack_start(self.script_btn, False, False, 0)
        self.command_container = command_box
        
        # Icon with hamburger button
        icon_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.icon_entry = Gtk.Entry()
        self.icon_entry.set_placeholder_text("icon-name or /path/to/icon")
        self.icon_entry.connect("changed", self._on_icon_changed)
        
        # Hamburger button for icon picker
        self.icon_picker_btn = Gtk.Button.new_with_label("☰")
        self.icon_picker_btn.set_tooltip_text("Icon Picker")
        self.icon_picker_btn.set_size_request(40, -1)
        self.icon_picker_btn.connect("clicked", self._on_icon_picker_clicked)
        
        self.icon_preview = Gtk.Image()
        self.icon_preview.set_size_request(24, 24)
        
        icon_box.pack_start(self.icon_entry, True, True, 0)
        icon_box.pack_start(self.icon_picker_btn, False, False, 0)
        icon_box.pack_start(self.icon_preview, False, False, 5)
        self.icon_container = icon_box
        
        # Window positioning header with checkbox inline
        window_header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        # Label
        window_label = Gtk.Label()
        window_label.set_markup("<b>Window Positioning</b>")
        window_label.set_xalign(0)
        
        # Checkbox with spaces
        self.enable_cb = Gtk.CheckButton(label="  Enable")
        self.enable_cb.set_active(True)
        self.enable_cb.connect("toggled", self._on_enable_changed)
        
        window_header_box.pack_start(window_label, False, False, 0)
        window_header_box.pack_start(self.enable_cb, False, False, 0)
        window_header_box.pack_start(Gtk.Label(), True, True, 0)  # Spacer
        
        self.window_header = window_header_box
        
        # Window positioning grid (ALWAYS VISIBLE)
        grid = Gtk.Grid()
        grid.set_column_spacing(5)
        grid.set_row_spacing(5)
        
        # Position
        grid.attach(Gtk.Label(label="X:"), 0, 0, 1, 1)
        self.x_entry = Gtk.Entry()
        self.x_entry.set_placeholder_text("0")
        self.x_entry.set_width_chars(6)
        self.x_entry.connect("changed", self._on_window_changed)
        grid.attach(self.x_entry, 1, 0, 1, 1)
        
        grid.attach(Gtk.Label(label="Y:"), 2, 0, 1, 1)
        self.y_entry = Gtk.Entry()
        self.y_entry.set_placeholder_text("0")
        self.y_entry.set_width_chars(6)
        self.y_entry.connect("changed", self._on_window_changed)
        grid.attach(self.y_entry, 3, 0, 1, 1)
        
        # Size
        grid.attach(Gtk.Label(label="W:"), 0, 1, 1, 1)
        self.w_entry = Gtk.Entry()
        self.w_entry.set_placeholder_text("800")
        self.w_entry.set_width_chars(6)
        self.w_entry.connect("changed", self._on_window_changed)
        grid.attach(self.w_entry, 1, 1, 1, 1)
        
        grid.attach(Gtk.Label(label="H:"), 2, 1, 1, 1)
        self.h_entry = Gtk.Entry()
        self.h_entry.set_placeholder_text("600")
        self.h_entry.set_width_chars(6)
        self.h_entry.connect("changed", self._on_window_changed)
        grid.attach(self.h_entry, 3, 1, 1, 1)
        
        # Display & State
        grid.attach(Gtk.Label(label="Display:"), 0, 2, 1, 1)
        self.display_entry = Gtk.Entry()
        self.display_entry.set_placeholder_text("0")
        self.display_entry.set_width_chars(4)
        self.display_entry.connect("changed", self._on_window_changed)
        grid.attach(self.display_entry, 1, 2, 1, 1)
        
        grid.attach(Gtk.Label(label="State:"), 2, 2, 1, 1)
        self.state_combo = Gtk.ComboBoxText()
        for state in ["Normal", "Maximized", "Minimized", "Fullscreen"]:
            self.state_combo.append_text(state)
        self.state_combo.set_active(0)
        self.state_combo.connect("changed", self._on_window_changed)
        grid.attach(self.state_combo, 3, 2, 1, 1)
        
        self.window_grid = grid
        
        # Instance selector - compact row
        instance_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        # 2-char instance combo
        self.instance_combo = Gtk.ComboBoxText()
        self.instance_combo.set_size_request(40, -1)  # 2 chars wide
        self.instance_combo.connect("changed", self._on_instance_changed)
        
        self.add_btn = Gtk.Button.new_with_label("+")
        self.add_btn.set_size_request(30, -1)
        self.add_btn.connect("clicked", self._on_add_instance)
        
        self.remove_btn = Gtk.Button.new_with_label("-")
        self.remove_btn.set_size_request(30, -1)
        self.remove_btn.connect("clicked", self._on_remove_instance)
        
        # Positioning Tool button
        self.positioning_btn = Gtk.Button.new_with_label("Positioning Tool")
        self.positioning_btn.connect("clicked", self._on_positioning_tool)
        
        instance_box.pack_start(self.instance_combo, False, False, 0)
        instance_box.pack_start(self.add_btn, False, False, 0)
        instance_box.pack_start(self.remove_btn, False, False, 0)
        instance_box.pack_start(Gtk.Label(), True, True, 0)  # Spacer
        instance_box.pack_start(self.positioning_btn, False, False, 0)
        
        self.instance_container = instance_box
    
    # === EVENT HANDLERS (same as before) ===
    
    def _on_title_changed(self, entry):
        if not self._is_loading and self.current_item_id and self.on_property_changed:
            self.on_property_changed(self.current_item_id, 'title', entry.get_text())
    
    def _on_command_changed(self, entry):
        if not self._is_loading and self.current_item_id and self.on_property_changed:
            self.on_property_changed(
                self.current_item_id, 'command', entry.get_text(),
                instance_idx=self.current_instance_idx
            )
    
    def _on_icon_changed(self, entry):
        if not self._is_loading and self.current_item_id and self.on_property_changed:
            icon = entry.get_text()
            self._update_preview(icon)
            self.on_property_changed(
                self.current_item_id, 'icon', icon,
                instance_idx=self.current_instance_idx
            )
    
    def _on_enable_changed(self, checkbox):
        if not self._is_loading and self.current_item_id and self.on_property_changed:
            self.on_property_changed(
                self.current_item_id, 'enable_positioning', checkbox.get_active(),
                instance_idx=self.current_instance_idx
            )
    
    def _on_window_changed(self, widget):
        if self._is_loading or not self.current_item_id or not self.on_property_changed:
            return
        
        try:
            window_state = {
                'x': int(self.x_entry.get_text()) if self.x_entry.get_text().strip() else None,
                'y': int(self.y_entry.get_text()) if self.y_entry.get_text().strip() else None,
                'width': int(self.w_entry.get_text()) if self.w_entry.get_text().strip() else None,
                'height': int(self.h_entry.get_text()) if self.h_entry.get_text().strip() else None,
                'display': int(self.display_entry.get_text()) if self.display_entry.get_text().strip() else 0,
                'state': self.state_combo.get_active_text().lower()
            }
            
            self.on_property_changed(
                self.current_item_id, 'window_state', window_state,
                instance_idx=self.current_instance_idx
            )
        except ValueError:
            pass
    
    def _on_instance_changed(self, combo):
        if self._is_loading:
            return
        
        idx = combo.get_active()
        if idx >= 0:
            self.current_instance_idx = idx
            # Reload data for this instance
            if self.on_property_changed:
                self.on_property_changed(
                    self.current_item_id, 'switch_instance', idx,
                    instance_idx=idx
                )
    
    def _on_add_instance(self, button):
        if self.current_item_id and self.on_property_changed:
            self.on_property_changed(
                self.current_item_id, 'add_instance', None,
                instance_idx=self.current_instance_idx
            )
    
    def _on_remove_instance(self, button):
        if self.current_item_id and self.on_property_changed:
            self.on_property_changed(
                self.current_item_id, 'remove_instance', self.current_instance_idx,
                instance_idx=self.current_instance_idx
            )
    
    def _on_script_clicked(self, button):
        """Hamburger button for script editor"""
        print("📝 Script Editor clicked (stub)")
        # TODO: Open script editor dialog
    
    def _on_icon_picker_clicked(self, button):
        """Hamburger button for icon picker"""
        print("🎨 Icon Picker clicked (stub)")
        # TODO: Open icon picker dialog
    
    def _on_positioning_tool(self, button):
        """Positioning Tool button"""
        print("🪟 Positioning Tool clicked (stub)")
        # TODO: Open positioning tool
    
    def _update_preview(self, icon):
        """Update icon preview"""
        if not icon:
            self.icon_preview.clear()
            return
        
        try:
            theme = Gtk.IconTheme.get_default()
            if theme.has_icon(icon):
                self.icon_preview.set_from_icon_name(icon, Gtk.IconSize.BUTTON)
                return
        except:
            pass
        
        if os.path.exists(icon):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon, 24, 24)
                self.icon_preview.set_from_pixbuf(pixbuf)
            except:
                self.icon_preview.clear()
        else:
            self.icon_preview.clear()
    
    # === PUBLIC API ===
    
    def load_item(self, item):
        """Load item with its instances"""
        self._is_loading = True
        self.current_item_id = item['id'] if isinstance(item, dict) else item.id
        
        # Load title
        title = item['title'] if isinstance(item, dict) else item.title
        self.title_entry.set_text(title)
        
        # Get instances
        instances = []
        if isinstance(item, dict) and 'instances' in item:
            instances = item['instances']
        elif hasattr(item, 'instances'):
            instances = item.instances
        
        # Update instance combo (2-char display)
        self.instance_combo.remove_all()
        if instances:
            for i in range(len(instances)):
                # Show "1", "2", etc. - always 1 or 2 chars
                self.instance_combo.append_text(str(i + 1))
            
            self.instance_combo.set_active(0)
            self.current_instance_idx = 0
            self._load_instance_data(instances[0])
        else:
            # Should never happen, but handle it
            self.instance_combo.append_text("1")
            self.instance_combo.set_active(0)
            self.current_instance_idx = 0
            self._clear_fields()
        
        self._is_loading = False
    
    def _load_instance_data(self, instance):
        """Load data for a specific instance"""
        # Basic fields
        self.command_entry.set_text(instance.get('command', ''))
        self.icon_entry.set_text(instance.get('icon', ''))
        self._update_preview(instance.get('icon', ''))
        
        # Enable positioning
        self.enable_cb.set_active(bool(instance.get('enable_positioning', True)))
        
        # Window state
        ws = instance.get('window_state')
        if ws:
            self.x_entry.set_text(str(ws.get('x', '')))
            self.y_entry.set_text(str(ws.get('y', '')))
            self.w_entry.set_text(str(ws.get('width', '')))
            self.h_entry.set_text(str(ws.get('height', '')))
            self.display_entry.set_text(str(ws.get('display', 0)))
            
            state = ws.get('state', 'normal').lower()
            state_map = {'normal': 0, 'maximized': 1, 'minimized': 2, 'fullscreen': 3}
            self.state_combo.set_active(state_map.get(state, 0))
        else:
            self._clear_window_fields()
    
    def _clear_fields(self):
        """Clear all fields"""
        self.title_entry.set_text("")
        self.command_entry.set_text("")
        self.icon_entry.set_text("")
        self.icon_preview.clear()
        self.enable_cb.set_active(True)
        self._clear_window_fields()
    
    def _clear_window_fields(self):
        """Clear window fields"""
        self.x_entry.set_text("")
        self.y_entry.set_text("")
        self.w_entry.set_text("")
        self.h_entry.set_text("")
        self.display_entry.set_text("0")
        self.state_combo.set_active(0)
    
    def create_panel(self):
        """Create the complete property panel with matching styling"""
        # Create the main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        
        # Header label (matching three-panel style)
        header = Gtk.Label()
        header.set_markup("<b>-  Properties  -</b>")
        header.set_xalign(0)
        main_box.pack_start(header, False, False, 0)
        
        # Frame with 2px border and radius
        frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        frame.get_style_context().add_class("panel-frame")
        frame.get_style_context().add_class("inactive-panel")
        
        # Content inside frame
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content.set_margin_top(8)
        content.set_margin_bottom(8)
        content.set_margin_start(8)
        content.set_margin_end(8)
        
        # Helper to add sections with labels
        def add_section(title, widget):
            lbl = Gtk.Label()
            lbl.set_markup(f"<b>{title}</b>")
            lbl.set_xalign(0)
            content.pack_start(lbl, False, False, 0)
            content.pack_start(widget, False, False, 2)
        
        # Add sections
        add_section("Title", self.title_entry)
        add_section("Command", self.command_container)
        add_section("Icon", self.icon_container)
        
        # Separator after icon
        sep1 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep1.set_margin_top(4)
        sep1.set_margin_bottom(4)
        content.pack_start(sep1, False, False, 0)
        
        # Window positioning header (with inline checkbox)
        content.pack_start(self.window_header, False, False, 0)
        content.pack_start(self.window_grid, False, False, 0)
        
        # Separator before instances
        sep2 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep2.set_margin_top(8)
        sep2.set_margin_bottom(4)
        content.pack_start(sep2, False, False, 0)
        
        # Instances label
        instances_label = Gtk.Label()
        instances_label.set_markup("<b>Instances</b>")
        instances_label.set_xalign(0)
        content.pack_start(instances_label, False, False, 0)
        
        # Instances controls
        content.pack_start(self.instance_container, False, False, 0)
        
        # Add content to frame
        frame.pack_start(content, True, True, 0)
        
        # Add frame to main box
        main_box.pack_start(frame, True, True, 0)
        
        return main_box
    
    def create_panel_contents(self):
        """Legacy method - use create_panel() instead"""
        return self.create_panel()

    def clear(self):
        """Clear all fields and reset state"""
        self._is_loading = True
        self.current_item_id = None
        self.current_instance_idx = 0

        self.title_entry.set_text("")
        self.command_entry.set_text("")
        self.icon_entry.set_text("")
        self.icon_preview.clear()
        self.enable_cb.set_active(True)
        self._clear_window_fields()

        # Clear instance combo
        self.instance_combo.remove_all()

        self._is_loading = False
