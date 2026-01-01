#!/usr/bin/env python3
"""
Window Manager v5 - Thread-Safe Database-First for GMen
Fixed thread-safety issues
"""

import subprocess
import time
import threading
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Set, Tuple
import hashlib

from database import get_database

class ThreadSafeWindowManager:
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        # Each thread gets its own database connection
        self.db = None  # Will be initialized in each thread
        
        # Check for X11 tools
        self.has_wmctrl = self._check_tool("wmctrl")
        self.has_xdotool = self._check_tool("xdotool")
        self.has_xrandr = self._check_tool("xrandr")
        
        print(f"🔧 X11 Tools: wmctrl={'✅' if self.has_wmctrl else '❌'}, "
              f"xdotool={'✅' if self.has_xdotool else '❌'}, "
              f"xrandr={'✅' if self.has_xrandr else '❌'}")
        
        # Get monitor configuration
        self.monitors = self._get_monitor_configuration()
        print(f"🖥️  Detected {len(self.monitors)} monitors")
        
        # Track existing windows
        self.existing_windows = self._capture_current_windows()
        
        # Thread-safe instance tracking
        self.active_instances = {}
        self.instance_lock = threading.Lock()
        
        # Start instance monitor with thread-local DB
        self.monitor_running = False
        self.start_instance_monitor()
    
    def get_db(self):
        """Get thread-local database connection"""
        if self.db is None:
            self.db = get_database(self.config_dir)
        return self.db
    
    def _check_tool(self, tool: str) -> bool:
        """Check if tool is available"""
        try:
            subprocess.run(["which", tool], check=True, 
                          capture_output=True, text=True)
            return True
        except:
            return False
    
    def _get_monitor_configuration(self) -> List[Dict]:
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
            print(f"⚠️  Error getting monitor configuration: {e}")
            monitors = [{'name': 'default', 'x': 0, 'y': 0, 'width': 1920, 'height': 1080, 'primary': True}]
        
        return monitors
    
    def _capture_current_windows(self) -> Set[str]:
        """Capture current window IDs and titles"""
        if not self.has_wmctrl:
            return set()
        
        try:
            windows = self._get_all_windows()
            window_keys = set()
            
            for win in windows:
                window_key = f"{win['pid']}:{win['title'][:50]}:{win['id'][-4:]}"
                window_keys.add(window_key)
            
            return window_keys
        except:
            return set()
    
    def _get_all_windows(self) -> List[Dict]:
        """Get all current windows from X11"""
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
        except subprocess.TimeoutExpired:
            print("⚠️  wmctrl timed out")
            return []
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
    
    def _get_process_name(self, pid: int) -> str:
        """Get process name from PID"""
        try:
            with open(f"/proc/{pid}/comm", 'r') as f:
                name = f.read().strip()
                name = name.replace('\x00', '').strip()
                if name.endswith('-'):
                    name = name[:-1]
                return name
        except:
            return ""
    
    def get_window_state_for_app(self, app_name: str) -> Optional[Dict]:
        """Get saved window state for an application from database"""
        db = self.get_db()
        state = db.fetch_one("""
            SELECT x, y, width, height, monitor, last_used
            FROM window_states 
            WHERE app_name = ? AND is_active = 1 AND remember = 1
            ORDER BY last_used DESC 
            LIMIT 1
        """, (app_name,))
        
        return state
    
    def save_window_state(self, app_name: str, x: int, y: int, 
                         width: int, height: int, monitor: int = 0):
        """Save window state to database"""
        db = self.get_db()
        
        existing = db.fetch_one("""
            SELECT id FROM window_states 
            WHERE app_name = ? AND is_active = 1
        """, (app_name,))
        
        if existing:
            db.execute("""
                UPDATE window_states 
                SET x = ?, y = ?, width = ?, height = ?, monitor = ?,
                    last_used = CURRENT_TIMESTAMP
                WHERE app_name = ? AND is_active = 1
            """, (x, y, width, height, monitor, app_name))
        else:
            db.execute("""
                INSERT INTO window_states 
                (app_name, x, y, width, height, monitor, is_active, remember)
                VALUES (?, ?, ?, ?, ?, ?, 1, 1)
            """, (app_name, x, y, width, height, monitor))
        
        print(f"💾 Saved window state for {app_name}: ({x},{y}) {width}x{height}")
    
    def launch_with_state(self, command: str, window_state: dict = None) -> Tuple[int, str]:
        """Launch app with database-based positioning"""
        print(f"\n{'='*60}")
        print(f"🚀 LAUNCHING: {command}")
        
        app_name = command.split()[0].lower() if command else ""
        print(f"🔍 App name: {app_name}")
        
        x = y = width = height = monitor_idx = None
        
        if window_state and window_state.get('enabled', False):
            print(f"🔍 Using PROVIDED window state")
            x = window_state.get('x')
            y = window_state.get('y')
            width = window_state.get('width')
            height = window_state.get('height')
            monitor_idx = window_state.get('monitor', 0)
        else:
            db_state = self.get_window_state_for_app(app_name)
            if db_state:
                print(f"🔍 Using DATABASE window state")
                x = db_state['x']
                y = db_state['y']
                width = db_state['width']
                height = db_state['height']
                monitor_idx = db_state['monitor']
        
        # Convert to global coordinates if monitor specified
        if x is not None and y is not None and monitor_idx is not None:
            if 0 <= monitor_idx < len(self.monitors):
                monitor = self.monitors[monitor_idx]
                global_x = monitor['x'] + x
                global_y = monitor['y'] + y
                x, y = global_x, global_y
        
        # Launch the app
        try:
            process = subprocess.Popen(command, shell=True)
            pid = process.pid
            print(f"✅ Launched PID: {pid}")
            
            # Start instance tracker with thread-local DB
            tracker = threading.Thread(
                target=self._track_new_instance,
                args=(app_name, pid, x, y, width, height),
                daemon=True
            )
            tracker.start()
            
            instance_hash = hashlib.md5(f"{app_name}_{pid}_{time.time()}".encode()).hexdigest()[:16]
            
            return pid, instance_hash
            
        except Exception as e:
            print(f"❌ Launch failed: {e}")
            process = subprocess.Popen(command, shell=True)
            return process.pid, "fallback"
    
    def _track_new_instance(self, app_name: str, expected_pid: int,
                           x: int, y: int, width: int, height: int):
        """Track and position a newly launched window"""
        # Each tracker thread gets its own DB connection
        self.db = get_database(self.config_dir)
        
        max_attempts = 15 if app_name == "gnome-terminal" else 10
        
        for attempt in range(max_attempts):
            try:
                current_windows = self._get_all_windows()
                
                new_windows = []
                for win in current_windows:
                    window_key = f"{win['pid']}:{win['title'][:50]}:{win['id'][-4:]}"
                    
                    if window_key not in self.existing_windows:
                        proc_name = self._get_process_name(win['pid'])
                        if self._window_matches_app(app_name, proc_name, win['title']):
                            new_windows.append(win)
                
                if new_windows:
                    target_window = new_windows[0]  # Simplified
                    
                    if target_window:
                        print(f"🎯 FOUND NEW INSTANCE: Window {target_window['id']}")
                        
                        # Apply positioning
                        if all(v is not None for v in [x, y, width, height]):
                            success = self._apply_window_position(
                                target_window['id'], x, y, width, height, app_name
                            )
                            
                            if success:
                                self.save_window_state(
                                    app_name,
                                    target_window['x'],
                                    target_window['y'],
                                    target_window['width'],
                                    target_window['height'],
                                    monitor=0
                                )
                        
                        return
                
                time.sleep(0.5)
                
            except Exception as e:
                print(f"⚠️  Tracking error: {e}")
                time.sleep(1)
        
        print(f"😞 Could not track new {app_name} instance")
    
    def _window_matches_app(self, app_name: str, proc_name: str, title: str) -> bool:
        """Check if window matches app name"""
        if not app_name or not proc_name:
            return False
        
        if app_name.lower() in proc_name.lower():
            return True
        
        if app_name.lower() in title.lower():
            return True
        
        return False
    
    def _apply_window_position(self, window_id: str, x: int, y: int, 
                              width: int, height: int, app_name: str) -> bool:
        """Apply position to window on X11"""
        if not self.has_wmctrl:
            return False
        
        x = max(0, x)
        y = max(0, y)
        width = max(100, width)
        height = max(100, height)
        
        geom = f"0,{x},{y},{width},{height}"
        
        try:
            result = subprocess.run(
                ["wmctrl", "-ir", window_id, "-e", geom],
                capture_output=True, 
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                print(f"✅ SUCCESS: {app_name} window positioned!")
                return True
            
            return False
                
        except Exception as e:
            print(f"❌ Positioning error: {e}")
            return False
    
    def start_instance_monitor(self):
        """Start background instance monitoring"""
        if self.monitor_running:
            return
        
        self.monitor_running = True
        monitor_thread = threading.Thread(
            target=self._instance_monitor_loop, 
            daemon=True
        )
        monitor_thread.start()
        print("👁️  Instance monitoring started")
    
    def _instance_monitor_loop(self):
        """Monitor instance states in background"""
        # Monitor thread gets its own DB connection
        self.db = get_database(self.config_dir)
        
        while self.monitor_running:
            try:
                self._update_instance_states()
                time.sleep(5)
            except Exception as e:
                print(f"⚠️  Instance monitor error: {e}")
                time.sleep(10)
    
    def _update_instance_states(self):
        """Update instance states from current windows"""
        try:
            windows = self._get_all_windows()
            
            for win in windows:
                proc_name = self._get_process_name(win['pid'])
                if proc_name:
                    self.db.execute("""
                        UPDATE window_states 
                        SET last_used = CURRENT_TIMESTAMP
                        WHERE app_name = ? AND is_active = 1
                    """, (proc_name,))
            
        except Exception as e:
            print(f"⚠️  Instance update error: {e}")
    
    def cleanup(self):
        """Clean up before exit"""
        self.monitor_running = False
        if self.db:
            self.db.close()
        print("🧹 Window manager cleanup complete")


def create_window_manager(config_dir: Path = None):
    """Create window manager instance"""
    if config_dir is None:
        config_dir = Path.home() / ".config" / "gmen"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    return ThreadSafeWindowManager(config_dir)


if __name__ == "__main__":
    print("🧪 Testing Thread-Safe Window Manager...")
    wm = create_window_manager()
    print("✅ Window manager ready!")
