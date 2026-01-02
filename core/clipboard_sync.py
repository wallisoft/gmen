# core/clipboard_sync.py
import time
import threading
import json
import logging
import requests
from gi.repository import GLib

logger = logging.getLogger(__name__)

class ClipboardManager:
    """Manages clipboard synchronization"""
    
    def __init__(self, discovery_service, api_port=8721):
        self.discovery = discovery_service
        self.api_port = api_port
        self.last_local_content = ""
        self.syncing = False
        self.sync_thread = None
        self.enabled_devices = set()  # Device IDs we sync with
        
        # Platform-specific clipboard
        try:
            import pyperclip
            self.clipboard = pyperclip
            self.has_clipboard = True
            logger.info("pyperclip available for clipboard sync")
        except ImportError:
            logger.warning("pyperclip not installed, clipboard sync disabled")
            self.has_clipboard = False
        
        # Callbacks for UI updates
        self.on_clipboard_received = None
        self.on_device_list_updated = None
    
    def start_sync(self):
        """Start clipboard synchronization"""
        if not self.has_clipboard:
            logger.error("Cannot start sync: pyperclip not available")
            return False
        
        if self.syncing:
            logger.warning("Sync already running")
            return False
        
        self.syncing = True
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.sync_thread.start()
        logger.info("Clipboard sync started")
        return True
    
    def stop_sync(self):
        """Stop clipboard synchronization"""
        self.syncing = False
        if self.sync_thread:
            self.sync_thread.join(timeout=2)
        logger.info("Clipboard sync stopped")
    
    def _sync_loop(self):
        """Main sync loop"""
        while self.syncing:
            try:
                # Check local clipboard for changes
                if self.has_clipboard:
                    current = self.clipboard.paste()
                    if current != self.last_local_content:
                        self.last_local_content = current
                        self._push_to_peers(current)
                
                # Check remote clipboards
                self._pull_from_peers()
                
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
            
            # Sleep a bit
            time.sleep(0.5)  # Check twice per second
    
    def _push_to_peers(self, content):
        """Push clipboard content to enabled peers"""
        if not content or len(content.strip()) == 0:
            return
        
        peers = self.discovery.get_peers()
        for device_id, peer in peers.items():
            if device_id in self.enabled_devices:
                try:
                    response = requests.post(
                        f"http://{peer['ip']}:{peer['port']}/clipboard",
                        json={'content': content},
                        timeout=1
                    )
                    if response.ok:
                        logger.debug(f"Clipboard sent to {peer['hostname']}")
                except requests.RequestException:
                    pass  # Peer offline or unreachable
    
    def _pull_from_peers(self):
        """Pull clipboard content from enabled peers"""
        peers = self.discovery.get_peers()
        for device_id, peer in peers.items():
            if device_id in self.enabled_devices:
                try:
                    response = requests.get(
                        f"http://{peer['ip']}:{peer['port']}/clipboard",
                        timeout=1
                    )
                    if response.ok:
                        data = response.json()
                        if data.get('success') and data.get('content'):
                            content = data['content']
                            
                            # Update local clipboard if different
                            if self.has_clipboard and content != self.clipboard.paste():
                                self.clipboard.copy(content)
                                self.last_local_content = content
                                
                                # Notify UI
                                if self.on_clipboard_received:
                                    GLib.idle_add(
                                        self.on_clipboard_received,
                                        peer['hostname'],
                                        content[:100] + "..." if len(content) > 100 else content
                                    )
                                
                                logger.debug(f"Clipboard updated from {peer['hostname']}")
                except requests.RequestException:
                    pass  # Peer offline or unreachable
    
    def enable_device(self, device_id):
        """Enable sync with a specific device"""
        self.enabled_devices.add(device_id)
        logger.info(f"Enabled sync with device {device_id[:8]}")
    
    def disable_device(self, device_id):
        """Disable sync with a specific device"""
        self.enabled_devices.discard(device_id)
        logger.info(f"Disabled sync with device {device_id[:8]}")
    
    def toggle_device(self, device_id):
        """Toggle sync with a device"""
        if device_id in self.enabled_devices:
            self.disable_device(device_id)
            return False
        else:
            self.enable_device(device_id)
            return True
    
    def get_clipboard(self):
        """Get current clipboard content"""
        if self.has_clipboard:
            return self.clipboard.paste()
        return ""
    
    def set_clipboard(self, content):
        """Set clipboard content"""
        if self.has_clipboard and content is not None:
            self.clipboard.copy(content)
            self.last_local_content = content
            return True
        return False
    
    def get_enabled_devices(self):
        """Get list of enabled device IDs"""
        return list(self.enabled_devices)
