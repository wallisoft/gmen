"""
Three Panel Editor - Left, Middle, Right click menus
Polished UI with compact controls
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from ui.editor.simple_list_manager import SimpleListManager
from ui.editor.property_panel import PropertyPanel
from ui.editor.toolbar import Toolbar


class ThreePanelWindow:
    def __init__(self, db):
        self.db = db
        
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
        
        # Toolbar (will only have Export/Import/Workspaces now)
        self.toolbar = Toolbar(db)
        self.toolbar.on_save = None  # We'll handle this in bottom panel
        self.toolbar.on_reload = None
        self.toolbar.on_debug = self._on_layout
        
        # Load trigger mapping
        self.trigger_mapping = self._load_trigger_mapping()
        
        # Active panel (starts with left panel)
        self.active_panel = 'left'
        
        # Frame widgets for color highlighting
        self.panel_frames = {}
        
        # Flag to prevent event loops
        self._updating_selection = False
        
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
        
        # Re-enable selection updates
        self._updating_selection = False
        print("✅ Data loaded")
    
    def _ensure_three_menus(self):
        """Get or create menus - use existing if only 1 menu"""
        menus = {}
        conn = self.db._get_connection()
        cursor = conn.cursor()
        
        # Get all menus
        cursor.execute("SELECT id, name FROM menus ORDER BY id")
        all_menus = cursor.fetchall()
        
        print(f"📊 Found {len(all_menus)} existing menus")
        
        # Menu configurations
        menu_configs = [
            ('left', "Left Click Menu", "Left click applications"),
            ('middle', "Middle Click Menu", "Middle click system tools"),
            ('right', "Right Click Menu", "Right click power user"),
        ]
        
        # If we have only 1 menu, use it for all three panels
        if len(all_menus) == 1:
            single_menu_id = all_menus[0][0]
            single_menu_name = all_menus[0][1]
            print(f"📋 Single menu found: {single_menu_name}")
            print("📋 Using same menu for all three panels")
            
            for key, _, _ in menu_configs:
                menus[key] = single_menu_id
        else:
            # Use or create separate menus
            for i, (key, name, description) in enumerate(menu_configs):
                if i < len(all_menus):
                    # Use existing menu
                    menus[key] = all_menus[i][0]
                    print(f"📋 Using existing menu for {key}: {all_menus[i][1]}")
                else:
                    # Create new menu
                    cursor.execute(
                        "INSERT INTO menus (name, description) VALUES (?, ?)",
                        (name, description)
                    )
                    conn.commit()
                    menus[key] = cursor.lastrowid
                    print(f"📋 Created new menu for {key}: {name}")
        
        return menus
    
    def _load_trigger_mapping(self):
        """Load mapping from database"""
        mapping = {
            'left': 'left',
            'middle': 'middle',
            'right': 'right',
            'ctrl_left': 'left',
            'alt_left': 'middle',  
            'shift_left': 'right',
        }
        
        conn = self.db._get_connection()
        cursor = conn.cursor()
        
        for trigger in mapping.keys():
            cursor.execute(
                "SELECT value FROM settings WHERE key = ?",
                (f'trigger_{trigger}',)
            )
            row = cursor.fetchone()
            if row and row[0] in ['left', 'middle', 'right']:
                mapping[trigger] = row[0]
        
        return mapping
    
    def _save_trigger_mapping(self):
        """Save mapping to database"""
        conn = self.db._get_connection()
        cursor = conn.cursor()
        
        for trigger, menu in self.trigger_mapping.items():
            cursor.execute("""
                INSERT OR REPLACE INTO settings (key, value, description)
                VALUES (?, ?, ?)
            """, (f'trigger_{trigger}', menu, f'Menu for {trigger}'))
        
        conn.commit()
    
    def _create_ui(self):
        self.window = Gtk.Window()
        self.window.set_title("GMen Editor - Left/Middle/Right")
        self.window.set_default_size(1200, 700)  # Compact size
        self.window.connect("destroy", Gtk.main_quit)
        
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window.add(main_vbox)
        
        # === TOP TOOLBAR (Export/Import/Workspaces only) ===
        toolbar_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        toolbar_box.set_margin_top(5)
        toolbar_box.set_margin_bottom(5)
        toolbar_box.set_margin_start(10)
        toolbar_box.set_margin_end(10)
        
        # Export button
        export_btn = Gtk.Button.new_with_label("📤 Export")
        export_btn.set_tooltip_text("Export menu to file")
        export_btn.connect("clicked", self._on_export)
        toolbar_box.pack_start(export_btn, False, False, 0)
        
        # Import button
        import_btn = Gtk.Button.new_with_label("📥 Import")
        import_btn.set_tooltip_text("Import menu from file")
        import_btn.connect("clicked", self._on_import)
        toolbar_box.pack_start(import_btn, False, False, 0)
        
        # Separator
        toolbar_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 5)
        
        # Workspaces button 
        workspaces_btn = Gtk.Button.new_with_label("🗺️ Workspaces")
        workspaces_btn.set_tooltip_text("Window positioning and workspaces")
        workspaces_btn.connect("clicked", self._on_layout)
        toolbar_box.pack_start(workspaces_btn, False, False, 0)
        
        # Separator
        toolbar_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 5)
        
        # Config button
        config_btn = Gtk.Button(label="⚙️ Configure Mouse & KeyMap")
        config_btn.connect("clicked", self._show_config_dialog)
        toolbar_box.pack_start(config_btn, False, False, 0)
        
        # Expand
        toolbar_box.pack_start(Gtk.Label(), True, True, 0)
        
        main_vbox.pack_start(toolbar_box, False, False, 0)
        
        # === MAIN CONTENT AREA ===
        content_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        content_hbox.set_margin_top(10)
        content_hbox.set_margin_bottom(10)
        content_hbox.set_margin_start(10)
        content_hbox.set_margin_end(10)
        main_vbox.pack_start(content_hbox, True, True, 0)
        
        # === LEFT SIDE: THREE MENUS + CONTROLS ===
        left_side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        
        # Three panels in a row
        panels_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        # Create clickable frames for each panel
        for panel_key, label_text in [
            ('left', "Left Click Menu"),
            ('middle', "Middle Click Menu"),
            ('right', "Right Click Menu")
        ]:
            frame = Gtk.Frame(label=label_text)
            frame.set_shadow_type(Gtk.ShadowType.IN)
            
            # Make frame clickable by adding event box
            event_box = Gtk.EventBox()
            frame.add(event_box)
            
            # Store reference to panel
            panel = self.panels[panel_key]
            
            # Create content for the panel
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            vbox.set_margin_top(5)
            vbox.set_margin_bottom(5)
            vbox.set_margin_start(5)
            vbox.set_margin_end(5)
            
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            scrolled.add(panel.listbox)
            vbox.pack_start(scrolled, True, True, 0)
            
            event_box.add(vbox)
            
            # Connect click event to frame
            event_box.connect("button-press-event", self._on_frame_clicked, panel_key)
            
            panels_hbox.pack_start(frame, True, True, 0)
            self.panel_frames[panel_key] = frame
        
        left_side.pack_start(panels_hbox, True, True, 0)
        
        # === CONTROLS (under the 3 menus) - COMPACT 1 LINE ===
        controls_frame = Gtk.Frame(label="Controls for Active Menu")
        controls_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        controls_vbox.set_margin_top(5)
        controls_vbox.set_margin_bottom(5)
        controls_vbox.set_margin_start(5)
        controls_vbox.set_margin_end(5)
        
        # Control buttons (ALL ON ONE LINE)
        controls_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        controls_hbox.set_halign(Gtk.Align.CENTER)
        
        # Create all buttons in one line
        button_configs = [
            ("Add", self._on_add),
            ("Del", self._on_delete),
            ("Up", self._on_up),
            ("Down", self._on_down),
            (">", self._on_indent),
            ("<", self._on_outdent)
        ]
        
        for label, callback in button_configs:
            btn = Gtk.Button(label=label)
            btn.set_size_request(50, 30)  # Compact size
            btn.connect("clicked", callback)
            controls_hbox.pack_start(btn, False, False, 0)
        
        controls_vbox.pack_start(controls_hbox, False, False, 0)
        controls_frame.add(controls_vbox)
        
        left_side.pack_start(controls_frame, False, False, 0)
        
        content_hbox.pack_start(left_side, True, True, 0)
        
        # === RIGHT SIDE: PROPERTY PANEL ===
        prop_frame = self.property_panel.create_panel()
        content_hbox.pack_start(prop_frame, False, False, 0)
        
        # === BOTTOM PANEL (Save/Reload/Exit) ===
        bottom_panel = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bottom_panel.set_margin_top(5)
        bottom_panel.set_margin_bottom(5)
        bottom_panel.set_margin_start(10)
        bottom_panel.set_margin_end(10)
        
        # Status label (left)
        self.status_label = Gtk.Label(label="Ready")
        self.status_label.set_xalign(0)
        bottom_panel.pack_start(self.status_label, True, True, 0)
        
        # Unsaved indicator
        self.unsaved_indicator = Gtk.Label(label="")
        self.unsaved_indicator.set_markup("<span foreground='orange' size='large'>●</span>")
        self.unsaved_indicator.set_tooltip_text("Unsaved changes")
        self.unsaved_indicator.set_visible(False)
        bottom_panel.pack_start(self.unsaved_indicator, False, False, 5)
        
        # Save button
        self.save_btn = Gtk.Button.new_with_label("💾 Save")
        self.save_btn.set_tooltip_text("Save all changes to database")
        self.save_btn.connect("clicked", self._on_save)
        bottom_panel.pack_start(self.save_btn, False, False, 0)
        
        # Reload button
        self.reload_btn = Gtk.Button.new_with_label("🔄 Reload")
        self.reload_btn.set_tooltip_text("Reload from database (discard changes)")
        self.reload_btn.connect("clicked", self._on_reload)
        bottom_panel.pack_start(self.reload_btn, False, False, 0)
        
        # Exit button (reuse property panel's button)
        exit_btn = Gtk.Button.new_with_label("❌ Exit")
        exit_btn.set_tooltip_text("Close the editor")
        exit_btn.connect("clicked", self._on_exit)
        bottom_panel.pack_start(exit_btn, False, False, 0)
        
        main_vbox.pack_start(bottom_panel, False, False, 0)
        
        self.window.show_all()
        
        # Apply CSS for color highlighting
        self._apply_css()
    
    def _apply_css(self):
        """Apply CSS styles for panel highlighting"""
        css = """
        .active-panel {
            border: 3px solid #26a269;
            border-radius: 4px;
        }
        .inactive-panel {
            border: 1px solid @borders;
        }
        .selected-row {
            background-color: #c0c0c0;
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
            print("⚠️ Could not load CSS")
    
    def _highlight_active_panel(self):
        """Highlight active panel with green border"""
        for panel_key, frame in self.panel_frames.items():
            ctx = frame.get_style_context()
            if panel_key == self.active_panel:
                ctx.add_class("active-panel")
                ctx.remove_class("inactive-panel")
            else:
                ctx.add_class("inactive-panel")
                ctx.remove_class("active-panel")
    
    def _on_frame_clicked(self, event_box, event, panel_key):
        """Handle frame click to activate panel - CLEAR OTHER PANELS"""
        print(f"🖱️ Frame clicked: {panel_key}")
        
        # Update active panel
        old_active = self.active_panel
        self.active_panel = panel_key
        
        # Update visual highlighting
        if old_active != panel_key:
            self._highlight_active_panel()
        
        # CLEAR SELECTION IN OTHER PANELS
        for other_key, other_panel in self.panels.items():
            if other_key != panel_key:
                other_panel.selected_id = None
                other_panel._refresh_listbox()  # Update visual
        
        # Select first item in active panel if it has items
        panel = self.panels[panel_key]
        if panel.items:
            # Only select first item if nothing is selected
            if not panel.selected_id:
                self._select_first_item_safe(panel_key)
            # If panel already has a selection, keep it selected (property panel already shows it)
        else:
            # No items - add one automatically AND SELECT IT
            print(f"📝 No items in {panel_key} menu, adding one...")
            new_item = panel.add_item()
            # Load the new item into property panel
            self._delayed_load_new_item(panel_key, new_item['id'])
        
        return True  # Stop event propagation
    
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
    
    def _select_first_item_safe(self, panel_key):
        """Select first item in a panel without triggering loops"""
        panel = self.panels[panel_key]
        if panel.items:
            panel.selected_id = panel.items[0]['id']
            
            # Load into property panel
            GLib.timeout_add(50, self._delayed_load_item, panel_key)
    
    def _delayed_load_item(self, panel_key):
        """Load item into property panel after UI is ready"""
        panel = self.panels[panel_key]
        if panel.items and panel.selected_id:
            for item in panel.items:
                if item['id'] == panel.selected_id:
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
                    print(f"📋 Loading item into property panel: {item['title'][:20]}...")
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
    
    def _on_exit(self, button=None):
        """Handle exit button click"""
        print("👋 Exiting editor...")
        Gtk.main_quit()
    
    def _show_config_dialog(self, button):
        """Show configuration window"""
        from ui.editor.config_window import ConfigWindow
        config_window = ConfigWindow(self.db, self.window)
        config_window.show()
    
    def _on_config_changed(self, trigger_key, menu_key):
        self.trigger_mapping[trigger_key] = menu_key
    
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
        """Handle when a panel gets selection from listbox - CLEAR OTHER PANELS"""
        if self._updating_selection:
            return
        
        # Update active panel if different
        if self.active_panel != panel_key:
            old_active = self.active_panel
            self.active_panel = panel_key
            if old_active != panel_key:
                self._highlight_active_panel()
            
            # CLEAR SELECTION IN OTHER PANELS
            for other_key, other_panel in self.panels.items():
                if other_key != panel_key:
                    other_panel.selected_id = None
                    other_panel._refresh_listbox()  # Update visual
        
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

    def _on_property_changed(self, item_id, field, value):
        if not self.active_panel or self._updating_selection:
            return
        
        panel = self.panels[self.active_panel]
        
        if field == 'title':
            panel.update_item(item_id, title=value)
        elif field == 'command':
            panel.update_item(item_id, command=value)
        elif field == 'icon':
            panel.update_item(item_id, icon=value)
        
        self.set_unsaved_changes(True)
    
    def _on_save(self, button=None):
        print("💾 Saving all menus...")
        self.show_message("Saving...")
        
        try:
            self.left_panel.save()
            self.middle_panel.save()
            self.right_panel.save()
            
            self._save_trigger_mapping()
            
            self.show_message("All saved")
            self.set_unsaved_changes(False)
            print("✅ All saved")
            
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
    
    def _on_layout(self, button=None):
        """Open Window Positioning Tool"""
        print("🪟 Opening Window Positioning Tool...")
        from ui.editor.layout_window import LayoutWindow
        layout_window = LayoutWindow(self.db)
        layout_window.run()
    
    def _on_export(self, button=None):
        """Export menu"""
        print("📤 Export feature not implemented yet")
        self.show_message("Export feature coming soon!")
    
    def _on_import(self, button=None):
        """Import menu"""
        print("📥 Import feature not implemented yet")
        self.show_message("Import feature coming soon!")
    
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
    
    def run(self):
        Gtk.main()
