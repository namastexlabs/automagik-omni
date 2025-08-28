#!/usr/bin/env python3
"""
Script to replace the original app.py with the updated version
"""
import shutil
import os

# Define file paths
original_app = "/home/cezar/automagik/automagik-omni/src/api/app.py"
updated_app = "/home/cezar/automagik/automagik-omni/src/api/app_updated.py"
backup_app = "/home/cezar/automagik/automagik-omni/src/api/app_backup.py"

try:
    # Create backup of original file
    if os.path.exists(original_app):
        shutil.copy2(original_app, backup_app)
        print(f"✅ Backup created: {backup_app}")
    
    # Replace original with updated version
    if os.path.exists(updated_app):
        shutil.copy2(updated_app, original_app)
        print(f"✅ Replaced {original_app} with updated version")
        
        # Clean up the temporary updated file
        os.remove(updated_app)
        print(f"✅ Cleaned up temporary file: {updated_app}")
        
        print("\n🎉 Successfully updated app.py with unified router registration!")
        print("Changes made:")
        print("  1. Added 'unified' tag to openapi_tags list")
        print("  2. Imported and included unified router after messages router")
        print("  3. Unified endpoints are now accessible at /api/v1/unified/*")
        
    else:
        print(f"❌ Updated file not found: {updated_app}")
        
except Exception as e:
    print(f"❌ Error during file replacement: {e}")
    if os.path.exists(backup_app):
        print("Backup file is available for manual restoration if needed")