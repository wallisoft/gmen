#!/usr/bin/env python3
"""
GMen v4 - Modular Architecture with Distributed Capabilities
Database-First System Tray Launcher
"""

import sys
import gi
from pathlib import Path

# Add our modules to path
sys.path.insert(0, str(Path(__file__).parent))

gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, GLib

from storage.database import Database
from utils.config import ConfigManager
from utils.logging import setup_logging
from window_management.manager import WindowManager
from network.transport import NetworkManager
from ui.main_window import GMenApp


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GMen - Database-First Menu Launcher")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Dry run mode (don't execute commands)")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug output")
    parser.add_argument("--remote", action="store_true",
                       help="Enable remote capabilities")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(debug=args.debug)
    
    # Load configuration
    config_dir = Path.home() / ".config" / "gmen"
    config = ConfigManager(config_dir)
    
    # Initialize database
    db = Database(config_dir)
    
    # Initialize window management
    window_mgr = WindowManager(config_dir, enable_remote=args.remote)
    
    # Initialize network if requested
    network_mgr = None
    if args.remote:
        network_mgr = NetworkManager(config_dir)
        network_mgr.start()
    
    # Create and run application
    app = GMenApp(db, window_mgr, network_mgr, config, dry_run=args.dry_run)
    app.run()


if __name__ == "__main__":
    main()
