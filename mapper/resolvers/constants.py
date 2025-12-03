"""
File: engines/mapper/resolvers/constants.py
Path: engines/mapper/resolvers/constants.py

Resolver Constants
==================

Centralized constants for concept resolution.
Extracted from concept_resolver.py to eliminate magic values and improve
maintainability.

FLOODGATE UPDATE (2025-11-20):
- Removed 'dei' and 'srt' from NON_MAPPABLE_NAMESPACES
- These are now mapped with proper taxonomy labels
- Only pure code lists (ISO codes, etc.) remain excluded
"""

from typing import Set, Dict, List


# ============================================================================
# NAMESPACE CONSTANTS
# ============================================================================

COMMON_PREFIXES: Set[str] = {
    # ========== US/SEC ==========
    'us-gaap',
    'dei',
    'srt',
    'ecd',              # Exhibit Cover Document
    'cyd',              # Cybersecurity Disclosure
    'country',          # ISO Country codes
    'currency',         # ISO Currency codes
    'exch',             # Stock Exchange
    'naics',            # Industry classification
    'sic',              # Industry classification (legacy)
    'stpr',             # State/Province
    'invest',
    
    # ========== UK/FCA ==========
    'uk-gaap',
    'frc',              # Financial Reporting Council
    'uk-bus',           # UK Business
    'uk-core',          # UK Core taxonomy
    'ukc',              # UK Companies House
    'frs',              # Financial Reporting Standards
    'charities-sorp',   # UK Charities SORP
    
    # ========== European/ESMA ==========
    'esef',             # European Single Electronic Format
    'esef_cor',         # ESEF Core
    'esef_all',         # ESEF All
    'esef-tech',        # ESEF Technical
    'eiopa',            # European Insurance and Occupational Pensions Authority
    'esma',             # European Securities and Markets Authority
    
    # ========== European National GAAPs ==========
    'de-gaap',          # Germany
    'fr-gaap',          # France
    'it-gaap',          # Italy
    'es-gaap',          # Spain
    'nl-gaap',          # Netherlands
    'se-gaap',          # Sweden
    'dk-gaap',          # Denmark
    'no-gaap',          # Norway
    'be-gaap',          # Belgium
    'ch-gaap',          # Switzerland
    'at-gaap',          # Austria
    'fi-gaap',          # Finland
    'pl-gaap',          # Poland
    'ie-gaap',          # Ireland
    'pt-gaap',          # Portugal
    'gr-gaap',          # Greece
    'cz-gaap',          # Czech Republic
    'hu-gaap',          # Hungary
    'ro-gaap',          # Romania
    
    # ========== International Standards ==========
    'ifrs',             # International Financial Reporting Standards
    'ifrs-full',        # IFRS Full taxonomy
    'ias',              # International Accounting Standards
    'iasb',             # International Accounting Standards Board
    'iso4217',          # Currency codes
    'iso3166',          # Country codes
    'lei',              # Legal Entity Identifier
    
    # ========== Industry-Specific International ==========
    'insurance',        # Insurance taxonomy
    'banking',          # Banking taxonomy
    'reit',             # Real Estate Investment Trust
    
    # ========== Asia-Pacific ==========
    'jp-gaap',          # Japan
    'jppfs',            # Japan - Public and Private Sector
    'jpcrp',            # Japan - Corporate Disclosure
    'au-gaap',          # Australia
    'aasb',             # Australian Accounting Standards Board
    'nz-gaap',          # New Zealand
    'nzasb',            # New Zealand Accounting Standards Board
    'sg-gaap',          # Singapore
    'sfrs',             # Singapore Financial Reporting Standards
    'hk-gaap',          # Hong Kong
    'hkfrs',            # Hong Kong Financial Reporting Standards
    'in-gaap',          # India
    'ind-as',           # Indian Accounting Standards
    'kr-gaap',          # South Korea
    'k-gaap',           # Korea GAAP (alternative prefix)
    'kifrs',            # Korean IFRS
    'cn-gaap',          # China
    'cas',              # Chinese Accounting Standards
    'th-gaap',          # Thailand
    'tfrs',             # Thai Financial Reporting Standards
    'my-gaap',          # Malaysia
    'mfrs',             # Malaysian Financial Reporting Standards
    'id-gaap',          # Indonesia
    'psak',             # Indonesian Accounting Standards
    'ph-gaap',          # Philippines
    'pfrs',             # Philippine Financial Reporting Standards
    'vn-gaap',          # Vietnam
    'vas',              # Vietnamese Accounting Standards
    'tw-gaap',          # Taiwan
    'tifrs',            # Taiwan IFRS
    
    # ========== Middle East ==========
    'ae-gaap',          # United Arab Emirates
    'sa-gaap',          # Saudi Arabia
    'socpa',            # Saudi Organization for CPAs
    'il-gaap',          # Israel
    
    # ========== Latin America ==========
    'br-gaap',          # Brazil
    'cpc',              # Brazilian Accounting Standards
    'mx-gaap',          # Mexico
    'nif',              # Mexican Financial Reporting Standards
    'ar-gaap',          # Argentina
    'cl-gaap',          # Chile
    'co-gaap',          # Colombia
    'pe-gaap',          # Peru
    
    # ========== Africa ==========
    'za-gaap',          # South Africa
    'saica',            # South African Institute of Chartered Accountants
    'ng-gaap',          # Nigeria
    'ke-gaap',          # Kenya
    'eg-gaap',          # Egypt
    
    # ========== Other Regions ==========
    'ca-gaap',          # Canada
    'aspe',             # Canadian Accounting Standards for Private Enterprises
    'ru-gaap',          # Russia
    'tr-gaap',          # Turkey
    
    # ========== XBRL Core ==========
    'xbrli',            # XBRL Instance
    'generic',          # XBRL Generic
    'bus',              # Business
}

