import time
import threading
import json
import logging
import requests
from gi.repository import GLib

logger = logging.getLogger(__name__)


class ClipboardManager:
    """Manages clipboard synchronization - EVENT DRIVEN VERSION"""
    
    def __init__(self, discovery_service, api_port=8721):
        self.discovery = discovery_service
        self.api_port = api_port
        self.last_local_content = ""
        self.syncing = False
        self.sync_thread = None
        self.remote_check_thread = None
        self.enabled_devices = set()  # Device IDs we sync with
        
        # Event-driven clipboard monitor
        self.clipboard_listener = None
        
        # Platform-specific clipboard
        try:
            import pyperclip
            self.clipboard = pyperclip
            self.has_clipboard = True
            logger.info("pyperclip available for clipboard sync")
        except ImportError:
            logger.warning("pyperclip not installed, clipboard sync will be read-only")
            self.has_clipboard = False
        
        # Callbacks for UI updates
        self.on_clipboard_received = None
        self.on_device_list_updated = None
        
        logger.info("ClipboardManager initialized (event-driven)")
    
    def start_sync(self):
        """Start clipboard synchronization - EVENT DRIVEN"""
        if self.syncing:
            logger.warning("Sync already running")
            return False
        
        # Try to create event-driven listener
        try:
            from core.clipboard_monitor import create_clipboard_listener
            self.clipboard_listener = create_clipboard_listener(self._on_local_clipboard_changed)
            self.clipboard_listener.start()
            logger.info("Event-driven clipboard listener started")
        except ImportError as e:
            logger.warning(f"Cannot create event listener: {e}, falling back to polling")
            return self._start_polling_sync()
        
        # Start checking for remote changes (less frequent)
        self.syncing = True
        self.remote_check_thread = threading.Thread(target=self._check_remote_loop, daemon=True)
        self.remote_check_thread.start()
        
        logger.info("Clipboard sync started (event-driven)")
        return True
    
    def _start_polling_sync(self):
        """Fallback to polling sync if event-driven fails"""
        if not self.has_clipboard:
            logger.error("Cannot start sync: pyperclip not available")
            return False
        
        self.syncing = True
        self.sync_thread = threading.Thread(target=self._polling_sync_loop, daemon=True)
        self.sync_thread.start()
        logger.info("Clipboard sync started (polling fallback)")
        return True
    
    def _polling_sync_loop(self):
        """Polling fallback loop (original behavior)"""
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
    
    def stop_sync(self):
        """Stop clipboard synchronization"""
        self.syncing = False
        
        # Stop event listener if active
        if self.clipboard_listener:
            self.clipboard_listener.stop()
            self.clipboard_listener = None
        
        # Wait for threads to finish (if they exist)
        if self.sync_thread:
            self.sync_thread.join(timeout=1)
        if self.remote_check_thread:
            self.remote_check_thread.join(timeout=1)
        
        logger.info("Clipboard sync stopped")
    
    def _on_local_clipboard_changed(self, content):
        """Called when local clipboard changes (event-driven)"""
        if not content or len(content.strip()) == 0:
            return
        
        self.last_local_content = content
        logger.debug(f"📤 Local clipboard changed: {content[:50]}...")
        self._push_to_peers(content)
    
    def _check_remote_loop(self):
        """Check for remote clipboard changes (every 2 seconds)"""
        while self.syncing:
            try:
                self._pull_from_peers()
            except Exception as e:
                logger.error(f"Remote check error: {e}")
            
            time.sleep(2)  # Check remote less frequently
    
    def _push_to_peers(self, content):
        """Push clipboard content to enabled peers"""
        if not content or len(content.strip()) == 0:
            return
        
        peers = self.discovery.get_peers()
        
        if not peers:
            logger.debug("No peers to push to")
            return
        
        sent_count = 0
        for device_id, peer in peers.items():
            if device_id in self.enabled_devices:
                try:
                    response = requests.post(
                        f"http://{peer['ip']}:{peer['port']}/clipboard",
                        json={'content': content},
                        timeout=1
                    )
                    if response.ok:
                        sent_count += 1
                        logger.debug(f"📨 Sent to {peer['hostname']}")
                except requests.RequestException as e:
                    logger.debug(f"Could not send to {peer['hostname']}: {e}")
        
        if sent_count > 0:
            logger.info(f"📤 Clipboard sent to {sent_count} device(s)")
    
    def _pull_from_peers(self):
        """Pull clipboard content from enabled peers"""
        peers = self.discovery.get_peers()
        
        if not peers:
            return
        
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
                            
                            # Update if different from current
                            current = self.get_clipboard()
                            if content and content != current:
                                success = self.set_clipboard(content)
                                
                                if success:
                                    # Notify UI
                                    if self.on_clipboard_received:
                                        GLib.idle_add(
                                            self.on_clipboard_received,
                                            peer['hostname'],
                                            content[:100] + "..." if len(content) > 100 else content
                                        )
                                    
                                    logger.debug(f"📥 Received from {peer['hostname']}")
                except requests.RequestException as e:
                    logger.debug(f"Could not receive from {peer['hostname']}: {e}")
                except json.JSONDecodeError as e:
                    logger.debug(f"Invalid response from {peer['hostname']}: {e}")
    
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
        # Try event listener first
        if self.clipboard_listener:
            return self.clipboard_listener.get_last_content()
        
        # Fallback to pyperclip
        if self.has_clipboard:
            try:
                return self.clipboard.paste()
            except Exception as e:
                logger.error(f"Failed to get clipboard: {e}")
        
        return ""
    
    def set_clipboard(self, content):
        """Set clipboard content"""
        if not content:
            return False
        
        try:
            if self.has_clipboard:
                self.clipboard.copy(content)
                self.last_local_content = content
                return True
            else:
                logger.warning("pyperclip not available, cannot set clipboard")
                return False
        except Exception as e:
            logger.error(f"Failed to set clipboard: {e}")
            return False
    
    def get_enabled_devices(self):
        """Get list of enabled device IDs"""
        return list(self.enabled_devices)
    
    def debug_status(self):
        """Print debug info"""
        peers = self.discovery.get_peers()
        
        status = {
            'syncing': self.syncing,
            'has_clipboard': self.has_clipboard,
            'enabled_devices': len(self.enabled_devices),
            'total_peers': len(peers),
            'event_driven': self.clipboard_listener is not None,
            'last_local': self.last_local_content[:50] + "..." if len(self.last_local_content) > 50 else self.last_local_content
        }
        
        logger.info(f"Clipboard Manager Status: {status}")
        
        if peers:
            logger.info("Peers:")
            for device_id, peer in peers.items():
                enabled = device_id in self.enabled_devices
                logger.info(f"  - {peer['hostname']} ({peer['ip']}): enabled={enabled}")
        
        return status
