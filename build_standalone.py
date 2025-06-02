#!/usr/bin/env python3
"""
Build script to create a standalone macOS Application Bundle of the YouTube Comment Explorer
"""

import os
import sys
import subprocess
import shutil
import json
import zipfile
from pathlib import Path

def create_icns_from_png(png_path, icns_path):
    """Create .icns file from PNG source using macOS iconutil"""
    if not Path(png_path).exists():
        print(f"❌ Source PNG not found: {png_path}")
        return False
    
    # Create iconset directory
    iconset_dir = Path("icon.iconset")
    if iconset_dir.exists():
        shutil.rmtree(iconset_dir)
    iconset_dir.mkdir()
    
    # Define required icon sizes
    sizes = [
        (16, "icon_16x16.png"),
        (32, "icon_16x16@2x.png"),
        (32, "icon_32x32.png"), 
        (64, "icon_32x32@2x.png"),
        (128, "icon_128x128.png"),
        (256, "icon_128x128@2x.png"),
        (256, "icon_256x256.png"),
        (512, "icon_256x256@2x.png"),
        (512, "icon_512x512.png"),
        (1024, "icon_512x512@2x.png")
    ]
    
    try:
        # Use sips (Scriptable Image Processing System) to resize
        for size, filename in sizes:
            output_path = iconset_dir / filename
            cmd = [
                'sips', '-z', str(size), str(size), 
                str(png_path), '--out', str(output_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Failed to create {filename}: {result.stderr}")
                return False
        
        # Create .icns file using iconutil
        cmd = ['iconutil', '-c', 'icns', str(iconset_dir), '-o', str(icns_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Cleanup
        shutil.rmtree(iconset_dir)
        
        if result.returncode == 0:
            print(f"✅ Created icon: {icns_path}")
            return True
        else:
            print(f"❌ Failed to create .icns: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating icon: {e}")
        if iconset_dir.exists():
            shutil.rmtree(iconset_dir)
        return False

def create_info_plist(app_name, bundle_id, executable_name, version="1.0.0", has_icon=False):
    """Create Info.plist for the macOS app bundle"""
    icon_section = ""
    if has_icon:
        icon_section = """    <key>CFBundleIconFile</key>
    <string>app_icon</string>"""
    
    plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleDisplayName</key>
    <string>{app_name}</string>
    <key>CFBundleExecutable</key>
    <string>{executable_name}</string>
    <key>CFBundleIdentifier</key>
    <string>{bundle_id}</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>{app_name}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>{version}</string>
    <key>CFBundleVersion</key>
    <string>{version}</string>{icon_section}
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSUIElement</key>
    <false/>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
</dict>
</plist>'''
    return plist_content

def find_app_icon():
    """Look for app icon in common locations"""
    # Prioritize .icns files for macOS, then fall back to .png
    icon_names = ['app_icon.icns', 'icon.icns', 'app_icon.png', 'icon.png']
    search_paths = ['.', 'assets', 'icons', 'resources']
    
    for path in search_paths:
        for icon_name in icon_names:
            icon_path = Path(path) / icon_name
            if icon_path.exists():
                return icon_path
    return None

def build_app_bundle():
    """Build macOS Application Bundle using PyInstaller"""
    
    app_name = "Medical Medium Comment Explorer"
    bundle_id = "com.medicalmedium.commentexplorer"
    executable_name = "MMCommentExplorer"
    
    # Look for app icon
    icon_source = find_app_icon()
    has_icon = False
    icon_args = []
    
    if icon_source:
        print(f"📱 Found icon source: {icon_source}")
        
        if icon_source.suffix.lower() == '.png':
            # Convert PNG to .icns
            icns_path = Path('app_icon.icns')
            try:
                if create_icns_from_png(icon_source, icns_path):
                    icon_args = ['--icon', str(icns_path)]
                    has_icon = True
                else:
                    print("⚠️  Icon conversion failed - PyInstaller requires .icns format on macOS")
                    print("⚠️  Continuing build without custom icon")
                    icon_args = []
                    has_icon = False
            except Exception as e:
                print(f"⚠️  Icon processing error: {e}")
                print("⚠️  Continuing build without custom icon")
                icon_args = []
                has_icon = False
        elif icon_source.suffix.lower() == '.icns':
            # Use existing .icns file
            icon_args = ['--icon', str(icon_source)]
            has_icon = True
            print(f"✅ Using existing .icns file: {icon_source}")
    else:
        print("💡 No icon found. To add an icon:")
        print("   1. Create a 1024x1024 PNG file named 'app_icon.png'")
        print("   2. Place it in the project root directory")
        print("   3. Run this build script again")
    
    # Read the .env file to embed API key in the build
    env_vars = {}
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f.read().strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")
        print(f"✅ Found {len(env_vars)} environment variables in .env file")
    else:
        print("❌ Warning: .env file not found - API key will not be embedded")
    
    # Create a launcher script that starts the Flask server and opens browser
    launcher_content = f'''
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Add the bundle directory to Python path
if getattr(sys, 'frozen', False):
    bundle_dir = Path(sys._MEIPASS)
    os.chdir(bundle_dir)

# Embed environment variables directly in the executable
EMBEDDED_ENV_VARS = {repr(env_vars)}

def setup_environment():
    """Set up environment variables from embedded data"""
    for key, value in EMBEDDED_ENV_VARS.items():
        os.environ[key] = value
        if key == 'YOUTUBE_API_KEY':
            print(f"✅ Embedded API key loaded (length: {{len(value)}} chars)")

def start_server():
    """Start the Flask server"""
    try:
    import webapp
    import logging
    
    # Suppress Flask development server warnings
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
        print("🚀 Starting Flask server...")
        webapp.app.run(debug=False, host='127.0.0.1', port=9191, use_reloader=False, threaded=True)
    except Exception as e:
        print(f"❌ Server error: {{e}}")
        import traceback
        traceback.print_exc()

def open_browser():
    """Open browser after a short delay"""
    try:
        print("⏳ Waiting for server to start...")
        time.sleep(3)
        print("🌐 Opening browser...")
    webbrowser.open('http://127.0.0.1:9191')
        print("✅ Browser opened")
    except Exception as e:
        print(f"⚠️  Browser opening failed: {{e}}")

if __name__ == '__main__':
    print("Starting Medical Medium YouTube Comment Explorer...")
    print("Server will start on http://127.0.0.1:9191")
    
    try:
    # Set up embedded environment variables
    setup_environment()
    
        # Start server in background thread (NOT daemon so it keeps app alive)
        print("🔧 Starting server thread...")
        server_thread = threading.Thread(target=start_server, daemon=False)
    server_thread.start()
    
        # Open browser in separate thread
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
        print("✅ App started successfully!")
        print("💡 Close this app by closing the browser or pressing Ctrl+C")
        
        # Keep main thread alive and wait for server thread
        server_thread.join()
        
    except KeyboardInterrupt:
        print("\\n🛑 Shutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Startup error: {{e}}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)
'''
    
    # Write launcher script
    with open('launcher.py', 'w') as f:
        f.write(launcher_content)
    
    # PyInstaller command to create app bundle
    cmd = [
        'pyinstaller',
        '--windowed',                     # Create app bundle instead of single file
        '--name=' + executable_name,
        '--add-data=templates:templates',  # Include HTML templates
        '--add-data=data:data',           # Include SQLite database
        '--add-data=ytscraper:ytscraper', # Include ytscraper module
        '--clean',                        # Clean PyInstaller cache
    ] + icon_args + ['launcher.py']      # Add icon if available
    
    print("Building macOS Application Bundle...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ PyInstaller build successful!")
        
        # Path to the created app bundle
        app_bundle_path = Path(f'dist/{executable_name}.app')
        
        if not app_bundle_path.exists():
            raise Exception(f"App bundle not found at {app_bundle_path}")
        
        # Create proper Info.plist
        info_plist_path = app_bundle_path / 'Contents' / 'Info.plist'
        plist_content = create_info_plist(app_name, bundle_id, executable_name, has_icon=has_icon)
        
        with open(info_plist_path, 'w') as f:
            f.write(plist_content)
        print("✅ Created custom Info.plist")
        
        # Set executable permissions on the main executable
        executable_path = app_bundle_path / 'Contents' / 'MacOS' / executable_name
        if executable_path.exists():
            os.chmod(executable_path, 0o755)
            print("✅ Set executable permissions")
        
        # Create distributable ZIP file
        zip_name = f"{executable_name}.zip"
        zip_path = Path('dist') / zip_name
        
        print(f"📦 Creating distributable ZIP: {zip_name}")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add the app bundle
            for file_path in app_bundle_path.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(Path('dist'))
                    zipf.write(file_path, arcname)
                    # Preserve executable permissions in ZIP
                    info = zipf.getinfo(str(arcname))
                    if file_path.name == executable_name:
                        info.external_attr = 0o755 << 16
            
            # Add helper files for macOS quarantine issues
            helper_files = ['INSTALL_README.md', 'install.sh']
            for helper_file in helper_files:
                if Path(helper_file).exists():
                    zipf.write(helper_file, helper_file)
                    print(f"✅ Added {helper_file} to distribution")
                    # Make install.sh executable
                    if helper_file == 'install.sh':
                        info = zipf.getinfo(helper_file)
                        info.external_attr = 0o755 << 16
        
        print("✅ Application Bundle created successfully!")
        print(f"📁 App Bundle: dist/{executable_name}.app")
        print(f"📦 Distribution ZIP: dist/{zip_name}")
        
        if has_icon:
            print("🎨 Icon successfully integrated!")
        
        print("\n🚀 Distribution Instructions:")
        print("   1. Share the ZIP file from dist/ folder")
        print("   2. Recipients should:")
        print("      - Download and extract the ZIP file")
        print("      - See INSTALL_README.md for detailed instructions")
        print("      - Run install.sh for automatic setup (recommended)")
        print("      - OR: Right-click .app, hold Option, select 'Open'")
        print("      - Click 'Open' when macOS warns about unsigned app")
        print("      - App will start automatically!")
        print("")
        print("   ⚠️  Note: Downloaded apps require quarantine removal")
        print("   📖 INSTALL_README.md contains step-by-step help")
        
    except subprocess.CalledProcessError as e:
        print("❌ Build failed!")
        print(f"Error: {e}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        raise
    finally:
    # Cleanup
    if os.path.exists('launcher.py'):
        os.remove('launcher.py')
        # Clean up temporary .icns file if created
        temp_icns = Path('app_icon.icns')
        if temp_icns.exists() and icon_source and icon_source.suffix.lower() == '.png':
            temp_icns.unlink()

def create_dmg():
    """Optional: Create a DMG file for professional distribution"""
    executable_name = "MMCommentExplorer"
    app_bundle_path = Path(f'dist/{executable_name}.app')
    
    if not app_bundle_path.exists():
        print("❌ App bundle not found. Run build first.")
        return
    
    # Check if hdiutil is available (should be on all macOS systems)
    try:
        dmg_name = f"{executable_name}.dmg"
        dmg_path = Path('dist') / dmg_name
        
        # Remove existing DMG
        if dmg_path.exists():
            dmg_path.unlink()
        
        cmd = [
            'hdiutil', 'create',
            '-volname', 'Medical Medium Comment Explorer',
            '-srcfolder', str(app_bundle_path),
            '-ov', '-format', 'UDZO',
            str(dmg_path)
        ]
        
        print("📀 Creating DMG file...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ DMG created: dist/{dmg_name}")
        
    except subprocess.CalledProcessError as e:
        print("❌ DMG creation failed (optional step)")
        print(f"Error: {e.stderr}")

def install_pyinstaller():
    """Install PyInstaller if not present"""
    try:
        import PyInstaller
        print("✅ PyInstaller is already installed")
    except ImportError:
        print("📦 Installing PyInstaller...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], check=True)

if __name__ == '__main__':
    print("🔧 Medical Medium YouTube Comment Explorer - macOS App Builder")
    print("=" * 70)
    
    # Check if we're on macOS
    if sys.platform != 'darwin':
        print("❌ This script is designed for macOS only")
        sys.exit(1)
    
    # Check if we're in the right directory
    if not os.path.exists('webapp.py'):
        print("❌ Error: Run this script from the project root directory")
        sys.exit(1)
    
    # Install PyInstaller if needed
    install_pyinstaller()
    
    # Build the app bundle
    try:
        build_app_bundle()
        
        # Ask if user wants to create DMG
        print("\n🤔 Would you like to create a DMG file for professional distribution?")
        print("   (This is optional - the ZIP file works perfectly for sharing)")
        response = input("Create DMG? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            create_dmg()
        
        print("\n🎉 Build completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        sys.exit(1) 