"""
Optimization Applicator
======================

File: tools/maintenance/optimization_applicator.py

Applies optimization recommendations to the system.
"""

from typing import Dict, Any, List
from datetime import datetime, timezone

from core.system_logger import get_logger

from .optimizer_config import OptimizerConfig

logger = get_logger(__name__, 'maintenance')


class OptimizationApplicator:
    """
    Apply optimization recommendations.
    
    Responsibilities:
    - Apply environment variable changes
    - Execute cleanup actions
    - Track applied optimizations
    """
    
    def __init__(self, config: OptimizerConfig):
        """
        Initialize optimization applicator.
        
        Args:
            config: Optimizer configuration
        """
        self.config = config
        self.logger = get_logger(__name__, 'maintenance')
    
    async def apply_safe_optimizations(
        self,
        recommendations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Apply optimizations that are marked as safe for automatic application.
        
        Args:
            recommendations: List of recommendations
            
        Returns:
            List of applied optimizations
        """
        applied = []
        
        for rec in recommendations:
            if not rec.get('auto_applicable', False):
                continue
            
            try:
                applied_items = await self._apply_recommendation(rec)
                applied.extend(applied_items)
            except Exception as e:
                self.logger.error(
                    f"Failed to apply optimization {rec['title']}: {e}"
                )
        
        return applied
    
    async def _apply_recommendation(
        self,
        rec: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Apply a single recommendation.
        
        Args:
            rec: Recommendation dictionary
            
        Returns:
            List of applied optimization details
        """
        applied = []
        
        # Apply environment variable changes
        env_changes = rec.get('env_changes', {})
        if env_changes:
            await self._apply_env_changes(env_changes)
            applied.append({
                'type': rec['type'],
                'title': rec['title'],
                'changes': env_changes,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        
        # Apply cleanup actions
        cleanup_actions = rec.get('cleanup_actions', [])
        if cleanup_actions:
            await self._apply_cleanup_actions(cleanup_actions)
            applied.append({
                'type': rec['type'],
                'title': rec['title'],
                'cleanup_actions': cleanup_actions,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        
        return applied
    
    async def _apply_env_changes(self, env_changes: Dict[str, Any]) -> None:
        """
        Apply environment variable changes.
        
        Note: In a real implementation, this would update the .env file.
        For now, we log what would be changed.
        
        Args:
            env_changes: Dictionary of environment variable changes
        """
        self.logger.info(f"Would apply environment changes: {env_changes}")
        # TODO: Implement .env file modification logic
    
    async def _apply_cleanup_actions(self, cleanup_actions: List[str]) -> None:
        """
        Apply cleanup actions.
        
        Args:
            cleanup_actions: List of cleanup action names
        """
        # Lazy import to avoid circular dependencies
        from tools.maintenance.cleanup_scheduler import CleanupScheduler
        
        cleanup_scheduler = CleanupScheduler()
        
        for action in cleanup_actions:
            await self._execute_cleanup_action(cleanup_scheduler, action)
    
    async def _execute_cleanup_action(
        self,
        cleanup_scheduler,
        action: str
    ) -> None:
        """
        Execute a single cleanup action.
        
        Args:
            cleanup_scheduler: CleanupScheduler instance
            action: Cleanup action name
        """
        action_map = {
            'temp_files': cleanup_scheduler.cleanup_temp_files,
            'old_logs': cleanup_scheduler.cleanup_old_logs,
            'old_downloads': cleanup_scheduler.cleanup_old_downloads
        }
        
        cleanup_func = action_map.get(action)
        if cleanup_func:
            await cleanup_func()
        else:
            self.logger.warning(f"Unknown cleanup action: {action}")