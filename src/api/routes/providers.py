"""
CRUD API for managing Agent Providers.

Agent Providers store reusable API credentials that can be shared across
multiple instances. When an instance is linked to a provider, it uses
the provider's credentials for agent communication.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict

from src.api.deps import get_database, verify_api_key
from src.db.models import AgentProvider
from src.services.provider_service import provider_service

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic schemas


class ProviderCreate(BaseModel):
    """Schema for creating an agent provider."""

    name: str = Field(..., description="Unique display name", min_length=1, max_length=255)
    api_url: str = Field(..., description="Base API URL")
    api_key: str = Field(..., description="API authentication key")
    description: Optional[str] = Field(None, description="Optional description")
    is_active: bool = Field(True, description="Whether the provider is active")


class ProviderUpdate(BaseModel):
    """Schema for updating an agent provider."""

    name: Optional[str] = Field(None, description="Display name", min_length=1, max_length=255)
    api_url: Optional[str] = Field(None, description="Base API URL")
    api_key: Optional[str] = Field(None, description="API authentication key")
    description: Optional[str] = Field(None, description="Optional description")
    is_active: Optional[bool] = Field(None, description="Whether the provider is active")


class ProviderResponse(BaseModel):
    """Schema for provider response."""

    id: int
    name: str
    api_url: str
    has_api_key: bool  # Don't expose the actual key
    description: Optional[str]
    is_active: bool
    last_health_check: Optional[str]
    last_health_status: Optional[str]
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class HealthCheckResponse(BaseModel):
    """Schema for health check response."""

    status: str
    http_status: Optional[int] = None
    message: Optional[str] = None
    checked_at: str


class AgentResponse(BaseModel):
    """Schema for agent from provider API."""

    id: str
    name: Optional[str] = None
    description: Optional[str] = None


class TeamResponse(BaseModel):
    """Schema for team from provider API."""

    id: str
    name: Optional[str] = None
    description: Optional[str] = None


# Helper functions


def _to_provider_response(provider: AgentProvider) -> ProviderResponse:
    """Convert ORM provider to response model."""
    created_at = provider.created_at.isoformat() if provider.created_at else ""
    updated_at = provider.updated_at.isoformat() if provider.updated_at else ""
    last_health_check = provider.last_health_check.isoformat() if provider.last_health_check else None

    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        api_url=provider.api_url,
        has_api_key=bool(provider.api_key),
        description=provider.description,
        is_active=provider.is_active,
        last_health_check=last_health_check,
        last_health_status=provider.last_health_status,
        created_at=created_at,
        updated_at=updated_at,
    )


# API Endpoints


@router.get(
    "/providers",
    response_model=List[ProviderResponse],
    summary="List Agent Providers",
    description="Retrieve all agent providers",
)
async def list_providers(
    include_inactive: bool = False,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """List all agent providers."""
    providers = provider_service.list_providers(db, include_inactive=include_inactive)
    return [_to_provider_response(p) for p in providers]


@router.get(
    "/providers/{provider_id}",
    response_model=ProviderResponse,
    summary="Get Agent Provider",
    description="Retrieve a specific agent provider by ID",
)
async def get_provider(
    provider_id: int,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Get a specific provider by ID."""
    provider = provider_service.get_provider(provider_id, db)

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider with ID {provider_id} not found",
        )

    return _to_provider_response(provider)


@router.post(
    "/providers",
    response_model=ProviderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Agent Provider",
    description="Create a new agent provider",
)
async def create_provider(
    data: ProviderCreate,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Create a new agent provider."""
    try:
        provider = provider_service.create_provider(
            name=data.name,
            api_url=data.api_url,
            api_key=data.api_key,
            db=db,
            description=data.description,
            is_active=data.is_active,
        )
        return _to_provider_response(provider)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put(
    "/providers/{provider_id}",
    response_model=ProviderResponse,
    summary="Update Agent Provider",
    description="Update an existing agent provider",
)
async def update_provider(
    provider_id: int,
    data: ProviderUpdate,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Update an existing provider."""
    try:
        provider = provider_service.update_provider(
            provider_id=provider_id,
            db=db,
            name=data.name,
            api_url=data.api_url,
            api_key=data.api_key,
            description=data.description,
            is_active=data.is_active,
        )
        return _to_provider_response(provider)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/providers/{provider_id}",
    summary="Delete Agent Provider",
    description="Delete an agent provider",
)
async def delete_provider(
    provider_id: int,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Delete an agent provider."""
    success = provider_service.delete_provider(provider_id, db)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider with ID {provider_id} not found",
        )

    return {"message": f"Provider {provider_id} deleted successfully"}


@router.post(
    "/providers/{provider_id}/health",
    response_model=HealthCheckResponse,
    summary="Check Provider Health",
    description="Check the health of a provider's API",
)
async def check_provider_health(
    provider_id: int,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Check the health of a provider's API."""
    result = await provider_service.check_health(provider_id, db)

    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("message", "Provider not found"),
        )

    return HealthCheckResponse(
        status=result["status"],
        http_status=result.get("http_status"),
        message=result.get("message"),
        checked_at=result["checked_at"],
    )


@router.get(
    "/providers/{provider_id}/agents",
    response_model=List[AgentResponse],
    summary="Fetch Agents",
    description="Fetch available agents from the provider's API",
)
async def fetch_agents(
    provider_id: int,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Fetch available agents from the provider's API."""
    try:
        agents = await provider_service.fetch_agents(provider_id, db)
        return [
            AgentResponse(
                id=a.get("id", a.get("agent_id", "")),
                name=a.get("name"),
                description=a.get("description"),
            )
            for a in agents
        ]

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/providers/{provider_id}/teams",
    response_model=List[TeamResponse],
    summary="Fetch Teams",
    description="Fetch available teams from the provider's API",
)
async def fetch_teams(
    provider_id: int,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Fetch available teams from the provider's API."""
    try:
        teams = await provider_service.fetch_teams(provider_id, db)
        return [
            TeamResponse(
                id=t.get("id", t.get("team_id", "")),
                name=t.get("name"),
                description=t.get("description"),
            )
            for t in teams
        ]

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
