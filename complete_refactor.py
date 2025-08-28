#!/usr/bin/env python3
"""Complete refactor script: unified -> omni"""

import subprocess
import sys
import os

def run_script(script_path):
    """Run a Python script"""
    try:
        result = subprocess.run([sys.executable, script_path], 
                              capture_output=True, text=True, cwd=os.getcwd())
        print(f"\n{'='*60}")
        print(f"Running: {script_path}")
        print(f"{'='*60}")
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        if result.returncode != 0:
            print(f"WARNING: Script {script_path} returned non-zero exit code: {result.returncode}")
        return result.returncode == 0
    except Exception as e:
        print(f"ERROR running {script_path}: {e}")
        return False

def main():
    """Run complete refactor"""
    print("Starting complete unified -> omni refactor...")
    
    base_dir = "/home/cezar/automagik/automagik-omni"
    
    scripts_to_run = [
        "update_app_py.py",
        "update_whatsapp_handler.py", 
        "update_discord_handler.py",
        "rename_test_files.py",
        "update_documentation.py",
        "cleanup_old_files.py"
    ]
    
    success_count = 0
    for script in scripts_to_run:
        script_path = os.path.join(base_dir, script)
        if os.path.exists(script_path):
            if run_script(script_path):
                success_count += 1
            else:
                print(f"Failed to run {script}")
        else:
            print(f"Script not found: {script_path}")
    
    print(f"\\n{'='*60}")
    print(f"REFACTOR COMPLETE!")
    print(f"Successfully ran {success_count}/{len(scripts_to_run)} scripts")
    print(f"{'='*60}")
    
    if success_count == len(scripts_to_run):
        print("\\n✅ All scripts completed successfully!")
        print("\\nRefactor Summary:")
        print("- Renamed all unified files to omni")
        print("- Updated all imports and references")
        print("- Updated class names from Unified* to Omni*")
        print("- Updated function names from *unified* to *omni*")
        print("- Renamed and updated test files")
        print("- Updated documentation")
        print("- Cleaned up old unified files")
    else:
        print("\\n⚠️  Some scripts failed. Please check the output above.")

if __name__ == "__main__":
    main()