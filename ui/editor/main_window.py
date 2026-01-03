"""
Main editor window - Clean integration with SIMPLE ListManager
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from ui.editor.list_manager import ListManager
from ui.editor.property_panel import PropertyPanel
from ui.editor.toolbar import Toolbar
from core.editor.menu_model import MenuItem  # For temporary items


class EditorMainWindow:
    """Main editor window with clean architecture"""
    
    def __init__(self, db, menu_model, save_handler, change_tracker):
        self.db = db
        self.model = menu_model
        self.save_handler = save_handler
        self.change_tracker = change_tracker
        
        # Current selection
        self.selected_item_id = None
        
        # UI components
        self.window = None
        self.list_manager = None
        self.property_panel = None
        self.toolbar = None
        
        # Initialize UI
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI"""
        # Create main window
        self.window = Gtk.Window()
        self.window.set_title(f"GMen Editor - {self.model.name}")
        self.window.set_default_size(1200, 800)
        self.window.connect("destroy", self.on_window_destroy)
        
        # Create main container
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window.add(main_vbox)
        
        # Create toolbar
        self.toolbar = Toolbar(self.db)
        self.toolbar.on_save = self.on_save
        self.toolbar.on_reload = self.on_reload
        self.toolbar.on_debug = self.on_debug
        self.toolbar.on_export = self.on_export
        self.toolbar.on_import = self.on_import
        main_vbox.pack_start(self.toolbar.create_toolbar(), False, False, 0)
        
        # Create content area
        content_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        content_hbox.set_margin_top(5)
        content_hbox.set_margin_bottom(5)
        content_hbox.set_margin_start(5)
        content_hbox.set_margin_end(5)
        main_vbox.pack_start(content_hbox, True, True, 0)
        
        # Create SIMPLE list manager
        self.list_manager = ListManager(self.db, self.model)
        self.list_manager.on_selection_changed = self.on_list_selection_changed
        self.list_manager.on_item_modified = self.on_item_modified
        
        # Create property panel
        self.property_panel = PropertyPanel(self.db)
        self.property_panel.on_property_changed = self.on_property_changed
        
        # Add list panel (left)
        list_frame = self.list_manager.create_nav_panel()
        content_hbox.pack_start(list_frame, True, True, 0)
        
        # Add property panel (right)
        property_frame = self.property_panel.create_panel()
        content_hbox.pack_start(property_frame, False, False, 0)
        
        # Show window
        self.window.show_all()

        # Load CSS
        self._load_css()
        
        print("✅ Editor UI initialized with SIMPLE ListManager")
    
    def run(self):
        """Run the main GTK loop"""
        Gtk.main()
    
    # ===== Event Handlers =====
    
    def on_window_destroy(self, window):
        """Handle window close"""
        print("🪟 Window closing...")
        
        # Check for unsaved changes
        if self.model.has_changes():
            print("⚠️ There are unsaved changes!")
            # TODO: Add confirmation dialog
        
        Gtk.main_quit()
    
    def on_list_selection_changed(self, item_id):
        """Handle list selection change"""
        print(f"📌 List selection changed: {item_id}")
        self.selected_item_id = item_id
        
        if item_id:
            # Get properties from list manager
            props = self.list_manager.get_item_properties(item_id)
            if props:
                # Create a temporary model item for the property panel
                temp_item = MenuItem(
                    id=item_id,
                    title=props.get('title', ''),
                    command=props.get('command', ''),
                    icon=props.get('icon', ''),
                    window_state=props.get('window_state')
                )
                # Try to get DB ID if available
                selected_item = self.list_manager.get_selected_item()
                if selected_item and selected_item.db_id:
                    temp_item.db_id = selected_item.db_id
                
                self.property_panel.load_item(temp_item)
                print(f"📋 Loaded properties for item {item_id}")
            else:
                self.property_panel.clear()
                print(f"⚠️ No properties found for item {item_id}")
        else:
            self.property_panel.clear()
            print("📋 Selection cleared")
    
    def on_item_modified(self, item_id, field, value):
        """Handle item modification from list manager"""
        print(f"📝 List modified: {item_id}.{field} = {value}")
        
        # Update change tracker
        self.change_tracker.mark_item_modified(item_id, field, value)
        
        # Mark model as modified
        self.model.is_modified = True
        
        # Update toolbar status
        self.toolbar.set_unsaved_changes(True)
    
    def on_property_changed(self, item_id, field, value):
        """Handle property change from property panel"""
        print(f"⚙️ Property changed: {item_id}.{field} = {value}")
        
        if field == 'title':
            # Update in list manager
            if self.list_manager.update_item_title(item_id, value):
                print(f"✅ Updated title in list")
        else:
            # Update in list manager's properties
            update_data = {field: value}
            self.list_manager.update_item_properties(item_id, **update_data)
            
            # If icon changed, refresh might be needed
            if field == 'icon':
                pass  # Icon updates are handled by property panel
        
        # Update change tracker
        self.change_tracker.mark_item_modified(item_id, field, value)
        
        # Mark model as modified
        self.model.is_modified = True
        
        # Update toolbar
        self.toolbar.set_unsaved_changes(True)
    
    def on_save(self):
        """Handle save button click"""
        print("💾 Save requested...")
        
        # First convert display list back to model
        print("🔄 Converting display list to model...")
        success = self.list_manager.save_to_model(self.model)
        
        if not success:
            self.toolbar.show_message("Save failed: could not convert to model")
            return
        
        if not self.model.has_changes():
            self.toolbar.show_message("No changes to save")
            return
        
        summary = self.change_tracker.get_change_summary()
        print(f"📊 Changes to save: {summary}")
        
        if summary['total'] == 0:
            self.toolbar.show_message("No changes to save")
            return
        
        self.toolbar.show_message("Saving...")
        
        # Save to database
        success, message = self.save_handler.save_model(self.model)
        
        if success:
            self.toolbar.show_message(f"Saved {summary['total']} changes")
            self.toolbar.set_unsaved_changes(False)
            
            # Clear change tracker
            self.change_tracker.clear()
            
            # Refresh list to update DB IDs
            self.list_manager.rebuild_list()
            
            # Re-select current item if any
            if self.selected_item_id:
                # Selection will be restored by rebuild_list
                pass
                
        else:
            self.toolbar.show_message(f"Save failed: {message}")
    
    def on_reload(self):
        """Handle reload button click"""
        print("🔄 Reload requested...")
        
        if self.model.has_changes():
            print("⚠️ Unsaved changes will be lost!")
            # TODO: Add confirmation dialog
        
        # Reload from database
        self.model.load_from_db(self.db)
        
        # Rebuild list from fresh model
        self.list_manager.rebuild_list()
        
        # Clear property panel
        self.property_panel.clear()
        
        # Clear selection
        self.selected_item_id = None
        
        # Clear change tracker
        self.change_tracker.clear()
        
        # Update toolbar
        self.toolbar.set_unsaved_changes(False)
        self.toolbar.show_message("Reloaded from database")
    
    def on_debug(self):
        """Handle debug button click"""
        print("\n=== DEBUG ===")
        print("Model:")
        self.model.print_debug()
        
        print("\nDisplay items:")
        selected = self.list_manager.get_selected_item()
        if selected:
            print(f"Selected: {selected}")
        else:
            print("No selection")
        
        print(f"Display items count: {len(self.list_manager.display_items)}")
        for i, item in enumerate(self.list_manager.display_items):
            print(f"  [{i}] {item}")
        
        print("=============")
        self.toolbar.show_message("Debug info printed to console")
    
    def on_export(self):
        """Handle export button click"""
        print("📤 Export requested")
        self.toolbar.show_message("Export (stub)")
        # TODO: Implement export
    
    def on_import(self):
        """Handle import button click"""
        print("📥 Import requested")
        self.toolbar.show_message("Import (stub)")
        # TODO: Implement import

    def _load_css(self):
        """Load CSS styles"""
        css = """
        .suggested-action {
            background-color: #26a269;
            color: white;
        }
        .destructive-action {
            background-color: #c01c28;
            color: white;
        }
        .dim-label {
            opacity: 0.7;
        }
        .list-row {
            padding: 3px;
        }
        .list-row:selected {
            background-color: #3584e4;
            color: white;
        }
        .indent-button {
            font-weight: bold;
        }
        .outdent-button {
            font-weight: bold;
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
            pass  # CSS not critical
