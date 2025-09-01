"""Dependency guard for optional features and lazy imports."""

import importlib
from functools import wraps
from typing import Any, Optional


class DependencyError(ImportError):
    """Raised when a required dependency is not available."""
    pass


class LazyImport:
    """Lazy import wrapper that imports modules only when accessed."""

    def __init__(self, module_name: str, package: Optional[str] = None):
        self.module_name = module_name
        self.package = package
        self._module = None

    def __getattr__(self, name: str) -> Any:
        if self._module is None:
            try:
                self._module = importlib.import_module(self.module_name, self.package)
            except ImportError as e:
                raise DependencyError(
                    f"Required dependency '{self.module_name}' is not installed. "
                    f"Install it with: pip install {self.module_name}"
                ) from e

        return getattr(self._module, name)


def requires_feature(feature_name: str):
    """
    Decorator that marks a function as requiring a specific feature.
    For now, just passes through - could be extended for feature flags.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator
