# Verification Module - Implementation Plan

## Overview

The verification module validates mapped financial statements for quality assessment. It determines whether company-provided XBRL filings are consistent, accurate, and suitable for financial analysis.

**Key Principle**: We do NOT correct company data. We detect and report inconsistencies in what companies have declared.

---

## Module Architecture (IPO Pattern)

```
verification/
├── __init__.py
├── verify.py                      # Main CLI entry point
├── constants.py                   # Module-wide constants
│
├── core/                          # Configuration & Utilities
│   ├── __init__.py
│   ├── config_loader.py           # Load VERIFICATION_* from .env
│   ├── data_paths.py              # Create /mnt/map_pro/verification/
│   └── logger.py                  # IPO-based logging setup
│
├── loaders/                       # INPUT: Data Access Layer
│   ├── __init__.py
│   ├── constants.py               # Loader-specific constants
│   ├── mapped_data.py             # Blind access to mapped statements
│   ├── mapped_reader.py           # Read/interpret mapped statements
│   ├── parsed_data.py             # (copy from mapper) Blind access to parsed.json
│   ├── parsed_reader.py           # Read/interpret parsed.json
│   ├── xbrl_filings.py            # (copy from mapper) Blind access to XBRL files
│   ├── xbrl_reader.py             # Read calculation/presentation linkbases
│   ├── taxonomy.py                # (copy from parser) Blind access to libraries
│   └── taxonomy_reader.py         # Read standard taxonomy definitions
│
├── engine/                        # PROCESS: Verification Logic
│   ├── __init__.py
│   ├── coordinator.py             # Main workflow orchestrator
│   ├── constants.py               # Engine-specific constants
│   │
│   ├── checks/                    # Verification Mechanisms
│   │   ├── __init__.py
│   │   ├── constants.py           # Check-specific constants
│   │   ├── horizontal_checker.py  # Within-statement validation
│   │   ├── vertical_checker.py    # Cross-statement consistency
│   │   └── library_checker.py     # Standard taxonomy conformance
│   │
│   ├── scoring/                   # Score Calculation
│   │   ├── __init__.py
│   │   ├── constants.py           # Scoring thresholds & weights
│   │   ├── score_calculator.py    # Aggregate scores from checks
│   │   └── quality_classifier.py  # Classify overall quality
│   │
│   └── markets/                   # Market-Specific Logic (ONLY place for this)
│       ├── __init__.py
│       ├── registry.py            # Market check registry
│       ├── sec/
│       │   ├── __init__.py
│       │   ├── constants.py       # SEC-specific thresholds
│       │   └── sec_checks.py      # SEC statement conventions
│       └── esef/
│           ├── __init__.py
│           ├── constants.py       # ESEF-specific thresholds
│           └── esef_checks.py     # ESEF/IFRS conventions
│
├── output/                        # OUTPUT: Report Generation
│   ├── __init__.py
│   ├── constants.py               # Output-specific constants
│   ├── report_generator.py        # Create verification report.json
│   ├── summary_exporter.py        # Create human-readable summary
│   └── statement_simplifier.py    # Create simplified statement versions
│
└── models/                        # Data Classes
    ├── __init__.py
    ├── check_result.py            # Individual check results
    ├── verification_result.py     # Complete verification output
    └── simplified_statement.py    # Simplified statement model
```

---

## IPO Data Flow

```
                          INPUT
                            |
         +------------------+------------------+
         |                  |                  |
    [CLI/User]      [File Sources]     [Taxonomy Libraries]
         |                  |                  |
         v                  v                  v
    verify.py         loaders/             loaders/
    - select company   - mapped_data.py    - taxonomy.py
    - select filing    - parsed_data.py    - taxonomy_reader.py
                       - xbrl_filings.py
                            |
                            v
                        PROCESS
                            |
              +-------------+-------------+
              |             |             |
         engine/checks/  engine/checks/  engine/checks/
         horizontal_     vertical_       library_
         checker.py      checker.py      checker.py
              |             |             |
              +-------------+-------------+
                            |
                            v
                    engine/scoring/
                    score_calculator.py
                    quality_classifier.py
                            |
                            v
                         OUTPUT
                            |
         +------------------+------------------+
         |                  |                  |
    output/            output/             output/
    report_            summary_            statement_
    generator.py       exporter.py         simplifier.py
         |                  |                  |
         v                  v                  v
    report.json      summary.txt      simplified_statements/
```

