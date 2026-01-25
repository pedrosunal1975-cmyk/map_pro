#!/usr/bin/env python3
"""
Map Pro Database Cleanup Tool
==============================

Standalone tool for comprehensive database cleanup and health check.
Can be run independently without starting the full Map Pro system.

Usage:
    python database_cleanup_tool.py --check          # Audit only (no changes)
    python database_cleanup_tool.py --clean          # Clean duplicates
    python database_cleanup_tool.py --constraints    # Add UNIQUE constraints
    python database_cleanup_tool.py --full           # Full cleanup + constraints

Requirements:
    - PostgreSQL connection details in .env or as arguments
    - psycopg2 package installed
"""

import argparse
import sys
from datetime import datetime
from typing import Dict, List, Tuple

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("ERROR: psycopg2 not installed. Install with: pip install psycopg2-binary")
    sys.exit(1)


class DatabaseCleanupTool:
    """
    Comprehensive database cleanup and health check tool.
    
    Handles:
    - Duplicate detection and removal
    - UNIQUE constraint management
    - Database health auditing
    - Detailed reporting
    """
    
    def __init__(self, db_config: Dict[str, str]):
        self.db_config = db_config
        self.results = {
            'core': {},
            'parsed': {},
            'mapped': {},
            'library': {}
        }
        
    def connect(self, database: str):
        """Create database connection."""
        config = self.db_config.copy()
        config['database'] = database
        return psycopg2.connect(**config)
    
    def audit_core_database(self, clean: bool = False) -> Dict:
        """
        Audit core database for duplicates and issues.
        
        Args:
            clean: If True, remove duplicates found
            
        Returns:
            Dict with audit results
        """
        print("\n" + "="*70)
        print("CORE DATABASE AUDIT")
        print("="*70)
        
        results = {}
        
        try:
            conn = self.connect('map_pro_core')
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Check duplicate documents
            print("\n1. Checking documents for duplicates...")
            cursor.execute("""
                SELECT 
                    COUNT(*) as duplicate_groups,
                    SUM(dup_count - 1) as total_duplicates
                FROM (
                    SELECT filing_universal_id, document_name, COUNT(*) as dup_count
                    FROM documents
                    GROUP BY filing_universal_id, document_name
                    HAVING COUNT(*) > 1
                ) AS dups
            """)
            doc_dups = cursor.fetchone()
            results['document_duplicates'] = doc_dups['total_duplicates'] or 0
            print(f"   Found: {results['document_duplicates']} duplicate documents")
            
            if clean and results['document_duplicates'] > 0:
                print("   Cleaning duplicates...")
                cursor.execute("""
                    DELETE FROM documents d1
                    USING documents d2
                    WHERE d1.filing_universal_id = d2.filing_universal_id
                    AND d1.document_name = d2.document_name
                    AND d1.document_universal_id > d2.document_universal_id
                """)
                deleted = cursor.rowcount
                conn.commit()
                print(f"   Deleted: {deleted} duplicate records")
                results['documents_cleaned'] = deleted
            
            # Check duplicate entities
            print("\n2. Checking entities for duplicates...")
            cursor.execute("""
                SELECT ticker_symbol, COUNT(*) as dup_count
                FROM entities
                WHERE ticker_symbol IS NOT NULL
                GROUP BY ticker_symbol
                HAVING COUNT(*) > 1
            """)
            entity_dups = cursor.fetchall()
            results['entity_duplicates'] = len(entity_dups)
            if entity_dups:
                print(f"   WARNING: {len(entity_dups)} duplicate ticker symbols found:")
                for dup in entity_dups[:5]:
                    print(f"      - {dup['ticker_symbol']}: {dup['dup_count']} occurrences")
            else:
                print("   OK: No duplicate entities")
            
            # Check duplicate filings
            print("\n3. Checking filings for duplicates...")
            cursor.execute("""
                SELECT market_filing_id, COUNT(*) as dup_count
                FROM filings
                GROUP BY market_filing_id
                HAVING COUNT(*) > 1
            """)
            filing_dups = cursor.fetchall()
            results['filing_duplicates'] = len(filing_dups)
            if filing_dups:
                print(f"   WARNING: {len(filing_dups)} duplicate filing IDs found")
            else:
                print("   OK: No duplicate filings")
            
            # Check for UNIQUE constraint
            print("\n4. Checking UNIQUE constraints...")
            cursor.execute("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = 'documents'
                AND constraint_name = 'documents_unique_filing_name'
            """)
            constraint_exists = cursor.fetchone() is not None
            results['documents_constraint'] = constraint_exists
            print(f"   documents UNIQUE constraint: {'EXISTS' if constraint_exists else 'MISSING'}")
            
            # Summary statistics
            print("\n5. Database statistics...")
            cursor.execute("SELECT COUNT(*) as count FROM entities")
            results['total_entities'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM filings")
            results['total_filings'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM documents")
            results['total_documents'] = cursor.fetchone()['count']
            
            cursor.execute("""
                SELECT job_type, COUNT(*) as count, job_status
                FROM processing_jobs
                GROUP BY job_type, job_status
                ORDER BY job_type, job_status
            """)
            job_stats = cursor.fetchall()
            results['job_statistics'] = job_stats
            
            print(f"   Entities: {results['total_entities']}")
            print(f"   Filings: {results['total_filings']}")
            print(f"   Documents: {results['total_documents']}")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"ERROR: Core database audit failed: {e}")
            results['error'] = str(e)
        
        return results
    
    def audit_parsed_database(self, clean: bool = False) -> Dict:
        """
        Audit parsed database for duplicates.
        
        Args:
            clean: If True, remove duplicates found
            
        Returns:
            Dict with audit results
        """
        print("\n" + "="*70)
        print("PARSED DATABASE AUDIT")
        print("="*70)
        
        results = {}
        
        try:
            conn = self.connect('map_pro_parsed')
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Check duplicate parsed_documents
            print("\n1. Checking parsed_documents for duplicates...")
            cursor.execute("""
                SELECT 
                    COUNT(*) as duplicate_groups,
                    SUM(dup_count - 1) as total_duplicates,
                    SUM(total_facts) as inflated_facts
                FROM (
                    SELECT 
                        filing_universal_id,
                        document_name,
                        COUNT(*) as dup_count,
                        SUM(facts_extracted) as total_facts
                    FROM parsed_documents
                    GROUP BY filing_universal_id, document_name
                    HAVING COUNT(*) > 1
                ) AS dups
            """)
            parsed_dups = cursor.fetchone()
            results['parsed_duplicates'] = parsed_dups['total_duplicates'] or 0
            results['inflated_facts'] = parsed_dups['inflated_facts'] or 0
            
            print(f"   Found: {results['parsed_duplicates']} duplicate parsed_documents")
            if results['inflated_facts'] > 0:
                print(f"   WARNING: {results['inflated_facts']} inflated fact count due to duplicates")
            
            if clean and results['parsed_duplicates'] > 0:
                print("   Cleaning duplicates...")
                cursor.execute("""
                    DELETE FROM parsed_documents p1
                    USING parsed_documents p2
                    WHERE p1.filing_universal_id = p2.filing_universal_id
                    AND p1.document_name = p2.document_name
                    AND p1.parsed_document_id > p2.parsed_document_id
                """)
                deleted = cursor.rowcount
                conn.commit()
                print(f"   Deleted: {deleted} duplicate records")
                results['parsed_cleaned'] = deleted
            
            # Check for UNIQUE constraint
            print("\n2. Checking UNIQUE constraints...")
            cursor.execute("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = 'parsed_documents'
                AND constraint_name = 'parsed_documents_unique_filing_doc'
            """)
            constraint_exists = cursor.fetchone() is not None
            results['parsed_constraint'] = constraint_exists
            print(f"   parsed_documents UNIQUE constraint: {'EXISTS' if constraint_exists else 'MISSING'}")
            
            # Summary statistics
            print("\n3. Database statistics...")
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(DISTINCT filing_universal_id) as unique_filings,
                    SUM(facts_extracted) as total_facts
                FROM parsed_documents
            """)
            stats = cursor.fetchone()
            results['total_parsed'] = stats['total_records']
            results['unique_filings'] = stats['unique_filings']
            results['total_facts'] = stats['total_facts']
            
            print(f"   Parsed documents: {results['total_parsed']}")
            print(f"   Unique filings: {results['unique_filings']}")
            print(f"   Total facts: {results['total_facts']}")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"ERROR: Parsed database audit failed: {e}")
            results['error'] = str(e)
        
        return results
    
    def audit_mapped_database(self) -> Dict:
        """Audit mapped database for issues."""
        print("\n" + "="*70)
        print("MAPPED DATABASE AUDIT")
        print("="*70)
        
        results = {}
        
        try:
            conn = self.connect('map_pro_mapped')
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Check duplicate mapped_statements
            print("\n1. Checking mapped_statements for duplicates...")
            cursor.execute("""
                SELECT 
                    statement_type,
                    COUNT(*) as total_records,
                    COUNT(DISTINCT filing_universal_id) as unique_filings,
                    COUNT(*) - COUNT(DISTINCT filing_universal_id) as duplicates
                FROM mapped_statements
                GROUP BY statement_type
                HAVING COUNT(*) - COUNT(DISTINCT filing_universal_id) > 0
            """)
            mapped_dups = cursor.fetchall()
            results['mapped_duplicates'] = len(mapped_dups)
            
            if mapped_dups:
                print(f"   WARNING: Found duplicates in {len(mapped_dups)} statement types")
                for dup in mapped_dups:
                    print(f"      - {dup['statement_type']}: {dup['duplicates']} duplicates")
            else:
                print("   OK: No duplicates found")
            
            # Summary statistics
            print("\n2. Database statistics...")
            cursor.execute("""
                SELECT 
                    statement_type,
                    COUNT(*) as record_count,
                    COUNT(DISTINCT filing_universal_id) as unique_filings
                FROM mapped_statements
                GROUP BY statement_type
                ORDER BY statement_type
            """)
            stats = cursor.fetchall()
            results['statement_stats'] = stats
            
            for stat in stats:
                print(f"   {stat['statement_type']}: {stat['record_count']} records")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"ERROR: Mapped database audit failed: {e}")
            results['error'] = str(e)
        
        return results
    
    def add_constraints(self) -> Dict:
        """Add UNIQUE constraints to prevent future duplicates."""
        print("\n" + "="*70)
        print("ADDING UNIQUE CONSTRAINTS")
        print("="*70)
        
        results = {}
        
        # Core database constraints
        try:
            print("\n1. Adding constraints to core database...")
            conn = self.connect('map_pro_core')
            cursor = conn.cursor()
            
            # Documents constraint
            try:
                cursor.execute("""
                    ALTER TABLE documents 
                    ADD CONSTRAINT documents_unique_filing_name 
                    UNIQUE (filing_universal_id, document_name)
                """)
                conn.commit()
                print("   Added: documents_unique_filing_name")
                results['documents_constraint'] = 'added'
            except psycopg2.errors.DuplicateTable:
                conn.rollback()
                print("   Skipped: documents_unique_filing_name (already exists)")
                results['documents_constraint'] = 'exists'
            
            # Job indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_filing_type_status 
                ON processing_jobs (job_type, filing_universal_id, job_status)
                WHERE filing_universal_id IS NOT NULL
            """)
            conn.commit()
            print("   Added: idx_jobs_filing_type_status")
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_entity_type_status 
                ON processing_jobs (job_type, entity_universal_id, job_status)
                WHERE entity_universal_id IS NOT NULL
            """)
            conn.commit()
            print("   Added: idx_jobs_entity_type_status")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"ERROR: Failed to add core constraints: {e}")
            results['core_error'] = str(e)
        
        # Parsed database constraints
        try:
            print("\n2. Adding constraints to parsed database...")
            conn = self.connect('map_pro_parsed')
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    ALTER TABLE parsed_documents 
                    ADD CONSTRAINT parsed_documents_unique_filing_doc 
                    UNIQUE (filing_universal_id, document_name)
                """)
                conn.commit()
                print("   Added: parsed_documents_unique_filing_doc")
                results['parsed_constraint'] = 'added'
            except psycopg2.errors.DuplicateTable:
                conn.rollback()
                print("   Skipped: parsed_documents_unique_filing_doc (already exists)")
                results['parsed_constraint'] = 'exists'
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"ERROR: Failed to add parsed constraints: {e}")
            results['parsed_error'] = str(e)
        
        return results
    
    def run_full_cleanup(self) -> Dict:
        """Run complete cleanup: audit, clean, add constraints."""
        print("\n" + "="*70)
        print("COMPREHENSIVE DATABASE CLEANUP")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        results = {}
        
        # Audit first
        results['core_audit'] = self.audit_core_database(clean=False)
        results['parsed_audit'] = self.audit_parsed_database(clean=False)
        results['mapped_audit'] = self.audit_mapped_database()
        
        # Clean duplicates
        print("\n" + "="*70)
        print("CLEANING DUPLICATES")
        print("="*70)
        
        results['core_clean'] = self.audit_core_database(clean=True)
        results['parsed_clean'] = self.audit_parsed_database(clean=True)
        
        # Add constraints
        results['constraints'] = self.add_constraints()
        
        # Final verification
        print("\n" + "="*70)
        print("FINAL VERIFICATION")
        print("="*70)
        
        results['final_core'] = self.audit_core_database(clean=False)
        results['final_parsed'] = self.audit_parsed_database(clean=False)
        
        print("\n" + "="*70)
        print("CLEANUP COMPLETE")
        print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        return results


