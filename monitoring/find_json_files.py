#!/usr/bin/env python3
"""
Find JSON Files Diagnostic Script
=================================

Helps locate where the JSON files were actually created and
compares with expected paths from the database.

Save location: tools/monitoring/find_json_files.py
Run command: python tools/monitoring/find_json_files.py
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.database_coordinator import db_coordinator
from core.data_paths import map_pro_paths
from database.models.core_models import Document, Filing, Entity


def find_all_json_files():
    """Find all JSON files in the parsed_facts directory."""
    print("\n" + "="*80)
    print("SEARCHING FOR JSON FILES IN PARSED_FACTS DIRECTORY")
    print("="*80 + "\n")
    
    parsed_facts_root = map_pro_paths.data_parsed_facts
    print(f"[DIR] Searching in: {parsed_facts_root}\n")
    
    if not parsed_facts_root.exists():
        print("[FAIL] ERROR: parsed_facts directory does not exist!")
        return []
    
    # Find all JSON files recursively
    json_files = list(parsed_facts_root.rglob('*.json'))
    
    if not json_files:
        print("[WARNING]  No JSON files found in parsed_facts directory")
        return []
    
    print(f"[OK] Found {len(json_files)} JSON file(s):\n")
    
    for idx, json_file in enumerate(json_files, 1):
        # Get relative path for display
        rel_path = json_file.relative_to(parsed_facts_root)
        file_size = json_file.stat().st_size / 1024  # KB
        mod_time = datetime.fromtimestamp(json_file.stat().st_mtime)
        
        print(f"[FILE] File {idx}:")
        print(f"   Path: {rel_path}")
        print(f"   Full: {json_file}")
        print(f"   Size: {file_size:.2f} KB")
        print(f"   Modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    return json_files


def check_database_paths():
    """Check what paths are stored in the database."""
    print("\n" + "="*80)
    print("CHECKING DATABASE FACTS_JSON_PATH VALUES")
    print("="*80 + "\n")
    
    with db_coordinator.get_session('core') as session:
        # Get all documents with facts_json_path set
        docs_with_paths = session.query(Document).filter(
            Document.facts_json_path.isnot(None)
        ).all()
        
        if not docs_with_paths:
            print("[WARNING]  No documents have facts_json_path set in database")
            return
        
        print(f"[OK] Found {len(docs_with_paths)} document(s) with JSON paths in database:\n")
        
        for idx, doc in enumerate(docs_with_paths, 1):
            # Extract filing and entity info
            filing = doc.filing
            entity = filing.entity if filing else None
            
            json_path = Path(doc.facts_json_path)
            exists = json_path.exists()
            
            print(f"[FILE] Document {idx}:")
            print(f"   ID: {doc.document_universal_id}")
            print(f"   Name: {doc.document_name}")
            if entity:
                print(f"   Company: {entity.primary_name}")
                print(f"   Market: {entity.market_type}")
            if filing:
                print(f"   Filing Type: {filing.filing_type}")
            print(f"   Stored Path: {doc.facts_json_path}")
            print(f"   File Exists: {'[OK] YES' if exists else '[FAIL] NO'}")
            if exists:
                file_size = json_path.stat().st_size / 1024
                print(f"   File Size: {file_size:.2f} KB")
            print()


def generate_expected_path(doc):
    """Generate what the expected path SHOULD be based on the new logic."""
    filing = doc.filing
    entity = filing.entity if filing else None
    
    if not entity:
        return None
    
    # Clean company name
    company_name = entity.primary_name.replace('/', '_').replace(' ', '_')
    
    # Get instance name from document
    instance_name = Path(doc.document_name).stem if doc.document_name else 'unknown_instance'
    
    # Build expected path
    expected_path = (
        map_pro_paths.data_parsed_facts / 
        entity.market_type / 
        company_name / 
        filing.filing_type / 
        instance_name /
        'facts.json'
    )
    
    return expected_path


def compare_paths():
    """Compare stored paths with expected paths."""
    print("\n" + "="*80)
    print("COMPARING STORED VS EXPECTED PATHS")
    print("="*80 + "\n")
    
    with db_coordinator.get_session('core') as session:
        # Get completed parsed documents
        completed_docs = session.query(Document).filter(
            Document.parsed_status == 'completed'
        ).all()
        
        if not completed_docs:
            print("[WARNING]  No completed parsed documents found")
            return
        
        print(f"[OK] Analyzing {len(completed_docs)} completed document(s):\n")
        
        for idx, doc in enumerate(completed_docs, 1):
            filing = doc.filing
            entity = filing.entity if filing else None
            
            stored_path = doc.facts_json_path
            expected_path = generate_expected_path(doc)
            
            print(f"[FILE] Document {idx}: {doc.document_name}")
            if entity:
                print(f"   Company: {entity.primary_name}")
            
            if stored_path:
                print(f"   Stored Path: {stored_path}")
                stored_exists = Path(stored_path).exists()
                print(f"   Stored Exists: {'[OK] YES' if stored_exists else '[FAIL] NO'}")
            else:
                print(f"   Stored Path: [FAIL] None")
            
            if expected_path:
                print(f"   Expected Path: {expected_path}")
                expected_exists = expected_path.exists()
                print(f"   Expected Exists: {'[OK] YES' if expected_exists else '[FAIL] NO'}")
                
                # Compare
                if stored_path and expected_path:
                    match = Path(stored_path) == expected_path
                    print(f"   Paths Match: {'[OK] YES' if match else '[FAIL] NO'}")
            
            print()


def main():
    """Main diagnostic function."""
    print("\n" + "="*80)
    print("JSON FILE LOCATION DIAGNOSTIC TOOL")
    print("="*80)
    
    # Initialize database
    if not db_coordinator._is_initialized:
        db_coordinator.initialize()
    
    # Run diagnostics
    find_all_json_files()
    check_database_paths()
    compare_paths()
    
    print("\n" + "="*80)
    print("DIAGNOSTIC COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()