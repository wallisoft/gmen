"""
Three Panel Editor - Left, Middle, Right click menus
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import os
from pathlib import Path
from storage.import_export import ImportExportManager
from ui.editor.simple_list_manager import SimpleListManager
from ui.editor.property_panel import PropertyPanel


class ThreePanelWindow:
    def __init__(self, db):
        self.db = db
        self.import_export = ImportExportManager(db)

        self.current_filename = None 
        self.original_menu_names = {} 
        
        # Get or create menus based on what exists
        self.menu_ids = self._ensure_three_menus()
        
        # Create list managers
        self.left_panel = SimpleListManager(db, self.menu_ids['left'])
        self.middle_panel = SimpleListManager(db, self.menu_ids['middle'])
        self.right_panel = SimpleListManager(db, self.menu_ids['right'])
        
        # Panels dict
        self.panels = {
            'left': self.left_panel,
            'middle': self.middle_panel, 
            'right': self.right_panel
        }
        
        # Property panel
        self.property_panel = PropertyPanel(db)
        self.property_panel.on_property_changed = self._on_property_changed

        # Active panel (starts with left panel)
        self.active_panel = 'left'
        
        self.panel_headers = {}  # Add this with other attributes

        # Frame widgets for color highlighting
        self.panel_frames = {}
        
        # Flag to prevent event loops
        self._updating_selection = False
        
        # Unsaved changes flag
        self.has_unsaved_changes = False

        self.save_btn = None  
        
        # Create UI
        self._create_ui()
        self._connect_events()
        
        # Highlight left panel as active
        self._highlight_active_panel()
        
        # Load data WITHOUT selecting first item yet
        # Let the UI initialize first
        GLib.timeout_add(100, self._delayed_load)
    
    def _delayed_load(self):
        """Load data after UI is fully initialized"""
        self._load_data()
        return False
    
    def _load_data(self):
        """Load data for all panels without triggering selection loops"""
        print("📋 Loading data for all panels...")
        # Block selection updates during initial load
        self._updating_selection = True
        
        # Load each panel
        self.left_panel._load()
        self.middle_panel._load()
        self.right_panel._load()
        
        # Now select first item in left panel
        self._select_first_item_safe('left')
        
        # Update menu name
        self._update_menu_name()
        
        # Re-enable selection updates
        self._updating_selection = False
        print("✅ Data loaded")
    
    def _ensure_three_menus(self):
        """Get or create THREE SEPARATE menus for three panels"""
        # Get all existing menus
        all_menus = self.db.get_all_menus()
        print(f"📊 Found {len(all_menus)} existing menus")
        
        # Default menu names - make them unique if needed
        default_names = [
            ("Left Click Menu", "Left click applications"),
            ("Middle Click Menu", "Middle click system tools"), 
            ("Right Click Menu", "Right click power user")
        ]
        
        # We need exactly 3 menu IDs
        menu_ids = []
        
        # Use existing menus first (up to 3)
        for i in range(min(3, len(all_menus))):
            menu_ids.append(all_menus[i]['id'])
            print(f"📋 Using existing menu {i+1}: '{all_menus[i]['name']}' (ID: {all_menus[i]['id']})")
        
        # Create missing menus with UNIQUE names
        for i in range(len(menu_ids), 3):
            base_name, base_desc = default_names[i]
            
            # Find a unique name
            name = base_name
            counter = 1
            while True:
                existing = self.db.get_menu(name)
                if not existing:
                    break  # Name is available
                name = f"{base_name} {counter}"
                counter += 1
            
            # Create with unique name
            menu_id = self.db.create_menu(name, base_desc)
            menu_ids.append(menu_id)
            print(f"📋 Created new menu: '{name}' (ID: {menu_id})")
        
        # Assign to panels
        menus = {
            'left': menu_ids[0],
            'middle': menu_ids[1], 
            'right': menu_ids[2]
        }
        
        print(f"✅ Menu assignments: {menus}")
        return menus
    
    def _create_ui(self):
        self.window = Gtk.Window()
        self.window.set_title("GMen Editor")
        self.window.set_default_size(1200, 700)
        self.window.connect("destroy", self._on_window_destroy)
        
        # Main container
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_vbox.get_style_context().add_class("main-container")
        self.window.add(main_vbox)
        
        # === TOOLBAR ===
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        toolbar.get_style_context().add_class("toolbar")
        toolbar.set_margin_top(8)
        toolbar.set_margin_bottom(8)
        toolbar.set_margin_start(16)
        toolbar.set_margin_end(16)
        
        # Menu selector
        self.menu_button = Gtk.Button.new_with_label("☰ Menu")
        self.menu_button.set_tooltip_text("Show all menus")
        self.menu_button.connect("clicked", self._show_all_menus_dialog)
        toolbar.pack_start(self.menu_button, False, False, 0)
        
        self.menu_name_entry = Gtk.Entry()
        self.menu_name_entry.set_placeholder_text("Menu name...")
        self.menu_name_entry.set_width_chars(20)
        self.menu_name_entry.connect("changed", self._on_menu_name_changed)
        self.menu_name_entry.connect("activate", self._on_menu_name_activated)
        toolbar.pack_start(self.menu_name_entry, False, False, 0)
        
        # Spacer
        toolbar.pack_start(Gtk.Box(), True, True, 0)
        
        # Action buttons - compact group
        for label, tooltip, callback in [
            ("Export", "Export active menu", self._on_export),
            ("Import", "Import menu file", self._on_import),
            ("Workspaces", "Window positioning", self._on_layout),
            ("Settings", "Configure mouse & keys", self._show_config_dialog),
        ]:
            btn = Gtk.Button.new_with_label(label)
            btn.set_tooltip_text(tooltip)
            btn.connect("clicked", callback)
            toolbar.pack_start(btn, False, False, 0)
        
        # Unsaved indicator
        self.toolbar_unsaved = Gtk.Label()
        self.toolbar_unsaved.set_markup("<span foreground='#e67700' size='large'>●</span>")
        self.toolbar_unsaved.set_tooltip_text("Unsaved changes")
        self.toolbar_unsaved.set_visible(False)
        toolbar.pack_end(self.toolbar_unsaved, False, False, 8)
        
        main_vbox.pack_start(toolbar, False, False, 0)
        
        # Toolbar separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        main_vbox.pack_start(sep, False, False, 0)
        
        # === MAIN CONTENT ===
        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        content.set_margin_top(16)
        content.set_margin_bottom(8)
        content.set_margin_start(16)
        content.set_margin_end(16)
        main_vbox.pack_start(content, True, True, 0)
        
        # === LEFT: Menu panels + controls ===
        left_side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        # Three menu panels in a row
        panels_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        
        for panel_key, label_text in [
            ('left', "-  Left Click  -"),
            ('middle', "-  Middle Click  -"),
            ('right', "-  Right Click  -")
        ]:
            # Panel container
            panel_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            
            # Header - just text, no background
            header = Gtk.Label()
            header.set_markup(f"<b>{label_text}</b>")
            header.set_xalign(0)
            header.get_style_context().add_class("panel-header")
            panel_box.pack_start(header, False, False, 0)
            self.panel_headers[panel_key] = header
            
            # List container - this gets the border
            list_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            list_frame.get_style_context().add_class("panel-frame")
            list_frame.get_style_context().add_class("inactive-panel")
            
            # Scrolled list
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            scrolled.set_min_content_height(200)
            
            panel = self.panels[panel_key]
            scrolled.add(panel.listbox)
            
            # Event box for click handling
            event_box = Gtk.EventBox()
            event_box.add(scrolled)
            event_box.connect("button-press-event", self._on_frame_clicked, panel_key)
            
            list_frame.pack_start(event_box, True, True, 0)
            panel_box.pack_start(list_frame, True, True, 0)
            
            panels_box.pack_start(panel_box, True, True, 0)
            self.panel_frames[panel_key] = list_frame
        
        left_side.pack_start(panels_box, True, True, 0)
        
        # === CONTROL BUTTONS ===
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        controls.set_halign(Gtk.Align.CENTER)
        controls.set_margin_top(8)
        
        # Button configurations: (label, tooltip, callback)
        button_configs = [
            ("+ Add", "Add item after selected", self._on_add),
            ("~ Ins", "Insert another menu's items here", self._on_insert_menu),
            ("− Del", "Delete selected item", self._on_delete),
            ("↑", "Move up", self._on_up),
            ("↓", "Move down", self._on_down),
            ("→", "Indent (make child)", self._on_indent),
            ("←", "Outdent (make parent)", self._on_outdent),
        ]
        
        for label, tooltip, callback in button_configs:
            btn = Gtk.Button.new_with_label(label)
            btn.set_tooltip_text(tooltip)
            btn.connect("clicked", callback)
            btn.get_style_context().add_class("control-button")
            
            # Set different widths for text vs icon buttons
            if len(label) > 2:  # Text buttons
                btn.set_size_request(70, -1)
            else:  # Icon buttons
                btn.set_size_request(40, -1)
            
            controls.pack_start(btn, False, False, 0)
        
        left_side.pack_start(controls, False, False, 0)
        
        content.pack_start(left_side, True, True, 0)
        
        # === RIGHT: Property panel ===
        prop_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        
        prop_header = Gtk.Label()
        prop_header.set_markup("<b>-  Properties  -</b>")
        prop_header.set_xalign(0)
        prop_header.get_style_context().add_class("panel-header")
        prop_container.pack_start(prop_header, False, False, 0)
        
        prop_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        prop_frame.get_style_context().add_class("panel-frame")
        prop_frame.get_style_context().add_class("inactive-panel")
        prop_frame.set_size_request(350, -1)
        
        prop_contents = self.property_panel.create_panel_contents()
        prop_frame.pack_start(prop_contents, True, True, 8)
        
        prop_container.pack_start(prop_frame, True, True, 0)
        content.pack_start(prop_container, False, False, 0)
            
        # === BOTTOM STATUS BAR ===
        status_sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        main_vbox.pack_start(status_sep, False, False, 0)
        
        status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        status_bar.get_style_context().add_class("status-bar")
        status_bar.set_margin_top(8)
        status_bar.set_margin_bottom(8)
        status_bar.set_margin_start(16)
        status_bar.set_margin_end(16)
        
        self.status_label = Gtk.Label(label="Ready")
        self.status_label.set_xalign(0)
        self.status_label.get_style_context().add_class("status-text")
        status_bar.pack_start(self.status_label, True, True, 0)
        
        # Save button
        self.save_btn = Gtk.Button.new_with_label("Save")
        self.save_btn.set_tooltip_text("Save all changes")
        self.save_btn.connect("clicked", self._on_save)
        self.save_btn.set_size_request(80, -1)
        status_bar.pack_start(self.save_btn, False, False, 0)
        
        for label, tooltip, callback in [
            ("Reload", "Discard changes", self._on_reload),
            ("Exit", "Close editor", self._on_exit),
        ]:
            btn = Gtk.Button.new_with_label(label)
            btn.set_tooltip_text(tooltip)
            btn.connect("clicked", callback)
            status_bar.pack_start(btn, False, False, 0)
        
        main_vbox.pack_start(status_bar, False, False, 0)
        
        self.window.show_all()
        self._apply_css()
   
    def _show_all_menus_dialog(self, button):
        """Show advanced menu manager"""
        from ui.editor.menu_manager import MenuManagerDialog
        manager = MenuManagerDialog(self.db, self.window)
        response = manager.run()

        # Check if a menu was selected
        if response == Gtk.ResponseType.OK and hasattr(manager.dialog, 'selected_menu_id'):
            selected_id = manager.dialog.selected_menu_id
            selected_name = manager.dialog.selected_menu_name

            print(f"🔄 Switching to menu: {selected_name} (ID: {selected_id})")

            # Find which panel to update (use active panel)
            panel = self.panels[self.active_panel]
            old_menu_id = panel.menu_id

            # Update panel to use selected menu
            panel.menu_id = selected_id
            self.menu_ids[self.active_panel] = selected_id

            # Reload panel with new menu
            panel._load()

            # Update menu name display
            self._update_menu_name()

            # Show message
            self.show_message(f"Switched to: {selected_name}", 3)

            # Mark as unsaved (configuration changed)
            self.set_unsaved_changes(True)

        # Always refresh our panels (in case menus were added/deleted)
        self._load_data()
        print("🔄 Menus updated, refreshing...")

    def _update_menu_name(self):
        """Update menu name entry with active panel's menu name"""
        panel = self.panels[self.active_panel]
        menu = self.db.fetch_one(
            "SELECT name FROM menus WHERE id = ?",
        (panel.menu_id,)
        )
        if menu:
            # Temporarily block signals to prevent loop
            self.menu_name_entry.handler_block_by_func(self._on_menu_name_changed)
            self.menu_name_entry.set_text(menu['name'])
            self.menu_name_entry.handler_unblock_by_func(self._on_menu_name_changed)
    
    def _on_menu_name_changed(self, entry):
        """Handle menu name change"""
        new_name = entry.get_text().strip()
        if new_name:
            panel = self.panels[self.active_panel]
            original_name = self.original_menu_names.get(panel.menu_id)
            
            if original_name != new_name:
                print(f"📝 Menu renamed: {original_name} → {new_name}")
                self.set_unsaved_changes(True)

    def _on_menu_name_activated(self, entry):
        """Handle Enter key in menu name entry - save the name"""
        new_name = entry.get_text().strip()
        if new_name:
            panel = self.panels[self.active_panel]
            
            # Update in database
            self.db.execute(
                "UPDATE menus SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_name, panel.menu_id)
            )
            
            # Update frame label
            frame = self.panel_frames[self.active_panel]
            frame.set_label(new_name)
            
            self.show_message(f"Menu renamed to '{new_name}'", 2)
            print(f"✅ Renamed menu {panel.menu_id} to '{new_name}'")
            
            self.set_unsaved_changes(True)
    
    def _on_frame_clicked(self, event_box, event, panel_key):
        """Handle frame click to activate panel - CLEAR OTHER PANELS"""
        print(f"🖱️ Frame clicked: {panel_key}")
        
        # Update active panel
        old_active = self.active_panel
        self.active_panel = panel_key
        
        # Update visual highlighting
        if old_active != panel_key:
            self._highlight_active_panel()
            # Update menu name when panel changes
            self._update_menu_name()
        
        # CLEAR SELECTION IN OTHER PANELS
        for other_key, other_panel in self.panels.items():
            if other_key != panel_key:
                other_panel.selected_id = None
                other_panel._refresh_listbox()
        
        # Select first item in active panel if it has items
        panel = self.panels[panel_key]
        if panel.items:
            # Only select first item if nothing is selected
            if not panel.selected_id:
                self._select_first_item_safe(panel_key)
        else:
            # No items - add one automatically AND SELECT IT
            print(f"📝 No items in {panel_key} menu, adding one...")
            new_item = panel.add_item()
            self._delayed_load_new_item(panel_key, new_item['id'])
        
        return True
    
    def _select_first_item_safe(self, panel_key):
        """Select first item in a panel without triggering loops"""
        panel = self.panels[panel_key]
        if panel.items:
            panel.selected_id = panel.items[0]['id']
            
            # Load into property panel
            GLib.timeout_add(50, self._delayed_load_item, panel_key)
    
