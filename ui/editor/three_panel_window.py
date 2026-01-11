"""
Three Panel Window - Minimal, clean version
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import os
from ui.editor.simple_list_manager import SimpleListManager
from ui.editor.property_panel import PropertyPanel


class ThreePanelWindow:
    def __init__(self, db):
        self.db = db
        self.panels = {}
        self.active_panel = 'left'
        
        # Track last selected item in each panel
        self.panel_selections = {
            'left': None,
            'middle': None,
            'right': None
        }

        # Create three panels
        self.menu_ids = self._get_menu_ids()
        
        for key in ['left', 'middle', 'right']:
            self.panels[key] = SimpleListManager(db, self.menu_ids[key])
        
        self.property_panel = PropertyPanel(db)
        self.property_panel.on_property_changed = self._on_property_changed
        
        self._create_ui()
        self._connect_events()
        
        # Initial load
        GLib.timeout_add(100, self._initial_load)
    
    def _get_menu_ids(self):
        """Get or create three menu IDs"""
        menus = self.db.get_all_menus()
        
        # Use existing or create new
        menu_ids = []
        for i in range(min(3, len(menus))):
            menu_ids.append(menus[i]['id'])
        
        # Create missing menus
        for i in range(len(menu_ids), 3):
            name = f"{['Left', 'Middle', 'Right'][i]} Click Menu"
            menu_id = self.db.create_menu(name, f"{name} description")
            menu_ids.append(menu_id)
        
        return {'left': menu_ids[0], 'middle': menu_ids[1], 'right': menu_ids[2]}
    
    def _create_ui(self):
        """Create clean UI with matching styling"""
        self.window = Gtk.Window()
        self.window.set_title("GMen Editor")
        self.window.set_default_size(1200, 700)
        
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window.add(main_vbox)
        
        # === TOOLBAR ===
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        toolbar.set_margin_top(8)
        toolbar.set_margin_bottom(8)
        toolbar.set_margin_start(16)
        toolbar.set_margin_end(16)
        
        # Menu button
        menu_btn = Gtk.Button.new_with_label("☰ Menu")
        menu_btn.connect("clicked", self._show_menu_manager)
        toolbar.pack_start(menu_btn, False, False, 0)
        
        # Spacer
        toolbar.pack_start(Gtk.Box(), True, True, 0)
        
        # Action buttons
        for label, callback in [
            ("Export", self._on_export),
            ("Import", self._on_import),
            ("Workspaces", self._on_workspaces),
            ("Settings", self._on_settings)
        ]:
            btn = Gtk.Button.new_with_label(label)
            btn.connect("clicked", callback)
            toolbar.pack_start(btn, False, False, 0)
        
        main_vbox.pack_start(toolbar, False, False, 0)
        main_vbox.pack_start(Gtk.Separator(), False, False, 0)
        
        # === MAIN CONTENT with focus handling ===
        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        content.set_margin_top(16)
        content.set_margin_bottom(16)
        content.set_margin_start(16)
        content.set_margin_end(16)
        main_vbox.pack_start(content, True, True, 0)
        
        # === LEFT: Three panels ===
        panels_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        # Panel headers
        headers = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        for key, label in [('left', "-  Left Click  -"), ('middle', "-  Middle Click  -"), ('right', "-  Right Click  -")]:
            lbl = Gtk.Label()
            lbl.set_markup(f"<b>{label}</b>")
            lbl.set_xalign(0)
            lbl.set_can_focus(False)  # Labels shouldn't get focus
            headers.pack_start(lbl, True, True, 0)
        
        panels_box.pack_start(headers, False, False, 0)
        
        # Panel lists with proper focus handling
        lists_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        self.panel_frames = {}
        
        for key in ['left', 'middle', 'right']:
            # Container for each panel
            panel_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            
            # Frame with click handler
            frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            frame.get_style_context().add_class("panel-frame")
            frame.get_style_context().add_class("inactive-panel")
            frame.set_size_request(250, 300)
            
            # Event box for clicks (doesn't steal focus)
            event_box = Gtk.EventBox()
            event_box.set_can_focus(False)  # Don't take keyboard focus
            event_box.add(frame)
            event_box.connect("button-press-event", self._on_panel_clicked, key)
            
            # Scrolled window with listbox
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            scrolled.set_min_content_width(240)
            scrolled.set_min_content_height(250)
            scrolled.set_can_focus(False)  # Don't take focus
            
            # Listbox should be focusable for keyboard navigation
            listbox = self.panels[key].listbox
            listbox.set_can_focus(True)
            
            scrolled.add(listbox)
            frame.pack_start(scrolled, True, True, 0)
            panel_container.pack_start(event_box, True, True, 0)
            
            self.panel_frames[key] = frame
            lists_box.pack_start(panel_container, True, True, 0)
        
        panels_box.pack_start(lists_box, True, True, 0)
                
        # Control buttons
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        controls.set_halign(Gtk.Align.CENTER)
        
        for label, callback in [
            ("+ Add", self._on_add),
            ("− Del", self._on_delete),
            ("↑", self._on_up),
            ("↓", self._on_down),
            ("→", self._on_indent),
            ("←", self._on_outdent)
        ]:
            btn = Gtk.Button.new_with_label(label)
            btn.connect("clicked", callback)
            controls.pack_start(btn, False, False, 0)
        
        panels_box.pack_start(controls, False, False, 8)
        content.pack_start(panels_box, True, True, 0)
        

        # === RIGHT: Property panel ===
        prop_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        # Create property panel using new create_panel() method
        prop_panel = self.property_panel.create_panel()
        prop_container.pack_start(prop_panel, True, True, 0)

        # Set fixed width for property panel
        prop_container.set_size_request(350, -1)  # FIXED WIDTH

        content.pack_start(prop_container, False, False, 0)
        
        # === STATUS BAR ===
        status = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        status.set_margin_top(8)
        status.set_margin_bottom(8)
        status.set_margin_start(16)
        status.set_margin_end(16)
        
        self.status_label = Gtk.Label(label="Ready")
        status.pack_start(self.status_label, True, True, 0)
        
        for label, callback in [
            ("Save", self._on_save),
            ("Reload", self._on_reload),
            ("Exit", self._on_exit)
        ]:
            btn = Gtk.Button.new_with_label(label)
            btn.connect("clicked", callback)
            status.pack_start(btn, False, False, 0)
        
        main_vbox.pack_start(Gtk.Separator(), False, False, 0)
        main_vbox.pack_start(status, False, False, 0)
        
        self.window.show_all()
        self._apply_css()  # Apply CSS styling
        self._highlight_active_panel()
    
    def _apply_css(self):
        """Apply CSS styling for frames and borders - SIMPLIFIED"""
        css = """
        /* Panel frames - 2px border with radius */
        .panel-frame {
            border: 2px solid #ddd;
            border-radius: 6px;
            background: white;
            padding: 4px;
        }

        /* Active panel - green border */
        .active-panel {
            border-color: #26a269;
            border-width: 2px;
        }

        /* Inactive panel - grey border */
        .inactive-panel {
            border-color: #ddd;
            border-width: 2px;
        }

        /* Listbox styling */
        list {
            background: transparent;
        }

        list row {
            padding: 6px 8px;
            border-radius: 4px;
            min-height: 28px;
        }

        list row:selected {
            background: #26a269;
            color: white;
        }

        list row:hover:not(:selected) {
            background: #f7f7f7;
        }

        /* Entry styling */
        entry {
            padding: 6px 8px;
            border-radius: 4px;
            border: 1px solid #ddd;
        }

        entry:focus {
            border-color: #26a269;
        }

        /* Button styling */
        button {
            padding: 6px 12px;
            border-radius: 4px;
            border: 1px solid #ddd;
            background: white;
        }

        button:hover {
            background: #f7f7f7;
            border-color: #ccc;
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
            print("✅ CSS applied successfully")
        except Exception as e:
            print(f"⚠️ CSS error: {e}")

    def _connect_events(self):
        """Connect listbox selection events"""
        for key, panel in self.panels.items():
            panel.listbox.connect("row-selected", self._on_item_selected, key)
    
    # === EVENT HANDLERS ===
    

    def _on_panel_clicked(self, event_box, event, panel_key):
        """Panel frame click - ONLY activates panel, NO clearing"""
        print(f"\n🖱️ Panel FRAME click: {panel_key} - JUST ACTIVATING")

        # Just switch active panel
        if self.active_panel != panel_key:
            self.active_panel = panel_key
            self._highlight_active_panel()

        # DO NOT clear anything!
        # If panel has a selection, keep it
        # Property panel stays as is

        return True

    def _on_item_selected(self, listbox, row, panel_key):
        """Item selection - clean version"""
        print(f"\n🎯 SELECTION in {panel_key}")

        # Make panel active
        if self.active_panel != panel_key:
            self.active_panel = panel_key
            self._highlight_active_panel()

        panel = self.panels[panel_key]

        if row and hasattr(row, 'item_id'):
            # SELECTION
            # Clear other panels
            for other_key, other_panel in self.panels.items():
                if other_key != panel_key:
                    other_panel.selected_id = None
                    other_panel.listbox.unselect_all()

            # Set this selection
            panel.selected_id = row.item_id

            # Load item
            item = panel.get_selected_item()
            if item:
                self.property_panel.load_item(item)
        else:
            # DESELECTION (clicked empty space IN the list)
            panel.selected_id = None
            self.property_panel.clear()

    def _on_property_changed(self, item_id, field, value, instance_idx=0):
        """Handle property changes from property panel"""
        panel = self.panels[self.active_panel]
        
        if field == 'title':
            # Update item title
            for item in panel.items:
                if item['id'] == item_id:
                    item['title'] = value
                    panel._refresh_listbox()
                    break
        elif field == 'switch_instance':
            # Just switch instance display
            self.property_panel.current_instance_idx = value
            # Reload data for new instance
            item = panel.get_selected_item()
            if item and value < len(item['instances']):
                self.property_panel._load_instance_data(item['instances'][value])
        elif field in ['add_instance', 'remove_instance']:
            if field == 'add_instance':
                panel.add_instance(item_id)
            else:
                panel.remove_instance(item_id, value)
            
            # Reload item to update instance count
            item = panel.get_selected_item()
            if item:
                self.property_panel.load_item(item)
        else:
            # Update instance property
            panel.update_instance(item_id, instance_idx, **{field: value})
    
    # === CONTROL BUTTONS ===
    
    def _on_add(self, button):
        """Add new item - maintains single selection"""
        panel = self.panels[self.active_panel]
        
        # Clear all selections first
        self._clear_all_selections_except(None, None)
        
        # Add new item
        new_item = panel.add_item()
        
        # Select and load the new item
        if new_item:
            panel.listbox.select_row(panel.listbox.get_row_at_index(len(panel.items) - 1))
            panel.selected_id = new_item['id']
            self.property_panel.load_item(new_item)

    def _on_delete(self, button):
        """Delete selected item - clears selection"""
        panel = self.panels[self.active_panel]
        panel.delete_item()
        
        # Clear all selections after delete
        self._clear_all_selections_except(None, None)
        self.property_panel.clear()

    def _on_up(self, button):
        """Move up - preserves selection"""
        panel = self.panels[self.active_panel]
        old_selected = panel.selected_id
        
        panel.move_up()
        
        # If we moved an item, reselect it
        if old_selected:
            panel.selected_id = old_selected
            # Force refresh to show new position
            panel._refresh_listbox()
            # Reselect in listbox
            for i, row in enumerate(panel.listbox.get_children()):
                if hasattr(row, 'item_id') and row.item_id == old_selected:
                    panel.listbox.select_row(row)
                    break

    def _on_down(self, button):
        """Move down - preserves selection"""
        panel = self.panels[self.active_panel]
        old_selected = panel.selected_id
        
        panel.move_down()
        
        # If we moved an item, reselect it
        if old_selected:
            panel.selected_id = old_selected
            panel._refresh_listbox()
            for i, row in enumerate(panel.listbox.get_children()):
                if hasattr(row, 'item_id') and row.item_id == old_selected:
                    panel.listbox.select_row(row)
                    break
        
    def _on_indent(self, button):
        self.panels[self.active_panel].indent()
    
    def _on_outdent(self, button):
        self.panels[self.active_panel].outdent()
    
    # === UTILITIES ===
    
    def _highlight_active_panel(self):
        """Toggle active/inactive classes on panel frames"""
        for panel_key, frame in self.panel_frames.items():
            ctx = frame.get_style_context()
            if panel_key == self.active_panel:
                ctx.remove_class("inactive-panel")
                ctx.add_class("active-panel")
                print(f"🎯 Panel {panel_key} is now ACTIVE (green border)")
            else:
                ctx.remove_class("active-panel")
                ctx.add_class("inactive-panel")
                print(f"🔘 Panel {panel_key} is now INACTIVE")
        
        # Force redraw
        self.window.queue_draw()
    
    def _initial_load(self):
        """Initial load after UI is ready - FIXED"""
        # Load first item in left panel if exists
        panel = self.panels['left']
        if panel.items:
            # Select the row
            first_row = panel.listbox.get_row_at_index(0)
            if first_row:
                panel.listbox.select_row(first_row)
                panel.selected_id = panel.items[0]['id']
                self.property_panel.load_item(panel.items[0])
        
        return False

    def _clear_all_selections_except(self, panel_key=None, item_id=None):
        """Clear ALL selections in ALL panels except the specified one"""
        print(f"🧹 Clearing all selections except {panel_key}:{item_id}")

        for key, panel in self.panels.items():
            if key == panel_key:
                # For the active panel, only keep the specified item selected
                if item_id:
                    # Clear all selections first
                    panel.listbox.unselect_all()
                    # Then select the specific item
                    for i, row in enumerate(panel.listbox.get_children()):
                        if hasattr(row, 'item_id') and row.item_id == item_id:
                            panel.listbox.select_row(row)
                            panel.selected_id = item_id
                            break
                else:
                    # No item to keep selected, clear everything
                    panel.listbox.unselect_all()
                    panel.selected_id = None
            else:
                # For other panels, clear everything
                panel.listbox.unselect_all()
                panel.selected_id = None
                panel._refresh_listbox()

    def _debug_selection_state(self):
        """Debug selection state"""
        print("   📊 CURRENT STATE:")
        for key in ['left', 'middle', 'right']:
            panel = self.panels[key]
            selected_row = panel.listbox.get_selected_row()
            row_id = selected_row.item_id if selected_row and hasattr(selected_row, 'item_id') else 'None'
            print(f"     {key}: panel.selected_id={panel.selected_id}, listbox_row={row_id}")



    # Add this debug method to ThreePanelWindow:
    def _debug_state(self):
        """Debug current state"""
        print("\n🎯 DEBUG STATE:")
        print(f"Active panel: {self.active_panel}")
        for key in ['left', 'middle', 'right']:
            panel = self.panels[key]
            selected_row = panel.listbox.get_selected_row()
            row_id = selected_row.item_id if selected_row and hasattr(selected_row, 'item_id') else 'None'
            print(f"  {key}: selected_id={panel.selected_id}, listbox_row={row_id}, items={len(panel.items)}")
    
    # === STUB HANDLERS ===
    
    def _show_menu_manager(self, button): print("Menu manager")
    def _on_export(self, button): print("Export")
    def _on_import(self, button): print("Import")
    def _on_workspaces(self, button): print("Workspaces")
    def _on_settings(self, button): print("Settings")
    def _on_save(self, button): print("Save")
    def _on_reload(self, button): print("Reload")
    def _on_exit(self, button): Gtk.main_quit()
    
    def run(self):
        Gtk.main()
