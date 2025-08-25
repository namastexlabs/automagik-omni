"""Health monitoring for Discord bot instances."""

import asyncio
import logging
import time
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime, timezone


logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Health status information."""
    instance_name: str
    status: str  # 'healthy', 'degraded', 'unhealthy'
    last_check: datetime
    uptime: float
    error_count: int = 0
    last_error: Optional[str] = None


class HealthMonitor:
    """Monitors Discord bot instance health."""
    
    def __init__(self, instance_name: str, check_interval: int = 30):
        """
        Initialize health monitor.
        
        Args:
            instance_name: Name of the Discord bot instance
            check_interval: Health check interval in seconds
        """
        self.instance_name = instance_name
        self.check_interval = check_interval
        self.start_time = time.time()
        self.last_heartbeat = time.time()
        self.error_count = 0
        self.last_error: Optional[str] = None
        self.status = "starting"
        self.callbacks: Dict[str, Callable] = {}
        self._monitor_task: Optional[asyncio.Task] = None
        self._shutdown = False
    
    def heartbeat(self) -> None:
        """Record a heartbeat to indicate the bot is alive."""
        self.last_heartbeat = time.time()
        if self.status == "starting":
            self.status = "healthy"
    
    def record_error(self, error_message: str) -> None:
        """Record an error occurrence."""
        self.error_count += 1
        self.last_error = error_message
        logger.warning(f"Health monitor recorded error for {self.instance_name}: {error_message}")
    
    def get_status(self) -> HealthStatus:
        """Get current health status."""
        current_time = time.time()
        uptime = current_time - self.start_time
        
        # Determine health status
        time_since_heartbeat = current_time - self.last_heartbeat
        if time_since_heartbeat > 120:  # No heartbeat for 2 minutes
            status = "unhealthy"
        elif time_since_heartbeat > 60 or self.error_count > 10:  # 1 minute or high errors
            status = "degraded"
        else:
            status = "healthy"
        
        return HealthStatus(
            instance_name=self.instance_name,
            status=status,
            last_check=datetime.now(timezone.utc),
            uptime=uptime,
            error_count=self.error_count,
            last_error=self.last_error
        )
    
    def register_callback(self, event: str, callback: Callable) -> None:
        """Register a callback for health events."""
        if event in ['on_healthy', 'on_degraded', 'on_unhealthy']:
            self.callbacks[event] = callback
    
    async def start_monitoring(self) -> None:
        """Start the health monitoring loop."""
        if self._monitor_task and not self._monitor_task.done():
            return  # Already running
        
        self._shutdown = False
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info(f"Health monitoring started for {self.instance_name}")
    
    async def stop_monitoring(self) -> None:
        """Stop the health monitoring loop."""
        self._shutdown = True
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info(f"Health monitoring stopped for {self.instance_name}")
    
    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        previous_status = None
        
        try:
            while not self._shutdown:
                health_status = self.get_status()
                
                # Trigger callbacks on status change
                if health_status.status != previous_status:
                    callback_event = f"on_{health_status.status}"
                    if callback_event in self.callbacks:
                        try:
                            callback = self.callbacks[callback_event]
                            if asyncio.iscoroutinefunction(callback):
                                await callback(health_status)
                            else:
                                callback(health_status)
                        except Exception as e:
                            logger.error(f"Health callback error: {e}")
                    
                    # Only log status changes that indicate problems or recovery
                    if health_status.status in ['degraded', 'unhealthy'] or (previous_status in ['degraded', 'unhealthy'] and health_status.status == 'healthy'):
                        logger.info(f"Health status changed for {self.instance_name}: {previous_status} -> {health_status.status}")
                    else:
                        logger.debug(f"Health status changed for {self.instance_name}: {previous_status} -> {health_status.status}")
                    previous_status = health_status.status
                
                await asyncio.sleep(self.check_interval)
                
        except asyncio.CancelledError:
            logger.info(f"Health monitoring cancelled for {self.instance_name}")
        except Exception as e:
            logger.error(f"Health monitoring error for {self.instance_name}: {e}")
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()