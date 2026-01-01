"""
Platform Factory - Auto-detects and returns platform implementation
"""

import os
import platform
from .base import PlatformInterface


def get_platform() -> PlatformInterface:
    """Get platform-specific implementation"""
    system = platform.system()
    
    # Check for Wayland first
    display = os.environ.get("WAYLAND_DISPLAY")
    session_type = os.environ.get("XDG_SESSION_TYPE")
    
    if system == "Linux":
        if display or session_type == "wayland":
            try:
                from .wayland import WaylandPlatform
                return WaylandPlatform()
            except ImportError:
                # Fall back to X11
                pass
        
        from .linux_x11 import X11Platform
        return X11Platform()
    
    elif system == "Darwin":
        from .macos import MacOSPlatform
        return MacOSPlatform()
    
    elif system == "Windows":
        from .windows import WindowsPlatform
        return WindowsPlatform()
    
    else:
        # Fallback platform
        from .base import PlatformInterface
        class FallbackPlatform(PlatformInterface):
            def get_monitors(self):
                return [{'name': 'default', 'x': 0, 'y': 0, 'width': 1920, 'height': 1080}]
            
            def get_all_windows(self):
                return []
            
            def move_window(self, window_id, x, y, width, height):
                return False
        
        return FallbackPlatform()
