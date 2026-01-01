#!/usr/bin/env python3
"""
GMen Database - Auto-create with proper schema
"""

import sqlite3
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

class GMenDB:
    """Simple database wrapper that auto-creates on startup"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None
        self._init_database()
    
    def _init_database(self):
        """Initialize or create database"""
        # Ensure config directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Connect to database (creates if doesn't exist)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        
        # Initialize schema
        self._create_schema()
        
        print(f"✅ Database ready: {self.db_path}")
    
    def _create_schema(self):
        """Create all required tables with proper schema"""
        # First, create scripts table (needed for foreign key)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS scripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                language TEXT DEFAULT 'lua',
                code TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create menus table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS menus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                is_default BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create menu_items table WITH script_id column
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS menu_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                menu_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                command TEXT,
                icon TEXT DEFAULT '',
                depth INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                parent_id INTEGER DEFAULT NULL,
                script_id INTEGER DEFAULT NULL,
                FOREIGN KEY (menu_id) REFERENCES menus(id),
                FOREIGN KEY (parent_id) REFERENCES menu_items(id),
                FOREIGN KEY (script_id) REFERENCES scripts(id)
            )
        """)
        
        # Check if script_id column exists (for migration from old schema)
        cursor = self.conn.execute("PRAGMA table_info(menu_items)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'script_id' not in columns:
            print("🔄 Adding script_id column to menu_items table...")
            # Add the column
            self.conn.execute("ALTER TABLE menu_items ADD COLUMN script_id INTEGER DEFAULT NULL")
            self.conn.execute("""
                CREATE TABLE menu_items_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    menu_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    command TEXT,
                    icon TEXT DEFAULT '',
                    depth INTEGER DEFAULT 0,
                    sort_order INTEGER DEFAULT 0,
                    parent_id INTEGER DEFAULT NULL,
                    script_id INTEGER DEFAULT NULL,
                    FOREIGN KEY (menu_id) REFERENCES menus(id),
                    FOREIGN KEY (parent_id) REFERENCES menu_items(id),
                    FOREIGN KEY (script_id) REFERENCES scripts(id)
                )
            """)
            self.conn.execute("""
                INSERT INTO menu_items_new 
                (id, menu_id, title, command, icon, depth, sort_order, parent_id, script_id)
                SELECT id, menu_id, title, command, icon, depth, sort_order, parent_id, NULL
                FROM menu_items
            """)
            self.conn.execute("DROP TABLE menu_items")
            self.conn.execute("ALTER TABLE menu_items_new RENAME TO menu_items")
        
        # Create other tables
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS window_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                menu_item_id INTEGER UNIQUE,
                app_name TEXT NOT NULL,
                x INTEGER DEFAULT 100,
                y INTEGER DEFAULT 100,
                width INTEGER DEFAULT 800,
                height INTEGER DEFAULT 600,
                monitor INTEGER DEFAULT 0,
                remember BOOLEAN DEFAULT 1,
                is_active BOOLEAN DEFAULT 1,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (menu_item_id) REFERENCES menu_items(id)
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS workspaces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS workspace_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id INTEGER NOT NULL,
                app_name TEXT NOT NULL,
                x INTEGER NOT NULL,
                y INTEGER NOT NULL,
                width INTEGER NOT NULL,
                height INTEGER NOT NULL,
                FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
            )
        """)
        
        self.conn.commit()
        
        # Create default menu if none exists
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM menus")
        if cursor.fetchone()['count'] == 0:
            self.conn.execute("""
                INSERT INTO menus (name, is_default) 
                VALUES ('Default Menu', 1)
            """)
            self.conn.commit()
            print("📋 Created default menu")
    
    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute SQL with parameters"""
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        self.conn.commit()
        return cursor
    
    def fetch(self, sql: str, params: tuple = ()) -> List[Dict]:
        """Fetch all rows as dictionaries"""
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def fetch_one(self, sql: str, params: tuple = ()) -> Optional[Dict]:
        """Fetch single row as dictionary"""
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


# Simple singleton
_db_instance = None

def get_database(config_dir: Path = None) -> GMenDB:
    """Get or create database instance - AUTO-CREATES IF MISSING"""
    global _db_instance
    
    if _db_instance is None:
        if config_dir is None:
            config_dir = Path.home() / ".config" / "gmen"
        
        db_path = config_dir / "gmen.db"
        
        print(f"📁 Database: {db_path}")
        
        # This will auto-create if doesn't exist
        _db_instance = GMenDB(db_path)
    
    return _db_instance
