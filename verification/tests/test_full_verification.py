# Path: verification/tests/test_full_verification.py
"""
Full Integration Test for XBRL Verification

Tests the complete verification pipeline:
1. Parse company calculation linkbase (_cal.xml)
2. Load mapped statements from XLSX files
3. Run verification with proper XBRL components
4. Analyze and report results

This test uses REAL data from the ACI company filing.
"""

import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import re
import xml.etree.ElementTree as ET

# Add map_pro root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import openpyxl
except ImportError:
    print("[ERROR] openpyxl not installed. Run: pip install openpyxl")
    sys.exit(1)


# ============================================================================
# DATA CLASSES (matching verification module)
# ============================================================================

@dataclass
class StatementFact:
    """A single fact from a mapped statement."""
    concept: str
    value: any
    unit: Optional[str] = None
    decimals: Optional[int] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    context_id: Optional[str] = None
    dimensions: dict = field(default_factory=dict)
    label: Optional[str] = None
    order: Optional[float] = None
    depth: int = 0
    is_total: bool = False
    is_abstract: bool = False


@dataclass
class Statement:
    """A financial statement with its facts."""
    name: str
    role: Optional[str] = None
    facts: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    source_file: Optional[str] = None
    file_size_bytes: int = 0
    is_main_statement: bool = False


@dataclass
class MappedStatements:
    """Complete set of mapped statements."""
    statements: list = field(default_factory=list)
    filing_info: dict = field(default_factory=dict)
    namespaces: dict = field(default_factory=dict)
    periods: list = field(default_factory=list)
    market: str = 'sec'
    main_statements: list = field(default_factory=list)
    total_statement_files: int = 0


@dataclass
class CalculationArc:
    """A calculation arc from XBRL."""
    parent_concept: str
    child_concept: str
    weight: float
    order: int


@dataclass
class CalculationNetwork:
    """A calculation network for a statement role."""
    role: str
    arcs: list = field(default_factory=list)


# ============================================================================
# XBRL INSTANCE CONTEXT PARSER
# ============================================================================

@dataclass
class ContextInfo:
    """Context information including period and dimensions."""
    context_id: str
    period: str = ""
    period_type: str = ""  # 'instant' or 'duration'
    dimensions: dict = field(default_factory=dict)

    @property
    def is_default(self) -> bool:
        """True if no dimensional qualifiers."""
        return len(self.dimensions) == 0


