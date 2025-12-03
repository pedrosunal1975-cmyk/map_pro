#!/usr/bin/env python3
"""
Manual Taxonomy Indexer
========================

Indexes downloaded taxonomy files into the database.
Run this to populate the taxonomy_concepts table.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from engines.librarian.library_coordinator import LibraryCoordinator
from core.database_coordinator import db_coordinator
from database.models.library_models import TaxonomyLibrary, TaxonomyConcept


async def index_all_libraries():
    """Index all libraries that have total_concepts = 0."""
    
    print("=" * 80)
    print("TAXONOMY INDEXER - Manual Library Indexing")
    print("=" * 80)
    
    # Initialize database coordinator
    print("\n[TOOL] Initializing database coordinator...")
    try:
        db_coordinator.initialize()
        print("[OK] Database coordinator initialized")
    except Exception as e:
        print(f"[FAIL] Failed to initialize database coordinator: {e}")
        return
    
    # Get libraries that need indexing
    with db_coordinator.get_session('library') as session:
        libraries = session.query(TaxonomyLibrary).filter(
            TaxonomyLibrary.total_concepts == 0,
            TaxonomyLibrary.library_status == 'active'
        ).all()
        
        if not libraries:
            print("\n[OK] No libraries need indexing (all have concepts loaded)")
            return
        
        print(f"\n📚 Found {len(libraries)} libraries to index:\n")
        for lib in libraries:
            print(f"   - {lib.taxonomy_name}-{lib.taxonomy_version} "
                  f"({lib.total_files} files downloaded)")
    
    # Initialize library coordinator
    print("\n[TOOL] Initializing library coordinator...")
    coordinator = LibraryCoordinator()
    
    # Index each library
    success_count = 0
    failure_count = 0
    
    for library in libraries:
        lib_name = f"{library.taxonomy_name}-{library.taxonomy_version}"
        print(f"\n{'='*80}")
        print(f"📖 Indexing: {lib_name}")
        print(f"{'='*80}")
        
        try:
            # Call the re-index method
            result = await coordinator.re_index_library(library.library_id)
            
            if result.get('success'):
                concepts_indexed = result.get('concepts_indexed', 0)
                print(f"[OK] Successfully indexed {concepts_indexed} concepts")
                success_count += 1
            else:
                error = result.get('error', 'Unknown error')
                print(f"[FAIL] Failed: {error}")
                failure_count += 1
                
        except Exception as e:
            print(f"[FAIL] Exception during indexing: {e}")
            import traceback
            traceback.print_exc()
            failure_count += 1
    
    # Summary
    print(f"\n{'='*80}")
    print("INDEXING SUMMARY")
    print(f"{'='*80}")
    print(f"[OK] Successful: {success_count}")
    print(f"[FAIL] Failed: {failure_count}")
    print(f"Total: {len(libraries)}")
    
    # Verify results
    print(f"\n{'='*80}")
    print("VERIFICATION")
    print(f"{'='*80}")
    
    with db_coordinator.get_session('library') as session:
        from sqlalchemy import func
        
        total_concepts = session.query(func.count(TaxonomyConcept.concept_id)).scalar()
        print(f"Total concepts in database: {total_concepts:,}")
        
        if total_concepts > 0:
            print("\n[OK] Taxonomy concepts successfully loaded!")
            print("\nYou can now run the mapper and expect 80-100% mapping success.")
        else:
            print("\n[FAIL] No concepts were loaded. Check the errors above.")
    
    # Cleanup
    print("\n[TOOL] Shutting down database coordinator...")
    db_coordinator.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(index_all_libraries())
    except KeyboardInterrupt:
        print("\n\nIndexing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[FAIL] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)