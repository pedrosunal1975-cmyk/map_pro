"""
Map Pro Results Saver
====================

Handles saving mapped results to JSON files and database.

Responsibilities:
- Save statements to JSON files
- Save quality reports
- Create database records for mapped statements
- Create mapping session records
"""

import json
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime, timezone

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from core.data_paths import map_pro_paths
from database.models.core_models import Filing
from database.models.parsed_models import ParsedDocument
from database.models.mapped_models import MappedStatement, MappingSession
from shared.exceptions.custom_exceptions import EngineError

logger = get_logger(__name__, 'engine')

# Constants
DEFAULT_CURRENCY = 'USD'
DEFAULT_MAPPER_VERSION = 'map_pro_mapper_v1'
DEFAULT_MAPPING_THRESHOLD = 0.0


class ResultsSaver:
    """
    Saves mapped results to JSON files and database.
    
    Handles:
    - JSON file creation with proper paths
    - Database record creation
    - Error handling for save operations
    """
    
    def __init__(self):
        """Initialize results saver."""
        self.logger = logger
    
    def save_mapped_results(
        self,
        filing_id: str,
        statements: List[Dict[str, Any]],
        quality_report: Dict[str, Any],
        success_metrics: Dict[str, Any],
        parsed_metadata: Dict[str, Any],
        null_quality_report: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Save mapped results to JSON files and database.
        
        Args:
            filing_id: Filing UUID
            statements: List of statement dictionaries
            quality_report: Quality assessment results
            success_metrics: Success calculation results
            parsed_metadata: Original parsed metadata
            null_quality_report: Optional null quality report
            
        Returns:
            Dictionary with save results
        """
        # Get filing information
        filing_info = self._get_filing_information(filing_id)
        
        # Save statements to JSON files
        statement_paths = self._save_statements_to_json(statements, filing_info)
        
        # Save null quality report if provided
        if null_quality_report and statement_paths:
            self._save_null_quality_report(null_quality_report, statement_paths[0])
        
        # Get parsed document ID
        parsed_document_id = self._get_parsed_document_id(filing_id)
        
        if not parsed_document_id:
            self.logger.warning(f"No parsed document found for filing {filing_id}")
            return {'error': 'No parsed document ID found'}
        
        # Save to database
        self._save_to_database(
            filing_id,
            filing_info,
            statements,
            statement_paths,
            quality_report,
            success_metrics,
            parsed_document_id
        )
        
        return {
            'statement_paths': statement_paths,
            'statements_saved': len(statement_paths)
        }
    
    def _get_filing_information(self, filing_id: str) -> Dict[str, Any]:
        """
        Get filing information from database.
        
        Args:
            filing_id: Filing UUID
            
        Returns:
            Dictionary with filing information
            
        Raises:
            EngineError: If filing not found
        """
        with db_coordinator.get_session('core') as session:
            filing = session.query(Filing).filter(
                Filing.filing_universal_id == filing_id
            ).first()
            
            if not filing:
                raise EngineError(f"Filing not found: {filing_id}")
            
            entity = filing.entity
            
            return {
                'entity_universal_id': filing.entity_universal_id,
                'market_type': entity.market_type,
                'entity_name': entity.primary_name.replace('/', '_').replace(' ', '_'),
                'form_type': filing.filing_type,
                'filing_date': filing.filing_date.strftime('%Y-%m-%d') if filing.filing_date else 'unknown',
                'filing_date_obj': filing.filing_date
            }
    
    def _save_statements_to_json(
        self,
        statements: List[Dict[str, Any]],
        filing_info: Dict[str, Any]
    ) -> List[str]:
        """
        Save statements to JSON files.
        
        Args:
            statements: List of statement dictionaries
            filing_info: Filing information dictionary
            
        Returns:
            List of saved file paths
        """
        statement_paths = []
        
        for statement in statements:
            try:
                file_path = self._save_single_statement(statement, filing_info)
                statement_paths.append(str(file_path))
            except Exception as e:
                self.logger.error(f"Failed to save statement: {e}")
        
        return statement_paths
    
    def _save_single_statement(
        self,
        statement: Dict[str, Any],
        filing_info: Dict[str, Any]
    ) -> Path:
        """
        Save a single statement to JSON file.
        
        Args:
            statement: Statement dictionary
            filing_info: Filing information
            
        Returns:
            Path to saved file
        """
        statement_type = statement['statement_type']
        
        # Get file path
        statement_path = map_pro_paths.get_mapped_statement_file_path(
            filing_info['market_type'],
            filing_info['entity_name'],
            filing_info['form_type'],
            filing_info['filing_date'],
            statement_type
        )
        
        # Create directory
        statement_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save JSON
        with open(statement_path, 'w', encoding='utf-8') as f:
            json.dump(statement, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Saved {statement_type}: {statement_path}")
        
        return statement_path
    
    def _save_null_quality_report(
        self,
        null_quality_report: Dict[str, Any],
        first_statement_path: str
    ) -> None:
        """
        Save null quality report to JSON file.
        
        Args:
            null_quality_report: Null quality report dictionary
            first_statement_path: Path to first saved statement (for directory)
        """
        try:
            mapped_dir = Path(first_statement_path).parent
            null_report_path = mapped_dir / "null_quality.json"
            
            with open(null_report_path, 'w', encoding='utf-8') as f:
                json.dump(null_quality_report, f, indent=2, default=str)
            
            self.logger.info(f"Null quality report saved: {null_report_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save null quality report: {e}")
    
    def _get_parsed_document_id(self, filing_id: str) -> int:
        """
        Get parsed document ID for filing.
        
        Args:
            filing_id: Filing UUID
            
        Returns:
            Parsed document ID or None
        """
        try:
            with db_coordinator.get_session('parsed') as session:
                parsed_doc = session.query(ParsedDocument).filter(
                    ParsedDocument.filing_universal_id == filing_id
                ).first()
                
                if parsed_doc:
                    return parsed_doc.parsed_document_id
                
        except Exception as e:
            self.logger.error(f"Failed to get parsed document ID: {e}")
        
        return None
    
    def _save_to_database(
        self,
        filing_id: str,
        filing_info: Dict[str, Any],
        statements: List[Dict[str, Any]],
        statement_paths: List[str],
        quality_report: Dict[str, Any],
        success_metrics: Dict[str, Any],
        parsed_document_id: int
    ) -> None:
        """
        Save results to database.
        
        Args:
            filing_id: Filing UUID
            filing_info: Filing information dictionary
            statements: List of statements
            statement_paths: List of statement file paths
            quality_report: Quality report dictionary
            success_metrics: Success metrics dictionary
            parsed_document_id: Parsed document ID
        """
        with db_coordinator.get_session('mapped') as session:
            # Create mapping session
            mapping_session = self._create_mapping_session(
                filing_info,
                quality_report,
                success_metrics
            )
            
            session.add(mapping_session)
            session.flush()
            
            # Create mapped statement records
            for statement, statement_path in zip(statements, statement_paths):
                mapped_statement = self._create_mapped_statement(
                    filing_id,
                    filing_info,
                    statement,
                    statement_path,
                    quality_report,
                    parsed_document_id,
                    mapping_session.mapping_session_id
                )
                
                session.add(mapped_statement)
            
            session.commit()
            
            self.logger.info(f"Saved {len(statements)} statements to database")
    
    def _create_mapping_session(
        self,
        filing_info: Dict[str, Any],
        quality_report: Dict[str, Any],
        success_metrics: Dict[str, Any]
    ) -> MappingSession:
        """
        Create mapping session database record.
        
        Args:
            filing_info: Filing information
            quality_report: Quality report
            success_metrics: Success metrics
            
        Returns:
            MappingSession instance
        """
        return MappingSession(
            session_name=f"Mapping_{filing_info['filing_date']}",
            mapping_algorithm=DEFAULT_MAPPER_VERSION,
            confidence_threshold=DEFAULT_MAPPING_THRESHOLD,
            facts_successfully_mapped=success_metrics['mapped_facts'],
            facts_failed_mapping=success_metrics['unmapped_facts'],
            average_mapping_confidence=quality_report.get('average_confidence', 0.0),
            session_status='completed',
            completed_at=datetime.now(timezone.utc)
        )
    
    def _create_mapped_statement(
        self,
        filing_id: str,
        filing_info: Dict[str, Any],
        statement: Dict[str, Any],
        statement_path: str,
        quality_report: Dict[str, Any],
        parsed_document_id: int,
        mapping_session_id: int
    ) -> MappedStatement:
        """
        Create mapped statement database record.
        
        Args:
            filing_id: Filing UUID
            filing_info: Filing information
            statement: Statement dictionary
            statement_path: Path to statement JSON file
            quality_report: Quality report
            parsed_document_id: Parsed document ID
            mapping_session_id: Mapping session ID
            
        Returns:
            MappedStatement instance
        """
        statement_facts = statement['facts']
        
        return MappedStatement(
            entity_universal_id=filing_info['entity_universal_id'],
            filing_universal_id=filing_id,
            parsed_document_id=parsed_document_id,
            mapping_session_id=mapping_session_id,
            statement_type=statement['statement_type'],
            reporting_period_start=statement.get('metadata', {}).get('period_start'),
            reporting_period_end=filing_info['filing_date_obj'],
            reporting_currency=statement.get('metadata', {}).get(
                'currency',
                DEFAULT_CURRENCY
            ),
            total_mapped_facts=len([
                f for f in statement_facts if not f.get('is_unmapped')
            ]),
            total_unmapped_facts=len([
                f for f in statement_facts if f.get('is_unmapped')
            ]),
            mapping_confidence_score=quality_report.get('average_confidence', 0.0),
            mapping_status='completed',
            statement_json_path=statement_path,
            mapped_at=datetime.now(timezone.utc),
            mapped_by=DEFAULT_MAPPER_VERSION
        )


__all__ = ['ResultsSaver']