"""
Wayland Platform Implementation (Stub)
"""

from .base import PlatformInterface
from typing import List, Dict


class WaylandPlatform(PlatformInterface):
    """Wayland-specific implementation (limited capabilities)"""
    
    def __init__(self):
        super().__init__()
        print("⚠️  Wayland support is experimental")
    
    def get_monitors(self) -> List[Dict]:
        """Get monitor configuration for Wayland"""
        # Try to use wlr-randr or similar
        try:
            import subprocess
            result = subprocess.run(
                ["wlr-randr"],
                capture_output=True, text=True
            )
            # Parse output... (simplified for now)
        except:
            pass
        
        return [{'name': 'wayland', 'x': 0, 'y': 0, 'width': 1920, 'height': 1080, 'primary': True}]
    
    def get_all_windows(self) -> List[Dict]:
        """Wayland window listing is limited"""
        print("⚠️  Window listing limited on Wayland")
        return []
    
    def move_window(self, window_id: str, x: int, y: int, 
                   width: int, height: int) -> bool:
        """Wayland window movement may be restricted"""
        print("⚠️  Direct window control limited on Wayland")
        return False
