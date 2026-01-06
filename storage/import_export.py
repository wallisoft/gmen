"""
Menu Import/Export System
Supports JSON (now) and extensible for VML/YAML/XML later
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import uuid
from datetime import datetime


class ImportExportManager:
    """Manage menu import/export in multiple formats"""
    
    def __init__(self, db):
        self.db = db
        self.settings = self._load_settings()
    
    def _load_settings(self):
        """Load settings from database"""
        settings = {}
        try:
            rows = self.db.fetch_all("SELECT key, value FROM settings")
            for row in rows:
                settings[row['key']] = row['value']
        except Exception as e:
            print(f"⚠️ Could not load settings: {e}")
            settings = {}
        
        # Set defaults if not in DB
        if 'import_export_directory' not in settings:
            settings['import_export_directory'] = '~/.config/gmen/menus'
        if 'import_export_format' not in settings:
            settings['import_export_format'] = 'json'
        
        return settings
    
    def get_default_directory(self):
        """Get default directory from settings"""
        path = self.settings.get('import_export_directory', '~/.config/gmen/menus')
        full_path = os.path.expanduser(path)
        os.makedirs(full_path, exist_ok=True)
        return full_path
    
    # ===== EXPORT =====
    
    def export_menu(self, menu_id: int, format: str = 'json') -> Dict[str, Any]:
        """Export menu to specified format"""
        if format.lower() == 'json':
            return self._export_json(menu_id)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _export_json(self, menu_id: int) -> Dict[str, Any]:
        """Export menu to JSON structure"""
        # Get menu info
        menu = self.db.fetch_one(
            "SELECT id, name, description FROM menus WHERE id = ?",
            (menu_id,)
        )
        
        if not menu:
            raise ValueError(f"Menu {menu_id} not found")
        
        # Get all active items for this menu
        items = self.db.get_menu_items(menu_id, active_only=True)
        
        # Build tree structure
        tree = self._build_menu_tree(items)
        
        # Create export structure
        export_data = {
            "version": "1.0",
            "format": "gmen-json",
            "menu": {
                "id": menu['id'],
                "name": menu['name'],
                "description": menu.get('description', ''),
                "items": tree
            },
            "metadata": {
                "exported_at": self._current_timestamp(),
                "item_count": len(items),
                "exported_by": "GMen Editor"
            }
        }
        
        return export_data
    
    def _build_menu_tree(self, items: List[Dict]) -> List[Dict]:
        """Convert flat item list to hierarchical tree"""
        # Create lookup dict and root list
        items_by_id = {item['id']: item for item in items}
        children = {}
        
        # Build parent-child relationships
        for item in items:
            parent_id = item.get('parent_id')
            if parent_id:
                if parent_id not in children:
                    children[parent_id] = []
                children[parent_id].append(item)
        
        # Find roots (items with no parent or parent not in list)
        roots = []
        for item in items:
            parent_id = item.get('parent_id')
            if not parent_id or parent_id not in items_by_id:
                roots.append(item)
        
        # Recursively build tree
        def build_branch(parent_item):
            item_data = self._item_to_dict(parent_item)
            item_id = parent_item['id']
            
            if item_id in children:
                item_data['children'] = []
                for child in sorted(children[item_id], key=lambda x: x.get('sort_order', 0)):
                    item_data['children'].append(build_branch(child))
            
            return item_data
        
        # Build complete tree
        tree = []
        for root in sorted(roots, key=lambda x: x.get('sort_order', 0)):
            tree.append(build_branch(root))
        
        return tree
    
    def _item_to_dict(self, item: Dict) -> Dict:
        """Convert database item to export dict"""
        # Get window state if exists
        window_state = None
        if item.get('window_state'):
            try:
                window_state = json.loads(item['window_state'])
            except:
                window_state = None
        
        return {
            "title": item['title'],
            "command": item.get('command', ''),
            "icon": item.get('icon', ''),
            "sort_order": item.get('sort_order', 0),
            "window_state": window_state,
            "is_script": bool(item.get('command', '').startswith('@'))
        }
    
    def _current_timestamp(self) -> str:
        """Get current timestamp for metadata"""
        return datetime.now().isoformat()
    
    # ===== IMPORT =====
    
    def import_menu(self, import_data: Dict[str, Any], format: str = 'json', 
                    menu_name: Optional[str] = None) -> int:
        """Import menu from data"""
        if format.lower() == 'json':
            return self._import_json(import_data, menu_name)
        else:
            raise ValueError(f"Unsupported import format: {format}")
    
# In storage/import_export.py, update _import_json method:
    def _import_json(self, import_data: Dict[str, Any], menu_name: Optional[str] = None) -> int:
        """Import menu from JSON data"""
        # Validate format
        if 'menu' not in import_data:
            raise ValueError("Invalid JSON format: missing 'menu' key")
        
        menu_data = import_data['menu']
        
        # Use provided name or original name
        name = menu_name or menu_data.get('name', 'Imported Menu')
        
        # Create new menu - check what method exists
        try:
            # Try different method names
            menu_id = self.db.add_menu(name, menu_data.get('description', ''))
        except AttributeError:
            try:
                # Try execute with INSERT
                self.db.execute(
                    "INSERT INTO menus (name, description) VALUES (?, ?)",
                    (name, menu_data.get('description', ''))
                )
                result = self.db.fetch_one("SELECT last_insert_rowid() AS id")
                menu_id = result['id']
            except Exception as e:
                # Last resort
                conn = self.db._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO menus (name, description) VALUES (?, ?)",
                    (name, menu_data.get('description', ''))
                )
                conn.commit()
                menu_id = cursor.lastrowid
        
        # Import items
        items = menu_data.get('items', [])
        if items:
            self._import_items_tree(menu_id, items, parent_id=None)
        
        return menu_id
    
    def _import_items_tree(self, menu_id: int, items: List[Dict], 
                          parent_id: Optional[int], sort_offset: int = 0):
        """Recursively import items tree"""
        for i, item_data in enumerate(items):
            sort_order = (i + 1) * 10 + sort_offset
            
            # Extract window state
            window_state = item_data.get('window_state')
            window_state_str = json.dumps(window_state) if window_state else None
            
            # Create item
            item_id = self.db.add_menu_item(
                menu_id=menu_id,
                title=item_data['title'],
                command=item_data.get('command', ''),
                icon=item_data.get('icon', ''),
                parent_id=parent_id,
                sort_order=sort_order,
                window_state=window_state_str
            )
            
            # Recursively import children
            children = item_data.get('children', [])
            if children:
                self._import_items_tree(menu_id, children, item_id, sort_order * 100)
    
    # ===== FILE OPERATIONS =====
    
    def export_to_file(self, menu_id: int, filename: str, format: str = 'json'):
        """Export menu to file"""
        export_data = self.export_menu(menu_id, format)
        
        with open(filename, 'w', encoding='utf-8') as f:
            if format == 'json':
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            else:
                raise ValueError(f"Unsupported file format: {format}")
        
        return filename
    
    def import_from_file(self, filename: str, menu_name: Optional[str] = None) -> int:
        """Import menu from file"""
        # Detect format from extension
        ext = Path(filename).suffix.lower()
        if ext == '.json':
            format = 'json'
        else:
            # Try to auto-detect
            with open(filename, 'r', encoding='utf-8') as f:
                first_chars = f.read(100)
                f.seek(0)
                if first_chars.strip().startswith('{'):
                    format = 'json'
                else:
                    # Could be VML/Lua in the future
                    format = 'json'  # Default for now
        
        # Read and parse file
        with open(filename, 'r', encoding='utf-8') as f:
            if format == 'json':
                import_data = json.load(f)
            else:
                import_data = f.read()
        
        return self.import_menu(import_data, format, menu_name)
    
    # ===== FORMAT DETECTION =====
    
    def get_supported_formats(self) -> List[Dict[str, str]]:
        """Get list of supported import/export formats"""
        return [
            {"id": "json", "name": "JSON", "extension": ".json", "description": "JSON format"},
            # {"id": "vml", "name": "VML", "extension": ".vml", "description": "Visualised Markup Language (Lua)"},
            # {"id": "yaml", "name": "YAML", "extension": ".yaml", "description": "YAML format"},
        ]
    
    def format_info(self, format_id: str) -> Dict[str, str]:
        """Get info about a specific format"""
        formats = {f["id"]: f for f in self.get_supported_formats()}
        return formats.get(format_id, {"id": format_id, "name": format_id.upper(), "extension": f".{format_id}"})
    
    # ===== UTILITIES =====
    
    def ensure_menus_directory(self):
        """Ensure the menus directory exists"""
        menus_dir = self.get_default_directory()
        os.makedirs(menus_dir, exist_ok=True)
        return menus_dir
    
    def list_exported_menus(self) -> List[Dict]:
        """List all exported menu files"""
        menus_dir = self.get_default_directory()
        menu_files = []
        
        for ext in ['.json', '.vml', '.yaml', '.yml']:  # Future formats
            for file in Path(menus_dir).glob(f"*{ext}"):
                try:
                    # Try to read basic info without full parse
                    with open(file, 'r', encoding='utf-8') as f:
                        if ext == '.json':
                            data = json.load(f)
                            menu_name = data.get('menu', {}).get('name', file.stem)
                        else:
                            menu_name = file.stem
                    
                    menu_files.append({
                        'path': str(file),
                        'name': menu_name,
                        'size': file.stat().st_size,
                        'modified': file.stat().st_mtime,
                        'format': ext[1:]  # Remove dot
                    })
                except:
                    # Skip unreadable files
                    continue
        
        return sorted(menu_files, key=lambda x: x['modified'], reverse=True)
