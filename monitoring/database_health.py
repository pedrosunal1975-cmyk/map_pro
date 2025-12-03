"""
Map Pro Database Health Checker
===============================

Monitors health and connectivity of all Map Pro PostgreSQL databases.

Save location: tools/monitoring/database_health.py
"""

import asyncio
from typing import Dict, Any
from sqlalchemy import text
from core.system_logger import get_logger
from core.database_coordinator import db_coordinator

logger = get_logger(__name__, 'monitoring')


class DatabaseHealthChecker:
    """
    Database health monitoring for all Map Pro databases.
    
    Responsibilities:
    - Database connectivity checking
    - Response time monitoring
    - Connection pool health
    
    Does NOT handle:
    - Database operations (database_coordinator handles this)
    - Health remediation (components handle their own recovery)
    """
    
    def __init__(self, response_time_threshold_ms: float = 1000.0):
        self.response_time_threshold_ms = response_time_threshold_ms
        logger.debug("Database health checker initialized")
    
    async def check_all_databases(self) -> Dict[str, Any]:
        """
        Check health of all Map Pro databases.
        
        Returns:
            Dictionary with health status for all databases
        """
        db_health = {
            'overall_healthy': True,
            'issues': [],
            'warnings': [],
            'databases': {}
        }
        
        if not db_coordinator._is_initialized:
            db_health['overall_healthy'] = False
            db_health['issues'].append("Database coordinator not initialized")
            return db_health
        
        try:
            # Check each database
            for db_name in ['core', 'parsed', 'library', 'mapped']:
                db_status = await self.check_single_database(db_name)
                db_health['databases'][db_name] = db_status
                
                if not db_status.get('healthy', False):
                    db_health['overall_healthy'] = False
                    db_health['issues'].append(f"Database {db_name}: {db_status.get('error', 'Unknown issue')}")
                
                # Check response time
                response_time = db_status.get('response_time_ms', 0)
                if response_time > self.response_time_threshold_ms:
                    db_health['warnings'].append(f"Database {db_name} slow response: {response_time}ms")
            
            return db_health
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            db_health['overall_healthy'] = False
            db_health['issues'].append(f"Database health check error: {e}")
            return db_health
    
    async def check_single_database(self, db_name: str) -> Dict[str, Any]:
        """
        Check health of a single database.
        
        Args:
            db_name: Name of database to check
            
        Returns:
            Dictionary with database health status
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            with db_coordinator.get_session(db_name) as session:
                # Simple health check query
                result = session.execute(text("SELECT 1")).fetchone()
                
                end_time = asyncio.get_event_loop().time()
                response_time_ms = (end_time - start_time) * 1000
                
                return {
                    'healthy': result is not None,
                    'response_time_ms': round(response_time_ms, 2),
                    'connection_status': 'connected'
                }
        
        except Exception as e:
            end_time = asyncio.get_event_loop().time()
            response_time_ms = (end_time - start_time) * 1000
            
            return {
                'healthy': False,
                'response_time_ms': round(response_time_ms, 2),
                'connection_status': 'failed',
                'error': str(e)
            }