---

## Component Specifications

### 1. Core Components

#### core/config_loader.py
```python
# Pattern from mapper/core/config_loader.py
# Singleton that loads VERIFICATION_* variables from .env

class ConfigLoader:
    _instance = None
    _initialized = False

    # Keys to load:
    # VERIFICATION_DATA_ROOT
    # VERIFICATION_OUTPUT_DIR
    # VERIFICATION_LOG_DIR
    # VERIFICATION_LOG_LEVEL
    # VERIFICATION_MAPPER_OUTPUT_DIR (input path)
    # VERIFICATION_PARSER_OUTPUT_DIR (input path)
    # VERIFICATION_XBRL_FILINGS_PATH (input path)
    # VERIFICATION_TAXONOMY_PATH (input path)
```

#### core/data_paths.py
```python
# Creates directories in data partition
# /mnt/map_pro/verification/
#   ├── reports/           # Verification reports
#   ├── simplified/        # Simplified statements
#   ├── logs/              # IPO logs
#   └── cache/             # Temporary cache
```

#### core/logger.py
```python
# IPO-based logging with separate log files:
# - input_activity.log
# - process_activity.log
# - output_activity.log
# - full_activity.log
```

### 2. Loaders (INPUT Layer)

#### loaders/mapped_data.py - Blind Doorkeeper
```python
# Discovers mapped statement folders
# Does NOT interpret contents
# Returns paths only

class MappedDataLoader:
    MAX_DEPTH = 25

    def discover_all_filings(self) -> list[MappedFilingEntry]:
        """Find all mapped statement folders."""
        # Search for MAIN_FINANCIAL_STATEMENTS.json as marker
        pass

    def get_filing_directory(self, market, company, form, date) -> Path:
        """Get path to specific filing."""
        pass
```

#### loaders/mapped_reader.py - Content Reader
```python
# Reads and interprets mapped statement files
# Returns structured data for verification

class MappedReader:
    def read_main_statements(self, path: Path) -> dict:
        """Load MAIN_FINANCIAL_STATEMENTS.json"""
        pass

    def read_statement_file(self, path: Path) -> Statement:
        """Load individual statement JSON"""
        pass

    def get_all_facts(self, filing_path: Path) -> list[Fact]:
        """Extract all facts from a filing"""
        pass
```

#### loaders/xbrl_reader.py - Linkbase Reader
```python
# Reads company's calculation and presentation linkbases
# Critical for verification: company declares relationships

class XBRLReader:
    def read_calculation_linkbase(self, filing_path: Path) -> CalculationNetwork:
        """Parse company's calculation linkbase"""
        pass

    def read_presentation_linkbase(self, filing_path: Path) -> PresentationNetwork:
        """Parse company's presentation linkbase"""
        pass

    def get_declared_calculations(self, filing_path: Path) -> list[CalculationArc]:
        """Get all calculation relationships company declared"""
        pass
```

### 3. Engine Components (PROCESS Layer)

#### engine/coordinator.py
```python
# Main orchestrator - coordinates all checks

class VerificationCoordinator:
    def __init__(self):
        self.horizontal_checker = HorizontalChecker()
        self.vertical_checker = VerticalChecker()
        self.library_checker = LibraryChecker()
        self.score_calculator = ScoreCalculator()
        self.quality_classifier = QualityClassifier()

    def verify_filing(self, filing_entry: MappedFilingEntry) -> VerificationResult:
        """Run all checks on a single filing"""
        # 1. Load mapped statements
        # 2. Load company's XBRL linkbases
        # 3. Run horizontal checks
        # 4. Run vertical checks
        # 5. Run library checks (optional)
        # 6. Calculate scores
        # 7. Classify quality
        pass

    def verify_all_filings(self) -> list[VerificationResult]:
        """Verify all available filings"""
        pass
```

