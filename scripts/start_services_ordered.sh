#!/bin/bash
# ===================================================================
# 🚀 Ordered Service Startup Script for Automagik-Omni
# ===================================================================
# This script ensures proper startup order: API -> Health Check -> Discord Bot

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Symbols
CHECKMARK="✅"
ERROR="❌"
WARNING="⚠️"
ROCKET="🚀"
INFO="ℹ️"
HEALTH="🏥"
DISCORD="🤖"

echo -e "${PURPLE}${ROCKET} Starting Automagik-Omni Services with Proper Order${NC}"
echo ""

# Function to print status
print_status() {
    echo -e "${BLUE}${INFO} $1${NC}"
}

print_success() {
    echo -e "${GREEN}${CHECKMARK} $1${NC}"
}

print_error() {
    echo -e "${RED}${ERROR} $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}${WARNING} $1${NC}"
}

# Function to wait for process to exit
wait_for_process_exit() {
    local process_name=$1
    local timeout=${2:-30}
    local count=0
    
    print_status "Waiting for $process_name to exit..."
    while pm2 show $process_name >/dev/null 2>&1; do
        if [ $count -ge $timeout ]; then
            print_warning "$process_name still running after ${timeout}s"
            break
        fi
        sleep 1
        ((count++))
    done
}

# Check if PM2 is available
if ! command -v pm2 &> /dev/null; then
    print_error "PM2 is not installed. Install with: npm install -g pm2"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "ecosystem.config.js" ]; then
    print_error "ecosystem.config.js not found. Run this script from the project root."
    exit 1
fi

# Step 1: Stop any existing services
print_status "Stopping any existing services..."
pm2 stop all >/dev/null 2>&1 || true
pm2 delete all >/dev/null 2>&1 || true
print_success "Stopped existing services"

# Step 2: Start API server first
print_status "${ROCKET} Starting API server..."
pm2 start ecosystem.config.js --only automagik-omni
sleep 5  # Give it a moment to initialize

# Check API status
if pm2 show automagik-omni >/dev/null 2>&1; then
    print_success "API server started"
else
    print_error "Failed to start API server"
    exit 1
fi

# Step 3: Wait for API to be healthy
print_status "${HEALTH} Waiting for API to become healthy..."
if python3 scripts/wait_for_api.py; then
    print_success "API is healthy!"
else
    print_error "API health check failed"
    print_error "Check API logs: pm2 logs automagik-omni"
    exit 1
fi

# Step 4: Start Discord bot
print_status "${DISCORD} Starting Discord bot..."
pm2 start ecosystem.config.js --only automagik-omni-discord
sleep 3

# Check Discord bot status
if pm2 show automagik-omni-discord >/dev/null 2>&1; then
    print_success "Discord bot started"
else
    print_error "Failed to start Discord bot"
    print_error "Check Discord logs: pm2 logs automagik-omni-discord"
    exit 1
fi

# Step 5: Show final status
echo ""
print_success "All services started successfully!"
echo ""
print_status "Service Status:"
pm2 status
echo ""
print_status "To monitor logs:"
echo -e "  ${CYAN}pm2 logs automagik-omni${NC}        # API logs"
echo -e "  ${CYAN}pm2 logs automagik-omni-discord${NC} # Discord logs"
echo -e "  ${CYAN}pm2 monit${NC}                      # Real-time monitoring"
echo ""
print_status "To stop services:"
echo -e "  ${CYAN}pm2 stop all${NC}                   # Stop all services"
echo -e "  ${CYAN}make stop-local${NC}                # Use Makefile command"
echo ""
print_success "Startup complete! ${ROCKET}"