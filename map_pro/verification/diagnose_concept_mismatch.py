#!/usr/bin/env python3
"""
Diagnostic script to compare concept names between:
1. XBRL calculation linkbase (from xbrl_reader)
2. Mapped statements (from mapped_reader)

This helps identify why calculation verification produces no results
even though 56 calculation trees were loaded.

Run from verification/ directory:
    python diagnose_concept_mismatch.py
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from verification.core.config_loader import ConfigLoader
from verification.loaders.xbrl_filings import XBRLFilingsLoader
from verification.loaders.xbrl_reader import XBRLReader
from verification.loaders.mapped_data import MappedDataLoader
from verification.loaders.mapped_reader import MappedReader
from verification.engine.formula_registry import FormulaRegistry


def main():
    print("="*70)
    print("CONCEPT NAME MISMATCH DIAGNOSTIC")
    print("="*70)

    config = ConfigLoader()

    # Find a mapped filing
    mapped_loader = MappedDataLoader(config)
    filings = mapped_loader.discover_all_mapped_filings()

    if not filings:
        print("No mapped filings found!")
        return 1

    filing = filings[0]
    print(f"\nUsing filing: {filing.market}/{filing.company}/{filing.form}/{filing.date}")

    # Load XBRL calculation linkbase
    print("\n" + "="*70)
    print("1. XBRL CALCULATION LINKBASE CONCEPTS")
    print("="*70)

    xbrl_loader = XBRLFilingsLoader(config)
    xbrl_reader = XBRLReader(config)

    xbrl_path = xbrl_loader.find_filing_for_company(
        filing.market, filing.company, filing.form, filing.date
    )

    if not xbrl_path:
        print(f"No XBRL path found for {filing.company}")
        return 1

    print(f"XBRL Path: {xbrl_path}")

    calc_networks = xbrl_reader.read_calculation_linkbase(xbrl_path)
    print(f"Calculation networks loaded: {len(calc_networks)}")

    # Collect all concepts from calculation linkbase
    xbrl_concepts = set()
    for network in calc_networks:
        for arc in network.arcs:
            xbrl_concepts.add(arc.parent_concept)
            xbrl_concepts.add(arc.child_concept)

    print(f"Total unique concepts in calc linkbase: {len(xbrl_concepts)}")
    print("\nSample XBRL concepts (first 20):")
    for i, concept in enumerate(sorted(xbrl_concepts)[:20], 1):
        print(f"  {i:2}. {concept}")

    # Load mapped statements
    print("\n" + "="*70)
    print("2. MAPPED STATEMENT CONCEPTS")
    print("="*70)

    mapped_reader = MappedReader()
    statements = mapped_reader.read_statements(filing)

    if not statements or not statements.statements:
        print("No statements found!")
        return 1

    print(f"Statements loaded: {len(statements.statements)}")

    # Collect all concepts from statements
    statement_concepts = set()
    for stmt in statements.statements:
        for fact in stmt.facts:
            if not fact.is_abstract and fact.concept:
                statement_concepts.add(fact.concept)

    print(f"Total unique concepts in statements: {len(statement_concepts)}")
    print("\nSample statement concepts (first 20):")
    for i, concept in enumerate(sorted(statement_concepts)[:20], 1):
        print(f"  {i:2}. {concept}")

    # Compare
    print("\n" + "="*70)
    print("3. COMPARISON")
    print("="*70)

    # Direct matches
    exact_matches = xbrl_concepts & statement_concepts
    print(f"\nExact matches: {len(exact_matches)}")
    if exact_matches:
        print("Sample exact matches:")
        for concept in sorted(exact_matches)[:10]:
            print(f"  - {concept}")

    # Check for namespace prefix differences
    print("\n" + "-"*50)
    print("Checking namespace prefix patterns...")

    # Extract local names (without namespace prefix)
    xbrl_local = {c.split(':')[-1] if ':' in c else c for c in xbrl_concepts}
    stmt_local = {c.split(':')[-1] if ':' in c else c for c in statement_concepts}

    local_matches = xbrl_local & stmt_local
    print(f"\nLocal name matches (ignoring namespace): {len(local_matches)}")

    if local_matches and not exact_matches:
        print("\nThis indicates a NAMESPACE PREFIX MISMATCH!")
        print("\nExample mismatches:")
        for local_name in sorted(local_matches)[:10]:
            xbrl_full = [c for c in xbrl_concepts if c.endswith(local_name) or c == local_name]
            stmt_full = [c for c in statement_concepts if c.endswith(local_name) or c == local_name]
            print(f"  Local: {local_name}")
            print(f"    XBRL: {xbrl_full[:2]}")
            print(f"    Stmt: {stmt_full[:2]}")

    # Check for underscore vs colon differences
    print("\n" + "-"*50)
    print("Checking underscore vs colon patterns...")

    xbrl_normalized = {c.replace(':', '_').lower() for c in xbrl_concepts}
    stmt_normalized = {c.replace(':', '_').lower() for c in statement_concepts}

    normalized_matches = xbrl_normalized & stmt_normalized
    print(f"Normalized matches (: -> _, lowercase): {len(normalized_matches)}")

    # Summary and recommendation
    print("\n" + "="*70)
    print("4. DIAGNOSIS & RECOMMENDATION")
    print("="*70)

    if exact_matches:
        print(f"\n{len(exact_matches)} concepts match exactly.")
        print("The issue may be in the verification logic, not concept names.")
    elif local_matches:
        print(f"\n{len(local_matches)} concepts match by local name (ignoring namespace).")
        print("\nRECOMMENDATION: Update calculation_verifier._extract_facts() to:")
        print("  1. Also index facts by local name (without namespace)")
        print("  2. Or normalize both XBRL and statement concepts")
    elif normalized_matches:
        print(f"\n{len(normalized_matches)} concepts match after normalizing (:/_).")
        print("\nRECOMMENDATION: Normalize concept names in both places.")
    else:
        print("\nNo obvious pattern found. Concepts may be fundamentally different.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
