#!/usr/bin/env python3
"""
Debug platform detection
"""

import os
import platform

print("=== System Info ===")
print(f"System: {platform.system()}")
print(f"Display: {os.environ.get('DISPLAY')}")
print(f"Wayland Display: {os.environ.get('WAYLAND_DISPLAY')}")
print(f"XDG Session Type: {os.environ.get('XDG_SESSION_TYPE')}")

# Try to import our platform module
try:
    from platforms import get_platform
    plat = get_platform()
    print(f"\n=== Platform Detection ===")
    print(f"Platform class: {plat.__class__.__name__}")
    print(f"Display server: {plat.display_server}")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
