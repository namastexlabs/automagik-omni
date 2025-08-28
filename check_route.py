import sys
import os
sys.path.insert(0, '/home/cezar/automagik/automagik-omni/src')

# Check the route parameters
try:
    from api.routes.omni import get_omni_contacts
    import inspect
    sig = inspect.signature(get_omni_contacts)
    print("get_omni_contacts signature:")
    for param_name, param in sig.parameters.items():
        print(f"  {param_name}: {param.annotation}")
        if hasattr(param, 'default') and param.default != inspect.Parameter.empty:
            print(f"    default: {param.default}")
except Exception as e:
    print(f"Error inspecting route: {e}")

# Also check if we can import the route modules
try:
    from api.routes.omni import router as omni_router
    print(f"\nOmni router: {omni_router}")
except Exception as e:
    print(f"Error importing omni router: {e}")