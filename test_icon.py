#!/usr/bin/env python3
from pathlib import Path

def find_app_icon():
    icon_names = ['app_icon.icns', 'icon.icns', 'app_icon.png', 'icon.png']
    search_paths = ['.', 'assets', 'icons', 'resources']
    
    print("Looking for icons in this order:")
    for path in search_paths:
        for icon_name in icon_names:
            icon_path = Path(path) / icon_name
            print(f"  Checking: {icon_path}")
            if icon_path.exists():
                print(f"  ✅ Found: {icon_path}")
                return icon_path
            else:
                print(f"  ❌ Not found: {icon_path}")
    return None

if __name__ == '__main__':
    result = find_app_icon()
    print(f"\nSelected icon: {result}") 