# Path: verification/tests/test_xbrl_components.py
"""
Unit tests for XBRL verification components.

Tests:
- CEqual: Context-based fact grouping
- BindingChecker: Calculation binding rules
- DecimalTolerance: XBRL rounding rules
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dataclasses import dataclass
from typing import Optional


# Mock StatementFact for testing
@dataclass
class MockFact:
    """Mock fact for testing."""
    concept: str
    value: float
    context_id: str
    unit: Optional[str] = "USD"
    decimals: Optional[int] = -6
    is_abstract: bool = False
    period_end: Optional[str] = None
    dimensions: Optional[dict] = None


# Mock Statement for testing
@dataclass
class MockStatement:
    """Mock statement for testing."""
    name: str
    facts: list
    is_main_statement: bool = True


# Mock MappedStatements for testing
@dataclass
class MockMappedStatements:
    """Mock mapped statements for testing."""
    statements: list


def test_c_equal_group_facts():
    """Test CEqual.group_facts() groups by context_id correctly."""
    from verification.engine.checks.c_equal import CEqual

    c_equal = CEqual()

    # Create test facts with different contexts
    facts = [
        MockFact("us-gaap:Assets", 1000000, "c-1"),
        MockFact("us-gaap:Liabilities", 600000, "c-1"),
        MockFact("us-gaap:Equity", 400000, "c-1"),
        MockFact("us-gaap:Assets", 1100000, "c-2"),  # Different context
        MockFact("us-gaap:Revenue", 500000, "c-3"),
    ]

    statements = MockMappedStatements(
        statements=[MockStatement("Balance Sheet", facts)]
    )

    groups = c_equal.group_facts(statements)

    # Should have 3 contexts
    assert groups.context_count == 3, f"Expected 3 contexts, got {groups.context_count}"

    # Check c-1 has 3 facts
    c1 = groups.get_context("c-1")
    assert c1 is not None, "Context c-1 should exist"
    assert len(c1.facts) == 3, f"Expected 3 facts in c-1, got {len(c1.facts)}"

    # Check values are accessible
    assert c1.get_value("assets") == 1000000
    assert c1.get_value("liabilities") == 600000
    assert c1.get_value("equity") == 400000

    print("[OK] CEqual.group_facts() works correctly")
    return True


def test_binding_checker():
    """Test BindingChecker determines binding correctly."""
    from verification.engine.checks.c_equal import CEqual, ContextGroup, FactEntry
    from verification.engine.checks.binding_checker import BindingChecker, BindingStatus

    c_equal = CEqual()
    checker = BindingChecker()

    # Create a context with parent and children
    context = ContextGroup(context_id="c-1")
    context.add_fact(FactEntry(
        concept="assets", original_concept="us-gaap:Assets",
        value=1000000, unit="USD", decimals=-6, context_id="c-1"
    ))
    context.add_fact(FactEntry(
        concept="liabilities", original_concept="us-gaap:Liabilities",
        value=600000, unit="USD", decimals=-6, context_id="c-1"
    ))
    context.add_fact(FactEntry(
        concept="equity", original_concept="us-gaap:Equity",
        value=400000, unit="USD", decimals=-6, context_id="c-1"
    ))

    # Test binding with all children present
    children = [("liabilities", 1.0), ("equity", 1.0)]
    result = checker.check_binding(context, "assets", children)

    assert result.binds, f"Calculation should bind: {result.message}"
    assert result.status == BindingStatus.BINDS
    assert len(result.children_found) == 2

    print("[OK] BindingChecker.check_binding() binds when all children present")

    # Test binding with missing child
    children_missing = [("liabilities", 1.0), ("cash", 1.0)]  # cash doesn't exist
    result2 = checker.check_binding(context, "assets", children_missing)

    # Should still bind - at least one child exists
    assert result2.binds, "Should bind with at least one child"
    assert "cash" in result2.children_missing

    print("[OK] BindingChecker.check_binding() binds with partial children")

    # Test no binding when no children found
    children_none = [("cash", 1.0), ("inventory", 1.0)]
    result3 = checker.check_binding(context, "assets", children_none)

    assert not result3.binds, "Should not bind when no children found"
    assert result3.status == BindingStatus.SKIP_NO_CHILDREN

    print("[OK] BindingChecker.check_binding() skips when no children found")

    return True


def test_decimal_tolerance():
    """Test DecimalTolerance comparison with XBRL rounding rules."""
    from verification.engine.checks.decimal_tolerance import DecimalTolerance

    tolerance = DecimalTolerance()

    # Test rounding to millions (decimals=-6)
    rounded = tolerance.round_to_decimals(532300000, -6)
    assert rounded == 532000000, f"Expected 532M, got {rounded}"

    print("[OK] DecimalTolerance.round_to_decimals() rounds to millions correctly")

    # Test comparison at lowest precision
    # 532M (decimals=-6) should equal 532.3M (decimals=-5) when compared at -6
    result = tolerance.compare(532000000, 532300000, -6, -5)
    assert result.values_equal, f"Values should be equal at decimals=-6: {result.message}"

    print("[OK] DecimalTolerance.compare() compares at lowest precision")

    # Test is_within_tolerance
    result2 = tolerance.is_within_tolerance(
        expected=1000000,
        actual=1000000,
        expected_decimals=-6,
        actual_decimals=-6
    )
    assert result2.values_equal, "Exact values should be within tolerance"

    print("[OK] DecimalTolerance.is_within_tolerance() works correctly")

    return True


def test_duplicate_handling():
    """Test duplicate fact handling per XBRL Duplicates Guidance."""
    from verification.engine.checks.c_equal import DuplicateInfo, FactEntry, DuplicateType

    # Test complete duplicates (same value, same precision)
    dup_info = DuplicateInfo(concept="assets")
    dup_info.add_entry(FactEntry(
        concept="assets", original_concept="us-gaap:Assets",
        value=1000000, unit="USD", decimals=-6, context_id="c-1"
    ))
    dup_info.add_entry(FactEntry(
        concept="assets", original_concept="us-gaap:Assets",
        value=1000000, unit="USD", decimals=-6, context_id="c-1"
    ))

    assert dup_info.duplicate_type == DuplicateType.COMPLETE
    assert dup_info.selected_value == 1000000

    print("[OK] Complete duplicates handled correctly")

    # Test consistent duplicates (same value, different precision)
    dup_info2 = DuplicateInfo(concept="assets")
    dup_info2.add_entry(FactEntry(
        concept="assets", original_concept="us-gaap:Assets",
        value=1000000, unit="USD", decimals=-6, context_id="c-1"
    ))
    dup_info2.add_entry(FactEntry(
        concept="assets", original_concept="us-gaap:Assets",
        value=1000000, unit="USD", decimals=-3, context_id="c-1"
    ))

    assert dup_info2.duplicate_type == DuplicateType.CONSISTENT
    assert dup_info2.selected_value == 1000000
    assert dup_info2.selected_decimals == -3  # Most precise

    print("[OK] Consistent duplicates use most precise value")

    # Test inconsistent duplicates (different values)
    dup_info3 = DuplicateInfo(concept="assets")
    dup_info3.add_entry(FactEntry(
        concept="assets", original_concept="us-gaap:Assets",
        value=1000000, unit="USD", decimals=-6, context_id="c-1"
    ))
    dup_info3.add_entry(FactEntry(
        concept="assets", original_concept="us-gaap:Assets",
        value=1100000, unit="USD", decimals=-6, context_id="c-1"
    ))

    assert dup_info3.duplicate_type == DuplicateType.INCONSISTENT
    assert dup_info3.selected_value is None  # Cannot select

    print("[OK] Inconsistent duplicates detected correctly")

    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("XBRL Verification Components - Unit Tests")
    print("=" * 60)
    print()

    tests = [
        ("CEqual group_facts", test_c_equal_group_facts),
        ("BindingChecker", test_binding_checker),
        ("DecimalTolerance", test_decimal_tolerance),
        ("Duplicate Handling", test_duplicate_handling),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\n--- Testing {name} ---")
        try:
            if test_func():
                passed += 1
                print(f"[PASS] {name}")
            else:
                failed += 1
                print(f"[FAIL] {name}")
        except Exception as e:
            failed += 1
            print(f"[FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
