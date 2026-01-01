#!/usr/bin/env python3
"""
Migrate existing menu items to scripting system
"""

from database import get_database

def migrate_to_scripts():
    """Migrate existing complex commands to scripts"""
    db = get_database()
    
    print("🔄 Migrating to scripting system...")
    
    # Find menu items with complex commands (multiple commands)
    items = db.fetch("""
        SELECT id, title, command 
        FROM menu_items 
        WHERE command LIKE '%;%' OR command LIKE '%&&%' OR command LIKE '%||%'
    """)
    
    migrated_count = 0
    
    for item in items:
        command = item['command']
        title = item['title']
        
        # Convert to Lua script
        lua_script = f"""-- {title}
function main()
    -- Converted from: {command}
    {convert_command_to_lua(command)}
end

return main"""
        
        # Create script
        script_name = f"{title.lower().replace(' ', '_')}_{item['id']}"
        
        db.execute("""
            INSERT OR IGNORE INTO scripts (name, language, code, description)
            VALUES (?, 'lua', ?, ?)
        """, (script_name, lua_script, f"Converted from: {command}"))
        
        # Update menu item to use script
        script_id = db.fetch_one("SELECT id FROM scripts WHERE name = ?", (script_name,))['id']
        
        db.execute("""
            UPDATE menu_items 
            SET script_id = ?, command = ''
            WHERE id = ?
        """, (script_id, item['id']))
        
        migrated_count += 1
        print(f"  ✓ Migrated: {title}")
    
    print(f"✅ Migration complete: {migrated_count} items migrated to scripts")


def convert_command_to_lua(command):
    """Convert shell command to Lua"""
    lines = []
    
    # Split by ; && ||
    import re
    
    # Simple conversion
    commands = re.split(r'[;|&]+', command)
    
    for cmd in commands:
        cmd = cmd.strip()
        if cmd:
            lines.append(f'    gmen.launch("{cmd}")')
    
    return '\n'.join(lines)


if __name__ == "__main__":
    migrate_to_scripts()