#### engine/checks/horizontal_checker.py
```python
# Validates within a single statement
# Compares facts against company-declared calculations

class HorizontalChecker:
    """
    HORIZONTAL CHECK (Correctness)

    Within one statement, verify:
    1. Calculation relationships (e.g., Assets = Liabilities + Equity)
    2. Sum totals match detail items
    3. Sign conventions are consistent

    Source of truth: Company's calculation linkbase
    We check if company's facts match their own declared calculations.
    """

    def check_calculation_consistency(
        self,
        statement: Statement,
        calc_network: CalculationNetwork
    ) -> list[CheckResult]:
        """
        For each calculation relationship company declared:
        - Find parent fact value
        - Find all child fact values
        - Apply weights (+1 or -1)
        - Check if sum matches parent
        """
        pass

    def check_total_reconciliation(
        self,
        statement: Statement,
        tolerance: float = 0.01
    ) -> list[CheckResult]:
        """
        Check that items marked as totals equal sum of components.
        Uses presentation hierarchy to identify totals.
        """
        pass
```

#### engine/checks/vertical_checker.py
```python
# Validates consistency across statements
# Cross-statement relationships must hold

class VerticalChecker:
    """
    VERTICAL CHECK (Consistency)

    Across statements, verify:
    1. Balance Sheet balances (Assets = Liabilities + Equity)
    2. Net Income flows to Retained Earnings
    3. Cash Flow ends with Cash position matching Balance Sheet
    4. Common values appear consistently

    These are fundamental accounting relationships.
    """

    def check_balance_sheet_equation(
        self,
        statements: list[Statement]
    ) -> CheckResult:
        """
        Verify: Total Assets = Total Liabilities + Total Equity
        """
        pass

    def check_income_statement_linkage(
        self,
        income_statement: Statement,
        equity_statement: Statement
    ) -> CheckResult:
        """
        Verify: Net Income appears in both statements with same value.
        """
        pass

    def check_cash_flow_ending_balance(
        self,
        cash_flow_statement: Statement,
        balance_sheet: Statement
    ) -> CheckResult:
        """
        Verify: Ending Cash in Cash Flow = Cash in Balance Sheet
        """
        pass
```

#### engine/checks/library_checker.py
```python
# Validates against standard taxonomy definitions
# Optional - runs after company-based checks

class LibraryChecker:
    """
    LIBRARY CHECK (Quality)

    Compare statements against standard taxonomy:
    1. Are concepts used correctly?
    2. Are period types appropriate?
    3. Are value types consistent with taxonomy definitions?

    This is informational - low scores don't invalidate data,
    but may indicate unusual reporting choices.
    """

    def check_concept_usage(
        self,
        statements: list[Statement],
        taxonomy: TaxonomyDefinition
    ) -> list[CheckResult]:
        """
        Check if concepts are used per taxonomy definition.
        """
        pass

    def check_period_type_consistency(
        self,
        facts: list[Fact],
        taxonomy: TaxonomyDefinition
    ) -> list[CheckResult]:
        """
        Instant concepts should have instant contexts.
        Duration concepts should have duration contexts.
        """
        pass
```

#### engine/scoring/score_calculator.py
```python
# Aggregates check results into scores

class ScoreCalculator:
    """
    Score Calculation

    Each check produces:
    - passed: bool
    - severity: critical | warning | info
    - difference: numeric (for calculation checks)

    Scores are calculated per category:
    - horizontal_score: 0-100
    - vertical_score: 0-100
    - library_score: 0-100 (optional)
    - overall_score: 0-100 (weighted average)
    """

    def calculate_scores(
        self,
        check_results: list[CheckResult]
    ) -> VerificationScores:
        """Calculate all scores from check results."""
        pass
```

