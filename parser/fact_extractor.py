"""
Map Pro Fact Extractor.

Main entry point for XBRL fact extraction that delegates to specialized extractors.

Extracts XBRL facts from Arelle models in a universal, market-agnostic way.
Combines comprehensive extraction with robust error handling.

Architecture:
    Universal fact extraction - works for all XBRL markets.
    Delegates to specialized components:
    - fact_value_extractor.py - Value extraction and cleaning
    - fact_concept_extractor.py - Concept information extraction
    - fact_context_extractor.py - Context reference extraction
    - fact_unit_extractor.py - Unit reference extraction
    - fact_attribute_extractor.py - Attribute extraction (decimals, precision, etc.)
    - fact_validator.py - Fact validation

Location: /engines/parser/fact_extractor.py

Example:
    >>> from engines.parser.fact_extractor import FactExtractor
    >>> extractor = FactExtractor()
    >>> facts = extractor.extract_facts(model_xbrl, document_id)
"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from core.system_logger import get_logger

# Arelle imports
try:
    from arelle.ModelXbrl import ModelXbrl
    from arelle.ModelInstanceObject import ModelFact
    ARELLE_AVAILABLE = True
except ImportError:
    ARELLE_AVAILABLE = False
    ModelXbrl = None
    ModelFact = None

# Import specialized extractors
from .fact_value_extractor import ValueExtractor
from .fact_concept_extractor import ConceptExtractor
from .fact_context_extractor import ContextExtractor
from .fact_unit_extractor import UnitExtractor
from .fact_attribute_extractor import AttributeExtractor
from .fact_validator import FactValidator
from .fact_utils import extract_numeric_value


logger = get_logger(__name__, 'engine')


class ExtractionStatistics:
    """
    Tracks fact extraction statistics.
    
    Attributes:
        facts_extracted: Total facts successfully extracted
        facts_with_values: Facts with non-empty values
        facts_nil: Facts marked as nil
        facts_skipped: Facts skipped due to errors or validation
    """
    
    def __init__(self):
        """Initialize statistics."""
        self.facts_extracted = 0
        self.facts_with_values = 0
        self.facts_nil = 0
        self.facts_skipped = 0
    
    def increment_extracted(self) -> None:
        """Increment extracted count."""
        self.facts_extracted += 1
    
    def increment_with_value(self) -> None:
        """Increment facts with values count."""
        self.facts_with_values += 1
    
    def increment_nil(self) -> None:
        """Increment nil facts count."""
        self.facts_nil += 1
    
    def increment_skipped(self) -> None:
        """Increment skipped facts count."""
        self.facts_skipped += 1
    
    def to_dict(self) -> Dict[str, int]:
        """
        Convert statistics to dictionary.
        
        Returns:
            Statistics dictionary
        """
        return {
            'facts_extracted': self.facts_extracted,
            'facts_with_values': self.facts_with_values,
            'facts_nil': self.facts_nil,
            'facts_skipped': self.facts_skipped
        }
    
    def reset(self) -> None:
        """Reset all statistics to zero."""
        self.facts_extracted = 0
        self.facts_with_values = 0
        self.facts_nil = 0
        self.facts_skipped = 0


class FactExtractor:
    """
    Main fact extractor that coordinates specialized extraction components.
    
    Responsibilities:
    - Coordinate fact extraction process
    - Validate input models
    - Track extraction statistics
    - Assemble complete fact dictionaries
    - Pass rich error context to all extractors
    
    Does NOT Handle:
    - Context processing (context_processor handles this)
    - Output formatting (output_formatter handles this)
    - Validation (validation_engine handles this)
    
    Example:
        >>> extractor = FactExtractor()
        >>> facts = extractor.extract_facts(model_xbrl, 'doc-uuid-123')
        >>> stats = extractor.get_statistics()
        >>> print(f"Extracted {stats['facts_extracted']} facts")
    """
    
    def __init__(self):
        """Initialize fact extractor with all specialized components."""
        self.logger = logger
        
        # Initialize specialized extractors
        self.value_extractor = ValueExtractor()
        self.concept_extractor = ConceptExtractor()
        self.context_extractor = ContextExtractor()
        self.unit_extractor = UnitExtractor()
        self.attribute_extractor = AttributeExtractor()
        self.validator = FactValidator()
        
        # Statistics tracking
        self.stats = ExtractionStatistics()
    
    def extract_facts(
        self,
        model_xbrl: ModelXbrl,
        document_id: str
    ) -> List[Dict[str, Any]]:
        """
        Extract all facts from XBRL model.
        
        Process:
        1. Validate model
        2. Iterate through facts
        3. Extract each fact using specialized components with rich error context
        4. Validate extracted facts
        5. Return fact list
        
        Args:
            model_xbrl: Arelle ModelXbrl instance
            document_id: Document universal ID (filing_id)
            
        Returns:
            List of fact dictionaries
            
        Example:
            >>> facts = extractor.extract_facts(model_xbrl, 'doc-123')
            >>> print(f"Extracted {len(facts)} facts")
        """
        # Validate input
        validation_error = self._validate_model_xbrl(model_xbrl)
        if validation_error:
            self.logger.error(validation_error)
            return []
        
        facts_list = []
        total_facts = len(model_xbrl.facts)
        
        self.logger.info(f"Starting fact extraction from {total_facts} facts")
        
        # Process each fact with rich context
        for i, arelle_fact in enumerate(model_xbrl.facts):
            fact_dict = self._process_single_fact(
                arelle_fact,
                document_id,
                i,
                total_facts  # Pass total for context
            )
            if fact_dict:
                facts_list.append(fact_dict)
        
        self._log_extraction_summary()
        
        return facts_list
    
    def _validate_model_xbrl(self, model_xbrl: ModelXbrl) -> Optional[str]:
        """
        Validate ModelXbrl instance.
        
        Args:
            model_xbrl: ModelXbrl to validate
            
        Returns:
            Error message if invalid, None if valid
        """
        if not model_xbrl:
            return "Cannot extract facts: model_xbrl is None"
        
        if not hasattr(model_xbrl, 'facts'):
            return "model_xbrl does not have facts attribute"
        
        return None
    
    def _process_single_fact(
        self,
        arelle_fact,
        document_id: str,
        index: int,
        total_facts: int
    ) -> Optional[Dict[str, Any]]:
        """
        Process a single fact with error handling and validation.
        
        Args:
            arelle_fact: Arelle ModelFact instance
            document_id: Document universal ID (filing_id)
            index: Fact index for logging
            total_facts: Total number of facts for context
            
        Returns:
            Fact dictionary or None if extraction failed
        """
        try:
            # Extract fact with rich error context
            fact_dict = self._extract_single_fact(arelle_fact, document_id, index, total_facts)
            
            # Validate
            if fact_dict and self.validator.validate(fact_dict, index):
                self._update_statistics(fact_dict)
                return fact_dict
            else:
                self.stats.increment_skipped()
                return None
        
        except Exception as e:
            # Rich error context for catastrophic failures
            error_context = self._build_error_context(
                filing_id=document_id,
                fact_index=index,
                total_facts=total_facts,
                concept_name="EXTRACTION_FAILED",
                error_message=str(e)
            )
            self.logger.error(f"[ERROR] Catastrophic fact extraction failure | {error_context}", exc_info=True)
            self.stats.increment_skipped()
            return None
    
    def _extract_single_fact(
        self,
        arelle_fact,
        document_id: str,
        index: int,
        total_facts: int
    ) -> Optional[Dict[str, Any]]:
        """
        Extract single fact using specialized extractors with rich error context.
        
        Args:
            arelle_fact: Arelle ModelFact instance
            document_id: Document universal ID (filing_id)
            index: Fact index for logging
            total_facts: Total number of facts for context
            
        Returns:
            Complete fact dictionary or None if extraction failed
        """
        # Create base fact dictionary
        fact_dict = self._create_base_fact_dict(document_id, index)
        
        # Extract concept information (critical - must succeed)
        # Pass rich context to concept extractor
        concept_info = self.concept_extractor.extract(
            arelle_fact,
            index=index,
            filing_id=document_id,
            total_facts=total_facts
        )
        if not concept_info:
            return None
        
        fact_dict.update(concept_info)
        
        # Extract all other attributes with rich context
        fact_dict.update(self._extract_all_attributes(
            arelle_fact,
            document_id,
            index,
            total_facts,
            concept_info.get('concept_local_name', 'UNKNOWN')
        ))
        
        return fact_dict
    
    def _create_base_fact_dict(
        self,
        document_id: str,
        index: int
    ) -> Dict[str, Any]:
        """
        Create base fact dictionary with required fields.
        
        Args:
            document_id: Document universal ID
            index: Fact index
            
        Returns:
            Base fact dictionary with IDs and timestamps
        """
        return {
            'fact_id': str(uuid.uuid4()),
            'document_universal_id': document_id,
            'fact_index': index,
            'extracted_at': datetime.now(timezone.utc).isoformat()
        }
    
    def _extract_all_attributes(
        self,
        arelle_fact,
        filing_id: str,
        fact_index: int,
        total_facts: int,
        concept_name: str
    ) -> Dict[str, Any]:
        """
        Extract all fact attributes using specialized extractors with rich error context.
        
        Args:
            arelle_fact: Arelle fact object
            filing_id: Filing ID for error context
            fact_index: Fact index for error context
            total_facts: Total facts for error context
            concept_name: Concept name for error context
            
        Returns:
            Dictionary with all extracted attributes
        """
        return {
            # Value (no context needed - ValueExtractor doesn't have errors that need context)
            'fact_value': self.value_extractor.extract(arelle_fact),
            
            # Context reference with rich error context
            'context_ref': self.context_extractor.extract(
                arelle_fact,
                filing_id=filing_id,
                fact_index=fact_index,
                total_facts=total_facts,
                concept_name=concept_name
            ),
            
            # Unit reference with rich error context
            'unit_ref': self.unit_extractor.extract(
                arelle_fact,
                filing_id=filing_id,
                fact_index=fact_index,
                total_facts=total_facts,
                concept_name=concept_name
            ),
            
            # Attributes with rich error context
            **self.attribute_extractor.extract(
                arelle_fact,
                filing_id=filing_id,
                fact_index=fact_index,
                total_facts=total_facts,
                concept_name=concept_name
            )
        }
    
    def _update_statistics(self, fact_dict: Dict[str, Any]) -> None:
        """
        Update statistics after successful extraction.
        
        Args:
            fact_dict: Extracted fact dictionary
        """
        self.stats.increment_extracted()
        
        if fact_dict.get('fact_value'):
            self.stats.increment_with_value()
        
        if fact_dict.get('is_nil'):
            self.stats.increment_nil()
    
    def _log_extraction_summary(self) -> None:
        """Log extraction summary."""
        self.logger.info(
            f"Fact extraction completed: {self.stats.facts_extracted} extracted, "
            f"{self.stats.facts_skipped} skipped"
        )
    
    def _build_error_context(
        self,
        filing_id: str,
        fact_index: int,
        total_facts: int,
        concept_name: str,
        error_message: str
    ) -> str:
        """
        Build rich error context string.
        
        Args:
            filing_id: Filing ID
            fact_index: Current fact index
            total_facts: Total facts count
            concept_name: Concept name
            error_message: Error description
            
        Returns:
            Formatted error context string
        """
        filing_str = f"Filing: {filing_id[:8]}..." if filing_id else "Filing: UNKNOWN"
        fact_str = f"Fact: {fact_index + 1}/{total_facts}"
        
        return (
            f"{filing_str} | "
            f"{fact_str} | "
            f"Concept: {concept_name} | "
            f"Reason: {error_message}"
        )
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get extraction statistics.
        
        Returns:
            Dictionary with extraction statistics
        """
        return self.stats.to_dict()
    
    def reset_statistics(self) -> None:
        """Reset extraction statistics to zero."""
        self.stats.reset()


__all__ = [
    'FactExtractor',
    'extract_numeric_value'
]