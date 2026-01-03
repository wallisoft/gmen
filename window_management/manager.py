"""
Main Window Manager - Orchestrates window management
"""

import time
import threading
import hashlib
import subprocess
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
    
    def launch_with_state(self, command: str, item_id: int = None,
                         window_state: Optional[Dict] = None) -> Tuple[int, str]:
        """Launch application with positioning"""
        
        # Get saved state from database if item_id provided
        saved_state = None
        if item_id:
            # FIXED: Use correct column names from your database schema
            saved_state = self.db.fetch_one("""
                SELECT x, y, width, height, display, state
                FROM window_states 
                WHERE item_id = ?
                LIMIT 1
            """, (item_id,))
        
        # Use provided state or saved state
        effective_state = window_state or saved_state or {}
        
        # Launch the app
        pid = self._launch_command(command, effective_state)
        
        # Start tracking for positioning if needed
        if effective_state and self.platform.supports_window_management():
            threading.Thread(
                target=self._track_and_position_window,
                args=(pid, command, effective_state, item_id),
                daemon=True
            ).start()
        
        # Generate instance hash
        instance_hash = hashlib.md5(
            f"{command}_{pid}_{time.time()}".encode()
        ).hexdigest()[:16]
        
        # Save state if item_id provided
        if item_id and effective_state:
            self._save_window_state(item_id, effective_state, instance_hash)
        
        return pid, instance_hash
    
    def _launch_command(self, command: str, window_state: Optional[Dict] = None) -> int:
        """Launch a shell command with optional window placement"""
        
        # Build command with window placement if state exists
        full_cmd = command
        
        if window_state and 'x' in window_state and 'y' in window_state:
            # Add window placement for supported apps
            x = window_state.get('x', 100)
            y = window_state.get('y', 100)
            width = window_state.get('width', 800)
            height = window_state.get('height', 600)
            
            if "gnome-terminal" in command.lower():
                full_cmd = f"gnome-terminal --geometry={width}x{height}+{x}+{y}"
            elif "xterm" in command.lower():
                full_cmd = f"xterm -geometry {width}x{height}+{x}+{y}"
        
        print(f"🚀 Launching: {full_cmd}")
        
        # Launch process
        process = subprocess.Popen(
            full_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True
        )
        
        return process.pid
    
    def _track_and_position_window(self, pid: int, command: str, 
                                  state: Dict, item_id: Optional[int] = None):
        """Background thread to track and position new window"""
        app_name = command.split()[0] if command else "app"
        max_attempts = 20
        
        for attempt in range(max_attempts):
            try:
                windows = self.platform.get_all_windows()
                
                # Find new window with matching PID
                for win in windows:
                    if win.get('pid') == pid:
                        # Found our window!
                        x, y, width, height = self._process_window_state(state)
                        
                        # Apply position if platform supports it
                        if hasattr(self.platform, 'move_window'):
                            success = self.platform.move_window(
                                win['id'], x, y, width, height
                            )
                            
                            if success and item_id:
                                # Update database with actual position
                                self._save_window_state(
                                    item_id,
                                    {'x': x, 'y': y, 'width': width, 'height': height},
                                    f"tracked_{pid}"
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
        display = state.get('display', 0)
        
        # Convert to global coordinates if display specified
        if hasattr(self.platform, 'get_monitors'):
            monitors = self.platform.get_monitors()
            if 0 <= display < len(monitors):
                monitor = monitors[display]
                x = monitor.get('x', 0) + x
                y = monitor.get('y', 0) + y
        
        return x, y, width, height
    
    def _save_window_state(self, item_id: int, state: Dict, instance_id: str):
        """Save window state to database"""
        try:
            # Check if state already exists
            existing = self.db.fetch_one(
                "SELECT id FROM window_states WHERE item_id = ?",
                (item_id,)
            )
            
            if existing:
                # Update existing
                self.db.execute("""
                    UPDATE window_states 
                    SET x = ?, y = ?, width = ?, height = ?, 
                        display = ?, state = ?, instance_id = ?
                    WHERE item_id = ?
                """, (
                    state.get('x'), state.get('y'), 
                    state.get('width'), state.get('height'),
                    state.get('display', 0), state.get('state', ''),
                    instance_id, item_id
                ))
            else:
                # Insert new
                self.db.execute("""
                    INSERT INTO window_states 
                    (item_id, x, y, width, height, display, state, instance_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item_id, state.get('x'), state.get('y'),
                    state.get('width'), state.get('height'),
                    state.get('display', 0), state.get('state', ''),
                    instance_id
                ))
            
            print(f"💾 Saved window state for item {item_id}")
            
        except Exception as e:
            print(f"⚠️  Failed to save window state: {e}")
    
    def get_window_state(self, item_id: int) -> Optional[Dict]:
        """Get saved window state for an item"""
        return self.db.fetch_one("""
            SELECT x, y, width, height, display, state
            FROM window_states 
            WHERE item_id = ?
            LIMIT 1
        """, (item_id,))
    
    def save_current_workspace(self, name: str) -> bool:
        """Save current window positions as workspace"""
        try:
            if not hasattr(self.platform, 'get_all_windows'):
                print("⚠️  Platform doesn't support window listing")
                return False
                
            windows = self.platform.get_all_windows()
            
            # Save to database (you'll need a workspaces table)
            # self.db.execute("""
            #     INSERT INTO workspaces (name, window_data)
            #     VALUES (?, ?)
            # """, (name, str(windows)))
            
            print(f"💾 Workspace '{name}' would save {len(windows)} windows")
            return True
        except Exception as e:
            print(f"❌ Failed to save workspace: {e}")
            return False
    
    def load_workspace(self, name: str) -> bool:
        """Load workspace (stub for now)"""
        try:
            # workspace = self.db.fetch_one("""
            #     SELECT window_data FROM workspaces 
            #     WHERE name = ? ORDER BY created_at DESC LIMIT 1
            # """, (name,))
            
            # if workspace:
            #     print(f"📂 Loaded workspace '{name}'")
            #     return True
            print(f"📂 Would load workspace '{name}'")
            return False
        except Exception as e:
            print(f"❌ Failed to load workspace: {e}")
            return False
    
    def close(self):
        """Cleanup resources"""
        self.db.close()
        print("🧹 Window manager cleanup complete")
