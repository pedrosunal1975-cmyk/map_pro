"""
Engine Operations.

Engine lifecycle management and control operations.

Location: tools/cli/engine_operations.py
"""

import time
from typing import Dict, Any, List, Optional

from core.system_logger import get_logger
from tools.cli.engine_display import (
    ExitCode,
    EngineDisplay,
    MessageDisplay
)


logger = get_logger(__name__, 'maintenance')


class EngineOperationError(Exception):
    """Base exception for engine operations."""
    pass


class EngineNotFoundError(EngineOperationError):
    """Engine not found."""
    pass


class EngineAlreadyRunningError(EngineOperationError):
    """Engine is already running."""
    pass


class ComponentNotAvailableError(EngineOperationError):
    """Required component not available."""
    pass


class EngineOperations:
    """Engine lifecycle management operations."""
    
    def __init__(self, engines: List[str], component_manager=None, job_orchestrator=None):
        """
        Initialize engine operations.
        
        Args:
            engines: List of valid engine names
            component_manager: Component manager instance (optional)
            job_orchestrator: Job orchestrator instance (optional)
        """
        self.engines = engines
        self.component_manager = component_manager
        self.job_orchestrator = job_orchestrator
        self.logger = logger
        self.display = EngineDisplay()
        self.message = MessageDisplay()
    
    def list_engines(self) -> int:
        """
        List all engines and their status.
        
        Returns:
            Exit code
        """
        try:
            # Get status for all engines
            status_map = {}
            for engine_name in self.engines:
                status_map[engine_name] = self._get_engine_status(engine_name)
            
            # Display
            self.display.print_engine_list(self.engines, status_map)
            
            return ExitCode.SUCCESS
        
        except Exception as e:
            self.logger.error(f"Failed to list engines: {e}", exc_info=True)
            self.message.error(f"Failed to list engines: {e}")
            return ExitCode.ERROR
    
    def show_status(self, engine_name: Optional[str] = None) -> int:
        """
        Show engine status.
        
        Args:
            engine_name: Specific engine name or None for all
            
        Returns:
            Exit code
        """
        try:
            engines_to_check = [engine_name] if engine_name else self.engines
            
            print("\n[STATS] Engine Status:")
            
            for eng_name in engines_to_check:
                self._validate_engine_name(eng_name)
                status = self._get_engine_status(eng_name)
                self.display.print_engine_status(eng_name, status)
            
            return ExitCode.SUCCESS
        
        except EngineNotFoundError as e:
            self.message.error(str(e))
            return ExitCode.ENGINE_NOT_FOUND
        except Exception as e:
            self.logger.error(f"Failed to get engine status: {e}", exc_info=True)
            self.message.error(f"Failed to get engine status: {e}")
            return ExitCode.ERROR
    
    def start_engine(self, engine_name: str, force: bool = False) -> int:
        """
        Start an engine.
        
        Args:
            engine_name: Engine to start
            force: Force start even if already running
            
        Returns:
            Exit code
        """
        try:
            self._validate_engine_name(engine_name)
            self._ensure_component_manager()
            
            print(f"Starting {engine_name} engine...")
            
            # Check if already running
            status = self._get_engine_status(engine_name)
            if status.get('running') and not force:
                self.message.warning(f"{engine_name} is already running. Use --force to restart.")
                return ExitCode.ALREADY_RUNNING
            
            # Start the engine
            self.component_manager.start_engine(engine_name)
            self.message.success(f"{engine_name} started successfully")
            
            return ExitCode.SUCCESS
        
        except EngineNotFoundError as e:
            self.message.error(str(e))
            return ExitCode.ENGINE_NOT_FOUND
        except ComponentNotAvailableError as e:
            self.message.error(str(e))
            self.message.info("Engines can only be started when system is running")
            return ExitCode.NOT_AVAILABLE
        except Exception as e:
            self.logger.error(f"Failed to start {engine_name}: {e}", exc_info=True)
            self.message.error(f"Failed to start {engine_name}: {e}")
            return ExitCode.ERROR
    
    def stop_engine(self, engine_name: str, force: bool = False) -> int:
        """
        Stop an engine.
        
        Args:
            engine_name: Engine to stop
            force: Force stop
            
        Returns:
            Exit code
        """
        try:
            self._validate_engine_name(engine_name)
            self._ensure_component_manager()
            
            print(f"Stopping {engine_name} engine...")
            
            # Stop the engine
            if force:
                self.component_manager.force_stop_engine(engine_name)
                self.message.success(f"{engine_name} force stopped")
            else:
                self.component_manager.stop_engine(engine_name)
                self.message.success(f"{engine_name} stopped gracefully")
            
            return ExitCode.SUCCESS
        
        except EngineNotFoundError as e:
            self.message.error(str(e))
            return ExitCode.ENGINE_NOT_FOUND
        except ComponentNotAvailableError as e:
            self.message.error(str(e))
            return ExitCode.NOT_AVAILABLE
        except Exception as e:
            self.logger.error(f"Failed to stop {engine_name}: {e}", exc_info=True)
            self.message.error(f"Failed to stop {engine_name}: {e}")
            return ExitCode.ERROR
    
    def restart_engine(self, engine_name: str) -> int:
        """
        Restart an engine.
        
        Args:
            engine_name: Engine to restart
            
        Returns:
            Exit code
        """
        try:
            self._validate_engine_name(engine_name)
            
            print(f"Restarting {engine_name} engine...")
            
            # Stop
            stop_result = self.stop_engine(engine_name, force=False)
            if stop_result not in [ExitCode.SUCCESS, ExitCode.NOT_AVAILABLE]:
                return stop_result
            
            # Brief pause
            time.sleep(2)
            
            # Start
            start_result = self.start_engine(engine_name, force=True)
            
            if start_result == ExitCode.SUCCESS:
                self.message.success(f"{engine_name} restarted successfully")
            
            return start_result
        
        except EngineNotFoundError as e:
            self.message.error(str(e))
            return ExitCode.ENGINE_NOT_FOUND
        except Exception as e:
            self.logger.error(f"Failed to restart {engine_name}: {e}", exc_info=True)
            self.message.error(f"Failed to restart {engine_name}: {e}")
            return ExitCode.ERROR
    
    def show_jobs(self, engine_name: str, limit: int) -> int:
        """
        Show jobs for an engine.
        
        Args:
            engine_name: Engine name
            limit: Maximum jobs to show
            
        Returns:
            Exit code
        """
        try:
            self._validate_engine_name(engine_name)
            self._validate_limit(limit)
            self._ensure_job_orchestrator()
            
            # Get jobs
            jobs = self.job_orchestrator.get_engine_jobs(engine_name, limit=limit)
            
            # Display
            self.display.print_jobs(engine_name, jobs, limit)
            
            return ExitCode.SUCCESS
        
        except EngineNotFoundError as e:
            self.message.error(str(e))
            return ExitCode.ENGINE_NOT_FOUND
        except ComponentNotAvailableError as e:
            self.message.error(str(e))
            self.message.info("Jobs can only be viewed when system is running")
            return ExitCode.NOT_AVAILABLE
        except Exception as e:
            self.logger.error(f"Failed to get jobs: {e}", exc_info=True)
            self.message.error(f"Failed to get jobs: {e}")
            return ExitCode.ERROR
    
    def check_health(self, engine_name: Optional[str] = None) -> int:
        """
        Check engine health.
        
        Args:
            engine_name: Specific engine name or None for all
            
        Returns:
            Exit code (0 if all healthy, 1 if issues found)
        """
        try:
            engines_to_check = [engine_name] if engine_name else self.engines
            
            print("\n🏥 Engine Health:")
            
            all_healthy = True
            
            for eng_name in engines_to_check:
                self._validate_engine_name(eng_name)
                health = self._get_engine_health(eng_name)
                self.display.print_health_status(eng_name, health)
                
                if not health.get('healthy', False):
                    all_healthy = False
            
            return ExitCode.SUCCESS if all_healthy else ExitCode.ERROR
        
        except EngineNotFoundError as e:
            self.message.error(str(e))
            return ExitCode.ENGINE_NOT_FOUND
        except Exception as e:
            self.logger.error(f"Health check failed: {e}", exc_info=True)
            self.message.error(f"Health check failed: {e}")
            return ExitCode.ERROR
    
    def show_performance(self, engine_name: Optional[str] = None) -> int:
        """
        Show engine performance metrics.
        
        Args:
            engine_name: Specific engine name or None for all
            
        Returns:
            Exit code
        """
        try:
            engines_to_check = [engine_name] if engine_name else self.engines
            
            print("\n⚡ Engine Performance:")
            
            for eng_name in engines_to_check:
                self._validate_engine_name(eng_name)
                metrics = self._get_engine_performance(eng_name)
                self.display.print_performance_metrics(eng_name, metrics)
            
            return ExitCode.SUCCESS
        
        except EngineNotFoundError as e:
            self.message.error(str(e))
            return ExitCode.ENGINE_NOT_FOUND
        except Exception as e:
            self.logger.error(f"Failed to get performance metrics: {e}", exc_info=True)
            self.message.error(f"Failed to get performance metrics: {e}")
            return ExitCode.ERROR
    
    # ========================================================================
    # Validation Methods
    # ========================================================================
    
    def _validate_engine_name(self, engine_name: str) -> None:
        """
        Validate engine name.
        
        Args:
            engine_name: Engine name to validate
            
        Raises:
            EngineNotFoundError: If engine not found
        """
        if engine_name not in self.engines:
            raise EngineNotFoundError(f"Unknown engine: {engine_name}")
    
    def _validate_limit(self, limit: int) -> None:
        """
        Validate limit parameter.
        
        Args:
            limit: Limit value to validate
            
        Raises:
            ValueError: If limit is invalid
        """
        if limit < 1:
            raise ValueError("Limit must be positive")
        if limit > 1000:
            raise ValueError("Limit cannot exceed 1000")
    
    def _ensure_component_manager(self) -> None:
        """
        Ensure component manager is available.
        
        Raises:
            ComponentNotAvailableError: If component manager not available
        """
        if not self.component_manager:
            raise ComponentNotAvailableError("Component manager not available")
    
    def _ensure_job_orchestrator(self) -> None:
        """
        Ensure job orchestrator is available.
        
        Raises:
            ComponentNotAvailableError: If job orchestrator not available
        """
        if not self.job_orchestrator:
            raise ComponentNotAvailableError("Job orchestrator not available")
    
    # ========================================================================
    # Internal Helper Methods
    # ========================================================================
    
    def _get_engine_status(self, engine_name: str) -> Dict[str, Any]:
        """
        Get engine status.
        
        Args:
            engine_name: Engine name
            
        Returns:
            Status dictionary
        """
        try:
            if self.component_manager:
                return self.component_manager.get_engine_status(engine_name)
            else:
                return {
                    'running': False,
                    'status': 'unavailable',
                    'active_jobs': 0,
                    'completed_jobs': 0,
                    'failed_jobs': 0
                }
        except Exception as e:
            self.logger.error(f"Error getting status for {engine_name}: {e}")
            return {
                'running': False,
                'status': 'error',
                'active_jobs': 0,
                'completed_jobs': 0,
                'failed_jobs': 0
            }
    
    def _get_engine_health(self, engine_name: str) -> Dict[str, Any]:
        """
        Get engine health.
        
        Args:
            engine_name: Engine name
            
        Returns:
            Health dictionary
        """
        try:
            status = self._get_engine_status(engine_name)
            
            # Basic health check
            failed_jobs = status.get('failed_jobs', 0)
            running = status.get('running', False)
            
            healthy = running and failed_jobs < 10
            
            issues = []
            if not running:
                issues.append("Engine not running")
            if failed_jobs >= 10:
                issues.append(f"High failure rate: {failed_jobs} failed jobs")
            
            return {
                'healthy': healthy,
                'status': 'healthy' if healthy else 'degraded',
                'issues': issues
            }
        except Exception as e:
            return {
                'healthy': False,
                'status': 'error',
                'issues': [str(e)]
            }
    
    def _get_engine_performance(self, engine_name: str) -> Dict[str, Any]:
        """
        Get engine performance metrics.
        
        Args:
            engine_name: Engine name
            
        Returns:
            Performance metrics dictionary
        """
        try:
            # Placeholder - would integrate with actual performance tracking
            return {
                'throughput': 0,
                'avg_time': 0.0,
                'success_rate': 0.0
            }
        except Exception as e:
            self.logger.error(f"Error getting performance for {engine_name}: {e}")
            return {
                'throughput': 0,
                'avg_time': 0.0,
                'success_rate': 0.0,
                'error': str(e)
            }


__all__ = [
    'EngineOperations',
    'EngineOperationError',
    'EngineNotFoundError',
    'EngineAlreadyRunningError',
    'ComponentNotAvailableError'
]