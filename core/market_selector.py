"""
Map Pro Market Selector
=======================

Market-agnostic market selection and prompt module loading.
Handles market discovery and dynamic loading of market-specific prompt modules.

Architecture:
- Discovers available markets from markets/ directory
- Loads market-specific prompt modules dynamically
- Provides market selection interface
- 100% market-agnostic - no hardcoded market names

Save location: core/market_selector.py
"""

import os
import importlib
from typing import Dict, Any, List, Optional
from pathlib import Path

from .system_logger import get_logger
from .data_paths import map_pro_paths

logger = get_logger(__name__, 'core')


class MarketPromptsInterface:
    """
    Interface that all market-specific prompt modules must implement.
    
    Each market must provide:
    - prompt_for_company_identifier(): Get company identifier
    - prompt_for_filing_type(): Get filing type
    """
    
    def prompt_for_company_identifier(self) -> str:
        """Prompt for company identifier (ticker, CIK, company number, etc.)."""
        raise NotImplementedError("Market must implement prompt_for_company_identifier")
    
    def prompt_for_filing_type(self) -> str:
        """Prompt for filing type."""
        raise NotImplementedError("Market must implement prompt_for_filing_type")


def discover_available_markets() -> List[Dict[str, Any]]:
    """
    Discover available markets by scanning markets/ directory.
    
    Returns:
        List of market info dictionaries
    """
    markets = []
    markets_dir = map_pro_paths.program_root / 'markets'
    
    if not markets_dir.exists():
        logger.warning(f"Markets directory not found: {markets_dir}")
        return markets
    
    # Scan markets directory
    for market_dir in markets_dir.iterdir():
        if not market_dir.is_dir():
            continue
        
        market_name = market_dir.name
        
        # Skip base and special directories
        if market_name in ['base', '__pycache__']:
            continue
        
        # Check if market is enabled via environment variable
        env_var_name = f'MAP_PRO_ENABLE_{market_name.upper()}_MARKET'
        is_enabled = os.getenv(env_var_name, 'false').lower() == 'true'
        
        if not is_enabled:
            logger.debug(f"Market {market_name} is disabled in .env (set {env_var_name}=true to enable)")
            continue
        
        # Check if market has interactive prompts module
        prompts_file = market_dir / f"{market_name}_interactive_prompts.py"
        
        if not prompts_file.exists():
            logger.debug(f"Market {market_name} has no interactive prompts module")
            continue
        
        # Market is available
        markets.append({
            'name': market_name,
            'display_name': market_name.upper(),
            'enabled': True,
            'prompts_module': f"markets.{market_name}.{market_name}_interactive_prompts"
        })
    
    return markets


def select_market() -> str:
    """
    Prompt user to select market.
    
    Returns:
        Selected market name (e.g., 'sec', 'fca', 'esma')
    """
    # Discover available markets
    markets = discover_available_markets()
    
    if not markets:
        print("\n[FAIL] No markets available!")
        print("   Please enable at least one market in .env")
        print("   Example: MAP_PRO_ENABLE_SEC_MARKET=true")
        print("            MAP_PRO_ENABLE_FCA_MARKET=true")
        print("            MAP_PRO_ENABLE_ESMA_MARKET=true")
        exit(1)
    
    # If only one market available, use it automatically
    if len(markets) == 1:
        market_name = markets[0]['name']
        print(f"Using market: {markets[0]['display_name']}")
        return market_name
    
    # Multiple markets available - prompt user
    print("Available markets:")
    for i, market in enumerate(markets, 1):
        print(f"  {i}. {market['display_name']}")
    
    print()
    
    while True:
        try:
            choice_input = input(f"Select market (1-{len(markets)}): ").strip()
            choice = int(choice_input)
            
            if 1 <= choice <= len(markets):
                selected_market = markets[choice - 1]
                return selected_market['name']
            
            print(f"[FAIL] Please enter a number between 1 and {len(markets)}")
        
        except ValueError:
            print("[FAIL] Please enter a valid number")
        except KeyboardInterrupt:
            print("\n\n[FAIL] Workflow cancelled by user\n")
            exit(0)


def load_market_prompts(market_type: str) -> MarketPromptsInterface:
    """
    Load market-specific prompts module.
    
    Args:
        market_type: Market identifier (e.g., 'sec', 'fca', 'esma')
        
    Returns:
        Market prompts module instance
        
    Raises:
        ImportError: If market prompts module not found
    """
    try:
        # Construct module path
        module_path = f"markets.{market_type}.{market_type}_interactive_prompts"
        
        logger.info(f"Loading market prompts: {module_path}")
        
        # Import module
        module = importlib.import_module(module_path)
        
        # Get prompts class (should be named like SECInteractivePrompts)
        class_name = f"{market_type.upper()}InteractivePrompts"
        prompts_class = getattr(module, class_name)
        
        # Instantiate and return
        return prompts_class()
    
    except ImportError as e:
        logger.error(f"Failed to load market prompts for {market_type}: {e}")
        print(f"\n[FAIL] Error: Market '{market_type}' prompts module not found")
        print(f"   Expected: markets/{market_type}/{market_type}_interactive_prompts.py")
        exit(1)
    
    except AttributeError as e:
        logger.error(f"Market prompts class not found: {e}")
        print(f"\n[FAIL] Error: Market '{market_type}' prompts class not found")
        print(f"   Expected class: {class_name}")
        exit(1)


__all__ = [
    'MarketPromptsInterface',
    'discover_available_markets',
    'select_market',
    'load_market_prompts',
]