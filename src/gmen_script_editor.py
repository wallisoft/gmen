#!/usr/bin/env python3
"""
GMen Script Editor - Multi-language script editor with Lua support
"""

import gi
import sys
import argparse
from pathlib import Path

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk, Pango

from database import get_database
from script_engine import ScriptEngine

class GMenScriptEditor:
    def __init__(self, script_id=None):
        self.db = get_database()
        self.script_engine = ScriptEngine(self.db)
        self.current_script_id = script_id
        self.unsaved_changes = False
        
        # Create main window
        self.window = Gtk.Window(title="📜 GMen Script Editor")
        self.window.set_default_size(800, 600)
        self.window.connect("destroy", self.on_window_close)
        
        # Build UI
        main_box = self.create_layout()
        self.window.add(main_box)
        
        # Load script if provided
        if self.current_script_id:
            self.load_script(self.current_script_id)
        elif '--new' in sys.argv:
            self.new_script()
        
        self.window.show_all()
    
    def create_layout(self):
        """Create the main UI layout"""
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox.set_margin_top(5)
        vbox.set_margin_bottom(5)
        vbox.set_margin_start(5)
        vbox.set_margin_end(5)
        
        # Top toolbar
        vbox.pack_start(self.create_toolbar(), False, False, 0)
        
        # Script info section
        vbox.pack_start(self.create_info_section(), False, False, 5)
        
        # Code editor with syntax highlighting
        vbox.pack_start(self.create_editor_section(), True, True, 0)
        
        # Bottom status bar
        vbox.pack_start(self.create_status_bar(), False, False, 0)
        
        return vbox
    
    def create_toolbar(self):
        """Create top toolbar"""
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        # Save button
        save_btn = Gtk.Button(label="💾 Save")
        save_btn.connect("clicked", self.on_save)
        
        # Save As button
        save_as_btn = Gtk.Button(label="💾 Save As...")
        save_as_btn.connect("clicked", self.on_save_as)
        
        # Run button
        run_btn = Gtk.Button(label="▶️ Test Run")
        run_btn.connect("clicked", self.on_run)
        
        # API Reference button
        api_btn = Gtk.Button(label="📚 API Reference")
        api_btn.connect("clicked", self.show_api_reference)
        
        hbox.pack_start(save_btn, False, False, 0)
        hbox.pack_start(save_as_btn, False, False, 0)
        hbox.pack_start(run_btn, False, False, 0)
        hbox.pack_start(api_btn, False, False, 0)
        
        return hbox
    
    def create_info_section(self):
        """Create script information section"""
        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(5)
        
        # Script Name
        grid.attach(Gtk.Label(label="Script Name:"), 0, 0, 1, 1)
        self.name_entry = Gtk.Entry()
        self.name_entry.set_width_chars(30)
        self.name_entry.connect("changed", self.on_content_changed)
        grid.attach(self.name_entry, 1, 0, 1, 1)
        
        # Language
        grid.attach(Gtk.Label(label="Language:"), 2, 0, 1, 1)
        self.language_combo = Gtk.ComboBoxText()
        self.language_combo.append_text("Lua")
        self.language_combo.append_text("Python")
        self.language_combo.append_text("Shell")
        self.language_combo.set_active(0)
        self.language_combo.connect("changed", self.on_language_changed)
        grid.attach(self.language_combo, 3, 0, 1, 1)
        
        # Description
        grid.attach(Gtk.Label(label="Description:"), 0, 1, 1, 1)
        self.desc_entry = Gtk.Entry()
        self.desc_entry.set_width_chars(50)
        self.desc_entry.connect("changed", self.on_content_changed)
        grid.attach(self.desc_entry, 1, 1, 3, 1)
        
        return grid
    
    def create_editor_section(self):
        """Create code editor section"""
        frame = Gtk.Frame(label="Code Editor")
        frame.set_shadow_type(Gtk.ShadowType.IN)
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
        # Scrolled window for code editor
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        # Text view for code editor
        self.text_view = Gtk.TextView()
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text_view.connect("key-release-event", self.on_text_changed)
        
        # Create monospace font
        font_desc = Pango.FontDescription("Monospace 10")
        self.text_view.modify_font(font_desc)
        
        # Add line numbers
        self.setup_line_numbers()
        
        scrolled.add(self.text_view)
        vbox.pack_start(scrolled, True, True, 0)
        
        # Example script button
        example_btn = Gtk.Button(label="📋 Load Example Script")
        example_btn.connect("clicked", self.load_example_script)
        vbox.pack_start(example_btn, False, False, 5)
        
        frame.add(vbox)
        return frame
    
    def setup_line_numbers(self):
        """Setup line numbers for the text editor"""
        # Simple line number implementation
        buffer = self.text_view.get_buffer()
        
        def update_line_numbers(*args):
            # Get current line count
            line_count = buffer.get_line_count()
            # Update status bar
            self.status_label.set_text(f"Lines: {line_count}")
        
        buffer.connect("changed", update_line_numbers)
    
    def create_status_bar(self):
        """Create status bar"""
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        self.status_label = Gtk.Label(label="Ready")
        self.status_label.set_xalign(0)
        
        hbox.pack_start(self.status_label, True, True, 0)
        
        return hbox
    
    def load_script(self, script_id):
        """Load a script from database"""
        script = self.db.fetch_one("""
            SELECT id, name, language, code, description
            FROM scripts 
            WHERE id = ?
        """, (script_id,))
        
        if script:
            self.current_script_id = script['id']
            self.name_entry.set_text(script['name'])
            self.desc_entry.set_text(script.get('description', ''))
            
            # Set language
            if script['language'].lower() == 'lua':
                self.language_combo.set_active(0)
            elif script['language'].lower() == 'python':
                self.language_combo.set_active(1)
            else:
                self.language_combo.set_active(2)
            
            # Set code
            buffer = self.text_view.get_buffer()
            buffer.set_text(script['code'])
            
            self.unsaved_changes = False
            self.window.set_title(f"📜 GMen Script Editor - {script['name']}")
            self.status_label.set_text(f"Loaded script: {script['name']}")
    
    def new_script(self):
        """Create a new script"""
        self.current_script_id = None
        self.name_entry.set_text("")
        self.desc_entry.set_text("")
        self.language_combo.set_active(0)
        
        buffer = self.text_view.get_buffer()
        buffer.set_text("")
        
        self.unsaved_changes = False
        self.window.set_title("📜 GMen Script Editor - New Script")
        self.status_label.set_text("New script")
    
    def on_content_changed(self, *args):
        """Handle content changes"""
        self.unsaved_changes = True
        self.status_label.set_text("Unsaved changes")
    
    def on_text_changed(self, widget, event):
        """Handle text changes"""
        self.unsaved_changes = True
        self.status_label.set_text("Unsaved changes")
    
    def on_language_changed(self, combo):
        """Handle language change"""
        self.unsaved_changes = True
        language = combo.get_active_text()
        self.status_label.set_text(f"Language changed to: {language}")
    
    def on_save(self, button):
        """Save current script"""
        name = self.name_entry.get_text().strip()
        if not name:
            self.show_message("Script name cannot be empty", Gtk.MessageType.ERROR)
            return
        
        language_map = {0: 'lua', 1: 'python', 2: 'shell'}
        language = language_map[self.language_combo.get_active()]
        
        buffer = self.text_view.get_buffer()
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        code = buffer.get_text(start, end, True)
        
        if not code.strip():
            self.show_message("Script code cannot be empty", Gtk.MessageType.WARNING)
            return
        
        description = self.desc_entry.get_text().strip()
        
        # Save to database
        if self.current_script_id:
            # Update existing
            self.db.execute("""
                UPDATE scripts 
                SET name = ?, language = ?, code = ?, description = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (name, language, code, description, self.current_script_id))
        else:
            # Create new
            self.db.execute("""
                INSERT INTO scripts (name, language, code, description)
                VALUES (?, ?, ?, ?)
            """, (name, language, code, description))
            result = self.db.fetch_one("SELECT last_insert_rowid() AS id")
            self.current_script_id = result['id']
        
        self.unsaved_changes = False
        self.window.set_title(f"📜 GMen Script Editor - {name}")
        self.status_label.set_text(f"Saved: {name}")
        self.show_message(f"Script '{name}' saved successfully", Gtk.MessageType.INFO)
    
    def on_save_as(self, button):
        """Save as new script"""
        dialog = Gtk.Dialog(
            "Save As",
            self.window,
            Gtk.DialogFlags.MODAL,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        )
        
        dialog.set_default_size(300, 150)
        
        box = dialog.get_content_area()
        
        label = Gtk.Label(label="Enter new script name:")
        box.add(label)
        
        entry = Gtk.Entry()
        entry.set_text(self.name_entry.get_text())
        box.add(entry)
        
        box.show_all()
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            new_name = entry.get_text().strip()
            if new_name:
                self.name_entry.set_text(new_name)
                self.current_script_id = None  # Force create new
                self.on_save(None)
        
        dialog.destroy()
    
    def on_run(self, button):
        """Test run the script"""
        if self.unsaved_changes:
            dialog = Gtk.MessageDialog(
                transient_for=self.window,
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO,
                text="Unsaved Changes"
            )
            dialog.format_secondary_text("Save before running test?")
            
            response = dialog.run()
            dialog.destroy()
            
            if response == Gtk.ResponseType.YES:
                self.on_save(None)
        
        # Get code
        buffer = self.text_view.get_buffer()
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        code = buffer.get_text(start, end, True)
        
        if not code.strip():
            self.show_message("No code to run", Gtk.MessageType.WARNING)
            return
        
        # Create temporary script file and execute
        try:
            language_map = {0: 'lua', 1: 'python', 2: 'shell'}
            language = language_map[self.language_combo.get_active()]
            
            if language == 'lua':
                result = self.script_engine.execute_lua(code)
                self.show_message(f"Script executed successfully\nResult: {result}", 
                                Gtk.MessageType.INFO)
            elif language == 'python':
                result = self.script_engine.execute_python(code)
                self.show_message(f"Script executed successfully\nResult: {result}", 
                                Gtk.MessageType.INFO)
            else:
                result = self.script_engine.execute_shell(code)
                self.show_message(f"Script executed successfully\nReturn code: {result['returncode']}", 
                                Gtk.MessageType.INFO)
        
        except Exception as e:
            self.show_message(f"Execution failed: {e}", Gtk.MessageType.ERROR)
    
    def load_example_script(self, button):
        """Load example Lua script"""
        example_code = """-- Setup development workspace
function main()
    -- Launch VS Code
    local code_id = gmen.launch("code")
    gmen.set_window(code_id, 100, 100, 1200, 800)
    
    -- Launch terminal
    gmen.sleep(1)
    local term_id = gmen.launch("gnome-terminal")
    gmen.set_window(term_id, 1300, 100, 600, 800)
    
    gmen.notify("Dev environment ready!")
end

-- Example of script chaining
function open_browser()
    gmen.launch("firefox https://github.com")
end

function check_email()
    gmen.launch("thunderbird")
    gmen.notify("Email client launched")
end

-- This script can be called from menu items
return main"""
        
        buffer = self.text_view.get_buffer()
        buffer.set_text(example_code)
        
        if not self.name_entry.get_text():
            self.name_entry.set_text("setup_dev")
            self.desc_entry.set_text("Setup development workspace")
        
        self.unsaved_changes = True
        self.status_label.set_text("Example script loaded")
    
    def show_api_reference(self, button):
        """Show GMen Lua API reference"""
        dialog = Gtk.Dialog(
            "GMen Lua API Reference",
            self.window,
            Gtk.DialogFlags.MODAL,
            (Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
        )
        
        dialog.set_default_size(500, 400)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        text_view = Gtk.TextView()
        text_view.set_editable(False)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        
        font_desc = Pango.FontDescription("Monospace 9")
        text_view.modify_font(font_desc)
        
        api_reference = """GMen Lua API Reference
=========================

Core Functions:
--------------
gmen.launch(command)
    Launch an application
    Returns: PID of launched process
    Example: local pid = gmen.launch("firefox")

gmen.notify(message)
    Show a notification
    Returns: true on success
    Example: gmen.notify("Hello from Lua!")

gmen.sleep(seconds)
    Pause script execution
    Returns: true
    Example: gmen.sleep(2.5)

Window Management:
------------------
gmen.set_window(pid, x, y, width, height)
    Set window position and size
    Returns: true on success
    Example: gmen.set_window(pid, 100, 100, 800, 600)

gmen.get_window_state(app_name)
    Get saved window state for app
    Returns: table with x, y, width, height, monitor
    Example: local state = gmen.get_window_state("firefox")

Script Chaining:
----------------
gmen.run_script(script_name)
    Run another script by name
    Returns: result of script execution
    Example: gmen.run_script("morning_routine")

Example Scripts:
----------------
-- Morning routine script
function main()
    gmen.run_script("check_email")
    gmen.launch("xdg-open https://calendar.google.com")
    gmen.run_script("start_pomodoro")
    gmen.notify("Good morning! Ready for work.")
end

-- Workspace setup script
function setup_workspace()
    -- Launch apps in specific positions
    local apps = {
        {"code", 100, 100, 1200, 800},
        {"gnome-terminal", 1300, 100, 600, 800},
        {"firefox", 100, 900, 1000, 600}
    }
    
    for i, app in ipairs(apps) do
        local pid = gmen.launch(app[1])
        gmen.set_window(pid, app[2], app[3], app[4], app[5])
        gmen.sleep(0.5)
    end
    
    gmen.notify("Workspace ready!")
end

-- Save this as "morning_routine.lua" and call from menu items
"""
        
        buffer = text_view.get_buffer()
        buffer.set_text(api_reference)
        
        scrolled.add(text_view)
        dialog.get_content_area().add(scrolled)
        dialog.show_all()
        dialog.run()
        dialog.destroy()
    
    def show_message(self, text, message_type=Gtk.MessageType.INFO):
        """Show a message dialog"""
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            flags=0,
            message_type=message_type,
            buttons=Gtk.ButtonsType.OK,
            text=text
        )
        
        # Auto-close after 3 seconds for info messages
        if message_type == Gtk.MessageType.INFO:
            GLib.timeout_add(3000, dialog.destroy)
        
        dialog.run()
        if message_type != Gtk.MessageType.INFO:
            dialog.destroy()
    
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
            dialog.format_secondary_text("Save before closing?")
            
            response = dialog.run()
            dialog.destroy()
            
            if response == Gtk.ResponseType.YES:
                self.on_save(None)
                Gtk.main_quit()
            elif response == Gtk.ResponseType.NO:
                Gtk.main_quit()
            else:
                return  # Don't close
        
        Gtk.main_quit()
    
    def run(self):
        """Start the application"""
        Gtk.main()


# Main entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='GMen Script Editor')
    parser.add_argument('--script', type=int, help='Script ID to edit')
    parser.add_argument('--new', action='store_true', help='Create new script')
    
    args = parser.parse_args()
    
    print("📜 GMen Script Editor")
    print("💾 Database: ~/.config/gmen/gmen.db")
    
    editor = GMenScriptEditor(script_id=args.script)
    editor.run()
