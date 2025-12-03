"""
Health Check Configuration
=========================

File: tools/health_check_config.py

Configuration for database health check operations.
"""

from dataclasses import dataclass
from pathlib import Path

from core.data_paths import map_pro_paths


@dataclass
class HealthCheckConfig:
    """
    Configuration for health check operations.
    
    Centralizes paths and settings for health checks.
    """
    
    # Filesystem paths
    data_root: Path = None
    parsed_facts_root: Path = None
    mapped_statements_root: Path = None
    
    # Check options
    max_report_items: int = 5  # Max items to show in report summaries
    
    # Repair options
    create_missing_records: bool = True
    delete_phantom_records: bool = True
    update_path_mismatches: bool = True
    
    def __post_init__(self):
        """Initialize paths if not provided."""
        if self.data_root is None:
            self.data_root = map_pro_paths.data_root
        
        if self.parsed_facts_root is None:
            self.parsed_facts_root = map_pro_paths.data_parsed_facts
        
        if self.mapped_statements_root is None:
            self.mapped_statements_root = map_pro_paths.data_mapped_statements
    
    def validate_paths(self) -> bool:
        """
        Validate that configured paths are accessible.
        
        Returns:
            True if all paths are valid
        """
        return (
            self.data_root.exists() and
            self.parsed_facts_root.exists() and
            self.mapped_statements_root.exists()
        )