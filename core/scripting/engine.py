#!/usr/bin/env python3
"""
Script Engine for GMen - Integrates Lua, Python, and Shell scripts
"""

import subprocess
import tempfile
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

from storage.database import Database
from .lua import LuaState


class ScriptEngine:
    """Executes scripts in various languages"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.db = Database(config_dir)
        self.script_dir = config_dir / "scripts"
        self.script_dir.mkdir(exist_ok=True)
        
        # Initialize Lua engine
        self.lua_engine = LuaState()
        
        # Set up GMen API for Lua
        self._setup_gmen_api()
    
    def _setup_gmen_api(self):
        """Setup GMen API for Lua scripts"""
        gmen_api = {
            'launch': self._gmen_launch,
            'notify': self._gmen_notify,
            'sleep': self._gmen_sleep,
            'run_script': self._gmen_run_script,
            'set_window': self._gmen_set_window,
            'get_window_state': self._gmen_get_window_state,
        }
        
        self.lua_engine.set_gmen_api(gmen_api)
    
    def execute_script(self, script_id: int, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a script by ID"""
        script = self.db.fetch_one("""
            SELECT name, content, language FROM scripts WHERE id = ?
        """, (script_id,))
        
        if not script:
            return {"success": False, "error": "Script not found"}
        
        print(f"📜 Executing script: {script['name']} ({script['language']})")
        
        # Execute based on language
        language = script['language'].lower()
        if language == 'lua':
            return self.execute_lua(script['content'], context or {})
        elif language == 'python':
            return self.execute_python(script['content'], context or {})
        elif language in ['bash', 'shell']:
            return self.execute_shell(script['content'], context or {})
        else:
            return {"success": False, "error": f"Unsupported language: {script['language']}"}
    
    def execute_lua(self, code: str, context: Dict) -> Dict[str, Any]:
        """Execute Lua script"""
        try:
            result = self.lua_engine.eval(code)
            return {
                "success": True,
                "output": str(result) if result is not None else "No return value",
                "result": result
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def execute_python(self, code: str, context: Dict) -> Dict[str, Any]:
        """Execute Python script"""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            # Execute
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Clean up
            os.unlink(temp_file)
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Script execution timeout (30s)"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def execute_shell(self, code: str, context: Dict) -> Dict[str, Any]:
        """Execute Shell script"""
        try:
            result = subprocess.run(
                ["bash", "-c", code],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Script execution timeout (30s)"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_script(self, script_id: int) -> Optional[Dict]:
        """Get script by ID"""
        return self.db.fetch_one("""
            SELECT id, name, content, language, description, created_at
            FROM scripts WHERE id = ?
        """, (script_id,))
    
    def list_scripts(self) -> List[Dict]:
        """List all scripts"""
        return self.db.fetch("""
            SELECT id, name, language, description, created_at
            FROM scripts 
            ORDER BY name
        """)
    
    def save_script(self, name: str, content: str, language: str = "lua", 
                   description: str = "") -> int:
        """Save or update a script"""
        existing = self.db.fetch_one("SELECT id FROM scripts WHERE name = ?", (name,))
        
        if existing:
            # Update existing
            self.db.execute("""
                UPDATE scripts 
                SET content = ?, language = ?, description = ?, 
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (content, language, description, existing['id']))
            return existing['id']
        else:
            # Insert new
            self.db.execute("""
                INSERT INTO scripts (name, content, language, description)
                VALUES (?, ?, ?, ?)
            """, (name, content, language, description))
            
            result = self.db.fetch_one("SELECT last_insert_rowid() AS id")
            return result['id']
    
    def delete_script(self, script_id: int) -> bool:
        """Delete a script"""
        self.db.execute("DELETE FROM scripts WHERE id = ?", (script_id,))
        return True
    
    # ===== GMEN API FUNCTIONS FOR LUA =====
    
    def _gmen_launch(self, command):
        """Launch application - to be integrated with WindowManager"""
        print(f"🚀 Launching: {command}")
        process = subprocess.Popen(command, shell=True)
        return process.pid
    
    def _gmen_notify(self, message):
        """Show notification"""
        print(f"📢 {message}")
        return True
    
    def _gmen_sleep(self, seconds):
        """Sleep for seconds"""
        import time
        time.sleep(seconds)
        return True
    
    def _gmen_run_script(self, script_name):
        """Run another script by name"""
        script = self.db.fetch_one("SELECT id FROM scripts WHERE name = ?", (script_name,))
        if script:
            return self.execute_script(script['id'], {})
        return {"success": False, "error": f"Script '{script_name}' not found"}
    
    def _gmen_set_window(self, pid, x, y, width, height):
        """Set window position - stub for now"""
        print(f"🪟 Setting window {pid} to ({x},{y}) {width}x{height}")
        return True
    
    def _gmen_get_window_state(self, app_name):
        """Get window state - stub for now"""
        return {'x': 100, 'y': 100, 'width': 800, 'height': 600, 'monitor': 0}
