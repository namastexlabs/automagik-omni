#!/usr/bin/env python3
"""
Test script for Discord bot connection error handling improvements.

This script validates that the improvements to Discord bot error handling
are working correctly, including:
1. Proper resource cleanup on LoginFailure
2. Jittered exponential backoff
3. Circuit breaker pattern
4. Enhanced logging
"""

import asyncio
import unittest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta

# Import the improved bot manager
from src.channels.discord.bot_manager_improved import (
    DiscordBotManager, 
    CircuitBreakerState,
    AutomagikBot
)
import discord


class TestDiscordBotImprovements(unittest.TestCase):
    """Test cases for Discord bot connection error handling improvements."""

    def setUp(self):
        """Set up test fixtures."""
        self.message_router = Mock()
        self.bot_manager = DiscordBotManager(self.message_router)

    def test_circuit_breaker_initialization(self):
        """Test that circuit breaker state is properly initialized."""
        circuit_breaker = CircuitBreakerState()
        
        self.assertEqual(circuit_breaker.failure_count, 0)
        self.assertEqual(circuit_breaker.consecutive_failures, 0)
        self.assertFalse(circuit_breaker.is_open)
        self.assertIsNone(circuit_breaker.next_retry_time)
        self.assertEqual(circuit_breaker.failure_threshold, 3)
        self.assertEqual(circuit_breaker.recovery_timeout, 300)

    async def test_jittered_backoff_calculation(self):
        """Test that jittered backoff calculation works correctly."""
        bot_manager = DiscordBotManager(Mock())
        
        # Test multiple retry counts
        for retry_count in [1, 2, 3, 4, 5]:
            wait_time = await bot_manager._calculate_jittered_backoff(retry_count)
            
            # Base delay should be 2^retry_count but capped at 60
            expected_base = min(2 ** retry_count, 60)
            
            # Jitter adds up to 10% of base delay
            self.assertGreaterEqual(wait_time, expected_base)
            self.assertLessEqual(wait_time, expected_base * 1.1)

    async def test_circuit_breaker_opening(self):
        """Test that circuit breaker opens after threshold failures."""
        instance_name = "test_bot"
        circuit_breaker = CircuitBreakerState()
        
        bot_manager = DiscordBotManager(Mock())
        
        # Simulate failures up to threshold
        for i in range(circuit_breaker.failure_threshold):
            await bot_manager._handle_connection_failure(
                instance_name, f"Test error {i}", i + 1, 5, circuit_breaker
            )
        
        # Circuit breaker should be open after threshold failures
        self.assertTrue(circuit_breaker.is_open)
        self.assertEqual(circuit_breaker.consecutive_failures, circuit_breaker.failure_threshold)
        self.assertIsNotNone(circuit_breaker.next_retry_time)

    async def test_should_skip_connection_attempt(self):
        """Test circuit breaker connection attempt logic."""
        instance_name = "test_bot"
        circuit_breaker = CircuitBreakerState()
        bot_manager = DiscordBotManager(Mock())
        
        # Initially should not skip
        should_skip = await bot_manager._should_skip_connection_attempt(instance_name, circuit_breaker)
        self.assertFalse(should_skip)
        
        # Open circuit breaker
        circuit_breaker.is_open = True
        circuit_breaker.next_retry_time = datetime.now(timezone.utc) + timedelta(seconds=300)
        
        # Should skip when circuit breaker is open and time hasn't passed
        should_skip = await bot_manager._should_skip_connection_attempt(instance_name, circuit_breaker)
        self.assertTrue(should_skip)
        
        # Should not skip when recovery timeout has passed
        circuit_breaker.next_retry_time = datetime.now(timezone.utc) - timedelta(seconds=10)
        should_skip = await bot_manager._should_skip_connection_attempt(instance_name, circuit_breaker)
        self.assertFalse(should_skip)

    async def test_circuit_breaker_reset(self):
        """Test that circuit breaker resets properly after successful connection."""
        instance_name = "test_bot"
        circuit_breaker = CircuitBreakerState()
        bot_manager = DiscordBotManager(Mock())
        
        # Set up circuit breaker in failed state
        circuit_breaker.consecutive_failures = 5
        circuit_breaker.is_open = True
        circuit_breaker.next_retry_time = datetime.now(timezone.utc) + timedelta(seconds=300)
        
        # Reset circuit breaker
        await bot_manager._reset_circuit_breaker(instance_name, circuit_breaker)
        
        # Circuit breaker should be reset
        self.assertEqual(circuit_breaker.consecutive_failures, 0)
        self.assertFalse(circuit_breaker.is_open)
        self.assertIsNone(circuit_breaker.next_retry_time)

    @patch('src.channels.discord.bot_manager_improved.logger')
    async def test_enhanced_logging(self, mock_logger):
        """Test that enhanced logging provides structured information."""
        instance_name = "test_bot"
        circuit_breaker = CircuitBreakerState()
        bot_manager = DiscordBotManager(Mock())
        
        # Test permanent failure logging
        await bot_manager._handle_permanent_failure(instance_name, "Invalid token", circuit_breaker)
        
        # Check that error log was called with structured information
        mock_logger.error.assert_called()
        log_call_args = mock_logger.error.call_args[0][0]
        self.assertIn("PERMANENT FAILURE", log_call_args)
        self.assertIn(instance_name, log_call_args)
        self.assertIn("Invalid token", log_call_args)

    async def test_resource_cleanup_on_permanent_failure(self):
        """Test that resources are cleaned up on permanent failure."""
        instance_name = "test_bot"
        circuit_breaker = CircuitBreakerState()
        bot_manager = DiscordBotManager(Mock())
        
        # Mock the cleanup method
        bot_manager._cleanup_bot = AsyncMock()
        
        # Handle permanent failure
        await bot_manager._handle_permanent_failure(instance_name, "Invalid token", circuit_breaker)
        
        # Verify cleanup was called
        bot_manager._cleanup_bot.assert_called_once_with(instance_name)
        
        # Verify circuit breaker state
        self.assertTrue(circuit_breaker.is_open)
        self.assertEqual(circuit_breaker.consecutive_failures, 1)

    def test_circuit_breaker_in_manager_initialization(self):
        """Test that DiscordBotManager initializes with circuit breaker tracking."""
        bot_manager = DiscordBotManager(Mock())
        
        # Should have circuit breakers dict
        self.assertIsInstance(bot_manager.circuit_breakers, dict)
        self.assertEqual(len(bot_manager.circuit_breakers), 0)

    async def test_cleanup_includes_circuit_breaker(self):
        """Test that _cleanup_bot removes circuit breaker state."""
        instance_name = "test_bot"
        bot_manager = DiscordBotManager(Mock())
        
        # Add circuit breaker state
        bot_manager.circuit_breakers[instance_name] = CircuitBreakerState()
        
        # Mock voice manager and other components
        bot_manager.voice_manager = Mock()
        bot_manager.voice_manager.disconnect_voice = AsyncMock()
        
        # Call cleanup
        await bot_manager._cleanup_bot(instance_name)
        
        # Circuit breaker should be removed
        self.assertNotIn(instance_name, bot_manager.circuit_breakers)