# In three_panel_window.py, update these key methods:

    def _delayed_load_item(self, panel_key):
        """Load item into property panel after UI is ready"""
        panel = self.panels[panel_key]
        if panel.items and panel.selected_id:
            for item in panel.items:
                if item['id'] == panel.selected_id:
                    # Create a SimpleMenuItem wrapper with instances
                    class SimpleMenuItem:
                        def __init__(self, id, title, command, icon, db_id, instances=None):
                            self.id = id
                            self.title = title
                            self.command = command or ""
                            self.icon = icon or ""
                            self.db_id = db_id
                            self.depth = item.get('depth', 0)
                            self.window_state = None
                            self.instances = instances or []
                            self._is_initial_load = True
                        
                        def is_script(self):
                            return self.command.startswith('@') if self.command else False
                    
                    # Use first instance's command/icon for compatibility
                    first_command = item['instances'][0]['command'] if item['instances'] else ''
                    first_icon = item['instances'][0]['icon'] if item['instances'] else ''
                    
                    menu_item = SimpleMenuItem(
                        id=item['id'],
                        title=item['title'],
                        command=first_command,
                        icon=first_icon,
                        db_id=item.get('db_id'),
                        instances=item['instances']  # Pass all instances!
                    )
                    
                    print(f"📋 Loading item into property panel: {item['title'][:20]}...")
                    self.property_panel.load_item(menu_item)
                    break
        return False

    def _delayed_load_new_item(self, panel_key, item_id):
        """Load newly added item into property panel"""
        GLib.timeout_add(50, self._load_specific_item, panel_key, item_id)

    def _load_specific_item(self, panel_key, item_id):
        """Load specific item into property panel - FIXED VERSION"""
        panel = self.panels[panel_key]
        for item in panel.items:
            if item['id'] == item_id:
                class SimpleMenuItem:
                    def __init__(self, id, title, command, icon, db_id, instances=None):
                        self.id = id
                        self.title = title
                        self.command = command or ""
                        self.icon = icon or ""
                        self.db_id = db_id
                        self.depth = item.get('depth', 0)
                        self.window_state = None
                        self.instances = instances or []
                        self._is_initial_load = True

                    def is_script(self):
                        return self.command.startswith('@') if self.command else False

                # FIX: Get command/icon from instances, not item root
                first_command = item['instances'][0]['command'] if item['instances'] else ''
                first_icon = item['instances'][0]['icon'] if item['instances'] else ''

                menu_item = SimpleMenuItem(
                    id=item['id'],
                    title=item['title'],
                    command=first_command,  # FROM INSTANCE
                    icon=first_icon,        # FROM INSTANCE
                    db_id=item.get('db_id'),
                    instances=item['instances']
                )

                print(f"📋 Loading new item into property panel: {item['title'][:20]}...")
                self.property_panel.load_item(menu_item)
                break
        return False

    def _on_panel_selected(self, panel_key, row):
        """Handle when a panel gets selection from listbox"""
        if self._updating_selection:
            return
        
        # Update active panel if different
        if self.active_panel != panel_key:
            old_active = self.active_panel
            self.active_panel = panel_key
            if old_active != panel_key:
                self._highlight_active_panel()
                self._update_menu_name()
            
            # CLEAR SELECTION IN OTHER PANELS
            for other_key, other_panel in self.panels.items():
                if other_key != panel_key:
                    other_panel.selected_id = None
                    other_panel._refresh_listbox()
        
        # Load selected item into property panel
        if row and hasattr(row, 'item_id'):
            panel = self.panels[panel_key]
            # Set the flag temporarily to prevent loops
            self._updating_selection = True
            panel.selected_id = row.item_id
            item = panel.get_selected_item()
            if item:
                # Create a SimpleMenuItem wrapper with instances
                class SimpleMenuItem:
                    def __init__(self, id, title, command, icon, db_id, instances=None):
                        self.id = id
                        self.title = title
                        self.command = command or ""
                        self.icon = icon or ""
                        self.db_id = db_id
                        self.depth = item.get('depth', 0)
                        self.window_state = None
                        self.instances = instances or []
                        self._is_initial_load = False
                    
                    def is_script(self):
                        return self.command.startswith('@') if self.command else False
                
                first_command = item['instances'][0]['command'] if item['instances'] else ''
                first_icon = item['instances'][0]['icon'] if item['instances'] else ''
                
                menu_item = SimpleMenuItem(
                    id=item['id'],
                    title=item['title'],
                    command=first_command,
                    icon=first_icon,
                    db_id=item.get('db_id'),
                    instances=item['instances']
                )
                
                print(f"📋 Loading selected item into property panel: {item['title'][:20]}...")
                self.property_panel.load_item(menu_item)
            self._updating_selection = False

    def _on_property_changed(self, item_id, field, value, instance_idx=0):
        """Handle property changes - now per instance!"""
        if not self.active_panel or self._updating_selection:
            return
        
        panel = self.panels[self.active_panel]
        
        # Pass all parameters to list manager
        kwargs = {field: value}
        if field in ['window_state', 'add_instance', 'remove_instance']:
            if field == 'window_state':
                kwargs['instance_idx'] = instance_idx
            elif field == 'remove_instance':
                kwargs['remove_instance'] = value
        
        success = panel.update_item(item_id, **kwargs)
        
        if success:
            self.set_unsaved_changes(True)
            print(f"✅ Property changed: {field} for item {item_id}, instance {instance_idx}")
        else:
            print(f"⚠️ Failed to update item {item_id}")
    
    def _delayed_load_new_item(self, panel_key, item_id):
        """Load newly added item into property panel"""
        GLib.timeout_add(50, self._load_specific_item, panel_key, item_id)
    
    def _load_specific_item(self, panel_key, item_id):
        """Load specific item into property panel"""
        panel = self.panels[panel_key]
        for item in panel.items:
            if item['id'] == item_id:
                class SimpleMenuItem:
                    def __init__(self, id, title, command, icon, db_id):
                        self.id = id
                        self.title = title
                        self.command = command or ""
                        self.icon = icon or ""
                        self.db_id = db_id
                        self.depth = item.get('depth', 0)
                        self.window_state = None
                        self._is_initial_load = True
                    
                    def is_script(self):
                        return self.command.startswith('@') if self.command else False
                
                menu_item = SimpleMenuItem(
                    id=item['id'],
                    title=item['title'],
                    command=item['command'],
                    icon=item['icon'],
                    db_id=item.get('db_id')
                )
                print(f"📋 Loading new item into property panel: {item['title'][:20]}...")
                self.property_panel.load_item(menu_item)
                break
        return False
    
    def _get_active_panel(self):
        """Get the currently active panel object"""
        return self.panels[self.active_panel]
    
    # === CONTROL BUTTON HANDLERS ===
    
    def _on_add(self, button):
        panel = self._get_active_panel()
        panel.add_item()
        self.set_unsaved_changes(True)
    
    def _on_delete(self, button):
        panel = self._get_active_panel()
        panel.delete_item()
        self.set_unsaved_changes(True)
    
    def _on_up(self, button):
        panel = self._get_active_panel()
        panel.move_up()
        self.set_unsaved_changes(True)
    
    def _on_down(self, button):
        panel = self._get_active_panel()
        panel.move_down()
        self.set_unsaved_changes(True)
    
    def _on_indent(self, button):
        panel = self._get_active_panel()
        panel.indent()
        self.set_unsaved_changes(True)
    
    def _on_outdent(self, button):
        panel = self._get_active_panel()
        panel.outdent()
        self.set_unsaved_changes(True)

    def _on_insert_menu(self, button):
        """Insert another menu's items under selected item"""
        panel = self._get_active_panel()
        selected_item = panel.get_selected_item()
        
        if not selected_item:
            self.show_message("Select an item to insert under", 2)
            return
        
        # REUSE the existing MenuManagerDialog as a picker!
        from ui.editor.menu_manager import MenuManagerDialog
        picker = MenuManagerDialog(self.db, self.window)
        
        # Modify dialog title for context
        picker.dialog.set_title("📁 Insert Menu Items")
        
        response = picker.run()
        
        if response == Gtk.ResponseType.OK and hasattr(picker.dialog, 'selected_menu_id'):
            source_menu_id = picker.dialog.selected_menu_id
            source_menu_name = picker.dialog.selected_menu_name
            
            # Prevent inserting same menu into itself
            if source_menu_id == panel.menu_id:
                self.show_message("Cannot insert a menu into itself", 2)
                return
            
            print(f"📋 Inserting menu '{source_menu_name}' under '{selected_item['title']}'")
            
            # Get items from source menu
            source_items = self.db.get_menu_items(source_menu_id, active_only=True)
            
            if not source_items:
                self.show_message(f"Menu '{source_menu_name}' is empty", 2)
                return
            
            # Find insertion point
            insert_index = None
            for i, item in enumerate(panel.items):
                if item['id'] == selected_item['id']:
                    insert_index = i + 1
                    break
            
            if insert_index is None:
                insert_index = len(panel.items)  # Append at end
            
            # Insert items with increased depth
            import uuid
            source_depth = selected_item.get('depth', 0)
            items_added = 0
            
            for source_item in source_items:
                new_id = str(uuid.uuid4())[:8]
                panel.items.insert(insert_index, {
                    'id': new_id,
                    'db_id': None,
                    'title': source_item['title'],
                    'command': source_item['command'],
                    'icon': source_item.get('icon', ''),
                    'depth': source_depth + 1,  # One level deeper
                    'parent_db_id': None
                })
                insert_index += 1
                items_added += 1
            
            # Refresh and mark unsaved
            panel._refresh_listbox()
            self.set_unsaved_changes(True)
            self.show_message(f"Inserted {items_added} items from '{source_menu_name}'", 3)
            print(f"✅ Inserted {items_added} items")
    
    # === PROPERTY HANDLER ===

    def _on_property_changed(self, item_id, field, value, instance_idx=0):
        if not self.active_panel or self._updating_selection:
            return
        
        panel = self.panels[self.active_panel]
        
        # Pass all data to the list manager
        kwargs = {field: value}
        if field == 'window_state':
            kwargs['instance_idx'] = instance_idx
        
        panel.update_item(item_id, **kwargs)
        self.set_unsaved_changes(True)
            
        # === EVENT HANDLERS ===

    def _connect_events(self):
        """Connect panel selection events"""
        def make_handler(panel_key):
            def handler(widget, row):
                return self._on_panel_selected(panel_key, row)
            return handler
        
        for panel_key, panel in self.panels.items():
            handler_id = panel.listbox.connect("row-selected", make_handler(panel_key))
            # Store the handler ID so SimpleListManager can block/unblock it
            panel._handler_id = handler_id
        
    def _on_panel_selected(self, panel_key, row):
        """Handle when a panel gets selection from listbox"""
        if self._updating_selection:
            return
        
        # Update active panel if different
        if self.active_panel != panel_key:
            old_active = self.active_panel
            self.active_panel = panel_key
            if old_active != panel_key:
                self._highlight_active_panel()
                self._update_menu_name()
            
            # CLEAR SELECTION IN OTHER PANELS
            for other_key, other_panel in self.panels.items():
                if other_key != panel_key:
                    other_panel.selected_id = None
                    other_panel._refresh_listbox()
        
        # Load selected item into property panel
        if row and hasattr(row, 'item_id'):
            panel = self.panels[panel_key]
            # Set the flag temporarily to prevent loops
            self._updating_selection = True
            panel.selected_id = row.item_id
            item = panel.get_selected_item()
            if item:
                # Create a simple MenuItem-like object
                class SimpleMenuItem:
                    def __init__(self, id, title, command, icon, db_id):
                        self.id = id
                        self.title = title
                        self.command = command or ""
                        self.icon = icon or ""
                        self.db_id = db_id
                        self.depth = item.get('depth', 0)
                        self.window_state = None
                        self._is_initial_load = False
                    
                    def is_script(self):
                        return self.command.startswith('@') if self.command else False
                
                menu_item = SimpleMenuItem(
                    id=item['id'],
                    title=item['title'],
                    command=item['command'],
                    icon=item['icon'],
                    db_id=item.get('db_id')
                )
                print(f"📋 Loading selected item into property panel: {item['title'][:20]}...")
                self.property_panel.load_item(menu_item)
            self._updating_selection = False
    
    # === IMPORT/EXPORT ===
    
    def _on_export(self, button):
        """Export active menu to file using settings"""
        # Get active panel's menu ID
        panel = self.panels[self.active_panel]
        menu_id = panel.menu_id
        
        # Get menu info
        menu = self.db.fetch_one(
            "SELECT name FROM menus WHERE id = ?",
            (menu_id,)
        )
        if not menu:
            self.show_message("Menu not found!", 2)
            return
        
        menu_name = menu['name']
        
        # Get export directory from settings
        export_dir = self._get_export_directory()
        
        # Create save dialog
        dialog = Gtk.FileChooserDialog(
            title=f"Export: {menu_name}",
            parent=self.window,
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            "Export", Gtk.ResponseType.OK
        )

        dialog.set_default_size(800, 600)
        
        # Set default filename
        safe_name = menu_name.replace(' ', '_').replace('/', '_')
        default_name = f"{safe_name}.json"
        default_path = os.path.join(export_dir, default_name)
        dialog.set_current_folder(export_dir)
        dialog.set_current_name(default_name)
        
        # Add JSON filter
        json_filter = Gtk.FileFilter()
        json_filter.set_name("JSON files (*.json)")
        json_filter.add_pattern("*.json")
        dialog.add_filter(json_filter)
        
        # All files filter
        all_filter = Gtk.FileFilter()
        all_filter.set_name("All files")
        all_filter.add_pattern("*")
        dialog.add_filter(all_filter)
        
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            
            if filename:
                try:
                    # Ensure .json extension
                    if not filename.lower().endswith('.json'):
                        filename += '.json'
                    
                    self.show_message("Exporting...")
                    
                    # Do the export
                    self.import_export.export_to_file(menu_id, filename, 'json')
                    
                    self.show_message(f"Exported to {os.path.basename(filename)}", 3)
                    print(f"✅ Exported menu '{menu_name}' to {filename}")
                    
                except Exception as e:
                    error_msg = f"Export failed: {str(e)}"
                    self.show_message(error_msg, 3)
                    print(f"❌ Export error: {e}")
                    
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
    
    def _get_export_directory(self):
        """Get export directory from settings or default"""
        setting = self.db.fetch_one(
            "SELECT value FROM settings WHERE key = ?",
            ("import_export_directory",)
        )
        if setting and setting['value']:
            path = setting['value']
        else:
            path = "~/.config/gmen/menus"
        
        # Expand user directory and ensure it exists
        full_path = os.path.expanduser(path)
        os.makedirs(full_path, exist_ok=True)
        return full_path
    
    def _on_import(self, button):
        """Import menu from file using settings"""
        # Get import directory from settings
        import_dir = self._get_export_directory()  # Same as export directory
        
        # Create file chooser dialog
        dialog = Gtk.FileChooserDialog(
            title="Import Menu",
            parent=self.window,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            "Import", Gtk.ResponseType.OK
        )

        dialog.set_default_size(800, 600)
        
        # Start in import directory
        dialog.set_current_folder(import_dir)
        
        # Add JSON filter
        json_filter = Gtk.FileFilter()
        json_filter.set_name("JSON files (*.json)")
        json_filter.add_pattern("*.json")
        dialog.add_filter(json_filter)
        
        # All files filter
        all_filter = Gtk.FileFilter()
        all_filter.set_name("All files")
        all_filter.add_pattern("*")
        dialog.add_filter(all_filter)
        
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            
            if filename and os.path.exists(filename):
                try:
                    self.show_message("Importing...")
                    
                    # Import the menu
                    new_menu_id = self.import_export.import_from_file(filename)
                    
                    # Get the imported menu name
                    menu = self.db.fetch_one(
                        "SELECT name FROM menus WHERE id = ?",
                        (new_menu_id,)
                    )
                    menu_name = menu['name'] if menu else "Imported Menu"
                    
                    # Ask which panel to replace
                    replace_dialog = Gtk.Dialog(
                        title="Import Destination",
                        parent=dialog,
                        flags=0
                    )
                    replace_dialog.add_buttons(
                        Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                        "Replace Active Menu", Gtk.ResponseType.OK,
                        "Create New Menu", 100  # Custom response
                    )
                    
                    content = replace_dialog.get_content_area()
                    
                    msg = Gtk.Label(label=f"Import '{menu_name}' into:")
                    msg.set_xalign(0)
                    content.pack_start(msg, False, False, 10)
                    
                    replace_dialog.show_all()
                    replace_response = replace_dialog.run()
                    
                    if replace_response == Gtk.ResponseType.OK:
                        # Replace active panel's menu
                        active_panel = self.panels[self.active_panel]
                        old_menu_id = active_panel.menu_id
                        
                        # Update panel to use new menu
                        active_panel.menu_id = new_menu_id
                        self.menu_ids[self.active_panel] = new_menu_id
                        
                        # Reload panel
                        active_panel._load()
                        
                        # Update menu name
                        self._update_menu_name()
                        
                        self.show_message(f"Replaced menu with '{menu_name}'", 3)
                        print(f"✅ Replaced menu {old_menu_id} with imported menu {new_menu_id}")
                        
                        # Mark as unsaved (configuration changed)
                        self.set_unsaved_changes(True)
                        
                    elif replace_response == 100:
                        # Create as new menu (already done by import)
                        # Just show success message
                        self.show_message(f"Created new menu '{menu_name}'", 3)
                        print(f"✅ Created new menu {new_menu_id}")
                    
                    replace_dialog.destroy()
                    
                except Exception as e:
                    error_msg = f"Import failed: {str(e)}"
                    self.show_message(error_msg, 3)
                    print(f"❌ Import error: {e}")
                    
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
    
    # === SAVE/RELOAD HANDLERS ===
    def _on_save(self, button=None):
        print("💾 Save clicked...")
        self.show_message("Saving...")
        
        try:
            self.left_panel.save()
            self.middle_panel.save()
            self.right_panel.save()
            
            self.show_message("All saved")
            self.set_unsaved_changes(False)
            print("✅ Save complete")
            
        except Exception as e:
            print(f"❌ Save failed: {e}")
            import traceback
            traceback.print_exc()
            self.show_message(f"Save failed: {e}")
            
    def _on_reload(self, button=None):
        print("🔄 Reloading...")
        self._updating_selection = True
        self.left_panel._load()
        self.middle_panel._load()
        self.right_panel._load()
        self.property_panel.clear()
        self.show_message("Reloaded")
        self.set_unsaved_changes(False)
        
        # Select first item again
        GLib.timeout_add(100, self._delayed_reselect)
        print("✅ Reloaded")
    
    def _delayed_reselect(self):
        """Reselect first item after reload"""
        self._select_first_item_safe(self.active_panel)
        self._updating_selection = False
        return False
    
    # === UI HELPERS === #

    def _apply_css(self):
        """Modern flat CSS - minimal decoration, clear hierarchy"""
        css = """
        /* Base colours */
        @define-color accent #26a269;
        @define-color accent_light #c8e6c9;
        @define-color border #ddd;
        @define-color bg_subtle #f7f7f7;
        @define-color text_dim #666;

        /* Control buttons */
            .control-button {
                border: 1px solid @accent;
            }

        /* Save button states */
            .save-clean {
                border: 2px solid @accent;
            }

            .save-dirty {
                border: 2px solid #e53935;
            }

        /* Panel frames - the key element */
        .panel-frame {
            border: 2px solid @border;
            border-radius: 6px;
            background: white;
            padding: 4px;
        }

        .active-panel {
            border-color: @accent;
        }

        .inactive-panel {
            border-color: @border;
        }

        /* Headers - just bold, no background */
        .panel-header {
            color: #333;
            padding: 4px 0;
        }

        /* Listbox rows */
        list {
            background: transparent;
        }

        list row {
            padding: 6px 8px;
            border-radius: 4px;
        }

        list row:selected {
            background: @accent;
            color: white;
        }

        list row:hover:not(:selected) {
            background: @bg_subtle;
        }

        /* Status bar */
        .status-bar {
            background: @bg_subtle;
            padding: 4px 0;
        }

        .status-text {
            color: @text_dim;
        }

        /* Buttons - flat style */
        button {
            padding: 6px 12px;
            border-radius: 4px;
            border: 1px solid @border;
            background: white;
        }

        button:hover {
            background: @bg_subtle;
            border-color: #ccc;
        }

        button:active {
            background: #eee;
        }

        /* Entry fields */
        entry {
            padding: 6px 8px;
            border-radius: 4px;
            border: 1px solid @border;
        }

        entry:focus {
            border-color: @accent;
        }
        """

        try:
            from gi.repository import Gdk
            provider = Gtk.CssProvider()
            provider.load_from_data(css.encode())
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(),
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        except Exception as e:
            print(f"⚠️ CSS error: {e}")

    def _highlight_active_panel(self):
        """Toggle active/inactive classes on panel frames"""
        for panel_key, frame in self.panel_frames.items():
            ctx = frame.get_style_context()
            if panel_key == self.active_panel:
                ctx.remove_class("inactive-panel")
                ctx.add_class("active-panel")
            else:
                ctx.remove_class("active-panel")
                ctx.add_class("inactive-panel")

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
        self.has_unsaved_changes = has_changes
        if self.save_btn:
            if has_changes:
                self.save_btn.set_label("Save")
            else:
                self.save_btn.set_label("Save") #todo
    
    # === EXIT HANDLERS ===
    def _on_window_destroy(self, widget):
        """Handle window close - check for unsaved changes"""
        Gtk.main_quit()
        return False
    
    def _on_exit(self, button=None):
        """Handle exit button click - COMPLETE HANDLER"""
        if self.has_unsaved_changes:
            dialog = Gtk.MessageDialog(
                transient_for=self.window,
                flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.NONE,
                text="Unsaved Changes"
            )
            dialog.add_buttons(
                "Save and Exit", 1,
                "Exit Without Saving", 2,
                "Cancel", Gtk.ResponseType.CANCEL
            )
            dialog.format_secondary_text(
                "You have unsaved changes. Save before exiting?"
            )
            
            response = dialog.run()
            dialog.destroy()
            
            if response == 1:  # Save and Exit
                self._on_save()
                # Wait a bit for save to complete, then quit
                GLib.timeout_add(500, Gtk.main_quit)
            elif response == 2:  # Exit Without Saving
                Gtk.main_quit()
            # Else cancel - do nothing
        else:
            Gtk.main_quit()

        
    # === OTHER HANDLERS ===
    def _show_config_dialog(self, button):
        """Show configuration window"""
        from ui.editor.config_window import ConfigWindow
        config_window = ConfigWindow(self.db, self.window)
        config_window.show()
    
    def _on_layout(self, button=None):
        """Open Window Positioning Tool"""
        print("🪟 Opening Window Positioning Tool...")
        from ui.editor.layout_window import LayoutWindow
        layout_window = LayoutWindow(self.db)
        layout_window.run()
    
    def run(self):
        Gtk.main()
