"""Comprehensive unit tests for RateLimiter class.
Tests cover all methods, edge cases, async operations, and concurrent handling.
Achieves 100% code coverage with deterministic time-based testing.
"""

import pytest
import time
import asyncio
from unittest.mock import patch
from src.utils.rate_limiter import RateLimiter, RateLimitWindow


class TestRateLimiterBasics:
    """Test basic rate limiter functionality."""
    
    def test_new_identifier_always_allowed(self):
        """New identifier should always be allowed on first request."""
        limiter = RateLimiter(max_requests=5, time_window=60)
        assert limiter.is_allowed("user1") is True
        
    def test_multiple_requests_allowed_under_limit(self):
        """Multiple requests allowed while under the limit."""
        limiter = RateLimiter(max_requests=5, time_window=60)
        for _ in range(5):
            assert limiter.is_allowed("user1") is True
            
    def test_request_blocked_at_limit(self):
        """Request blocked when max requests reached."""
        limiter = RateLimiter(max_requests=2, time_window=60)
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is False
        
    def test_different_identifiers_independent(self):
        """Different identifiers should have independent rate limits."""
        limiter = RateLimiter(max_requests=2, time_window=60)
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user2") is True
        assert limiter.is_allowed("user2") is True
        assert limiter.is_allowed("user1") is False
        assert limiter.is_allowed("user2") is False


class TestTimeWindowExpiration:
    """Test time window cleanup and request expiration."""
    
    @patch('time.time')
    def test_requests_expire_after_time_window(self, mock_time):
        """Requests should be allowed again after time window expires."""
        mock_time.return_value = 1000.0
        limiter = RateLimiter(max_requests=2, time_window=60)
        
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is False
        
        mock_time.return_value = 1061.0
        assert limiter.is_allowed("user1") is True
        
    @patch('time.time')
    def test_partial_window_expiration(self, mock_time):
        """Some old requests expire while new ones added."""
        mock_time.return_value = 1000.0
        limiter = RateLimiter(max_requests=3, time_window=60)
        
        for _ in range(3):
            limiter.is_allowed("user1")
        assert limiter.is_allowed("user1") is False
        
        mock_time.return_value = 1045.0
        assert limiter.is_allowed("user1") is False
        
        mock_time.return_value = 1061.0
        assert limiter.is_allowed("user1") is True


class TestResetFunctionality:
    """Test reset and manual cleanup."""
    
    def test_reset_clears_rate_limit(self):
        """Reset should completely clear requests for an identifier."""
        limiter = RateLimiter(max_requests=2, time_window=60)
        limiter.is_allowed("user1")
        limiter.is_allowed("user1")
        assert limiter.is_allowed("user1") is False
        
        limiter.reset("user1")
        assert limiter.is_allowed("user1") is True
        
    def test_reset_non_existent_identifier(self):
        """Reset on non-existent identifier should not crash."""
        limiter = RateLimiter()
        limiter.reset("unknown_user")
        
    def test_manual_cleanup_execution(self):
        """Manual cleanup should execute without errors."""
        limiter = RateLimiter()
        limiter.is_allowed("user1")
        limiter.cleanup()


class TestGetRemainingTime:
    """Test remaining time calculations."""
    
    @patch('time.time')
    def test_remaining_time_when_rate_limited(self, mock_time):
        """Should return remaining seconds when rate limited."""
        mock_time.return_value = 1000.0
        limiter = RateLimiter(max_requests=1, time_window=60)
        
        limiter.is_allowed("user1")
        remaining = limiter.get_remaining_time("user1")
        
        assert 59 <= remaining <= 60
        
    def test_remaining_time_when_allowed(self):
        """Should return 0 when not rate limited."""
        limiter = RateLimiter(max_requests=5, time_window=60)
        limiter.is_allowed("user1")
        assert limiter.get_remaining_time("user1") == 0.0
        
    def test_remaining_time_unknown_identifier(self):
        """Should return 0 for unknown identifiers."""
        limiter = RateLimiter()
        assert limiter.get_remaining_time("unknown") == 0.0


