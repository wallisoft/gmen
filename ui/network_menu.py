import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import logging

logger = logging.getLogger(__name__)

class NetworkMenu:
    """Network-related menu items"""
    
    def __init__(self, clipboard_manager, discovery_service):
        self.clipboard_manager = clipboard_manager
        self.discovery = discovery_service
        self.device_items = {}  # device_id -> menu_item
        self.devices_menu_item = None  # The menu item that contains devices submenu
        
        # Setup callbacks
        if clipboard_manager:
            clipboard_manager.on_clipboard_received = self.on_clipboard_received
        
        if discovery_service:
            discovery_service.callback = self.on_device_discovered
    
    def create_network_menu(self):
        """Create network submenu"""
        network_menu = Gtk.Menu()
        
        # Clipboard sync toggle
        self.sync_item = Gtk.CheckMenuItem(label="Sync Clipboard")
        self.sync_item.set_active(False)
        self.sync_item.connect("toggled", self.on_sync_toggled)
        network_menu.append(self.sync_item)
        
        network_menu.append(Gtk.SeparatorMenuItem())
        
        # Device list header
        devices_header = Gtk.MenuItem(label="Connected Devices")
        devices_header.set_sensitive(False)
        network_menu.append(devices_header)
        
        # Devices submenu - store reference to the parent menu item
        self.devices_menu = Gtk.Menu()
        self.devices_menu_item = Gtk.MenuItem(label="No devices found")
        self.devices_menu_item.set_submenu(self.devices_menu)
        network_menu.append(self.devices_menu_item)
        
        # Refresh button
        refresh_item = Gtk.MenuItem(label="Refresh List")
        refresh_item.connect("activate", self.refresh_device_list)
        network_menu.append(refresh_item)
        
        network_menu.append(Gtk.SeparatorMenuItem())
        
        # Network info
        info_item = Gtk.MenuItem(label="Network Info")
        info_item.connect("activate", self.show_network_info)
        network_menu.append(info_item)
        
        return network_menu
    
    def on_sync_toggled(self, menu_item):
        """Handle clipboard sync toggle"""
        if menu_item.get_active():
            if self.clipboard_manager and self.clipboard_manager.start_sync():
                menu_item.set_label("✓ Sync Clipboard")
                self.show_notification("Clipboard sync enabled", 2000)
            else:
                menu_item.set_active(False)
                self.show_notification("Clipboard sync failed - install pyperclip", 3000)
        else:
            if self.clipboard_manager:
                self.clipboard_manager.stop_sync()
            menu_item.set_label("Sync Clipboard")
            self.show_notification("Clipboard sync disabled", 2000)
    
    def on_device_discovered(self, device_id, peer_info):
        """Called when a new device is discovered"""
        GLib.idle_add(self._add_device_item, device_id, peer_info)
    
    def _add_device_item(self, device_id, peer_info):
        """Add a device to the menu"""
        # Remove old item if exists
        if device_id in self.device_items:
            old_item = self.device_items[device_id]
            self.devices_menu.remove(old_item)
        
        # Create new menu item
        label = f"{peer_info['hostname']} ({peer_info['user']})"
        device_item = Gtk.CheckMenuItem(label=label)
        
        # Check if this device is enabled for sync
        is_enabled = False
        if self.clipboard_manager:
            is_enabled = device_id in self.clipboard_manager.get_enabled_devices()
        device_item.set_active(is_enabled)
        
        # Connect toggle handler
        device_item.connect("toggled", self.on_device_toggled, device_id)
        
        # Add to menu
        self.devices_menu.append(device_item)
        self.device_items[device_id] = device_item
        
        # Update the devices menu item label
        if self.devices_menu_item:
            if self.device_items:
                self.devices_menu_item.set_label(f"Devices ({len(self.device_items)})")
            else:
                self.devices_menu_item.set_label("No devices found")
        
        self.devices_menu.show_all()
    
    def on_device_toggled(self, menu_item, device_id):
        """Handle device sync toggle"""
        if self.clipboard_manager:
            enabled = self.clipboard_manager.toggle_device(device_id)
            if enabled:
                self.show_notification(f"Syncing with {menu_item.get_label()}", 1500)
            else:
                self.show_notification(f"Stopped syncing with {menu_item.get_label()}", 1500)
    
    def refresh_device_list(self, menu_item):
        """Refresh the device list"""
        # Clear current items
        for item in list(self.devices_menu.get_children()):
            self.devices_menu.remove(item)
        self.device_items.clear()
        
        # Add current peers
        if self.discovery:
            peers = self.discovery.get_peers()
            for device_id, peer_info in peers.items():
                self._add_device_item(device_id, peer_info)
        
        # Update menu item label
        if self.devices_menu_item:
            if self.device_items:
                self.devices_menu_item.set_label(f"Devices ({len(self.device_items)})")
            else:
                self.devices_menu_item.set_label("No devices found")
        
        self.show_notification("Device list refreshed", 1000)
    
    def update_device_list(self):
        """Update device list from discovery service"""
        self.refresh_device_list(None)
    
    def on_clipboard_received(self, hostname, content_preview):
        """Called when clipboard is received from another device"""
        self.show_notification(f"Clipboard from {hostname}: {content_preview}", 3000)
    
    def show_network_info(self, menu_item):
        """Show network information dialog"""
        dialog = Gtk.Dialog(
            title="GMen Network Info",
            parent=None,
            flags=0,
            buttons=(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        )
        
        dialog.set_default_size(300, 200)
        
        content = dialog.get_content_area()
        
        # Device ID
        device_id = self.discovery.device_id if self.discovery else "Unknown"
        id_label = Gtk.Label(label=f"Device ID: {device_id[:16]}...")
        id_label.set_xalign(0)
        content.pack_start(id_label, False, False, 5)
        
        # API Port
        port = self.clipboard_manager.api_port if self.clipboard_manager else "Unknown"
        port_label = Gtk.Label(label=f"API Port: {port}")
        port_label.set_xalign(0)
        content.pack_start(port_label, False, False, 5)
        
        # Status
        status = "Active" if self.clipboard_manager and self.clipboard_manager.syncing else "Inactive"
        status_label = Gtk.Label(label=f"Sync Status: {status}")
        status_label.set_xalign(0)
        content.pack_start(status_label, False, False, 5)
        
        # Peers count
        peers = self.discovery.get_peers() if self.discovery else {}
        peers_label = Gtk.Label(label=f"Peers Found: {len(peers)}")
        peers_label.set_xalign(0)
        content.pack_start(peers_label, False, False, 5)
        
        # Local IP (helpful for debugging)
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            ip_label = Gtk.Label(label=f"Local IP: {local_ip}")
            ip_label.set_xalign(0)
            content.pack_start(ip_label, False, False, 5)
        except:
            pass
        
        dialog.show_all()
        dialog.run()
        dialog.destroy()
    
    def show_notification(self, message, duration=2000):
        """Show a temporary notification"""
        logger.info(f"Notification: {message}")
