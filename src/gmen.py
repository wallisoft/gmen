#!/usr/bin/env python3
"""
GMen v3 - Database-First System Tray Launcher
No JSON config - everything from SQLite database
"""

import gi
import subprocess
import threading
import sys
import os
from datetime import datetime
from pathlib import Path

gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, GLib, AppIndicator3

# Try to import window manager
try:
    from window_manager import create_window_manager
    HAS_WINDOW_MANAGER = True
except ImportError as e:
    HAS_WINDOW_MANAGER = False
    print(f"⚠️  Window manager not available: {e}")

from database import get_database

class GMen:
    def __init__(self, dry_run=False):
        self.name = "GMen"
        self.version = "3.0.0"
        self.dry_run = dry_run
        
        if self.dry_run:
            print("🚫 DRY-RUN MODE: No commands will be executed")
        
        # Initialize database
        self.db = get_database()
        
        # Initialize window manager if available
        self.HAS_WINDOW_MANAGER = HAS_WINDOW_MANAGER
        if self.HAS_WINDOW_MANAGER:
            try:
                config_dir = Path.home() / ".config" / "gmen"
                self.window_manager = create_window_manager(config_dir)
                print("✅ Instance-aware window manager initialized")
            except Exception as e:
                print(f"⚠️  Window manager failed: {e}")
                self.window_manager = None
        else:
            self.window_manager = None
            print("⚠️  Window management disabled")
        
        # Load default menu
        self.current_menu_id = self.get_default_menu_id()
        if not self.current_menu_id:
            print("❌ No default menu found in database")
            sys.exit(1)
        
        # Create system tray icon
        self.create_tray_icon()
        
        # Show startup message
        self.show_startup_info()
    
    def get_default_menu_id(self):
        """Get the ID of the default menu"""
        menu = self.db.fetch_one("""
            SELECT id, name FROM menus WHERE is_default = 1 LIMIT 1
        """)
        
        if menu:
            print(f"📋 Loaded menu: {menu['name']} (ID: {menu['id']})")
            return menu['id']
        return None
    
    def create_tray_icon(self):
        """Create system tray icon and menu"""
        # Create indicator
        self.indicator = AppIndicator3.Indicator.new(
            "gmen-indicator",
            "view-grid-symbolic",  # Grid icon
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        
        # Create menu
        self.menu = Gtk.Menu()
        self.build_menu()
        
        self.indicator.set_menu(self.menu)
        print("🎯 System tray icon created")
    
    def build_menu(self):
        """Build the menu from database"""
        # Clear existing items
        for item in self.menu.get_children():
            self.menu.remove(item)
        
        # ===== APPLICATION LAUNCHER =====
        launcher_header = Gtk.MenuItem.new_with_label("🚀 Application Launcher")
        launcher_header.set_sensitive(False)
        self.menu.append(launcher_header)
        
        # Load menu items from database
        menu_items = self.db.fetch("""
            SELECT mi.id, mi.title, mi.command, mi.icon, mi.depth,
                   ws.x, ws.y, ws.width, ws.height, ws.monitor
            FROM menu_items mi
            LEFT JOIN window_states ws ON mi.id = ws.menu_item_id AND ws.is_active = 1
            WHERE mi.menu_id = ? AND mi.command != ''
            ORDER BY mi.depth, 
                     (SELECT sort_order FROM menu_items WHERE id = mi.parent_id),
                     mi.sort_order
        """, (self.current_menu_id,)) 

        # Build hierarchical menu
        self.add_menu_items_recursive(menu_items, self.menu, parent_id=None)
        
        self.menu.append(Gtk.SeparatorMenuItem())
        
        # ===== CONFIGURE GMEN SUB-MENU =====
        config_item = Gtk.MenuItem.new_with_label("⚙️  Configure GMen")
        config_menu = Gtk.Menu()
        
        # Workspace Manager Section
        ws_header = Gtk.MenuItem.new_with_label("🖥️  Workspace Manager")
        ws_header.set_sensitive(False)
        config_menu.append(ws_header)
        
        # Save Current Workspace
        save_ws_item = Gtk.MenuItem.new_with_label("💾 Save Current Workspace")
        save_ws_item.connect('activate', self.save_current_workspace)
        config_menu.append(save_ws_item)
        
        # Quick Save Workspace
        quick_save_item = Gtk.MenuItem.new_with_label("⚡ Quick Save Workspace")
        quick_save_item.connect('activate', self.quick_save_workspace)
        config_menu.append(quick_save_item)
        
        # Load Workspace
        load_ws_item = Gtk.MenuItem.new_with_label("📂 Load Workspace")
        load_ws_item.connect('activate', self.load_workspace_dialog)
        config_menu.append(load_ws_item)
        
        config_menu.append(Gtk.SeparatorMenuItem())
        
        # Window Management Section
        wm_header = Gtk.MenuItem.new_with_label("🗔  Window Management")
        wm_header.set_sensitive(False)
        config_menu.append(wm_header)
        
        if self.HAS_WINDOW_MANAGER and self.window_manager:
            # Save All Window Positions
            save_positions_item = Gtk.MenuItem.new_with_label("💾 Save All Window Positions")
            save_positions_item.connect('activate', self.save_all_window_positions)
            config_menu.append(save_positions_item)
            
            # View Running Instances
            instances_item = Gtk.MenuItem.new_with_label("👁️  View Running Instances")
            instances_item.connect('activate', self.show_running_instances)
            config_menu.append(instances_item)
        else:
            wm_disabled_item = Gtk.MenuItem.new_with_label("⚠️  Window Management Disabled")
            wm_disabled_item.set_sensitive(False)
            config_menu.append(wm_disabled_item)
        
        config_menu.append(Gtk.SeparatorMenuItem())
        
        # Database Tools Section
        db_header = Gtk.MenuItem.new_with_label("💾 Database Tools")
        db_header.set_sensitive(False)
        config_menu.append(db_header)
        
        # Backup Database
        backup_db_item = Gtk.MenuItem.new_with_label("💾 Backup Database")
        backup_db_item.connect('activate', self.backup_database)
        config_menu.append(backup_db_item)
        
        # Open Editor
        edit_item = Gtk.MenuItem.new_with_label("✏️ Edit Menu")
        edit_item.connect('activate', self.open_editor)
        config_menu.append(edit_item)
        
        # Reload Menu
        reload_item = Gtk.MenuItem.new_with_label("🔄 Reload Menu")
        reload_item.connect('activate', self.reload_menu)
        config_menu.append(reload_item)
        
        config_menu.append(Gtk.SeparatorMenuItem())
        
        # System Section
        system_header = Gtk.MenuItem.new_with_label("🖥️  System")
        system_header.set_sensitive(False)
        config_menu.append(system_header)
        
        # Open Config Directory
        config_dir_item = Gtk.MenuItem.new_with_label("📁 Open Config Directory")
        config_dir_item.connect('activate', self.open_config_directory)
        config_menu.append(config_dir_item)
        
        # View Database Info
        db_info_item = Gtk.MenuItem.new_with_label("📊 Database Info")
        db_info_item.connect('activate', self.show_database_info)
        config_menu.append(db_info_item)
        
        config_menu.append(Gtk.SeparatorMenuItem())
        
        # Status Item
        menu_info = self.db.fetch_one("""
            SELECT COUNT(*) as item_count FROM menu_items WHERE menu_id = ?
        """, (self.current_menu_id,))
        
        status_text = f"📋 Menu: {menu_info['item_count']} items"
        if self.HAS_WINDOW_MANAGER:
            status_text += " | 🗔 Window Mgmt: ✅"
        else:
            status_text += " | 🗔 Window Mgmt: ⚠️"
        
        status_item = Gtk.MenuItem.new_with_label(status_text)
        status_item.set_sensitive(False)
        config_menu.append(status_item)
        
        # Set the submenu
        config_item.set_submenu(config_menu)
        self.menu.append(config_item)
        
        self.menu.append(Gtk.SeparatorMenuItem())
        
        # ===== QUIT =====
        quit_item = Gtk.MenuItem.new_with_label("🚪 Quit GMen")
        quit_item.connect('activate', self.quit_app)
        self.menu.append(quit_item)
        
        self.menu.show_all()
        print(f"📝 Menu built with {menu_info['item_count']} items")
    
    def add_menu_items_recursive(self, all_items, parent_menu, parent_id=None, depth=0):
        """Add menu items recursively based on hierarchy"""
        # Filter items at current depth and parent
        current_items = [item for item in all_items 
                        if ((parent_id is None and item['depth'] == 0) or
                            (parent_id is not None and self.get_parent_id(all_items, item['id']) == parent_id))]
        
        for item in current_items:
            # Check if this item has children
            has_children = any(self.get_parent_id(all_items, child['id']) == item['id'] 
                             for child in all_items)
            
            if has_children:
                # Create submenu
                submenu_item = Gtk.MenuItem.new_with_label(item['title'])
                submenu = Gtk.Menu()
                
                # Add children recursively
                self.add_menu_items_recursive(all_items, submenu, item['id'], depth + 1)
                
                submenu_item.set_submenu(submenu)
                parent_menu.append(submenu_item)
            else:
                # Create regular menu item
                menu_item = self.create_menu_item(item)
                if menu_item:
                    parent_menu.append(menu_item)
    
    def get_parent_id(self, all_items, item_id):
        """Helper to find parent ID by checking if any item has this as parent"""
        for item in all_items:
            # Check children of this item
            child_ids = [child['id'] for child in all_items 
                        if self.get_item_depth(all_items, child['id']) == self.get_item_depth(all_items, item_id) - 1
                        and self.get_item_sort_key(all_items, child['id']) > self.get_item_sort_key(all_items, item_id)]
            
            if item_id in child_ids:
                return item['id']
        return None
    
    def get_item_depth(self, all_items, item_id):
        """Get depth of an item"""
        for item in all_items:
            if item['id'] == item_id:
                return item['depth']
        return 0
    
    def get_item_sort_key(self, all_items, item_id):
        """Get sort key for an item (simplified)"""
        for i, item in enumerate(all_items):
            if item['id'] == item_id:
                return i
        return 0
    
    def create_menu_item(self, item):
        """Create a GTK menu item from database record"""
        if not item['command']:
            return None
        
        # Create window state dict if available
        window_state = None
        if item['x'] is not None:
            window_state = {
                'enabled': True,
                'x': item['x'],
                'y': item['y'],
                'width': item['width'],
                'height': item['height'],
                'monitor': item['monitor'] or 0
            }
        
        # Create menu item with or without icon
        if item['icon'] and item['icon'].strip():
            menu_item = Gtk.ImageMenuItem.new_with_label(item['title'])
            try:
                image = Gtk.Image.new_from_icon_name(item['icon'], Gtk.IconSize.MENU)
                menu_item.set_image(image)
            except:
                pass
        else:
            menu_item = Gtk.MenuItem.new_with_label(item['title'])
        
        # Connect click handler
        menu_item.connect('activate', 
                         lambda w, cmd=item['command'], ws=window_state: 
                         self.launch_application(cmd, ws))
        
        return menu_item
    
    def launch_application(self, command, window_state=None):
        """Launch an application with optional window positioning"""
        if self.dry_run:
            print(f"🚫 DRY-RUN: Would launch: {command}")
            if window_state:
                print(f"     With window state: {window_state}")
            return
        
        print(f"🚀 Launching: {command}")
        
        def run():
            try:
                if self.HAS_WINDOW_MANAGER and self.window_manager and window_state:
                    # Use window manager for instance-aware positioning
                    pid, instance_id = self.window_manager.launch_with_state(command, window_state)
                    if pid > 0:
                        print(f"✅ Launched with PID: {pid}, Instance: {instance_id}")
                        
                        # Update usage timestamp in database
                        app_name = command.split()[0].lower() if command else ""
                        if app_name:
                            self.db.execute("""
                                UPDATE window_states 
                                SET last_used = CURRENT_TIMESTAMP
                                WHERE app_name = ? AND is_active = 1
                            """, (app_name,))
                    else:
                        # Fallback to simple launch
                        subprocess.Popen(command, shell=True)
                else:
                    # Simple launch without window management
                    subprocess.Popen(command, shell=True)
                    print(f"✅ Launched: {command}")
                    
            except Exception as e:
                print(f"❌ Launch failed: {e}")
                # Try simple shell execution as last resort
                try:
                    subprocess.Popen(command, shell=True)
                except Exception as e2:
                    print(f"❌ Complete failure: {e2}")
        
        # Launch in background thread
        threading.Thread(target=run, daemon=True).start()
    
    # ===== CONFIGURE GMEN FUNCTIONS =====
    
    def save_current_workspace(self, *args):
        """Save current window positions as workspace"""
        if not self.HAS_WINDOW_MANAGER or not self.window_manager:
            self.show_notification("Window manager not available", 3000)
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ws_name = f"Workspace_{timestamp}"
        
        success = self.window_manager.save_current_workspace(ws_name)
        if success:
            self.show_notification(f"Workspace '{ws_name}' saved!", 3000)
        else:
            self.show_notification("Failed to save workspace", 3000)
    
    def quick_save_workspace(self, *args):
        """Quick save with name dialog"""
        dialog = Gtk.Dialog(
            "Save Workspace",
            None,
            Gtk.DialogFlags.MODAL,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             "Save", Gtk.ResponseType.OK)
        )
        
        dialog.set_default_size(300, 100)
        
        box = dialog.get_content_area()
        label = Gtk.Label(label="Enter workspace name:")
        box.add(label)
        
        entry = Gtk.Entry()
        entry.set_text(f"Workspace_{datetime.now().strftime('%H%M%S')}")
        box.add(entry)
        
        box.show_all()
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            ws_name = entry.get_text().strip()
            if ws_name and self.HAS_WINDOW_MANAGER and self.window_manager:
                success = self.window_manager.save_current_workspace(ws_name)
                if success:
                    self.show_notification(f"Workspace '{ws_name}' saved!", 3000)
        
        dialog.destroy()
    
    def load_workspace_dialog(self, *args):
        """Show dialog to load workspace"""
        # Get saved workspaces from database
        workspaces = self.db.fetch("SELECT name FROM workspaces ORDER BY created_at DESC")
        
        if not workspaces:
            self.show_notification("No saved workspaces", 3000)
            return
        
        dialog = Gtk.Dialog(
            "Load Workspace",
            None,
            Gtk.DialogFlags.MODAL,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        )
        
        dialog.set_default_size(300, 400)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        scrolled.add(box)
        
        for ws in workspaces:
            btn = Gtk.Button(label=f"📂 {ws['name']}")
            btn.connect('clicked', lambda w, name=ws['name']: self.load_workspace(name, dialog))
            box.add(btn)
        
        dialog.get_content_area().add(scrolled)
        dialog.show_all()
        dialog.run()
        dialog.destroy()
    
    def load_workspace(self, name, dialog=None):
        """Load a workspace"""
        if not self.HAS_WINDOW_MANAGER or not self.window_manager:
            self.show_notification("Window manager not available", 3000)
            return
        
        success = self.window_manager.load_workspace(name)
        if success:
            self.show_notification(f"Workspace '{name}' loaded!", 3000)
        else:
            self.show_notification(f"Failed to load workspace '{name}'", 3000)
        
        if dialog:
            dialog.destroy()
    
    def save_all_window_positions(self, *args):
        """Save all current window positions to database"""
        if self.HAS_WINDOW_MANAGER and self.window_manager:
            success = self.window_manager.save_all_window_states()
            if success:
                self.show_notification("All window positions saved!", 3000)
            else:
                self.show_notification("Failed to save window positions", 3000)
    
    def show_running_instances(self, *args):
        """Show dialog with running instances"""
        if not self.HAS_WINDOW_MANAGER or not self.window_manager:
            self.show_notification("Instance tracking not available", 3000)
            return
        
        instances = self.window_manager.get_instance_info()
        
        dialog = Gtk.Dialog(
            "Running Instances",
            None,
            Gtk.DialogFlags.MODAL,
            (Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
        )
        
        dialog.set_default_size(400, 300)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        scrolled.add(box)
        
        if instances:
            for instance in instances:
                app_name = instance.get('app_name', 'Unknown')
                title = instance.get('title', 'No title')[:50]
                pid = instance.get('pid', 'N/A')
                
                label = Gtk.Label(label=f"• {app_name} (PID: {pid})\n  '{title}...'")
                label.set_xalign(0)
                box.add(label)
        else:
            label = Gtk.Label(label="No instances currently tracked")
            box.add(label)
        
        dialog.get_content_area().add(scrolled)
        dialog.show_all()
        dialog.run()
        dialog.destroy()
    
    def backup_database(self, *args):
        """Create a backup of the database"""
        backup_path = self.db.backup()
        self.show_notification(f"Database backed up to {backup_path.name}", 3000)
        print(f"💾 Backup created: {backup_path}")
    
    def open_editor(self, *args):
        """Launch the menu editor"""
        print("✏️ Launching menu editor...")
        try:
            # Try to find editor in current directory
            editor_path = Path.cwd() / "gmen_editor.py"
            if editor_path.exists():
                subprocess.Popen([sys.executable, str(editor_path)])
                self.show_notification("Editor launched", 2000)
            else:
                self.show_notification("Editor not found", 3000)
        except Exception as e:
            print(f"❌ Could not launch editor: {e}")
            self.show_notification(f"Failed to launch editor: {e}", 3000)
    
    def reload_menu(self, *args):
        """Reload menu from database"""
        # Rebuild the menu
        self.build_menu()
        self.show_notification("Menu reloaded from database", 2000)
        print("🔄 Menu reloaded")
    
    def open_config_directory(self, *args):
        """Open the config directory in file manager"""
        try:
            config_dir = Path.home() / ".config" / "gmen"
            subprocess.Popen(["xdg-open", str(config_dir)])
            print(f"📁 Opened config directory: {config_dir}")
        except Exception as e:
            print(f"❌ Could not open config directory: {e}")
    
    def show_database_info(self, *args):
        """Show database information dialog"""
        try:
            # Get stats
            menu_count = self.db.fetch_one("SELECT COUNT(*) as count FROM menus")['count']
            item_count = self.db.fetch_one("SELECT COUNT(*) as count FROM menu_items")['count']
            state_count = self.db.fetch_one("SELECT COUNT(*) as count FROM window_states WHERE is_active = 1")['count']
            workspace_count = self.db.fetch_one("SELECT COUNT(*) as count FROM workspaces")['count']
            
            db_size = os.path.getsize(self.db.db_path) / 1024  # KB
            
            dialog = Gtk.Dialog(
                "Database Information",
                None,
                Gtk.DialogFlags.MODAL,
                (Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
            )
            
            dialog.set_default_size(400, 300)
            
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            box.set_margin_start(20)
            box.set_margin_end(20)
            box.set_margin_top(20)
            box.set_margin_bottom(20)
            
            info = f"""
📊 Database Stats:
────────────────
Menus: {menu_count}
Menu Items: {item_count}
Window States: {state_count}
Workspaces: {workspace_count}
Database Size: {db_size:.1f} KB

📁 Location:
{self.db.db_path}
            """
            
            label = Gtk.Label(label=info)
            label.set_xalign(0)
            box.add(label)
            
            dialog.get_content_area().add(box)
            dialog.show_all()
            dialog.run()
            dialog.destroy()
            
        except Exception as e:
            print(f"❌ Could not show database info: {e}")
    
    def show_notification(self, message, duration=3000):
        """Show a temporary notification"""
        # Update tooltip
        self.indicator.set_label(message, "")
        
        # Reset after duration
        GLib.timeout_add(duration, self.reset_indicator_label)
    
    def reset_indicator_label(self):
        """Reset indicator label"""
        self.indicator.set_label("", "")
        return False
    
    def show_startup_info(self):
        """Show startup information"""
        menu_info = self.db.fetch_one("""
            SELECT m.name, COUNT(mi.id) as item_count 
            FROM menus m
            LEFT JOIN menu_items mi ON m.id = mi.menu_id
            WHERE m.id = ?
        """, (self.current_menu_id,))
        
        startup_msg = f"""
🎯 GMen v{self.version} - Database-First
───────────────────────────────
Menu: {menu_info['name']}
Items: {menu_info['item_count']}
Window Management: {'✅' if self.HAS_WINDOW_MANAGER else '⚠️ Disabled'}
Database: {self.db.db_path}
───────────────────────────────
Right-click the system tray icon
to access the menu.
        """
        
        print(startup_msg)
    
    def quit_app(self, *args):
        """Quit the application"""
        print("🛑 Quitting GMen...")
        
        # Cleanup window manager
        if self.HAS_WINDOW_MANAGER and self.window_manager:
            try:
                self.window_manager.cleanup()
                print("🧹 Cleaned up window manager")
            except Exception as e:
                print(f"⚠️  Cleanup error: {e}")
        
        # Close database
        self.db.close()
        
        # Quit GTK
        Gtk.main_quit()
        
        # Exit process
        sys.exit(0)
    
    def run(self):
        """Start the application"""
        print("▶️ GMen started - Running in system tray")
        Gtk.main()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GMen - Database-First Menu Launcher")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Dry run mode (don't execute commands)")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug output")
    
    args = parser.parse_args()
    
    # Create and run GMen
    gmen = GMen(dry_run=args.dry_run)
    gmen.run()


if __name__ == "__main__":
    main()
