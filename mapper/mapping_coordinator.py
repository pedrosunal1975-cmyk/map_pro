"""
Map Pro Mapping Coordinator
===========================

Main mapping engine - inherits from BaseEngine.
Orchestrates the mapping of parsed facts to taxonomy concepts and builds statements.

Architecture: Universal mapper - market-agnostic fact-to-concept mapping.

Note: Data loading/saving operations extracted to data_loader.py.
Logging operations extracted to mapping_logger.py.
Utility functions extracted to mapping_utils.py.
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timezone
import uuid as uuid_module

from engines.base.engine_base import BaseEngine
from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from core.data_paths import map_pro_paths
from database.models.core_models import Filing, Document
from database.models.parsed_models import ParsedDocument
from database.models.library_models import TaxonomyConcept
from database.models.mapped_models import MappedStatement, MappingSession
from shared.constants.job_constants import JobType, JobStatus
from shared.exceptions.custom_exceptions import EngineError

from .concept_resolver import ConceptResolver
from .fact_matcher import FactMatcher
from .statement_builder import StatementBuilder
from .quality_assessor import QualityAssessor
from .success_calculator import SuccessCalculator
from .data_loader import DataLoader
from .null_value_validator import NullValueValidator
from .mapping_logger import MappingLogger
from .mapping_utils import extract_filing_id_from_job_data
from .analysis.duplicate_detector import DuplicateDetector  # UPDATED PATH


class MappingCoordinator(BaseEngine):
    """
    Universal mapping engine for parsed facts.
    
    Responsibilities:
    - Process mapping jobs from database queue
    - Load parsed facts from JSON files
    - Load taxonomy concepts from library_db
    - Get company XBRL extension files
    - Coordinate concept resolution and fact matching
    - Build financial statements
    - Save mapped results to JSON and database
    
    Does NOT handle:
    - File parsing (parser handles this)
    - Taxonomy downloads (librarian handles this)
    - Market-specific logic (uses universal approach)
    - Detailed logging (mapping_logger handles this)
    - Data extraction utilities (mapping_utils handles this)
    """
    
    def __init__(self):
        """Initialize mapping engine."""
        super().__init__("mapper")
        
        # Initialize components
        self.concept_resolver: Optional[ConceptResolver] = None
        self.fact_matcher: Optional[FactMatcher] = None
        self.statement_builder: Optional[StatementBuilder] = None
        self.quality_assessor: Optional[QualityAssessor] = None
        self.success_calculator: Optional[SuccessCalculator] = None
        self.data_loader: Optional[DataLoader] = None
        self.null_validator: Optional[NullValueValidator] = None
        self.mapping_logger: Optional[MappingLogger] = None
        self.duplicate_detector: Optional[DuplicateDetector] = None
        
        self.logger.info("Mapping coordinator initialized")
    
    def get_primary_database(self) -> str:
        """Return primary database name."""
        return 'mapped'
    
    def get_supported_job_types(self) -> List[str]:
        """Return supported job types."""
        return [JobType.MAP_FACTS.value]
    
    async def process_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process mapping job.
        
        Args:
            job_data: Dictionary containing:
                - filing_universal_id: Filing UUID
                - parsed_document_id: ParsedDocument UUID (optional)
                
        Returns:
            Dictionary with processing results
        """
        filing_id = extract_filing_id_from_job_data(job_data)
        
        if not filing_id:
            self.logger.error(f"Missing filing_universal_id in job data: {job_data}")
            return {'success': False, 'error': 'Missing filing_universal_id in job parameters'}
        
        self.logger.info(f"Processing mapping job for filing {filing_id}")
        
        try:
            # Ensure components are initialized
            if not self.data_loader:
                if not self._engine_specific_initialization():
                    return {'success': False, 'error': 'Failed to initialize mapper components'}
            
            # Execute mapping workflow
            result = self._execute_mapping_workflow(filing_id)
            
            return result
            
        except Exception as e:
            return self._handle_mapping_error(e, filing_id)
    
    def _execute_mapping_workflow(self, filing_id: str) -> Dict[str, Any]:
        """
        Execute the complete mapping workflow.
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            Result dictionary
        """
        # Step 1: Load parsed facts from JSON
        parsed_facts, parsed_metadata = self.data_loader.load_parsed_facts(filing_id)
        
        if not parsed_facts:
            return {'success': False, 'error': 'No parsed facts found'}
        
        # Step 1.5: Detect duplicates in source XBRL (NEW)
        self.logger.info("Analyzing source XBRL for duplicates")
        duplicate_report = self.duplicate_detector.analyze_duplicates(
            parsed_facts=parsed_facts, 
            metadata=parsed_metadata
        )
        
        # Step 2: Load taxonomy and company concepts
        all_concepts = self._load_all_concepts(filing_id)
        
        # Step 3-6: Resolve, match, and build
        resolved_facts = self.concept_resolver.resolve_facts(parsed_facts, all_concepts)
        categorized_facts = self.fact_matcher.match_facts_to_statements(resolved_facts)
        statements = self.statement_builder.build_statements(categorized_facts, parsed_metadata)
        
        # Step 7: Assess quality and validate nulls
        quality_report = self.quality_assessor.assess_quality(resolved_facts, statements)
        null_quality_report = self._validate_null_values(
            resolved_facts, 
            statements, 
            parsed_metadata
        )
        
        # Step 8: Calculate success (now includes duplicate metrics)
        success_metrics = self.success_calculator.calculate_success(
            resolved_facts,
            quality_report,
            duplicate_report  # ADDED
        )
        
        # Step 9: Save results (now includes duplicate report)
        save_result = self._save_results_with_duplicate_report(
            filing_id,
            statements,
            quality_report,
            success_metrics,
            parsed_metadata,
            null_quality_report,
            duplicate_report  # ADDED
        )
        
        # Step 10: Log results (now includes duplicate analysis)
        self._log_mapping_results(
            resolved_facts, 
            success_metrics, 
            null_quality_report,
            duplicate_report  # ADDED
        )
        
        return self._build_success_result(
            filing_id, 
            success_metrics, 
            statements, 
            save_result
        )
    
    def _load_all_concepts(self, filing_id: str) -> List[Dict[str, Any]]:
        """
        Load taxonomy and company extension concepts.
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            Combined list of all concepts
        """
        taxonomy_concepts = self.data_loader.load_taxonomy_concepts(filing_id)
        company_concepts = self.data_loader.load_company_extensions(filing_id)
        
        self.logger.info(
            f"Loaded {len(taxonomy_concepts)} standard + "
            f"{len(company_concepts)} company concepts"
        )
        
        return taxonomy_concepts + company_concepts
    
    def _validate_null_values(
        self,
        resolved_facts: List[Dict[str, Any]],
        statements: List[Dict[str, Any]],
        parsed_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate null values in facts and statements.
        
        Args:
            resolved_facts: List of resolved facts
            statements: List of built statements
            parsed_metadata: Metadata from parsing
            
        Returns:
            Null quality report
        """
        null_validation = self.null_validator.validate_parsed_facts(
            resolved_facts,
            document_metadata=parsed_metadata
        )
        
        null_statement_validation = self.null_validator.validate_mapped_statements(
            statements,
            resolved_facts
        )
        
        null_quality_report = self.null_validator.generate_null_quality_report(
            null_validation,
            null_statement_validation
        )
        
        return null_quality_report
    
    def _save_results_with_duplicate_report(
        self,
        filing_id: str,
        statements: List[Dict[str, Any]],
        quality_report: Dict[str, Any],
        success_metrics: Dict[str, Any],
        parsed_metadata: Dict[str, Any],
        null_quality_report: Dict[str, Any],
        duplicate_report: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Save all mapping results including duplicate report.
        
        Args:
            filing_id: Filing UUID
            statements: Built statements
            quality_report: Quality assessment
            success_metrics: Success metrics
            parsed_metadata: Original metadata
            null_quality_report: Null quality report
            duplicate_report: Duplicate analysis report (NEW)
            
        Returns:
            Save result dictionary
        """
        # Save statements and standard reports
        save_result = self.data_loader.save_mapped_results(
            filing_id,
            statements,
            quality_report,
            success_metrics,
            parsed_metadata,
            null_quality_report
        )
        
        # Save duplicate report (NEW)
        if save_result.get('statement_paths'):
            self._save_duplicate_report(
                duplicate_report,
                save_result['statement_paths'][0]
            )
        
        return save_result
    
    def _save_duplicate_report(
        self,
        duplicate_report: Dict[str, Any],
        first_statement_path: str
    ) -> None:
        """
        Save duplicate analysis report to JSON file.
        
        Args:
            duplicate_report: Duplicate analysis report
            first_statement_path: Path to first saved statement (for directory)
        """
        try:
            mapped_dir = Path(first_statement_path).parent
            duplicate_report_path = mapped_dir / "duplicates.json"
            
            with open(duplicate_report_path, 'w', encoding='utf-8') as f:
                json.dump(duplicate_report, f, indent=2, default=str)
            
            self.logger.info(f"Duplicate analysis report saved: {duplicate_report_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save duplicate report: {e}")
    
    def _log_mapping_results(
        self,
        resolved_facts: List[Dict[str, Any]],
        success_metrics: Dict[str, Any],
        null_quality_report: Dict[str, Any],
        duplicate_report: Dict[str, Any]
    ) -> None:
        """
        Log mapping completion, unmapped facts, null quality, and duplicates.
        
        Args:
            resolved_facts: Resolved facts
            success_metrics: Success metrics
            null_quality_report: Null quality report
            duplicate_report: Duplicate analysis report (NEW)
        """
        self.mapping_logger.log_mapping_completion(success_metrics)
        self.mapping_logger.log_unmapped_facts_details(resolved_facts, success_metrics)
        self.mapping_logger.log_null_quality_report(null_quality_report)
        
        # Log duplicate analysis (NEW)
        # Note: Duplicate logging already happens in duplicate_detector via duplicate_logger_util
        # So we just log a summary here
        if duplicate_report:
            total_groups = duplicate_report.get('total_duplicate_groups', 0)
            duplicate_pct = duplicate_report.get('duplicate_percentage', 0)
            self.logger.info(
                f"Duplicate Analysis: {total_groups} groups ({duplicate_pct}% of facts)"
            )
    
    def _build_success_result(
        self,
        filing_id: str,
        success_metrics: Dict[str, Any],
        statements: List[Dict[str, Any]],
        save_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build success result dictionary.
        
        Args:
            filing_id: Filing universal ID
            success_metrics: Success metrics
            statements: Built statements
            save_result: Save operation result
            
        Returns:
            Success result dictionary
        """
        return {
            'success': True,
            'filing_id': filing_id,
            'total_facts': success_metrics['total_facts'],
            'mapped_facts': success_metrics['mapped_facts'],
            'unmapped_facts': success_metrics['unmapped_facts'],
            'success_rate': success_metrics['success_rate'],
            'statements_created': len(statements),
            'statement_paths': save_result['statement_paths']
        }
    
    def _handle_mapping_error(
        self,
        error: Exception,
        filing_id: str
    ) -> Dict[str, Any]:
        """
        Handle mapping errors.
        
        Args:
            error: Exception that occurred
            filing_id: Filing universal ID
            
        Returns:
            Error result dictionary
        """
        error_msg = f"Mapping error: {str(error)}"
        
        error_report = self.error_handler.handle_engine_processing_error(
            error,
            context={'filing_id': filing_id}
        )
        
        return {
            'success': False, 
            'error': error_msg,
            'error_type': error_report['error_type']
        }
    
    def _engine_specific_initialization(self) -> bool:
        """Initialize mapper-specific components."""
        try:
            self.concept_resolver = ConceptResolver()
            self.fact_matcher = FactMatcher()
            self.statement_builder = StatementBuilder()
            self.quality_assessor = QualityAssessor()
            self.success_calculator = SuccessCalculator()
            self.data_loader = DataLoader()
            self.null_validator = NullValueValidator()
            self.mapping_logger = MappingLogger('mapper')
            self.duplicate_detector = DuplicateDetector()  # ADDED
            
            self.logger.info("Mapper components initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Mapper initialization failed: {e}")
            return False
    
    def _get_engine_specific_status(self) -> Dict[str, Any]:
        """Get mapper-specific status."""
        return {
            'components_initialized': all([
                self.concept_resolver is not None,
                self.fact_matcher is not None,
                self.statement_builder is not None,
                self.quality_assessor is not None,
                self.success_calculator is not None,
                self.data_loader is not None,
                self.null_validator is not None,
                self.mapping_logger is not None,
                self.duplicate_detector is not None
            ])
        }


def create_mapping_engine() -> MappingCoordinator:
    """
    Factory function to create mapping engine.
    
    Returns:
        Initialized MappingCoordinator instance
    """
    return MappingCoordinator()


__all__ = ['MappingCoordinator', 'create_mapping_engine']