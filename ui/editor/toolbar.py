"""
Editor toolbar
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class EditorToolbar:
    """Editor toolbar with actions"""
    
    def __init__(self):
        self.on_reload = None
        self.on_backup = None
        self.on_script_editor = None
        self.on_test = None
        self.on_quit = None
    
    def create_toolbar(self):
        """Create bottom toolbar"""
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        buttons = [
            ("🔄 Reload", self._on_reload),
            ("💾 Backup DB", self._on_backup),
            ("📜 Script Editor", self._on_script_editor),
            ("▶️ Test", self._on_test),
            ("🚪 Quit", self._on_quit),
        ]
        
        for label, callback in buttons:
            btn = Gtk.Button(label=label)
            btn.connect("clicked", callback)
            hbox.pack_start(btn, False, False, 0)
        
        return hbox
    
    def _on_reload(self, button):
        if self.on_reload:
            self.on_reload()
    
    def _on_backup(self, button):
        if self.on_backup:
            self.on_backup()
    
    def _on_script_editor(self, button):
        if self.on_script_editor:
            self.on_script_editor()
    
    def _on_test(self, button):
        if self.on_test:
            self.on_test()
    
    def _on_quit(self, button):
        if self.on_quit:
            self.on_quit()
