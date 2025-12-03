"""
Map Pro Company Discovery Component
===================================

Market-agnostic component for discovering companies across different regulatory markets.
Loads and delegates to market-specific plugins for actual API interactions.

Architecture: Coordination component that loads market plugins without market-specific logic.
"""

from typing import Dict, Any, Optional, List, Tuple
import importlib
from pathlib import Path

from core.system_logger import get_logger
from core.data_paths import map_pro_paths
from shared.exceptions.custom_exceptions import EngineError

logger = get_logger(__name__, 'engine')


class CompanyDiscovery:
    """
    Market-agnostic company discovery coordinator.
    
    Responsibilities:
    - Load market-specific searcher plugins
    - Route company searches to appropriate market plugin
    - Validate search parameters
    - Standardize company information format
    
    Does NOT handle:
    - Market-specific API calls (market plugins handle this)
    - Database operations (results_processor handles this)
    - Filing discovery (filing_identification handles this)
    """
    
    def __init__(self):
        """Initialize company discovery with market plugin loading."""
        self.market_plugins = {}
        self._load_market_plugins()
        
        logger.info("Company discovery component initialized")
    
    def _load_market_plugins(self):
        """
        Dynamically load market-specific searcher plugins.
        
        Loads available markets gracefully - missing markets don't break working ones.
        """
        try:
            markets_path = map_pro_paths.markets
            
            if not self._validate_markets_directory(markets_path):
                return
            
            logger.info("Loading market plugins...")
            
            # Load plugins and track results
            loaded_markets, failed_markets = self._scan_and_load_markets(markets_path)
            
            # Report results
            self._report_loading_results(loaded_markets, failed_markets)
                
        except Exception as e:
            logger.error(f"Market plugin loading failed: {e}")
            # Don't re-raise - allow system to continue with whatever loaded successfully
    
    def _validate_markets_directory(self, markets_path: Path) -> bool:
        """
        Validate that markets directory exists.
        
        Args:
            markets_path: Path to markets directory
            
        Returns:
            True if valid, False otherwise
        """
        if not markets_path.exists():
            logger.warning(f"Markets directory not found: {markets_path}")
            return False
        return True
    
    def _scan_and_load_markets(self, markets_path: Path) -> Tuple[List[str], List[str]]:
        """
        Scan markets directory and load all available market plugins.
        
        Args:
            markets_path: Path to markets directory
            
        Returns:
            Tuple of (loaded_markets, failed_markets) lists
        """
        loaded_markets = []
        failed_markets = []
        
        for market_dir in markets_path.iterdir():
            if not self._is_valid_market_directory(market_dir):
                continue
            
            market_name = market_dir.name
            
            # Attempt to load this market
            load_result = self._attempt_load_market(market_name, market_dir)
            
            if load_result['success']:
                loaded_markets.append(market_name)
            elif load_result['error']:
                failed_markets.append(f"{market_name} (error: {load_result['error']})")
        
        return loaded_markets, failed_markets
    
    def _is_valid_market_directory(self, market_dir: Path) -> bool:
        """
        Check if directory is a valid market directory.
        
        Args:
            market_dir: Directory to check
            
        Returns:
            True if valid market directory, False otherwise
        """
        if not market_dir.is_dir():
            return False
        
        if market_dir.name in ['base', '__pycache__']:
            return False
        
        return True
    
    def _attempt_load_market(self, market_name: str, market_dir: Path) -> Dict[str, Any]:
        """
        Attempt to load a market plugin from various possible locations.
        
        Args:
            market_name: Name of the market
            market_dir: Path to market directory
            
        Returns:
            Dictionary with 'success' boolean and optional 'error' message
        """
        possible_locations = self._get_possible_plugin_locations(market_name, market_dir)
        
        for searcher_path, module_path in possible_locations:
            if not searcher_path.exists():
                continue
            
            load_result = self._try_load_from_location(
                market_name, 
                searcher_path, 
                module_path
            )
            
            if load_result['success']:
                return load_result
            
            if load_result.get('fatal'):
                # Fatal error means don't try other locations
                return load_result
        
        # No locations worked
        logger.debug(f"Market {market_name}: no searcher module found in any expected location")
        return {'success': False, 'error': None}
    
    def _get_possible_plugin_locations(
        self, 
        market_name: str, 
        market_dir: Path
    ) -> List[Tuple[Path, str]]:
        """
        Get list of possible locations for market plugin.
        
        Args:
            market_name: Name of the market
            market_dir: Path to market directory
            
        Returns:
            List of (file_path, module_path) tuples
        """
        return [
            # Location 1: Direct file (legacy/simple structure)
            (
                market_dir / f"{market_name}_searcher.py",
                f"markets.{market_name}.{market_name}_searcher"
            ),
            
            # Location 2: Subdirectory structure (actual current structure)
            (
                market_dir / f"{market_name}_searcher" / f"{market_name}_searcher.py",
                f"markets.{market_name}.{market_name}_searcher.{market_name}_searcher"
            ),
        ]
    
    def _try_load_from_location(
        self, 
        market_name: str, 
        searcher_path: Path, 
        module_path: str
    ) -> Dict[str, Any]:
        """
        Try to load a market plugin from a specific location.
        
        Args:
            market_name: Name of the market
            searcher_path: Path to searcher file
            module_path: Python module path
            
        Returns:
            Dictionary with 'success', optional 'error', and optional 'fatal' flag
        """
        logger.info(f"Attempting to load market plugin: {market_name} from {searcher_path}")
        
        try:
            # Import the module
            module = importlib.import_module(module_path)
            
            # Try to get and instantiate the searcher class
            return self._instantiate_searcher(market_name, module, module_path)
            
        except ImportError as e:
            logger.debug(f"Failed to import {module_path}: {e}")
            return {'success': False, 'error': None}  # Try next location
        
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Failed to instantiate {market_name} plugin: {e}")
            return {'success': False, 'error': error_msg, 'fatal': True}
    
    def _instantiate_searcher(
        self, 
        market_name: str, 
        module: Any, 
        module_path: str
    ) -> Dict[str, Any]:
        """
        Instantiate a searcher class from a loaded module.
        
        Args:
            market_name: Name of the market
            module: Loaded Python module
            module_path: Module path (for logging)
            
        Returns:
            Dictionary with 'success' and optional 'error'
        """
        class_name = f"{market_name.upper()}Searcher"
        
        if not hasattr(module, class_name):
            logger.warning(f"Market {market_name}: {class_name} class not found in {module_path}")
            return {'success': False, 'error': f'{class_name} not found'}
        
        searcher_class = getattr(module, class_name)
        
        # Try to instantiate (this validates the implementation)
        searcher_instance = searcher_class()
        
        # Store the working plugin
        self.market_plugins[market_name] = searcher_instance
        logger.info(f"Successfully loaded market plugin: {market_name}")
        
        return {'success': True}
    
    def _report_loading_results(self, loaded_markets: List[str], failed_markets: List[str]):
        """
        Report the results of market plugin loading.
        
        Args:
            loaded_markets: List of successfully loaded markets
            failed_markets: List of markets that failed to load
        """
        if loaded_markets:
            logger.info(
                f"Successfully loaded {len(loaded_markets)} market plugins: "
                f"{', '.join(loaded_markets)}"
            )
        
        if failed_markets:
            logger.warning(
                f"Failed to load {len(failed_markets)} market plugins: "
                f"{', '.join(failed_markets)}"
            )
        
        if not loaded_markets and not failed_markets:
            logger.info("No market plugins found (this is normal during development)")
    
    def get_available_markets(self) -> List[str]:
        """
        Get list of available market types.
        
        Returns:
            List of market identifiers (e.g., ['sec', 'fca', 'esma'])
        """
        return list(self.market_plugins.keys())
    
    async def discover_company(
        self, 
        company_identifier: str, 
        market_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Discover company information using market-specific plugin.
        
        Args:
            company_identifier: Company identifier (ticker, CIK, company number, etc.)
            market_type: Market type ('sec', 'fca', 'esma', etc.)
            
        Returns:
            Standardized company information dictionary or None if not found
            
        Raises:
            EngineError: If market plugin not available or search fails
        """
        # Validate and get market plugin
        market_plugin = self._get_market_plugin(market_type)
        
        logger.info(f"Discovering company '{company_identifier}' in {market_type}")
        
        try:
            # Delegate to market-specific plugin
            company_info = await market_plugin.search_company(company_identifier)
            
            return self._process_company_search_result(
                company_info, 
                company_identifier, 
                market_type
            )
                
        except Exception as e:
            logger.error(f"Company discovery failed for {company_identifier}: {e}")
            raise EngineError(f"Company discovery failed: {str(e)}")
    
    def _get_market_plugin(self, market_type: str):
        """
        Get market plugin for specified market type.
        
        Args:
            market_type: Market type
            
        Returns:
            Market plugin instance
            
        Raises:
            EngineError: If market plugin not available
        """
        if market_type not in self.market_plugins:
            available = ', '.join(self.get_available_markets())
            raise EngineError(
                f"Market '{market_type}' not available. Available markets: {available}"
            )
        
        return self.market_plugins[market_type]
    
    def _process_company_search_result(
        self, 
        company_info: Optional[Dict[str, Any]], 
        company_identifier: str, 
        market_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Process the result of a company search.
        
        Args:
            company_info: Company info from market plugin (or None)
            company_identifier: Original search identifier
            market_type: Market type
            
        Returns:
            Standardized company info or None
        """
        if not company_info:
            logger.warning(f"Company not found: {company_identifier} in {market_type}")
            return None
        
        # Validate and standardize the response
        standardized_info = self._standardize_company_info(company_info, market_type)
        logger.info(f"Company discovered: {standardized_info.get('name')}")
        return standardized_info
    
    def _standardize_company_info(
        self, 
        company_info: Dict[str, Any], 
        market_type: str
    ) -> Dict[str, Any]:
        """
        Standardize company information to common format.
        
        Args:
            company_info: Raw company info from market plugin
            market_type: Market type
            
        Returns:
            Standardized company information dictionary
            
        Raises:
            EngineError: If required fields are missing
        """
        # Validate required fields
        self._validate_required_fields(company_info)
        
        # Build standardized format
        return self._build_standardized_info(company_info, market_type)
    
    def _validate_required_fields(self, company_info: Dict[str, Any]):
        """
        Validate that required fields are present in company info.
        
        Args:
            company_info: Company info to validate
            
        Raises:
            EngineError: If required fields are missing
        """
        required_fields = ['market_entity_id', 'name']
        
        for field in required_fields:
            if field not in company_info:
                raise EngineError(
                    f"Market plugin returned incomplete data: missing '{field}'"
                )
    
    def _build_standardized_info(
        self, 
        company_info: Dict[str, Any], 
        market_type: str
    ) -> Dict[str, Any]:
        """
        Build standardized company information dictionary.
        
        Args:
            company_info: Raw company info
            market_type: Market type
            
        Returns:
            Standardized company information
        """
        return {
            # Required fields
            'market_entity_id': str(company_info['market_entity_id']),
            'name': str(company_info['name']).strip(),
            'market_type': market_type,
            
            # Optional fields with defaults
            'ticker': company_info.get('ticker'),
            'identifiers': company_info.get('identifiers', {}),
            'jurisdiction': company_info.get('jurisdiction'),
            'entity_type': company_info.get('entity_type'),
            'status': company_info.get('status', 'active'),
            
            # Metadata
            'discovered_at': company_info.get('discovered_at'),
            'source_url': company_info.get('source_url'),
            'additional_info': company_info.get('additional_info', {})
        }
    
    def validate_company_identifier(
        self, 
        company_identifier: str, 
        market_type: str
    ) -> bool:
        """
        Validate company identifier format for specific market.
        
        Args:
            company_identifier: Company identifier to validate
            market_type: Market type
            
        Returns:
            True if valid format, False otherwise
        """
        # Basic validation
        if not company_identifier or not company_identifier.strip():
            return False
        
        # Delegate to market plugin if available
        return self._validate_with_market_plugin(company_identifier, market_type)
    
    def _validate_with_market_plugin(
        self, 
        company_identifier: str, 
        market_type: str
    ) -> bool:
        """
        Validate identifier using market plugin if available.
        
        Args:
            company_identifier: Identifier to validate
            market_type: Market type
            
        Returns:
            True if valid, False otherwise
        """
        if market_type not in self.market_plugins:
            # Default: accept any non-empty string
            return True
        
        market_plugin = self.market_plugins[market_type]
        
        if not hasattr(market_plugin, 'validate_identifier'):
            # Plugin doesn't provide validation
            return True
        
        try:
            return market_plugin.validate_identifier(company_identifier)
        except Exception as e:
            logger.warning(f"Identifier validation failed: {e}")
            return False
    
    def get_search_capabilities(self, market_type: str) -> Dict[str, Any]:
        """
        Get search capabilities for specific market.
        
        Args:
            market_type: Market type
            
        Returns:
            Dictionary describing search capabilities
        """
        if market_type not in self.market_plugins:
            return {'available': False}
        
        capabilities = self._build_base_capabilities(market_type)
        
        # Enhance with plugin-specific capabilities
        self._add_plugin_capabilities(capabilities, market_type)
        
        return capabilities
    
    def _build_base_capabilities(self, market_type: str) -> Dict[str, Any]:
        """
        Build base capabilities dictionary.
        
        Args:
            market_type: Market type
            
        Returns:
            Base capabilities dictionary
        """
        return {
            'available': True,
            'market_type': market_type,
            'supported_identifiers': []
        }
    
    def _add_plugin_capabilities(self, capabilities: Dict[str, Any], market_type: str):
        """
        Add plugin-specific capabilities to capabilities dictionary.
        
        Modifies capabilities dictionary in place.
        
        Args:
            capabilities: Capabilities dictionary to enhance
            market_type: Market type
        """
        market_plugin = self.market_plugins[market_type]
        
        if not hasattr(market_plugin, 'get_capabilities'):
            return
        
        try:
            plugin_capabilities = market_plugin.get_capabilities()
            capabilities.update(plugin_capabilities)
        except Exception as e:
            logger.warning(f"Failed to get capabilities for {market_type}: {e}")