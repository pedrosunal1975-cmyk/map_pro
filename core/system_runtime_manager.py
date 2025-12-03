# File: /map_pro/core/system_runtime_manager.py

"""
System Runtime Manager
======================

Manages system runtime operations including the main loop, health monitoring,
and graceful shutdown coordination.

Responsibilities:
- Main system operation loop
- Periodic health checks
- Component health monitoring
- Graceful shutdown coordination
- Signal handling
"""

import signal
import asyncio
from typing import Dict, Any
from datetime import datetime, timezone

from .system_logger import get_logger
from .database_coordinator import db_coordinator
from .component_manager import ComponentManager
from tools.monitoring.health_checker import SystemHealthChecker

logger = get_logger(__name__, 'core')

# Runtime configuration constants
HEALTH_CHECK_INTERVAL_SECONDS = 300  # 5 minutes
MAIN_LOOP_SLEEP_SECONDS = 10


class SystemRuntimeManager:
    """
    Manages system runtime operations.
    
    Handles:
    - Main operation loop
    - Periodic health monitoring
    - Component failure recovery
    - Graceful shutdown
    - Signal handling
    """
    
    def __init__(
        self,
        component_manager: ComponentManager,
        health_checker: SystemHealthChecker
    ):
        """
        Initialize runtime manager.
        
        Args:
            component_manager: Component lifecycle manager
            health_checker: System health monitoring service
        """
        self.component_manager = component_manager
        self.health_checker = health_checker
        
        # Runtime state
        self.is_running = False
        self.start_time = None
        self.shutdown_requested = False
        self.last_health_check = None
        
        logger.debug("System runtime manager created")
    
    async def start_system(self) -> bool:
        """
        Start the system and all components.
        
        Returns:
            True if startup successful, False otherwise
        """
        logger.info("Starting Map Pro system components")
        
        try:
            # Setup signal handlers
            self._setup_signal_handlers()
            
            # Start all registered components
            if not await self.component_manager.start_components():
                logger.error("Failed to start system components")
                return False
            
            # Perform initial health check with startup mode
            await self._perform_initial_health_check()
            
            # Mark system as running
            self.is_running = True
            self.start_time = datetime.now(timezone.utc)
            
            logger.info("Map Pro system started successfully")
            return True
            
        except Exception as e:
            logger.error(f"System startup failed: {e}")
            return False
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown")
            self.shutdown_requested = True
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.debug("Signal handlers configured")
    
    async def _perform_initial_health_check(self) -> None:
        """
        Perform initial health check after startup.
        
        Uses startup_mode=True to apply relaxed criteria appropriate for
        a system that has just started and may not have stabilized yet.
        """
        try:
            # Use startup mode for initial check
            health_status = await self.health_checker.perform_health_check(startup_mode=True)
            
            if not health_status.get('overall_healthy', False):
                logger.warning("Initial health check detected critical issues")
                issues = health_status.get('issues', [])
                for issue in issues:
                    logger.warning(f"Critical startup issue: {issue}")
            else:
                logger.info("Initial health check passed - system ready")
                
        except Exception as e:
            logger.error(f"Initial health check failed: {e}")
    
    async def run_main_loop(self) -> None:
        """
        Main system operation loop.
        
        Monitors health and handles events while system is running.
        """
        logger.info("Entering main system operation loop")
        
        last_health_check = 0
        
        try:
            while self.is_running and not self.shutdown_requested:
                current_time = asyncio.get_event_loop().time()
                
                # Periodic health checks
                if self._should_perform_health_check(current_time, last_health_check):
                    await self._perform_periodic_health_check()
                    last_health_check = current_time
                
                # Check component health
                await self._check_component_health()
                
                # Sleep to prevent busy waiting
                await asyncio.sleep(MAIN_LOOP_SLEEP_SECONDS)
                
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            self.shutdown_requested = True
        
        logger.info("Main system loop ended")
    
    def _should_perform_health_check(
        self,
        current_time: float,
        last_check_time: float
    ) -> bool:
        """
        Check if periodic health check should be performed.
        
        Args:
            current_time: Current time
            last_check_time: Time of last health check
            
        Returns:
            True if health check should be performed
        """
        elapsed = current_time - last_check_time
        return elapsed >= HEALTH_CHECK_INTERVAL_SECONDS
    
    async def _perform_periodic_health_check(self) -> None:
        """
        Perform periodic system health check.
        
        Uses standard production thresholds (startup_mode=False).
        """
        try:
            # Use production mode for periodic checks
            health_status = await self.health_checker.perform_health_check(startup_mode=False)
            self.last_health_check = datetime.now(timezone.utc)
            
            if not health_status.get('overall_healthy', False):
                issues = health_status.get('issues', [])
                logger.warning(f"Health check detected issues: {issues}")
            else:
                logger.debug("Periodic health check passed")
                
        except Exception as e:
            logger.error(f"Periodic health check failed: {e}")
    
    async def _check_component_health(self) -> None:
        """
        Check health of individual components and attempt recovery.
        
        For critical components that are unhealthy, attempts automatic restart.
        """
        try:
            component_health = self.component_manager.check_component_health()
            
            for component_name, health_status in component_health.items():
                if not health_status.get('healthy', True):
                    logger.warning(
                        f"Component {component_name} health issues: "
                        f"{health_status}"
                    )
                    
                    # Attempt recovery for critical components
                    if health_status.get('critical', False):
                        await self._attempt_component_recovery(component_name)
                        
        except Exception as e:
            logger.error(f"Component health check failed: {e}")
    
    async def _attempt_component_recovery(self, component_name: str) -> None:
        """
        Attempt to recover a failed component.
        
        Args:
            component_name: Name of component to recover
        """
        try:
            logger.info(f"Attempting automatic recovery for: {component_name}")
            await self.component_manager.restart_component(component_name)
            logger.info(f"Component {component_name} restarted successfully")
            
        except Exception as e:
            logger.error(
                f"Failed to recover component {component_name}: {e}"
            )
    
    async def shutdown_system(self) -> bool:
        """
        Gracefully shutdown the system.
        
        Returns:
            True if shutdown successful, False otherwise
        """
        logger.info("Starting Map Pro system shutdown")
        
        self.shutdown_requested = True
        
        try:
            # Stop all components in reverse order
            await self.component_manager.stop_components()
            
            # Shutdown database coordinator
            if db_coordinator._is_initialized:
                db_coordinator.shutdown()
            
            # Calculate uptime
            uptime = self._calculate_uptime()
            
            # Mark system as stopped
            self.is_running = False
            
            logger.info(
                f"Map Pro system shutdown completed. "
                f"Uptime: {uptime:.1f} seconds"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error during system shutdown: {e}")
            return False
    
    def _calculate_uptime(self) -> float:
        """
        Calculate system uptime in seconds.
        
        Returns:
            Uptime in seconds
        """
        if self.start_time is None:
            return 0.0
        
        uptime_delta = datetime.now(timezone.utc) - self.start_time
        return uptime_delta.total_seconds()
    
    def get_runtime_status(self) -> Dict[str, Any]:
        """
        Get current runtime status.
        
        Returns:
            Dictionary with runtime status information
        """
        return {
            'is_running': self.is_running,
            'start_time': (
                self.start_time.isoformat() if self.start_time else None
            ),
            'uptime_seconds': self._calculate_uptime(),
            'shutdown_requested': self.shutdown_requested,
            'last_health_check': (
                self.last_health_check.isoformat() 
                if self.last_health_check else None
            )
        }


__all__ = ['SystemRuntimeManager']