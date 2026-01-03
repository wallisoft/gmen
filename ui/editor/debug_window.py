"""
Debug window for testing window positioning WITH WORKSPACE SUPPORT
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk
import subprocess
import threading
import json
from typing import Optional, Dict, List
from datetime import datetime


class DebugWindow:
    """Debug window for testing window positioning and scripts WITH WORKSPACE SUPPORT"""
    
    def __init__(self, db, menu_model, save_handler):
        self.db = db
        self.model = menu_model
        self.save_handler = save_handler
        
        # UI state
        self.window = None
        self.menu_combo = None
        self.script_combo = None
        self.status_label = None
        self.save_btn = None
        self.test_btn = None
        self.workspace_btn = None
        self.terminal_output = None
        
        # Current test
        self.current_test_item = None
        self.is_saved = True
        
        # Track preview windows we've opened
        self.preview_windows = {}  # item_id -> window
        
        # Workspace mode
        self.workspace_mode = False
    
    def show(self):
        """Show the debug window"""
        self.window = Gtk.Window()
        self.window.set_title("🔧 GMen Debug & Workspace Builder")
        self.window.set_default_size(900, 700)
        self.window.set_position(Gtk.WindowPosition.CENTER)
        self.window.connect("destroy", self._on_window_destroy)
        
        # Main container
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_vbox.set_margin_top(10)
        main_vbox.set_margin_bottom(10)
        main_vbox.set_margin_start(10)
        main_vbox.set_margin_end(10)
        self.window.add(main_vbox)
        
        # === CONTROL PANEL ===
        control_grid = Gtk.Grid()
        control_grid.set_column_spacing(10)
        control_grid.set_row_spacing(10)
        
        # Menu selector
        control_grid.attach(Gtk.Label(label="📋 Menu:"), 0, 0, 1, 1)
        self.menu_combo = Gtk.ComboBoxText()
        self._load_menus()
        self.menu_combo.connect("changed", self._on_menu_changed)
        control_grid.attach(self.menu_combo, 1, 0, 2, 1)
        
        # Script/Item selector
        control_grid.attach(Gtk.Label(label="🎯 Test Item:"), 0, 1, 1, 1)
        self.script_combo = Gtk.ComboBoxText()
        control_grid.attach(self.script_combo, 1, 1, 2, 1)
        
        # Window info display
        self.window_info = Gtk.TextView()
        self.window_info.set_editable(False)
        self.window_info.set_wrap_mode(Gtk.WrapMode.WORD)
        self.window_info.set_size_request(-1, 140)
        
        scrolled_info = Gtk.ScrolledWindow()
        scrolled_info.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_info.add(self.window_info)
        control_grid.attach(scrolled_info, 0, 2, 3, 2)
        
        main_vbox.pack_start(control_grid, False, False, 0)
        
        # === WORKSPACE CONTROLS ===
        workspace_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        workspace_box.set_margin_top(10)
        workspace_box.set_margin_bottom(10)
        
        workspace_label = Gtk.Label(label="<b>🏢 Workspace Builder:</b>")
        workspace_label.set_use_markup(True)
        workspace_box.pack_start(workspace_label, False, False, 0)
        
        # Open All Windows button
        self.open_all_btn = Gtk.Button.new_with_label("🪟 Open All Preview Windows")
        self.open_all_btn.set_tooltip_text("Open all windows in this menu as preview windows that you can reposition")
        self.open_all_btn.connect("clicked", self._on_open_all_clicked)
        workspace_box.pack_start(self.open_all_btn, False, False, 0)
        
        # Capture Positions button
        self.capture_btn = Gtk.Button.new_with_label("📸 Capture Window Positions")
        self.capture_btn.set_tooltip_text("Read positions of all open preview windows and save to database")
        self.capture_btn.connect("clicked", self._on_capture_clicked)
        self.capture_btn.set_sensitive(False)
        workspace_box.pack_start(self.capture_btn, False, False, 0)
        
        # Close All button
        close_all_btn = Gtk.Button.new_with_label("🗑️ Close All Previews")
        close_all_btn.set_tooltip_text("Close all preview windows")
        close_all_btn.connect("clicked", self._on_close_all_clicked)
        workspace_box.pack_start(close_all_btn, False, False, 0)
        
        main_vbox.pack_start(workspace_box, False, False, 0)
        
        # Workspace info label
        self.workspace_info = Gtk.Label(label="No preview windows open")
        self.workspace_info.set_xalign(0)
        self.workspace_info.get_style_context().add_class("dim-label")
        main_vbox.pack_start(self.workspace_info, False, False, 0)
        
        # === TERMINAL OUTPUT ===
        term_label = Gtk.Label(label="<b>📊 Output:</b>")
        term_label.set_use_markup(True)
        term_label.set_xalign(0)
        main_vbox.pack_start(term_label, False, False, 5)
        
        self.terminal_output = Gtk.TextView()
        self.terminal_output.set_editable(False)
        self.terminal_output.set_monospace(True)
        self.terminal_output.set_wrap_mode(Gtk.WrapMode.WORD)
        
        scrolled_term = Gtk.ScrolledWindow()
        scrolled_term.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_term.add(self.terminal_output)
        main_vbox.pack_start(scrolled_term, True, True, 0)
        
        # === BUTTON PANEL ===
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        self.test_btn = Gtk.Button.new_with_label("▶️ Test Script")
        self.test_btn.set_tooltip_text("Execute the selected script/item")
        self.test_btn.connect("clicked", self._on_test_clicked)
        
        edit_btn = Gtk.Button.new_with_label("✏️ Edit Script")
        edit_btn.set_tooltip_text("Edit the selected script in external editor")
        edit_btn.connect("clicked", self._on_edit_clicked)
        
        # Tile button (NEW)
        tile_btn = Gtk.Button.new_with_label("⎔ Tile Alongside")
        tile_btn.set_tooltip_text("Position this window next to the last positioned window")
        tile_btn.connect("clicked", self._on_tile_clicked)
        
        self.save_btn = Gtk.Button.new_with_label("💾 Saved")
        self.save_btn.set_tooltip_text("Save this item's window position to database")
        self.save_btn.get_style_context().add_class("suggested-action")
        self.save_btn.set_sensitive(False)
        self.save_btn.connect("clicked", self._on_save_clicked)
        
        close_btn = Gtk.Button.new_with_label("Close")
        close_btn.connect("clicked", lambda b: self.window.destroy())
        
        button_box.pack_start(self.test_btn, False, False, 0)
        button_box.pack_start(edit_btn, False, False, 0)
        button_box.pack_start(tile_btn, False, False, 0)
        button_box.pack_start(self.save_btn, False, False, 0)
        button_box.pack_start(Gtk.Label(), True, True, 0)  # Spacer
        button_box.pack_start(close_btn, False, False, 0)
        
        main_vbox.pack_start(button_box, False, False, 0)
        
        # === STATUS BAR ===
        self.status_label = Gtk.Label(label="Ready")
        self.status_label.set_xalign(0)
        self.status_label.get_style_context().add_class("dim-label")
        main_vbox.pack_start(self.status_label, False, False, 0)
        
        self.window.show_all()
        
        # Load initial data
        self._update_script_list()
        
        # Apply CSS
        self._apply_css()
    
    def _apply_css(self):
        """Apply CSS styles"""
        css = """
        .suggested-action {
            background-color: #26a269;
            color: white;
        }
        .destructive-action {
            background-color: #c01c28;
            color: white;
        }
        .preview-window {
            border: 3px solid #3584e4;
            border-radius: 5px;
        }
        .dim-label {
            opacity: 0.7;
        }
        """
        
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
    def _load_menus(self):
        """Load menus into dropdown"""
        self.menu_combo.remove_all()
        menus = self.db.fetch_all("SELECT id, name FROM menus ORDER BY name")
        for menu in menus:
            self.menu_combo.append(str(menu['id']), menu['name'])
        
        # Select current menu if exists
        for i, menu in enumerate(menus):
            if menu['id'] == self.model.id:
                self.menu_combo.set_active(i)
                break
    
    def _update_script_list(self):
        """Update script/item list based on selected menu"""
        self.script_combo.remove_all()
        self.script_combo.append_text("-- Select Item --")
        self.script_combo.set_active(0)
        
        # Get all items from current model
        items = self.model.get_all_items()
        for item in items:
            if item.command:  # Only show items with commands/scripts
                item_type = "SCRIPT" if item.is_script() else "CMD"
                display = f"[{item_type}] {item.title}"
                if item.is_script():
                    display += f" ({item.get_script_name()})"
                
                # Store item ID as data
                self.script_combo.append(display, item.id)
    
    def _on_menu_changed(self, combo):
        """Handle menu selection change"""
        menu_id_str = combo.get_active_id()
        if menu_id_str:
            try:
                menu_id = int(menu_id_str)
                # Reload model with selected menu
                menu_data = self.db.fetch_one("SELECT id, name FROM menus WHERE id = ?", (menu_id,))
                if menu_data:
                    self.model = self.model.__class__(menu_data['id'], menu_data['name'])
                    self.model.load_from_db(self.db)
                    self._update_script_list()
                    self._update_status(f"Loaded menu: {menu_data['name']}")
            except ValueError:
                pass
    
    # === WORKSPACE METHODS ===
    
    def _on_open_all_clicked(self, button):
        """Open all windows in this menu as preview windows"""
        items = self.model.get_all_items()
        window_items = [item for item in items if item.command]  # Only items with commands
        
        self._log_output(f"=== Opening {len(window_items)} preview windows ===")
        
        # Close any existing previews
        self._close_all_previews()
        
        # Track position for tiling
        current_x = 100
        current_y = 100
        max_y = 100
        
        for i, item in enumerate(window_items):
            # Create preview window
            preview = self._create_preview_window(item, i)
            
            # Position window (tile if no position set)
            if item.window_state:
                x = item.window_state.get('x', current_x)
                y = item.window_state.get('y', current_y)
                width = item.window_state.get('width', 400)
                height = item.window_state.get('height', 300)
                
                preview.window.move(x, y)
                preview.window.resize(width, height)
            else:
                # Tile windows
                preview.window.move(current_x, current_y)
                preview.window.resize(400, 300)
                
                # Update position for next window
                current_x += 420  # Window width + gap
                if current_x > 1600:  # Wrap to next row
                    current_x = 100
                    current_y = max_y + 320
                
                max_y = max(max_y, current_y)
            
            self.preview_windows[item.id] = preview
            self._log_output(f"Opened preview: {item.title}")
        
        self.capture_btn.set_sensitive(True)
        self.workspace_info.set_text(f"📊 {len(window_items)} preview windows open. Reposition them, then click 'Capture Positions'")
        self._update_status(f"Opened {len(window_items)} preview windows")
    
    def _create_preview_window(self, item, index):
        """Create a preview window for an item"""
        class PreviewWindow:
            def __init__(self, item, index):
                self.item = item
                self.window = Gtk.Window()
                self.window.set_title(f"🪟 Preview: {item.title} [{index+1}]")
                self.window.set_default_size(400, 300)
                self.window.set_decorated(True)
                self.window.set_resizable(True)
                self.window.set_skip_taskbar_hint(True)
                
                # Add CSS class for styling
                context = self.window.get_style_context()
                context.add_class("preview-window")
                
                # Add content
                vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
                vbox.set_margin_top(20)
                vbox.set_margin_bottom(20)
                vbox.set_margin_start(20)
                vbox.set_margin_end(20)
                self.window.add(vbox)
                
                title = Gtk.Label(label=f"<b>{item.title}</b>")
                title.set_use_markup(True)
                vbox.pack_start(title, False, False, 0)
                
                if item.command:
                    cmd_label = Gtk.Label(label=f"Command: {item.command}")
                    cmd_label.set_xalign(0)
                    vbox.pack_start(cmd_label, False, False, 0)
                
                if item.icon:
                    icon_label = Gtk.Label(label=f"Icon: {item.icon}")
                    icon_label.set_xalign(0)
                    vbox.pack_start(icon_label, False, False, 0)
                
                pos_label = Gtk.Label(label="Move and resize this window, then capture positions")
                pos_label.set_xalign(0)
                vbox.pack_start(pos_label, False, False, 10)
                
                # Current position label
                self.pos_label = Gtk.Label(label="Position: (?, ?) Size: ?x?")
                self.pos_label.set_xalign(0)
                vbox.pack_start(self.pos_label, False, False, 0)
                
                # Update position on configure events
                self.window.connect("configure-event", self._on_configure)
                
                self.window.show_all()
            
            def _on_configure(self, window, event):
                """Update position label when window moves/resizes"""
                x, y = window.get_position()
                width, height = window.get_size()
                self.pos_label.set_text(f"Position: ({x}, {y}) Size: {width}x{height}")
                return False
        
        return PreviewWindow(item, index)
    
    def _on_capture_clicked(self, button):
        """Capture positions of all preview windows and save to database"""
        self._log_output("=== Capturing window positions ===")
        
        changed_count = 0
        
        for item_id, preview in self.preview_windows.items():
            item = self.model.get_item(item_id)
            if not item:
                continue
            
            # Get window position and size
            x, y = preview.window.get_position()
            width, height = preview.window.get_size()
            
            # Create or update window state
            window_state = item.window_state or {}
            old_x = window_state.get('x')
            old_y = window_state.get('y')
            old_width = window_state.get('width')
            old_height = window_state.get('height')
            
            # Check if changed
            if (old_x != x or old_y != y or 
                old_width != width or old_height != height):
                
                window_state.update({
                    'x': x,
                    'y': y,
                    'width': width,
                    'height': height,
                    'state': 'normal',
                    'display': 0
                })
                
                item.window_state = window_state
                item.is_modified = True
                self.model.is_modified = True
                changed_count += 1
                
                self._log_output(f"📸 Captured: {item.title} at ({x}, {y}) {width}x{height}")
        
        if changed_count > 0:
            # Save to database
            success, message = self.save_handler.save_model(self.model)
            if success:
                self._log_output(f"✅ Saved {changed_count} window positions to database")
                self._update_status(f"Saved {changed_count} window positions")
                self._update_saved_state(True)
            else:
                self._log_output(f"❌ Save failed: {message}")
                self._update_status(f"Save failed: {message}")
        else:
            self._log_output("ℹ️ No changes to capture")
            self._update_status("No changes to capture")
    
    def _on_close_all_clicked(self, button):
        """Close all preview windows"""
        self._close_all_previews()
        self.capture_btn.set_sensitive(False)
        self.workspace_info.set_text("No preview windows open")
        self._update_status("Closed all preview windows")
    
    def _close_all_previews(self):
        """Close all preview windows"""
        for preview in self.preview_windows.values():
            preview.window.destroy()
        self.preview_windows.clear()
    
    # === TILE FUNCTION ===
    
    def _on_tile_clicked(self, button):
        """Tile the selected window alongside the last positioned window"""
        item_id = self.script_combo.get_active_id()
        if not item_id or item_id == "0":
            self._update_status("Please select an item to tile")
            return
        
        item = self.model.get_item(item_id)
        if not item:
            self._update_status("Item not found")
            return
        
        # Get all items with window states
        all_items = self.model.get_all_items()
        positioned_items = [i for i in all_items if i.window_state and i.id != item_id]
        
        if not positioned_items:
            self._update_status("No other windows positioned yet. Set a position first.")
            return
        
        # Get the last positioned window
        last_item = positioned_items[-1]
        last_state = last_item.window_state
        
        # Calculate position to the right
        new_x = last_state.get('x', 0) + last_state.get('width', 400) + 20
        new_y = last_state.get('y', 0)
        
        # If would go off screen, move down instead
        screen = Gdk.Screen.get_default()
        screen_width = screen.get_width()
        
        if new_x + (last_state.get('width', 400)) > screen_width - 100:
            new_x = 100
            new_y = last_state.get('y', 0) + last_state.get('height', 300) + 20
        
        # Update item's window state
        window_state = item.window_state or {}
        window_state.update({
            'x': new_x,
            'y': new_y,
            'width': last_state.get('width', 400),
            'height': last_state.get('height', 300),
            'state': 'normal',
            'display': last_state.get('display', 0)
        })
        
        item.window_state = window_state
        item.is_modified = True
        self.model.is_modified = True
        
        # Update UI
        self._update_window_info(item)
        self._update_saved_state(False)
        
        self._log_output(f"⎔ Tiled '{item.title}' alongside '{last_item.title}'")
        self._update_status(f"Position set to ({new_x}, {new_y})")
    
    # === EXISTING METHODS (updated) ===
    
    def _on_test_clicked(self, button):
        """Test the selected script/item"""
        item_id = self.script_combo.get_active_id()
        if not item_id or item_id == "0":
            self._update_status("Please select an item to test")
            return
        
        item = self.model.get_item(item_id)
        if not item:
            self._update_status("Item not found")
            return
        
        self.current_test_item = item
        
        # Clear terminal
        buffer = self.terminal_output.get_buffer()
        buffer.set_text("")
        
        # Update window info
        self._update_window_info(item)
        
        # Execute in background thread
        thread = threading.Thread(target=self._execute_test, args=(item,))
        thread.daemon = True
        thread.start()
    
    def _execute_test(self, item):
        """Execute script/command in background thread"""
        def update_output(text):
            buffer = self.terminal_output.get_buffer()
            end_iter = buffer.get_end_iter()
            buffer.insert(end_iter, text + "\n")
            
            # Scroll to end
            mark = buffer.create_mark("end", end_iter, False)
            GLib.idle_add(lambda: self.terminal_output.scroll_to_mark(mark, 0, False, 0, 0))
        
        GLib.idle_add(lambda: self._update_status(f"Testing: {item.title}"))
        GLib.idle_add(lambda: update_output(f"=== Testing: {item.title} ==="))
        GLib.idle_add(lambda: update_output(f"Command: {item.command}"))
        
        if item.window_state:
            GLib.idle_add(lambda: update_output(f"Window: {item.window_state}"))
        
        # Execute command
        try:
            if item.is_script():
                script_name = item.get_script_name()
                GLib.idle_add(lambda: update_output(f"[INFO] Would execute script: @{script_name}"))
                GLib.idle_add(lambda: update_output(f"[INFO] Script would be looked up in 'scripts' table"))
            else:
                GLib.idle_add(lambda: update_output(f"[EXEC] $ {item.command}"))
                GLib.idle_add(lambda: update_output("[INFO] Command execution disabled in debug mode"))
            
            GLib.idle_add(lambda: update_output("=== Test Complete ==="))
            GLib.idle_add(lambda: self._update_status("Test complete"))
            
        except Exception as e:
            GLib.idle_add(lambda: update_output(f"[ERROR] {str(e)}"))
            GLib.idle_add(lambda: self._update_status(f"Test failed: {str(e)}"))
    
    def _on_edit_clicked(self, button):
        """Edit script in external editor"""
        item_id = self.script_combo.get_active_id()
        if not item_id or item_id == "0":
            self._update_status("Please select an item to edit")
            return
        
        item = self.model.get_item(item_id)
        if not item:
            self._update_status("Item not found")
            return
        
        if not item.is_script():
            self._update_status("Selected item is not a script (@scriptname)")
            return
        
        script_name = item.get_script_name()
        
        # Look up script in database
        script = self.db.fetch_one("SELECT id, content FROM scripts WHERE name = ?", (script_name,))
        if not script:
            self._update_status(f"Script '{script_name}' not found in database")
            return
        
        # Create temporary file with script content
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(script['content'] or "# Script content\n")
            temp_path = f.name
        
        # Open in default editor
        try:
            subprocess.Popen(['xdg-open', temp_path])
            self._update_status(f"Opening script in editor: {temp_path}")
            
            GLib.timeout_add_seconds(30, lambda: os.unlink(temp_path) if os.path.exists(temp_path) else False)
            
        except Exception as e:
            self._update_status(f"Failed to open editor: {str(e)}")
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def _on_save_clicked(self, button):
        """Save changes to database"""
        if not self.current_test_item:
            self._update_status("No item selected to save")
            return
        
        # Mark item as modified
        self.current_test_item.is_modified = True
        self.model.is_modified = True
        
        # Save to database
        success, message = self.save_handler.save_model(self.model)
        
        if success:
            self._update_saved_state(True)
            self._update_status("Saved to database")
        else:
            self._update_status(f"Save failed: {message}")
    
    def _update_window_info(self, item):
        """Update window info display"""
        buffer = self.window_info.get_buffer()
        
        info_text = f"Title: {item.title}\n"
        info_text += f"Type: {'Script' if item.is_script() else 'Command'}\n"
        info_text += f"Command: {item.command}\n"
        info_text += f"Icon: {item.icon or '(none)'}\n"
        info_text += f"Depth: {item.depth}\n"
        info_text += f"DB ID: {item.db_id or '(new)'}\n"
        
        if item.window_state:
            info_text += "\n=== Window Position ===\n"
            info_text += f"Position: ({item.window_state.get('x', '?')}, {item.window_state.get('y', '?')})\n"
            info_text += f"Size: {item.window_state.get('width', '?')}x{item.window_state.get('height', '?')}\n"
            info_text += f"State: {item.window_state.get('state', 'normal')}\n"
            info_text += f"Display: {item.window_state.get('display', 0)}\n"
        else:
            info_text += "\n⚠️ No window position set\n"
        
        buffer.set_text(info_text)
        
        # Check if item has unsaved changes
        has_unsaved = item.is_new or item.is_modified
        self._update_saved_state(not has_unsaved)
    
    def _update_saved_state(self, is_saved):
        """Update save button state"""
        self.is_saved = is_saved
        
        if is_saved:
            self.save_btn.set_label("💾 Saved")
            self.save_btn.get_style_context().remove_class("destructive-action")
            self.save_btn.get_style_context().add_class("suggested-action")
            self.save_btn.set_sensitive(False)
        else:
            self.save_btn.set_label("💾 Save Changes")
            self.save_btn.get_style_context().remove_class("suggested-action")
            self.save_btn.get_style_context().add_class("destructive-action")
            self.save_btn.set_sensitive(True)
    
    def _update_status(self, message):
        """Update status label"""
        self.status_label.set_text(message)
    
    def _log_output(self, message):
        """Add message to terminal output"""
        buffer = self.terminal_output.get_buffer()
        end_iter = buffer.get_end_iter()
        buffer.insert(end_iter, message + "\n")
        
        # Scroll to end
        mark = buffer.create_mark("end", end_iter, False)
        self.terminal_output.scroll_to_mark(mark, 0, False, 0, 0)
    
    def _on_window_destroy(self, window):
        """Handle window close"""
        # Close all preview windows
        self._close_all_previews()
        self.window = None
