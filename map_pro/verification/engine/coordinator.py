# Path: verification/engine/coordinator.py
"""
Verification Coordinator

Main orchestration for verification module.
Coordinates all checks, scoring, and output generation.

100% AGNOSTIC - coordinates other components without hardcoded logic.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..core.config_loader import ConfigLoader
from ..core.data_paths import DataPathsManager
from ..core.logger.ipo_logging import setup_ipo_logging
from ..loaders.mapped_data import MappedDataLoader, MappedFilingEntry
from ..loaders.mapped_reader import MappedReader, MappedStatements
from ..loaders.xbrl_filings import XBRLFilingsLoader
from ..loaders.xbrl_reader import XBRLReader, CalculationNetwork
from ..loaders.taxonomy_reader import TaxonomyReader
from .checks.horizontal_checker import HorizontalChecker, CheckResult
from .checks.vertical_checker import VerticalChecker
from .checks.library_checker import LibraryChecker
from .scoring.score_calculator import ScoreCalculator, VerificationScores
from .scoring.quality_classifier import QualityClassifier, QualityClassification
from .taxonomy_manager import TaxonomyManager
from .formula_registry import FormulaRegistry
from .markets import get_statement_identifier, MainStatements
from ..constants import LOG_INPUT, LOG_PROCESS, LOG_OUTPUT


@dataclass
class VerificationResult:
    """
    Complete verification result for a filing.

    Attributes:
        filing_id: Unique filing identifier
        market: Market identifier
        company: Company name
        form: Form type
        date: Filing date
        scores: Verification scores
        quality: Quality classification
        horizontal_results: Results from horizontal checks
        vertical_results: Results from vertical checks
        library_results: Results from library checks
        issues_summary: Count of issues by severity
        recommendation: Recommended action
        verified_at: Verification timestamp
        processing_time_seconds: Time taken to verify
        statement_info: Information about statements verified
        taxonomy_status: Status of taxonomy availability
    """
    filing_id: str
    market: str
    company: str
    form: str
    date: str
    scores: VerificationScores = None
    quality: QualityClassification = None
    horizontal_results: list[CheckResult] = field(default_factory=list)
    vertical_results: list[CheckResult] = field(default_factory=list)
    library_results: list[CheckResult] = field(default_factory=list)
    xbrl_calculation_results: list[CheckResult] = field(default_factory=list)
    taxonomy_calculation_results: list[CheckResult] = field(default_factory=list)
    issues_summary: dict = field(default_factory=dict)
    recommendation: str = ''
    verified_at: datetime = None
    processing_time_seconds: float = 0.0
    statement_info: dict = field(default_factory=dict)
    taxonomy_status: dict = field(default_factory=dict)
    formula_registry_summary: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.verified_at is None:
            self.verified_at = datetime.now()


class VerificationCoordinator:
    """
    Main verification workflow orchestrator.

    Coordinates:
    1. Loading mapped statements
    2. Loading company XBRL linkbases
    3. Running horizontal checks
    4. Running vertical checks
    5. Running library checks (optional)
    6. Calculating scores
    7. Classifying quality

    Example:
        coordinator = VerificationCoordinator()

        # Verify all available filings
        results = coordinator.verify_all_filings()

        # Verify specific filing
        result = coordinator.verify_filing(filing_entry)
    """

    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize verification coordinator.

        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        self.logger = logging.getLogger('process.coordinator')

        self.logger.info(f"{LOG_PROCESS} Initializing verification coordinator")

        # Setup logging
        self._setup_logging()

        # Ensure data directories exist
        self._ensure_directories()

        # Initialize loaders
        self.mapped_loader = MappedDataLoader(self.config)
        self.mapped_reader = MappedReader()
        self.xbrl_loader = XBRLFilingsLoader(self.config)
        self.xbrl_reader = XBRLReader(self.config)
        self.taxonomy_reader = TaxonomyReader(self.config)

        # Initialize taxonomy manager for library integration
        self.taxonomy_manager = TaxonomyManager(self.config)

        # Initialize formula registry for XBRL-sourced verification
        self.formula_registry = FormulaRegistry(self.config)

        # Initialize checkers
        tolerance = self.config.get('calculation_tolerance', 0.01)
        rounding = self.config.get('rounding_tolerance', 1.0)

        self.horizontal_checker = HorizontalChecker(tolerance, rounding)
        self.vertical_checker = VerticalChecker(tolerance, rounding, self.formula_registry)
        self.library_checker = LibraryChecker()

        # Configuration for XBRL-sourced verification
        self.enable_xbrl_verification = self.config.get('enable_xbrl_verification', True)

        # Initialize scoring
        h_weight = self.config.get('horizontal_weight', 0.4)
        v_weight = self.config.get('vertical_weight', 0.4)
        l_weight = self.config.get('library_weight', 0.2)

        self.score_calculator = ScoreCalculator(h_weight, v_weight, l_weight)
        self.quality_classifier = QualityClassifier(
            excellent_threshold=self.config.get('excellent_threshold', 90),
            good_threshold=self.config.get('good_threshold', 75),
            fair_threshold=self.config.get('fair_threshold', 50),
            poor_threshold=self.config.get('poor_threshold', 25),
        )

        # Configuration
        self.enable_library_checks = self.config.get('enable_library_checks', True)
        self.continue_on_error = self.config.get('continue_on_error', True)

        self.logger.info(f"{LOG_OUTPUT} Verification coordinator initialized")

    def _setup_logging(self) -> None:
        """Setup IPO-aware logging."""
        log_dir = self.config.get('log_dir')
        if log_dir:
            log_dir = Path(log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)

            setup_ipo_logging(
                log_dir=log_dir,
                log_level=self.config.get('log_level', 'INFO'),
                console_output=True
            )

    def _ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        try:
            manager = DataPathsManager()
            result = manager.ensure_all_directories()
            self.logger.info(f"{LOG_OUTPUT} Directories ready: {len(result['created'])} created")
        except Exception as e:
            self.logger.warning(f"Could not create all directories: {e}")

    def verify_filing(self, filing: MappedFilingEntry) -> VerificationResult:
        """
        Verify a single mapped filing.

        Args:
            filing: MappedFilingEntry from MappedDataLoader

        Returns:
            VerificationResult with all check results and scores
        """
        start_time = datetime.now()
        filing_id = f"{filing.market}/{filing.company}/{filing.form}/{filing.date}"

        self.logger.info(f"{LOG_INPUT} Verifying filing: {filing_id}")

        result = VerificationResult(
            filing_id=filing_id,
            market=filing.market,
            company=filing.company,
            form=filing.form,
            date=filing.date,
        )

        try:
            # Step 1: Load mapped statements
            self.logger.info(f"{LOG_INPUT} Loading mapped statements")
            statements = self.mapped_reader.read_statements(filing)

            if not statements or not statements.statements:
                self.logger.warning(f"{LOG_OUTPUT} No statements found for {filing_id}")
                result.recommendation = "No statements found - cannot verify"
                return result

            self.logger.info(f"{LOG_OUTPUT} Loaded {len(statements.statements)} statements")

            # Step 1b: Identify main statements using market-specific logic
            self.logger.info(f"{LOG_PROCESS} Identifying main statements for {filing.market}")
            main_statements = self._identify_main_statements(filing.market, statements, filing)
            main_statement_names = main_statements.get_names() if main_statements else set()

            self.logger.info(
                f"{LOG_OUTPUT} Identified {len(main_statement_names)} main statements: "
                f"{', '.join(main_statement_names) if main_statement_names else 'none'}"
            )

            # Update statement flags based on market-specific identification
            for stmt in statements.statements:
                stmt.is_main_statement = stmt.name in main_statement_names

            # Track statement info
            result.statement_info = {
                'total_statements': len(statements.statements),
                'main_statements': list(main_statement_names),
                'main_statement_count': len(main_statement_names),
                'total_files': statements.total_statement_files,
                'market': statements.market,
                'identified_main': {
                    'balance_sheet': main_statements.balance_sheet.name if main_statements and main_statements.balance_sheet else None,
                    'income_statement': main_statements.income_statement.name if main_statements and main_statements.income_statement else None,
                    'cash_flow': main_statements.cash_flow.name if main_statements and main_statements.cash_flow else None,
                    'equity_statement': main_statements.equity_statement.name if main_statements and main_statements.equity_statement else None,
                },
                'statements': [
                    {
                        'name': stmt.name,
                        'source_file': stmt.source_file,
                        'file_size_bytes': stmt.file_size_bytes,
                        'is_main': stmt.is_main_statement,
                        'fact_count': len(stmt.facts),
                    }
                    for stmt in statements.statements
                ]
            }

            # Step 2: Load company XBRL linkbases
            self.logger.info(f"{LOG_INPUT} Loading XBRL linkbases")
            calc_networks = self._load_calculation_linkbase(filing)
            self.logger.info(f"{LOG_OUTPUT} Loaded {len(calc_networks)} calculation networks")

            # Step 2b: Load formulas into registry (for XBRL-sourced verification)
            # This MUST happen BEFORE vertical checks so formulas are available
            if self.enable_xbrl_verification:
                self.logger.info(f"{LOG_PROCESS} Loading formulas into registry")
                self._load_formula_registry(filing, statements)
                result.formula_registry_summary = self.formula_registry.get_summary()
                self.logger.info(
                    f"{LOG_OUTPUT} Formula registry: "
                    f"{result.formula_registry_summary.get('company_trees', 0)} company trees, "
                    f"{result.formula_registry_summary.get('taxonomy_trees', 0)} taxonomy trees"
                )

                # === DIAGNOSTIC: Find WHY children are missing ===
                print("\n" + "="*60)
                print("DIAGNOSTIC: WHY ARE CHILDREN MISSING?")
                print("="*60)

                from .checks.constants import ConceptNormalizer
                test_normalizer = ConceptNormalizer()

                # Collect facts with detailed info about WHY they might be filtered
                all_facts_info = {}  # normalized -> {value, has_dims, stmt_name}
                normalized_facts = {}

                for stmt in statements.statements:
                    for fact in stmt.facts:
                        if fact.value is None or fact.is_abstract:
                            continue

                        norm = test_normalizer.normalize(fact.concept)
                        has_dims = bool(fact.dimensions and any(fact.dimensions.values()))

                        # Store info about this fact
                        if norm not in all_facts_info:
                            all_facts_info[norm] = []
                        all_facts_info[norm].append({
                            'value': fact.value,
                            'has_dims': has_dims,
                            'stmt': stmt.name,
                            'is_main': stmt.is_main_statement
                        })

                        # Only add to calc facts if no dimensions
                        if not has_dims:
                            raw_val = str(fact.value).strip() if fact.value else ''
                            if raw_val in ('', '—', '–', '-', 'nil', 'N/A', 'n/a'):
                                normalized_facts[norm] = 0.0
                            else:
                                try:
                                    normalized_facts[norm] = float(raw_val.replace(',', '').replace('$', ''))
                                except:
                                    pass

                print(f"\nTotal concepts with values: {len(all_facts_info)}")
                print(f"Concepts usable for calc (no dims): {len(normalized_facts)}")

                # Find LiabilitiesAndStockholdersEquity tree
                trees = self.formula_registry.get_all_calculations('company')
                target_tree = None
                for tree in trees:
                    if 'LiabilitiesAndStockholdersEquity' in tree.parent:
                        target_tree = tree
                        break

                if target_tree:
                    print(f"\n=== {target_tree.parent} ===")
                    parent_norm = test_normalizer.normalize(target_tree.parent)
                    parent_val = normalized_facts.get(parent_norm)
                    print(f"Parent value: {parent_val:,.0f}" if parent_val else "Parent: NOT FOUND")

                    print(f"\nChildren analysis:")
                    found_sum = 0.0
                    for child, weight in target_tree.children:
                        child_norm = test_normalizer.normalize(child)
                        child_val = normalized_facts.get(child_norm)

                        if child_val is not None:
                            found_sum += child_val * weight
                            print(f"  OK: {child_norm} = {child_val:,.0f}")
                        else:
                            # WHY is it missing?
                            if child_norm in all_facts_info:
                                info = all_facts_info[child_norm]
                                print(f"  FILTERED: {child_norm}")
                                for i in info[:2]:  # Show first 2 occurrences
                                    print(f"    -> value={i['value']}, dims={i['has_dims']}, stmt={i['stmt']}, main={i['is_main']}")
                            else:
                                print(f"  NOT IN STATEMENTS: {child_norm}")

                    print(f"\nSum of found: {found_sum:,.0f}")
                    print(f"Parent: {parent_val:,.0f}" if parent_val else "")
                    if parent_val:
                        print(f"GAP: {parent_val - found_sum:,.0f}")

                print("\n" + "="*60 + "\n")

            # Step 3: Run horizontal checks
            self.logger.info(f"{LOG_PROCESS} Running horizontal checks")
            result.horizontal_results = self.horizontal_checker.check_all(
                statements, calc_networks
            )

            # Step 4: Run vertical checks
            # VerticalChecker now automatically uses XBRL-sourced verification
            # when formula_registry has formulas loaded (preferred method)
            # Otherwise falls back to legacy pattern-based checks
            self.logger.info(f"{LOG_PROCESS} Running vertical checks")
            result.vertical_results = self.vertical_checker.check_all(statements)

            # Store XBRL and taxonomy results separately for detailed analysis
            # Now uses distinct check_names for proper scoring separation
            result.xbrl_calculation_results = [
                r for r in result.vertical_results
                if r.check_name in ('xbrl_calculation_company', 'xbrl_calculation_comparison')
            ]
            result.taxonomy_calculation_results = [
                r for r in result.vertical_results
                if r.check_name == 'xbrl_calculation_taxonomy'
            ]

            # Step 5: Ensure taxonomies are available (if library checks enabled)
            if self.enable_library_checks:
                self.logger.info(f"{LOG_PROCESS} Checking taxonomy availability")
                result.taxonomy_status = self.taxonomy_manager.ensure_taxonomies_available(
                    filing.market, filing.company, filing.form, filing.date
                )

                if result.taxonomy_status.get('ready', False):
                    self.logger.info(f"{LOG_OUTPUT} Taxonomies ready for library checks")
                else:
                    self.logger.info(
                        f"{LOG_OUTPUT} Taxonomies not ready: {result.taxonomy_status.get('message', '')}"
                    )

            # Step 6: Run library checks (optional)
            if self.enable_library_checks:
                self.logger.info(f"{LOG_PROCESS} Running library checks")
                taxonomy_id = self._detect_taxonomy(statements)
                result.library_results = self.library_checker.check_all(
                    statements, taxonomy_id
                )

            # Step 7: Calculate scores
            # Note: vertical_results already includes xbrl/taxonomy calculation results
            # so we don't add them again to avoid double-counting
            self.logger.info(f"{LOG_PROCESS} Calculating scores")
            all_results = (
                result.horizontal_results +
                result.vertical_results +
                result.library_results
            )
            result.scores = self.score_calculator.calculate_scores(all_results)

            # Step 8: Classify quality
            self.logger.info(f"{LOG_PROCESS} Classifying quality")
            result.quality = self.quality_classifier.classify(result.scores)
            result.recommendation = result.quality.recommendation

            # Build issues summary
            result.issues_summary = {
                'critical': result.scores.critical_issues,
                'warnings': result.scores.warning_issues,
                'info': result.scores.info_issues,
            }

            # Calculate processing time
            elapsed = (datetime.now() - start_time).total_seconds()
            result.processing_time_seconds = elapsed

            self.logger.info(
                f"{LOG_OUTPUT} Verification complete: {result.quality.level} "
                f"(score: {result.scores.overall_score:.1f}) in {elapsed:.2f}s"
            )

        except Exception as e:
            self.logger.error(f"Error verifying {filing_id}: {e}")
            result.recommendation = f"Verification failed: {str(e)}"

            if not self.continue_on_error:
                raise

        return result

    def verify_all_filings(self) -> list[VerificationResult]:
        """
        Verify all available mapped filings.

        Returns:
            List of VerificationResult for each filing
        """
        self.logger.info(f"{LOG_INPUT} Discovering mapped filings")

        filings = self.mapped_loader.discover_all_mapped_filings()
        self.logger.info(f"{LOG_OUTPUT} Found {len(filings)} mapped filings")

        results = []
        for filing in filings:
            try:
                result = self.verify_filing(filing)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Failed to verify {filing.company}: {e}")
                if not self.continue_on_error:
                    raise

        self.logger.info(f"{LOG_OUTPUT} Verified {len(results)} filings")

        return results

    def verify_by_id(
        self,
        market: str,
        company: str,
        form: str,
        date: str
    ) -> Optional[VerificationResult]:
        """
        Verify a specific filing by its identifiers.

        Args:
            market: Market identifier
            company: Company name
            form: Form type
            date: Filing date

        Returns:
            VerificationResult or None if not found
        """
        filing = self.mapped_loader.find_mapped_filing(market, company, form, date)

        if not filing:
            self.logger.warning(f"Filing not found: {market}/{company}/{form}/{date}")
            return None

        return self.verify_filing(filing)

    def _load_calculation_linkbase(
        self,
        filing: MappedFilingEntry
    ) -> list[CalculationNetwork]:
        """Load calculation linkbase for the filing."""
        try:
            xbrl_path = self.xbrl_loader.find_filing_for_company(
                filing.market,
                filing.company,
                filing.form,
                filing.date
            )

            if xbrl_path:
                return self.xbrl_reader.read_calculation_linkbase(xbrl_path)

        except Exception as e:
            self.logger.warning(f"Could not load calculation linkbase: {e}")

        return []

    def _load_formula_registry(
        self,
        filing: MappedFilingEntry,
        statements: MappedStatements
    ) -> None:
        """
        Load formulas into the formula registry from both sources.

        Loads:
        1. Company XBRL calculation linkbase
        2. Standard taxonomy calculation linkbase (if available)

        Args:
            filing: Filing entry
            statements: Loaded statements (for taxonomy detection)
        """
        # Clear previous data
        self.formula_registry.clear()

        # Load company formulas from XBRL
        try:
            xbrl_path = self.xbrl_loader.find_filing_for_company(
                filing.market,
                filing.company,
                filing.form,
                filing.date
            )

            self.logger.info(f"{LOG_INPUT} XBRL path for formula loading: {xbrl_path}")

            if xbrl_path:
                company_count = self.formula_registry.load_company_formulas(xbrl_path)
                self.logger.info(f"{LOG_OUTPUT} Loaded {company_count} company calculation trees")

                if company_count == 0:
                    self.logger.warning(
                        f"{LOG_OUTPUT} No company calculation trees loaded - "
                        f"will fall back to legacy pattern-based checks"
                    )
            else:
                self.logger.warning(
                    f"{LOG_OUTPUT} No XBRL path found for {filing.company} - "
                    f"will fall back to legacy pattern-based checks"
                )

        except Exception as e:
            self.logger.error(f"Could not load company formulas: {e}", exc_info=True)

        # Load taxonomy formulas
        try:
            taxonomy_id = self._detect_taxonomy(statements)
            if taxonomy_id:
                taxonomy_count = self.formula_registry.load_taxonomy_formulas(taxonomy_id)
                self.logger.info(f"{LOG_OUTPUT} Loaded {taxonomy_count} taxonomy calculation trees")
            else:
                self.logger.info(f"{LOG_OUTPUT} No taxonomy detected for taxonomy formula loading")

        except Exception as e:
            self.logger.warning(f"Could not load taxonomy formulas: {e}")

    def _detect_taxonomy(self, statements: MappedStatements) -> Optional[str]:
        """
        Detect which standard taxonomy is used.

        Looks at available taxonomy directories and matches against
        concept prefixes or namespace URIs in the statements.
        """
        # First, get list of actually available taxonomies
        available_taxonomies = []
        try:
            taxonomy_dirs = self.taxonomy_reader.taxonomy_loader.list_taxonomies()
            available_taxonomies = [t.name for t in taxonomy_dirs]
            self.logger.info(f"Available taxonomies: {available_taxonomies}")
        except Exception as e:
            self.logger.warning(f"Could not list available taxonomies: {e}")

        # Look at namespaces in the statements
        namespaces = statements.namespaces

        if not namespaces:
            # Try to detect from concept prefixes
            for statement in statements.statements:
                for fact in statement.facts:
                    concept = fact.concept.lower()
                    # Check against available taxonomies
                    for tax_id in available_taxonomies:
                        if tax_id.lower() in concept:
                            return tax_id
                    # Fallback checks
                    if 'us-gaap' in concept:
                        return 'us-gaap' if 'us-gaap' in available_taxonomies else None
                    elif 'ifrs' in concept:
                        return 'ifrs-full' if 'ifrs-full' in available_taxonomies else None

        # Check namespace values
        for ns_prefix, ns_uri in namespaces.items():
            ns_uri_lower = ns_uri.lower()
            # Check against available taxonomies
            for tax_id in available_taxonomies:
                if tax_id.lower() in ns_uri_lower:
                    return tax_id
            # Fallback checks
            if 'us-gaap' in ns_uri_lower:
                return 'us-gaap' if 'us-gaap' in available_taxonomies else None
            elif 'ifrs' in ns_uri_lower:
                return 'ifrs-full' if 'ifrs-full' in available_taxonomies else None

        return None

    def _identify_main_statements(
        self,
        market: str,
        statements: MappedStatements,
        filing: MappedFilingEntry
    ) -> Optional[MainStatements]:
        """
        Identify main financial statements using market-specific logic.

        SEC: Identifies consolidated statements by size (>40KB) and naming
        ESEF: Matches against 6 standard IFRS statement names

        Args:
            market: Market identifier ('sec', 'esef')
            statements: Loaded mapped statements
            filing: Filing entry with path info

        Returns:
            MainStatements container with identified main statements
        """
        try:
            # Get market-specific statement identifier
            identifier = get_statement_identifier(market)

            # Build statement dicts for identifier
            statement_dicts = [
                {
                    'statement_name': stmt.name,
                    'name': stmt.name,
                    'facts': stmt.facts,
                    'file_size': stmt.file_size_bytes,
                }
                for stmt in statements.statements
            ]

            # Get JSON directory for file size checks
            json_dir = filing.json_folder if filing.json_folder else None

            # Identify main statements
            main_statements = identifier.identify_main_statements(
                statement_dicts,
                json_dir
            )

            return main_statements

        except ValueError as e:
            self.logger.warning(f"Could not get statement identifier for {market}: {e}")
            return None
        except Exception as e:
            self.logger.warning(f"Error identifying main statements: {e}")
            return None

    def get_available_filings(self) -> list[MappedFilingEntry]:
        """
        Get list of available filings for verification.

        Returns:
            List of MappedFilingEntry objects
        """
        return self.mapped_loader.discover_all_mapped_filings()

    def get_statistics(self) -> dict:
        """
        Get verification statistics.

        Returns:
            Dictionary with statistics
        """
        filings = self.mapped_loader.discover_all_mapped_filings()

        return {
            'total_filings': len(filings),
            'by_market': self._count_by_field(filings, 'market'),
            'by_form': self._count_by_field(filings, 'form'),
            'companies': list(set(f.company for f in filings)),
        }

    def _count_by_field(
        self,
        filings: list[MappedFilingEntry],
        field: str
    ) -> dict[str, int]:
        """Count filings by a field."""
        counts = {}
        for filing in filings:
            value = getattr(filing, field, 'unknown')
            counts[value] = counts.get(value, 0) + 1
        return counts


__all__ = ['VerificationCoordinator', 'VerificationResult']
