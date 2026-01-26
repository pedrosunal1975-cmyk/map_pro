#!/usr/bin/env python
"""
Test script to verify taxonomy loaders can read downloaded libraries.
Run this from map_pro directory: python verification/test_taxonomy_loaders.py
"""
import sys
from pathlib import Path

# Add map_pro to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from verification.loaders.taxonomy import TaxonomyLoader
from verification.loaders.taxonomy_reader import TaxonomyReader
from verification.core.config_loader import ConfigLoader

def main():
    config = ConfigLoader()

    print("=" * 60)
    print("TAXONOMY LOADER TEST")
    print("=" * 60)

    # Test 1: TaxonomyLoader - Can it find taxonomy directories?
    print("\n=== TEST 1: TaxonomyLoader ===")
    try:
        loader = TaxonomyLoader(config)
        print(f"Taxonomy path: {loader.taxonomy_path}")
        print(f"Path exists: {loader.taxonomy_path.exists()}")

        if not loader.taxonomy_path.exists():
            print("\nERROR: Taxonomy directory does not exist!")
            print("Make sure library module has downloaded taxonomies first.")
            return

        taxonomies = loader.list_taxonomies()
        print(f"\nFound {len(taxonomies)} taxonomy directories:")

        for t in taxonomies:
            xsd_count = len(list(t.glob('*.xsd')))
            all_xsd = len(list(t.rglob('*.xsd')))
            print(f"  - {t.name}")
            print(f"      Root XSD files: {xsd_count}")
            print(f"      Total XSD files (recursive): {all_xsd}")

    except Exception as e:
        print(f"TaxonomyLoader Error: {e}")
        return

    # Test 2: TaxonomyReader - Can it read and parse taxonomies?
    print("\n=== TEST 2: TaxonomyReader ===")
    try:
        reader = TaxonomyReader(config)

        for taxonomy_dir in taxonomies[:3]:  # Test first 3
            taxonomy_id = taxonomy_dir.name
            print(f"\nReading: {taxonomy_id}")

            taxonomy = reader.read_taxonomy(taxonomy_id)

            if taxonomy:
                print(f"  SUCCESS!")
                print(f"  Namespace: {taxonomy.namespace[:60]}..." if len(taxonomy.namespace) > 60 else f"  Namespace: {taxonomy.namespace}")
                print(f"  Concepts loaded: {len(taxonomy.concepts)}")

                # Show sample concepts
                if taxonomy.concepts:
                    print(f"  Sample concepts:")
                    for i, (name, concept) in enumerate(taxonomy.concepts.items()):
                        if i >= 5:
                            break
                        print(f"    - {name}")
                        print(f"        period_type: {concept.period_type}")
                        print(f"        balance_type: {concept.balance_type}")
            else:
                print(f"  FAILED to load!")

    except Exception as e:
        print(f"TaxonomyReader Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == '__main__':
    main()