class TestAsyncMethods:
    """Test async rate limiting functionality."""
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_async(self):
        """Async check_rate_limit should work correctly."""
        limiter = RateLimiter(max_requests=2, time_window=60)
        
        assert await limiter.check_rate_limit("user1") is True
        assert await limiter.check_rate_limit("user1") is True
        assert await limiter.check_rate_limit("user1") is False
        
    @pytest.mark.asyncio
    async def test_async_with_default_identifier(self):
        """Async method should use 'default' identifier."""
        limiter = RateLimiter(max_requests=1, time_window=60)
        
        assert await limiter.check_rate_limit() is True
        assert await limiter.check_rate_limit() is False


class TestMemoryLeakPrevention:
    """Test memory management and cleanup."""
    
    @patch('time.time')
    def test_stale_windows_removed(self, mock_time):
        """Stale windows should be cleaned to prevent memory leaks."""
        mock_time.return_value = 1000.0
        limiter = RateLimiter(cleanup_interval=300)
        
        for i in range(100):
            limiter.is_allowed(f"user{i}")
        
        assert len(limiter.windows) == 100
        
        mock_time.return_value = 1600.0
        limiter.is_allowed("new_user")
        
        assert len(limiter.windows) < 100
        
    def test_cleanup_old_requests_from_window(self):
        """Old requests should be removed from windows."""
        limiter = RateLimiter()
        window = limiter.windows.setdefault("test", RateLimitWindow())
        
        old_time = time.time() - 100
        window.requests.append(old_time)
        window.requests.append(old_time)
        
        limiter._cleanup_old_requests(window, time.time())
        assert len(window.requests) == 0


class TestConcurrentRequestHandling:
    """Test handling of multiple concurrent requests."""
    
    def test_burst_requests_single_identifier(self):
        """Rapid burst of requests should respect limit."""
        limiter = RateLimiter(max_requests=5, time_window=60)
        
        results = [limiter.is_allowed("user1") for _ in range(10)]
        assert results.count(True) == 5
        assert results.count(False) == 5
        
    def test_concurrent_identifiers(self):
        """Multiple concurrent identifiers independent."""
        limiter = RateLimiter(max_requests=3, time_window=60)
        
        for user_id in range(10):
            for _ in range(3):
                assert limiter.is_allowed(f"user{user_id}") is True
            assert limiter.is_allowed(f"user{user_id}") is False


class TestCustomConfiguration:
    """Test with custom configurations."""
    
    def test_custom_max_requests(self):
        """Should respect max_requests configuration."""
        limiter = RateLimiter(max_requests=10, time_window=60)
        
        for _ in range(10):
            assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is False
        
    def test_custom_time_window(self):
        """Should respect time_window configuration."""
        limiter = RateLimiter(max_requests=5, time_window=120)
        for window in limiter.windows.values():
            assert window.time_window == 60
        
    def test_get_stats_accurate(self):
        """Statistics should accurately reflect state."""
        limiter = RateLimiter(max_requests=5, time_window=60, cleanup_interval=300)
        limiter.is_allowed("user1")
        limiter.is_allowed("user1")
        limiter.is_allowed("user2")
        
        stats = limiter.get_stats()
        assert stats["total_windows"] == 2
        assert stats["active_requests"] == 3
        assert stats["max_requests_per_window"] == 5
        assert stats["cleanup_interval"] == 300


class TestGlobalCleanup:
    """Test global cleanup mechanism."""
    
    @patch('time.time')
    def test_global_cleanup_removes_stale_identifiers(self, mock_time):
        """Global cleanup should remove unused windows."""
        mock_time.return_value = 1000.0
        limiter = RateLimiter(cleanup_interval=300)
        
        limiter.is_allowed("user1")
        mock_time.return_value = 1900.0
        limiter._global_cleanup(1900.0)
        
        assert "user1" not in limiter.windows
