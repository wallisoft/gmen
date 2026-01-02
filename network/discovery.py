# network/discovery.py
import socket
import json
import time
import threading
import os
from uuid import getnode
import logging

logger = logging.getLogger(__name__)

class LANDiscovery:
    """Simple LAN discovery via UDP broadcast"""
    
    def __init__(self, port=8720, api_port=8721):
        self.device_id = f"gmen-{getnode():012x}"
        self.port = port
        self.api_port = api_port
        self.peers = {}  # device_id -> peer_info
        self.running = False
        self.callback = None
        
    def start(self):
        """Start discovery service"""
        self.running = True
        # Start listener thread
        threading.Thread(target=self._listen_loop, daemon=True).start()
        # Start broadcaster thread
        threading.Thread(target=self._broadcast_loop, daemon=True).start()
        logger.info(f"LAN Discovery started (Device ID: {self.device_id[:8]}...)")
        return True
    
    def stop(self):
        """Stop discovery service"""
        self.running = False
    
    def _listen_loop(self):
        """Listen for UDP broadcasts from other GMen instances"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', self.port))
        sock.settimeout(1)
        
        while self.running:
            try:
                data, addr = sock.recvfrom(1024)
                peer_info = json.loads(data.decode())
                
                if peer_info.get('type') == 'presence':
                    device_id = peer_info['device_id']
                    
                    # Don't add ourselves
                    if device_id != self.device_id:
                        was_new = device_id not in self.peers
                        self.peers[device_id] = {
                            'ip': addr[0],
                            'port': peer_info.get('clipboard_port', self.api_port + 1),
                            'last_seen': time.time(),
                            'user': peer_info.get('user', 'unknown'),
                            'hostname': peer_info.get('hostname', 'unknown'),
                            'device_id': device_id
                        }
                        
                        logger.debug(f"Discovered peer: {peer_info.get('hostname')} at {addr[0]}")
                        
                        # Notify callback if set
                        if self.callback and was_new:
                            GLib.idle_add(self.callback, device_id, self.peers[device_id])
                            
            except socket.timeout:
                continue
            except json.JSONDecodeError as e:
                logger.debug(f"Invalid JSON from {addr}: {e}")
            except Exception as e:
                logger.error(f"Discovery error: {e}")
        
        sock.close()
    
    def _broadcast_loop(self):
        """Broadcast our presence on LAN"""
        while self.running:
            try:
                self._broadcast_presence()
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
            
            # Broadcast every 30 seconds
            for _ in range(30):
                if not self.running:
                    break
                time.sleep(1)
    
    def _broadcast_presence(self):
        """Send a presence broadcast"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        message = json.dumps({
            'type': 'presence',
            'device_id': self.device_id,
            'user': os.getlogin(),
            'hostname': socket.gethostname(),
            'clipboard_port': self.api_port,
            'timestamp': time.time()
        }).encode()
        
        sock.sendto(message, ('255.255.255.255', self.port))
        sock.close()
        logger.debug("Sent presence broadcast")
    
    def get_peers(self):
        """Get list of active peers (seen in last 2 minutes)"""
        now = time.time()
        active_peers = {}
        
        for device_id, peer in self.peers.items():
            if now - peer['last_seen'] < 120:  # 2 minutes
                active_peers[device_id] = peer
        
        return active_peers
    
    def set_callback(self, callback):
        """Set callback for new peer discovery"""
        self.callback = callback
