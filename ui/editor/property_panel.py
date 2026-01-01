"""
Property editing panel for menu items
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class PropertyPanel:
    """Property editing panel with window state controls"""
    
    def __init__(self):
        self.current_item_id = None
        self.on_changed = None  # Callback: func(item_id, field, value)
    
    def create_panel(self):
        """Create the properties panel"""
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
        
        # Command
        vbox.pack_start(Gtk.Label(label="Command:"), False, False, 0)
        self.cmd_entry = Gtk.Entry()
        self.cmd_entry.connect("changed", self.on_cmd_changed)
        vbox.pack_start(self.cmd_entry, False, False, 0)
        
        # Icon
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
        for entry in [self.x_entry, self.y_entry, self.width_entry, 
                     self.height_entry, self.monitor_entry]:
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
        
        # Info label
        self.info_label = Gtk.Label()
        self.info_label.set_line_wrap(True)
        vbox.pack_start(self.info_label, True, True, 0)
        
        frame.add(vbox)
        return frame
    
    def load_item(self, item_id, db):
        """Load item properties from database"""
        self.current_item_id = item_id
        
        item = db.fetch_one("""
            SELECT title, command, icon FROM menu_items WHERE id = ?
        """, (item_id,))
        
        if item:
            self.title_entry.set_text(item['title'] or "")
            self.cmd_entry.set_text(item['command'] or "")
            self.icon_entry.set_text(item['icon'] or "")
        
        # Load window state
        window_state = db.fetch_one("""
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
            self.clear_window_state()
        
        # Enable/disable window state entries
        self.on_window_enable_toggled(self.window_enable_check)
        
        self.update_info(item_id)
    
    def clear(self):
        """Clear all property fields"""
        self.current_item_id = None
        self.title_entry.set_text("")
        self.cmd_entry.set_text("")
        self.icon_entry.set_text("")
        self.window_enable_check.set_active(False)
        self.clear_window_state()
        self.info_label.set_text("Select an item to edit")
    
    def clear_window_state(self):
        """Clear window state fields"""
        self.x_entry.set_text("")
        self.y_entry.set_text("")
        self.width_entry.set_text("")
        self.height_entry.set_text("")
        self.monitor_entry.set_text("")
    
    def update_info(self, item_id):
        """Update info label"""
        self.info_label.set_text(f"Item ID: {item_id}")
    
    def on_title_changed(self, entry):
        if self.current_item_id and self.on_changed:
            self.on_changed(self.current_item_id, 'title', entry.get_text())
    
    def on_cmd_changed(self, entry):
        if self.current_item_id and self.on_changed:
            self.on_changed(self.current_item_id, 'command', entry.get_text())
    
    def on_icon_changed(self, entry):
        if self.current_item_id and self.on_changed:
            self.on_changed(self.current_item_id, 'icon', entry.get_text())
    
    def on_window_enable_toggled(self, check):
        enabled = check.get_active()
        for entry in [self.x_entry, self.y_entry, self.width_entry, 
                     self.height_entry, self.monitor_entry]:
            entry.set_sensitive(enabled)
        
        if self.current_item_id and not enabled and self.on_changed:
            # Window state disabled - clear values
            self.clear_window_state()
            self.on_changed(self.current_item_id, 'window_state', None)
    
    def on_window_state_changed(self, entry):
        if self.current_item_id and self.on_changed:
            # Collect all window state values
            window_state = {
                'x': self.get_int_or_none(self.x_entry.get_text()),
                'y': self.get_int_or_none(self.y_entry.get_text()),
                'width': self.get_int_or_none(self.width_entry.get_text()),
                'height': self.get_int_or_none(self.height_entry.get_text()),
                'monitor': self.get_int_or_none(self.monitor_entry.get_text()),
                'enabled': self.window_enable_check.get_active()
            }
            self.on_changed(self.current_item_id, 'window_state', window_state)
    
    def get_int_or_none(self, text):
        """Convert text to int or return None"""
        text = str(text).strip()
        if text and text.replace('-', '', 1).isdigit():
            return int(text)
        return None
