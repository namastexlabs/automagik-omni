#!/usr/bin/env python3
"""
Test runner to verify our fixes work.
"""

import subprocess
import sys
import os

def run_fix_scripts():
    """Run the fix scripts first."""
    print("🔧 Applying test fixes...")
    
    # Run the handler mock fix
    try:
        result = subprocess.run([sys.executable, "fix_handler_mock.py"], 
                              cwd="/home/cezar/automagik/automagik-omni",
                              capture_output=True, text=True)
        print(f"Handler mock fix: {result.stdout.strip()}")
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"Error running handler fix: {e}")
    
    # Run the general fix script
    try:
        result = subprocess.run([sys.executable, "fix_tests.py"], 
                              cwd="/home/cezar/automagik/automagik-omni",
                              capture_output=True, text=True)
        print(f"General fixes: {result.stdout.strip()}")
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"Error running general fix: {e}")

def test_imports():
    """Test if our imports work correctly."""
    print("\n📦 Testing imports...")
    
    test_script = """
import sys
sys.path.insert(0, '/home/cezar/automagik/automagik-omni/src')

try:
    from services.unified_transformers import WhatsAppTransformer, DiscordTransformer
    print("✅ Transformers imported successfully")
except Exception as e:
    print(f"❌ Transformer import failed: {e}")

try:
    from channels.handlers.whatsapp_chat_handler import WhatsAppChatHandler
    print("✅ WhatsApp handler imported successfully")
except Exception as e:
    print(f"❌ WhatsApp handler import failed: {e}")
    
try:
    from channels.handlers.discord_chat_handler import DiscordChatHandler
    print("✅ Discord handler imported successfully")
except Exception as e:
    print(f"❌ Discord handler import failed: {e}")
"""
    
    try:
        result = subprocess.run([sys.executable, "-c", test_script],
                              cwd="/home/cezar/automagik/automagik-omni",
                              capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"Import errors: {result.stderr}")
    except Exception as e:
        print(f"Error testing imports: {e}")

def test_simple_transformer():
    """Test a simple transformer operation."""
    print("\n🔄 Testing transformer functionality...")
    
    test_script = """
import sys
sys.path.insert(0, '/home/cezar/automagik/automagik-omni/src')

try:
    from services.unified_transformers import WhatsAppTransformer
    
    # Test contact transformation
    test_contact = {
        "id": "5511999999999@c.us",
        "name": "Test Contact", 
        "profilePictureUrl": "https://example.com/avatar.jpg"
    }
    
    result = WhatsAppTransformer.contact_to_unified(test_contact, "test-instance")
    
    print(f"✅ Transformer works! Contact ID: {result.id}")
    print(f"✅ Name: {result.name}")
    print(f"✅ Avatar URL: {result.avatar_url}")
    
except Exception as e:
    print(f"❌ Transformer test failed: {e}")
    import traceback
    traceback.print_exc()
"""
    
    try:
        result = subprocess.run([sys.executable, "-c", test_script],
                              cwd="/home/cezar/automagik/automagik-omni",
                              capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"Transformer errors: {result.stderr}")
    except Exception as e:
        print(f"Error testing transformer: {e}")

def run_specific_tests():
    """Run specific test files to check our fixes."""
    print("\n🧪 Running specific tests...")
    
    test_files = [
        "tests/test_unified_transformers.py::TestWhatsAppTransformer::test_contact_to_unified_success",
        "tests/test_unified_handlers.py::TestWhatsAppChatHandler::test_initialization",
    ]
    
    for test_file in test_files:
        print(f"\n  Running: {test_file}")
        try:
            result = subprocess.run(["uv", "run", "pytest", test_file, "-v", "--tb=short"],
                                  cwd="/home/cezar/automagik/automagik-omni",
                                  capture_output=True, text=True, timeout=60)
            
            if "PASSED" in result.stdout:
                print("✅ PASSED")
            elif "FAILED" in result.stdout:
                print("❌ FAILED")
                print(result.stdout[-500:])  # Show last 500 chars
            else:
                print("⚠️  Unknown result")
                print(result.stdout[-200:])
                
            if result.stderr and "warning" not in result.stderr.lower():
                print(f"Errors: {result.stderr[-200:]}")
                
        except subprocess.TimeoutExpired:
            print("⏰ Test timed out")
        except Exception as e:
            print(f"❌ Error running test: {e}")

if __name__ == "__main__":
    print("🚀 Starting test fix validation...")
    
    # Apply fixes
    run_fix_scripts()
    
    # Test imports
    test_imports()
    
    # Test transformer functionality
    test_simple_transformer()
    
    # Run specific tests
    run_specific_tests()
    
    print("\n✨ Test fix validation complete!")