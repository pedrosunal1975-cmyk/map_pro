"""
Database Schema Verification - Foreign Key Checker
===================================================

Location: tools/cli/foreign_key_checker.py

Checks and reports on foreign key constraints.
"""

from typing import List, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session

from .db_check_constants import DiagnosticConstants, DiagnosticMessages, SQLQueries
from .db_check_models import ForeignKeyInfo


class ForeignKeyChecker:
    """Checks and reports on foreign key constraints."""
    
    def __init__(self, session: Session):
        """
        Initialize the foreign key checker.
        
        Args:
            session: Database session
        """
        self.session = session
    
    def get_table_structure(self) -> List[Tuple]:
        """
        Get the structure of the processing_jobs table.
        
        Returns:
            List of tuples containing column information
        """
        query = text(SQLQueries.TABLE_STRUCTURE)
        return self.session.execute(
            query, 
            {'table_name': DiagnosticConstants.PROCESSING_JOBS_TABLE}
        ).fetchall()
    
    def get_foreign_key_constraints(self) -> List[ForeignKeyInfo]:
        """
        Get foreign key constraints for the processing_jobs table.
        
        Returns:
            List of ForeignKeyInfo objects
        """
        query = text(SQLQueries.FOREIGN_KEY_CONSTRAINTS)
        
        results = self.session.execute(
            query,
            {'table_name': DiagnosticConstants.PROCESSING_JOBS_TABLE}
        ).fetchall()
        
        return [
            ForeignKeyInfo(
                constraint_name=row[0],
                column_name=row[1],
                foreign_table=row[2],
                foreign_column=row[3]
            )
            for row in results
        ]
    
    def get_entity_count(self) -> int:
        """
        Get the count of entities in the entities table.
        
        Returns:
            Number of entities
        """
        query = text(
            SQLQueries.ENTITY_COUNT.format(
                table_name=DiagnosticConstants.ENTITIES_TABLE
            )
        )
        return self.session.execute(query).fetchone()[0]
    
    def print_table_structure(self, structure: List[Tuple]) -> None:
        """
        Print table structure in a formatted manner.
        
        Args:
            structure: List of column information tuples
        """
        print(DiagnosticMessages.HEADER_TABLE_STRUCTURE.format(
            DiagnosticConstants.PROCESSING_JOBS_TABLE
        ))
        for row in structure:
            print(f"  {row[0]}: {row[1]} (nullable: {row[2]})")
    
    def print_foreign_keys(self, foreign_keys: List[ForeignKeyInfo]) -> None:
        """
        Print foreign key constraints in a formatted manner.
        
        Args:
            foreign_keys: List of ForeignKeyInfo objects
        """
        print(DiagnosticMessages.HEADER_FOREIGN_KEYS)
        for fk in foreign_keys:
            print(f"  {fk.column_name} -> {fk.foreign_table}.{fk.foreign_column} "
                  f"({fk.constraint_name})")