#### engine/scoring/quality_classifier.py
```python
# Classifies overall quality level

class QualityClassifier:
    """
    Quality Classification

    Based on scores, classify filing as:
    - EXCELLENT (90-100): Fully consistent, ready for analysis
    - GOOD (75-89): Minor issues, usable with caution
    - FAIR (50-74): Notable issues, limited analysis value
    - POOR (25-49): Significant issues, use at own risk
    - UNUSABLE (0-24): Major inconsistencies, not recommended

    Thresholds are in constants.py
    """

    def classify(self, scores: VerificationScores) -> QualityLevel:
        """Determine quality level from scores."""
        pass
```

### 4. Market-Specific Logic

#### engine/markets/sec/sec_checks.py
```python
# SEC-specific validation rules

class SECChecks:
    """
    SEC-specific checks:
    - Form 10-K should have complete annual statements
    - Form 10-Q should have quarterly statements
    - DEI (Document and Entity Information) validation
    """
    pass
```

#### engine/markets/esef/esef_checks.py
```python
# ESEF-specific validation rules

class ESEFChecks:
    """
    ESEF-specific checks:
    - IFRS concept usage
    - Block tagging requirements
    - Mandatory disclosures
    """
    pass
```

### 5. Output Components (OUTPUT Layer)

#### output/report_generator.py
```python
# Creates verification report.json

class ReportGenerator:
    """
    Creates comprehensive verification report:

    report.json:
    {
        "filing_info": {...},
        "verification_timestamp": "...",
        "scores": {
            "horizontal_score": 95,
            "vertical_score": 88,
            "library_score": 72,
            "overall_score": 85
        },
        "quality_level": "GOOD",
        "check_results": {
            "horizontal": [...],
            "vertical": [...],
            "library": [...]
        },
        "issues_summary": {
            "critical": 0,
            "warnings": 3,
            "info": 12
        },
        "recommendation": "Filing is suitable for financial analysis."
    }
    """
    pass
```

#### output/statement_simplifier.py
```python
# Creates simplified statement versions

class StatementSimplifier:
    """
    Creates simplified versions of statements:

    1. Extracts key financial metrics
    2. Removes granular detail items
    3. Normalizes naming conventions
    4. Creates analysis-ready format

    Output structure:
    simplified_statements/
    ├── balance_sheet_simple.json
    ├── income_statement_simple.json
    ├── cash_flow_simple.json
    └── key_metrics.json

    Simplification rules are in constants.py - NOT hardcoded.
    """
    pass
```

---

## Environment Configuration

Add to map_pro/.env:
```bash
# ==============================================================================
# VERIFICATION MODULE CONFIGURATION
# ==============================================================================
# Base Paths
VERIFICATION_DATA_ROOT=/mnt/map_pro/verification
VERIFICATION_LOADERS_ROOT=/mnt/map_pro

# Input Paths (Read from other modules)
VERIFICATION_MAPPER_OUTPUT_DIR=${VERIFICATION_LOADERS_ROOT}/mapper/mapped_statements
VERIFICATION_PARSER_OUTPUT_DIR=${VERIFICATION_LOADERS_ROOT}/parser/parsed_reports
VERIFICATION_XBRL_FILINGS_PATH=${VERIFICATION_LOADERS_ROOT}/downloader/entities
VERIFICATION_TAXONOMY_PATH=${VERIFICATION_LOADERS_ROOT}/taxonomies/libraries

# Output Paths
VERIFICATION_OUTPUT_DIR=${VERIFICATION_DATA_ROOT}/reports
VERIFICATION_SIMPLIFIED_DIR=${VERIFICATION_DATA_ROOT}/simplified

# Logging
VERIFICATION_LOG_DIR=${VERIFICATION_DATA_ROOT}/logs
VERIFICATION_LOG_LEVEL=INFO
VERIFICATION_LOG_FORMAT=json
VERIFICATION_LOG_ROTATION=daily
VERIFICATION_LOG_RETENTION_DAYS=30
VERIFICATION_STRUCTURED_LOGGING=true

# Verification Configuration
VERIFICATION_CALCULATION_TOLERANCE=0.01
VERIFICATION_ENABLE_LIBRARY_CHECKS=true
VERIFICATION_STRICT_MODE=false
VERIFICATION_CONTINUE_ON_ERROR=true

# Scoring Thresholds
VERIFICATION_EXCELLENT_THRESHOLD=90
VERIFICATION_GOOD_THRESHOLD=75
VERIFICATION_FAIR_THRESHOLD=50
VERIFICATION_POOR_THRESHOLD=25

# Score Weights
VERIFICATION_HORIZONTAL_WEIGHT=0.40
VERIFICATION_VERTICAL_WEIGHT=0.40
VERIFICATION_LIBRARY_WEIGHT=0.20

# Performance
VERIFICATION_MAX_CONCURRENT_JOBS=3
VERIFICATION_BATCH_SIZE=10
```

