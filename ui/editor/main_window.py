"""
Main editor window - integrates all modular components
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
from pathlib import Path
import sys

from ui.editor.tree_manager import TreeManager
from ui.editor.property_panel import PropertyPanel
from ui.editor.toolbar import EditorToolbar
from core.editor.change_tracker import ChangeTracker
from core.editor.save_handler import SaveHandler


class EditorMainWindow:
    """Main editor window - coordinates all components"""
    
    def __init__(self, db, config_manager):
        self.db = db
        self.config = config_manager
        
        self.current_menu_id = None
        self.current_menu_name = "Default Menu"
        self.unsaved_changes = False
        
        # Initialize core components
        self.change_tracker = ChangeTracker()
        self.save_handler = SaveHandler(db)
        
        # Initialize UI components
        self.tree_manager = TreeManager(db)
        self.property_panel = PropertyPanel()
        self.toolbar = EditorToolbar()
        
        # Create window
        self.window = Gtk.Window(title=f"🎯 GMen Editor - {self.current_menu_name}")
        self.window.set_default_size(1000, 600)
        self.window.connect("destroy", self.on_window_close)
        
        # Build UI
        self.create_layout()
        
        # Connect signals
        self.connect_signals()
        
        # Load initial menu
        self.load_initial_menu()
    
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
        nav_frame = self.tree_manager.create_nav_panel()
        hbox.pack_start(nav_frame, True, True, 0)
        
        # Right - Properties panel
        props_frame = self.property_panel.create_panel()
        hbox.pack_start(props_frame, False, False, 0)
        
        vbox.pack_start(hbox, True, True, 0)
        
        # 3. Bottom toolbar
        vbox.pack_start(self.toolbar.create_toolbar(), False, False, 0)
        
        self.window.add(vbox)
    
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
        self.unsaved_label.set_markup("<span foreground='orange' weight='bold'>●</span>")
        self.unsaved_label.set_no_show_all(True)
        self.unsaved_label.hide()
        
        hbox.pack_start(name_label, False, False, 0)
        hbox.pack_start(self.menu_name_entry, True, True, 0)
        hbox.pack_start(self.default_check, False, False, 0)
        hbox.pack_start(self.save_btn, False, False, 0)
        hbox.pack_start(self.unsaved_label, False, False, 5)
        
        return hbox
    
    def connect_signals(self):
        """Connect all component signals"""
        # Tree manager callbacks
        self.tree_manager.on_selection_changed = self.on_tree_selection_changed
        self.tree_manager.on_item_modified = self.on_item_modified
        self.tree_manager.on_item_added = self.on_item_added
        self.tree_manager.on_item_deleted = self.on_item_deleted
        
        # Property panel callback
        self.property_panel.on_changed = self.on_property_changed
        
        # Toolbar callbacks
        self.toolbar.on_reload = self.on_reload
        self.toolbar.on_backup = self.on_backup
        self.toolbar.on_script_editor = self.on_script_editor
        self.toolbar.on_test = self.on_test
        self.toolbar.on_quit = self.on_quit
    
    def load_initial_menu(self):
        """Load initial menu data"""
        # Get default menu
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
        
        self.menu_name_entry.set_text(self.current_menu_name)
        self.window.set_title(f"🎯 GMen Editor - {self.current_menu_name}")
        
        # Load menu items into tree
        self.tree_manager.load_menu(self.current_menu_id)
    
    # ===== EVENT HANDLERS =====
    
    def on_window_close(self, window):
        """Handle window close"""
        if self.unsaved_changes or self.change_tracker.has_changes():
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
                if not self.save_menu():
                    return  # Save failed, don't close
            elif response == Gtk.ResponseType.CANCEL:
                return  # Don't close
        
        Gtk.main_quit()
    
    def on_menu_name_changed(self, entry):
        new_name = entry.get_text().strip()
        if new_name != self.current_menu_name:
            self.current_menu_name = new_name
            self.window.set_title(f"🎯 GMen Editor - {new_name}")
            self.change_tracker.mark_menu_modified(name=new_name)
            self.mark_unsaved_changes()
    
    def on_default_toggled(self, check):
        self.change_tracker.mark_menu_modified(is_default=check.get_active())
        self.mark_unsaved_changes()
    
    def on_tree_selection_changed(self, item_id):
        """When tree selection changes"""
        if item_id > 0:  # Real item (not temp)
            self.property_panel.load_item(item_id, self.db)
        else:
            self.property_panel.clear()
    
    def on_item_modified(self, item_id, field, value):
        """When an item is modified in tree"""
        self.change_tracker.mark_item_modified(item_id, field, value)
        self.mark_unsaved_changes()
    
    def on_item_added(self, temp_id, item_data):
        """When a new item is added to tree"""
        self.change_tracker.add_new_item(temp_id, item_data)
        self.mark_unsaved_changes()
    
    def on_item_deleted(self, item_id):
        """When an item is deleted from tree"""
        self.change_tracker.mark_item_deleted(item_id)
        self.mark_unsaved_changes()
    
    def on_property_changed(self, item_id, field, value):
        """When a property changes"""
        print(f"🔧 Property changed: item_id={item_id}, field={field}, value='{value}'")

        if field == 'window_state':
            self.change_tracker.update_window_state(item_id, value)
        else:
            self.change_tracker.mark_item_modified(item_id, field, value)
            print(f"   📝 Marked item {item_id} as modified in field '{field}'")

        # Update tree if title changed
        if field == 'title':
            print(f"   🌳 Calling tree_manager.update_item_title({item_id}, '{value}')")
            self.tree_manager.update_item_title(item_id, value)

        self.mark_unsaved_changes()
        
    def on_save(self, button):
    """Save button clicked"""
    self.save_menu()
    
    def save_menu(self):
        """Save all changes to database"""
        print(f"🔍 Save called. Unsaved: {self.unsaved_changes}, Has changes: {self.change_tracker.has_changes()}")
        print(f"Change tracker summary: {self.change_tracker.get_change_summary()}")

        if not self.unsaved_changes and not self.change_tracker.has_changes():
            self.show_message("No changes to save", Gtk.MessageType.INFO)
            return True

        success, message = self.save_handler.save_all(
            self.current_menu_id,
            self.change_tracker
        )

        print(f"Save result: success={success}, message={message}")

        if success:
            # Clear change tracking
            self.change_tracker.clear()
            self.unsaved_changes = False
            self.update_unsaved_indicator()

            # Reload the entire tree from database
            self.tree_manager.load_menu(self.current_menu_id)
            self.property_panel.clear()

            self.show_message("💾 All changes saved")
            print(f"✅ Menu '{self.current_menu_name}' saved")
            return True
        else:
            self.show_message(f"❌ {message}", Gtk.MessageType.ERROR)
            return False
            
    def on_reload(self):
        """Reload from database"""
        if self.change_tracker.has_changes():
            dialog = Gtk.MessageDialog(
                transient_for=self.window,
                flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.YES_NO,
                text="Discard Unsaved Changes?"
            )
            dialog.format_secondary_text("Reloading will lose unsaved changes.")
            
            response = dialog.run()
            dialog.destroy()
            
            if response != Gtk.ResponseType.YES:
                return
        
        # Clear changes and reload
        self.change_tracker.clear()
        self.unsaved_changes = False
        self.update_unsaved_indicator()
        
        self.tree_manager.load_menu(self.current_menu_id)
        self.property_panel.clear()
        
        self.show_message("🔄 Reloaded from database")
    
    def on_backup(self):
        """Create database backup"""
        from storage.database import Database
        config_dir = Path.home() / ".config" / "gmen"
        db = Database(config_dir)
        backup_path = db.backup()
        self.show_message(f"💾 Backup created: {backup_path.name}")
    
    def on_script_editor(self):
        """Open script editor"""
        try:
            editor_path = Path.cwd() / "gmen_script_editor.py"
            if editor_path.exists():
                import subprocess
                subprocess.Popen([sys.executable, str(editor_path)])
            else:
                self.show_message("Script editor not found", Gtk.MessageType.WARNING)
        except Exception as e:
            print(f"❌ Could not launch script editor: {e}")
    
    def on_test(self):
        """Test launch GMen"""
        import subprocess
        
        # Save first
        if self.change_tracker.has_changes():
            if not self.save_menu():
                self.show_message("Please save changes before testing", Gtk.MessageType.WARNING)
                return
        
        # Launch GMen
        try:
            gmen_path = Path.cwd() / "gmen.py"
            if gmen_path.exists():
                subprocess.Popen([sys.executable, str(gmen_path)], cwd=Path.cwd())
                self.show_message("🚀 GMen launched!")
            else:
                self.show_message("⚠️ GMen executable not found")
        except Exception as e:
            self.show_message(f"❌ Failed to launch: {e}")
    
    def on_quit(self):
        """Quit button handler"""
        self.on_window_close(self.window)
    
    def mark_unsaved_changes(self):
        """Mark that there are unsaved changes"""
        self.unsaved_changes = True
        self.update_unsaved_indicator()
    
    def update_unsaved_indicator(self):
        """Update the unsaved changes indicator"""
        has_changes = self.unsaved_changes or self.change_tracker.has_changes()
        
        if has_changes:
            summary = self.change_tracker.get_change_summary()
            change_count = (summary['modified'] + summary['new'] + 
                          summary['deleted'] + summary['window_states'])
            
            if summary['menu_modified']:
                change_count += 1
            
            self.unsaved_label.set_markup(
                f"<span foreground='orange' weight='bold'>{change_count} unsaved</span>"
            )
            self.unsaved_label.show()
            self.save_btn.set_sensitive(True)
        else:
            self.unsaved_label.hide()
            self.save_btn.set_sensitive(False)
    
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
        self.window.show_all()
        Gtk.main()
