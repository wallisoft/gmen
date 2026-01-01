#!/usr/bin/env python3
"""
Mini Position Debug Window - Shows window positioning with clipboard copy
"""

import gi
import subprocess
import sys
from pathlib import Path

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk

class MiniDebugWindow:
    """Simple version - shows position with clipboard copy"""
    
    def __init__(self):
        self.window = Gtk.Window(title="📍 Position Debug")
        self.window.set_default_size(350, 280)
        self.window.set_position(Gtk.WindowPosition.MOUSE)  # Opens at mouse
        
        # Track geometry
        self.last_pos = None
        self.window.connect("configure-event", self.on_move)
        self.window.connect("destroy", Gtk.main_quit)
        
        # Create main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_margin_top(15)
        main_box.set_margin_bottom(15)
        main_box.set_margin_start(15)
        main_box.set_margin_end(15)
        
        # Title
        title = Gtk.Label()
        title.set_markup("<span size='large' weight='bold'>📍 Window Position Debug</span>")
        main_box.pack_start(title, False, False, 5)
        
        # Info label
        self.info_label = Gtk.Label(label="Drag me to see coordinates!")
        self.info_label.set_line_wrap(True)
        self.info_label.set_selectable(True)
        self.info_label.set_margin_bottom(10)
        main_box.pack_start(self.info_label, True, True, 0)
        
        # Button box
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_homogeneous(True)
        
        # Copy button
        copy_btn = Gtk.Button.new_with_label("📋 Copy")
        copy_btn.connect("clicked", self.copy_to_clipboard)
        button_box.pack_start(copy_btn, True, True, 0)
        
        # Paste to editor button
        paste_btn = Gtk.Button.new_with_label("📝 Editor")
        paste_btn.connect("clicked", self.paste_to_editor)
        button_box.pack_start(paste_btn, True, True, 0)
        
        main_box.pack_start(button_box, False, False, 5)
        
        # Status label
        self.status_label = Gtk.Label(label="")
        self.status_label.set_line_wrap(True)
        self.status_label.set_margin_top(10)
        main_box.pack_start(self.status_label, False, False, 5)
        
        # Format options (radio buttons)
        format_frame = Gtk.Frame(label="Clipboard Format")
        format_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        format_box.set_margin_top(5)
        format_box.set_margin_bottom(5)
        format_box.set_margin_start(10)
        format_box.set_margin_end(10)
        
        # Radio buttons for format
        self.simple_rb = Gtk.RadioButton.new_with_label(None, "Simple (x,y,w,h)")
        self.json_rb = Gtk.RadioButton.new_with_label_from_widget(self.simple_rb, "JSON")
        self.python_rb = Gtk.RadioButton.new_with_label_from_widget(self.simple_rb, "Python Code")
        
        format_box.pack_start(self.simple_rb, False, False, 0)
        format_box.pack_start(self.json_rb, False, False, 0)
        format_box.pack_start(self.python_rb, False, False, 0)
        
        format_frame.add(format_box)
        main_box.pack_start(format_frame, False, False, 10)
        
        self.window.add(main_box)
        self.window.show_all()
        
        # Store current position data
        self.current_data = {
            'x': 0,
            'y': 0,
            'width': 350,
            'height': 280,
            'monitor': 'Unknown'
        }
        
    def on_move(self, widget, event):
        """Update label when window moves"""
        new_pos = (event.x, event.y, event.width, event.height)
        
        if self.last_pos != new_pos:
            self.last_pos = new_pos
            
            # Update current data
            self.current_data['x'] = event.x
            self.current_data['y'] = event.y
            self.current_data['width'] = event.width
            self.current_data['height'] = event.height
            self.current_data['monitor'] = self.get_monitor(event.x, event.y)
            
            # Format text
            text = f"""
<b>Position:</b> ({event.x}, {event.y})
<b>Size:</b> {event.width} × {event.height}
<b>Monitor:</b> {self.current_data['monitor']}
<b>Bottom-Left:</b> ({event.x}, {event.y + event.height})
<b>Center:</b> ({event.x + event.width//2}, {event.y + event.height//2})
"""
            self.info_label.set_markup(text)
        
        return False
    
    def get_monitor(self, x, y):
        """Simple monitor detection"""
        try:
            result = subprocess.run(
                ["xrandr", "--query"],
                capture_output=True, text=True, timeout=1
            )
            
            for line in result.stdout.splitlines():
                if " connected" in line:
                    parts = line.split()
                    name = parts[0]
                    
                    # Find geometry
                    import re
                    geo_match = re.search(r'\d+x\d+\+(\d+)\+(\d+)', line)
                    if geo_match:
                        mon_x = int(geo_match.group(1))
                        mon_y = int(geo_match.group(2))
                        
                        # Check if in this monitor (simplified)
                        if abs(x - mon_x) < 1000:  # Rough check
                            return name
            
            return "Unknown"
        except:
            return "Unknown"
    
    def get_formatted_data(self, format_type="simple"):
        """Return formatted position data based on selected format"""
        x, y, w, h = (self.current_data['x'], self.current_data['y'], 
                     self.current_data['width'], self.current_data['height'])
        monitor = self.current_data['monitor']
        
        if format_type == "json" or self.json_rb.get_active():
            import json
            data = {
                "window_position": {
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h,
                    "monitor": monitor,
                    "bottom_left": [x, y + h],
                    "center": [x + w // 2, y + h // 2]
                }
            }
            return json.dumps(data, indent=2)
        
        elif format_type == "python" or self.python_rb.get_active():
            return f"""# Window Position for Menuing App
x_position = {x}
y_position = {y}
width = {w}
height = {h}
monitor = "{monitor}"

# Bottom-left corner (for taskbars/docks)
bottom_left = ({x}, {y + h})

# Center position
center_x = {x + w // 2}
center_y = {y + h // 2}

# For Gtk window placement
# window.move({x}, {y})
# window.resize({w}, {h})"""
        
        else:  # Simple format
            return f"""Window Position:
X: {x}
Y: {y}
Width: {w}
Height: {h}
Monitor: {monitor}
Bottom-Left: ({x}, {y + h})
Center: ({x + w // 2}, {y + h // 2})"""
    
    def copy_to_clipboard(self, button):
        """Copy position data to clipboard using GTK's clipboard"""
        try:
            # Get formatted data based on selected format
            if self.json_rb.get_active():
                data = self.get_formatted_data("json")
                format_name = "JSON"
            elif self.python_rb.get_active():
                data = self.get_formatted_data("python")
                format_name = "Python code"
            else:
                data = self.get_formatted_data("simple")
                format_name = "simple format"
            
            # Copy to clipboard using GTK
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clipboard.set_text(data, -1)
            
            # Clear status after 3 seconds
            self.status_label.set_markup(f"<span foreground='green'>✓ Copied ({format_name}) to clipboard!</span>")
            GLib.timeout_add(3000, self.clear_status)
            
        except Exception as e:
            self.status_label.set_markup(f"<span foreground='red'>✗ Error: {str(e)}</span>")
    
    def paste_to_editor(self, button):
        """Copy editor-ready Python code to clipboard"""
        try:
            data = self.get_formatted_data("python")
            
            # Copy to clipboard using GTK
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clipboard.set_text(data, -1)
            
            # Show instructions
            instructions = """✓ Python code copied to clipboard!

Now you can:
1. Open your editor
2. Place the cursor where you want the position
3. Press Ctrl+V or right-click → Paste

The code includes variables for:
- Position (x_position, y_position)
- Size (width, height)
- Monitor name
- Bottom-left and center coordinates
- Gtk window placement comments"""
            
            self.status_label.set_text(instructions)
            
        except Exception as e:
            self.status_label.set_markup(f"<span foreground='red'>✗ Error: {str(e)}</span>")
    
    def clear_status(self):
        """Clear the status label"""
        self.status_label.set_text("")
        return False  # Don't run again
    
    def run(self):
        Gtk.main()


if __name__ == "__main__":
    print("📍 Mini Position Debug Window")
    print("-" * 40)
    print("No external dependencies needed!")
    print("Uses GTK's built-in clipboard system.")
    print("-" * 40)
    print("Drag the window to see coordinates update in real-time.")
    print("Use the buttons to copy in different formats.")
    print("-" * 40)
    
    # Start the app
    mini = MiniDebugWindow()
    mini.run()
