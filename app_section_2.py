# The router registration section that needs to be modified
# Include instance management routes
app.include_router(instances_router, prefix="/api/v1", tags=["instances"])
# Include unified endpoints routes  
app.include_router(unified_router, prefix="/api/v1/instances", tags=["unified-instances"])