"""
X11 Platform Implementation
"""

import subprocess
import re
from typing import List, Dict, Optional
from .base import PlatformInterface
import platform as sys_platform


class X11Platform(PlatformInterface):
    """X11-specific implementation"""
    
    def __init__(self):
        super().__init__()
        self.has_wmctrl = self._check_command("wmctrl")
        self.has_xdotool = self._check_command("xdotool")
        self.has_xrandr = self._check_command("xrandr")
    
    def _check_command(self, cmd: str) -> bool:
        try:
            subprocess.run(["which", cmd], check=True, 
                          capture_output=True)
            return True
        except:
            return False
    
    def get_monitors(self) -> List[Dict]:
        """Get monitor configuration from xrandr"""
        monitors = []
        
        if not self.has_xrandr:
            return [{'name': 'default', 'x': 0, 'y': 0, 'width': 1920, 'height': 1080, 'primary': True}]
        
        try:
            result = subprocess.run(
                ["xrandr", "--query"], 
                capture_output=True, 
                text=True,
                timeout=2
            )
            
            for line in result.stdout.splitlines():
                if " connected" in line:
                    parts = line.split()
                    name = parts[0]
                    is_primary = "primary" in line
                    
                    geometry_match = re.search(r'(\d+)x(\d+)\+(\d+)\+(\d+)', line)
                    
                    if geometry_match:
                        monitor = {
                            'name': name,
                            'width': int(geometry_match.group(1)),
                            'height': int(geometry_match.group(2)),
                            'x': int(geometry_match.group(3)),
                            'y': int(geometry_match.group(4)),
                            'primary': is_primary,
                            'connected': True
                        }
                        monitors.append(monitor)
            
            monitors.sort(key=lambda m: (m['x'], m['y']))
            
            if not monitors:
                monitors = [{'name': 'default', 'x': 0, 'y': 0, 'width': 1920, 'height': 1080, 'primary': True}]
            
        except Exception as e:
            monitors = [{'name': 'default', 'x': 0, 'y': 0, 'width': 1920, 'height': 1080, 'primary': True}]
        
        return monitors
    
    def get_all_windows(self) -> List[Dict]:
        """Get all windows from wmctrl"""
        if not self.has_wmctrl:
            return []
        
        try:
            result = subprocess.run(
                ["wmctrl", "-lpG"], 
                capture_output=True, 
                text=True,
                timeout=2
            )
            
            windows = []
            for line in result.stdout.splitlines():
                parsed = self._parse_wmctrl_line(line)
                if parsed:
                    windows.append(parsed)
            
            return windows
        except:
            return []
    
    def _parse_wmctrl_line(self, line: str) -> Optional[Dict]:
        """Parse wmctrl -lpG output"""
        parts = line.split(None, 8)
        if len(parts) >= 9:
            try:
                return {
                    'id': parts[0],
                    'desktop': parts[1],
                    'pid': int(parts[2]),
                    'x': int(parts[3]),
                    'y': int(parts[4]),
                    'width': int(parts[5]),
                    'height': int(parts[6]),
                    'hostname': parts[7],
                    'title': parts[8] if len(parts) > 8 else ""
                }
            except (ValueError, IndexError):
                return None
        return None
    
    def move_window(self, window_id: str, x: int, y: int, 
                   width: int, height: int) -> bool:
        """Move window using wmctrl"""
        if not self.has_wmctrl:
            return False
        
        geom = f"0,{x},{y},{width},{height}"
        
        try:
            result = subprocess.run(
                ["wmctrl", "-ir", window_id, "-e", geom],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    def get_active_window(self) -> Optional[Dict]:
        """Get active window using xdotool"""
        if not self.has_xdotool:
            return None
        
        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                window_id = result.stdout.strip()
                return {'id': window_id}
        except:
            pass
        
        return None
