#!/usr/bin/env python3
"""Clean up old unified files"""

import os
import glob

def cleanup():
    base_dir = "/home/cezar/automagik/automagik-omni"
    
    # Files to remove
    old_files = [
        "src/api/schemas/unified.py",
        "src/channels/unified_base.py", 
        "src/channels/whatsapp/unified_evolution_client.py",
        "src/services/unified_transformers.py",
        "src/api/routes/unified.py"
    ]
    
    # Also remove compiled Python files
    old_pycache_files = glob.glob(f"{base_dir}/src/**/*unified*.pyc", recursive=True)
    old_pycache_files.extend(glob.glob(f"{base_dir}/src/**/__pycache__/*unified*", recursive=True))
    
    all_files_to_remove = [f"{base_dir}/{f}" for f in old_files] + old_pycache_files
    
    removed_count = 0
    for filepath in all_files_to_remove:
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                print(f"Removed: {filepath}")
                removed_count += 1
            except Exception as e:
                print(f"Error removing {filepath}: {e}")
    
    print(f"Removed {removed_count} old unified files.")

if __name__ == "__main__":
    cleanup()