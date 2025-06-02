#!/bin/bash
# Medical Medium Comment Explorer - Auto Installer
# This script removes quarantine attributes and launches the app

echo "🔧 Medical Medium Comment Explorer - Auto Installer"
echo "======================================================"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "📁 Script location: $SCRIPT_DIR"

# Change to the script's directory
cd "$SCRIPT_DIR"
echo "📂 Changed to directory: $(pwd)"

# Check if app exists
if [ ! -d "MMCommentExplorer.app" ]; then
    echo "❌ MMCommentExplorer.app not found in current directory"
    echo "📋 Contents of current directory:"
    ls -la
    echo ""
    echo "💡 Make sure the app is in the same folder as this script"
    echo "💡 Or try the manual installation method in INSTALL_README.md"
    exit 1
fi

echo "📱 Found MMCommentExplorer.app"

# Remove quarantine attributes
echo "🔓 Removing macOS quarantine attributes..."
xattr -cr MMCommentExplorer.app

# Check if removal was successful
if [ $? -eq 0 ]; then
    echo "✅ Quarantine attributes removed successfully"
else
    echo "⚠️  Warning: Could not remove quarantine attributes"
    echo "💡 You may need to run: sudo xattr -cr MMCommentExplorer.app"
fi

# Launch the app
echo "🚀 Launching Medical Medium Comment Explorer..."
open MMCommentExplorer.app

if [ $? -eq 0 ]; then
    echo "✅ App launched successfully!"
    echo "🌐 The app will open your browser to http://127.0.0.1:9191"
    echo "🎉 Enjoy exploring Medical Medium YouTube comments!"
else
    echo "❌ Failed to launch app"
    echo "💡 Try running manually: open MMCommentExplorer.app"
fi

echo ""
echo "📧 If you need help, contact the app creator"
echo "⏸️  Press any key to close this window..."
read -n 1 -s 