"""
Map Pro Taxonomy Configuration
==============================

Central configuration for standard XBRL taxonomy downloads.
Inspired by xbrl_parser's librarian_config.py but adapted for map_pro architecture.

Architecture: Multi-market taxonomy support with authentication handling.

IMPORTANT: This file contains market-specific taxonomy configuration data.
TODO: In future refactoring, this data should be:
  1. Moved to /map_pro/config/taxonomies/ directory as JSON/YAML files, OR
  2. Moved to individual market plugin directories (/map_pro/markets/<market>/taxonomies/), OR
  3. Stored in database for dynamic configuration

Current location (engines/librarian/) is acceptable as this data is:
  - Reference data used by all markets
  - Not hardcoded logic or market-specific code
  - Taxonomy metadata that doesn't change frequently
  
However, for best practices, configuration data should be separated from code.
"""

from typing import List, Dict, Any, Optional


# Global taxonomy configurations
TAXONOMY_CONFIGS = [
    # US GAAP (SEC Market) - Multiple versions for historical compatibility
    {
        'taxonomy_name': 'us-gaap',
        'version': '2025',
        'authority': 'FASB',
        'namespace': 'http://fasb.org/us-gaap/2025',  # Normalized: Removed date suffix
        'url': 'https://xbrl.fasb.org/us-gaap/2025/us-gaap-2025.zip',
        'folder_name': 'us-gaap-2025',
        'file_type': 'zip',
        'market_types': ['sec'],
        'required': True,
        'credentials_required': False
    },
    {
        'taxonomy_name': 'us-gaap',
        'version': '2024',
        'authority': 'FASB',
        'namespace': 'http://fasb.org/us-gaap/2024',  # Normalized: Removed date suffix
        'url': 'https://xbrl.fasb.org/us-gaap/2024/us-gaap-2024.zip',
        'folder_name': 'us-gaap-2024',
        'file_type': 'zip',
        'market_types': ['sec'],
        'required': True,
        'credentials_required': False
    },
    {
        'taxonomy_name': 'us-gaap',
        'version': '2023',
        'authority': 'FASB',
        'namespace': 'http://fasb.org/us-gaap/2023',  # Normalized: Removed date suffix
        'url': 'https://xbrl.fasb.org/us-gaap/2023/us-gaap-2023.zip',
        'folder_name': 'us-gaap-2023',
        'file_type': 'zip',
        'market_types': ['sec'],
        'required': False,
        'credentials_required': False
    },
    
    # SRT (Statement Reporting Taxonomy) - SEC Market
    {
        'taxonomy_name': 'srt',
        'version': '2025',
        'authority': 'FASB',
        'namespace': 'http://fasb.org/srt/2025',  # Normalized: Removed date suffix
        'url': 'https://xbrl.fasb.org/srt/2025/srt-2025.zip',
        'folder_name': 'srt-2025',
        'file_type': 'zip',
        'market_types': ['sec'],
        'required': True,
        'credentials_required': False
    },
    {
        'taxonomy_name': 'srt',
        'version': '2024',
        'authority': 'FASB',
        'namespace': 'http://fasb.org/srt/2024',  # Normalized: Removed date suffix
        'url': 'https://xbrl.fasb.org/srt/2024/srt-2024.zip',
        'folder_name': 'srt-2024',
        'file_type': 'zip',
        'market_types': ['sec'],
        'required': True,
        'credentials_required': False
    },
    
    # DEI (Document Entity Information) - SEC Market
    {
        'taxonomy_name': 'dei',
        'version': '2024',
        'authority': 'SEC',
        'namespace': 'http://xbrl.sec.gov/dei/2024',
        'url': 'https://xbrl.sec.gov/2024.zip',
        'folder_name': 'dei-2024',
        'file_type': 'zip',
        'market_types': ['sec'],
        'required': True,
        'credentials_required': False
    },
    
    # ECD (Extractable Company Data) - SEC Market
    # FIX: Added missing ECD taxonomy (Issue 1)
    {
        'taxonomy_name': 'ecd',
        'version': '2024',
        'authority': 'SEC',
        'namespace': 'http://xbrl.sec.gov/ecd/2024',
        'url': 'https://xbrl.sec.gov/ecd/2024/ecd-2024.xsd',
        'folder_name': 'ecd-2024',
        'file_type': 'single_file',
        'market_types': ['sec'],
        'required': False,
        'credentials_required': False
    },
    
    # IFRS (Global - FCA, ESMA, ASIC markets)
    {
        'taxonomy_name': 'ifrs',
        'version': '2025',
        'authority': 'IFRS Foundation',
        'namespace': 'http://xbrl.ifrs.org/taxonomy/2025-03-27/ifrs-full',
        'url': 'https://www.ifrs.org/content/dam/ifrs/standards/taxonomy/ifrs-taxonomies/IFRSAT-2025.zip',
        'folder_name': 'ifrs-2025',
        'file_type': 'zip',
        'market_types': ['fca', 'esma', 'asic'],
        'required': True,
        'credentials_required': True,  # IFRS often requires credentials
        'auth_env_vars': ['IFRS_EMAIL', 'IFRS_PASSWORD']
    },
    {
        'taxonomy_name': 'ifrs',
        'version': '2024',
        'authority': 'IFRS Foundation',
        'namespace': 'http://xbrl.ifrs.org/taxonomy/2024-03-27/ifrs-full',
        'url': 'https://www.ifrs.org/content/dam/ifrs/standards/taxonomy/ifrs-taxonomies/IFRSAT-2024-03-27.zip',
        'folder_name': 'ifrs-2024',
        'file_type': 'zip',
        'market_types': ['fca', 'esma', 'asic'],
        'required': True,
        'credentials_required': True,
        'auth_env_vars': ['IFRS_EMAIL', 'IFRS_PASSWORD']
    },
    
    # UK FRC (FCA Market)
    {
        'taxonomy_name': 'frc',
        'version': '2025',
        'authority': 'FRC',
        'namespace': 'http://www.frc.org.uk/fr/gaap/pt/2025-01-01',
        'url': 'https://www.frc.org.uk/documents/7759/FRC-2025-Taxonomy-v1.0.0_LK4mek8.zip',
        'folder_name': 'frc-2025',
        'file_type': 'zip',
        'market_types': ['fca'],
        'required': True,
        'credentials_required': False
    },
    {
        'taxonomy_name': 'frc',
        'version': '2024',
        'authority': 'FRC',
        'namespace': 'http://www.frc.org.uk/fr/gaap/pt/2024-01-01',
        'url': 'https://www.frc.org.uk/documents/6566/FRC-2024-Taxonomy-v1.0.0_GJp67Do.zip',
        'folder_name': 'frc-2024',
        'file_type': 'zip',
        'market_types': ['fca'],
        'required': True,
        'credentials_required': False
    },
    
    # EU ESMA (ESMA Market)
    {
        'taxonomy_name': 'esef',
        'version': '2024',
        'authority': 'ESMA',
        'namespace': 'http://www.esma.europa.eu/taxonomy/2024-01-01/esef',
        'url': 'https://www.esma.europa.eu/sites/default/files/2025-01/esef_taxonomy_2024.zip',
        'folder_name': 'esef-2024',
        'file_type': 'zip',
        'market_types': ['esma'],
        'required': True,
        'credentials_required': False
    },
    
    # XBRL International Taxonomies
    {
        'taxonomy_name': 'xbrl-utr',
        'version': '2024',
        'authority': 'XBRL International',
        'namespace': 'http://www.xbrl.org/2009/utr',
        'url': 'https://www.xbrl.org/packages/utr-2024-01-31.zip',
        'folder_name': 'xbrl-utr-2024',
        'file_type': 'zip',
        'market_types': ['sec', 'fca', 'esma', 'asic'],
        'required': False,
        'credentials_required': False
    },
    {
        'taxonomy_name': 'xbrl-currency',
        'version': '2025',
        'authority': 'XBRL International',
        'namespace': 'http://www.xbrl.org/2003/iso4217',
        'url': 'https://www.xbrl.org/taxonomy/int/currency/currency-REC-2025-05-06.zip',
        'folder_name': 'xbrl-currency-2025',
        'file_type': 'zip',
        'market_types': ['sec', 'fca', 'esma', 'asic'],
        'required': False,
        'credentials_required': False
    }
]


