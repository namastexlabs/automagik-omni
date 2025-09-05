#!/bin/bash

# Automagik Omni Update Script
# Updates code, syncs dependencies, and restarts PM2 process

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Automagik Omni Update Script ===${NC}"

# Change to project directory
cd /home/namastex/prod/automagik-omni

# 1. Check for uncommitted changes
echo -e "${YELLOW}Checking for uncommitted changes...${NC}"
if [[ -n $(git status --porcelain) ]]; then
    echo -e "${YELLOW}Found uncommitted changes. Stashing...${NC}"
    git stash push -m "Auto-stash before update $(date +%Y%m%d-%H%M%S)"
fi

# 2. Fetch and pull latest changes
echo -e "${YELLOW}Fetching latest changes...${NC}"
git fetch origin

# Get current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo -e "${GREEN}Current branch: ${CURRENT_BRANCH}${NC}"

# Pull latest changes for current branch
echo -e "${YELLOW}Pulling latest changes...${NC}"
git pull origin ${CURRENT_BRANCH}

# 3. Sync dependencies with uv
echo -e "${YELLOW}Syncing dependencies with uv...${NC}"
/home/namastex/.local/bin/uv sync

# 4. Check PM2 status before restart
echo -e "${YELLOW}Checking PM2 status...${NC}"
PM2_STATUS=$(pm2 list --json 2>/dev/null || echo "[]")

# Find automagik-omni-api process
API_PROCESS=$(echo "$PM2_STATUS" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for app in data:
    if 'automagik-omni-api' in app.get('name', ''):
        print(app['name'])
        break
" 2>/dev/null || echo "")

if [ -n "$API_PROCESS" ]; then
    echo -e "${GREEN}Found PM2 process: ${API_PROCESS}${NC}"
    
    # Restart the PM2 process
    echo -e "${YELLOW}Restarting PM2 process...${NC}"
    pm2 restart "$API_PROCESS"
    
    # Wait for process to restart
    sleep 3
    
    # Check if process is running
    PM2_CHECK=$(pm2 describe "$API_PROCESS" 2>/dev/null | grep "status" | grep "online" || echo "")
    if [ -n "$PM2_CHECK" ]; then
        echo -e "${GREEN}✓ PM2 process restarted successfully!${NC}"
    else
        echo -e "${RED}PM2 process might be having issues. Checking status...${NC}"
        pm2 status "$API_PROCESS"
    fi
else
    echo -e "${RED}No PM2 process found for automagik-omni-api${NC}"
    echo -e "${YELLOW}Available PM2 processes:${NC}"
    pm2 list
    echo
    echo -e "${YELLOW}To start the process manually, use:${NC}"
    echo "pm2 start ecosystem.config.js --only automagik-omni-api"
fi

# 5. Test API health endpoints
echo -e "${YELLOW}Testing API endpoints...${NC}"
sleep 2

# Test main API port (38889)
echo -e "${YELLOW}Testing main API on port 38889...${NC}"
if curl -s -f http://localhost:38889/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Main API (38889) is responding!${NC}"
    curl -s http://localhost:38889/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:38889/health
else
    echo -e "${YELLOW}Main API (38889) not responding yet...${NC}"
fi

# Test Discord webhook port if applicable (38890)
echo -e "${YELLOW}Testing Discord webhook on port 38890...${NC}"
if curl -s -f http://localhost:38890/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Discord webhook (38890) is responding!${NC}"
else
    echo -e "${YELLOW}Discord webhook (38890) not active or not configured${NC}"
fi

# 6. Show PM2 logs for diagnostics
echo -e "${YELLOW}Recent PM2 logs:${NC}"
pm2 logs automagik-omni-api --lines 5 --nostream 2>/dev/null || echo "No logs available"

# 7. Final status check
echo
echo -e "${BLUE}=== Final Status Check ===${NC}"
pm2 list | grep -E "automagik-omni|App name" || echo "No automagik-omni processes found"

# 8. Pop stash if we stashed earlier
if git stash list | grep -q "Auto-stash before update"; then
    echo -e "${YELLOW}Restoring stashed changes...${NC}"
    git stash pop || echo -e "${YELLOW}Could not auto-restore stash. Run 'git stash pop' manually if needed.${NC}"
fi

echo
echo -e "${GREEN}=== Update Complete ===${NC}"
echo -e "Current branch: ${CURRENT_BRANCH}"
echo -e "Latest commit: $(git log -1 --oneline)"
echo
echo -e "${BLUE}Useful commands:${NC}"
echo "  View logs:    pm2 logs automagik-omni-api"
echo "  Check status: pm2 status automagik-omni-api"
echo "  Restart:      pm2 restart automagik-omni-api"
echo "  Stop:         pm2 stop automagik-omni-api"