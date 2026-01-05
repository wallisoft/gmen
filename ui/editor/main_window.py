import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from ui.editor.list_manager import ListManager
from ui.editor.property_panel import PropertyPanel
from ui.editor.toolbar import Toolbar
from core.editor.menu_model import MenuItem


class EditorMainWindow:
    def __init__(self, db, menu_model, save_handler, change_tracker):
        self.db = db
        self.model = menu_model
        self.save_handler = save_handler
        self.change_tracker = change_tracker
        
        self.selected_item_id = None
        
        self.window = None
        self.list_manager = None
        self.property_panel = None
        self.toolbar = None
        
        self._init_ui()
    
    def _init_ui(self):
        self.window = Gtk.Window()
        self.window.set_title(f"GMen Editor - {self.model.name}")
        self.window.set_default_size(1200, 800)
        self.window.connect("destroy", self.on_window_destroy)
        
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window.add(main_vbox)
        
        self.toolbar = Toolbar(self.db)
        self.toolbar.on_save = self.on_save
        self.toolbar.on_reload = self.on_reload
        self.toolbar.on_debug = self.on_debug
        self.toolbar.on_export = self.on_export
        self.toolbar.on_import = self.on_import
        main_vbox.pack_start(self.toolbar.create_toolbar(), False, False, 0)
        
        content_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        content_hbox.set_margin_top(5)
        content_hbox.set_margin_bottom(5)
        content_hbox.set_margin_start(5)
        content_hbox.set_margin_end(5)
        main_vbox.pack_start(content_hbox, True, True, 0)
        
        self.list_manager = ListManager(self.db, self.model)
        self.list_manager.on_selection_changed = self.on_list_selection_changed
        self.list_manager.on_item_modified = self.on_item_modified
        
        self.property_panel = PropertyPanel(self.db)
        self.property_panel.on_property_changed = self.on_property_changed
        
        list_frame = self.list_manager.create_nav_panel()
        content_hbox.pack_start(list_frame, True, True, 0)
        
        property_frame = self.property_panel.create_panel()
        content_hbox.pack_start(property_frame, False, False, 0)
        
        self.window.show_all()
        self._load_css()
        
        print("✅ Editor UI initialized")
    
    def run(self):
        Gtk.main()
    
    def on_window_destroy(self, window):
        print("🪟 Window closing...")
        Gtk.main_quit()
    
    def on_list_selection_changed(self, item_id):
        self.selected_item_id = item_id
        
        if item_id:
            props = self.list_manager.get_item_properties(item_id)
            if props:
                temp_item = MenuItem(
                    id=item_id,
                    title=props.get('title', ''),
                    command=props.get('command', ''),
                    icon=props.get('icon', ''),
                    window_state=props.get('window_state')
                )
                
                selected_item = self.list_manager.get_selected_item()
                if selected_item and 'db_id' in selected_item:
                    temp_item.db_id = selected_item['db_id']
                
                self.property_panel.load_item(temp_item)
            else:
                self.property_panel.clear()
        else:
            self.property_panel.clear()
    
    def on_item_modified(self, item_id, field, value):
        print(f"📝 List: {item_id}.{field} = {value}")
        self.model.is_modified = True
        self.toolbar.set_unsaved_changes(True)
    
    def on_property_changed(self, item_id, field, value):
        print(f"⚙️ Property: {item_id}.{field} = {value}")
        
        if field == 'title':
            self.list_manager.update_item_title(item_id, value)
        else:
            update_data = {field: value}
            self.list_manager.update_item_properties(item_id, **update_data)
        
        self.model.is_modified = True
        self.toolbar.set_unsaved_changes(True)
    
    def on_save(self):
        print("💾 Save requested...")
        
        # Get flat items from list manager
        flat_items = self.list_manager.items
        
        try:
            menu = self.db.get_default_menu()
            if not menu:
                self.toolbar.show_message("No menu found")
                return
            
            menu_id = menu['id']
            
            # Save to database
            success = self._save_to_database(menu_id, flat_items)
            
            if success:
                self.toolbar.show_message(f"Saved {len(flat_items)} items")
                self.toolbar.set_unsaved_changes(False)
                self.model.is_modified = False
                
                # Refresh to get any new db_ids
                self.list_manager.rebuild_list()
                
                # Try to restore selection
                if self.selected_item_id:
                    GLib.idle_add(lambda: self.list_manager.listbox.select_row(
                        self._find_row_by_id(self.selected_item_id)
                    ))
                
                print("✅ Save successful!")
            else:
                self.toolbar.show_message("Save failed")
                
        except Exception as e:
            print(f"❌ Save failed: {e}")
            import traceback
            traceback.print_exc()
            self.toolbar.show_message(f"Save failed: {e}")

    def _save_to_database(self, menu_id, flat_items):
        """Save flat items to database, preserving existing IDs"""
        print(f"📊 Saving {len(flat_items)} items to menu {menu_id}")

        with self.db.transaction():
            # Convert flat → tree
            tree = self._flat_to_tree(flat_items)
            print(f"📊 Converted to tree with {len(tree)} root nodes")

            # Track which db_ids we're keeping
            kept_ids = set()
            sort_counter = [0]

            def save_nodes(nodes, parent_db_id):
                for node in nodes:
                    sort_counter[0] += 10

                    print(f"📋 Processing: '{node['title']}' (db_id: {node.get('db_id')}, parent: {parent_db_id})")

                    if node.get('db_id'):
                        # UPDATE existing
                        print(f"  Updating item {node['db_id']}...")
                        rows_affected = self.db.update_menu_item(
                            node['db_id'],
                            title=node['title'],
                            command=node['command'],
                            icon=node['icon'],
                            parent_id=parent_db_id,
                            sort_order=sort_counter[0],
                            is_active=True
                        )
                        print(f"  Update affected {rows_affected} rows")
                        kept_ids.add(node['db_id'])
                    else:
                        # INSERT new
                        print(f"  Inserting new item...")
                        new_db_id = self.db.add_menu_item(
                            menu_id=menu_id,
                            title=node['title'],
                            command=node['command'],
                            icon=node['icon'],
                            parent_id=parent_db_id,
                            sort_order=sort_counter[0]
                        )
                        node['db_id'] = new_db_id
                        kept_ids.add(new_db_id)
                        print(f"  New item ID: {new_db_id}")

                    # Save children
                    if node['children']:
                        save_nodes(node['children'], node.get('db_id'))

            save_nodes(tree, None)

            print(f"📊 Kept {len(kept_ids)} item IDs")

            # Check what's in the database
            all_items = self.db.get_menu_items(menu_id, active_only=False)
            print(f"📊 Database has {len(all_items)} total items")

            # Soft delete items not in our list
            deleted_count = 0
            for item in all_items:
                if item['id'] not in kept_ids and item['is_active']:
                    print(f"🗑️ Soft deleting item {item['id']}: {item['title']}")
                    rows = self.db.execute(
                        "UPDATE menu_items SET is_active = 0 WHERE id = ?",
                        (item['id'],)
                    )
                    print(f"  Delete affected {rows} rows")
                    deleted_count += 1

            if deleted_count > 0:
                print(f"🗑️ Soft deleted {deleted_count} old items")

            return True


    def _find_row_by_id(self, item_id):
        """Find a row by item_id"""
        for row in self.list_manager.listbox.get_children():
            if hasattr(row, 'item_id') and row.item_id == item_id:
                return row
        return None
    
    def _flat_to_tree(self, flat_items):
        """Convert flat list to tree structure"""
        tree = []
        stack = []  # (depth, node)
        
        for flat_item in flat_items:
            node = {
                'db_id': flat_item.get('db_id'),
                'title': flat_item['title'],
                'command': flat_item.get('command', ''),
                'icon': flat_item.get('icon', ''),
                'depth': flat_item['depth'],
                'children': []
            }
            
            # Find parent
            while stack and stack[-1][0] >= node['depth']:
                stack.pop()
            
            if stack:
                stack[-1][1]['children'].append(node)
            else:
                tree.append(node)
            
            stack.append((node['depth'], node))
        
        return tree
    
    def _insert_tree(self, menu_id, tree_nodes, parent_id, sort_counter=[0]):
        """Insert tree into database"""
        for node in tree_nodes:
            sort_counter[0] += 10
            
            # Always insert new (we soft-deleted all old ones)
            db_id = self.db.add_menu_item(
                menu_id=menu_id,
                title=node['title'],
                command=node['command'],
                icon=node['icon'],
                parent_id=parent_id,
                sort_order=sort_counter[0]
            )
            
            # Update the flat item with new db_id if it matches
            # (This is tricky without temp_id mapping...)
            
            if node['children']:
                self._insert_tree(menu_id, node['children'], db_id, sort_counter)
    
    def on_reload(self):
        print("🔄 Reload requested...")
        self.model.load_from_db(self.db)
        self.list_manager.rebuild_list()
        self.property_panel.clear()
        self.selected_item_id = None
        self.toolbar.set_unsaved_changes(False)
        self.toolbar.show_message("Reloaded from database")
    
    def on_debug(self):
        print("\n=== DEBUG ===")
        print(f"Model has changes: {self.model.is_modified}")
        print(f"Selected item: {self.selected_item_id}")
        print(f"List items: {len(self.list_manager.items)}")
        for i, item in enumerate(self.list_manager.items):
            print(f"  [{i}] depth={item['depth']}: {item['title']} (db_id: {item.get('db_id')})")
        print("=============")
        self.toolbar.show_message("Debug info printed")
    
    def on_export(self):
        print("📤 Export requested")
        self.toolbar.show_message("Export (stub)")
    
    def on_import(self):
        print("📥 Import requested")
        self.toolbar.show_message("Import (stub)")
    
    def _load_css(self):
        css = """
        .list-row:selected {
            background-color: #3584e4;
            color: white;
        }
        """
        try:
            provider = Gtk.CssProvider()
            provider.load_from_data(css.encode())
            from gi.repository import Gdk
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(),
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        except:
            pass
