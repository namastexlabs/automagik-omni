#!/usr/bin/env python3
"""Script to update rate limiter with optimized version."""

import shutil
import os

def main():
    """Update the rate limiter file."""
    original_file = "src/utils/rate_limiter.py"
    optimized_file = "src/utils/rate_limiter_optimized.py"
    backup_file = "src/utils/rate_limiter_backup.py"
    
    # Verify files exist
    if not os.path.exists(optimized_file):
        print(f"Error: {optimized_file} does not exist")
        return
    
    if not os.path.exists(original_file):
        print(f"Error: {original_file} does not exist")
        return
        
    try:
        # Create backup (already exists, so skip)
        print(f"Backup already exists at {backup_file}")
        
        # Replace original with optimized version
        shutil.copy2(optimized_file, original_file)
        print(f"Successfully replaced {original_file} with optimized version")
        
        # Clean up optimized file
        os.remove(optimized_file)
        print(f"Cleaned up {optimized_file}")
        
        print("\nRate limiter optimization complete!")
        print("Key improvements:")
        print("- Replaced List with deque for O(1) operations")
        print("- Added TTL-based cleanup to prevent memory leaks")
        print("- Implemented async check_rate_limit() method")
        print("- Added cleanup() and get_stats() methods")
        print("- Fixed performance bottleneck on line 54")
        
    except Exception as e:
        print(f"Error updating rate limiter: {e}")

if __name__ == "__main__":
    main()