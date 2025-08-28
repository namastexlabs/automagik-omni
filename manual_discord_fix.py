import re

# Read the test file
with open("tests/test_unified_handlers.py", "r") as f:
    content = f.read()

# Fix all Discord test function signatures by removing mock_get_bot parameter
original = content
content = re.sub(r"self, mock_get_bot, handler, mock_instance_config, mock_discord_bot", 
                 "self, handler, mock_instance_config, mock_discord_bot", content)
content = re.sub(r"self, mock_get_bot, handler, mock_instance_config(?!\S)", 
                 "self, handler, mock_instance_config", content)

changes = original.count("mock_get_bot") - content.count("mock_get_bot")
print(f"Removed {changes} mock_get_bot parameters")

# Write back
with open("tests/test_unified_handlers.py", "w") as f:
    f.write(content)

print("Discord fixture fix applied!")