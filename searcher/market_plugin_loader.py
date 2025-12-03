# File: /map_pro/engines/searcher/market_plugin_loader.py

"""
Market Plugin Loader
====================

Dynamically loads market-specific searcher plugins.
Handles plugin discovery, validation, and initialization.

Responsibilities:
- Scan markets directory for plugins
- Load and instantiate market searchers
- Handle loading errors gracefully
- Report loading results
"""

import importlib
from typing import Dict, Any
from pathlib import Path

from core.system_logger import get_logger
from core.data_paths import map_pro_paths

logger = get_logger(__name__, 'engine')

# Plugin loading constants
EXCLUDED_DIRECTORIES = ['base', '__pycache__']


class MarketPluginLoader:
    """Loads market-specific searcher plugins dynamically."""
    
    def __init__(self):
        """Initialize plugin loader."""
        self.markets_path = map_pro_paths.markets
    
    def load_plugins(self) -> Dict[str, Any]:
        """
        Load all available market searcher plugins.
        
        Loads available markets gracefully - missing markets don't break working ones.
        Looks for plugins in: markets/{market}/{market}_searcher/{market}_searcher.py
        
        Returns:
            Dictionary mapping market names to searcher instances
        """
        if not self.markets_path.exists():
            logger.warning(f"Markets directory not found: {self.markets_path}")
            return {}
        
        logger.info("Loading market plugins...")
        
        # Track loading results
        loaded_markets = []
        failed_markets = []
        
        # Scan for market directories
        for market_dir in self.markets_path.iterdir():
            if not self._is_valid_market_directory(market_dir):
                continue
            
            market_name = market_dir.name
            
            # Try to load the market plugin
            plugin_result = self._load_market_plugin(market_name, market_dir)
            
            if plugin_result['success']:
                loaded_markets.append((market_name, plugin_result['instance']))
            elif plugin_result.get('attempted'):
                failed_markets.append(
                    f"{market_name} (error: {plugin_result.get('error', 'unknown')})"
                )
        
        # Create plugin dictionary
        plugins = {name: instance for name, instance in loaded_markets}
        
        # Report results
        self._report_loading_results(loaded_markets, failed_markets)
        
        return plugins
    
    def _is_valid_market_directory(self, market_dir: Path) -> bool:
        """
        Check if directory is a valid market directory.
        
        Args:
            market_dir: Directory path to check
            
        Returns:
            True if valid market directory
        """
        if not market_dir.is_dir():
            return False
        
        if market_dir.name in EXCLUDED_DIRECTORIES:
            return False
        
        return True
    
    def _load_market_plugin(
        self,
        market_name: str,
        market_dir: Path
    ) -> Dict[str, Any]:
        """
        Load a single market plugin.
        
        Args:
            market_name: Name of the market
            market_dir: Market directory path
            
        Returns:
            Dictionary with loading result
        """
        # Define possible plugin locations
        possible_locations = self._get_plugin_locations(market_name, market_dir)
        
        # Try each location
        for searcher_path, module_path in possible_locations:
            if searcher_path.exists():
                result = self._try_load_from_location(
                    market_name, searcher_path, module_path
                )
                
                if result['success']:
                    return result
                
                # If instantiation failed, don't try other locations
                if result.get('attempted'):
                    return result
        
        # No plugin found in any location
        logger.debug(
            f"Market {market_name}: no searcher module found in any expected location"
        )
        return {'success': False, 'attempted': False}
    
    def _get_plugin_locations(
        self,
        market_name: str,
        market_dir: Path
    ) -> list:
        """
        Get possible plugin file locations for a market.
        
        Args:
            market_name: Name of the market
            market_dir: Market directory path
            
        Returns:
            List of (file_path, module_path) tuples
        """
        return [
            # Location 1: Direct file (legacy/simple structure)
            (
                market_dir / f"{market_name}_searcher.py",
                f"markets.{market_name}.{market_name}_searcher"
            ),
            
            # Location 2: Subdirectory structure (current structure)
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
        Try to load plugin from specific location.
        
        Args:
            market_name: Name of the market
            searcher_path: Path to searcher file
            module_path: Python module path
            
        Returns:
            Dictionary with loading result
        """
        try:
            logger.info(
                f"Attempting to load market plugin: {market_name} "
                f"from {searcher_path}"
            )
            
            # Import the market searcher module
            module = importlib.import_module(module_path)
            
            # Look for the searcher class
            class_name = f"{market_name.upper()}Searcher"
            
            if not hasattr(module, class_name):
                logger.warning(
                    f"Market {market_name}: {class_name} class not found "
                    f"in {module_path}"
                )
                return {'success': False, 'attempted': False}
            
            # Get and instantiate the class
            searcher_class = getattr(module, class_name)
            searcher_instance = searcher_class()
            
            logger.info(f"Successfully loaded market plugin: {market_name}")
            
            return {
                'success': True,
                'instance': searcher_instance,
                'attempted': True
            }
            
        except ImportError as e:
            logger.debug(f"Failed to import {module_path}: {e}")
            return {'success': False, 'attempted': False}
            
        except Exception as e:
            logger.warning(f"Failed to instantiate {market_name} plugin: {e}")
            return {
                'success': False,
                'attempted': True,
                'error': str(e)
            }
    
    def _report_loading_results(
        self,
        loaded_markets: list,
        failed_markets: list
    ) -> None:
        """
        Report plugin loading results.
        
        Args:
            loaded_markets: List of successfully loaded markets
            failed_markets: List of failed market loads
        """
        if loaded_markets:
            market_names = [name for name, _ in loaded_markets]
            logger.info(
                f"Successfully loaded {len(loaded_markets)} market plugins: "
                f"{', '.join(market_names)}"
            )
        
        if failed_markets:
            logger.warning(
                f"Failed to load {len(failed_markets)} market plugins: "
                f"{', '.join(failed_markets)}"
            )
        
        if not loaded_markets and not failed_markets:
            logger.info("No market plugins found (this is normal during development)")


__all__ = ['MarketPluginLoader']