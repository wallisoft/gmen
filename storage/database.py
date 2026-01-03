"""
Database Layer - SQLite with thread-local connections
"""

import sqlite3
import threading
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from contextlib import contextmanager


class Database:
    """Thread-safe database abstraction"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = config_dir / "gmen.db"
        self._local = threading.local()
        
        # Initialize database
        self._init_database()
        
        # Update schema if needed
        self._update_schema()
    
    def _get_connection(self):
        """Get thread-local connection"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30
            )
            self._local.conn.row_factory = sqlite3.Row
            # Enable foreign keys
            self._local.conn.execute("PRAGMA foreign_keys = ON")
        return self._local.conn
    
    def get_cursor(self):
        """Get cursor from current connection"""
        return self._get_connection().cursor()
    
    @contextmanager
    def transaction(self):
        """Context manager for transactions"""
        conn = self._get_connection()
        try:
            conn.execute("BEGIN")
            yield
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    def execute(self, query: str, params: tuple = (), commit: bool = True) -> int:
        """Execute a query and optionally commit"""
        conn = self._get_connection()
        cursor = conn.execute(query, params)
        if commit:
            conn.commit()
        return cursor.rowcount
    
    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """Execute many queries"""
        conn = self._get_connection()
        cursor = conn.executemany(query, params_list)
        conn.commit()
        return cursor.rowcount
    
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """Fetch a single row"""
        cursor = self._get_connection().execute(query, params)
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict]:
        """Fetch all rows"""
        cursor = self._get_connection().execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def _init_database(self):
        """Initialize database schema"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Core tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS menus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                is_default BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS menu_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                menu_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                command TEXT,
                script_id INTEGER,
                icon TEXT,
                category TEXT,
                tags TEXT,
                depth INTEGER DEFAULT 0,
                parent_id INTEGER,
                sort_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (menu_id) REFERENCES menus(id) ON DELETE CASCADE,
                FOREIGN KEY (parent_id) REFERENCES menu_items(id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS window_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                instance_id TEXT,
                x INTEGER,
                y INTEGER,
                width INTEGER,
                height INTEGER,
                display INTEGER DEFAULT 0,
                state TEXT DEFAULT '',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (item_id) REFERENCES menu_items(id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                content TEXT,
                language TEXT DEFAULT 'bash',
                description TEXT,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                description TEXT,
                category TEXT DEFAULT 'general',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Workspaces table (for future use)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workspaces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                window_data TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_menu_items_menu_id ON menu_items(menu_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_menu_items_parent_id ON menu_items(parent_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_menu_items_sort_order ON menu_items(sort_order)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_menu_items_is_active ON menu_items(is_active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_window_states_item_id ON window_states(item_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_window_states_is_active ON window_states(is_active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key)")
        
        # Insert default menu if none exists
        cursor.execute("SELECT COUNT(*) as count FROM menus")
        if cursor.fetchone()['count'] == 0:
            cursor.execute("""
                INSERT INTO menus (name, description, is_default)
                VALUES (?, ?, 1)
            """, ("Main Menu", "Default application menu"))
            print("📋 Created default 'Main Menu'")
        
        conn.commit()
        print(f"📊 Database initialized at {self.db_path}")
    
    def _update_schema(self):
        """Update database schema for existing installations"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Check and add missing columns to menus table
        cursor.execute("PRAGMA table_info(menus)")
        menu_columns = {col[1] for col in cursor.fetchall()}
        
        if 'description' not in menu_columns:
            cursor.execute("ALTER TABLE menus ADD COLUMN description TEXT")
        
        # Check and add missing columns to menu_items table
        cursor.execute("PRAGMA table_info(menu_items)")
        item_columns = {col[1] for col in cursor.fetchall()}
        
        missing_item_columns = {
            'category': 'TEXT',
            'tags': 'TEXT',
            'is_active': 'BOOLEAN DEFAULT 1',
            'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        }
        
        for col_name, col_type in missing_item_columns.items():
            if col_name not in item_columns:
                cursor.execute(f"ALTER TABLE menu_items ADD COLUMN {col_name} {col_type}")
        
        # Check and add missing columns to window_states table
        cursor.execute("PRAGMA table_info(window_states)")
        window_columns = {col[1] for col in cursor.fetchall()}
        
        missing_window_columns = {
            'instance_id': 'TEXT',
            'display': 'INTEGER DEFAULT 0',
            'state': 'TEXT DEFAULT ""',
            'is_active': 'BOOLEAN DEFAULT 1',
            'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        }
        
        for col_name, col_type in missing_window_columns.items():
            if col_name not in window_columns:
                cursor.execute(f"ALTER TABLE window_states ADD COLUMN {col_name} {col_type}")
        
        # Check and add missing columns to scripts table
        cursor.execute("PRAGMA table_info(scripts)")
        script_columns = {col[1] for col in cursor.fetchall()}
        
        if 'description' not in script_columns:
            cursor.execute("ALTER TABLE scripts ADD COLUMN description TEXT")
        if 'tags' not in script_columns:
            cursor.execute("ALTER TABLE scripts ADD COLUMN tags TEXT")
        
        conn.commit()
    
    # Menu management methods
    def get_menu(self, menu_name: str) -> Optional[Dict]:
        """Get menu by name"""
        return self.fetch_one("SELECT * FROM menus WHERE name = ?", (menu_name,))
    
    def get_default_menu(self) -> Optional[Dict]:
        """Get default menu"""
        return self.fetch_one("SELECT * FROM menus WHERE is_default = 1 LIMIT 1")
    
    def create_menu(self, name: str, description: str = "", is_default: bool = False) -> int:
        """Create a new menu"""
        if is_default:
            # Clear any existing default
            self.execute("UPDATE menus SET is_default = 0")
        
        self.execute("""
            INSERT INTO menus (name, description, is_default)
            VALUES (?, ?, ?)
        """, (name, description, 1 if is_default else 0))
        
        return self._get_connection().lastrowid
    
    # Menu item management methods
    def get_menu_items(self, menu_id: int, active_only: bool = True) -> List[Dict]:
        """Get all items for a menu"""
        query = """
            SELECT * FROM menu_items 
            WHERE menu_id = ?
        """
        params = [menu_id]
        
        if active_only:
            query += " AND is_active = 1"
        
        query += " ORDER BY sort_order, title"
        
        return self.fetch_all(query, tuple(params))
    
    def get_menu_item(self, item_id: int) -> Optional[Dict]:
        """Get a specific menu item"""
        return self.fetch_one("SELECT * FROM menu_items WHERE id = ?", (item_id,))
    
    def add_menu_item(self, menu_id: int, title: str, command: str = None,
                     script_id: int = None, icon: str = None, category: str = None,
                     parent_id: int = None, sort_order: int = 0) -> int:
        """Add a new menu item"""
        
        # Calculate depth
        depth = 0
        if parent_id:
            parent = self.get_menu_item(parent_id)
            if parent:
                depth = parent.get('depth', 0) + 1
        
        self.execute("""
            INSERT INTO menu_items 
            (menu_id, title, command, script_id, icon, category, 
             depth, parent_id, sort_order, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (menu_id, title, command, script_id, icon, category,
              depth, parent_id, sort_order))
        
        return self._get_connection().lastrowid
    
    def update_menu_item(self, item_id: int, **kwargs):
        """Update a menu item"""
        if not kwargs:
            return
        
        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        params = list(kwargs.values())
        params.append(item_id)
        
        query = f"UPDATE menu_items SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        self.execute(query, tuple(params))
    
    def delete_menu_item(self, item_id: int, cascade: bool = True):
        """Delete a menu item"""
        if cascade:
            # Delete child items first
            self.execute("DELETE FROM menu_items WHERE parent_id = ?", (item_id,))
        
        self.execute("DELETE FROM menu_items WHERE id = ?", (item_id,))
    
    # Window state management methods
    def get_window_state(self, item_id: int) -> Optional[Dict]:
        """Get window state for an item"""
        return self.fetch_one("""
            SELECT * FROM window_states 
            WHERE item_id = ? AND is_active = 1
            ORDER BY updated_at DESC LIMIT 1
        """, (item_id,))
    
    def save_window_state(self, item_id: int, instance_id: str, 
                         x: int, y: int, width: int, height: int,
                         display: int = 0, state: str = ""):
        """Save window state"""
        
        # Check if exists
        existing = self.fetch_one(
            "SELECT id FROM window_states WHERE item_id = ? AND is_active = 1",
            (item_id,)
        )
        
        if existing:
            self.execute("""
                UPDATE window_states 
                SET x = ?, y = ?, width = ?, height = ?, 
                    display = ?, state = ?, instance_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE item_id = ? AND is_active = 1
            """, (x, y, width, height, display, state, instance_id, item_id))
        else:
            self.execute("""
                INSERT INTO window_states 
                (item_id, instance_id, x, y, width, height, display, state, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (item_id, instance_id, x, y, width, height, display, state))
    
    # Script management methods
    def get_script(self, script_id: int) -> Optional[Dict]:
        """Get script by ID"""
        return self.fetch_one("SELECT * FROM scripts WHERE id = ?", (script_id,))
    
    def get_script_by_name(self, name: str) -> Optional[Dict]:
        """Get script by name"""
        return self.fetch_one("SELECT * FROM scripts WHERE name = ?", (name,))
    
    def get_all_scripts(self, include_content: bool = False) -> List[Dict]:
        """Get all scripts"""
        if include_content:
            return self.fetch_all("SELECT * FROM scripts ORDER BY name")
        else:
            return self.fetch_all("SELECT id, name, language, description FROM scripts ORDER BY name")
    
    def save_script(self, name: str, content: str, language: str = "bash",
                   description: str = "") -> int:
        """Save or update a script"""
        
        existing = self.get_script_by_name(name)
        
        if existing:
            self.execute("""
                UPDATE scripts 
                SET content = ?, language = ?, description = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE name = ?
            """, (content, language, description, name))
            return existing['id']
        else:
            self.execute("""
                INSERT INTO scripts (name, content, language, description)
                VALUES (?, ?, ?, ?)
            """, (name, content, language, description))
            return self._get_connection().lastrowid
    
    # Settings management methods
    def get_setting(self, key: str, default: str = "") -> str:
        """Get a setting value"""
        result = self.fetch_one("SELECT value FROM settings WHERE key = ?", (key,))
        return result['value'] if result else default
    
    def set_setting(self, key: str, value: str, description: str = "", category: str = "general"):
        """Set a setting value"""
        self.execute("""
            INSERT OR REPLACE INTO settings (key, value, description, category)
            VALUES (?, ?, ?, ?)
        """, (key, value, description, category))
    
    def get_all_settings(self, category: str = None) -> List[Dict]:
        """Get all settings, optionally filtered by category"""
        if category:
            return self.fetch_all("SELECT * FROM settings WHERE category = ? ORDER BY key", (category,))
        else:
            return self.fetch_all("SELECT * FROM settings ORDER BY category, key")
    
    # Utility methods
    def backup(self, backup_path: Path = None):
        """Create a backup of the database"""
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.config_dir / f"gmen_backup_{timestamp}.db"
        
        shutil.copy2(self.db_path, backup_path)
        print(f"📋 Database backed up to {backup_path}")
        return backup_path
    
    def vacuum(self):
        """Vacuum the database to optimize"""
        self.execute("VACUUM")
        print("🧹 Database vacuumed")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {}
        
        # Get counts
        tables = ['menus', 'menu_items', 'window_states', 'scripts', 'settings', 'workspaces']
        for table in tables:
            result = self.fetch_one(f"SELECT COUNT(*) as count FROM {table}")
            if result:
                stats[f"{table}_count"] = result['count']
        
        # Get database size
        if self.db_path.exists():
            stats['db_size'] = self.db_path.stat().st_size
        
        # Get last update times
        for table in ['menus', 'menu_items', 'scripts']:
            result = self.fetch_one(f"SELECT MAX(updated_at) as last_update FROM {table}")
            if result and result['last_update']:
                stats[f"{table}_last_update"] = result['last_update']
        
        return stats
    
    def set_mouse_menu_mapping(self, left_menu_id: int = 1, middle_menu_id: int = 1, right_menu_id: int = 1):
        """Set which menus are triggered by which mouse button"""
        self.set_setting('mouse_left_menu', str(left_menu_id), 'Menu ID for left click')
        self.set_setting('mouse_middle_menu', str(middle_menu_id), 'Menu ID for middle click')
        self.set_setting('mouse_right_menu', str(right_menu_id), 'Menu ID for right click')
        print(f"🖱️ Set mouse menu mapping: L={left_menu_id}, M={middle_menu_id}, R={right_menu_id}")

    def get_mouse_menu_mapping(self) -> Dict[str, int]:
        """Get mouse button to menu mapping"""
        return {
            'left': int(self.get_setting('mouse_left_menu', '1')),
            'middle': int(self.get_setting('mouse_middle_menu', '1')),
            'right': int(self.get_setting('mouse_right_menu', '1'))
        }

    def get_all_menus(self) -> List[Dict]:
        """Get all menus for selection dropdown"""
        return self.fetch_all("SELECT id, name, is_default FROM menus ORDER BY name")

    def close(self):
        """Close all connections"""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
