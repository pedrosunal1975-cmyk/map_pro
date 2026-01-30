#!/usr/bin/env python3
"""
Diagnostic script for taxonomy calculation loading.

Checks:
1. What taxonomy ID is being detected
2. Whether taxonomy directory exists
3. What calculation linkbase files are found
4. Sample content of calculation files

Run from verification/ directory:
    python diagnose_taxonomy_calc.py
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from verification.core.config_loader import ConfigLoader
from verification.loaders.taxonomy import TaxonomyLoader
from verification.loaders.taxonomy_calc_reader import TaxonomyCalcReader
from verification.loaders.constants import CALCULATION_LINKBASE_PATTERNS


def main():
    print("="*70)
    print("TAXONOMY CALCULATION DIAGNOSTIC")
    print("="*70)

    config = ConfigLoader()
    taxonomy_path = config.get('taxonomy_path')
    print(f"\nTaxonomy base path: {taxonomy_path}")

    if not taxonomy_path or not Path(taxonomy_path).exists():
        print("ERROR: Taxonomy path does not exist!")
        return 1

    # List all subdirectories (taxonomies)
    print("\n" + "-"*50)
    print("Available taxonomy directories:")
    for d in sorted(Path(taxonomy_path).iterdir()):
        if d.is_dir():
            print(f"  - {d.name}")

    # Check us-gaap specifically
    us_gaap_path = Path(taxonomy_path) / "us-gaap"
    print(f"\n" + "-"*50)
    print(f"US-GAAP directory: {us_gaap_path}")
    print(f"Exists: {us_gaap_path.exists()}")

    if us_gaap_path.exists():
        print("\nUS-GAAP subdirectories:")
        for d in sorted(us_gaap_path.iterdir()):
            print(f"  - {d.name}")

    # Search for ALL files with 'cal' in the name
    print("\n" + "-"*50)
    print("Searching for files containing 'cal' in name:")
    cal_files = []
    for f in Path(taxonomy_path).rglob("*"):
        if f.is_file() and 'cal' in f.name.lower():
            cal_files.append(f)

    if cal_files:
        print(f"Found {len(cal_files)} files:")
        for f in cal_files[:20]:
            print(f"  - {f.relative_to(taxonomy_path)}")
        if len(cal_files) > 20:
            print(f"  ... and {len(cal_files) - 20} more")
    else:
        print("  NO FILES FOUND with 'cal' in name!")

    # Check our patterns
    print("\n" + "-"*50)
    print("Checking CALCULATION_LINKBASE_PATTERNS:")
    print(f"Patterns: {CALCULATION_LINKBASE_PATTERNS}")

    matched_files = []
    for f in Path(taxonomy_path).rglob("*"):
        if f.is_file():
            fname_lower = f.name.lower()
            for pattern in CALCULATION_LINKBASE_PATTERNS:
                if pattern.lower() in fname_lower:
                    matched_files.append(f)
                    break

    if matched_files:
        print(f"\nMatched {len(matched_files)} files:")
        for f in matched_files[:20]:
            print(f"  - {f.relative_to(taxonomy_path)}")
    else:
        print("\nNO FILES matched our patterns!")

    # Try the TaxonomyCalcReader
    print("\n" + "-"*50)
    print("Testing TaxonomyCalcReader:")

    reader = TaxonomyCalcReader(config)

    # Try different taxonomy IDs
    test_ids = ['us-gaap', 'us-gaap-2024', 'ifrs']
    for tax_id in test_ids:
        print(f"\n  Testing taxonomy_id = '{tax_id}':")
        try:
            result = reader.read_taxonomy_calculations(tax_id)
            if result:
                print(f"    SUCCESS: {len(result.relationships)} relationships found")
                print(f"    Parent concepts: {len(result.by_parent)}")
                if result.by_parent:
                    sample_parents = list(result.by_parent.keys())[:5]
                    print(f"    Sample parents: {sample_parents}")
            else:
                print(f"    FAILED: No calculations returned")
        except Exception as e:
            print(f"    ERROR: {e}")

    # Show file type distribution
    print("\n" + "-"*50)
    print("File type distribution in taxonomy:")
    extensions = {}
    for f in Path(taxonomy_path).rglob("*"):
        if f.is_file():
            ext = f.suffix.lower()
            extensions[ext] = extensions.get(ext, 0) + 1

    for ext, count in sorted(extensions.items(), key=lambda x: -x[1])[:10]:
        print(f"  {ext}: {count} files")

    return 0


if __name__ == "__main__":
    sys.exit(main())
