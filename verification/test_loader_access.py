# Path: verification/test_loader_access.py
"""
Diagnostic script to verify loader access to all statement files.

Run from map_pro/ folder:
    python -m verification.test_loader_access
"""

import sys
from pathlib import Path

# Add map_pro root to path for imports
map_pro_root = Path(__file__).parent.parent
sys.path.insert(0, str(map_pro_root))

from verification.loaders.mapped_data import MappedDataLoader
from verification.loaders.mapped_reader import MappedReader


def main():
    print("=" * 70)
    print("LOADER ACCESS DIAGNOSTIC")
    print("=" * 70)

    # Initialize loaders
    try:
        data_loader = MappedDataLoader()
        reader = MappedReader()
    except Exception as e:
        print(f"[FAIL] Could not initialize loaders: {e}")
        return

    print(f"\n[OK] Mapper output dir: {data_loader.mapper_output_dir}")

    # Discover all filings
    filings = data_loader.discover_all_mapped_filings()
    print(f"[OK] Discovered {len(filings)} mapped filings")

    if not filings:
        print("[WARN] No filings found!")
        return

    # Test each filing
    for i, filing in enumerate(filings):
        print(f"\n{'=' * 70}")
        print(f"FILING {i+1}: {filing.company} / {filing.form} / {filing.date}")
        print("=" * 70)

        print(f"\n  filing_folder: {filing.filing_folder}")
        print(f"  json_folder:   {filing.json_folder}")
        print(f"  available_files['json']: {len(filing.available_files.get('json', []))} files")

        # Check what folders exist
        print("\n  FOLDER STRUCTURE CHECK:")
        folders_to_check = ['core_statements', 'details', 'other']

        # Check under json_folder
        if filing.json_folder and filing.json_folder.exists():
            print(f"    json_folder exists: {filing.json_folder}")
            for folder in folders_to_check:
                path = filing.json_folder / folder
                if path.exists():
                    count = len(list(path.glob('*.json')))
                    print(f"      [OK] json/{folder}/: {count} json files")
                else:
                    print(f"      [--] json/{folder}/: NOT FOUND")
        else:
            print(f"    json_folder: None or doesn't exist")

        # Check directly under filing_folder
        print(f"\n    filing_folder: {filing.filing_folder}")
        for folder in folders_to_check:
            path = filing.filing_folder / folder
            if path.exists():
                count = len(list(path.glob('*.json')))
                print(f"      [OK] {folder}/: {count} json files")
            else:
                print(f"      [--] {folder}/: NOT FOUND")

        # Check json/ subfolder explicitly
        for subdir in ['json', 'JSON']:
            json_root = filing.filing_folder / subdir
            if json_root.exists():
                print(f"\n    {subdir}/ subfolder exists:")
                for folder in folders_to_check:
                    path = json_root / folder
                    if path.exists():
                        count = len(list(path.glob('*.json')))
                        print(f"      [OK] {subdir}/{folder}/: {count} json files")
                    else:
                        print(f"      [--] {subdir}/{folder}/: NOT FOUND")

        # Now test the actual reader
        print("\n  MAPPED READER TEST:")
        statements = reader.read_statements(filing)

        if statements:
            print(f"    [OK] Loaded {len(statements.statements)} statements")
            print(f"    [OK] Main statements: {len(statements.main_statements)}")

            # Count facts
            total_facts = sum(len(s.facts) for s in statements.statements)
            print(f"    [OK] Total facts: {total_facts}")

            # Show statement breakdown by source
            by_folder = {}
            for stmt in statements.statements:
                if stmt.source_file:
                    parent = Path(stmt.source_file).parent.name
                    by_folder[parent] = by_folder.get(parent, 0) + 1

            print("\n    Statements by folder:")
            for folder, count in sorted(by_folder.items()):
                print(f"      {folder}: {count} statements")
        else:
            print("    [FAIL] read_statements returned None!")

    print("\n" + "=" * 70)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 70)


if __name__ == '__main__':
    main()
