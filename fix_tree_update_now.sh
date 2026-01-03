#!/bin/bash
cd ~/gmen

echo "🔧 FIXING TREE UPDATE BUG"

# 1. FIRST: Make sure on_property_changed calls tree_manager for ALL fields that affect tree
echo "=== Updating on_property_changed to refresh tree ==="
sed -i "/def on_property_changed/,/self.mark_unsaved_changes()/ {
    # Add tree refresh for title changes
    /if field == 'title':/ {
        n
        n
        a \        # Force tree refresh for visual update
        a \        print(f'🔄 Forcing tree refresh for item {item_id}')
        a \        self.tree_manager.update_item_title(item_id, value)
    }
    
    # Also refresh for icon changes if tree shows icons
    /if field == 'icon':/ {
        n  
        n
        a \        # Tree might show icons - refresh if it does
        a \        self.tree_manager.refresh_item(item_id)
    }
}" ui/editor/main_window.py

# 2. ENSURE tree_manager.update_item_title actually updates the display
echo "=== Ensuring update_item_title forces GTK refresh ==="
sed -i "/def update_item_title/,/^    def/ {
    # After setting the value, force GTK to redraw
    /self.list_store.set_value(iter, 0, new_title)/a \
        \        # FORCE GTK TO REDRAW THIS ROW\
        \        path = self.list_store.get_path(iter)\
        \        self.treeview.queue_draw()\
        \        print(f'✅ Tree updated and queued redraw for item {item_id}')
}" ui/editor/tree_manager.py

# 3. ADD a refresh_item method if missing (for icon/other updates)
echo "=== Adding refresh_item method to TreeManager ==="
if ! grep -q "def refresh_item" ui/editor/tree_manager.py; then
    cat >> ui/editor/tree_manager.py << 'ADDON'

    def refresh_item(self, item_id):
        """Force refresh of an item in tree (for icon/other changes)"""
        print(f'🌳 TreeManager.refresh_item({item_id}) called')
        iter = self._get_iter_by_id(item_id)
        if iter:
            # Get current values
            title = self.list_store.get_value(iter, 0)
            # Just re-set the title to force refresh
            self.list_store.set_value(iter, 0, title)
            path = self.list_store.get_path(iter)
            self.treeview.queue_draw()
            return True
        return False
ADDON
fi

# 4. ADD debug to see what's happening
echo "=== Adding debug logging ==="
sed -i "s/def on_property_changed/    print(f'🎯 ON_PROPERTY_CHANGED: item={item_id}, field={field}, value={value}')\n    def on_property_changed/" ui/editor/main_window.py

sed -i "s/def update_item_title/    print(f'🌳 UPDATE_ITEM_TITLE: Searching for item {item_id} in tree')\n    def update_item_title/" ui/editor/tree_manager.py

# 5. CHECK if property_panel is calling on_changed correctly
echo "=== Ensuring property_panel triggers updates ==="
if grep -q "def on_field_changed" ui/editor/property_panel.py; then
    sed -i "s/def on_field_changed/    print(f'📝 PROPERTY_PANEL: Field {field} changed to {value} for item {self.current_item_id}')\n    def on_field_changed/" ui/editor/property_panel.py
    
    # Make sure it calls the callback
    sed -i "s/if self.current_item_id and self.on_changed:/    if self.current_item_id and self.on_changed:\n        print(f'📝 PROPERTY_PANEL: Calling on_changed callback...')/" ui/editor/property_panel.py
fi

echo ""
echo "✅ FIXES APPLIED!"
echo ""
echo "🚀 TEST NOW:"
echo "1. python3 gmen_editor.py"
echo "2. Add item"
echo "3. Change title"
echo "4. Tree SHOULD update immediately (not wait for save)"
echo ""
echo "Debug output will show:"
echo "📝 PROPERTY_PANEL: Field title changed..."
echo "🎯 ON_PROPERTY_CHANGED: item=-1, field=title..."
echo "🌳 UPDATE_ITEM_TITLE: Searching for item -1 in tree"
echo "✅ Tree updated and queued redraw..."