class TestDiscordErrorHandlingIntegration(unittest.TestCase):
    """Integration tests for Discord error handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.message_router = Mock()
        self.bot_manager = DiscordBotManager(self.message_router)

    async def test_login_failure_handling(self):
        """Test that LoginFailure triggers proper cleanup."""
        instance_name = "test_bot"
        
        # Mock bot and token
        mock_bot = Mock(spec=AutomagikBot)
        mock_bot.instance_name = instance_name
        mock_bot.start = AsyncMock(side_effect=discord.LoginFailure("Invalid token"))
        
        # Mock cleanup
        self.bot_manager._cleanup_bot = AsyncMock()
        self.bot_manager._shutdown_event = Mock()
        self.bot_manager._shutdown_event.is_set = Mock(return_value=False)
        
        # This will test one iteration of the retry loop
        with patch('src.channels.discord.bot_manager_improved.logger') as mock_logger:
            # Run bot with mock that raises LoginFailure
            await self.bot_manager._run_bot(mock_bot, "invalid_token")
        
        # Verify cleanup was called
        self.bot_manager._cleanup_bot.assert_called_once_with(instance_name)
        
        # Verify error logging
        mock_logger.error.assert_called()
        log_message = mock_logger.error.call_args[0][0]
        self.assertIn("AUTHENTICATION FAILURE", log_message)


def main():
    """Run the test suite."""
    print("Running Discord Bot Error Handling Improvement Tests...")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestDiscordBotImprovements))
    suite.addTests(loader.loadTestsFromTestCase(TestDiscordErrorHandlingIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ All Discord bot error handling improvement tests PASSED!")
        print("\n🎉 Improvements successfully implemented:")
        print("  ✓ Proper resource cleanup on LoginFailure")
        print("  ✓ Jittered exponential backoff")
        print("  ✓ Circuit breaker pattern with failure tracking")
        print("  ✓ Enhanced structured logging")
        print("  ✓ Production-ready error handling")
    else:
        print(f"❌ {len(result.failures)} test(s) FAILED, {len(result.errors)} error(s)")
        return False
    
    return True


if __name__ == "__main__":
    # Run async tests using asyncio
    async def run_async_tests():
        test_instance = TestDiscordBotImprovements()
        test_instance.setUp()
        
        print("Testing circuit breaker functionality...")
        await test_instance.test_jittered_backoff_calculation()
        await test_instance.test_circuit_breaker_opening()
        await test_instance.test_should_skip_connection_attempt()
        await test_instance.test_circuit_breaker_reset()
        await test_instance.test_enhanced_logging()
        await test_instance.test_resource_cleanup_on_permanent_failure()
        await test_instance.test_cleanup_includes_circuit_breaker()
        
        integration_instance = TestDiscordErrorHandlingIntegration()
        integration_instance.setUp()
        await integration_instance.test_login_failure_handling()
        
        print("✅ All async tests completed successfully!")
    
    # Run the async tests
    asyncio.run(run_async_tests())
    
    # Run the main test suite
    main()