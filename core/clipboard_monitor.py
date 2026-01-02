import threading
import time
import logging
import platform
import subprocess
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ClipboardListener(ABC):
    """Abstract base for clipboard event listeners"""
    
    @abstractmethod
    def start(self):
        """Start listening for clipboard changes"""
        pass
    
    @abstractmethod
    def stop(self):
        """Stop listening"""
        pass
    
    @abstractmethod
    def get_last_content(self):
        """Get current clipboard content"""
        pass


class LinuxX11Listener(ClipboardListener):
    """X11 clipboard event listener"""
    
    def __init__(self, callback):
        self.callback = callback
        self.running = False
        self.last_content = ""
        self.thread = None
        self.check_interval = 0.1  # 100ms
        
    def start(self):
        """Start monitoring X11 clipboard"""
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.info("X11 clipboard listener started")
        return True
        
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("X11 clipboard listener stopped")
            
    def _monitor_loop(self):
        """Monitor clipboard changes"""
        while self.running:
            try:
                current = self._get_clipboard_x11()
                
                if current != self.last_content:
                    self.last_content = current
                    if current and current.strip():  # Only callback on non-empty content
                        self.callback(current)
                
                time.sleep(self.check_interval)
                    
            except Exception as e:
                logger.error(f"Clipboard monitor error: {e}")
                time.sleep(1)
    
    def _get_clipboard_x11(self):
        """Get clipboard content using xclip or xsel"""
        # Try xclip first (most common)
        try:
            result = subprocess.run(
                ['xclip', '-selection', 'clipboard', '-o'],
                capture_output=True,
                text=True,
                timeout=0.5
            )
            if result.returncode == 0:
                return result.stdout
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
            
        # Fallback to xsel
        try:
            result = subprocess.run(
                ['xsel', '--clipboard', '--output'],
                capture_output=True,
                text=True,
                timeout=0.5
            )
            if result.returncode == 0:
                return result.stdout
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
            
        return ""
    
    def get_last_content(self):
        return self.last_content


class PollingListener(ClipboardListener):
    """Fallback polling listener"""
    
    def __init__(self, callback):
        self.callback = callback
        self.running = False
        self.last_content = ""
        self.thread = None
        self.check_interval = 0.5  # 500ms
        
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()
        logger.info("Polling clipboard listener started")
        return True
        
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("Polling clipboard listener stopped")
            
    def _poll_loop(self):
        """Poll clipboard for changes"""
        while self.running:
            try:
                current = self._get_clipboard()
                
                if current != self.last_content:
                    self.last_content = current
                    if current and current.strip():
                        self.callback(current)
                
                time.sleep(self.check_interval)
                    
            except Exception as e:
                logger.error(f"Polling error: {e}")
                time.sleep(1)
    
    def _get_clipboard(self):
        """Get clipboard using pyperclip or system commands"""
        # Try pyperclip first
        try:
            import pyperclip
            return pyperclip.paste()
        except ImportError:
            pass
        
        # System fallbacks
        system = platform.system()
        
        if system == "Linux":
            try:
                result = subprocess.run(
                    ['xclip', '-selection', 'clipboard', '-o'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    return result.stdout
            except:
                pass
        elif system == "Darwin":
            try:
                result = subprocess.run(
                    ['pbpaste'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    return result.stdout
            except:
                pass
        
        return ""
    
    def get_last_content(self):
        return self.last_content


def create_clipboard_listener(callback):
    """Factory to create platform-specific clipboard listener"""
    system = platform.system()
    
    if system == "Linux":
        # Check session type
        display = platform.getenv("XDG_SESSION_TYPE", "").lower()
        wayland = platform.getenv("WAYLAND_DISPLAY")
        
        if wayland or display == "wayland":
            logger.warning("Wayland detected - clipboard events limited, using polling")
            return PollingListener(callback)
        else:
            # X11 - use optimized listener
            return LinuxX11Listener(callback)
    
    elif system == "Windows":
        # TODO: Implement proper Windows listener
        logger.info("Windows detected - using polling")
        return PollingListener(callback)
    
    elif system == "Darwin":
        # TODO: Implement proper macOS listener
        logger.info("macOS detected - using polling")
        return PollingListener(callback)
    
    else:
        logger.warning(f"Unsupported platform: {system}, using polling")
        return PollingListener(callback)
