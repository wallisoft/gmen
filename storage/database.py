"""
Database Layer - SQLite with thread-local connections
Updated for item_instances schema
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
    """Thread-safe database abstraction with instance-based schema"""
    
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
    
    def _init_database(self):
        """Initialize database with new schema"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Create tables in correct order
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
                parent_id INTEGER,
                depth INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (menu_id) REFERENCES menus(id) ON DELETE CASCADE,
                FOREIGN KEY (parent_id) REFERENCES menu_items(id) ON DELETE CASCADE
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
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workspaces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # NEW: item_instances with runtime tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS item_instances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                workspace_id INTEGER,
                instance_name TEXT,
                
                -- Content properties
                command TEXT,
                script_id INTEGER,
                icon TEXT,
                
                -- Window properties
                x INTEGER,
                y INTEGER,
                width INTEGER,
                height INTEGER,
                display INTEGER DEFAULT 0,
                state TEXT DEFAULT 'normal',
                
                -- Script execution tracking
                instance_pid INTEGER,
                instance_status TEXT DEFAULT 'idle'
                       CHECK(instance_status IN ('idle', 'launching', 'running', 'failed', 'killed')),
                instance_output TEXT,
                instance_exit_code INTEGER,
                instance_started TIMESTAMP,
                instance_ended TIMESTAMP,
                
                -- Instance metadata
                is_default BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (item_id) REFERENCES menu_items(id) ON DELETE CASCADE,
                FOREIGN KEY (script_id) REFERENCES scripts(id) ON DELETE SET NULL,
                FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE SET NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                description TEXT,
                category TEXT DEFAULT 'general',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_menu_items_menu_id ON menu_items(menu_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_menu_items_parent_id ON menu_items(parent_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_instances_item_id ON item_instances(item_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_instances_workspace_id ON item_instances(workspace_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_instances_is_default ON item_instances(is_default)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_instances_instance_status ON item_instances(instance_status)")
        
        # Ensure default workspace exists
        cursor.execute("INSERT OR IGNORE INTO workspaces (id, name, description) VALUES (1, 'Default Workspace', 'Auto-created default workspace')")
        
        # Ensure default menu exists
        cursor.execute("INSERT OR IGNORE INTO menus (id, name, description, is_default) VALUES (1, 'Main Menu', 'Default application menu', 1)")
        
        conn.commit()
        
        # Check if migration needed
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='window_states'")
        if cursor.fetchone():
            self._migrate_old_schema(conn)
        
        print(f"✅ Database initialized at {self.db_path}")
    
    def _migrate_old_schema(self, conn):
        """Migrate from old schema to new item_instances schema"""
        cursor = conn.cursor()
        print("🔄 Migrating to new instance-based schema...")
        
        try:
            # 1. Create item_instances from menu_items commands/icons
            cursor.execute("""
                SELECT id, command, icon FROM menu_items 
                WHERE command IS NOT NULL OR icon IS NOT NULL
            """)
            
            for item_id, command, icon in cursor.fetchall():
                cursor.execute("""
                    INSERT INTO item_instances 
                    (item_id, workspace_id, instance_name, command, icon, is_default, instance_status)
                    VALUES (?, NULL, 'Default', ?, ?, 1, 'idle')
                """, (item_id, command, icon))
            
            # 2. Migrate window_states to item_instances
            cursor.execute("""
                SELECT ws.item_id, ws.instance_id, ws.x, ws.y, ws.width, ws.height, 
                       ws.display, ws.state, ws.script_status, ws.script_pid
                FROM window_states ws
                JOIN menu_items mi ON ws.item_id = mi.id
                WHERE ws.is_active = 1
            """)
            
            for row in cursor.fetchall():
                item_id, instance_id, x, y, width, height, display, state, script_status, script_pid = row
                
                # Find or create instance for this window state
                cursor.execute("""
                    SELECT id FROM item_instances 
                    WHERE item_id = ? AND instance_name = ?
                """, (item_id, instance_id or 'Default'))
                
                instance = cursor.fetchone()
                if instance:
                    # Update existing instance with window data
                    cursor.execute("""
                        UPDATE item_instances 
                        SET x = ?, y = ?, width = ?, height = ?, display = ?, state = ?,
                            instance_status = COALESCE(?, 'idle'), instance_pid = ?
                        WHERE id = ?
                    """, (x, y, width, height, display, state, script_status, script_pid, instance[0]))
                else:
                    # Create new instance with window data
                    cursor.execute("""
                        INSERT INTO item_instances 
                        (item_id, workspace_id, instance_name, x, y, width, height, 
                         display, state, instance_status, instance_pid, is_active)
                        VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """, (item_id, instance_id or 'Default', x, y, width, height, 
                          display, state, script_status or 'idle', script_pid))
            
            # 3. Clear old fields from menu_items
            cursor.execute("""
                UPDATE menu_items 
                SET command = NULL, icon = NULL
            """)
            
            # 4. Drop old table
            cursor.execute("DROP TABLE IF EXISTS window_states")
            
            conn.commit()
            print("✅ Migration complete!")
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Migration failed: {e}")
            raise
    
    def _update_schema(self):
        """Update schema if needed (future migrations)"""
        # Currently just the initial migration above
        pass
    
    # === MENU ITEMS (title/hierarchy only) ===
    
    def get_menu_items(self, menu_id, active_only=True):
        """Get menu items (without command/icon - those are in instances)"""
        cursor = self.get_cursor()
        
        if active_only:
            query = """
                SELECT id, title, parent_id, depth, sort_order, is_active
                FROM menu_items 
                WHERE menu_id = ? AND is_active = 1
                ORDER BY sort_order
            """
        else:
            query = """
                SELECT id, title, parent_id, depth, sort_order, is_active
                FROM menu_items 
                WHERE menu_id = ?
                ORDER BY sort_order
            """
        
        cursor.execute(query, (menu_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def create_menu_item(self, menu_id, title, parent_id=None, depth=0):
        """Create a new menu item (title only)"""
        cursor = self.get_cursor()
        cursor.execute("""
            INSERT INTO menu_items (menu_id, title, parent_id, depth, sort_order)
            VALUES (?, ?, ?, ?, 
                (SELECT COALESCE(MAX(sort_order), 0) + 10 
                 FROM menu_items WHERE menu_id = ?))
        """, (menu_id, title, parent_id, depth, menu_id))
        conn = self._get_connection()
        conn.commit()
        return cursor.lastrowid
    
    def update_menu_item(self, item_id, **kwargs):
        """Update menu item properties"""
        if not kwargs:
            return 0
        
        set_clauses = []
        params = []
        for key, value in kwargs.items():
            if key in ['title', 'parent_id', 'depth', 'sort_order', 'is_active']:
                set_clauses.append(f"{key} = ?")
                params.append(value)
        
        if not set_clauses:
            return 0
        
        params.append(item_id)
        query = f"""
            UPDATE menu_items 
            SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        
        return self.execute(query, tuple(params))
    
    def delete_menu_item(self, item_id):
        """Delete a menu item (cascades to instances)"""
        return self.execute("DELETE FROM menu_items WHERE id = ?", (item_id,))
    
    # === ITEM INSTANCES (complete instance definitions) ===
    
    def get_item_instances(self, item_id, workspace_id=None):
        """Get all instances for an item, optionally filtered by workspace"""
        cursor = self.get_cursor()
        
        if workspace_id:
            query = """
                SELECT id, item_id, workspace_id, instance_name,
                       command, script_id, icon,
                       x, y, width, height, display, state,
                       instance_pid, instance_status, instance_output,
                       instance_exit_code, instance_started, instance_ended,
                       is_default, is_active
                FROM item_instances 
                WHERE item_id = ? AND (workspace_id = ? OR workspace_id IS NULL)
                ORDER BY is_default DESC, id
            """
            cursor.execute(query, (item_id, workspace_id))
        else:
            query = """
                SELECT id, item_id, workspace_id, instance_name,
                       command, script_id, icon,
                       x, y, width, height, display, state,
                       instance_pid, instance_status, instance_output,
                       instance_exit_code, instance_started, instance_ended,
                       is_default, is_active
                FROM item_instances 
                WHERE item_id = ? 
                ORDER BY is_default DESC, id
            """
            cursor.execute(query, (item_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_default_instance(self, item_id):
        """Get the default instance for an item"""
        cursor = self.get_cursor()
        cursor.execute("""
            SELECT id, item_id, workspace_id, instance_name,
                   command, script_id, icon,
                   x, y, width, height, display, state,
                   instance_pid, instance_status,
                   is_default, is_active
            FROM item_instances 
            WHERE item_id = ? AND is_default = 1 AND is_active = 1
            LIMIT 1
        """, (item_id,))
        
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def save_item_instance(self, instance_data):
        """Save or update an item instance"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if 'id' in instance_data and instance_data['id']:
            # Update existing instance
            cursor.execute("""
                UPDATE item_instances 
                SET item_id = ?, workspace_id = ?, instance_name = ?,
                    command = ?, script_id = ?, icon = ?,
                    x = ?, y = ?, width = ?, height = ?, display = ?, state = ?,
                    instance_pid = ?, instance_status = ?, instance_output = ?,
                    instance_exit_code = ?, instance_started = ?, instance_ended = ?,
                    is_default = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                instance_data.get('item_id'),
                instance_data.get('workspace_id'),
                instance_data.get('instance_name'),
                instance_data.get('command'),
                instance_data.get('script_id'),
                instance_data.get('icon'),
                instance_data.get('x'),
                instance_data.get('y'),
                instance_data.get('width'),
                instance_data.get('height'),
                instance_data.get('display', 0),
                instance_data.get('state', 'normal'),
                instance_data.get('instance_pid'),
                instance_data.get('instance_status', 'idle'),
                instance_data.get('instance_output'),
                instance_data.get('instance_exit_code'),
                instance_data.get('instance_started'),
                instance_data.get('instance_ended'),
                instance_data.get('is_default', 0),
                instance_data.get('is_active', 1),
                instance_data['id']
            ))
            instance_id = instance_data['id']
        else:
            # Insert new instance
            cursor.execute("""
                INSERT INTO item_instances 
                (item_id, workspace_id, instance_name,
                 command, script_id, icon,
                 x, y, width, height, display, state,
                 instance_pid, instance_status, instance_output,
                 instance_exit_code, instance_started, instance_ended,
                 is_default, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                instance_data['item_id'],
                instance_data.get('workspace_id'),
                instance_data.get('instance_name'),
                instance_data.get('command'),
                instance_data.get('script_id'),
                instance_data.get('icon'),
                instance_data.get('x'),
                instance_data.get('y'),
                instance_data.get('width'),
                instance_data.get('height'),
                instance_data.get('display', 0),
                instance_data.get('state', 'normal'),
                instance_data.get('instance_pid'),
                instance_data.get('instance_status', 'idle'),
                instance_data.get('instance_output'),
                instance_data.get('instance_exit_code'),
                instance_data.get('instance_started'),
                instance_data.get('instance_ended'),
                instance_data.get('is_default', 0),
                instance_data.get('is_active', 1)
            ))
            instance_id = cursor.lastrowid
        
        conn.commit()
        return instance_id
    
    def delete_item_instance(self, instance_id):
        """Delete an item instance"""
        return self.execute("DELETE FROM item_instances WHERE id = ?", (instance_id,))
    
    def get_workspace_instances(self, workspace_id):
        """Get all instances for a workspace"""
        cursor = self.get_cursor()
        cursor.execute("""
            SELECT ii.*, mi.title as item_title
            FROM item_instances ii
            JOIN menu_items mi ON ii.item_id = mi.id
            WHERE ii.workspace_id = ? AND ii.is_active = 1
            ORDER BY mi.sort_order, ii.is_default DESC
        """, (workspace_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    # === RUNTIME METHODS (for gmen launcher) ===
    
    def update_instance_runtime(self, instance_id, **kwargs):
        """Update runtime fields of an instance (pid, status, etc.)"""
        allowed_fields = ['instance_pid', 'instance_status', 'instance_output',
                         'instance_exit_code', 'instance_started', 'instance_ended']
        
        set_clauses = []
        params = []
        for key, value in kwargs.items():
            if key in allowed_fields:
                set_clauses.append(f"{key} = ?")
                params.append(value)
        
        if not set_clauses:
            return 0
        
        params.append(instance_id)
        query = f"""
            UPDATE item_instances 
            SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        
        return self.execute(query, tuple(params))
    
    def get_running_instances(self):
        """Get all instances that are currently running"""
        cursor = self.get_cursor()
        cursor.execute("""
            SELECT ii.*, mi.title as item_title
            FROM item_instances ii
            JOIN menu_items mi ON ii.item_id = mi.id
            WHERE ii.instance_status = 'running' AND ii.instance_pid IS NOT NULL
            ORDER BY ii.instance_started
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    # === EXISTING METHODS (unchanged or slightly modified) ===
    
    def get_all_menus(self):
        cursor = self.get_cursor()
        cursor.execute("SELECT * FROM menus ORDER BY is_default DESC, name")
        return [dict(row) for row in cursor.fetchall()]
    
    def get_menu(self, name):
        cursor = self.get_cursor()
        cursor.execute("SELECT * FROM menus WHERE name = ?", (name,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def create_menu(self, name, description=""):
        cursor = self.get_cursor()
        cursor.execute("""
            INSERT INTO menus (name, description) 
            VALUES (?, ?)
        """, (name, description))
        conn = self._get_connection()
        conn.commit()
        return cursor.lastrowid
    
    def get_all_scripts(self):
        cursor = self.get_cursor()
        cursor.execute("SELECT * FROM scripts ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]
    
    def get_script(self, script_id):
        cursor = self.get_cursor()
        cursor.execute("SELECT * FROM scripts WHERE id = ?", (script_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def save_script(self, script_data):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if 'id' in script_data and script_data['id']:
            cursor.execute("""
                UPDATE scripts 
                SET name = ?, content = ?, language = ?, 
                    description = ?, tags = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                script_data['name'],
                script_data['content'],
                script_data.get('language', 'bash'),
                script_data.get('description'),
                script_data.get('tags'),
                script_data['id']
            ))
            script_id = script_data['id']
        else:
            cursor.execute("""
                INSERT INTO scripts (name, content, language, description, tags)
                VALUES (?, ?, ?, ?, ?)
            """, (
                script_data['name'],
                script_data['content'],
                script_data.get('language', 'bash'),
                script_data.get('description'),
                script_data.get('tags')
            ))
            script_id = cursor.lastrowid
        
        conn.commit()
        return script_id
    
    def fetch_one(self, query, params=()):
        """Execute a query and return first row as dict"""
        cursor = self.get_cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def fetch_all(self, query, params=()):
        """Execute a query and return all rows as list of dicts"""
        cursor = self.get_cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def backup(self, backup_path=None):
        """Create a backup of the database"""
        if backup_path is None:
            backup_path = self.config_dir / f"gmen.db.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        shutil.copy2(self.db_path, backup_path)
        print(f"💾 Backup created: {backup_path}")
        return backup_path

    def close(self):
        """Close database connection"""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

