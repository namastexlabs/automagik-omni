#!/usr/bin/env python3
"""
Final verification that our fixes are correct.
"""

def verify_transformer_test_data():
    """Verify transformer tests use correct field names."""
    print("🔍 Verifying transformer test data...")
    
    with open("/home/cezar/automagik/automagik-omni/tests/test_unified_transformers.py", 'r') as f:
        content = f.read()
    
    profilePicture_count = content.count('"profilePicture":')
    profilePictureUrl_count = content.count('"profilePictureUrl":')
    
    print(f"  - Old 'profilePicture': {profilePicture_count} occurrences")
    print(f"  - New 'profilePictureUrl': {profilePictureUrl_count} occurrences")
    
    if profilePicture_count == 0 and profilePictureUrl_count > 0:
        print("  ✅ Transformer tests fixed!")
        return True
    else:
        print("  ❌ Transformer tests need fixing")
        return False

def verify_handler_test_config():
    """Verify handler tests use correct mock configuration."""
    print("\n🔍 Verifying handler test configuration...")
    
    with open("/home/cezar/automagik/automagik-omni/tests/test_unified_handlers.py", 'r') as f:
        content = f.read()
    
    old_config_pattern = 'config.config = {'
    new_config_pattern = 'config.evolution_url ='
    
    has_old_config = old_config_pattern in content
    has_new_config = new_config_pattern in content
    
    print(f"  - Old nested config pattern: {'Found' if has_old_config else 'Not found'}")
    print(f"  - New direct attributes: {'Found' if has_new_config else 'Not found'}")
    
    if not has_old_config and has_new_config:
        print("  ✅ Handler test config fixed!")
        return True
    else:
        print("  ❌ Handler test config needs fixing")
        return False

def verify_implementation_match():
    """Verify that implementation matches test expectations."""
    print("\n🔍 Verifying implementation matches...")
    
    # Check transformer implementation
    with open("/home/cezar/automagik/automagik-omni/src/services/unified_transformers.py", 'r') as f:
        transformer_content = f.read()
    
    has_profilePictureUrl = 'profilePictureUrl' in transformer_content
    print(f"  - Transformer expects 'profilePictureUrl': {has_profilePictureUrl}")
    
    # Check handler implementation  
    with open("/home/cezar/automagik/automagik-omni/src/channels/handlers/whatsapp_chat_handler.py", 'r') as f:
        handler_content = f.read()
    
    has_get_contacts = 'async def get_contacts(' in handler_content
    has_evolution_url_access = 'instance.evolution_url' in handler_content
    
    print(f"  - Handler implements get_contacts: {has_get_contacts}")
    print(f"  - Handler accesses evolution_url directly: {has_evolution_url_access}")
    
    if has_profilePictureUrl and has_get_contacts and has_evolution_url_access:
        print("  ✅ Implementation matches test expectations!")
        return True
    else:
        print("  ❌ Implementation mismatch found")
        return False

def apply_remaining_fixes():
    """Apply any remaining fixes."""
    print("\n🔧 Applying remaining fixes...")
    
    # Apply handler mock fix
    import subprocess
    import sys
    
    try:
        result = subprocess.run([sys.executable, "fix_handler_mock.py"], 
                              cwd="/home/cezar/automagik/automagik-omni",
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("  ✅ Handler mock fix applied")
        else:
            print(f"  ❌ Handler mock fix failed: {result.stderr}")
    except Exception as e:
        print(f"  ❌ Error applying handler fix: {e}")

if __name__ == "__main__":
    print("🚀 Final verification of test fixes...")
    
    # Apply fixes first
    apply_remaining_fixes()
    
    # Verify fixes
    transformer_ok = verify_transformer_test_data()
    handler_ok = verify_handler_test_config() 
    implementation_ok = verify_implementation_match()
    
    print(f"\n📊 Final Status:")
    print(f"  - Transformer tests: {'✅ FIXED' if transformer_ok else '❌ NEEDS WORK'}")
    print(f"  - Handler tests: {'✅ FIXED' if handler_ok else '❌ NEEDS WORK'}")
    print(f"  - Implementation match: {'✅ GOOD' if implementation_ok else '❌ ISSUES'}")
    
    if all([transformer_ok, handler_ok, implementation_ok]):
        print("\n🎉 All fixes verified successfully!")
        print("Tests should now pass!")
    else:
        print("\n⚠️  Some issues remain. Check the output above.")