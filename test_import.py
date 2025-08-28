#!/usr/bin/env python3
"""Test if we can import the unified router module"""

import sys
import os

# Add the src directory to path
sys.path.insert(0, '/home/cezar/automagik/automagik-omni/src')

try:
    from api.routes.unified import router as unified_router
    print("✅ Successfully imported unified router")
    print(f"Router type: {type(unified_router)}")
    print(f"Router routes: {len(unified_router.routes)} routes found")
    
    # Check if it's a FastAPI router
    from fastapi import APIRouter
    if isinstance(unified_router, APIRouter):
        print("✅ unified_router is a valid APIRouter")
    else:
        print(f"❌ unified_router is not an APIRouter, it's: {type(unified_router)}")
        
except ImportError as e:
    print(f"❌ Failed to import unified router: {e}")
    
try:
    from api.routes.instances import router as instances_router
    print("✅ Successfully imported instances router (for comparison)")
except ImportError as e:
    print(f"❌ Failed to import instances router: {e}")