"""
Clean Database Module - Just what we need
"""

import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager


class Database:
    def __init__(self, db_path=None):
        if db_path is None:
            config_dir = os.path.expanduser("~/.config/gmen")
            os.makedirs(config_dir, exist_ok=True)
            db_path = os.path.join(config_dir, "gmen.db")
        
        self.db_path = db_path
        self._init_db()
    
    @contextmanager
    def transaction(self):
        """Context manager for transactions"""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _get_connection(self):
        """Get database connection with proper settings"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return dict-like rows
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def _init_db(self):
        """Initialize database schema"""
        with self.transaction() as conn:
            # Menus table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS menus (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    is_default BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Menu items table
            conn.execute("""
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
            
            # Item instances table - THE CORE TABLE
            conn.execute("""
                CREATE TABLE IF NOT EXISTS item_instances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL,
                    instance_name TEXT DEFAULT 'Instance 1',
                    
                    -- Content properties
                    command TEXT,
                    icon TEXT,
                    
                    -- Window properties
                    x INTEGER,
                    y INTEGER,
                    width INTEGER,
                    height INTEGER,
                    display INTEGER DEFAULT 0,
                    state TEXT DEFAULT 'normal',
                    enable_positioning BOOLEAN DEFAULT 1,
                    
                    -- Instance metadata
                    is_default BOOLEAN DEFAULT 1,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (item_id) REFERENCES menu_items(id) ON DELETE CASCADE
                )
            """)
            
            # Scripts table (for @script commands)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scripts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    content TEXT,
                    language TEXT DEFAULT 'bash',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Settings table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_menu_items_menu_id ON menu_items(menu_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_menu_items_parent_id ON menu_items(parent_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_item_instances_item_id ON item_instances(item_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_item_instances_is_default ON item_instances(is_default)")
            
            # Insert default menu if none exists
            cursor = conn.execute("SELECT COUNT(*) as count FROM menus")
            if cursor.fetchone()['count'] == 0:
                conn.execute(
                    "INSERT INTO menus (name, description, is_default) VALUES (?, ?, ?)",
                    ("Main Menu", "Default menu", 1)
                )
    
    # === MENU METHODS ===
    
    def get_all_menus(self):
        """Get all menus"""
        with self.transaction() as conn:
            cursor = conn.execute("SELECT * FROM menus ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]
    
    def get_menu(self, menu_id):
        """Get menu by ID"""
        with self.transaction() as conn:
            cursor = conn.execute("SELECT * FROM menus WHERE id = ?", (menu_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def create_menu(self, name, description=""):
        """Create new menu"""
        with self.transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO menus (name, description) VALUES (?, ?) RETURNING id",
                (name, description)
            )
            return cursor.fetchone()['id']
    
    def update_menu(self, menu_id, **kwargs):
        """Update menu"""
        if not kwargs:
            return False
        
        with self.transaction() as conn:
            set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            values = list(kwargs.values()) + [menu_id]
            
            conn.execute(
                f"UPDATE menus SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                values
            )
            return True
    
    def delete_menu(self, menu_id):
        """Delete menu (cascades to items and instances)"""
        with self.transaction() as conn:
            conn.execute("DELETE FROM menus WHERE id = ?", (menu_id,))
            return True
    
    # === MENU ITEM METHODS ===
    
    def get_menu_items(self, menu_id, active_only=True):
        """Get all items for a menu"""
        with self.transaction() as conn:
            query = """
                SELECT * FROM menu_items 
                WHERE menu_id = ? 
                {}
                ORDER BY sort_order, id
            """.format("AND is_active = 1" if active_only else "")
            
            cursor = conn.execute(query, (menu_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_item(self, item_id):
        """Get item by ID"""
        with self.transaction() as conn:
            cursor = conn.execute("SELECT * FROM menu_items WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def create_menu_item(self, menu_id, title, parent_id=None, depth=0):
        """Create new menu item"""
        with self.transaction() as conn:
            # Get max sort_order for this position
            cursor = conn.execute(
                "SELECT COALESCE(MAX(sort_order), 0) as max_order FROM menu_items WHERE menu_id = ?",
                (menu_id,)
            )
            max_order = cursor.fetchone()['max_order']
            
            cursor = conn.execute(
                """INSERT INTO menu_items (menu_id, title, parent_id, depth, sort_order) 
                   VALUES (?, ?, ?, ?, ?) RETURNING id""",
                (menu_id, title, parent_id, depth, max_order + 10)
            )
            return cursor.fetchone()['id']
    
    def update_menu_item(self, item_id, **kwargs):
        """Update menu item"""
        if not kwargs:
            return False
        
        with self.transaction() as conn:
            set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            values = list(kwargs.values()) + [item_id]
            
            conn.execute(
                f"UPDATE menu_items SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                values
            )
            return True
    
    def delete_menu_item(self, item_id):
        """Delete menu item (cascades to instances)"""
        with self.transaction() as conn:
            conn.execute("DELETE FROM menu_items WHERE id = ?", (item_id,))
            return True
    
    # === ITEM INSTANCE METHODS ===
    
    def get_item_instances(self, item_id, active_only=True):
        """Get all instances for an item"""
        with self.transaction() as conn:
            query = """
                SELECT * FROM item_instances 
                WHERE item_id = ? 
                {}
                ORDER BY is_default DESC, id
            """.format("AND is_active = 1" if active_only else "")
            
            cursor = conn.execute(query, (item_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_instance(self, instance_id):
        """Get instance by ID"""
        with self.transaction() as conn:
            cursor = conn.execute("SELECT * FROM item_instances WHERE id = ?", (instance_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def save_item_instance(self, instance_data):
        """Save or update item instance"""
        with self.transaction() as conn:
            instance_id = instance_data.get('id')
            
            if instance_id:
                # Update existing instance
                fields = ['command', 'icon', 'x', 'y', 'width', 'height', 
                         'display', 'state', 'enable_positioning', 'is_default']
                
                updates = []
                values = []
                for field in fields:
                    if field in instance_data:
                        updates.append(f"{field} = ?")
                        values.append(instance_data[field])
                
                if updates:
                    values.append(instance_id)
                    set_clause = ", ".join(updates)
                    conn.execute(
                        f"UPDATE item_instances SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        values
                    )
                
                return instance_id
            else:
                # Insert new instance
                cursor = conn.execute(
                    """INSERT INTO item_instances 
                       (item_id, command, icon, x, y, width, height, display, state, enable_positioning, is_default)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id""",
                    (
                        instance_data['item_id'],
                        instance_data.get('command', ''),
                        instance_data.get('icon', ''),
                        instance_data.get('x'),
                        instance_data.get('y'),
                        instance_data.get('width'),
                        instance_data.get('height'),
                        instance_data.get('display', 0),
                        instance_data.get('state', 'normal'),
                        instance_data.get('enable_positioning', True),
                        instance_data.get('is_default', True)
                    )
                )
                return cursor.fetchone()['id']
    
    def delete_instance(self, instance_id):
        """Delete instance"""
        with self.transaction() as conn:
            conn.execute("DELETE FROM item_instances WHERE id = ?", (instance_id,))
            return True
    
    # === SCRIPT METHODS ===
    
    def get_all_scripts(self):
        """Get all scripts"""
        with self.transaction() as conn:
            cursor = conn.execute("SELECT * FROM scripts ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]
    
    def get_script(self, script_id):
        """Get script by ID"""
        with self.transaction() as conn:
            cursor = conn.execute("SELECT * FROM scripts WHERE id = ?", (script_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def save_script(self, script_data):
        """Save or update script"""
        with self.transaction() as conn:
            script_id = script_data.get('id')
            
            if script_id:
                conn.execute(
                    """UPDATE scripts SET name = ?, content = ?, language = ?, 
                       updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
                    (script_data['name'], script_data.get('content'), 
                     script_data.get('language', 'bash'), script_id)
                )
                return script_id
            else:
                cursor = conn.execute(
                    """INSERT INTO scripts (name, content, language) 
                       VALUES (?, ?, ?) RETURNING id""",
                    (script_data['name'], script_data.get('content'), 
                     script_data.get('language', 'bash'))
                )
                return cursor.fetchone()['id']
    
    # === SETTINGS METHODS ===
    
    def get_setting(self, key, default=None):
        """Get setting value"""
        with self.transaction() as conn:
            cursor = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row['value'] if row else default
    
    def set_setting(self, key, value, description=None):
        """Set setting value"""
        with self.transaction() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO settings (key, value, description, updated_at)
                   VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
                (key, value, description)
            )
            return True
    
    # === UTILITY METHODS ===
    
    def execute(self, query, params=()):
        """Execute raw query"""
        with self.transaction() as conn:
            return conn.execute(query, params)
    
    def fetch_one(self, query, params=()):
        """Fetch single row"""
        with self.transaction() as conn:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def fetch_all(self, query, params=()):
        """Fetch all rows"""
        with self.transaction() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        """Close database connection"""
        pass  # Connections are managed per-transaction
