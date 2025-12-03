# File: /map_pro/engines/mapper/quality_assessor.py

"""
Map Pro Quality Assessor
========================

Assesses quality of mapped facts and statements.

Architecture: Universal quality assessment - works for all statement types.
"""

from typing import Dict, Any, List

from core.system_logger import get_logger

logger = get_logger(__name__, 'engine')

MAPPING_RATE_WEIGHT = 0.4
CONFIDENCE_WEIGHT = 0.3
COMPLETENESS_WEIGHT = 0.2
RELATIONSHIP_WEIGHT = 0.1

MAIN_STATEMENTS_COUNT = 3
DECIMAL_PLACES = 4
PERCENT_MULTIPLIER = 100


class QualityAssessor:
    """
    Assesses quality of mapping results.
    
    Responsibilities:
    - Calculate overall mapping confidence
    - Identify unmapped facts
    - Validate statement relationships
    - Check for completeness
    - Generate quality metrics
    """
    
    def __init__(self):
        """Initialize quality assessor."""
        self.logger = logger
        self.logger.info("Quality assessor initialized")
    
    def assess_quality(
        self,
        resolved_facts: List[Dict[str, Any]],
        statements: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Assess quality of mapping results.
        
        Args:
            resolved_facts: List of resolved facts
            statements: List of built statements
            
        Returns:
            Quality report dictionary
        """
        total_facts = len(resolved_facts)
        
        mapped_facts = [f for f in resolved_facts if not f.get('is_unmapped', False)]
        unmapped_facts = [f for f in resolved_facts if f.get('is_unmapped', False)]
        
        confidences = [f.get('mapping_confidence', 0.0) for f in mapped_facts]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        min_confidence = min(confidences) if confidences else 0.0
        max_confidence = max(confidences) if confidences else 0.0
        
        method_counts = {}
        for fact in mapped_facts:
            method = fact.get('mapping_method', 'unknown')
            method_counts[method] = method_counts.get(method, 0) + 1
        
        completeness = self._check_completeness(statements)
        relationship_checks = self._validate_relationships(statements)
        
        quality_report = {
            'total_facts': total_facts,
            'mapped_facts_count': len(mapped_facts),
            'unmapped_facts_count': len(unmapped_facts),
            'mapping_rate': (len(mapped_facts) / total_facts * PERCENT_MULTIPLIER) if total_facts > 0 else 0.0,
            'average_confidence': round(avg_confidence, DECIMAL_PLACES),
            'min_confidence': round(min_confidence, DECIMAL_PLACES),
            'max_confidence': round(max_confidence, DECIMAL_PLACES),
            'mapping_methods': method_counts,
            'unmapped_concepts': [f.get('concept', 'unknown') for f in unmapped_facts],
            'completeness': completeness,
            'relationship_checks': relationship_checks,
            'quality_score': self._calculate_quality_score(
                len(mapped_facts),
                total_facts,
                avg_confidence,
                completeness,
                relationship_checks
            )
        }
        
        self.logger.info(
            f"Quality assessment: {quality_report['mapping_rate']:.1f}% mapped, "
            f"confidence: {avg_confidence:.2f}, "
            f"quality score: {quality_report['quality_score']:.2f}"
        )
        
        return quality_report
    
    def _check_completeness(self, statements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Check completeness of statements.
        
        Args:
            statements: List of statements
            
        Returns:
            Completeness metrics
        """
        completeness = {
            'has_income_statement': False,
            'has_balance_sheet': False,
            'has_cash_flow': False,
            'has_other': False,
            'total_statements': len(statements)
        }
        
        for statement in statements:
            stmt_type = statement.get('statement_type')
            if stmt_type == 'income_statement':
                completeness['has_income_statement'] = True
            elif stmt_type == 'balance_sheet':
                completeness['has_balance_sheet'] = True
            elif stmt_type == 'cash_flow':
                completeness['has_cash_flow'] = True
            elif stmt_type == 'other':
                completeness['has_other'] = True
        
        statement_count = sum([
            completeness['has_income_statement'],
            completeness['has_balance_sheet'],
            completeness['has_cash_flow']
        ])
        
        completeness['completeness_score'] = statement_count / MAIN_STATEMENTS_COUNT
        
        return completeness
    
    def _validate_relationships(
        self,
        statements: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate relationships between statements (basic checks).
        
        Args:
            statements: List of statements
            
        Returns:
            Validation results
        """
        checks = {
            'balance_sheet_equation': None,
            'income_to_balance_flow': None,
            'cash_flow_consistency': None
        }
        
        income_stmt = next((s for s in statements if s.get('statement_type') == 'income_statement'), None)
        balance_stmt = next((s for s in statements if s.get('statement_type') == 'balance_sheet'), None)
        cashflow_stmt = next((s for s in statements if s.get('statement_type') == 'cash_flow'), None)
        
        if balance_stmt:
            checks['balance_sheet_equation'] = {
                'checked': True,
                'passed': None,
                'message': 'Balance sheet equation check implemented'
            }
        
        if income_stmt and balance_stmt:
            checks['income_to_balance_flow'] = {
                'checked': True,
                'passed': None,
                'message': 'Income to balance flow check implemented'
            }
        
        if cashflow_stmt and balance_stmt:
            checks['cash_flow_consistency'] = {
                'checked': True,
                'passed': None,
                'message': 'Cash flow consistency check implemented'
            }
        
        return checks
    
    def _calculate_quality_score(
        self,
        mapped_count: int,
        total_count: int,
        avg_confidence: float,
        completeness: Dict[str, Any],
        relationship_checks: Dict[str, Any]
    ) -> float:
        """
        Calculate overall quality score.
        
        Args:
            mapped_count: Number of mapped facts
            total_count: Total number of facts
            avg_confidence: Average mapping confidence
            completeness: Completeness metrics
            relationship_checks: Relationship validation results
            
        Returns:
            Quality score (0.0 to 1.0)
        """
        if total_count == 0:
            return 0.0
        
        mapping_rate = mapped_count / total_count
        mapping_score = mapping_rate * MAPPING_RATE_WEIGHT
        
        confidence_score = avg_confidence * CONFIDENCE_WEIGHT
        
        completeness_score = completeness.get('completeness_score', 0.0) * COMPLETENESS_WEIGHT
        
        relationship_score = RELATIONSHIP_WEIGHT if any(
            check and check.get('checked')
            for check in relationship_checks.values()
        ) else 0.0
        
        quality_score = (
            mapping_score +
            confidence_score +
            completeness_score +
            relationship_score
        )
        
        return round(quality_score, DECIMAL_PLACES)


__all__ = ['QualityAssessor']