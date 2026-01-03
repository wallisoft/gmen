"""
Main editor window - Clean integration
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from ui.editor.tree_manager import TreeManager
from ui.editor.property_panel import PropertyPanel
from ui.editor.toolbar import Toolbar


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
        self.tree_manager = None
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
        
        # Create tree manager (connected to model)
        self.tree_manager = TreeManager(self.db, self.model)
        self.tree_manager.on_selection_changed = self.on_tree_selection_changed
        self.tree_manager.on_item_modified = self.on_item_modified
        
        # Create property panel (with script dropdown)
        self.property_panel = PropertyPanel(self.db)
        self.property_panel.on_property_changed = self.on_property_changed
        
        # Add tree panel (left)
        tree_frame = self.tree_manager.create_nav_panel()
        content_hbox.pack_start(tree_frame, True, True, 0)
        
        # Add property panel (right)
        property_frame = self.property_panel.create_panel()
        content_hbox.pack_start(property_frame, False, False, 0)
        
        # Load initial data into tree
        self.tree_manager.rebuild_tree()
        
        # Show window
        self.window.show_all()

        # Load CSS
        self._load_css()
        
        print("✅ Editor UI initialized")
    
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
    
    def on_tree_selection_changed(self, item_id):
        """Handle tree selection change"""
        self.selected_item_id = item_id
        
        # Update property panel with selected item
        if item_id:
            item = self.model.get_item(item_id)
            if item:
                self.property_panel.load_item(item)
            else:
                self.property_panel.clear()
        else:
            self.property_panel.clear()
    
    def on_item_modified(self, item_id, field, value):
        """Handle item modification from tree"""
        print(f"📝 Tree modified: {item_id}.{field} = {value}")
        
        # Update change tracker
        self.change_tracker.mark_item_modified(item_id, field, value)
        
        # Update toolbar status
        self.toolbar.set_unsaved_changes(self.model.has_changes())
    
    def on_property_changed(self, item_id, field, value):
        """Handle property change from property panel"""
        print(f"⚙️ Property changed: {item_id}.{field} = {value}")

        if field == 'title':
            # FIXED: Update tree IMMEDIATELY with debounce protection
            GLib.idle_add(self._update_title_delayed, item_id, value)
        else:
            # Update in model
            self.model.update_item(item_id, **{field: value})

            # If icon changed, tree might need refresh
            if field == 'icon':
                self.tree_manager.refresh_item(item_id)

        # Update change tracker
        self.change_tracker.mark_item_modified(item_id, field, value)

        # Update toolbar
        self.toolbar.set_unsaved_changes(self.model.has_changes())

    def _update_title_delayed(self, item_id, value):
        """Update title with debounce to avoid recursion"""
        # Update in tree (immediate)
        if self.tree_manager.update_item_title(item_id, value):
            print(f"✅ Updated title in tree")
        return False  # Don't repeat
    
    def on_save(self):
        """Handle save button click"""
        print("💾 Save requested...")
        
        if not self.model.has_changes():
            self.toolbar.show_message("No changes to save")
            return
        
        summary = self.change_tracker.get_change_summary()
        print(f"📊 Changes to save: {summary}")
        
        self.toolbar.show_message("Saving...")
        
        # Save to database
        success, message = self.save_handler.save_model(self.model)
        
        if success:
            self.toolbar.show_message(f"Saved {summary['total']} changes")
            self.toolbar.set_unsaved_changes(False)
            
            # Refresh tree to update temp→real IDs
            self.tree_manager.rebuild_tree()
            
            # Restore selection if possible
            if self.selected_item_id:
                self.tree_manager.selection.unselect_all()
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
        
        # Rebuild tree
        self.tree_manager.rebuild_tree()
        
        # Clear property panel
        self.property_panel.clear()
        
        # Clear selection
        self.selected_item_id = None
        
        # Update toolbar
        self.toolbar.set_unsaved_changes(False)
        self.toolbar.show_message("Reloaded from database")
    
    def on_debug(self):
        """Handle debug button click"""
        print("\n=== DEBUG ===")
        self.model.print_debug()
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
