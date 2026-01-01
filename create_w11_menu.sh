#!/bin/bash
# Create Windows 11-style menu for GMen on Ubuntu 24.04

DB_PATH="$HOME/.config/gmen/gmen.db"

sqlite3 "$DB_PATH" << 'EOF'
-- Clear existing data (be careful!)
DELETE FROM window_states;
DELETE FROM menu_items;
DELETE FROM menus;

-- Insert Windows 11-style menu
INSERT INTO menus (name, is_default) VALUES ('Windows 11 Style', 1);
SELECT last_insert_rowid() INTO @menu_id;

-- ===== POWER MENU (First item with submenu) =====
INSERT INTO menu_items (menu_id, title, icon, depth, parent_id, sort_order) VALUES
    (@menu_id, '⚡ Power', 'system-shutdown', 0, NULL, 1);
SELECT last_insert_rowid() INTO @power_id;

-- Power submenu items
INSERT INTO menu_items (menu_id, title, command, icon, depth, parent_id, sort_order) VALUES
    (@menu_id, '🔒 Lock Screen', 'xdg-screensaver lock', 'system-lock-screen', 1, @power_id, 1),
    (@menu_id, '🔄 Restart', 'systemctl reboot', 'system-reboot', 1, @power_id, 2),
    (@menu_id, '⏻ Shutdown', 'systemctl poweroff', 'system-shutdown', 1, @power_id, 3),
    (@menu_id, '💤 Suspend', 'systemctl suspend', 'system-suspend', 1, @power_id, 4),
    (@menu_id, '👤 Log Out', 'gnome-session-quit --logout', 'system-log-out', 1, @power_id, 5);

-- ===== SYSTEM TOOLS =====
INSERT INTO menu_items (menu_id, title, command, icon, depth, parent_id, sort_order) VALUES
    (@menu_id, '🛠️ System Tools', 'gnome-system-monitor', 'utilities-system-monitor', 0, NULL, 2);
SELECT last_insert_rowid() INTO @sys_tools_id;

INSERT INTO menu_items (menu_id, title, command, icon, depth, parent_id, sort_order) VALUES
    (@menu_id, '📊 System Monitor', 'gnome-system-monitor', 'utilities-system-monitor', 1, @sys_tools_id, 1),
    (@menu_id, '⚙️ Settings', 'gnome-control-center', 'preferences-system', 1, @sys_tools_id, 2),
    (@menu_id, '📦 Software', 'gnome-software', 'application-x-executable', 1, @sys_tools_id, 3),
    (@menu_id, '💿 Disks', 'gnome-disks', 'drive-harddisk', 1, @sys_tools_id, 4),
    (@menu_id, '🌐 Network', 'nm-connection-editor', 'network-wired', 1, @sys_tools_id, 5);

-- ===== OFFICE & PRODUCTIVITY =====
INSERT INTO menu_items (menu_id, title, icon, depth, parent_id, sort_order) VALUES
    (@menu_id, '📎 Productivity', 'x-office-document', 0, NULL, 3);
SELECT last_insert_rowid() INTO @office_id;

INSERT INTO menu_items (menu_id, title, command, icon, depth, parent_id, sort_order) VALUES
    (@menu_id, '📝 Text Editor', 'gedit', 'accessories-text-editor', 1, @office_id, 1),
    (@menu_id, '📊 Calculator', 'gnome-calculator', 'accessories-calculator', 1, @office_id, 2),
    (@menu_id, '🗓️ Calendar', 'gnome-calendar', 'x-office-calendar', 1, @office_id, 3),
    (@menu_id, '📅 Tasks', 'gnome-todo', 'x-office-calendar', 1, @office_id, 4),
    (@menu_id, '📋 Notes', 'gnome-todo', 'x-office-calendar', 1, @office_id, 5);

-- ===== INTERNET =====
INSERT INTO menu_items (menu_id, title, icon, depth, parent_id, sort_order) VALUES
    (@menu_id, '🌐 Internet', 'applications-internet', 0, NULL, 4);
SELECT last_insert_rowid() INTO @internet_id;

INSERT INTO menu_items (menu_id, title, command, icon, depth, parent_id, sort_order) VALUES
    (@menu_id, '🦊 Firefox', 'firefox', 'firefox', 1, @internet_id, 1),
    (@menu_id, '📧 Email', 'thunderbird', 'thunderbird', 1, @internet_id, 2),
    (@menu_id, '💬 Discord', 'discord', 'discord', 1, @internet_id, 3),
    (@menu_id, '📹 Zoom', 'zoom', 'zoom', 1, @internet_id, 4),
    (@menu_id, '🗄️ File Sharing', 'nautilus', 'folder-remote', 1, @internet_id, 5);

-- ===== DEVELOPMENT =====
INSERT INTO menu_items (menu_id, title, icon, depth, parent_id, sort_order) VALUES
    (@menu_id, '💻 Development', 'applications-development', 0, NULL, 5);