def parse_instance_contexts_full(instance_file: Path) -> dict[str, ContextInfo]:
    """
    Parse XBRL instance document to extract full context definitions.

    Returns dict mapping context_id -> ContextInfo with period and dimensions.
    """
    contexts = {}

    if not instance_file.exists():
        print(f"    [WARN] Instance file not found: {instance_file}")
        return contexts

    try:
        with open(instance_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Pattern for context definitions
        context_pattern = re.compile(
            r'<[^>]*context[^>]*id="([^"]+)"[^>]*>(.*?)</[^>]*context>',
            re.DOTALL | re.IGNORECASE
        )

        # Patterns for period
        instant_pattern = re.compile(r'<[^>]*instant[^>]*>([^<]+)<', re.IGNORECASE)
        start_pattern = re.compile(r'<[^>]*startDate[^>]*>([^<]+)<', re.IGNORECASE)
        end_pattern = re.compile(r'<[^>]*endDate[^>]*>([^<]+)<', re.IGNORECASE)

        # Pattern for explicit dimension members
        dim_pattern = re.compile(
            r'<[^>]*explicitMember[^>]*dimension="([^"]+)"[^>]*>([^<]+)<',
            re.IGNORECASE
        )

        for match in context_pattern.finditer(content):
            ctx_id = match.group(1)
            ctx_content = match.group(2)

            ctx_info = ContextInfo(context_id=ctx_id)

            # Extract period
            instant = instant_pattern.search(ctx_content)
            if instant:
                ctx_info.period = instant.group(1)
                ctx_info.period_type = 'instant'
            else:
                start = start_pattern.search(ctx_content)
                end = end_pattern.search(ctx_content)
                if start and end:
                    ctx_info.period = f"{start.group(1)}_{end.group(1)}"
                    ctx_info.period_type = 'duration'

            # Extract dimensions
            for dim_match in dim_pattern.finditer(ctx_content):
                dimension = dim_match.group(1)
                member = dim_match.group(2)
                dim_local = dimension.split(':')[-1] if ':' in dimension else dimension
                member_local = member.split(':')[-1] if ':' in member else member
                ctx_info.dimensions[dim_local] = member_local

            contexts[ctx_id] = ctx_info

    except Exception as e:
        print(f"    [ERROR] Failed to parse instance contexts: {e}")

    return contexts


def parse_instance_contexts(instance_file: Path) -> dict[str, dict[str, str]]:
    """
    Parse XBRL instance document to extract context dimensions.

    Returns dict mapping context_id -> {dimension: member} dict.
    Empty dict means default context (no dimensional qualifiers).
    """
    full_contexts = parse_instance_contexts_full(instance_file)
    return {ctx_id: info.dimensions for ctx_id, info in full_contexts.items()}


def build_period_aware_fallback(
    all_facts: dict[str, list[tuple[str, float, Optional[str], Optional[int]]]],
    context_info: dict[str, ContextInfo]
) -> dict[str, dict[str, tuple[float, Optional[str], Optional[int]]]]:
    """
    Build a period-aware fallback index.

    Returns dict[concept][period] -> (value, unit, decimals)
    This allows looking up values by concept AND period.
    """
    result = {}

    for concept, instances in all_facts.items():
        if concept not in result:
            result[concept] = {}

        for ctx_id, value, unit, decimals in instances:
            if ctx_id in context_info:
                period = context_info[ctx_id].period
                # Store by period - if multiple values for same period, keep first
                if period and period not in result[concept]:
                    result[concept][period] = (value, unit, decimals, ctx_id)

    return result


# ============================================================================
# XLSX READER
# ============================================================================

def read_xlsx_statements(xlsx_dir: Path) -> list[Statement]:
    """Read all XLSX files and convert to Statement objects."""
    statements = []

    for xlsx_file in xlsx_dir.rglob('*.xlsx'):
        try:
            wb = openpyxl.load_workbook(xlsx_file, read_only=True, data_only=True)
            sheet = wb.active

            # Get header row
            rows = list(sheet.iter_rows(values_only=True))
            if not rows:
                continue

            header = rows[0]

            # Find column indices
            col_map = {str(h).lower(): i for i, h in enumerate(header) if h}

            concept_col = col_map.get('concept', 0)
            value_col = col_map.get('display value', col_map.get('value', 1))
            context_col = col_map.get('context ref', col_map.get('context_ref', 4))
            unit_col = col_map.get('unit ref', col_map.get('unit_ref', 5))
            decimals_col = col_map.get('decimals', 6)

            # Create facts
            facts = []
            for row in rows[1:]:
                if not row or not row[concept_col]:
                    continue

                concept = str(row[concept_col])

                # Skip abstract concepts
                if 'abstract' in concept.lower():
                    continue

                # Convert concept format from underscore to colon
                # us-gaap_Assets -> us-gaap:Assets
                if '_' in concept and ':' not in concept:
                    parts = concept.split('_', 1)
                    if len(parts) == 2:
                        concept = f"{parts[0]}:{parts[1]}"

                # Get value
                try:
                    raw_value = row[value_col] if value_col < len(row) else None
                    if raw_value is None or str(raw_value).strip() in ('', '-', '--', 'None'):
                        continue
                    value = float(str(raw_value).replace(',', ''))
                except (ValueError, TypeError):
                    continue

                # Get context_id
                context_id = str(row[context_col]) if context_col < len(row) and row[context_col] else None

                # Get unit
                unit = str(row[unit_col]).upper() if unit_col < len(row) and row[unit_col] else None

                # Get decimals
                decimals = None
                if decimals_col < len(row) and row[decimals_col]:
                    try:
                        decimals = int(float(str(row[decimals_col])))
                    except (ValueError, TypeError):
                        pass

                fact = StatementFact(
                    concept=concept,
                    value=value,
                    context_id=context_id,
                    unit=unit,
                    decimals=decimals,
                    is_abstract=False,
                )
                facts.append(fact)

            if facts:
                stmt_name = xlsx_file.stem
                is_main = xlsx_file.stat().st_size > 10000  # >10KB = main statement

                statement = Statement(
                    name=stmt_name,
                    facts=facts,
                    source_file=str(xlsx_file),
                    file_size_bytes=xlsx_file.stat().st_size,
                    is_main_statement=is_main,
                )
                statements.append(statement)

            wb.close()

        except Exception as e:
            print(f"[WARN] Error reading {xlsx_file}: {e}")

    return statements


# ============================================================================
# CALCULATION LINKBASE PARSER
# ============================================================================

def parse_calculation_linkbase(cal_file: Path) -> list[CalculationNetwork]:
    """Parse XBRL calculation linkbase to extract formulas."""
    networks = []

    tree = ET.parse(cal_file)
    root = tree.getroot()

    # Namespaces
    ns = {
        'link': 'http://www.xbrl.org/2003/linkbase',
        'xlink': 'http://www.w3.org/1999/xlink',
    }

    # Find all calculation links
    for calc_link in root.findall('.//link:calculationLink', ns):
        role = calc_link.get('{http://www.w3.org/1999/xlink}role', '')

        # Build locator map: label -> concept
        locators = {}
        for loc in calc_link.findall('link:loc', ns):
            label = loc.get('{http://www.w3.org/1999/xlink}label', '')
            href = loc.get('{http://www.w3.org/1999/xlink}href', '')

            # Extract concept from href
            # https://xbrl.fasb.org/us-gaap/2024/elts/us-gaap-2024.xsd#us-gaap_Assets
            if '#' in href:
                concept = href.split('#')[-1]
                # Convert to standard format: us-gaap_Assets -> us-gaap:Assets
                if '_' in concept and ':' not in concept:
                    parts = concept.split('_', 1)
                    if len(parts) == 2:
                        concept = f"{parts[0]}:{parts[1]}"
                locators[label] = concept

        # Extract calculation arcs
        arcs = []
        for arc in calc_link.findall('link:calculationArc', ns):
            from_label = arc.get('{http://www.w3.org/1999/xlink}from', '')
            to_label = arc.get('{http://www.w3.org/1999/xlink}to', '')
            weight = float(arc.get('weight', '1.0'))
            order = int(float(arc.get('order', '0')))

            parent = locators.get(from_label)
            child = locators.get(to_label)

            if parent and child:
                arcs.append(CalculationArc(
                    parent_concept=parent,
                    child_concept=child,
                    weight=weight,
                    order=order,
                ))

        if arcs:
            networks.append(CalculationNetwork(role=role, arcs=arcs))

    return networks


# ============================================================================
# MAIN TEST
# ============================================================================

def run_full_verification():
    """Run full verification test with real data."""
    print("=" * 70)
    print("FULL XBRL VERIFICATION TEST")
    print("Using ACI Company Filing Data")
    print("=" * 70)

    # Paths
    map_pro_root = Path(__file__).parent.parent.parent
    xlsx_dir = map_pro_root / 'mapped_statements'
    cal_file = map_pro_root / 'acI_company_xbrl_filings' / 'aci-20250222_cal.xml'

    # Check files exist
    if not xlsx_dir.exists():
        print(f"[ERROR] XLSX directory not found: {xlsx_dir}")
        return False

    if not cal_file.exists():
        print(f"[ERROR] Calculation linkbase not found: {cal_file}")
        return False

    # Step 1: Load mapped statements from XLSX
    print("\n--- Step 1: Loading Mapped Statements ---")
    statements = read_xlsx_statements(xlsx_dir)
    print(f"[OK] Loaded {len(statements)} statements")

    total_facts = sum(len(s.facts) for s in statements)
    print(f"[OK] Total facts: {total_facts}")

    main_stmts = [s for s in statements if s.is_main_statement]
    print(f"[OK] Main statements: {len(main_stmts)}")

    # Step 2: Parse calculation linkbase
    print("\n--- Step 2: Parsing Calculation Linkbase ---")
    calc_networks = parse_calculation_linkbase(cal_file)
    print(f"[OK] Found {len(calc_networks)} calculation networks")

    total_arcs = sum(len(n.arcs) for n in calc_networks)
    print(f"[OK] Total calculation arcs: {total_arcs}")

    # Show calculation summary
    for network in calc_networks:
        role_name = network.role.split('/')[-1] if '/' in network.role else network.role
        # Group arcs by parent
        parents = {}
        for arc in network.arcs:
            if arc.parent_concept not in parents:
                parents[arc.parent_concept] = []
            parents[arc.parent_concept].append(arc)
        print(f"    {role_name}: {len(parents)} calculations, {len(network.arcs)} arcs")

    # Step 3: Create MappedStatements object
    print("\n--- Step 3: Creating MappedStatements ---")
    mapped = MappedStatements(
        statements=statements,
        filing_info={'company': 'Albertsons Companies Inc', 'form': '10-K'},
        market='sec',
        main_statements=[s.name for s in main_stmts],
        total_statement_files=len(statements),
    )
    print(f"[OK] MappedStatements created")

    # Step 4: Import and run verification components
    print("\n--- Step 4: Running Verification Components ---")

    try:
        from verification.engine.checks.c_equal import CEqual
        from verification.engine.checks.binding_checker import BindingChecker, BindingStatus
        from verification.engine.checks.decimal_tolerance import DecimalTolerance
        from verification.engine.checks.horizontal_checker import HorizontalChecker
        from verification.engine.checks.dimension_handler import DimensionHandler
        from verification.engine.checks.sign_weight_handler import SignWeightHandler
    except ImportError as e:
        print(f"[ERROR] Could not import verification components: {e}")
        return False

    # Initialize components
    c_equal = CEqual()
    binding_checker = BindingChecker()
    decimal_tolerance = DecimalTolerance()
    dimension_handler = DimensionHandler()
    sign_handler = SignWeightHandler()

    # Parse dimension structures from definition linkbase
    print("\n    Parsing dimensional structure...")
    def_file = Path('acI_company_xbrl_filings/aci-20250222_def.xml')
    if def_file.exists():
        dimension_handler.parse_definition_linkbase(def_file)
        dim_summary = dimension_handler.get_summary()
        print(f"    [OK] {dim_summary['roles_with_dimensions']} roles with dimensional structures")
    else:
        print(f"    [WARN] Definition linkbase not found, dimensional analysis limited")

    # Parse context definitions from instance document (full info with periods)
    instance_file = Path('acI_company_xbrl_filings/aci-20250222.htm')
    context_info_full = parse_instance_contexts_full(instance_file)
    print(f"    [OK] Parsed {len(context_info_full)} context definitions")

    # Parse sign attributes from instance document
    print("\n    Parsing sign attributes...")
    sign_corrections = sign_handler.parse_instance_document(instance_file)
    sign_summary = sign_handler.get_summary()
    print(f"    [OK] Found {sign_summary['negative_corrections']} facts with sign='-' attribute")

    # Classify contexts
    default_contexts = set()
    dimensional_contexts = set()
    for ctx_id, info in context_info_full.items():
        if info.is_default:
            default_contexts.add(ctx_id)
        else:
            dimensional_contexts.add(ctx_id)
    print(f"    [OK] {len(default_contexts)} default contexts, {len(dimensional_contexts)} dimensional contexts")

    # Dimensional fallback - now enabled with proper context filtering
    use_dimensional_fallback = True

    # Group facts by context
    print("\n    Grouping facts by context (C-Equal)...")
    fact_groups = c_equal.group_facts(mapped)
    print(f"    [OK] {fact_groups.total_facts} facts in {fact_groups.context_count} contexts")

    # Check for inconsistent duplicates
    inconsistent = fact_groups.find_inconsistent_duplicates()
    if inconsistent:
        print(f"    [WARN] Found {len(inconsistent)} concepts with inconsistent duplicates")
    else:
        print(f"    [OK] No inconsistent duplicates found")

    # Build cross-context lookup index for dimensional fallback
    all_facts_by_concept = fact_groups.get_all_facts_by_concept()
    print(f"    [OK] Built dimensional fallback index: {len(all_facts_by_concept)} concepts")

    # Build period-aware fallback for smart dimensional lookups
    period_aware_fallback = build_period_aware_fallback(all_facts_by_concept, context_info_full)
    print(f"    [OK] Built period-aware fallback: {len(period_aware_fallback)} concepts with period mapping")

    # Step 5: Verify calculations
    print("\n--- Step 5: Verifying Calculations ---")

    total_checked = 0
    total_passed = 0
    total_skipped = 0
    total_failed = 0

    failed_details = []

    for network in calc_networks:
        role_name = network.role.split('/')[-1] if '/' in network.role else network.role

        # Group arcs by parent
        parent_children = {}
        for arc in network.arcs:
            if arc.parent_concept not in parent_children:
                parent_children[arc.parent_concept] = []
            parent_children[arc.parent_concept].append((arc.child_concept, arc.weight))

        network_passed = 0
        network_skipped = 0
        network_failed = 0

        for parent_concept, children in parent_children.items():
            parent_norm = c_equal.normalize_concept(parent_concept)
            children_norm = [
                (c_equal.normalize_concept(child), weight)
                for child, weight in children
            ]

            # Find contexts where parent exists
            contexts_with_parent = fact_groups.get_contexts_with_concept(parent_norm)

            if not contexts_with_parent:
                continue

            for context_id in contexts_with_parent:
                context_group = fact_groups.get_context(context_id)
                if not context_group:
                    continue

                # KEY: Only verify in DEFAULT contexts (no dimensional qualifiers)
                # Dimensional contexts represent component breakdowns, not totals
                is_default = context_id in default_contexts

                if not is_default:
                    # Skip dimensional context - it's a component breakdown
                    continue

                total_checked += 1

                # Check if calculation binds
                # For DEFAULT contexts, use period-aware dimensional fallback
                if use_dimensional_fallback and is_default:
                    # Get parent's period
                    parent_period = None
                    if context_id in context_info_full:
                        parent_period = context_info_full[context_id].period

                    # Build period-specific fallback for this context
                    period_specific_facts = {}
                    if parent_period:
                        for concept, period_values in period_aware_fallback.items():
                            if parent_period in period_values:
                                value, unit, decimals, src_ctx = period_values[parent_period]
                                period_specific_facts[concept] = [(src_ctx, value, unit, decimals)]

                    binding = binding_checker.check_binding_with_fallback(
                        context_group, parent_norm, children_norm, period_specific_facts
                    )
                else:
                    binding = binding_checker.check_binding(
                        context_group, parent_norm, children_norm
                    )

                if not binding.binds:
                    total_skipped += 1
                    network_skipped += 1
                    continue

                # Calculate expected sum with sign corrections on children
                expected_sum = 0.0
                min_decimals = None

                for child_info in binding.children_found:
                    child_value = child_info['value']
                    child_weight = child_info['weight']

                    # Apply sign correction to child value if it has a sign attribute
                    # Get the child's original concept (with namespace)
                    child_concept = child_info.get('original_concept', child_info['concept'])
                    child_ctx = child_info.get('context', context_id)

                    # Try to find sign correction for this child
                    # Need to match the concept format used in sign_corrections
                    child_corrected, _ = sign_handler.apply_sign_correction(
                        child_concept, child_ctx, child_value
                    )

                    weighted_value = child_corrected * child_weight
                    expected_sum += weighted_value

                    if child_info['decimals'] is not None:
                        if min_decimals is None:
                            min_decimals = child_info['decimals']
                        else:
                            min_decimals = min(min_decimals, child_info['decimals'])

                # Apply sign correction to parent value if needed
                # XBRL iXBRL uses sign="-" attribute for negative values displayed as positive
                parent_value_corrected, was_corrected = sign_handler.apply_sign_correction(
                    parent_concept, context_id, binding.parent_value
                )

                # Compare using decimal tolerance
                tolerance_result = decimal_tolerance.is_within_tolerance(
                    expected=expected_sum,
                    actual=parent_value_corrected,
                    expected_decimals=min_decimals,
                    actual_decimals=binding.parent_decimals,
                )

                if tolerance_result.values_equal:
                    total_passed += 1
                    network_passed += 1
                else:
                    total_failed += 1
                    network_failed += 1

                    if len(failed_details) < 10:  # Limit to first 10 failures
                        failed_details.append({
                            'role': role_name,
                            'parent': parent_concept,
                            'context': context_id,
                            'expected': expected_sum,
                            'actual': parent_value_corrected,
                            'original_value': binding.parent_value if was_corrected else None,
                            'sign_corrected': was_corrected,
                            'difference': tolerance_result.difference,
                            'children_found': len(binding.children_found),
                            'children_missing': len(binding.children_missing),
                        })

        print(f"    {role_name}: {network_passed} passed, {network_failed} failed, {network_skipped} skipped")

    # Step 6: Report results
    print("\n" + "=" * 70)
    print("VERIFICATION RESULTS")
    print("=" * 70)

    print(f"\nTotal calculations checked: {total_checked}")
    print(f"  Passed:  {total_passed} ({100*total_passed/max(total_checked,1):.1f}%)")
    print(f"  Failed:  {total_failed} ({100*total_failed/max(total_checked,1):.1f}%)")
    print(f"  Skipped: {total_skipped} ({100*total_skipped/max(total_checked,1):.1f}%)")

    # Calculate pass rate (excluding skipped)
    verified = total_passed + total_failed
    if verified > 0:
        pass_rate = 100 * total_passed / verified
        print(f"\nPass rate (verified only): {pass_rate:.1f}%")

    if failed_details:
        print(f"\n--- First {len(failed_details)} Failures ---")
        for detail in failed_details:
            print(f"\n  {detail['role']} / {detail['parent']} (context: {detail['context']})")
            print(f"    Expected: {detail['expected']:,.0f}")
            print(f"    Actual:   {detail['actual']:,.0f}")
            if detail.get('sign_corrected'):
                print(f"    (sign-corrected from {detail['original_value']:,.0f})")
            print(f"    Diff:     {detail['difference']:,.0f}")
            print(f"    Children: {detail['children_found']} found, {detail['children_missing']} missing")

    print("\n" + "=" * 70)

    # Return success if pass rate > 80%
    if verified > 0:
        success = pass_rate >= 80
        print(f"TEST {'PASSED' if success else 'FAILED'}: Pass rate is {pass_rate:.1f}%")
        return success
    else:
        print("TEST INCONCLUSIVE: No calculations were verified")
        return False


if __name__ == '__main__':
    success = run_full_verification()
    sys.exit(0 if success else 1)
