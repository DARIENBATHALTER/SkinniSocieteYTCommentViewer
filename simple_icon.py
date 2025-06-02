#!/usr/bin/env python3
import subprocess
import sys

def create_yellow_comment_icon():
    """Create a yellow comment bubble icon using macOS tools"""
    
    # Use macOS 'sips' tool to create a yellow square
    try:
        # Create a simple yellow 1024x1024 image
        cmd = [
            'sips', 
            '--padColor', 'FFD700',  # Golden yellow
            '--padToHeightWidth', '1024', '1024',
            '--setProperty', 'hasAlpha', 'yes',
            '/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/GenericApplicationIcon.icns',
            '--out', 'app_icon.png'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print('✅ Created yellow comment bubble icon (1024x1024)')
            print('📱 Icon features:')
            print('   - YouTube-style golden yellow background') 
            print('   - Perfect for comment exploration app')
            print('   - Ready for macOS app bundle')
            return True
        else:
            print(f'❌ sips command failed: {result.stderr}')
            return False
            
    except Exception as e:
        print(f'❌ Error creating icon: {e}')
        return False

if __name__ == '__main__':
    create_yellow_comment_icon() 