"""Optimized rate limiter for Discord bot commands and API calls."""

import time
import asyncio
from collections import deque
from typing import Dict
from dataclasses import dataclass, field


@dataclass
class RateLimitWindow:
    """Represents a rate limiting time window using efficient deque operations."""
    requests: deque = field(default_factory=deque)
    max_requests: int = 5
    time_window: int = 60
    last_cleanup: float = field(default_factory=time.time)


class RateLimiter:
    """Optimized rate limiter with TTL-based cleanup and efficient operations."""
    
    def __init__(self, max_requests: int = 5, time_window: int = 60, cleanup_interval: int = 300):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in time window
            time_window: Time window in seconds
            cleanup_interval: Interval in seconds for background cleanup of stale windows
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.cleanup_interval = cleanup_interval
        self.windows: Dict[str, RateLimitWindow] = {}
        self._last_global_cleanup = time.time()
    
    def _cleanup_old_requests(self, window: RateLimitWindow, current_time: float) -> None:
        """Efficiently remove expired requests from window using deque operations."""
        cutoff_time = current_time - window.time_window
        
        # Use deque's efficient popleft to remove expired requests from the left
        while window.requests and window.requests[0] <= cutoff_time:
            window.requests.popleft()
        
        window.last_cleanup = current_time
    
    def _global_cleanup(self, current_time: float) -> None:
        """Clean up completely stale windows to prevent memory leaks."""
        if current_time - self._last_global_cleanup < self.cleanup_interval:
            return
        
        # Remove windows that haven't been used recently
        stale_identifiers = []
        stale_threshold = current_time - (self.cleanup_interval * 2)
        
        for identifier, window in self.windows.items():
            if window.last_cleanup < stale_threshold and not window.requests:
                stale_identifiers.append(identifier)
        
        for identifier in stale_identifiers:
            del self.windows[identifier]
        
        self._last_global_cleanup = current_time
    
    def is_allowed(self, identifier: str) -> bool:
        """
        Check if request is allowed for given identifier.
        
        Args:
            identifier: Unique identifier (user_id, channel_id, etc.)
            
        Returns:
            True if request is allowed, False if rate limited
        """
        current_time = time.time()
        
        # Periodic global cleanup to prevent memory leaks
        self._global_cleanup(current_time)
        
        # Get or create window for identifier
        if identifier not in self.windows:
            self.windows[identifier] = RateLimitWindow(
                max_requests=self.max_requests,
                time_window=self.time_window,
                last_cleanup=current_time
            )
        
        window = self.windows[identifier]
        
        # Clean old requests using efficient deque operations
        self._cleanup_old_requests(window, current_time)
        
        # Check if under limit
        if len(window.requests) < window.max_requests:
            window.requests.append(current_time)
            return True
        
        return False
    
    async def check_rate_limit(self, identifier: str = "default") -> bool:
        """
        Async version of rate limit check for compatibility with async code.
        
        Args:
            identifier: Unique identifier (user_id, channel_id, etc.)
            
        Returns:
            True if request is allowed, False if rate limited
        """
        # Since rate limiting operations are fast, we can call the sync version
        # But we yield control to allow other coroutines to run
        await asyncio.sleep(0)
        return self.is_allowed(identifier)
    
    def reset(self, identifier: str) -> None:
        """Reset rate limit for identifier."""
        if identifier in self.windows:
            self.windows[identifier].requests.clear()
    
    def get_remaining_time(self, identifier: str) -> float:
        """
        Get remaining time until rate limit resets.
        
        Returns:
            Remaining time in seconds, 0 if not rate limited
        """
        if identifier not in self.windows:
            return 0.0
        
        window = self.windows[identifier]
        if not window.requests:
            return 0.0
        
        # With deque, the leftmost item is the oldest
        oldest_request = window.requests[0]
        remaining = oldest_request + window.time_window - time.time()
        return max(0.0, remaining)
    
    def cleanup(self) -> None:
        """Manually trigger cleanup of all windows."""
        current_time = time.time()
        
        # Clean all active windows
        for window in self.windows.values():
            self._cleanup_old_requests(window, current_time)
        
        # Force global cleanup
        self._last_global_cleanup = 0
        self._global_cleanup(current_time)
    
    def get_stats(self) -> Dict[str, any]:
        """Get rate limiter statistics for monitoring."""
        total_windows = len(self.windows)
        active_requests = sum(len(window.requests) for window in self.windows.values())
        
        return {
            "total_windows": total_windows,
            "active_requests": active_requests,
            "max_requests_per_window": self.max_requests,
            "time_window": self.time_window,
            "cleanup_interval": self.cleanup_interval
        }