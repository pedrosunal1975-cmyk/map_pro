"""
Database Schema Verification - Data Models
===========================================

Location: tools/cli/db_check_models.py

Data classes for database diagnostic operations.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class ForeignKeyInfo:
    """Information about a foreign key constraint."""
    constraint_name: str
    column_name: str
    foreign_table: str
    foreign_column: str


@dataclass
class OrphanedJobInfo:
    """Information about an orphaned job."""
    job_id: int
    entity_id: str
    job_type: str
    created_at: str


@dataclass
class JobDebugInfo:
    """Detailed information for job debugging."""
    job_id: int
    job_type: str
    status: str
    entity_id_raw: Optional[str]
    parameters: Dict[str, Any]
    created_at: str


@dataclass
class EntityAnalysis:
    """Results of entity ID analysis."""
    db_column: Optional[str]
    from_parameters: Optional[str]
    param_type: str
    param_valid: bool


@dataclass
class SearcherEngineAnalysis:
    """Results of searcher engine access simulation."""
    from_job_data: Optional[str]
    from_parameters: Optional[str]
    final_entity_id: Optional[str]
    is_truthy: bool