---

## Output Directory Structure

```
/mnt/map_pro/verification/
├── reports/
│   └── {market}/
│       └── {company}/
│           └── {form}/
│               └── {date}/
│                   ├── report.json          # Full verification report
│                   └── summary.txt          # Human-readable summary
├── simplified/
│   └── {market}/
│       └── {company}/
│           └── {form}/
│               └── {date}/
│                   ├── balance_sheet.json
│                   ├── income_statement.json
│                   ├── cash_flow.json
│                   └── key_metrics.json
├── logs/
│   ├── input_activity.log
│   ├── process_activity.log
│   ├── output_activity.log
│   └── full_activity.log
└── cache/
    └── (temporary files)
```

---

## CLI Interface (verify.py)

```
$ python verify.py

========================================
VERIFICATION MODULE
========================================

Available Companies with Mapped Statements:
  1. sec / Apple_Inc / 10-K / 2024-01-15
  2. sec / Microsoft_Corporation / 10-K / 2024-02-01
  3. esef / Tesco_PLC / AFR / 2024-05-20
  0. Exit

Enter selection: 1

========================================
VERIFYING: Apple_Inc / 10-K / 2024-01-15
========================================

[INPUT] Loading mapped statements...
[INPUT] Loading company XBRL linkbases...
[PROCESS] Running horizontal checks... 15/15 passed
[PROCESS] Running vertical checks... 4/5 passed
[PROCESS] Running library checks... 42/50 passed
[PROCESS] Calculating scores...

========================================
VERIFICATION RESULTS
========================================
Horizontal Score: 100/100
Vertical Score:   80/100
Library Score:    84/100
Overall Score:    88/100

Quality Level: GOOD

Issues Found:
- WARNING: Cash Flow ending balance differs from Balance Sheet by $1,234
- INFO: 8 concepts not found in standard taxonomy

[OUTPUT] Report saved: /mnt/map_pro/verification/reports/sec/Apple_Inc/10-K/2024-01-15/report.json
[OUTPUT] Summary saved: /mnt/map_pro/verification/reports/sec/Apple_Inc/10-K/2024-01-15/summary.txt

Generate simplified statements? [y/n]: y
[OUTPUT] Simplified statements saved to: /mnt/map_pro/verification/simplified/...

========================================
Continue with another filing? [y/n]:
```

---

## Data Models

#### models/check_result.py
```python
@dataclass
class CheckResult:
    check_name: str              # e.g., "balance_sheet_equation"
    check_type: str              # horizontal | vertical | library
    passed: bool
    severity: str                # critical | warning | info
    message: str                 # Human-readable description
    expected_value: Optional[float]
    actual_value: Optional[float]
    difference: Optional[float]
    details: dict                # Additional context
```

#### models/verification_result.py
```python
@dataclass
class VerificationResult:
    filing_id: str
    market: str
    company: str
    form: str
    date: str

    scores: VerificationScores
    quality_level: str

    horizontal_results: list[CheckResult]
    vertical_results: list[CheckResult]
    library_results: list[CheckResult]

    issues_summary: dict[str, int]  # {critical: 0, warnings: 2, info: 5}
    recommendation: str

    verified_at: datetime
    processing_time_seconds: float

@dataclass
class VerificationScores:
    horizontal_score: float  # 0-100
    vertical_score: float    # 0-100
    library_score: float     # 0-100
    overall_score: float     # 0-100 (weighted)
```