def main():
    """Main entry point for the cleanup tool."""
    parser = argparse.ArgumentParser(
        description='Map Pro Database Cleanup Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python database_cleanup_tool.py --check
  python database_cleanup_tool.py --clean
  python database_cleanup_tool.py --full
  python database_cleanup_tool.py --host localhost --user map_pro_user --check
        """
    )
    
    parser.add_argument('--check', action='store_true',
                       help='Audit databases (no changes)')
    parser.add_argument('--clean', action='store_true',
                       help='Clean duplicates from databases')
    parser.add_argument('--constraints', action='store_true',
                       help='Add UNIQUE constraints')
    parser.add_argument('--full', action='store_true',
                       help='Full cleanup (audit + clean + constraints)')
    
    parser.add_argument('--host', default='localhost',
                       help='Database host (default: localhost)')
    parser.add_argument('--port', type=int, default=5432,
                       help='Database port (default: 5432)')
    parser.add_argument('--user', default='map_pro_user',
                       help='Database user (default: map_pro_user)')
    parser.add_argument('--password', default='map_pro_pass',
                       help='Database password (default: map_pro_pass)')
    
    args = parser.parse_args()
    
    # Require at least one action
    if not any([args.check, args.clean, args.constraints, args.full]):
        parser.print_help()
        sys.exit(1)
    
    # Database configuration
    db_config = {
        'host': args.host,
        'port': args.port,
        'user': args.user,
        'password': args.password
    }
    
    # Create cleanup tool
    tool = DatabaseCleanupTool(db_config)
    
    try:
        if args.full:
            results = tool.run_full_cleanup()
        else:
            if args.check:
                tool.audit_core_database(clean=False)
                tool.audit_parsed_database(clean=False)
                tool.audit_mapped_database()
            
            if args.clean:
                tool.audit_core_database(clean=True)
                tool.audit_parsed_database(clean=True)
            
            if args.constraints:
                tool.add_constraints()
        
        print("\n[SUCCESS] Database cleanup completed")
        
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Cleanup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Cleanup failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()