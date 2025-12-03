# File: map_pro/engines/mapper/null_value_validator.py

"""
Map Pro Null Value Validator
============================

Validates null/nil values in parsed and mapped data to distinguish between:
1. Legitimate nulls from source XBRL (with explanatory context)
2. Missing data due to processing failures or gaps

This is CRITICAL for data quality and trust in mapped statements.

Architecture: Refactored to follow SOLID principles with separated concerns.
Each responsibility is delegated to specialized components.

Improvements Made:
- Extracted complex report generation into QualityReportBuilder
- Separated analysis logic into NullValueAnalyzer
- Moved explanation finding to ExplanationFinder
- Centralized constants to eliminate magic numbers
- Reduced cyclomatic complexity of all methods
- Each class has single, clear responsibility
- Maintained 100% backward compatibility
"""

from typing import Dict, Any, List
from collections import defaultdict

from core.system_logger import get_logger

from .explanation_finder import ExplanationFinder, ConceptChecker
from .null_value_analyzer import NullValueAnalyzer
from .quality_report_builder import QualityReportBuilder, RecommendationGenerator
from .summary_generator import SummaryGenerator

logger = get_logger(__name__, 'engine')


class NullValueValidator:
    """
    Validates null values and provides context about their origin.
    
    Responsibilities:
    - Orchestrate validation workflow
    - Coordinate component interactions
    - Provide public API for validation
    - Maintain validation statistics
    
    Key Metrics:
    - Null with explanation (OK)
    - Null without explanation (SUSPICIOUS)
    - Nil in source XBRL (LEGITIMATE)
    - Missing expected value (FAILURE)
    """
    
    def __init__(self):
        """Initialize null value validator with all components."""
        self.logger = logger
        
        # Initialize helper components
        self.concept_checker = ConceptChecker()
        self.explanation_finder = ExplanationFinder()
        self.analyzer = NullValueAnalyzer(
            self.concept_checker,
            self.explanation_finder
        )
        self.summary_generator = SummaryGenerator()
        self.report_builder = QualityReportBuilder()
        self.recommendation_generator = RecommendationGenerator()
        
        self.logger.info("Null value validator initialized")
    
    def validate_parsed_facts(
        self,
        facts: List[Dict[str, Any]],
        document_metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Validate null values in parsed facts.
        
        Args:
            facts: List of parsed fact dictionaries
            document_metadata: Optional document-level metadata (unused currently)
            
        Returns:
            Validation report with null value analysis
        """
        self.logger.info(f"Validating null values in {len(facts)} parsed facts")
        
        # Initialize analysis containers
        null_analysis = self._initialize_null_analysis(len(facts))
        
        # Extract explanatory texts first
        explanatory_texts = self.explanation_finder.extract_explanatory_texts(facts)
        
        # Analyze each fact
        self._analyze_all_facts(facts, explanatory_texts, null_analysis)
        
        # Store explanatory contexts
        null_analysis['context_explanations'] = explanatory_texts
        
        # Generate summary
        null_analysis['summary'] = self._generate_parsed_summary(null_analysis)
        
        self._log_validation_results(null_analysis['summary'])
        
        return null_analysis
    
    def validate_mapped_statements(
        self,
        statements: List[Dict[str, Any]],
        resolved_facts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate null values in mapped statements.
        
        Args:
            statements: List of mapped statement dictionaries
            resolved_facts: Original resolved facts for context (unused currently)
            
        Returns:
            Validation report for mapped statements
        """
        self.logger.info(f"Validating null values in {len(statements)} mapped statements")
        
        validation_report = {
            'statements_analyzed': len(statements),
            'statements_with_nulls': [],
            'null_patterns': defaultdict(int),
            'recommendations': []
        }
        
        # Analyze each statement
        for statement in statements:
            self._analyze_statement(statement, validation_report)
        
        # Generate recommendations
        validation_report['recommendations'] = (
            self.recommendation_generator.generate_recommendations(validation_report)
        )
        
        return validation_report
    
    def generate_null_quality_report(
        self,
        parsed_validation: Dict[str, Any],
        mapped_validation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive null quality report.
        
        Args:
            parsed_validation: Parsed facts validation results
            mapped_validation: Mapped statements validation results
            
        Returns:
            Comprehensive quality report
        """
        return self.report_builder.build_quality_report(
            parsed_validation,
            mapped_validation
        )
    
    # ========================================================================
    # PRIVATE ORCHESTRATION METHODS
    # ========================================================================
    
    def _initialize_null_analysis(self, total_facts: int) -> Dict[str, Any]:
        """Initialize null analysis data structure."""
        return {
            'total_facts': total_facts,
            'null_facts': [],
            'nil_facts': [],
            'suspicious_nulls': [],
            'explained_nulls': [],
            'context_explanations': [],
            'summary': {}
        }
    
    def _analyze_all_facts(
        self,
        facts: List[Dict[str, Any]],
        explanatory_texts: List[Dict[str, str]],
        null_analysis: Dict[str, Any]
    ) -> None:
        """Analyze all facts and populate null analysis."""
        for fact in facts:
            null_info = self.analyzer.analyze_fact(fact, explanatory_texts)
            
            if null_info:
                self._categorize_null_info(null_info, null_analysis)
    
    def _categorize_null_info(
        self,
        null_info: Dict[str, Any],
        null_analysis: Dict[str, Any]
    ) -> None:
        """Categorize null info into appropriate analysis lists."""
        classification = null_info.get('classification')
        
        if classification == 'nil_in_source':
            null_analysis['nil_facts'].append(null_info)
        elif classification == 'explained_null':
            null_analysis['explained_nulls'].append(null_info)
            null_analysis['null_facts'].append(null_info)
        elif classification == 'unexplained_null':
            null_analysis['suspicious_nulls'].append(null_info)
            null_analysis['null_facts'].append(null_info)
    
    def _generate_parsed_summary(self, null_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary for parsed facts analysis."""
        stats = self.analyzer.get_statistics()
        
        return self.summary_generator.generate_parsed_summary(
            total_facts=null_analysis['total_facts'],
            null_facts=null_analysis['null_facts'],
            nil_facts=null_analysis['nil_facts'],
            explained_nulls=null_analysis['explained_nulls'],
            suspicious_nulls=null_analysis['suspicious_nulls'],
            critical_nulls_count=stats['critical_nulls']
        )
    
    def _analyze_statement(
        self,
        statement: Dict[str, Any],
        validation_report: Dict[str, Any]
    ) -> None:
        """Analyze a single statement for null values."""
        statement_analysis = self.analyzer.analyze_statement_nulls(statement)
        
        if statement_analysis:
            validation_report['statements_with_nulls'].append(statement_analysis)
            
            # Track null pattern
            statement_type = statement_analysis['statement_type']
            validation_report['null_patterns'][statement_type] += 1
    
    def _log_validation_results(self, summary: Dict[str, Any]) -> None:
        """Log validation results summary."""
        self.logger.info(
            f"Null validation: {summary.get('total_nulls', 0)} nulls found, "
            f"{summary.get('explained_nulls', 0)} explained, "
            f"{summary.get('suspicious_nulls', 0)} suspicious"
        )


def create_null_validator() -> NullValueValidator:
    """
    Factory function to create null value validator.
    
    Returns:
        Configured NullValueValidator instance
    """
    return NullValueValidator()


__all__ = ['NullValueValidator', 'create_null_validator']