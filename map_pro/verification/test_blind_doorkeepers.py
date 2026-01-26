#!/usr/bin/env python3
"""
Test script for Blind Doorkeeper Loaders

Tests that all 4 blind doorkeeper loaders can access their destination
folders and discover files recursively.

Run from verification/ directory:
    python test_blind_doorkeepers.py
"""

import random
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from verification.core.config_loader import ConfigLoader
from verification.loaders.xbrl_filings import XBRLFilingsLoader
from verification.loaders.mapped_data import MappedDataLoader
from verification.loaders.taxonomy import TaxonomyLoader
from verification.loaders.parsed_data import ParsedDataLoader


def print_header(name: str):
    """Print section header."""
    print(f"\n{'='*60}")
    print(f"DOORKEEPER: {name}")
    print(f"{'='*60}")


def test_xbrl_loader(config: ConfigLoader) -> list[Path]:
    """Test XBRL Filings Loader."""
    print_header("XBRL Filings Loader (xbrl_filings.py)")

    try:
        loader = XBRLFilingsLoader(config)
        print(f"Base Path: {loader.xbrl_path}")

        if not loader.xbrl_path or not Path(loader.xbrl_path).exists():
            print("WARNING: Path does not exist!")
            return []

        all_files = loader.discover_all_files()
        print(f"Total files discovered: {len(all_files)}")

        if not all_files:
            print("No files found!")
            return []

        sample_size = min(2, len(all_files))
        selected = random.sample(all_files, sample_size)

        print(f"\nRandom sample ({sample_size} files):")
        for i, f in enumerate(selected, 1):
            print(f"  {i}. {f.name}")
            print(f"     Path: {f}")

        return selected

    except Exception as e:
        print(f"ERROR: {e}")
        return []


def test_mapped_loader(config: ConfigLoader) -> list[Path]:
    """Test Mapped Data Loader."""
    print_header("Mapped Data Loader (mapped_data.py)")

    try:
        loader = MappedDataLoader(config)
        print(f"Base Path: {loader.mapper_output_dir}")

        if not loader.mapper_output_dir or not Path(loader.mapper_output_dir).exists():
            print("WARNING: Path does not exist!")
            return []

        filings = loader.discover_all_mapped_filings()
        print(f"Total filings discovered: {len(filings)}")

        if not filings:
            print("No filings found!")
            return []

        # Collect all files from filings
        all_files = []
        for filing in filings:
            for format_type, file_list in filing.available_files.items():
                all_files.extend(file_list)

        print(f"Total files in filings: {len(all_files)}")

        if not all_files:
            print("No files found in filings!")
            return []

        sample_size = min(2, len(all_files))
        selected = random.sample(all_files, sample_size)

        print(f"\nRandom sample ({sample_size} files):")
        for i, f in enumerate(selected, 1):
            print(f"  {i}. {f.name}")
            print(f"     Path: {f}")

        return selected

    except Exception as e:
        print(f"ERROR: {e}")
        return []


def test_taxonomy_loader(config: ConfigLoader) -> list[Path]:
    """Test Taxonomy Loader."""
    print_header("Taxonomy Loader (taxonomy.py)")

    try:
        loader = TaxonomyLoader(config)
        print(f"Base Path: {loader.taxonomy_path}")

        if not loader.taxonomy_path or not Path(loader.taxonomy_path).exists():
            print("WARNING: Path does not exist!")
            return []

        all_files = loader.discover_all_files()
        print(f"Total files discovered: {len(all_files)}")

        if not all_files:
            print("No files found!")
            return []

        sample_size = min(2, len(all_files))
        selected = random.sample(all_files, sample_size)

        print(f"\nRandom sample ({sample_size} files):")
        for i, f in enumerate(selected, 1):
            print(f"  {i}. {f.name}")
            print(f"     Path: {f}")

        return selected

    except Exception as e:
        print(f"ERROR: {e}")
        return []


def test_parsed_loader(config: ConfigLoader) -> list[Path]:
    """Test Parsed Data Loader."""
    print_header("Parsed Data Loader (parsed_data.py)")

    try:
        loader = ParsedDataLoader(config)
        print(f"Base Path: {loader.parser_output_dir}")

        if not loader.parser_output_dir or not Path(loader.parser_output_dir).exists():
            print("WARNING: Path does not exist!")
            return []

        filings = loader.discover_all_parsed_filings()
        print(f"Total filings discovered: {len(filings)}")

        if not filings:
            print("No filings found!")
            return []

        # Collect all files from filings
        # Note: ParsedFilingEntry.available_files is dict[str, Path] (single paths)
        all_files = []
        for filing in filings:
            for format_type, file_path in filing.available_files.items():
                if isinstance(file_path, Path):
                    all_files.append(file_path)
                elif isinstance(file_path, list):
                    all_files.extend(file_path)

        print(f"Total files in filings: {len(all_files)}")

        if not all_files:
            print("No files found in filings!")
            return []

        sample_size = min(2, len(all_files))
        selected = random.sample(all_files, sample_size)

        print(f"\nRandom sample ({sample_size} files):")
        for i, f in enumerate(selected, 1):
            print(f"  {i}. {f.name}")
            print(f"     Path: {f}")

        return selected

    except Exception as e:
        print(f"ERROR: {e}")
        return []


def main():
    print("="*60)
    print("BLIND DOORKEEPER TEST")
    print("Testing recursive file discovery for all 4 loaders")
    print("="*60)

    # Initialize config
    try:
        config = ConfigLoader()
        print(f"\nConfiguration loaded successfully")
    except Exception as e:
        print(f"ERROR loading config: {e}")
        return 1

    all_selected = []

    # Test all 4 doorkeepers
    all_selected.extend(test_xbrl_loader(config))
    all_selected.extend(test_mapped_loader(config))
    all_selected.extend(test_taxonomy_loader(config))
    all_selected.extend(test_parsed_loader(config))

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total files selected: {len(all_selected)} (expected: 8)")
    print("\nAll selected files:")
    for i, f in enumerate(all_selected, 1):
        print(f"  {i}. {f}")

    if len(all_selected) == 8:
        print("\nSUCCESS: All 4 doorkeepers found files!")
    elif len(all_selected) > 0:
        print(f"\nPARTIAL: {len(all_selected)}/8 files found")
    else:
        print("\nFAILED: No files found!")

    return 0 if len(all_selected) >= 4 else 1


if __name__ == "__main__":
    sys.exit(main())