# ULTRA-FLOODGATE: Map EVERYTHING! No namespace exclusions.
# All namespaces (dei, srt, country, currency, naics, sic, etc.) are now mapped
NON_MAPPABLE_NAMESPACES: Set[str] = set()  # Empty - no exclusions!


# ============================================================================
# PATTERN MATCHING CONSTANTS
# ============================================================================

# FLOODGATE: Removed all document/entity patterns - let them be mapped
# Only keeping extensible list/enumeration references (these are pointers, not data)
NON_MAPPABLE_PATTERNS: List[str] = [
    'ExtensibleList',
    'ExtensibleEnumeration',
]


# ============================================================================
# FINANCIAL CONCEPT MAPPINGS
# ============================================================================

FINANCIAL_MAPPINGS: Dict[str, List[str]] = {
    'incentives': ['IncentiveCompensation', 'AccruedCompensation'],
    'client': ['CustomerReceivables', 'CustomerDeposits'],
    'territory': ['GeographicConcentrationRisk', 'SegmentReportingInformation'],
    'settlement': ['SettlementLiability', 'AccruedLiabilities'],
    'omnibus': ['ContractualCommitments', 'RelatedPartyTransactions'],
    'conversion': ['ConversionRights', 'DerivativeAssets'],
    'sharing': ['RevenueSharing', 'ProfitSharingArrangements'],
    'recovery': ['RecoveryOfBadDebt', 'OtherReceivables'],
    'receivable': ['AccountsReceivable', 'OtherReceivables'],
    'liability': ['AccruedLiabilities', 'OtherLiabilities'],
    'losses': ['LossContingency', 'ImpairmentOfInvestments'],
    'collateral': ['CollateralAssets', 'SecuritiesCollateral'],
    'escrow': ['RestrictedCash', 'EscrowDeposits']
}


# ============================================================================
# MATCHING CONFIGURATION
# ============================================================================

# Semantic similarity matching threshold (0.0-1.0)
SEMANTIC_SIMILARITY_THRESHOLD: float = 0.5

# Bonus confidence added to semantic similarity scores
SEMANTIC_SIMILARITY_BONUS: float = 0.05

# Maximum number of base names to search in semantic similarity
SEMANTIC_SIMILARITY_SEARCH_LIMIT: int = 500


# ============================================================================
# XBRL TYPE MAPPING
# ============================================================================

NUMERIC_TYPE_KEYWORDS: List[str] = [
    'monetary',
    'decimal',
    'integer',
    'float',
    'num'
]

DATE_TIME_TYPE_KEYWORDS: List[str] = [
    'date',
    'time'
]

PERCENT_RATIO_TYPE_KEYWORDS: List[str] = [
    'percent',
    'ratio'
]


__all__ = [
    'COMMON_PREFIXES',
    'NON_MAPPABLE_NAMESPACES',
    'NON_MAPPABLE_PATTERNS',
    'FINANCIAL_MAPPINGS',
    'SEMANTIC_SIMILARITY_THRESHOLD',
    'SEMANTIC_SIMILARITY_BONUS',
    'SEMANTIC_SIMILARITY_SEARCH_LIMIT',
    'NUMERIC_TYPE_KEYWORDS',
    'DATE_TIME_TYPE_KEYWORDS',
    'PERCENT_RATIO_TYPE_KEYWORDS',
]