def get_taxonomies_for_market(market_type: str, required_only: bool = True) -> List[Dict[str, Any]]:
    """
    Get taxonomy configurations for specific market.
    
    Args:
        market_type: Market identifier (sec, fca, esma, asic)
        required_only: If True, return only required taxonomies
        
    Returns:
        List of taxonomy configurations
    """
    results = []
    for config in TAXONOMY_CONFIGS:
        if market_type in config.get('market_types', []):
            if not required_only or config.get('required', False):
                results.append(config)
    return results


def get_all_taxonomies() -> List[Dict[str, Any]]:
    """Get all available taxonomy configurations."""
    return TAXONOMY_CONFIGS.copy()


def get_taxonomy_by_name(taxonomy_name: str, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get specific taxonomy configuration by name and optional version.
    
    Args:
        taxonomy_name: Taxonomy name (e.g., 'us-gaap', 'ifrs')
        version: Optional version string (e.g., '2025', '2024')
        
    Returns:
        Taxonomy configuration or None if not found
    """
    for config in TAXONOMY_CONFIGS:
        if config['taxonomy_name'] == taxonomy_name:
            if version is None or config['version'] == version:
                return config
    return None


def validate_market_coverage(market_type: str) -> Dict[str, Any]:
    """
    Validate taxonomy coverage for market type.
    
    Args:
        market_type: Market identifier
        
    Returns:
        Dictionary with coverage details
    """
    required = get_taxonomies_for_market(market_type, required_only=True)
    all_taxonomies = get_taxonomies_for_market(market_type, required_only=False)
    
    return {
        'market_type': market_type,
        'required_taxonomies': len(required),
        'total_taxonomies': len(all_taxonomies),
        'taxonomy_names': [f"{t['taxonomy_name']}-{t['version']}" for t in required]
    }


__all__ = [
    'TAXONOMY_CONFIGS',
    'get_taxonomies_for_market',
    'get_all_taxonomies',
    'get_taxonomy_by_name',
    'validate_market_coverage'
]