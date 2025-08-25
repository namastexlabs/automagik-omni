"""
Agent API routes for handling Discord/WhatsApp message processing.
This is a simple mock implementation for testing.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/agent",
    tags=["agent"],
)


class AgentRunRequest(BaseModel):
    message: str
    session_id: str
    user_id: Optional[str] = None
    agent_name: Optional[str] = "default"
    context: Optional[Dict[str, Any]] = None


class AgentRunResponse(BaseModel):
    message: str
    success: bool
    session_id: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = []
    tool_outputs: List[str] = []
    usage: Dict[str, Any] = {}
    error: str = ""


@router.post("/{agent_name}/run", response_model=AgentRunResponse)
async def run_agent(
    agent_name: str,
    request: AgentRunRequest
) -> AgentRunResponse:
    """
    Process a message through an agent.
    This is a mock implementation that returns a simple response.
    """
    logger.info(f"Processing message for agent '{agent_name}': {request.message}")
    
    # Simple mock response for testing
    response_message = f"Olá! Recebi sua mensagem: '{request.message}'. Este é um sistema de teste."
    
    return AgentRunResponse(
        message=response_message,
        success=True,
        session_id=request.session_id,
        tool_calls=[],
        tool_outputs=[],
        usage={
            "tokens": len(request.message) + len(response_message)
        },
        error=""
    )


@router.get("/{agent_name}")
async def get_agent_info(agent_name: str):
    """Get information about an agent."""
    return {
        "name": agent_name,
        "type": "mock",
        "status": "active",
        "description": "Mock agent for testing Discord/WhatsApp integration"
    }