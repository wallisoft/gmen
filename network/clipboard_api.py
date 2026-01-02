# network/clipboard_api.py
import json
import time
import threading
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import traceback

logger = logging.getLogger(__name__)

class ClipboardAPIHandler(BaseHTTPRequestHandler):
    """Simple HTTP API for clipboard exchange"""
    
    def __init__(self, *args, clipboard_manager=None, **kwargs):
        self.clipboard_manager = clipboard_manager
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        parsed = urlparse(self.path)
        
        if parsed.path == '/clipboard':
            # Get current clipboard content
            content = self.clipboard_manager.get_clipboard() if self.clipboard_manager else ""
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = json.dumps({
                'success': True,
                'content': content,
                'timestamp': time.time()
            })
            self.wfile.write(response.encode())
            
        elif parsed.path == '/devices':
            # List discovered devices
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            if self.clipboard_manager and self.clipboard_manager.discovery:
                devices = self.clipboard_manager.discovery.get_peers()
                response = json.dumps({'devices': list(devices.values())})
            else:
                response = json.dumps({'devices': []})
            
            self.wfile.write(response.encode())
            
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        """Handle POST requests"""
        if self.path == '/clipboard':
            # Set clipboard content
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                
                data = json.loads(post_data.decode())
                content = data.get('content', '')
                
                if self.clipboard_manager:
                    success = self.clipboard_manager.set_clipboard(content)
                else:
                    success = False
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response = json.dumps({'success': success})
                self.wfile.write(response.encode())
                
            except Exception as e:
                logger.error(f"POST error: {e}")
                self.send_response(400)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.debug(f"HTTP {self.address_string()} - {format % args}")


class ClipboardAPIServer:
    """Simple HTTP server for clipboard API"""
    
    def __init__(self, port=8721, clipboard_manager=None):
        self.port = port
        self.clipboard_manager = clipboard_manager
        self.server = None
        self.thread = None
        
    def start(self):
        """Start the API server"""
        try:
            handler = lambda *args: ClipboardAPIHandler(
                *args, clipboard_manager=self.clipboard_manager
            )
            
            self.server = HTTPServer(('0.0.0.0', self.port), handler)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            logger.info(f"Clipboard API server started on port {self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to start API server: {e}")
            return False
    
    def stop(self):
        """Stop the API server"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            logger.info("Clipboard API server stopped")
