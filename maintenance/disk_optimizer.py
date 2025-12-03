"""
Disk Optimizer
=============

File: tools/maintenance/disk_optimizer.py

Analyzes disk usage and generates optimization recommendations.
"""

from typing import Dict, Any, List

from .optimizer_config import OptimizerConfig


class DiskOptimizer:
    """
    Disk usage optimization analyzer.
    
    Responsibilities:
    - Analyze disk space utilization
    - Identify large directories
    - Generate disk cleanup recommendations
    """
    
    def __init__(self, config: OptimizerConfig):
        """
        Initialize disk optimizer.
        
        Args:
            config: Optimizer configuration
        """
        self.config = config
    
    def analyze(self, analysis_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze disk usage and generate recommendations.
        
        Args:
            analysis_data: System analysis data
            
        Returns:
            List of disk optimization recommendations
        """
        recommendations = []
        system_resources = analysis_data.get('system_resources', {})
        disk_analysis = analysis_data.get('disk_analysis', {})
        
        disk_percent = system_resources.get('disk_percent', 0)
        
        # Check overall disk usage
        if disk_percent > self.config.max_disk_usage_percent:
            recommendations.append(
                self._create_high_disk_usage_recommendation(disk_percent)
            )
        
        # Check for large directories
        large_dir_recs = self._analyze_large_directories(disk_analysis)
        recommendations.extend(large_dir_recs)
        
        return recommendations
    
    def _create_high_disk_usage_recommendation(
        self,
        disk_percent: float
    ) -> Dict[str, Any]:
        """
        Create high disk usage recommendation.
        
        Args:
            disk_percent: Current disk usage percent
            
        Returns:
            Recommendation dictionary
        """
        return {
            'type': 'disk_optimization',
            'priority': 'high',
            'priority_score': 95,
            'title': 'High Disk Usage',
            'description': (
                f'Disk usage is {disk_percent:.1f}%, exceeding threshold of '
                f'{self.config.max_disk_usage_percent}%'
            ),
            'recommendations': [
                'Run cleanup operations immediately',
                'Review log retention policies',
                'Clean temporary files and old downloads',
                'Consider archiving old data'
            ],
            'auto_applicable': True,
            'cleanup_actions': ['temp_files', 'old_logs', 'old_downloads']
        }
    
    def _analyze_large_directories(
        self,
        disk_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Analyze large directories for optimization opportunities.
        
        Args:
            disk_analysis: Disk analysis data
            
        Returns:
            List of large directory recommendations
        """
        recommendations = []
        large_dirs = disk_analysis.get('large_directories', [])
        
        for dir_info in large_dirs:
            size_gb = dir_info.get('size_gb', 0)
            
            if size_gb > self.config.large_directory_threshold_gb:
                recommendations.append(
                    self._create_large_directory_recommendation(dir_info)
                )
        
        return recommendations
    
    def _create_large_directory_recommendation(
        self,
        dir_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create large directory recommendation.
        
        Args:
            dir_info: Directory information
            
        Returns:
            Recommendation dictionary
        """
        return {
            'type': 'disk_optimization',
            'priority': 'medium',
            'priority_score': 60,
            'title': f'Large Directory: {dir_info["path"]}',
            'description': (
                f'Directory {dir_info["path"]} is using {dir_info["size_gb"]:.1f}GB'
            ),
            'recommendations': [
                'Review contents for cleanup opportunities',
                'Consider archiving old files',
                'Implement automated cleanup policies'
            ],
            'auto_applicable': False
        }