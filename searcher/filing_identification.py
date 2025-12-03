"""
Map Pro Filing Identification Component
=======================================

Market-agnostic component for identifying filings for discovered companies.
Loads and delegates to market-specific plugins for actual filing discovery.

Architecture: Coordination component that loads market plugins without market-specific logic.

Responsibilities:
- Route filing searches to appropriate market plugin
- Coordinate filing identification workflow
- Provide unified interface for filing discovery

Delegates detailed work to:
- MarketPluginLoader: Dynamic plugin loading
- FilingStandardizer: Standardize filing information
- FilingCriteriaValidator: Validate search criteria
- FilingFilter: Apply search filters
"""

from typing import Dict, Any, Optional, List

from core.system_logger import get_logger
from shared.exceptions.custom_exceptions import EngineError

from .market_plugin_loader import MarketPluginLoader
from .filing_standardizer import FilingStandardizer
from .filing_criteria_validator import FilingCriteriaValidator
from .filing_filter import FilingFilter

logger = get_logger(__name__, 'engine')


class FilingIdentification:
    """
    Market-agnostic filing identification coordinator.
    
    Responsibilities:
    - Route filing searches to appropriate market plugin
    - Coordinate standardization and filtering
    - Provide unified interface for filing discovery
    
    Does NOT handle:
    - Market-specific API calls (market plugins handle this)
    - Database operations (results_processor handles this)
    - File downloading (downloader engine handles this)
    """
    
    def __init__(self):
        """Initialize filing identification with component modules."""
        # Initialize component modules
        self.plugin_loader = MarketPluginLoader()
        self.standardizer = FilingStandardizer()
        self.criteria_validator = FilingCriteriaValidator()
        self.filing_filter = FilingFilter()
        
        # Load market plugins
        self.market_plugins = self.plugin_loader.load_plugins()
        
        logger.info(
            f"Filing identification initialized with "
            f"{len(self.market_plugins)} market plugins"
        )
    
    async def identify_filings(
        self, 
        market_entity_id: str, 
        market_type: str,
        search_criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Identify available filings for an entity using market-specific plugin.
        
        Args:
            market_entity_id: Market-specific entity identifier
            market_type: Market type ('sec', 'fca', 'esma', etc.)
            search_criteria: Optional filters (date_from, date_to, filing_types, etc.)
            
        Returns:
            List of standardized filing information dictionaries
            
        Raises:
            EngineError: If market plugin not available or search fails
        """
        # Validate market availability
        self._validate_market_type(market_type)
        
        # Get market plugin
        market_plugin = self.market_plugins[market_type]
        
        # Prepare search criteria
        criteria = search_criteria or {}
        
        logger.info(
            f"Identifying filings for entity '{market_entity_id}' in {market_type} "
            f"with criteria: {criteria}"
        )
        
        try:
            # Execute filing search
            filings = await self._search_and_process_filings(
                market_plugin, market_entity_id, market_type, criteria
            )
            
            logger.info(
                f"Identified {len(filings)} filings for entity {market_entity_id}"
            )
            
            return filings
            
        except Exception as e:
            logger.error(
                f"Filing identification failed for {market_entity_id}: {e}",
                exc_info=True
            )
            raise EngineError(f"Filing identification failed: {str(e)}")
    
    async def _search_and_process_filings(
        self,
        market_plugin: Any,
        market_entity_id: str,
        market_type: str,
        criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Execute filing search and process results.
        
        Args:
            market_plugin: Market-specific searcher plugin
            market_entity_id: Entity identifier
            market_type: Market type
            criteria: Search criteria
            
        Returns:
            List of processed filing dictionaries
        """
        # Delegate search to market plugin
        filings_info = await market_plugin.find_filings(market_entity_id, criteria)
        
        if not filings_info:
            logger.info(f"No filings found for entity {market_entity_id}")
            return []
        
        # Standardize and filter results
        processed_filings = self._process_filing_results(
            filings_info, market_type, criteria
        )
        
        return processed_filings
    
    def _process_filing_results(
        self,
        filings_info: List[Dict[str, Any]],
        market_type: str,
        criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Process raw filing results through standardization and filtering.
        
        Args:
            filings_info: Raw filing information from market plugin
            market_type: Market type
            criteria: Search criteria for filtering
            
        Returns:
            List of standardized and filtered filing dictionaries
        """
        standardized_filings = []
        
        for filing in filings_info:
            try:
                # Standardize filing format
                standardized = self.standardizer.standardize_filing(
                    filing, market_type
                )
                
                # Apply filters
                if self.filing_filter.should_include_filing(standardized, criteria):
                    standardized_filings.append(standardized)
                    
            except Exception as e:
                logger.warning(f"Failed to process filing: {e}")
                continue
        
        return standardized_filings
    
    def _validate_market_type(self, market_type: str) -> None:
        """
        Validate that market type is supported.
        
        Args:
            market_type: Market type to validate
            
        Raises:
            EngineError: If market type not available
        """
        if market_type not in self.market_plugins:
            available = ', '.join(self.market_plugins.keys()) or 'none'
            raise EngineError(
                f"Market '{market_type}' not available. "
                f"Available markets: {available}"
            )
    
    def get_supported_filing_types(self, market_type: str) -> List[str]:
        """
        Get supported filing types for specific market.
        
        Args:
            market_type: Market type
            
        Returns:
            List of supported filing types
        """
        if market_type not in self.market_plugins:
            return []
        
        market_plugin = self.market_plugins[market_type]
        
        if hasattr(market_plugin, 'get_supported_filing_types'):
            try:
                return market_plugin.get_supported_filing_types()
            except Exception as e:
                logger.warning(
                    f"Failed to get filing types for {market_type}: {e}"
                )
        
        return []
    
    def validate_search_criteria(
        self, 
        criteria: Dict[str, Any], 
        market_type: str
    ) -> Dict[str, Any]:
        """
        Validate and normalize search criteria.
        
        Args:
            criteria: Raw search criteria
            market_type: Market type
            
        Returns:
            Validated and normalized criteria
        """
        return self.criteria_validator.validate_criteria(criteria, market_type)


__all__ = ['FilingIdentification']