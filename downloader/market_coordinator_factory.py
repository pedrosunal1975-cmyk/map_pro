"""
Market Coordinator Factory
==========================

Dynamically discovers and creates market-specific coordinators.
Handles imports and creation with proper error handling.
"""

from typing import Optional


class MarketCoordinatorFactory:
    """
    Factory for creating market-specific download coordinators.
    
    Dynamically imports and instantiates coordinators following the pattern:
    markets.{market}.{market}_downloader.create_{market}_downloader()
    """
    
    def __init__(self, logger):
        """
        Initialize factory.
        
        Args:
            logger: Logger instance for error reporting
        """
        self.logger = logger
        self._coordinator_cache = {}
    
    def get_coordinator(self, market_type: str, generic_downloader):
        """
        Get or create market-specific coordinator.
        
        Args:
            market_type: Market identifier (e.g., 'sec', 'fca', 'esma')
            generic_downloader: Generic downloader instance to pass to coordinator
            
        Returns:
            Market coordinator instance or None if not available
        """
        if not market_type:
            return None
        
        market_lower = market_type.lower()
        
        # Check cache first
        if market_lower in self._coordinator_cache:
            return self._coordinator_cache[market_lower]
        
        # Try to create coordinator
        coordinator = self._create_coordinator(market_lower, generic_downloader)
        
        # Cache successful creation (including None for markets without coordinators)
        self._coordinator_cache[market_lower] = coordinator
        
        return coordinator
    
    def _create_coordinator(self, market_type: str, generic_downloader):
        """
        Create market-specific coordinator.
        
        Args:
            market_type: Lowercase market identifier
            generic_downloader: Generic downloader instance
            
        Returns:
            Coordinator instance or None
        """
        try:
            module = self._import_market_module(market_type)
            if not module:
                return None
            
            creator_func = self._get_creator_function(module, market_type)
            if not creator_func:
                return None
            
            coordinator = creator_func(generic_downloader=generic_downloader)
            self.logger.debug(f"Successfully created {market_type} coordinator")
            
            return coordinator
            
        except Exception as e:
            self.logger.warning(
                f"Error creating market coordinator for {market_type}: {e}"
            )
            return None
    
    def _import_market_module(self, market_type: str):
        """
        Import market-specific downloader module.
        
        Args:
            market_type: Lowercase market identifier
            
        Returns:
            Imported module or None if not found
        """
        module_path = f"markets.{market_type}.{market_type}_downloader"
        creator_func_name = f"create_{market_type}_downloader"
        
        try:
            module = __import__(module_path, fromlist=[creator_func_name])
            return module
            
        except ImportError as e:
            self.logger.debug(
                f"No market coordinator available for {market_type}: {e}"
            )
            return None
    
    def _get_creator_function(self, module, market_type: str):
        """
        Get creator function from module.
        
        Args:
            module: Imported module
            market_type: Market identifier for function name
            
        Returns:
            Creator function or None if not found
        """
        creator_func_name = f"create_{market_type}_downloader"
        
        if hasattr(module, creator_func_name):
            return getattr(module, creator_func_name)
        
        self.logger.debug(
            f"No creator function '{creator_func_name}' found in module"
        )
        return None
    
    def clear_cache(self) -> None:
        """Clear coordinator cache (useful for testing)."""
        self._coordinator_cache.clear()