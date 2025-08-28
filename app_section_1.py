# The imports section that needs to be modified
from src.api.deps import get_database, get_instance_by_name
from fastapi.openapi.utils import get_openapi
from src.api.routes.instances import router as instances_router
from src.api.routes.unified import router as unified_router
from src.db.database import create_tables