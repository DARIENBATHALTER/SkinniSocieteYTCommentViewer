# Medical Medium Comment Explorer - Installation Guide

## 📥 Installation Steps

### Method 1: Automatic Installer (Easiest!)

1. **Download and extract** the ZIP file
2. **Optional**: Rename `install.sh` to `RUNFIRST.sh` for clarity
3. **Double-click** the script file
4. **Allow** Terminal to run the script if prompted
5. Script will automatically:
   - Find the correct directory
   - Remove quarantine attributes
   - Launch the app
   - Open your browser

### Method 2: Terminal Command

1. **Download and extract** the ZIP file
2. **Open Terminal** (found in Applications > Utilities)
3. **Drag the app** into Terminal window (this will type the path)
4. **Backspace** to remove the app name, leaving just the folder path
5. **Type this command**:
   ```bash
   cd [paste the folder path here]
   xattr -cr MMCommentExplorer.app
   open MMCommentExplorer.app
   ```

### Method 3: Manual Steps

1. **Download and extract** the ZIP file
2. **Right-click** on `MMCommentExplorer.app`
3. **Hold Option key** and select **"Open"** from menu
4. Click **"Open"** in the security dialog
5. App will launch automatically!

### Method 4: One-Line Terminal Fix

If you're comfortable with Terminal:
```bash
xattr -cr ~/Downloads/MMCommentExplorer.app && open ~/Downloads/MMCommentExplorer.app
```
*(Adjust path if downloaded elsewhere)*

## ⚠️ Why This Happens

macOS adds a "quarantine" attribute to downloaded apps for security. This is normal and affects all unsigned apps downloaded from the internet.

## 🚀 What the App Does

- Launches a local web server on http://127.0.0.1:9191
- Opens your browser automatically
- Provides a beautiful interface to explore Medical Medium YouTube comments
- All data processing happens locally on your computer

## 🔒 Privacy & Security

- **No data leaves your computer** - everything runs locally
- **No internet required** after initial setup
- **Your API keys are embedded** - no configuration needed
- **Open source** - you can inspect the code

## 📧 Need Help?

If you have issues, the app creator can provide additional assistance. 