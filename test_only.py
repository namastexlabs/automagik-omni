path="/home/cezar/automagik/automagik-omni/tests/conftest.py"
content=open(path).read()
pattern="        mock_evolution.delete_instance = mock_delete_instance\n\n        mock_client.return_value = mock_evolution"
print("Pattern found:", pattern in content)
if pattern not in content:
    # Show what's actually around that area
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if "delete_instance = mock_delete_instance" in line:
            print(f"Found at line {i+1}: {line}")
            print(f"Line {i+2}: {repr(lines[i+1]) if i+1 < len(lines) else 'EOF'}")
            print(f"Line {i+3}: {repr(lines[i+2]) if i+2 < len(lines) else 'EOF'}")
            break