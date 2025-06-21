#!/bin/bash

# ===========================================
# 🚀 Omni-Hub Simple Deployment Script v0.2.0
# ===========================================

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${PURPLE}🚀 Starting Omni-Hub v0.2.0 Deployment${NC}"
echo "=============================================="

# Check if Python is available
if ! command -v python3 >/dev/null 2>&1; then
    echo -e "${RED}❌ Python3 not found. Please install Python 3.10+${NC}"
    exit 1
fi

echo -e "${BLUE}ℹ️ Python detected - using manual deployment${NC}"

# Check environment configuration
if [ ! -f ".env" ]; then
    if [ -f ".env.production" ]; then
        echo -e "${BLUE}ℹ️ Copying production environment template...${NC}"
        cp .env.production .env
        echo -e "${YELLOW}⚠️ Please edit .env with your actual configuration values${NC}"
    else
        echo -e "${YELLOW}⚠️ No .env file found. Creating from example...${NC}"
        cp .env.example .env
        echo -e "${YELLOW}⚠️ Please edit .env with your configuration before continuing${NC}"
    fi
    echo "Press Enter after editing .env to continue..."
    read -r
fi

# Install dependencies
echo -e "${BLUE}ℹ️ Installing dependencies...${NC}"
if command -v uv >/dev/null 2>&1; then
    uv sync
else
    pip install -e .
fi

# Initialize database
echo -e "${BLUE}ℹ️ Initializing database...${NC}"
python -c "from src.db.bootstrap import bootstrap_default_instance; bootstrap_default_instance()"

# Create logs directory
mkdir -p logs

# Start service
echo -e "${BLUE}ℹ️ Starting service...${NC}"
nohup python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 > logs/omni-hub.log 2>&1 &

sleep 5

# Health check
echo -e "${BLUE}ℹ️ Checking service health...${NC}"
if curl -f http://localhost:8000/health >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Health check passed!${NC}"
else
    echo -e "${RED}❌ Health check failed!${NC}"
    tail logs/omni-hub.log
    exit 1
fi

# Final verification
if curl -f http://localhost:8000/docs >/dev/null 2>&1; then
    echo -e "${GREEN}✅ API documentation accessible${NC}"
fi

if curl -f http://localhost:8000/api/instances/ >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Multi-tenancy API accessible${NC}"
fi

# Deployment summary
echo ""
echo "=============================================="
echo -e "${GREEN}✅ Omni-Hub v0.2.0 Deployment Complete!${NC}"
echo ""
echo -e "${BLUE}ℹ️ Service Information:${NC}"
echo "  • API URL: http://localhost:8000"
echo "  • API Documentation: http://localhost:8000/docs"
echo "  • Health Check: http://localhost:8000/health"
echo "  • Multi-tenant Instances: http://localhost:8000/api/instances/"
echo ""
echo -e "${BLUE}ℹ️ Management Commands:${NC}"
echo "  • View logs: tail -f logs/omni-hub.log"
echo "  • Stop service: pkill -f uvicorn"
echo "  • Restart: ./scripts/deploy.sh"
echo "  • List instances: make cli-instances"
echo "  • Create instance: make cli-create"
echo ""
echo -e "${GREEN}✅ Ready for production use!${NC}"
echo "=============================================="