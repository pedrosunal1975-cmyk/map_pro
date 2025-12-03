"""
Map Pro Central Path Authority
=============================

This file is the single source of truth for ALL file system paths in Map Pro.
No other file should contain hardcoded paths. All path operations must go through this module.

Changing paths here allows easy system migration to different computers/environments.
Paths are configured via environment variables in .env file.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
# Look for .env in the project root (parent directory of this file)
_env_file = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_env_file, interpolate=True)


class MapProPaths:
    """Central path management for Map Pro system."""
    
    def __init__(self, custom_data_root: Optional[Path] = None, custom_program_root: Optional[Path] = None):
        """Initialize paths from .env file or custom values."""
        # Get paths from environment variables (required)
        data_root_env = os.getenv('MAP_PRO_DATA_ROOT')
        program_root_env = os.getenv('MAP_PRO_PROGRAM_ROOT')
        
        # Validate required environment variables
        if not custom_data_root and not data_root_env:
            raise ValueError(
                "MAP_PRO_DATA_ROOT must be set in .env file. "
                "Example: MAP_PRO_DATA_ROOT=/mnt/map_pro"
            )
        
        if not custom_program_root and not program_root_env:
            raise ValueError(
                "MAP_PRO_PROGRAM_ROOT must be set in .env file. "
                "Example: MAP_PRO_PROGRAM_ROOT=/home/user/map_pro"
            )
        
        # Set paths
        self.data_root = custom_data_root or Path(data_root_env)
        self.program_root = custom_program_root or Path(program_root_env)
        
        # Initialize all path structures
        self._initialize_data_paths()
        self._initialize_program_paths()
    
    def _initialize_data_paths(self):
        """Initialize all data partition paths."""
        # Main data directories
        self.data_entities = self.data_root / "data" / "entities"
        self.data_parsed_facts = self.data_root / "data" / "parsed_facts"
        self.data_taxonomies = self.data_root / "data" / "taxonomies"
        self.data_mapped_statements = self.data_root / "data" / "mapped_statements"
        self.data_temp = self.data_root / "data" / "temp"
        
        # Database directories
        self.databases_root = self.data_root / "databases"
        self.postgresql_data = self.databases_root / "postgresql_data"
        self.database_backups = self.databases_root / "backups"
        
        # Configuration directories
        self.config_root = self.data_root / "config"
        self.config_system = self.config_root / "system"
        self.config_markets = self.config_root / "markets"
        self.config_taxonomies = self.config_root / "taxonomies"
        self.config_integrations = self.config_root / "integrations"
        
        # Logging directories
        self.logs_root = self.data_root / "logs"
        self.logs_engines = self.logs_root / "engines"
        self.logs_integrations = self.logs_root / "integrations"
        self.logs_system = self.logs_root / "system"
        self.logs_alerts = self.logs_root / "alerts"
        
        # Output directories
        self.outputs_root = self.data_root / "outputs"
        self.outputs_reports = self.outputs_root / "reports"
        self.outputs_exports = self.outputs_root / "exports"
        self.outputs_integration_ready = self.outputs_root / "integration_ready"
    
    def _initialize_program_paths(self):
        """Initialize all program partition paths."""
        # Core program directories
        self.core = self.program_root / "core"
        self.engines = self.program_root / "engines"
        self.markets = self.program_root / "markets"
        self.database = self.program_root / "database"
        self.integrations = self.program_root / "integrations"
        self.shared = self.program_root / "shared"
        self.tests = self.program_root / "tests"
        self.tools = self.program_root / "tools"
        self.arelle_integration = self.program_root / "arelle_integration"
        self.docs = self.program_root / "docs"
    
    def get_entity_data_path(self, market_type: str, entity_id: str) -> Path:
        """Get entity-specific data directory path."""
        return self.data_entities / market_type / entity_id 

    def get_entity_file_path(self, market_type: str, entity_id: str) -> Path:
        """Get entity metadata file path."""
        return self.data_entities / market_type / f"{entity_id}.json"
    
    def get_entity_filings_path(self, market_type: str, entity_id: str) -> Path:
        """Get entity filings directory path."""
        return self.data_entities / market_type / entity_id / "filings"
    
    def get_raw_downloads_path(self, market_type: str, entity_id: str) -> Path:
        """Get raw downloads directory path."""
        return self.get_entity_filings_path(market_type, entity_id) / "raw_downloads"
    
    def get_extracted_files_path(self, market_type: str, entity_id: str) -> Path:
        """Get extracted files directory path."""
        return self.get_entity_filings_path(market_type, entity_id) / "extracted_files"
    
    def get_parsed_facts_path(self, market_type: str, entity_id: str, form_type: str) -> Path:
        """Get parsed facts directory path."""
        return self.data_parsed_facts / market_type / entity_id / form_type
    
    def get_parsed_facts_file_path(self, market_type: str, entity_id: str, form_type: str, filing_date: str) -> Path:
        """Get specific parsed facts file path."""
        return self.get_parsed_facts_path(market_type, entity_id, form_type) / f"{filing_date}_facts.json"

    def get_parsed_facts_instance_path(self, market_type: str, entity_id: str, form_type: str, 
                                    filing_date: str, instance_name: str) -> Path:
        """Get specific parsed facts file path for an XBRL instance."""
        return (self.get_parsed_facts_path(market_type, entity_id, form_type) / 
                filing_date / 
                instance_name / 
                'facts.json')
    
    def get_mapped_statements_path(self, market_type: str, entity_id: str, form_type: str) -> Path:
        """Get mapped statements directory path."""
        return self.data_mapped_statements / market_type / entity_id / form_type
    
    def get_mapped_statement_file_path(self, market_type: str, entity_id: str, form_type: str, 
                                      filing_date: str, statement_type: str) -> Path:
        """Get specific mapped statement file path."""
        return (self.get_mapped_statements_path(market_type, entity_id, form_type) / 
                filing_date / 
                f"{statement_type}.json")
    
    def get_taxonomy_library_path(self, library_name: str) -> Path:
        """Get taxonomy library directory path."""
        return self.data_taxonomies / "libraries" / library_name
    
    def get_engine_log_path(self, engine_name: str) -> Path:
        """Get engine-specific log directory path."""
        return self.logs_engines / engine_name
    
    def get_temp_workspace_path(self, workspace_type: str) -> Path:
        """Get temporary workspace directory path."""
        return self.data_temp / f"{workspace_type}_workspace"
    
    def ensure_data_directories(self):
        """Create all necessary data directories if they don't exist."""
        directories_to_create = [
            self.data_entities, self.data_parsed_facts, self.data_taxonomies,
            self.data_mapped_statements, self.data_temp, self.postgresql_data,
            self.database_backups, self.config_system, self.config_markets,
            self.config_taxonomies, self.config_integrations, self.logs_engines,
            self.logs_integrations, self.logs_system, self.logs_alerts,
            self.outputs_reports, self.outputs_exports, self.outputs_integration_ready
        ]
        
        for directory in directories_to_create:
            directory.mkdir(parents=True, exist_ok=True)


# Global instance for system-wide use
map_pro_paths = MapProPaths()