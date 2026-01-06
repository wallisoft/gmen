"""
Enhanced toolbar with real import/export
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import os
from datetime import datetime
from pathlib import Path
from storage.import_export import ImportExportManager


class Toolbar:
    """Enhanced toolbar with real import/export"""
    
    def __init__(self, db):
        self.db = db
        self.import_export = ImportExportManager(db)
        
        # Callbacks
        self.on_save = None
        self.on_reload = None
        self.on_debug = None
        self.on_export = None
        self.on_import = None
        self.on_menu_name_changed = None
        self.on_menu_selected = None
        
        # UI widgets
        self.save_btn = None
        self.reload_btn = None
        self.debug_btn = None
        self.export_btn = None
        self.import_btn = None
        self.status_label = None
        self.menu_combo = None
        self.unsaved_indicator = None
        
        # Current menu ID
        self.current_menu_id = None
    
    def create_toolbar(self):
        """Create the enhanced toolbar"""
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        toolbar.set_margin_top(5)
        toolbar.set_margin_bottom(5)
        toolbar.set_margin_start(5)
        toolbar.set_margin_end(5)
        
        # Menu selector with dropdown
        name_label = Gtk.Label(label="📋 Menu:")
        toolbar.pack_start(name_label, False, False, 0)
        
        self.menu_combo = Gtk.ComboBoxText()
        self.menu_combo.set_tooltip_text("Select menu to edit")
        self.menu_combo.set_size_request(150, -1)
        self.menu_combo.connect("changed", self._on_menu_selected)
        
        # Load menus
        self._load_menus()
        
        toolbar.pack_start(self.menu_combo, False, False, 0)
        
        # New menu button
        new_menu_btn = Gtk.Button.new_with_label("+")
        new_menu_btn.set_tooltip_text("Create new menu")
        new_menu_btn.set_size_request(30, -1)
        new_menu_btn.connect("clicked", self._on_new_menu)
        toolbar.pack_start(new_menu_btn, False, False, 0)
        
        # Separator
        toolbar.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 5)
        
        # Export button
        self.export_btn = Gtk.Button.new_with_label("📤 Export")
        self.export_btn.set_tooltip_text("Export menu to file")
        self.export_btn.connect("clicked", self._on_export_clicked)
        toolbar.pack_start(self.export_btn, False, False, 0)
        
        # Import button
        self.import_btn = Gtk.Button.new_with_label("📥 Import")
        self.import_btn.set_tooltip_text("Import menu from file")
        self.import_btn.connect("clicked", self._on_import_clicked)
        toolbar.pack_start(self.import_btn, False, False, 0)
        
        # Separator
        toolbar.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 5)
        
        # Workspaces button 
        self.debug_btn = Gtk.Button.new_with_label("🗺️ Workspaces")
        self.debug_btn.set_tooltip_text("Window positioning and workspaces")
        self.debug_btn.connect("clicked", self._on_debug_clicked)
        toolbar.pack_start(self.debug_btn, False, False, 0)
        
        # Separator
        toolbar.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 5)
        
        # Status area (expands)
        self.status_label = Gtk.Label(label="Ready")
        self.status_label.set_xalign(0)
        self.status_label.get_style_context().add_class("dim-label")
        toolbar.pack_start(self.status_label, True, True, 0)
        
        # Unsaved changes indicator
        self.unsaved_indicator = Gtk.Label(label="")
        self.unsaved_indicator.set_markup("<span foreground='orange' size='large'>●</span>")
        self.unsaved_indicator.set_tooltip_text("Unsaved changes")
        self.unsaved_indicator.set_visible(False)
        toolbar.pack_end(self.unsaved_indicator, False, False, 5)
        
        return toolbar
    
    def _load_menus(self):
        """Load all menus from database into dropdown"""
        self.menu_combo.remove_all()
        
        try:
            menus = self.db.fetch_all("SELECT id, name, is_default FROM menus ORDER BY name")
            for menu in menus:
                display = f"{menu['name']}"
                if menu['is_default']:
                    display += " ★"
                self.menu_combo.append(display, str(menu['id']))
        except Exception as e:
            print(f"❌ Error loading menus: {e}")
    
    def set_current_menu(self, menu_id: int, menu_name: str):
        """Set the current menu in the dropdown"""
        self.current_menu_id = menu_id
        
        # Find and select this menu in the combo
        model = self.menu_combo.get_model()
        iter = model.get_iter_first()
        i = 0
        while iter:
            value = model.get_value(iter, 1)  # ID is in column 1
            if value == str(menu_id):
                self.menu_combo.set_active(i)
                break
            iter = model.iter_next(iter)
            i += 1
    
    def _on_menu_selected(self, combo):
        """Handle menu selection from dropdown"""
        menu_id_str = combo.get_active_id()
        if menu_id_str and self.on_menu_selected:
            try:
                menu_id = int(menu_id_str)
                self.on_menu_selected(menu_id)
            except ValueError:
                pass
    
    def _on_new_menu(self, button):
        """Create new menu"""
        dialog = Gtk.Dialog(
            title="New Menu",
            parent=None,
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            "Create", Gtk.ResponseType.OK
        )
        
        content = dialog.get_content_area()
        entry = Gtk.Entry()
        entry.set_placeholder_text("Menu name")
        entry.set_margin_top(10)
        entry.set_margin_bottom(10)
        entry.set_margin_start(10)
        entry.set_margin_end(10)
        content.pack_start(entry, True, True, 0)
        
        dialog.show_all()
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            menu_name = entry.get_text().strip()
            if menu_name:
                # Create new menu in DB
                self.db.execute(
                    "INSERT INTO menus (name) VALUES (?)",
                    (menu_name,)
                )
                result = self.db.fetch_one("SELECT last_insert_rowid() AS id")
                new_id = result['id']
                
                # Refresh dropdown
                self._load_menus()
                
                # Select new menu
                self.set_current_menu(new_id, menu_name)
                
                if self.on_menu_selected:
                    self.on_menu_selected(new_id)
        
        dialog.destroy()
    
    def _on_export_clicked(self, button):
        """Handle export button click"""
        if not self.current_menu_id:
            self.show_message("No menu selected", 2)
            return
        
        # Create format selection dialog
        dialog = Gtk.Dialog(
            title="Export Menu",
            parent=None,
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            "Export", Gtk.ResponseType.OK
        )
        
        dialog.set_default_size(400, 200)
        
        content = dialog.get_content_area()
        
        # Format selection
        format_label = Gtk.Label(label="<b>Export Format:</b>")
        format_label.set_use_markup(True)
        format_label.set_xalign(0)
        content.pack_start(format_label, False, False, 5)
        
        format_combo = Gtk.ComboBoxText()
        for fmt in self.import_export.get_supported_formats():
            format_combo.append(fmt["id"], fmt["name"])
        format_combo.set_active(0)  # JSON is first
        
        format_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        format_box.pack_start(Gtk.Label(label="Format:"), False, False, 0)
        format_box.pack_start(format_combo, False, False, 0)
        content.pack_start(format_box, False, False, 5)
        
        content.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 10)
        
        # Get menu name for default filename
        menu = self.db.fetch_one(
            "SELECT name FROM menus WHERE id = ?",
            (self.current_menu_id,)
        )
        menu_name = menu['name'] if menu else "menu"
        safe_name = "".join(c for c in menu_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        default_name = f"{safe_name}_export.json"
        
        # File chooser
        file_chooser = Gtk.FileChooserButton(title="Select Export Location")
        file_chooser.set_current_name(default_name)
        
        # Add filters for each format
        for fmt in self.import_export.get_supported_formats():
            filter = Gtk.FileFilter()
            filter.set_name(f"{fmt['name']} files")
            filter.add_pattern(f"*{fmt['extension']}")
            file_chooser.add_filter(filter)
        
        content.pack_start(file_chooser, False, False, 5)
        
        dialog.show_all()
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            filename = file_chooser.get_filename()
            format_id = format_combo.get_active_id()
            
            if filename:
                try:
                    # Ensure correct extension
                    fmt_info = self.import_export.format_info(format_id)
                    if not filename.endswith(fmt_info['extension']):
                        filename += fmt_info['extension']
                    
                    # Do the export
                    self.show_message("Exporting...")
                    self.import_export.export_to_file(self.current_menu_id, filename, format_id)
                    
                    self.show_message(f"Exported to {Path(filename).name}", 3)
                    print(f"✅ Exported menu {self.current_menu_id} to {filename}")
                    
                except Exception as e:
                    error_msg = f"Export failed: {str(e)}"
                    self.show_message(error_msg, 3)
                    print(f"❌ Export error: {e}")
                    
                    # Show error dialog
                    error_dialog = Gtk.MessageDialog(
                        parent=dialog,
                        flags=0,
                        message_type=Gtk.MessageType.ERROR,
                        buttons=Gtk.ButtonsType.OK,
                        text="Export Failed"
                    )
                    error_dialog.format_secondary_text(str(e))
                    error_dialog.run()
                    error_dialog.destroy()
        
        dialog.destroy()
    
    def _on_import_clicked(self, button):
        """Handle import button click"""
        # Create file chooser dialog
        dialog = Gtk.FileChooserDialog(
            title="Import Menu",
            parent=None,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            "Import", Gtk.ResponseType.OK
        )
        
        # Add filters for supported formats
        for fmt in self.import_export.get_supported_formats():
            filter = Gtk.FileFilter()
            filter.set_name(f"{fmt['name']} files (*{fmt['extension']})")
            filter.add_pattern(f"*{fmt['extension']}")
            dialog.add_filter(filter)
        
        # All supported files filter
        all_filter = Gtk.FileFilter()
        all_filter.set_name("All supported files")
        for fmt in self.import_export.get_supported_formats():
            all_filter.add_pattern(f"*{fmt['extension']}")
        dialog.add_filter(all_filter)
        
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            
            if filename and os.path.exists(filename):
                # Ask for menu name
                name_dialog = Gtk.Dialog(
                    title="Import Menu Name",
                    parent=dialog,
                    flags=0
                )
                name_dialog.add_buttons(
                    Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                    "Import", Gtk.ResponseType.OK
                )
                
                content = name_dialog.get_content_area()
                
                # Suggest name based on filename
                suggested_name = Path(filename).stem.replace('_', ' ').title()
                
                name_label = Gtk.Label(label="<b>Menu Name:</b>")
                name_label.set_use_markup(True)
                name_label.set_xalign(0)
                content.pack_start(name_label, False, False, 5)
                
                name_entry = Gtk.Entry()
                name_entry.set_text(suggested_name)
                name_entry.set_margin_top(5)
                name_entry.set_margin_bottom(10)
                content.pack_start(name_entry, True, True, 0)
                
                name_dialog.show_all()
                name_response = name_dialog.run()
                menu_name = name_entry.get_text().strip() if name_response == Gtk.ResponseType.OK else None
                
                name_dialog.destroy()
                
                if menu_name:
                    try:
                        self.show_message("Importing...")
                        
                        # Do the import
                        new_menu_id = self.import_export.import_from_file(filename, menu_name)
                        
                        self.show_message(f"Imported '{menu_name}'", 3)
                        print(f"✅ Imported menu from {filename} as ID {new_menu_id}")
                        
                        # Refresh menu list and select new menu
                        self._load_menus()
                        self.set_current_menu(new_menu_id, menu_name)
                        
                        if self.on_menu_selected:
                            self.on_menu_selected(new_menu_id)
                            
                    except Exception as e:
                        error_msg = f"Import failed: {str(e)}"
                        self.show_message(error_msg, 3)
                        print(f"❌ Import error: {e}")
                        
                        # Show error dialog
                        error_dialog = Gtk.MessageDialog(
                            parent=dialog,
                            flags=0,
                            message_type=Gtk.MessageType.ERROR,
                            buttons=Gtk.ButtonsType.OK,
                            text="Import Failed"
                        )
                        error_dialog.format_secondary_text(str(e))
                        error_dialog.run()
                        error_dialog.destroy()
        
        dialog.destroy()
    
    def show_message(self, message: str, duration: int = 3):
        """Show a message in the status area"""
        self.status_label.set_text(message)
        if duration > 0:
            GLib.timeout_add_seconds(duration, self._clear_message)
    
    def _clear_message(self):
        """Clear the status message"""
        self.status_label.set_text("Ready")
        return False
    
    def set_unsaved_changes(self, has_changes: bool):
        """Update unsaved changes indicator"""
        self.unsaved_indicator.set_visible(has_changes)
        if has_changes:
            self.status_label.set_text("Unsaved changes")
