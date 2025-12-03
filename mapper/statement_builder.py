"""
Map Pro Statement Builder
=========================

Builds financial statement structures from categorized facts.

Architecture: Universal statement building - works for all statement types.

CRITICAL FIX (2025-11-20):
- Added fact preservation verification
- Added comprehensive logging
- Removed duplicate-related legacy code (aggregation removed from fact_matcher)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from core.system_logger import get_logger

logger = get_logger(__name__, 'engine')


class StatementBuilder:
    """
    Builds financial statement structures.
    
    Responsibilities:
    - Build Income Statement structure
    - Build Balance Sheet structure
    - Build Cash Flow Statement structure
    - Build Other statements (notes, disclosures, entity info)
    - Create proper JSON hierarchy
    - Calculate summary metrics
    - VERIFY all facts are preserved (no data loss)
    """
    
    def __init__(self):
        """Initialize statement builder."""
        self.logger = logger
        
        self.stats = {
            'statements_built': 0,
            'income_statements': 0,
            'balance_sheets': 0,
            'cash_flow_statements': 0,
            'other_statements': 0,
            'total_facts_input': 0,
            'total_facts_output': 0
        }
        
        self.logger.info("Statement builder initialized")
    
    def build_statements(
        self,
        categorized_facts: Dict[str, List[Dict[str, Any]]],
        parsed_metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Build all financial statements from categorized facts.
        
        CRITICAL: All facts are preserved. Verification is performed.
        
        Args:
            categorized_facts: Facts categorized by statement type
            parsed_metadata: Original parsed metadata
            
        Returns:
            List of statement dictionaries
        """
        # Count input facts
        self.stats['total_facts_input'] = sum(
            len(facts) for facts in categorized_facts.values()
        )
        
        statements = []
        
        # Build each statement type
        if categorized_facts.get('income_statement'):
            income_stmt = self._build_income_statement(
                categorized_facts['income_statement'],
                parsed_metadata
            )
            statements.append(income_stmt)
            self.stats['income_statements'] += 1
        
        if categorized_facts.get('balance_sheet'):
            balance_stmt = self._build_balance_sheet(
                categorized_facts['balance_sheet'],
                parsed_metadata
            )
            statements.append(balance_stmt)
            self.stats['balance_sheets'] += 1
        
        if categorized_facts.get('cash_flow'):
            cashflow_stmt = self._build_cash_flow_statement(
                categorized_facts['cash_flow'],
                parsed_metadata
            )
            statements.append(cashflow_stmt)
            self.stats['cash_flow_statements'] += 1
        
        if categorized_facts.get('other'):
            other_stmt = self._build_other_statement(
                categorized_facts['other'],
                parsed_metadata
            )
            statements.append(other_stmt)
            self.stats['other_statements'] += 1
        
        self.stats['statements_built'] = len(statements)
        
        # Count output facts and verify
        self.stats['total_facts_output'] = sum(
            len(stmt.get('facts', [])) for stmt in statements
        )
        
        # Log and verify
        self._log_build_results(statements)
        self._verify_fact_preservation()
        
        return statements
    
    def _log_build_results(self, statements: List[Dict[str, Any]]) -> None:
        """
        Log comprehensive build results.
        
        Args:
            statements: Built statements
        """
        self.logger.info(
            f"Statement building complete: "
            f"Input={self.stats['total_facts_input']} facts, "
            f"Output={self.stats['total_facts_output']} facts"
        )
        
        for stmt in statements:
            stmt_type = stmt.get('statement_type', 'unknown')
            fact_count = len(stmt.get('facts', []))
            self.logger.info(f"  {stmt_type}: {fact_count} facts")
    
    def _verify_fact_preservation(self) -> None:
        """
        Verify that all input facts are preserved in output.
        
        Logs error if any facts were lost.
        """
        input_count = self.stats['total_facts_input']
        output_count = self.stats['total_facts_output']
        
        if input_count != output_count:
            self.logger.error(
                f"CRITICAL: Statement builder lost facts! "
                f"Input: {input_count}, Output: {output_count}, "
                f"Lost: {input_count - output_count} facts"
            )
        else:
            self.logger.info(
                f"Fact preservation verified: {input_count} facts in = {output_count} facts out"
            )
    
    def _build_income_statement(
        self,
        facts: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build Income Statement structure."""
        return {
            'statement_type': 'income_statement',
            'metadata': self._create_statement_metadata(metadata, 'Income Statement'),
            'facts': self._organize_facts(facts, 'income'),
            'summary': self._calculate_summary(facts)
        }
    
    def _build_balance_sheet(
        self,
        facts: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build Balance Sheet structure."""
        return {
            'statement_type': 'balance_sheet',
            'metadata': self._create_statement_metadata(metadata, 'Balance Sheet'),
            'facts': self._organize_facts(facts, 'balance'),
            'summary': self._calculate_summary(facts)
        }
    
    def _build_cash_flow_statement(
        self,
        facts: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build Cash Flow Statement structure."""
        return {
            'statement_type': 'cash_flow',
            'metadata': self._create_statement_metadata(metadata, 'Cash Flow Statement'),
            'facts': self._organize_facts(facts, 'cashflow'),
            'summary': self._calculate_summary(facts)
        }
    
    def _build_other_statement(
        self,
        facts: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build Other statement (notes, disclosures, entity info)."""
        return {
            'statement_type': 'other',
            'metadata': self._create_statement_metadata(metadata, 'Other Information'),
            'facts': self._organize_facts(facts, 'other'),
            'summary': self._calculate_summary(facts)
        }
    
    def _create_statement_metadata(
        self,
        parsed_metadata: Dict[str, Any],
        statement_name: str
    ) -> Dict[str, Any]:
        """
        Create statement metadata.
        
        Args:
            parsed_metadata: Original parsed metadata
            statement_name: Name of the statement
            
        Returns:
            Metadata dictionary for statement
        """
        return {
            'statement_name': statement_name,
            'company': parsed_metadata.get('company', 'Unknown'),
            'ticker': parsed_metadata.get('ticker'),
            'filing_type': parsed_metadata.get('filing_type'),
            'filing_date': parsed_metadata.get('filing_date'),
            'market': parsed_metadata.get('market'),
            'currency': 'USD',  # Default, should be detected from facts
            'mapped_at': datetime.now(timezone.utc).isoformat()
        }
    
    def _organize_facts(
        self,
        facts: List[Dict[str, Any]],
        statement_type: str
    ) -> List[Dict[str, Any]]:
        """
        Organize facts into logical structure.
        
        CRITICAL: All facts are preserved. Only sorting and cleaning occurs.
        
        Args:
            facts: List of facts to organize
            statement_type: Type of statement (income, balance, cashflow, other)
            
        Returns:
            List of organized and cleaned facts (same count as input)
        """
        input_count = len(facts)
        
        # Sort facts by concept for consistent ordering
        organized = self._sort_facts_by_concept(facts)
        
        # Clean and structure each fact
        cleaned_facts = [
            self._clean_fact(fact) for fact in organized
        ]
        
        # Verify no facts were lost during organizing
        if len(cleaned_facts) != input_count:
            self.logger.error(
                f"CRITICAL: _organize_facts lost facts! "
                f"Input: {input_count}, Output: {len(cleaned_facts)}"
            )
        
        return cleaned_facts
    
    def _sort_facts_by_concept(
        self,
        facts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Sort facts by their concept name for consistent ordering.
        
        Args:
            facts: List of facts to sort
            
        Returns:
            Sorted list of facts (same count as input)
        """
        return sorted(
            facts,
            key=lambda f: (
                f.get('taxonomy_concept') or f.get('concept') or '',
                f.get('context') or f.get('contextRef') or ''
            )
        )
    
    def _clean_fact(self, fact: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and structure a single fact.
        
        Extracts all relevant fields with fallback chains and creates
        a standardized fact dictionary.
        
        Args:
            fact: Raw fact dictionary
            
        Returns:
            Cleaned fact dictionary
        """
        # Build base cleaned fact - preserve ALL relevant fields
        cleaned_fact = {
            'concept': self._extract_concept(fact),
            'label': fact.get('taxonomy_label'),
            'value': self._extract_value(fact),
            'unit': self._extract_unit(fact),
            'context': self._extract_context(fact),
            'period_type': fact.get('period_type'),
            'balance_type': fact.get('balance_type'),
            'decimals': fact.get('decimals'),
            'is_abstract': fact.get('is_abstract', False),
            'is_extension': fact.get('is_extension', False),
            'mapping_confidence': fact.get('mapping_confidence', 0.0),
            'mapping_method': fact.get('mapping_method'),
            'is_unmapped': fact.get('is_unmapped', False)
        }
        
        # Preserve fact_id if present (for traceability)
        if 'fact_id' in fact:
            cleaned_fact['fact_id'] = fact['fact_id']
        
        # Preserve original concept_qname if different from taxonomy_concept
        if 'concept_qname' in fact:
            cleaned_fact['original_concept'] = fact['concept_qname']
        
        return cleaned_fact
    
    def _extract_concept(self, fact: Dict[str, Any]) -> Optional[str]:
        """
        Extract concept from fact with fallback.
        
        Args:
            fact: Fact dictionary
            
        Returns:
            Concept string or None
        """
        return fact.get('taxonomy_concept', fact.get('concept'))
    
    def _extract_value(self, fact: Dict[str, Any]) -> Any:
        """
        Extract value from fact using universal field detection.
        
        Market-agnostic value extraction with fallback chain.
        
        Args:
            fact: Fact dictionary
            
        Returns:
            Fact value (various types) or None
        """
        return (
            fact.get('value') or 
            fact.get('fact_value') or 
            fact.get('amount') or 
            fact.get('content') or
            fact.get('text')
        )
    
    def _extract_unit(self, fact: Dict[str, Any]) -> Optional[str]:
        """
        Extract unit from fact with fallback chain.
        
        Handles various field names used across different markets.
        
        Args:
            fact: Fact dictionary
            
        Returns:
            Unit string or None
        """
        return (
            fact.get('unit') or
            fact.get('unitRef') or
            fact.get('unit_ref') or
            fact.get('uom') or
            fact.get('currency')
        )
    
    def _extract_context(self, fact: Dict[str, Any]) -> Optional[str]:
        """
        Extract context from fact with fallback chain.
        
        Handles various field names used across different markets.
        
        Args:
            fact: Fact dictionary
            
        Returns:
            Context string or None
        """
        return (
            fact.get('context') or
            fact.get('contextRef') or
            fact.get('context_ref') or
            fact.get('context_id') or
            fact.get('period')
        )
    
    def _calculate_summary(self, facts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate summary metrics for statement.
        
        Args:
            facts: List of facts
            
        Returns:
            Summary metrics dictionary
        """
        total_facts = len(facts)
        
        # Calculate mapping statistics
        mapping_stats = self._calculate_mapping_stats(facts, total_facts)
        
        # Calculate fact type statistics
        type_stats = self._calculate_fact_type_stats(facts, total_facts)
        
        # Merge all statistics
        return {
            **mapping_stats,
            **type_stats
        }
    
    def _calculate_mapping_stats(
        self,
        facts: List[Dict[str, Any]],
        total_facts: int
    ) -> Dict[str, Any]:
        """
        Calculate mapping-related statistics.
        
        Args:
            facts: List of facts
            total_facts: Total number of facts
            
        Returns:
            Mapping statistics dictionary
        """
        mapped_facts = sum(1 for f in facts if not f.get('is_unmapped', False))
        unmapped_facts = total_facts - mapped_facts
        
        # Calculate average confidence (excluding unmapped)
        avg_confidence = self._calculate_average_confidence(facts)
        
        return {
            'total_facts': total_facts,
            'mapped_facts': mapped_facts,
            'unmapped_facts': unmapped_facts,
            'mapping_rate': (
                (mapped_facts / total_facts * 100) if total_facts > 0 else 0.0
            ),
            'average_confidence': round(avg_confidence, 4)
        }
    
    def _calculate_average_confidence(
        self,
        facts: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate average mapping confidence for mapped facts.
        
        Args:
            facts: List of facts
            
        Returns:
            Average confidence score (0.0 if no mapped facts)
        """
        mapped_confidences = [
            f.get('mapping_confidence', 0.0)
            for f in facts
            if not f.get('is_unmapped', False)
        ]
        
        if not mapped_confidences:
            return 0.0
        
        return sum(mapped_confidences) / len(mapped_confidences)
    
    def _calculate_fact_type_stats(
        self,
        facts: List[Dict[str, Any]],
        total_facts: int
    ) -> Dict[str, Any]:
        """
        Calculate statistics about fact types (numeric vs text, extensions).
        
        Args:
            facts: List of facts
            total_facts: Total number of facts
            
        Returns:
            Fact type statistics dictionary
        """
        numeric_facts = sum(
            1 for f in facts
            if isinstance(f.get('value'), (int, float))
        )
        text_facts = total_facts - numeric_facts
        
        extension_facts = sum(1 for f in facts if f.get('is_extension', False))
        
        return {
            'numeric_facts': numeric_facts,
            'text_facts': text_facts,
            'extension_facts': extension_facts
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get builder statistics.
        
        Returns:
            Copy of statistics dictionary
        """
        return self.stats.copy()


__all__ = ['StatementBuilder']