SELECT last_insert_rowid() INTO @dev_id;

INSERT INTO menu_items (menu_id, title, command, icon, depth, parent_id, sort_order) VALUES
    (@menu_id, '📝 VS Code', 'code', 'visual-studio-code', 1, @dev_id, 1),
    (@menu_id, '🐍 Python', 'gnome-terminal -e "python3"', 'application-x-python', 1, @dev_id, 2),
    (@menu_id, '📁 File Browser', 'nautilus', 'system-file-manager', 1, @dev_id, 3),
    (@menu_id, '🖥️ Terminal', 'gnome-terminal', 'utilities-terminal', 1, @dev_id, 4),
    (@menu_id, '🔧 Git GUI', 'gitg', 'git', 1, @dev_id, 5);

-- ===== MULTIMEDIA =====
INSERT INTO menu_items (menu_id, title, icon, depth, parent_id, sort_order) VALUES
    (@menu_id, '🎵 Multimedia', 'applications-multimedia', 0, NULL, 6);
SELECT last_insert_rowid() INTO @media_id;

INSERT INTO menu_items (menu_id, title, command, icon, depth, parent_id, sort_order) VALUES
    (@menu_id, '🎬 Videos', 'totem', 'totem', 1, @media_id, 1),
    (@menu_id, '🎵 Music', 'rhythmbox', 'rhythmbox', 1, @media_id, 2),
    (@menu_id, '🖼️ Photos', 'shotwell', 'shotwell', 1, @media_id, 3),
    (@menu_id, '🎮 Games', 'steam', 'steam', 1, @media_id, 4),
    (@menu_id, '📸 Screenshot', 'gnome-screenshot --interactive', 'applets-screenshooter', 1, @media_id, 5);

-- ===== UTILITIES (Quick access at bottom) =====
INSERT INTO menu_items (menu_id, title, command, icon, depth, parent_id, sort_order) VALUES
    (@menu_id, '🔍 Search Files', 'catfish', 'system-search', 0, NULL, 7),
    (@menu_id, '📋 Clipboard', 'gpaste-client ui', 'edit-paste', 0, NULL, 8),
    (@menu_id, '🎨 Color Picker', 'gcolor3', 'color-picker', 0, NULL, 9),
    (@menu_id, '📏 Screen Ruler', 'screenruler', 'measure', 0, NULL, 10);

-- Add window states for common apps (remember positions)
INSERT INTO window_states (menu_item_id, app_name, x, y, width, height, monitor, remember, is_active) VALUES
    -- Terminal: Open on monitor 1, left side
    ((SELECT id FROM menu_items WHERE command LIKE '%gnome-terminal%' LIMIT 1), 
     'gnome-terminal', 100, 100, 800, 600, 0, 1, 1),
    
    -- File Browser: Open on monitor 2
    ((SELECT id FROM menu_items WHERE command = 'nautilus' LIMIT 1),
     'nautilus', 100, 100, 1000, 700, 1, 1, 1),
    
    -- Firefox: Full screen on monitor 0
    ((SELECT id FROM menu_items WHERE command = 'firefox' LIMIT 1),
     'firefox', 0, 0, 1920, 1080, 0, 1, 1);

-- Verify the data
SELECT '=== WINDOWS 11 STYLE MENU CREATED ===' AS '';
SELECT 'Total items: ' || COUNT(*) FROM menu_items WHERE menu_id = @menu_id;

SELECT '';
SELECT '=== MENU STRUCTURE ===' AS '';
WITH RECURSIVE menu_tree AS (
    SELECT id, title, depth, parent_id, sort_order, 0 as level
    FROM menu_items 
    WHERE menu_id = @menu_id AND parent_id IS NULL
    
    UNION ALL
    
    SELECT mi.id, mi.title, mi.depth, mi.parent_id, mi.sort_order, mt.level + 1
    FROM menu_items mi
    JOIN menu_tree mt ON mi.parent_id = mt.id
    WHERE mi.menu_id = @menu_id
)
SELECT 
    CASE 
        WHEN level = 0 THEN '📁 ' || title
        WHEN level = 1 THEN '   ├── ' || title
        WHEN level = 2 THEN '   │   ├── ' || title
        ELSE '   │       ├── ' || title
    END AS menu_structure
FROM menu_tree
ORDER BY sort_order, level;

SELECT '';
SELECT '=== WINDOW STATES ===' AS '';
SELECT ws.id, mi.title, ws.app_name, ws.x, ws.y, ws.width, ws.height, ws.monitor
FROM window_states ws
JOIN menu_items mi ON ws.menu_item_id = mi.id
WHERE mi.menu_id = @menu_id;
EOF

echo "✅ Windows 11-style menu created!"
echo "📁 Database: $DB_PATH"
echo "🎯 Launch GMen to see the menu: ./gmen.py"
