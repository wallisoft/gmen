"""
Platform Abstraction Interface
"""

import os
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import platform
import subprocess


class PlatformInterface(ABC):
    """Abstract interface all platforms must implement"""
    
    def __init__(self):
        self.name = self.__class__.__name__
        self.display_server = self._detect_display_server()
    
    @abstractmethod
    def get_monitors(self) -> List[Dict]:
        """Get list of monitors with geometry"""
        pass
    
    @abstractmethod
    def get_all_windows(self) -> List[Dict]:
        """Get all visible windows"""
        pass
    
    @abstractmethod
    def move_window(self, window_id: str, x: int, y: int, 
                   width: int, height: int) -> bool:
        """Move/resize window"""
        pass
    
    def _detect_display_server(self) -> str:
        """Detect display server"""
        system = platform.system()
        if system != "Linux":
            return system.lower()
        
        if os.environ.get("WAYLAND_DISPLAY"):
            return "wayland"
        if os.environ.get("XDG_SESSION_TYPE") == "wayland":
            return "wayland"
        
        return "x11"
    
    def get_clipboard_text(self) -> Optional[str]:
        """Get text from clipboard (cross-platform)"""
        try:
            import pyperclip
            return pyperclip.paste()
        except ImportError:
            # Fallback to platform-specific
            system = platform.system()
            if system == "Linux":
                if self.display_server == "x11":
                    return self._get_clipboard_x11()
                else:
                    return self._get_clipboard_wayland()
            return None
    
    def set_clipboard_text(self, text: str) -> bool:
        """Set text to clipboard (cross-platform)"""
        try:
            import pyperclip
            pyperclip.copy(text)
            return True
        except ImportError:
            # Fallback to platform-specific
            system = platform.system()
            if system == "Linux":
                if self.display_server == "x11":
                    return self._set_clipboard_x11(text)
                else:
                    return self._set_clipboard_wayland(text)
            return False
    
    def _get_clipboard_x11(self) -> Optional[str]:
        """X11 clipboard access"""
        try:
            result = subprocess.run(
                ["xclip", "-selection", "clipboard", "-o"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return None
    
    def _set_clipboard_x11(self, text: str) -> bool:
        """X11 clipboard set"""
        try:
            process = subprocess.Popen(
                ["xclip", "-selection", "clipboard"],
                stdin=subprocess.PIPE
            )
            process.communicate(input=text.encode())
            return process.returncode == 0
        except:
            return False
    
    def _get_clipboard_wayland(self) -> Optional[str]:
        """Wayland clipboard access"""
        try:
            result = subprocess.run(
                ["wl-paste"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return None
    
    def _set_clipboard_wayland(self, text: str) -> bool:
        """Wayland clipboard set"""
        try:
            process = subprocess.Popen(
                ["wl-copy"],
                stdin=subprocess.PIPE
            )
            process.communicate(input=text.encode())
            return process.returncode == 0
        except:
            return False
    
    def launch_process(self, command: str) -> int:
        """Launch a process and return PID"""
        import subprocess
        process = subprocess.Popen(command, shell=True)
        return process.pid
