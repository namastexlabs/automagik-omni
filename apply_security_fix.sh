#!/bin/bash
# Apply critical Discord security fixes
echo "🚨 APPLYING CRITICAL DISCORD SECURITY FIXES"
echo "Backing up original file..."
cp src/api/routes/instances.py src/api/routes/instances.py.backup
echo "Applying security fixes..."
cp src/api/routes/instances_fixed.py src/api/routes/instances.py
echo "Cleaning up temporary file..."
rm src/api/routes/instances_fixed.py
echo "✅ SECURITY FIXES APPLIED SUCCESSFULLY!"
echo ""
echo "FIXES APPLIED:"
echo "1. Removed discord_bot_token from InstanceConfigResponse schema"
echo "2. Added discord_bot_token masking to logging section"  
echo "3. Updated response building to use has_discord_bot_token boolean"
echo ""
echo "Discord bot tokens are now secure from API response and logging exposure!"