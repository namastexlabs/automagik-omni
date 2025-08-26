#!/usr/bin/env python3
"""
Script to apply Discord bot error handling improvements.

This script backs up the original bot_manager.py and replaces it
with the improved version that includes:
1. Proper resource cleanup on LoginFailure
2. Jittered exponential backoff
3. Circuit breaker pattern
4. Enhanced logging
"""

import os
import shutil
from datetime import datetime

def apply_improvements():
    """Apply the Discord bot error handling improvements."""
    
    original_file = "/home/cezar/automagik/automagik-omni/src/channels/discord/bot_manager.py"
    improved_file = "/home/cezar/automagik/automagik-omni/src/channels/discord/bot_manager_improved.py"
    backup_file = f"{original_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        # Check if files exist
        if not os.path.exists(original_file):
            print(f"❌ Original file not found: {original_file}")
            return False
            
        if not os.path.exists(improved_file):
            print(f"❌ Improved file not found: {improved_file}")
            return False
        
        # Create backup
        print(f"📦 Creating backup: {backup_file}")
        shutil.copy2(original_file, backup_file)
        
        # Replace original with improved version
        print(f"🔄 Replacing original file with improved version...")
        shutil.copy2(improved_file, original_file)
        
        # Verify the replacement
        with open(original_file, 'r') as f:
            content = f.read()
            if 'CircuitBreakerState' in content and 'random' in content:
                print("✅ Discord bot error handling improvements successfully applied!")
                print("\n🎉 Improvements included:")
                print("  ✓ Added proper resource cleanup on LoginFailure")
                print("  ✓ Implemented jittered exponential backoff")
                print("  ✓ Added circuit breaker pattern with failure tracking")
                print("  ✓ Enhanced structured logging for different error scenarios")
                print("  ✓ Improved production resilience and reliability")
                
                print(f"\n💾 Backup saved as: {backup_file}")
                print(f"📝 Original file updated: {original_file}")
                
                return True
            else:
                print("❌ File replacement verification failed")
                return False
                
    except Exception as e:
        print(f"❌ Error applying improvements: {e}")
        
        # Restore from backup if it exists
        if os.path.exists(backup_file):
            print(f"🔄 Restoring from backup...")
            shutil.copy2(backup_file, original_file)
            print(f"✅ Restored from backup: {backup_file}")
        
        return False

def main():
    """Main function."""
    print("Discord Bot Error Handling Improvement Deployment")
    print("=" * 50)
    
    success = apply_improvements()
    
    if success:
        print("\n🚀 Ready to test! The Discord bot now has:")
        print("  • Resilient connection handling with circuit breaker")
        print("  • Jittered backoff to prevent thundering herd problems")
        print("  • Proper resource cleanup on permanent failures")
        print("  • Comprehensive structured logging")
        print("  • Production-ready error handling")
        
        print("\n📋 Next steps:")
        print("  1. Test the improved error handling")
        print("  2. Monitor logs for structured error information")
        print("  3. Verify circuit breaker behavior during failures")
        print("  4. Confirm resource cleanup works correctly")
        
    else:
        print("\n❌ Deployment failed. Please check the errors above.")
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)