---

## Constants Files

#### constants.py (module-level)
```python
# Path: verification/constants.py

# Quality Levels
QUALITY_EXCELLENT = 'EXCELLENT'
QUALITY_GOOD = 'GOOD'
QUALITY_FAIR = 'FAIR'
QUALITY_POOR = 'POOR'
QUALITY_UNUSABLE = 'UNUSABLE'

# Check Types
CHECK_TYPE_HORIZONTAL = 'horizontal'
CHECK_TYPE_VERTICAL = 'vertical'
CHECK_TYPE_LIBRARY = 'library'

# Severity Levels
SEVERITY_CRITICAL = 'critical'
SEVERITY_WARNING = 'warning'
SEVERITY_INFO = 'info'

# IPO Logging Prefixes
LOG_INPUT = '[INPUT]'
LOG_PROCESS = '[PROCESS]'
LOG_OUTPUT = '[OUTPUT]'

# File markers
MAIN_STATEMENTS_FILE = 'MAIN_FINANCIAL_STATEMENTS.json'
REPORT_FILE = 'report.json'
SUMMARY_FILE = 'summary.txt'

# Max recursion depth for file discovery
MAX_SEARCH_DEPTH = 25
```

#### engine/checks/constants.py
```python
# Path: verification/engine/checks/constants.py

# Horizontal Check Names
CHECK_CALCULATION_CONSISTENCY = 'calculation_consistency'
CHECK_TOTAL_RECONCILIATION = 'total_reconciliation'
CHECK_SIGN_CONVENTION = 'sign_convention'

# Vertical Check Names
CHECK_BALANCE_SHEET_EQUATION = 'balance_sheet_equation'
CHECK_INCOME_LINKAGE = 'income_statement_linkage'
CHECK_CASH_FLOW_LINKAGE = 'cash_flow_linkage'
CHECK_RETAINED_EARNINGS_ROLL = 'retained_earnings_rollforward'

# Default Tolerances
DEFAULT_CALCULATION_TOLERANCE = 0.01  # 1%
DEFAULT_ROUNDING_TOLERANCE = 1.0      # $1 for small differences
```

#### engine/scoring/constants.py
```python
# Path: verification/engine/scoring/constants.py

# Default Thresholds (can be overridden by .env)
DEFAULT_EXCELLENT_THRESHOLD = 90
DEFAULT_GOOD_THRESHOLD = 75
DEFAULT_FAIR_THRESHOLD = 50
DEFAULT_POOR_THRESHOLD = 25

# Default Weights
DEFAULT_HORIZONTAL_WEIGHT = 0.40
DEFAULT_VERTICAL_WEIGHT = 0.40
DEFAULT_LIBRARY_WEIGHT = 0.20

# Severity Penalties
CRITICAL_PENALTY = 25.0   # Points deducted for critical issue
WARNING_PENALTY = 5.0     # Points deducted for warning
INFO_PENALTY = 0.5        # Points deducted for info
```

---

## Implementation Phases

### Phase 1: Foundation
1. Create directory structure
2. Implement core/config_loader.py
3. Implement core/data_paths.py
4. Implement core/logger.py
5. Add VERIFICATION_* variables to .env
6. Create constants.py files

### Phase 2: Loaders (INPUT)
1. Copy xbrl_filings.py, parsed_data.py, taxonomy.py from mapper/parser
2. Implement mapped_data.py (blind access)
3. Implement mapped_reader.py
4. Implement xbrl_reader.py (calculation linkbase focus)
5. Implement taxonomy_reader.py

### Phase 3: Checks (PROCESS)
1. Implement horizontal_checker.py
2. Implement vertical_checker.py
3. Implement library_checker.py
4. Implement market-specific checks (SEC, ESEF)

### Phase 4: Scoring (PROCESS)
1. Implement score_calculator.py
2. Implement quality_classifier.py

