# Include instance management routes
app.include_router(instances_router, prefix="/api/v1", tags=["instances"])

# Include unified instance endpoints with clean routing
app.include_router(instances_unified_router, prefix="/api/v1", tags=["instances"])

# Include trace management routes
from src.api.routes.traces import router as traces_router