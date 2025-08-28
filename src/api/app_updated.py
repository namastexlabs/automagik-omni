"""
FastAPI application for receiving Evolution API webhooks.
"""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
import json
import time

# Import telemetry
from src.core.telemetry import track_api_request, track_webhook_processed

# Import configuration first to ensure environment variables are loaded
from src.config import config

# Import and set up logging
from src.logger import setup_logging

# Set up logging with defaults from config
setup_logging()

from src.services.agent_service import agent_service
from src.channels.whatsapp.evolution_api_sender import evolution_api_sender
from src.api.deps import get_database, get_instance_by_name
from fastapi.openapi.utils import get_openapi
from src.api.routes.instances import router as instances_router
from src.api.routes.unified import router as instances_unified_router
from src.db.database import create_tables