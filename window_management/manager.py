"""
Main Window Manager - Orchestrates window management
"""

import time
import threading
import hashlib
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any

from platforms import get_platform
from storage.database import Database


class WindowManager:
    """Main window manager orchestrator"""
    
    def __init__(self, config_dir: Path, enable_remote: bool = False):
        self.config_dir = config_dir
        self.db = Database(config_dir)
        
        # Get platform-specific implementation
        self.platform = get_platform()
        
        # Track existing windows
        self.existing_windows = set()
        self._capture_existing_windows()
        
        # Remote capabilities (stub for now)
        self.remote_enabled = enable_remote
        
        print(f"🌍 Platform: {self.platform.name}")
        print(f"🖥️  Monitors: {len(self.platform.get_monitors())}")
        print(f"🌐 Remote: {'✅' if enable_remote else '❌'}")
    
    def _capture_existing_windows(self):
        """Capture existing windows at startup"""
        try:
            windows = self.platform.get_all_windows()
            for win in windows:
                window_key = f"{win.get('pid', 0)}:{win.get('title', '')[:30]}"
                self.existing_windows.add(window_key)
        except:
            pass
    
    def launch_with_state(self, command: str, 
                         window_state: Optional[Dict] = None) -> Tuple[int, str]:
        """Launch application with positioning"""
        
        app_name = command.split()[0].lower() if command else ""
        
        # Get saved state from database if not provided
        saved_state = None
        if not window_state:
            saved_state = self.db.fetch_one("""
                SELECT x, y, width, height, monitor
                FROM window_states 
                WHERE app_name = ? AND is_active = 1
                ORDER BY last_used DESC LIMIT 1
            """, (app_name,))
        
        # Use provided state or saved state
        effective_state = window_state or saved_state
        
        # Launch the app
        pid = self.platform.launch_process(command)
        
        # Start tracking for positioning
        if effective_state:
            threading.Thread(
                target=self._track_and_position_window,
                args=(pid, app_name, effective_state),
                daemon=True
            ).start()
        
        # Generate instance hash
        instance_hash = hashlib.md5(
            f"{app_name}_{pid}_{time.time()}".encode()
        ).hexdigest()[:16]
        
        return pid, instance_hash
    
    def _track_and_position_window(self, pid: int, app_name: str, state: Dict):
        """Background thread to track and position new window"""
        max_attempts = 20
        for attempt in range(max_attempts):
            try:
                windows = self.platform.get_all_windows()
                
                # Find new window with matching PID
                for win in windows:
                    if win.get('pid') == pid:
                        # Found our window!
                        x, y, width, height = self._process_window_state(state)
                        
                        # Apply position
                        success = self.platform.move_window(
                            win['id'], x, y, width, height
                        )
                        
                        if success:
                            # Save to database
                            self.save_window_state(
                                app_name,
                                x, y, width, height,
                                state.get('monitor', 0)
                            )
                        
                        return
                
                time.sleep(0.5)
            except Exception as e:
                print(f"⚠️  Window tracking error: {e}")
                time.sleep(1)
        
        print(f"😞 Could not track window for {app_name}")
    
    def _process_window_state(self, state: Dict) -> Tuple[int, int, int, int]:
        """Convert window state to absolute coordinates"""
        x = state.get('x', 100)
        y = state.get('y', 100)
        width = state.get('width', 800)
        height = state.get('height', 600)
        monitor_idx = state.get('monitor', 0)
        
        # Convert to global coordinates if monitor specified
        monitors = self.platform.get_monitors()
        if 0 <= monitor_idx < len(monitors):
            monitor = monitors[monitor_idx]
            x = monitor['x'] + x
            y = monitor['y'] + y
        
        return x, y, width, height
    
    def save_window_state(self, app_name: str, 
                         x: int, y: int, 
                         width: int, height: int, 
                         monitor: int = 0):
        """Save window state to database"""
        existing = self.db.fetch_one("""
            SELECT id FROM window_states 
            WHERE app_name = ? AND is_active = 1
        """, (app_name,))
        
        if existing:
            self.db.execute("""
                UPDATE window_states 
                SET x = ?, y = ?, width = ?, height = ?, monitor = ?,
                    last_used = CURRENT_TIMESTAMP
                WHERE app_name = ? AND is_active = 1
            """, (x, y, width, height, monitor, app_name))
        else:
            self.db.execute("""
                INSERT INTO window_states 
                (app_name, x, y, width, height, monitor, is_active, remember)
                VALUES (?, ?, ?, ?, ?, ?, 1, 1)
            """, (app_name, x, y, width, height, monitor))
        
        print(f"💾 Saved window state for {app_name}: ({x},{y}) {width}x{height}")
    
    def get_window_state(self, app_name: str) -> Optional[Dict]:
        """Get saved window state"""
        return self.db.fetch_one("""
            SELECT x, y, width, height, monitor
            FROM window_states 
            WHERE app_name = ? AND is_active = 1
            ORDER BY last_used DESC LIMIT 1
        """, (app_name,))
    
    def save_current_workspace(self, name: str) -> bool:
        """Save current window positions as workspace"""
        try:
            windows = self.platform.get_all_windows()
            
            # Save to database
            self.db.execute("""
                INSERT INTO workspaces (name, window_data)
                VALUES (?, ?)
            """, (name, str(windows)))  # Simplified for now
            
            print(f"💾 Workspace '{name}' saved with {len(windows)} windows")
            return True
        except Exception as e:
            print(f"❌ Failed to save workspace: {e}")
            return False
    
    def load_workspace(self, name: str) -> bool:
        """Load workspace (stub for now)"""
        try:
            workspace = self.db.fetch_one("""
                SELECT window_data FROM workspaces 
                WHERE name = ? ORDER BY created_at DESC LIMIT 1
            """, (name,))
            
            if workspace:
                print(f"📂 Loaded workspace '{name}'")
                return True
            return False
        except Exception as e:
            print(f"❌ Failed to load workspace: {e}")
            return False
    
    def cleanup(self):
        """Cleanup resources"""
        print("🧹 Window manager cleanup complete")