### Phase 5: Coordinator (PROCESS)
1. Implement coordinator.py
2. Wire all components together

### Phase 6: Output (OUTPUT)
1. Implement report_generator.py
2. Implement summary_exporter.py
3. Implement statement_simplifier.py

### Phase 7: CLI
1. Implement verify.py
2. Add company/filing selection
3. Display results formatting

### Phase 8: Integration
1. Test with SEC filings
2. Test with ESEF filings
3. Integrate into main.py (optional)

---

## Key Verification Checks Detail

### Horizontal Checks (Within Statement)

| Check | Description | Source |
|-------|-------------|--------|
| Calculation Consistency | Facts match company-declared calc relationships | Company's calculation linkbase |
| Total Reconciliation | Total items = sum of component items | Presentation hierarchy |
| Sign Convention | Credit/debit signs are consistent | Calculation arc weights |

### Vertical Checks (Across Statements)

| Check | Description | Formula |
|-------|-------------|---------|
| Balance Sheet Equation | Assets = Liabilities + Equity | A = L + E |
| Net Income Linkage | IS Net Income = Equity Change | From Income Statement to Equity |
| Cash Flow Ending | CF Ending Cash = BS Cash | End of Cash Flow = Balance Sheet |
| Retained Earnings | Prior RE + NI - Div = Current RE | Rollforward check |

### Library Checks (Standard Taxonomy)

| Check | Description | Source |
|-------|-------------|--------|
| Concept Validity | Concepts exist in declared taxonomy | Standard taxonomy files |
| Period Type Match | Instant/duration context matches concept | Taxonomy definition |
| Balance Type Match | Debit/credit matches taxonomy | Taxonomy definition |

---

## Design Principles Compliance

| Principle | Implementation |
|-----------|----------------|
| No hardcoding | All thresholds in constants.py or .env |
| Market-agnostic core | Only engine/markets/ has market-specific code |
| IPO architecture | loaders/ (I), engine/ (P), output/ (O) |
| File path comments | All files start with `# Path: verification/...` |
| Company data as primary | We detect issues, never correct data |
| Taxonomy agnostic | No embedded taxonomy knowledge |
| Lowercase conventions | Use dict, list, any, not Dict, List, Any |
| Clear, testable functions | Each function has single responsibility |
| No capital letters in code | Follow existing codebase style |
| Output to data partition | /mnt/map_pro/verification/ |

---

## Files to Copy from Other Modules

From `mapper/loaders/`:
- xbrl_filings.py (adapt path config to VERIFICATION_*)
- parsed_data.py (adapt path config to VERIFICATION_*)

From `parser/loaders/`:
- taxonomy.py (adapt path config to VERIFICATION_*)

From `library/loaders/`:
- parsed_reader.py (reference pattern)
- taxonomy_reader.py (reference pattern)

---

## Testing Strategy

```
tests/
└── verification/
    ├── __init__.py
    ├── test_loaders/
    │   ├── test_mapped_data.py
    │   ├── test_mapped_reader.py
    │   └── test_xbrl_reader.py
    ├── test_checks/
    │   ├── test_horizontal_checker.py
    │   ├── test_vertical_checker.py
    │   └── test_library_checker.py
    ├── test_scoring/
    │   ├── test_score_calculator.py
    │   └── test_quality_classifier.py
    └── test_integration/
        └── test_full_verification.py
```

---

## Dependencies

Existing (no new packages needed):
- pathlib (file operations)
- json (data serialization)
- logging (logging framework)
- dataclasses (data models)
- typing (type hints)
- python-dotenv (env configuration)

---

## Success Criteria

1. Can discover all mapped filings from CLI
2. Horizontal checks validate company-declared calculations
3. Vertical checks validate cross-statement relationships
4. Scores accurately reflect data quality
5. Reports clearly identify issues
6. Simplified statements extract key metrics
7. Works for both SEC and ESEF filings
8. No hardcoded values outside constants.py
9. All market-specific code in engine/markets/
10. Follows existing codebase patterns exactly
