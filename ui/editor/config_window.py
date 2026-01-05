"""
Mouse & Keyboard Configuration Window
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class ConfigWindow:
    def __init__(self, db, parent_window):
        self.db = db
        self.parent_window = parent_window
        self.window = None
        self._create_ui()
        self._load_config()
    
    def _create_ui(self):
        self.window = Gtk.Window()
        self.window.set_title("Mouse & Keyboard Configuration")
        self.window.set_default_size(600, 500)
        self.window.set_transient_for(self.parent_window)
        self.window.set_modal(True)
        self.window.connect("destroy", self._on_close)
        
        notebook = Gtk.Notebook()
        
        # Mouse Configuration Tab
        mouse_tab = self._create_mouse_tab()
        notebook.append_page(mouse_tab, Gtk.Label(label="Mouse"))
        
        # Keyboard Configuration Tab  
        keyboard_tab = self._create_keyboard_tab()
        notebook.append_page(keyboard_tab, Gtk.Label(label="Keyboard"))
        
        # General Tab
        general_tab = self._create_general_tab()
        notebook.append_page(general_tab, Gtk.Label(label="General"))
        
        # Buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_margin_top(10)
        button_box.set_margin_bottom(10)
        button_box.set_margin_start(10)
        button_box.set_margin_end(10)
        button_box.set_halign(Gtk.Align.END)
        
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: self.window.destroy())
        button_box.pack_start(cancel_btn, False, False, 0)
        
        save_btn = Gtk.Button(label="Save Configuration")
        save_btn.get_style_context().add_class("suggested-action")
        save_btn.connect("clicked", self._on_save)
        button_box.pack_start(save_btn, False, False, 0)
        
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_vbox.pack_start(notebook, True, True, 0)
        main_vbox.pack_start(button_box, False, False, 0)
        
        self.window.add(main_vbox)
        
        # Load CSS
        self._load_css()
    
    def _load_css(self):
        css = """
        .suggested-action {
            background-color: #26a269;
            color: white;
        }
        .warning {
            color: #c01c28;
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
            pass
    
    def _create_mouse_tab(self):
        """Create mouse configuration tab"""
        tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        tab.set_margin_top(20)
        tab.set_margin_bottom(20)
        tab.set_margin_start(20)
        tab.set_margin_end(20)
        
        # Title
        title = Gtk.Label(label="🖱️ Mouse Button Configuration")
        title.set_halign(Gtk.Align.CENTER)
        title.set_markup("<span size='large'><b>Map menus to mouse buttons</b></span>")
        tab.pack_start(title, False, False, 0)
        
        # Description
        desc = Gtk.Label(label="Configure which menu appears for each mouse button click.")
        desc.set_halign(Gtk.Align.CENTER)
        tab.pack_start(desc, False, False, 0)
        
        # Configuration grid
        grid = Gtk.Grid()
        grid.set_column_spacing(15)
        grid.set_row_spacing(10)
        grid.set_halign(Gtk.Align.CENTER)
        grid.set_margin_top(20)
        
        # Headers
        grid.attach(Gtk.Label(label="Mouse Button"), 0, 0, 1, 1)
        grid.attach(Gtk.Label(label="Shows Menu"), 1, 0, 1, 1)
        grid.attach(Gtk.Label(label="Platform Support"), 2, 0, 1, 1)
        
        # Mouse buttons
        mouse_buttons = [
            ('left', "Left Click", "All platforms"),
            ('middle', "Middle Click", "Windows/Linux dock"),
            ('right', "Right Click", "Windows/Linux dock"),
        ]
        
        self.mouse_widgets = {}
        
        for i, (button_key, button_name, support) in enumerate(mouse_buttons, 1):
            # Button name
            label = Gtk.Label(label=button_name)
            label.set_halign(Gtk.Align.START)
            grid.attach(label, 0, i, 1, 1)
            
            # Menu selector
            combo = Gtk.ComboBoxText()
            for menu_key in ['left', 'middle', 'right']:
                menu_name = {
                    'left': 'Left Click Menu',
                    'middle': 'Middle Click Menu',
                    'right': 'Right Click Menu'
                }[menu_key]
                combo.append(menu_key, menu_name)
            grid.attach(combo, 1, i, 1, 1)
            self.mouse_widgets[button_key] = combo
            
            # Support info
            support_label = Gtk.Label(label=support)
            support_label.set_halign(Gtk.Align.START)
            grid.attach(support_label, 2, i, 1, 1)
        
        tab.pack_start(grid, False, False, 0)
        
        # X11 note
        x11_note = Gtk.Label()
        x11_note.set_markup("<span class='warning'>⚠️ X11 system tray only supports left-click. Use keyboard modifiers below.</span>")
        x11_note.set_halign(Gtk.Align.CENTER)
        x11_note.set_margin_top(20)
        tab.pack_start(x11_note, False, False, 0)
        
        return tab
    
    def _create_keyboard_tab(self):
        """Create keyboard configuration tab"""
        tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        tab.set_margin_top(20)
        tab.set_margin_bottom(20)
        tab.set_margin_start(20)
        tab.set_margin_end(20)
        
        # Title
        title = Gtk.Label(label="⌨️ Keyboard Modifier Configuration")
        title.set_halign(Gtk.Align.CENTER)
        title.set_markup("<span size='large'><b>Map menus to keyboard shortcuts</b></span>")
        tab.pack_start(title, False, False, 0)
        
        # Description
        desc = Gtk.Label(label="For X11/Linux users: Map modifier+click combinations to access all menus.")
        desc.set_halign(Gtk.Align.CENTER)
        tab.pack_start(desc, False, False, 0)
        
        # Configuration grid
        grid = Gtk.Grid()
        grid.set_column_spacing(15)
        grid.set_row_spacing(10)
        grid.set_halign(Gtk.Align.CENTER)
        grid.set_margin_top(20)
        
        # Headers
        grid.attach(Gtk.Label(label="Keyboard Shortcut"), 0, 0, 1, 1)
        grid.attach(Gtk.Label(label="Shows Menu"), 1, 0, 1, 1)
        grid.attach(Gtk.Label(label="Description"), 2, 0, 1, 1)
        
        # Keyboard shortcuts
        shortcuts = [
            ('ctrl_left', "Ctrl + Left Click", "Hold Ctrl while clicking tray icon"),
            ('alt_left', "Alt + Left Click", "Hold Alt while clicking tray icon"),
            ('shift_left', "Shift + Left Click", "Hold Shift while clicking tray icon"),
            ('ctrl_shift_left', "Ctrl+Shift + Click", "Hold Ctrl+Shift while clicking"),
        ]
        
        self.keyboard_widgets = {}
        
        for i, (shortcut_key, shortcut_name, description) in enumerate(shortcuts, 1):
            # Shortcut name
            label = Gtk.Label(label=shortcut_name)
            label.set_halign(Gtk.Align.START)
            grid.attach(label, 0, i, 1, 1)
            
            # Menu selector
            combo = Gtk.ComboBoxText()
            for menu_key in ['left', 'middle', 'right']:
                menu_name = {
                    'left': 'Left Click Menu',
                    'middle': 'Middle Click Menu',
                    'right': 'Right Click Menu'
                }[menu_key]
                combo.append(menu_key, menu_name)
            grid.attach(combo, 1, i, 1, 1)
            self.keyboard_widgets[shortcut_key] = combo
            
            # Description
            desc_label = Gtk.Label(label=description)
            desc_label.set_halign(Gtk.Align.START)
            grid.attach(desc_label, 2, i, 1, 1)
        
        tab.pack_start(grid, False, False, 0)
        
        # Note
        note = Gtk.Label(label="💡 Tip: You can map multiple triggers to the same menu.")
        note.set_halign(Gtk.Align.CENTER)
        note.set_margin_top(20)
        tab.pack_start(note, False, False, 0)
        
        return tab
    
    def _create_general_tab(self):
        """Create general configuration tab"""
        tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        tab.set_margin_top(20)
        tab.set_margin_bottom(20)
        tab.set_margin_start(20)
        tab.set_margin_end(20)
        
        # Title
        title = Gtk.Label(label="⚙️ General Settings")
        title.set_halign(Gtk.Align.CENTER)
        title.set_markup("<span size='large'><b>Application behavior</b></span>")
        tab.pack_start(title, False, False, 0)
        
        # Settings grid
        grid = Gtk.Grid()
        grid.set_column_spacing(15)
        grid.set_row_spacing(10)
        grid.set_halign(Gtk.Align.START)
        grid.set_margin_top(20)
        grid.set_margin_start(20)
        
        # Auto-save
        row = 0
        grid.attach(Gtk.Label(label="Auto-save changes:"), 0, row, 1, 1)
        self.auto_save_combo = Gtk.ComboBoxText()
        self.auto_save_combo.append("never", "Never (manual save only)")
        self.auto_save_combo.append("5min", "Every 5 minutes")
        self.auto_save_combo.append("10min", "Every 10 minutes")
        self.auto_save_combo.append("30min", "Every 30 minutes")
        grid.attach(self.auto_save_combo, 1, row, 1, 1)
        
        # Click behavior
        row += 1
        grid.attach(Gtk.Label(label="Click empty menu:"), 0, row, 1, 1)
        self.empty_click_combo = Gtk.ComboBoxText()
        self.empty_click_combo.append("add", "Add new item")
        self.empty_click_combo.append("select", "Select menu only")
        self.empty_click_combo.append("nothing", "Do nothing")
        grid.attach(self.empty_click_combo, 1, row, 1, 1)
        
        # Default menu
        row += 1
        grid.attach(Gtk.Label(label="Default menu:"), 0, row, 1, 1)
        self.default_menu_combo = Gtk.ComboBoxText()
        self.default_menu_combo.append("left", "Left Click Menu")
        self.default_menu_combo.append("middle", "Middle Click Menu")
        self.default_menu_combo.append("right", "Right Click Menu")
        grid.attach(self.default_menu_combo, 1, row, 1, 1)
        
        tab.pack_start(grid, False, False, 0)
        
        # Spacer
        tab.pack_start(Gtk.Label(), True, True, 0)
        
        return tab
    
    def _load_config(self):
        """Load current configuration"""
        # Load mouse mapping
        for button_key, combo in self.mouse_widgets.items():
            value = self.db.get_setting(f'mouse_{button_key}', button_key)
            if value in ['left', 'middle', 'right']:
                combo.set_active_id(value)
            else:
                combo.set_active_id(button_key)  # Default
        
        # Load keyboard mapping
        for shortcut_key, combo in self.keyboard_widgets.items():
            value = self.db.get_setting(f'key_{shortcut_key}', 'left')
            if value in ['left', 'middle', 'right']:
                combo.set_active_id(value)
            else:
                combo.set_active_id('left')  # Default to left menu
        
        # Load general settings
        self.auto_save_combo.set_active_id(
            self.db.get_setting('auto_save', 'never')
        )
        self.empty_click_combo.set_active_id(
            self.db.get_setting('empty_click', 'add')
        )
        self.default_menu_combo.set_active_id(
            self.db.get_setting('default_menu', 'left')
        )
    
    def _on_save(self, button):
        """Save configuration"""
        print("💾 Saving configuration...")
        
        # Save mouse mapping
        for button_key, combo in self.mouse_widgets.items():
            value = combo.get_active_id()
            self.db.set_setting(f'mouse_{button_key}', value, f'Menu for {button_key} click')
        
        # Save keyboard mapping  
        for shortcut_key, combo in self.keyboard_widgets.items():
            value = combo.get_active_id()
            self.db.set_setting(f'key_{shortcut_key}', value, f'Menu for {shortcut_key}')
        
        # Save general settings
        self.db.set_setting('auto_save', self.auto_save_combo.get_active_id(), 'Auto-save interval')
        self.db.set_setting('empty_click', self.empty_click_combo.get_active_id(), 'Click behavior on empty menu')
        self.db.set_setting('default_menu', self.default_menu_combo.get_active_id(), 'Default menu to show')
        
        # Show success message
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Configuration Saved"
        )
        dialog.format_secondary_text("Changes will take effect when GMen is restarted.")
        dialog.run()
        dialog.destroy()
        
        # Close window
        self.window.destroy()
    
    def _on_close(self, window):
        self.window = None
    
    def show(self):
        """Show the configuration window"""
        if self.window:
            self.window.show_all()
