"""
Enhanced toolbar with menu selector
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import os
from datetime import datetime
from typing import Optional


class Toolbar:
    """Enhanced toolbar with menu selector"""
    
    def __init__(self, db):
        self.db = db
        
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
        
        # Save button
        self.save_btn = Gtk.Button.new_with_label("💾 Save")
        self.save_btn.set_tooltip_text("Save all changes to database")
        self.save_btn.connect("clicked", self._on_save_clicked)
        toolbar.pack_start(self.save_btn, False, False, 0)
        
        # Reload button
        self.reload_btn = Gtk.Button.new_with_label("🔄 Reload")
        self.reload_btn.set_tooltip_text("Reload from database (discard changes)")
        self.reload_btn.connect("clicked", self._on_reload_clicked)
        toolbar.pack_start(self.reload_btn, False, False, 0)
        
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
    
    def _on_save_clicked(self, button):
        if self.on_save:
            self.on_save()
    
    def _on_reload_clicked(self, button):
        if self.on_reload:
            self.on_reload()
    
    def _on_debug_clicked(self, button):
        if self.on_debug:
            self.on_debug()
    
    def _on_export_clicked(self, button):
        if self.on_export:
            self.on_export()
        else:
            self._export_stub()
    
    def _on_import_clicked(self, button):
        if self.on_import:
            self.on_import()
        else:
            self._import_stub()
    
    def _export_stub(self):
        """Stub export implementation"""
        dialog = Gtk.FileChooserDialog(
            title="Export Menu",
            parent=None,
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            "Export", Gtk.ResponseType.OK
        )
        
        default_name = f"gmen_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        dialog.set_current_name(default_name)
        
        filter_json = Gtk.FileFilter()
        filter_json.set_name("JSON files")
        filter_json.add_pattern("*.json")
        dialog.add_filter(filter_json)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            self.show_message(f"Would export to: {filename}")
        
        dialog.destroy()
    
    def _import_stub(self):
        """Stub import implementation"""
        dialog = Gtk.FileChooserDialog(
            title="Import Menu",
            parent=None,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            "Import", Gtk.ResponseType.OK
        )
        
        filter_json = Gtk.FileFilter()
        filter_json.set_name("JSON files")
        filter_json.add_pattern("*.json")
        dialog.add_filter(filter_json)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            self.show_message(f"Would import from: {filename}")
        
        dialog.destroy()
    
    def show_message(self, message: str, duration: int = 3):
        """Show a message in the status area"""
        self.status_label.set_text(message)
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
