"""
Main UI Application - System Tray Interface
"""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, GLib, AppIndicator3

import subprocess
import sys
from pathlib import Path
from typing import Optional

from core.menu.builder import MenuItem, MenuBuilder


class GMenApp:
    """Main application UI"""
    
    def __init__(self, db, window_mgr, network_mgr, config, dry_run=False):
        self.db = db
        self.window_mgr = window_mgr
        self.network_mgr = network_mgr
        self.config = config
        self.dry_run = dry_run
        
        # Build menu
        self.menu_builder = MenuBuilder(db)
        self.menu_root = self.menu_builder.build_default_menu()
        
        # Create system tray
        self._create_tray_icon()
        
        # Build UI menu
        self._build_menu()
        
        print("🎯 GMen started - Running in system tray")
        self.menu_builder.print_menu(self.menu_root)
    
    def _create_tray_icon(self):
        """Create system tray icon"""
        icon_name = self.config.get("ui.tray_icon", "view-grid-symbolic")
        
        self.indicator = AppIndicator3.Indicator.new(
            "gmen-indicator",
            icon_name,
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        
        self.menu = Gtk.Menu()
        self.indicator.set_menu(self.menu)
    
    def _build_menu(self):
        """Build menu from menu tree"""
        # Clear existing
        for item in self.menu.get_children():
            self.menu.remove(item)
        
        # Build from menu root (skip the virtual root)
        for child in self.menu_root.children:
            self._build_menu_recursive(child, self.menu)
        
        # Add configuration section
        self._add_config_section()
        
        self.menu.show_all()
    
    def _build_menu_recursive(self, menu_item: MenuItem, parent_menu):
        """Build menu recursively"""
        if menu_item.children:
            # Submenu
            submenu_item = Gtk.MenuItem.new_with_label(menu_item.title)
            submenu = Gtk.Menu()
            
            for child in menu_item.children:
                self._build_menu_recursive(child, submenu)
            
            submenu_item.set_submenu(submenu)
            parent_menu.append(submenu_item)
        else:
            # Regular menu item
            menu_item_widget = self._create_menu_item(menu_item)
            parent_menu.append(menu_item_widget)
    
    def _create_menu_item(self, item: MenuItem) -> Gtk.MenuItem:
        """Create a GTK menu item from MenuItem"""
        if item.icon:
            menu_item = Gtk.ImageMenuItem.new_with_label(item.title)
            try:
                image = Gtk.Image.new_from_icon_name(
                    item.icon, Gtk.IconSize.MENU
                )
                menu_item.set_image(image)
            except:
                pass
        else:
            menu_item = Gtk.MenuItem.new_with_label(item.title)
        
        # Connect handler
        menu_item.connect('activate', 
                         lambda w, cmd=item.command, ws=item.window_state: 
                         self._launch_application(cmd, ws))
        
        return menu_item
    
    def _launch_application(self, command: str, window_state=None):
        """Launch application"""
        if not command:
            return
        
        if self.dry_run:
            print(f"🚫 DRY-RUN: Would launch: {command}")
            if window_state:
                print(f"     With window state: {window_state}")
            return
        
        print(f"🚀 Launching: {command}")
        
        # Use window manager if available
        if self.window_mgr:
            pid, instance_id = self.window_mgr.launch_with_state(
                command, window_state
            )
            print(f"✅ Launched with PID: {pid}")
        else:
            # Simple launch
            subprocess.Popen(command, shell=True)
    
    def _add_config_section(self):
        """Add configuration section to menu"""
        self.menu.append(Gtk.SeparatorMenuItem())
        
        # Configure submenu
        config_item = Gtk.MenuItem.new_with_label("⚙️  Configure GMen")
        config_menu = Gtk.Menu()
        
        # Window management items
        if self.window_mgr:
            save_ws = Gtk.MenuItem.new_with_label("💾 Save Workspace")
            save_ws.connect('activate', self._save_workspace)
            config_menu.append(save_ws)
            
            load_ws = Gtk.MenuItem.new_with_label("📂 Load Workspace")
            load_ws.connect('activate', self._load_workspace_dialog)
            config_menu.append(load_ws)
        
        # Network items if enabled
        if self.network_mgr:
            network_item = Gtk.MenuItem.new_with_label("🌐 Network")
            network_menu = Gtk.Menu()
            
            hosts = self.network_mgr.get_connected_hosts() if hasattr(self.network_mgr, 'get_connected_hosts') else []
            if hosts:
                for host in hosts:
                    host_item = Gtk.MenuItem.new_with_label(f"📡 {host.get('hostname', 'Unknown')}")
                    host_item.set_sensitive(host.get('reachable', False))
                    network_menu.append(host_item)
            else:
                none_item = Gtk.MenuItem.new_with_label("No hosts found")
                none_item.set_sensitive(False)
                network_menu.append(none_item)
            
            network_item.set_submenu(network_menu)
            config_menu.append(network_item)
        
        config_menu.append(Gtk.SeparatorMenuItem())
        
        # Editor
        editor_item = Gtk.MenuItem.new_with_label("✏️  Edit Menu")
        editor_item.connect('activate', self._open_editor)
        config_menu.append(editor_item)
        
        # Reload
        reload_item = Gtk.MenuItem.new_with_label("🔄 Reload")
        reload_item.connect('activate', self._reload_menu)
        config_menu.append(reload_item)
        
        # Quit
        quit_item = Gtk.MenuItem.new_with_label("🚪 Quit")
        quit_item.connect('activate', self.quit)
        config_menu.append(quit_item)
        
        config_item.set_submenu(config_menu)
        self.menu.append(config_item)
    
    def _save_workspace(self, *args):
        """Save current workspace"""
        if self.window_mgr:
            self.window_mgr.save_current_workspace("QuickSave")
            self.show_notification("Workspace saved!", 2000)
    
    def _load_workspace_dialog(self, *args):
        """Show workspace load dialog"""
        # Simplified for now
        if self.window_mgr:
            success = self.window_mgr.load_workspace("QuickSave")
            if success:
                self.show_notification("Workspace loaded!", 2000)
    
    def _open_editor(self, *args):
        """Open menu editor"""
        try:
            editor_path = Path.cwd() / "gmen_editor.py"
            if editor_path.exists():
                subprocess.Popen([sys.executable, str(editor_path)])
                self.show_notification("Editor launched", 2000)
        except Exception as e:
            print(f"❌ Could not launch editor: {e}")
    
    def _reload_menu(self, *args):
        """Reload menu from database"""
        self.menu_root = self.menu_builder.build_default_menu()
        self._build_menu()
        self.show_notification("Menu reloaded", 2000)
    
    def show_notification(self, message: str, duration: int = 3000):
        """Show notification"""
        self.indicator.set_label(message, "")
        GLib.timeout_add(duration, self._reset_indicator)
    
    def _reset_indicator(self):
        """Reset indicator label"""
        self.indicator.set_label("", "")
        return False
    
    def quit(self, *args):
        """Quit application"""
        print("🛑 Quitting GMen...")
        
        # Cleanup
        if self.window_mgr:
            self.window_mgr.cleanup()
        
        if self.network_mgr:
            self.network_mgr.stop()
        
        Gtk.main_quit()
        sys.exit(0)
    
    def run(self):
        """Run application"""
        Gtk.main()
