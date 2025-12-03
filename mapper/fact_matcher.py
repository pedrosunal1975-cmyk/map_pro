# File: /map_pro/engines/mapper/fact_matcher.py

"""
Map Pro Fact Matcher
===================

Matches resolved facts to financial statement categories and line items.

Architecture: Universal fact categorization - works for all statement types.

CRITICAL FIX (2025-11-20):
- REMOVED aggregation logic that was causing data loss
- ALL facts are now preserved separately regardless of concept/context
- Added comprehensive logging for transparency

ENHANCEMENT (2025-12-02):
- Improved cash flow keyword specificity
- Reduced false positives in classification
"""

from typing import Dict, Any, List, Tuple
from collections import defaultdict

from core.system_logger import get_logger

logger = get_logger(__name__, 'engine')


class FactMatcher:
    """
    Matches facts to financial statement categories.
    
    Responsibilities:
    - Categorize facts by statement type (Income, Balance, Cash Flow, Other)
    - Group facts by context and period
    - Handle instant vs duration facts
    - PRESERVE ALL FACTS (no aggregation - each fact is kept separately)
    
    CRITICAL: This class does NOT aggregate or merge any facts.
    Every fact from the input is preserved in the output.
    """
    
    # Statement categorization keywords
    INCOME_KEYWORDS = [
        'revenue', 'income', 'expense', 'cost', 'earnings', 'profit', 'loss',
        'sales', 'operating', 'gross', 'net', 'gain', 'interest', 'tax'
    ]
    
    BALANCE_KEYWORDS = [
        'asset', 'liability', 'equity', 'receivable', 'payable', 'cash',
        'inventory', 'property', 'debt', 'capital', 'retained', 'stock'
    ]
    
    # ENHANCED: More specific cash flow keywords
    CASHFLOW_KEYWORDS = [
        'cashflow', 'cash flow', 'financing', 'investing', 'operating activities',
        'depreciation', 'amortization', 
        'proceedsfrom', 'paymentsfor', 'paymentsto',  # More specific
        'cashprovided', 'cashused', 'netcashflow',    # More specific
        'cashpaid', 'cashreceived', 'cashand'         # Additional specific patterns
    ]
    
    def __init__(self):
        """Initialize fact matcher."""
        self.logger = logger
        
        self.stats = {
            'total_facts_input': 0,
            'total_facts_output': 0,
            'income_statement': 0,
            'balance_sheet': 0,
            'cash_flow': 0,
            'other': 0,
            'contexts_found': 0
        }
        
        self.logger.info("Fact matcher initialized (NO AGGREGATION - all facts preserved)")
    
    def match_facts_to_statements(
        self,
        resolved_facts: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Match resolved facts to statement categories.
        
        CRITICAL: All facts are preserved. No aggregation or merging occurs.
        
        Args:
            resolved_facts: List of resolved facts with taxonomy info
            
        Returns:
            Dictionary with facts categorized by statement type
        """
        self.stats['total_facts_input'] = len(resolved_facts)
        
        # Categorize facts
        categorized = {
            'income_statement': [],
            'balance_sheet': [],
            'cash_flow': [],
            'other': []
        }
        
        # Group facts by context for logging/analysis purposes only
        context_groups = self._group_by_context(resolved_facts)
        self.stats['contexts_found'] = len(context_groups)
        
        # Categorize each fact - NO AGGREGATION
        for fact in resolved_facts:
            category = self._categorize_fact(fact)
            categorized[category].append(fact)
            self.stats[category] += 1
        
        # Calculate total output (should equal input)
        total_output = sum(len(facts) for facts in categorized.values())
        self.stats['total_facts_output'] = total_output
        
        # Log comprehensive statistics
        self._log_matching_results(categorized)
        
        # Verify no facts were lost
        self._verify_fact_preservation(resolved_facts, categorized)
        
        return categorized
    
    def _log_matching_results(
        self,
        categorized: Dict[str, List[Dict[str, Any]]]
    ) -> None:
        """
        Log comprehensive matching results.
        
        Args:
            categorized: Categorized facts dictionary
        """
        self.logger.info(
            f"Fact matching complete: "
            f"Input={self.stats['total_facts_input']}, "
            f"Output={self.stats['total_facts_output']}"
        )
        
        self.logger.info(
            f"Distribution: "
            f"Income={self.stats['income_statement']}, "
            f"Balance={self.stats['balance_sheet']}, "
            f"CashFlow={self.stats['cash_flow']}, "
            f"Other={self.stats['other']}"
        )
        
        self.logger.info(
            f"Unique contexts found: {self.stats['contexts_found']}"
        )
    
    def _verify_fact_preservation(
        self,
        input_facts: List[Dict[str, Any]],
        categorized: Dict[str, List[Dict[str, Any]]]
    ) -> None:
        """
        Verify that all input facts are preserved in output.
        
        Logs a warning if any facts were lost (should never happen).
        
        Args:
            input_facts: Original input facts
            categorized: Categorized output facts
        """
        input_count = len(input_facts)
        output_count = sum(len(facts) for facts in categorized.values())
        
        if input_count != output_count:
            self.logger.error(
                f"CRITICAL: Fact preservation failed! "
                f"Input: {input_count}, Output: {output_count}, "
                f"Lost: {input_count - output_count} facts"
            )
        else:
            self.logger.info(
                f"Fact preservation verified: {input_count} facts in = {output_count} facts out"
            )
    
    def _categorize_fact(self, fact: Dict[str, Any]) -> str:
        """
        Categorize single fact into statement type.
        
        PRIORITY ORDER (highest to lowest):
        1. Period type from taxonomy (NOW AUTHORITATIVE after taxonomy fix)
        2. Concept suffix patterns (PeriodIncreaseDecrease, PaymentsFor, etc.)
        3. Balance type (debit/credit) 
        4. Keywords (fallback)
        
        Args:
            fact: Resolved fact dictionary
            
        Returns:
            Statement category: income_statement, balance_sheet, cash_flow, or other
        """
        # Extract and normalize fact attributes
        fact_attrs = self._extract_fact_attributes(fact)
        
        # PRIORITY 1: Period type from taxonomy (HIGHEST - now authoritative)
        category = self._categorize_by_period_type(fact_attrs)
        if category:
            return category
        
        # PRIORITY 2: Check concept suffix patterns
        category = self._categorize_by_concept_suffix(fact_attrs)
        if category:
            return category
        
        # PRIORITY 3: Try categorization by balance type
        category = self._categorize_by_balance_type(fact_attrs)
        if category:
            return category
        
        # PRIORITY 4: Try categorization by keywords (fallback)
        category = self._categorize_by_keywords(fact_attrs)
        if category:
            return category
        
        # Default to other
        return 'other'
    
    def _extract_fact_attributes(self, fact: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract and normalize fact attributes for categorization.
        
        Args:
            fact: Raw fact dictionary
            
        Returns:
            Dictionary with normalized attributes (all lowercase strings)
        """
        # Get fact identifiers with null safety
        concept = fact.get('taxonomy_concept') or fact.get('concept') or ''
        label = fact.get('taxonomy_label') or fact.get('label') or ''
        balance_type = fact.get('balance_type') or ''
        period_type = fact.get('period_type') or ''
        
        # Normalize to lowercase strings
        return {
            'concept': str(concept).lower() if concept else '',
            'label': str(label).lower() if label else '',
            'balance_type': str(balance_type).lower() if balance_type else '',
            'period_type': str(period_type).lower() if period_type else '',
            'combined_text': f"{str(concept).lower()} {str(label).lower()}"
        }
    
    def _categorize_by_period_type(self, fact_attrs: Dict[str, str]) -> str:
        """
        Categorize fact based on period type (instant vs duration).
        
        NOW PRIORITIZED: Uses taxonomy period_type as PRIMARY signal.
        
        Args:
            fact_attrs: Normalized fact attributes
            
        Returns:
            Category string or empty string if not determined
        """
        period_type = fact_attrs['period_type']
        combined_text = fact_attrs['combined_text']
        
        if period_type == 'instant':
            # Instant facts are balance sheet
            return 'balance_sheet'
        
        elif period_type == 'duration':
            # Duration facts: distinguish between income statement and cash flow
            
            # Check for cash flow keywords (most specific)
            if self._matches_keywords(combined_text, self.CASHFLOW_KEYWORDS):
                return 'cash_flow'
            
            # ENHANCED: Additional cash flow indicators (more specific)
            cash_flow_indicators = [
                'depreciationand', 'amortizationof', 'stockbased', 'sharebased',
                'deferredtax', 'provisionfor', 'changesin', 'increasein', 'decreasein',
                'netcashprovided', 'netcashused', 'operatingcashflow'
            ]
            if any(indicator in combined_text.replace(' ', '').replace('-', '') for indicator in cash_flow_indicators):
                return 'cash_flow'
            
            # Check for income statement keywords
            if self._matches_keywords(combined_text, self.INCOME_KEYWORDS):
                return 'income_statement'
            
            # Default duration facts to income statement
            return 'income_statement'
        
        return ''
    
    def _categorize_by_concept_suffix(self, fact_attrs: Dict[str, str]) -> str:
        """
        Categorize fact based on concept name suffix patterns.
        
        This catches highly specific patterns that override other signals.
        
        Args:
            fact_attrs: Normalized fact attributes
            
        Returns:
            Category string or empty string if not determined
        """
        concept = fact_attrs['concept']
        
        # Cash flow suffix patterns (ALWAYS cash flow)
        cash_flow_suffixes = [
            'periodincreasedecrease',
            'paymentsfor',
            'proceedsfrom',
            'cashprovided',
            'cashused',
            'netcashflow',
            'netcashprovided',
            'netcashused'
        ]
        
        for suffix in cash_flow_suffixes:
            if suffix in concept:
                return 'cash_flow'
        
        # Income statement suffix patterns
        income_suffixes = [
            'revenue',
            'income',
            'expense',
            'grossprofit',
            'operatingincome',
            'netincome',
            'ebit',
            'ebitda'
        ]
        
        for suffix in income_suffixes:
            if concept.endswith(suffix):
                return 'income_statement'
        
        # Balance sheet suffix patterns
        balance_suffixes = [
            'assets',
            'liabilities',
            'equity',
            'stockholdersequity',
            'shareholdersequity'
        ]
        
        for suffix in balance_suffixes:
            if concept.endswith(suffix):
                return 'balance_sheet'
        
        return ''
    
    def _categorize_by_balance_type(self, fact_attrs: Dict[str, str]) -> str:
        """
        Categorize fact based on balance type (debit/credit).
        
        Balance type indicates balance sheet items.
        
        Args:
            fact_attrs: Normalized fact attributes
            
        Returns:
            Category string or empty string if not determined
        """
        if fact_attrs['balance_type'] not in ['debit', 'credit']:
            return ''
        
        # Balance sheet items have debit/credit
        if self._matches_keywords(fact_attrs['combined_text'], self.BALANCE_KEYWORDS):
            return 'balance_sheet'
        
        return ''
    
    def _categorize_by_keywords(self, fact_attrs: Dict[str, str]) -> str:
        """
        Categorize fact based on keyword matching.
        
        This is the fallback categorization method.
        
        Args:
            fact_attrs: Normalized fact attributes
            
        Returns:
            Category string or empty string if not determined
        """
        combined_text = fact_attrs['combined_text']
        
        if self._matches_keywords(combined_text, self.CASHFLOW_KEYWORDS):
            return 'cash_flow'
        elif self._matches_keywords(combined_text, self.INCOME_KEYWORDS):
            return 'income_statement'
        elif self._matches_keywords(combined_text, self.BALANCE_KEYWORDS):
            return 'balance_sheet'
        
        return ''
    
    def _matches_keywords(self, text: str, keywords: List[str]) -> bool:
        """
        Check if text matches any keyword.
        
        Args:
            text: Text to search in
            keywords: List of keywords to search for
            
        Returns:
            True if any keyword found in text
        """
        return any(keyword in text for keyword in keywords)
    
    def _group_by_context(
        self,
        facts: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group facts by context for analysis purposes.
        
        NOTE: This is for logging/analysis only. Facts are NOT aggregated.
        
        Args:
            facts: List of facts
            
        Returns:
            Dictionary mapping context to facts
        """
        context_groups = defaultdict(list)
        
        for fact in facts:
            context = fact.get('context', fact.get('contextRef', 'default'))
            context_groups[context].append(fact)
        
        return dict(context_groups)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get matching statistics.
        
        Returns:
            Copy of statistics dictionary
        """
        return self.stats.copy()


__all__ = ['FactMatcher']