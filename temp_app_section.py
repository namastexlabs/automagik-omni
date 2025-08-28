# This is a temporary file to help with the edit
# Current OpenAPI tags end with:
        {
            "name": "health",
            "description": "System Health & Status",
        }
    ],

# Should be modified to:
        {
            "name": "health",
            "description": "System Health & Status",
        },
        {
            "name": "unified",
            "description": "Unified Multi-Channel Operations",
        }
    ],

# Current messages router section:
# Include message sending routes
try:
    from src.api.routes.messages import router as messages_router

    app.include_router(messages_router, prefix="/api/v1/instance", tags=["messages"])
except Exception as e:
    logger.error(f"❌ Failed to include messages router: {e}")
    import traceback

    logger.error(traceback.format_exc())

# Should be modified to add after that:
# Include unified multi-channel routes
try:
    from src.api.routes.unified import router as unified_router

    app.include_router(unified_router, prefix="/api/v1", tags=["unified"])
    logger.info("✅ Unified multi-channel routes included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include unified router: {e}")
    import traceback

    logger.error(traceback.format_exc())