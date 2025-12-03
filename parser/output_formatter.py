"""
Map Pro Output Formatter
========================

Creates JSON output files for parsed XBRL facts.
One JSON file per filing containing all extracted data.

Architecture: Universal JSON formatting - works for all markets.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, timezone

from core.system_logger import get_logger
from core.data_paths import map_pro_paths

logger = get_logger(__name__, 'engine')


class OutputFormatter:
    """
    Formats parsed XBRL data as JSON files.
    
    Responsibilities:
    - Create JSON structure with facts/contexts/units
    - Write JSON files to disk
    - Generate appropriate file paths
    
    Does NOT handle:
    - Data extraction (fact_extractor handles this)
    - Database updates (parser_coordinator handles this)
    """
    
    def __init__(self):
        """Initialize output formatter."""
        self.stats = {
            'files_created': 0,
            'total_facts_written': 0
        }
    
    async def create_json_output(
        self,
        filing,
        document,
        facts: List[Dict[str, Any]],
        contexts: List[Dict[str, Any]],
        units: List[Dict[str, Any]]
    ) -> Path:
        """
        Create JSON output file for parsed data.
        
        Args:
            filing: Filing database object
            document: Document database object
            facts: List of extracted facts
            contexts: List of extracted contexts
            units: List of extracted units
            
        Returns:
            Path to created JSON file
            
        Note:
            Ensures file is fully written to disk before returning to prevent
            race conditions with consumers trying to read incomplete files.
        """
        # Generate output path
        json_path = self._generate_json_path(filing, document)
        
        # Ensure directory exists
        json_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create JSON structure
        output_data = {
            'metadata': {
                'filing_id': str(filing.filing_universal_id),
                'document_id': str(document.document_universal_id),
                'company': filing.entity.primary_name if filing.entity else 'Unknown',
                'ticker': filing.entity.ticker_symbol if filing.entity else None,
                'filing_type': filing.filing_type,
                'filing_date': filing.filing_date.isoformat() if filing.filing_date else None,
                'market': filing.entity.market_type if filing.entity else None,
                'parsed_at': datetime.now(timezone.utc).isoformat(),
                'document_name': document.document_name
            },
            'statistics': {
                'total_facts': len(facts),
                'total_contexts': len(contexts),
                'total_units': len(units)
            },
            'facts': facts,
            'contexts': contexts,
            'units': units
        }
        
        # Write JSON file with explicit disk synchronization
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
                f.flush()  # Flush Python's internal buffer to OS
                os.fsync(f.fileno())  # Force OS to write to physical disk
            
            # Verify file was actually created and is readable
            if not json_path.exists():
                raise IOError(f"File creation verification failed: {json_path}")
            
            # Verify file has content (not empty due to write failure)
            if json_path.stat().st_size == 0:
                raise IOError(f"File created but empty: {json_path}")
                
        except Exception as e:
            logger.error(f"Failed to create JSON output at {json_path}: {e}")
            raise
        
        # Update statistics
        self.stats['files_created'] += 1
        self.stats['total_facts_written'] += len(facts)
        
        logger.info(f"Created JSON output: {json_path} ({len(facts)} facts)")
        
        return json_path
    
    def _generate_json_path(self, filing, document) -> Path:
        """
        Generate JSON file path that matches the filing directory structure.
        
        CRITICAL: Must use the same entity identifier that's in the filing_directory_path
        to ensure mapper can find the files.
        
        Args:
            filing: Filing database object
            document: Document database object
            
        Returns:
            Path object for the JSON file
        """
        entity = filing.entity
        if not entity:
            fallback_dir = map_pro_paths.data_parsed_facts / 'unknown'
            fallback_dir.mkdir(parents=True, exist_ok=True)
            return fallback_dir / f"{filing.filing_universal_id}_facts.json"
        
        # CRITICAL FIX: Extract entity_id from filing_directory_path to ensure consistency
        # filing_directory_path format: data/entities/sec/{ENTITY_ID}/filings/{FORM_TYPE}/{ACCESSION}
        # Example: data/entities/sec/Albertsons_Companies__Inc_/filings/10-K/0001646972-25-000052
        
        entity_id = None
        if filing.filing_directory_path:
            try:
                # Split path and extract entity identifier (4th component)
                path_parts = filing.filing_directory_path.split('/')
                if len(path_parts) > 3:
                    entity_id = path_parts[3]
                    logger.debug(f"Extracted entity_id from filing path: {entity_id}")
            except Exception as e:
                logger.warning(f"Failed to extract entity_id from filing path: {e}")
        
        # Fallback to market_entity_id if extraction failed
        if not entity_id:
            entity_id = entity.market_entity_id or str(entity.entity_universal_id)
            logger.warning(
                f"Using fallback entity_id: {entity_id} "
                f"(could not extract from filing_directory_path)"
            )
        
        # Generate other path components
        filing_date = filing.filing_date.strftime('%Y-%m-%d') if filing.filing_date else 'unknown_date'
        instance_name = Path(document.document_name).stem if document.document_name else 'unknown_instance'
        
        # Use centralized path method with extracted entity identifier
        json_path = map_pro_paths.get_parsed_facts_instance_path(
            entity.market_type,
            entity_id,  # Now matches filesystem structure
            filing.filing_type,
            filing_date,
            instance_name
        )
        
        logger.debug(f"Generated JSON path: {json_path}")
        
        return json_path
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get output formatter statistics."""
        return self.stats.copy()


__all__ = ['OutputFormatter']