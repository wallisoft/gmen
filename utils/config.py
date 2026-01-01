"""
Configuration Management with JSON
"""

import json
from pathlib import Path
from typing import Dict, Any


class ConfigManager:
    """Manages application configuration in JSON format"""
    
    def __init__(self, config_dir):
        """config_dir can be Path object or string"""
        self.config_dir = Path(config_dir) if isinstance(config_dir, str) else config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.config_file = self.config_dir / "config.json"
        self.settings = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or defaults"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Default configuration
        defaults = {
            "version": 1,
            "ui": {
                "theme": "default",
                "show_icons": True,
                "animation_speed": 1.0,
                "tray_icon": "view-grid-symbolic"
            },
            "window_manager": {
                "tracking_enabled": True,
                "auto_save_delay": 5,
                "enable_remote": False,
                "default_monitor": 0
            },
            "network": {
                "discovery_enabled": True,
                "default_transport": "ssh",
                "auto_connect": False,
                "known_hosts": []
            },
            "platform_overrides": {
                "linux_x11": {
                    "use_wmctrl": True,
                    "use_xdotool": True,
                    "clipboard_tool": "xclip"
                },
                "wayland": {
                    "use_wl_clipboard": True
                },
                "macos": {
                    "use_applescript": True
                },
                "windows": {
                    "use_powershell": True
                }
            },
            "workspaces": {
                "auto_save": False,
                "max_saved": 10
            }
        }
        
        self._save_config(defaults)
        return defaults
    
    def _save_config(self, config: Dict):
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation"""
        keys = key.split('.')
        value = self.settings
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """Set configuration value using dot notation"""
        keys = key.split('.')
        config = self.settings
        
        # Navigate to the right level
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value
        
        # Save to disk
        self._save_config(self.settings)
    
    def get_platform_config(self, platform_name: str) -> Dict:
        """Get platform-specific configuration"""
        return self.get(f"platform_overrides.{platform_name}", {})
    
    def save(self):
        """Explicitly save configuration"""
        self._save_config(self.settings)
