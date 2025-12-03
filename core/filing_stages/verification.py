# File: /map_pro/core/filing_stages/verification.py

"""
Output Verification
==================

Verifies that stage outputs actually exist on filesystem.
Provides reality checks beyond database status.

Responsibilities:
- Verify parsed facts files exist
- Verify mapped statement files exist
- Reality check for database status
"""

import json
from typing import Optional
from pathlib import Path

from core.system_logger import get_logger
from core.data_paths import map_pro_paths

logger = get_logger(__name__, 'core')

# Constants
METADATA_READ_SIZE = 3000
CONTENT_READ_SIZE = 2000


class OutputVerifier:
    """
    Verifies stage outputs exist on filesystem.
    
    Provides reality checks to catch database/filesystem inconsistencies.
    """
    
    def __init__(self):
        """Initialize output verifier."""
        self.logger = logger
    
    def verify_parsing_output(self, filing_id: str) -> bool:
        """
        Verify that parsed facts JSON file exists for filing.
        
        Args:
            filing_id: Filing UUID
            
        Returns:
            True if facts.json file exists with facts
        """
        try:
            parsed_facts_root = map_pro_paths.data_parsed_facts
            
            if not parsed_facts_root.exists():
                self.logger.debug(f"Parsed facts directory missing: {parsed_facts_root}")
                return False
            
            # Search for facts.json files
            for json_file in parsed_facts_root.rglob("facts.json"):
                if self._verify_facts_file_for_filing(json_file, filing_id):
                    return True
            
            self.logger.debug(f"No facts.json found for filing {filing_id}")
            return False
            
        except Exception as e:
            self.logger.warning(f"Parse verification failed for {filing_id}: {e}")
            return False
    
    def _verify_facts_file_for_filing(
        self,
        json_file: Path,
        filing_id: str
    ) -> bool:
        """
        Verify a specific facts file contains the filing.
        
        Args:
            json_file: Path to facts.json file
            filing_id: Filing UUID to verify
            
        Returns:
            True if file contains facts for this filing
        """
        try:
            # Quick check: is filing_id in first part of file?
            with open(json_file, 'r', encoding='utf-8') as f:
                content = f.read(METADATA_READ_SIZE)
                
                if filing_id not in content:
                    return False
                
                # Full verification: load and check
                f.seek(0)
                data = json.load(f)
                
                metadata = data.get('metadata', {})
                file_filing_id = metadata.get('filing_id')
                
                if file_filing_id == filing_id:
                    facts = data.get('facts', [])
                    if len(facts) > 0:
                        self.logger.info(
                            f"[REALITY CHECK] Parse output verified: "
                            f"{json_file} ({len(facts)} facts)"
                        )
                        return True
            
            return False
            
        except json.JSONDecodeError as e:
            self.logger.debug(f"Invalid JSON in {json_file}: {e}")
            return False
        except Exception as e:
            self.logger.debug(f"Error reading {json_file}: {e}")
            return False
    
    def verify_mapping_output(self, filing_id: str) -> bool:
        """
        Verify that mapped statement JSON files exist for filing.
        
        Args:
            filing_id: Filing UUID
            
        Returns:
            True if statement files exist
        """
        try:
            mapped_statements_root = map_pro_paths.data_mapped_statements
            
            if not mapped_statements_root.exists():
                self.logger.debug(
                    f"Mapped statements directory missing: {mapped_statements_root}"
                )
                return False
            
            statement_files = self._find_statement_files(
                mapped_statements_root,
                filing_id
            )
            
            if statement_files:
                self.logger.info(
                    f"[REALITY CHECK] Mapping output verified: "
                    f"{len(statement_files)} statement files found"
                )
                return True
            
            self.logger.debug(f"No statement files found for filing {filing_id}")
            return False
            
        except Exception as e:
            self.logger.warning(f"Mapping verification failed for {filing_id}: {e}")
            return False
    
    def _find_statement_files(
        self,
        search_root: Path,
        filing_id: str
    ) -> list:
        """
        Find statement files for filing.
        
        Args:
            search_root: Root directory to search
            filing_id: Filing UUID
            
        Returns:
            List of statement file paths
        """
        statement_files = []
        
        for json_file in search_root.rglob("*.json"):
            try:
                # Skip null quality reports
                if 'null_quality' in json_file.name:
                    continue
                
                # Check if file contains filing_id
                if self._file_contains_filing(json_file, filing_id):
                    statement_files.append(json_file)
                    
            except Exception as e:
                self.logger.debug(f"Error checking {json_file}: {e}")
                continue
        
        return statement_files
    
    def _file_contains_filing(self, json_file: Path, filing_id: str) -> bool:
        """
        Check if file contains filing_id.
        
        Args:
            json_file: Path to JSON file
            filing_id: Filing UUID to check for
            
        Returns:
            True if filing_id found in file
        """
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                content = f.read(CONTENT_READ_SIZE)
                return filing_id in content
        except Exception:
            return False


__all__ = ['OutputVerifier']