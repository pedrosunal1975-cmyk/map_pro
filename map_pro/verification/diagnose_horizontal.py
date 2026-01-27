# Path: verification/diagnose_horizontal.py
"""
Diagnostic script to debug horizontal calculation check issues.

Run this to see why calculation_consistency returns no results.
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from verification.loaders.mapped_data import MappedDataLoader
from verification.loaders.mapped_reader import MappedReader
from verification.loaders.xbrl_reader import XBRLReader
from verification.loaders.xbrl_filings import XBRLFilingsLoader
from verification.engine.checks.c_equal import CEqual


def diagnose():
    """Run horizontal check diagnostics."""
    print("=" * 60)
    print("HORIZONTAL CHECK DIAGNOSTIC")
    print("=" * 60)

    # Initialize loaders
    mapped_loader = MappedDataLoader()
    mapped_reader = MappedReader()
    xbrl_reader = XBRLReader()
    xbrl_loader = XBRLFilingsLoader()
    c_equal = CEqual()

    # Find a filing
    filings = mapped_loader.discover_all_mapped_filings()
    if not filings:
        print("ERROR: No mapped filings found")
        return

    filing = filings[0]
    print(f"\nFiling: {filing.market}/{filing.company}/{filing.form}/{filing.date}")

    # Step 1: Load statements
    print("\n--- STEP 1: Load Statements ---")
    statements = mapped_reader.read_statements(filing)
    if not statements:
        print("ERROR: Could not load statements")
        return

    total_facts = sum(len(s.facts) for s in statements.statements)
    main_facts = sum(len(s.facts) for s in statements.statements if s.is_main_statement)
    print(f"Total statements: {len(statements.statements)}")
    print(f"Main statements: {len([s for s in statements.statements if s.is_main_statement])}")
    print(f"Total facts: {total_facts}")
    print(f"Main statement facts: {main_facts}")

    # Step 2: Load calc_networks
    print("\n--- STEP 2: Load Calculation Networks ---")
    xbrl_path = xbrl_loader.find_filing_for_company(
        filing.market, filing.company, filing.form, filing.date
    )
    print(f"XBRL path found: {xbrl_path}")

    if not xbrl_path:
        print("ERROR: No XBRL path found - calculation check will be skipped!")
        return

    calc_networks = xbrl_reader.read_calculation_linkbase(xbrl_path)
    print(f"Calculation networks loaded: {len(calc_networks)}")

    if not calc_networks:
        print("ERROR: No calculation networks loaded - calculation check will be skipped!")
        return

    total_arcs = sum(len(n.arcs) for n in calc_networks)
    print(f"Total calculation arcs: {total_arcs}")

    # Show first few parent concepts from calc_networks
    parent_concepts = set()
    for network in calc_networks:
        for arc in network.arcs:
            parent_concepts.add(arc.parent_concept)

    print(f"\nUnique parent concepts in calc_networks: {len(parent_concepts)}")
    print("First 10 parent concepts:")
    for i, pc in enumerate(sorted(parent_concepts)[:10]):
        normalized = c_equal.normalize_concept(pc)
        print(f"  {i+1}. {pc} -> normalized: {normalized}")

    # Step 3: Group facts
    print("\n--- STEP 3: Group Facts ---")
    fact_groups = c_equal.group_facts(statements, main_only=True, group_by='period')
    print(f"Fact groups (periods): {fact_groups.context_count}")
    print(f"Total facts in groups: {fact_groups.total_facts}")

    # Show concepts in fact_groups
    all_concepts = set()
    for group in fact_groups.iter_groups():
        all_concepts.update(group.facts.keys())

    print(f"Unique concepts in fact_groups: {len(all_concepts)}")

    # Step 4: Check parent concept matching
    print("\n--- STEP 4: Parent Concept Matching ---")
    matched = 0
    not_matched = []

    for pc in parent_concepts:
        pc_norm = c_equal.normalize_concept(pc)
        contexts = fact_groups.get_contexts_with_concept(pc_norm)
        if contexts:
            matched += 1
        else:
            not_matched.append((pc, pc_norm))

    print(f"Parent concepts found in facts: {matched}/{len(parent_concepts)}")

    if not_matched:
        print(f"\nParent concepts NOT found ({len(not_matched)}):")
        for pc, pc_norm in not_matched[:10]:
            print(f"  - {pc} (normalized: {pc_norm})")
        if len(not_matched) > 10:
            print(f"  ... and {len(not_matched) - 10} more")

    # Check if any normalized parent matches any fact concept
    print("\n--- STEP 5: Concept Name Comparison ---")
    parent_norms = {c_equal.normalize_concept(pc) for pc in parent_concepts}
    fact_norms = all_concepts  # Already normalized

    overlap = parent_norms & fact_norms
    print(f"Calc network parent concepts (normalized): {len(parent_norms)}")
    print(f"Fact concepts (normalized): {len(fact_norms)}")
    print(f"Overlap (matching concepts): {len(overlap)}")

    if not overlap:
        print("\nWARNING: NO OVERLAP between calc parents and facts!")
        print("\nSample calc parent concepts:")
        for p in list(parent_norms)[:5]:
            print(f"  - {p}")
        print("\nSample fact concepts:")
        for f in list(fact_norms)[:5]:
            print(f"  - {f}")
    else:
        print("\nMatching concepts found:")
        for c in list(overlap)[:10]:
            print(f"  - {c}")


if __name__ == '__main__':
    diagnose()
