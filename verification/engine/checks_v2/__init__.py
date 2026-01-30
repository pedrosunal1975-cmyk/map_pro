# Path: verification/engine/checks_v2/__init__.py
"""
XBRL Verification Checks Module (v2)

Reorganized verification architecture with three main sections:

1. CONSTANTS - All configuration values, no hardcoding in working files
   - tolerances: Numeric thresholds
   - patterns: Regex patterns for extraction
   - xbrl: XBRL specification constants
   - naming: Concept name handling constants
   - check_names: Standard check identifiers
   - enums: Type-safe enumerations

2. TOOLS - Specialized, reusable skill modules
   - naming: Concept name normalization
   - period: Period extraction and comparison
   - sign: Sign correction parsing and lookup
   - context: Context classification and grouping
   - fact: Fact finding and parsing
   - dimension: Dimensional structure handling
   - hierarchy: Parent/child relationships
   - calculation: Calculation weights and sums
   - tolerance: Decimal tolerance and comparisons

3. PROCESSORS - Multi-stage verification pipeline
   - stage1_discovery: Structure scanning, identification
   - stage2_preparation: Organization, preparation for verification
   - stage3_verification: Final verification and output

Design Principles:
- Tools are stateless and reusable across all processing stages
- Processors pick the right tool/technique for each situation
- Constants configure, tools do work, processors orchestrate
- All techniques from original checks/ are preserved and consolidated
"""

__version__ = '2.0.0'
__author__ = 'MAP PRO Team'

# Version 2 is under development - imports will be added as modules are completed
