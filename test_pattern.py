#!/usr/bin/env python3
"""Test if our pattern matching will work"""

def test_pattern():
    conftest_path = "/home/cezar/automagik/automagik-omni/tests/conftest.py"
    
    with open(conftest_path, 'r') as f:
        content = f.read()
    
    # Check if the pattern exists
    pattern = """        mock_evolution.delete_instance = mock_delete_instance

        mock_client.return_value = mock_evolution"""
    
    if pattern in content:
        print("✅ Pattern found! Fix can be applied.")
        # Show some context
        start = content.find(pattern)
        context = content[start-100:start+len(pattern)+100]
        print("\nContext:")
        print(repr(context))
    else:
        print("❌ Pattern not found. Let's check what's around that area...")
        # Find the delete_instance line
        if "mock_evolution.delete_instance = mock_delete_instance" in content:
            start = content.find("mock_evolution.delete_instance = mock_delete_instance")
            context = content[start:start+200]
            print("Found delete_instance line, context:")
            print(repr(context))
        else:
            print("Even delete_instance line not found!")

if __name__ == "__main__":
    test_pattern()