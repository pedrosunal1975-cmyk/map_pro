# File: /map_pro/core/database_connectivity_validator.py

"""
Database Connectivity Validator
================================

Validates database connectivity and health.

Responsibility: Database validation only.
"""

from typing import Dict, Any

from core.system_logger import get_logger
from core.database_coordinator import check_database_health

from .validation_constants import (
    STATUS_PASS,
    STATUS_FAIL,
    STATUS_ERROR,
    KEY_STATUS,
    KEY_DETAILS,
    KEY_ERROR,
    KEY_DATABASE_HEALTH,
    DB_STATUS_HEALTHY,
    DETAIL_COORDINATOR_ERROR,
    DETAIL_UNHEALTHY_DBS,
    DETAIL_ALL_DBS_HEALTHY,
    MSG_COORDINATOR_NOT_INITIALIZED
)

logger = get_logger(__name__, 'core')


class DatabaseConnectivityValidator:
    """
    Validates database connectivity and health.
    
    Responsibility: Database connectivity and health validation.
    """
    
    def __init__(self):
        """Initialize database connectivity validator."""
        logger.debug("Database connectivity validator initialized")
    
    def validate_database_connectivity(self) -> Dict[str, Any]:
        """
        Validate database connectivity and health.
        
        Returns:
            Validation result dictionary with status and details
        """
        result = self._create_base_result()
        
        try:
            health_status = check_database_health()
            
            # Check coordinator initialization
            if not self._is_coordinator_initialized(health_status):
                self._mark_coordinator_failure(result)
                return result
            
            # Check individual database health
            databases = health_status.get('databases', {})
            unhealthy_databases = self._find_unhealthy_databases(databases, result)
            
            if unhealthy_databases:
                result[KEY_STATUS] = STATUS_FAIL
                result[KEY_DETAILS][DETAIL_UNHEALTHY_DBS] = unhealthy_databases
            else:
                result[KEY_DETAILS][DETAIL_ALL_DBS_HEALTHY] = True
                
        except Exception as e:
            result[KEY_STATUS] = STATUS_ERROR
            result[KEY_ERROR] = str(e)
            logger.error(f"Database connectivity validation error: {e}")
        
        return result
    
    def is_database_healthy(self) -> bool:
        """
        Quick check if database is healthy.
        
        Returns:
            True if database is healthy, False otherwise
        """
        try:
            health_status = check_database_health()
            
            if not health_status.get('coordinator_initialized', False):
                return False
            
            databases = health_status.get('databases', {})
            for db_status in databases.values():
                if db_status.get('status') != DB_STATUS_HEALTHY:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Database health check error: {e}")
            return False
    
    # ========================================================================
    # PRIVATE VALIDATION METHODS
    # ========================================================================
    
    def _create_base_result(self) -> Dict[str, Any]:
        """Create base result structure."""
        return {
            KEY_STATUS: STATUS_PASS,
            KEY_DATABASE_HEALTH: {},
            KEY_DETAILS: {}
        }
    
    def _is_coordinator_initialized(self, health_status: Dict[str, Any]) -> bool:
        """Check if database coordinator is initialized."""
        return health_status.get('coordinator_initialized', False)
    
    def _mark_coordinator_failure(self, result: Dict[str, Any]) -> None:
        """Mark coordinator initialization failure."""
        result[KEY_STATUS] = STATUS_FAIL
        result[KEY_DETAILS][DETAIL_COORDINATOR_ERROR] = MSG_COORDINATOR_NOT_INITIALIZED
    
    def _find_unhealthy_databases(
        self,
        databases: Dict[str, Dict[str, Any]],
        result: Dict[str, Any]
    ) -> list:
        """
        Find unhealthy databases and update result.
        
        Args:
            databases: Database status dictionary
            result: Result dictionary to update
            
        Returns:
            List of unhealthy database names
        """
        unhealthy_databases = []
        
        for db_name, db_status in databases.items():
            status = db_status.get('status', 'unknown')
            result[KEY_DATABASE_HEALTH][db_name] = status
            
            if status != DB_STATUS_HEALTHY:
                unhealthy_databases.append(db_name)
        
        return unhealthy_databases