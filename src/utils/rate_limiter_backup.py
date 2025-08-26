"""Rate limiter for Discord bot commands and API calls."""
import time
from typing import Dict, List
from dataclasses import dataclass, field
@dataclass
class RateLimitWindow:
    """Represents a rate limiting time window."""
    requests: List[float] = field(default_factory=list)
    max_requests: int = 5
    time_window: int = 60
class RateLimiter:
    """Simple rate limiter for Discord bot operations."""
    
    def __init__(self, max_requests: int = 5, time_window: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.windows: Dict[str, RateLimitWindow] = {}
    
    def is_allowed(self, identifier: str) -> bool:
        """
        Check if request is allowed for given identifier.
        
        Args:
            identifier: Unique identifier (user_id, channel_id, etc.)
            
        Returns:
            True if request is allowed, False if rate limited
        """
        current_time = time.time()
        
        # Get or create window for identifier
        if identifier not in self.windows:
            self.windows[identifier] = RateLimitWindow(
                max_requests=self.max_requests,
                time_window=self.time_window
            )
        
        window = self.windows[identifier]
        
        # Clean old requests outside time window
        cutoff_time = current_time - window.time_window
        window.requests = [req_time for req_time in window.requests if req_time > cutoff_time]
        
        # Check if under limit
        if len(window.requests) < window.max_requests:
            window.requests.append(current_time)
            return True
        
        return False
    
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
        
        oldest_request = min(window.requests)
        remaining = oldest_request + window.time_window - time.time()
        return max(0.0, remaining)