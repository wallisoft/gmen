"""
Database Layer - SQLite with thread-local connections
"""

import sqlite3
import threading
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
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
    
    def _get_connection(self):
        """Get thread-local connection"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False
            )
            self._local.conn.row_factory = sqlite3.Row
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
    
    def begin(self):
        """Start a transaction"""
        self._get_connection().execute("BEGIN")
    
    def commit(self):
        """Commit current transaction"""
        self._get_connection().commit()
    
    def rollback(self):
        """Rollback current transaction"""
        self._get_connection().rollback()
    
    def _init_database(self):
        """Initialize database schema"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Core tables (same as your existing schema)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS menus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
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
                depth INTEGER DEFAULT 0,
                parent_id INTEGER,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (menu_id) REFERENCES menus(id) ON DELETE CASCADE,
                FOREIGN KEY (parent_id) REFERENCES menu_items(id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                language TEXT DEFAULT 'lua',
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS window_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                menu_item_id INTEGER,
                app_name TEXT NOT NULL,
                x INTEGER,
                y INTEGER,
                width INTEGER,
                height INTEGER,
                monitor INTEGER DEFAULT 0,
                remember BOOLEAN DEFAULT 1,
                is_active BOOLEAN DEFAULT 1,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (menu_item_id) REFERENCES menu_items(id) ON DELETE SET NULL
            )
        """)
        
        # NEW: Remote hosts for distributed mode
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS remote_hosts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hostname TEXT UNIQUE NOT NULL,
                display_name TEXT,
                platform TEXT,
                capabilities TEXT,
                ssh_key TEXT,
                last_seen TIMESTAMP,
                is_online BOOLEAN DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workspaces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                window_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Ensure default menu exists
        cursor.execute("SELECT COUNT(*) as count FROM menus")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO menus (name, is_default) 
                VALUES ('Default Menu', 1)
            """)
        
        conn.commit()
    
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """Fetch a single row"""
        conn = self._get_connection()
        cursor = conn.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def fetch(self, query: str, params: tuple = ()) -> List[Dict]:
        """Fetch all rows"""
        conn = self._get_connection()
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def backup(self) -> Path:
        """Create a database backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.config_dir / f"gmen_backup_{timestamp}.db"
        shutil.copy2(self.db_path, backup_path)
        return backup_path
    
    def close(self):
        """Close all connections"""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
