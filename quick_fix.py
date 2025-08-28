exec('''
import os
os.chdir('/home/cezar/automagik/automagik-omni')
with open('src/api/app.py') as f: content = f.read()
content = content.replace('"description": "System Health & Status",\\n        }\\n    ],', '"description": "System Health & Status",\\n        },\\n        {\\n            "name": "unified",\\n            "description": "Unified Multi-Channel Operations",\\n        }\\n    ],')
content = content.replace('    logger.error(traceback.format_exc())\\n\\n# Add request logging middleware', '    logger.error(traceback.format_exc())\\n\\n# Include unified multi-channel routes\\ntry:\\n    from src.api.routes.unified import router as unified_router\\n\\n    app.include_router(unified_router, prefix="/api/v1", tags=["unified"])\\n    logger.info("✅ Unified multi-channel routes included successfully")\\nexcept Exception as e:\\n    logger.error(f"❌ Failed to include unified router: {e}")\\n    import traceback\\n\\n    logger.error(traceback.format_exc())\\n\\n# Add request logging middleware')
with open('src/api/app.py', 'w') as f: f.write(content)
print("Successfully updated src/api/app.py with unified endpoints registration!")
''')