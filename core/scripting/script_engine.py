#!/usr/bin/env python3
"""
GMen Script Engine - Lua interpreter integration
"""

import os
import subprocess
import threading
from pathlib import Path
from typing import Optional, Dict, Any

from database import get_database

class ScriptEngine:
    """Script execution engine with Lua support"""
    
    def __init__(self, db):
        self.db = db
        self.lua_engine = None
        
        # Try to load Lua interpreter
        try:
            from lua import LuaState
            self.lua_engine = LuaState()
            print("✅ LuaPure interpreter loaded")
        except ImportError as e:
            print(f"⚠️  LuaPure not available: {e}")
            self.lua_engine = None
    
    def execute_script(self, script_name: str) -> Any:
        """Execute a script by name"""
        script = self.db.fetch_one("""
            SELECT name, language, code, description
            FROM scripts 
            WHERE name = ?
        """, (script_name,))
        
        if not script:
            raise ValueError(f"Script not found: {script_name}")
        
        print(f"📜 Executing script: {script['name']}")
        print(f"   Language: {script['language']}")
        print(f"   Description: {script['description']}")
        
        if script['language'].lower() == 'lua':
            return self.execute_lua(script['code'])
        elif script['language'].lower() == 'python':
            return self.execute_python(script['code'])
        elif script['language'].lower() == 'shell':
            return self.execute_shell(script['code'])
        else:
            raise ValueError(f"Unsupported language: {script['language']}")
    
    def execute_lua(self, code: str) -> Any:
        """Execute Lua code"""
        if not self.lua_engine:
            raise RuntimeError("Lua interpreter not available")
        
        try:
            result = self.lua_engine.eval(code)
            print(f"✅ Lua script executed successfully")
            return result
        except Exception as e:
            print(f"❌ Lua execution error: {e}")
            raise
    
    def execute_python(self, code: str) -> Any:
        """Execute Python code"""
        try:
            # Create a safe execution environment
            local_vars = {}
            global_vars = {
                '__builtins__': {
                    'print': print,
                    'len': len,
                    'str': str,
                    'int': int,
                    'float': float,
                    'list': list,
                    'dict': dict,
                    'range': range,
                }
            }
            
            exec(code, global_vars, local_vars)
            
            # Check for main function
            if 'main' in local_vars and callable(local_vars['main']):
                result = local_vars['main']()
            else:
                result = None
            
            print(f"✅ Python script executed successfully")
            return result
        except Exception as e:
            print(f"❌ Python execution error: {e}")
            raise
    
    def execute_shell(self, code: str) -> Any:
        """Execute shell script"""
        try:
            result = subprocess.run(
                code,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            print(f"✅ Shell script executed successfully")
            return {
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        except Exception as e:
            print(f"❌ Shell execution error: {e}")
            raise
    
    def get_or_create_script(self, name: str, code: str, language: str = 'lua', description: str = '') -> int:
        """Get existing script ID or create new"""
        existing = self.db.fetch_one("SELECT id FROM scripts WHERE name = ?", (name,))
        
        if existing:
            # Update existing
            self.db.execute("""
                UPDATE scripts 
                SET code = ?, language = ?, description = ?, updated_at = CURRENT_TIMESTAMP
                WHERE name = ?
            """, (code, language, description, name))
            return existing['id']
        else:
            # Create new
            self.db.execute("""
                INSERT INTO scripts (name, language, code, description)
                VALUES (?, ?, ?, ?)
            """, (name, language, code, description))
            result = self.db.fetch_one("SELECT last_insert_rowid() AS id")
            return result['id']
    
    def list_scripts(self) -> list:
        """List all available scripts"""
        return self.db.fetch("""
            SELECT id, name, language, description, 
                   created_at, updated_at
            FROM scripts 
            ORDER BY name
        """)
    
    def delete_script(self, script_name: str) -> bool:
        """Delete a script"""
        try:
            self.db.execute("DELETE FROM scripts WHERE name = ?", (script_name,))
            return True
        except Exception as e:
            print(f"❌ Failed to delete script: {e}")
            return False
    
    def get_script(self, script_name: str) -> Optional[Dict]:
        """Get script details by name"""
        return self.db.fetch_one("""
            SELECT id, name, language, code, description,
                   created_at, updated_at
            FROM scripts 
            WHERE name = ?
        """, (script_name,))


# Test the script engine
if __name__ == "__main__":
    print("🧪 Testing Script Engine...")
    
    db = get_database()
    engine = ScriptEngine(db)
    
    # Test Lua execution
    lua_code = """
function main()
    print("Hello from Lua!")
    return 42
end
"""
    
    try:
        script_id = engine.get_or_create_script("test_lua", lua_code, "lua", "Test Lua script")
        print(f"Created script with ID: {script_id}")
        
        result = engine.execute_script("test_lua")
        print(f"Script result: {result}")
    except Exception as e:
        print(f"Test failed: {e}")
    
    print("\n✅ Script engine ready!")
