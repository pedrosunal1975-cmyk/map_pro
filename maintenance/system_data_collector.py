"""
System Data Collector
====================

File: tools/maintenance/system_data_collector.py

Collects system data for optimization analysis.
"""

import psutil
from typing import Dict, Any
from datetime import datetime, timezone
from pathlib import Path

from core.system_logger import get_logger
from core.data_paths import map_pro_paths

logger = get_logger(__name__, 'maintenance')


class SystemDataCollector:
    """
    Collect system data for optimization.
    
    Responsibilities:
    - Collect system resource metrics
    - Gather database metrics
    - Collect performance analysis data
    - Analyze disk usage patterns
    """
    
    def __init__(self, performance_analyzer, system_monitor):
        """
        Initialize data collector.
        
        Args:
            performance_analyzer: PerformanceAnalyzer instance
            system_monitor: SystemMonitor instance
        """
        self.performance_analyzer = performance_analyzer
        self.system_monitor = system_monitor
        self.logger = get_logger(__name__, 'maintenance')
    
    async def collect(self) -> Dict[str, Any]:
        """
        Collect all optimization data.
        
        Returns:
            Dictionary with collected data
        """
        self.logger.debug("Collecting optimization data")
        
        return {
            'system_resources': self._collect_system_resources(),
            'database_metrics': await self._collect_database_metrics(),
            'performance_analysis': await self._collect_performance_analysis(),
            'queue_metrics': await self._collect_queue_metrics(),
            'disk_analysis': await self._collect_disk_analysis(),
            'collection_timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def _collect_system_resources(self) -> Dict[str, Any]:
        """
        Collect system resource metrics.
        
        Returns:
            Dictionary with resource metrics
        """
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(str(map_pro_paths.data_root))
        cpu_percent = psutil.cpu_percent(interval=1)
        
        return {
            'memory_percent': memory.percent,
            'memory_total_gb': round(memory.total / (1024**3), 2),
            'memory_available_gb': round(memory.available / (1024**3), 2),
            'disk_percent': round((disk.used / disk.total) * 100, 2),
            'disk_total_gb': round(disk.total / (1024**3), 2),
            'disk_free_gb': round(disk.free / (1024**3), 2),
            'cpu_percent': cpu_percent
        }
    
    async def _collect_database_metrics(self) -> Dict[str, Any]:
        """
        Collect database metrics.
        
        Returns:
            Dictionary with database metrics
        """
        return await self.system_monitor._collect_database_metrics()
    
    async def _collect_performance_analysis(self) -> Dict[str, Any]:
        """
        Collect performance analysis data.
        
        Returns:
            Dictionary with performance data
        """
        return await self.performance_analyzer.analyze_system_performance()
    
    async def _collect_queue_metrics(self) -> Dict[str, Any]:
        """
        Collect job queue metrics.
        
        Returns:
            Dictionary with queue metrics
        """
        return await self.system_monitor._collect_queue_metrics()
    
    async def _collect_disk_analysis(self) -> Dict[str, Any]:
        """
        Analyze disk usage patterns.
        
        Returns:
            Dictionary with disk analysis
        """
        try:
            disk_analysis = {
                'large_directories': [],
                'analysis_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Analyze major directories
            directories_to_check = [
                map_pro_paths.data_root,
                map_pro_paths.logs_root,
                map_pro_paths.data_entities,
                map_pro_paths.data_parsed_facts,
                map_pro_paths.data_mapped_statements
            ]
            
            for directory in directories_to_check:
                if directory.exists():
                    dir_info = self._analyze_directory(directory)
                    disk_analysis['large_directories'].append(dir_info)
            
            return disk_analysis
            
        except Exception as e:
            self.logger.error(f"Failed to analyze disk usage: {e}")
            return {'error': str(e)}
    
    def _analyze_directory(self, directory: Path) -> Dict[str, Any]:
        """
        Analyze a single directory.
        
        Args:
            directory: Directory path to analyze
            
        Returns:
            Dictionary with directory information
        """
        size_bytes = sum(
            f.stat().st_size for f in directory.rglob('*') if f.is_file()
        )
        size_gb = size_bytes / (1024**3)
        
        return {
            'path': str(directory),
            'size_gb': round(size_gb, 2),
            'size_bytes': size_bytes
        }