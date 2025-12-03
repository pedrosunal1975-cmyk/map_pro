"""
Map Pro Connection Pool Manager
================================

Manages PostgreSQL connection pool health and automatically cleans up idle connections.
Prevents connection exhaustion by monitoring and terminating stale connections.

Architecture: Integrates with existing maintenance infrastructure
- Works with CleanupScheduler for scheduled execution
- Uses database_coordinator for connection info
- Integrates with system_logger for consistent logging
- Follows Map Pro component patterns

Save location: tools/maintenance/connection_pool_manager.py
"""

import os
import subprocess
from typing import Dict, Any, List
from datetime import datetime, timezone

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator

logger = get_logger(__name__, 'maintenance')


class ConnectionPoolManager:
    """
    PostgreSQL connection pool health manager.
    
    Responsibilities:
    - Monitor connection pool usage across all databases
    - Terminate idle connections to prevent exhaustion
    - Report connection statistics for monitoring
    - Integrate with cleanup scheduler for automated maintenance
    
    Configuration:
    - MAP_PRO_CONNECTION_IDLE_TIMEOUT: Minutes before idle connection cleanup (default: 5)
    - MAP_PRO_CONNECTION_CLEANUP_ENABLED: Enable/disable automatic cleanup (default: true)
    - MAP_PRO_CONNECTION_WARNING_THRESHOLD: Warn if connections exceed this % (default: 80)
    """
    
    def __init__(self):
        """Initialize connection pool manager."""
        # Load configuration from environment
        self.idle_timeout_minutes = int(os.getenv('MAP_PRO_CONNECTION_IDLE_TIMEOUT', '5'))
        self.cleanup_enabled = os.getenv('MAP_PRO_CONNECTION_CLEANUP_ENABLED', 'true').lower() == 'true'
        self.warning_threshold_percent = int(os.getenv('MAP_PRO_CONNECTION_WARNING_THRESHOLD', '80'))
        
        # PostgreSQL connection details (from environment or defaults)
        self.pg_user = os.getenv('POSTGRES_ADMIN_USER', 'postgres')
        self.pg_database = 'postgres'
        
        logger.info("Connection pool manager initialized")
        logger.info(f"Idle timeout: {self.idle_timeout_minutes} minutes")
        logger.info(f"Cleanup enabled: {self.cleanup_enabled}")
        logger.info(f"Warning threshold: {self.warning_threshold_percent}%")
    
    def cleanup_idle_connections(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Clean up idle connections from map_pro_user.
        
        Args:
            dry_run: If True, only report what would be cleaned without actually cleaning
            
        Returns:
            Dictionary with cleanup results
        """
        if not self.cleanup_enabled and not dry_run:
            logger.info("Connection cleanup disabled in configuration")
            return {
                'success': False,
                'reason': 'cleanup_disabled',
                'connections_terminated': 0
            }
        
        try:
            # Get connection stats before cleanup
            stats_before = self.get_connection_stats()
            
            if dry_run:
                logger.info(f"DRY RUN: Would terminate {stats_before.get('idle_connections', 0)} idle connections")
                return {
                    'success': True,
                    'dry_run': True,
                    'connections_would_terminate': stats_before.get('idle_connections', 0),
                    'stats_before': stats_before
                }
            
            # Build PostgreSQL query to terminate idle connections
            query = f"""
            SELECT pg_terminate_backend(pid) 
            FROM pg_stat_activity 
            WHERE usename = 'map_pro_user'
              AND state = 'idle' 
              AND state_change < NOW() - INTERVAL '{self.idle_timeout_minutes} minutes'
              AND pid <> pg_backend_pid();
            """
            
            # Execute termination query
            result = subprocess.run(
                ['psql', '-U', self.pg_user, '-d', self.pg_database, '-t', '-c', query],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to terminate connections: {result.stderr}")
                return {
                    'success': False,
                    'error': result.stderr,
                    'connections_terminated': 0
                }
            
            # Count terminated connections
            output_lines = result.stdout.strip().split('\n')
            terminated_count = sum(1 for line in output_lines if line.strip() == 't')
            
            # Get stats after cleanup
            stats_after = self.get_connection_stats()
            
            logger.info(f"Terminated {terminated_count} idle connections (>{self.idle_timeout_minutes}min)")
            
            return {
                'success': True,
                'connections_terminated': terminated_count,
                'stats_before': stats_before,
                'stats_after': stats_after,
                'idle_timeout_minutes': self.idle_timeout_minutes
            }
            
        except subprocess.TimeoutExpired:
            logger.error("Connection cleanup timed out after 30 seconds")
            return {
                'success': False,
                'error': 'timeout',
                'connections_terminated': 0
            }
        except Exception as e:
            logger.error(f"Error during connection cleanup: {e}")
            return {
                'success': False,
                'error': str(e),
                'connections_terminated': 0
            }
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get current connection pool statistics.
        
        Returns:
            Dictionary with connection statistics
        """
        try:
            # Query to get connection statistics
            query = """
            SELECT 
                COUNT(*) as total_connections,
                COUNT(*) FILTER (WHERE usename = 'map_pro_user') as map_pro_connections,
                COUNT(*) FILTER (WHERE usename = 'map_pro_user' AND state = 'idle') as idle_connections,
                COUNT(*) FILTER (WHERE usename = 'map_pro_user' AND state = 'active') as active_connections,
                (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') as max_connections
            FROM pg_stat_activity;
            """
            
            result = subprocess.run(
                ['psql', '-U', self.pg_user, '-d', self.pg_database, '-t', '-c', query],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to get connection stats: {result.stderr}")
                return {'error': result.stderr}
            
            # Parse output (format: total | map_pro | idle | active | max)
            output = result.stdout.strip()
            parts = [p.strip() for p in output.split('|')]
            
            if len(parts) >= 5:
                total = int(parts[0])
                map_pro = int(parts[1])
                idle = int(parts[2])
                active = int(parts[3])
                max_conn = int(parts[4])
                
                usage_percent = (total / max_conn * 100) if max_conn > 0 else 0
                
                stats = {
                    'total_connections': total,
                    'map_pro_connections': map_pro,
                    'idle_connections': idle,
                    'active_connections': active,
                    'max_connections': max_conn,
                    'usage_percent': round(usage_percent, 1),
                    'available_connections': max_conn - total,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                # Check if we should warn
                if usage_percent >= self.warning_threshold_percent:
                    logger.warning(f"Connection pool usage high: {usage_percent:.1f}% ({total}/{max_conn})")
                    stats['warning'] = f"High connection usage: {usage_percent:.1f}%"
                
                return stats
            else:
                logger.error(f"Unexpected query output format: {output}")
                return {'error': 'parse_error', 'raw_output': output}
                
        except subprocess.TimeoutExpired:
            logger.error("Connection stats query timed out")
            return {'error': 'timeout'}
        except Exception as e:
            logger.error(f"Error getting connection stats: {e}")
            return {'error': str(e)}
    
    def get_detailed_connections(self) -> List[Dict[str, Any]]:
        """
        Get detailed information about all map_pro connections.
        
        Returns:
            List of dictionaries with connection details
        """
        try:
            query = """
            SELECT 
                pid,
                datname as database,
                state,
                query_start,
                state_change,
                EXTRACT(EPOCH FROM (NOW() - state_change))::int as idle_seconds
            FROM pg_stat_activity 
            WHERE usename = 'map_pro_user'
            ORDER BY state_change;
            """
            
            result = subprocess.run(
                ['psql', '-U', self.pg_user, '-d', self.pg_database, '-t', '-c', query],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to get detailed connections: {result.stderr}")
                return []
            
            connections = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 6:
                        connections.append({
                            'pid': int(parts[0]),
                            'database': parts[1],
                            'state': parts[2],
                            'query_start': parts[3],
                            'state_change': parts[4],
                            'idle_seconds': int(parts[5])
                        })
            
            return connections
            
        except Exception as e:
            logger.error(f"Error getting detailed connections: {e}")
            return []
    
    def check_health(self) -> Dict[str, Any]:
        """
        Check connection pool health and return comprehensive status.
        
        Returns:
            Dictionary with health status
        """
        stats = self.get_connection_stats()
        
        if 'error' in stats:
            return {
                'healthy': False,
                'error': stats['error'],
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        
        # Determine health status
        usage_percent = stats.get('usage_percent', 0)
        healthy = usage_percent < self.warning_threshold_percent
        
        health_status = {
            'healthy': healthy,
            'stats': stats,
            'warnings': []
        }
        
        # Add warnings
        if usage_percent >= 90:
            health_status['warnings'].append('CRITICAL: Connection pool nearly exhausted')
        elif usage_percent >= self.warning_threshold_percent:
            health_status['warnings'].append('WARNING: Connection pool usage high')
        
        idle_count = stats.get('idle_connections', 0)
        if idle_count > 20:
            health_status['warnings'].append(f'Many idle connections: {idle_count}')
        
        return health_status


# Export for use in cleanup scheduler and monitoring
__all__ = ['ConnectionPoolManager']