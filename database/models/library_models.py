# File: /map_pro/database/models/library_models.py

"""
Map Pro Library Database Models
===============================

SQLAlchemy models for the library database (map_pro_library).
Handles taxonomy libraries, concepts, and library management.

CRITICAL CHANGE: Models now verify physical file existence.
Database is a REFLECTION of reality, not the source of truth.

Architecture: Maps to PostgreSQL library database schema.
"""

from pathlib import Path
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date, Text,
    DECIMAL, BigInteger, UUID, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
import uuid as uuid_module

from .core_models import Base

DEFAULT_LIBRARY_STATUS = 'active'
DEFAULT_VALIDATION_STATUS = 'pending'
DEFAULT_FILE_STATUS = 'healthy'
DEFAULT_COUNT = 0

MAX_TAXONOMY_NAME_LENGTH = 100
MAX_VERSION_LENGTH = 50
MAX_AUTHORITY_LENGTH = 100
MAX_STATUS_LENGTH = 20
MAX_LOCAL_NAME_LENGTH = 255
MAX_CONCEPT_TYPE_LENGTH = 50
MAX_PERIOD_TYPE_LENGTH = 20
MAX_FILE_NAME_LENGTH = 255
MAX_FILE_TYPE_LENGTH = 50
MAX_CHECK_TYPE_LENGTH = 50
MAX_SHA256_LENGTH = 64

SIZE_PRECISION = 10
SIZE_SCALE = 2

# Relevant file extensions for counting
RELEVANT_EXTENSIONS = {'.xsd', '.xml', '.html', '.htm', '.xbri'}


class TaxonomyLibrary(Base):
    """
    Registry of taxonomy libraries (US-GAAP, IFRS, ESEF, etc.).
    
    CRITICAL: This model now verifies physical file existence.
    Use .files_actually_exist property to check reality.
    """
    __tablename__ = 'taxonomy_libraries'
    
    library_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    taxonomy_name = Column(String(MAX_TAXONOMY_NAME_LENGTH), nullable=False)
    taxonomy_version = Column(String(MAX_VERSION_LENGTH), nullable=False)
    taxonomy_authority = Column(String(MAX_AUTHORITY_LENGTH), nullable=False)
    base_namespace = Column(Text, nullable=False)
    library_status = Column(String(MAX_STATUS_LENGTH), default=DEFAULT_LIBRARY_STATUS)
    download_source_url = Column(Text)
    library_directory_path = Column(Text)
    total_concepts = Column(Integer, default=DEFAULT_COUNT)
    total_files = Column(Integer, default=DEFAULT_COUNT)
    library_size_mb = Column(DECIMAL(SIZE_PRECISION, SIZE_SCALE))
    download_date = Column(Date)
    last_validated_at = Column(DateTime(timezone=True))
    validation_status = Column(String(MAX_STATUS_LENGTH), default=DEFAULT_VALIDATION_STATUS)
    is_required_by_markets = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    concepts = relationship("TaxonomyConcept", back_populates="library", cascade="all, delete-orphan")
    files = relationship("TaxonomyFile", back_populates="library", cascade="all, delete-orphan")
    health_checks = relationship("LibraryHealthCheck", back_populates="library", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('taxonomy_name', 'taxonomy_version', name='taxonomy_name_version_unique'),
    )
    
    @property
    def directory_exists(self) -> bool:
        """
        Check if library directory actually exists on disk.
        
        CRITICAL: This checks REALITY, not database.
        
        Returns:
            True if directory exists, False otherwise
        """
        if not self.library_directory_path:
            return False
        
        try:
            path = Path(self.library_directory_path)
            return path.exists() and path.is_dir()
        except Exception:
            return False
    
    @property
    def actual_file_count(self) -> int:
        """
        Count actual files in library directory.
        
        CRITICAL: This counts REAL files, not database records.
        
        Returns:
            Number of actual taxonomy files on disk
        """
        if not self.directory_exists:
            return 0
        
        try:
            path = Path(self.library_directory_path)
            count = 0
            
            for file_path in path.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in RELEVANT_EXTENSIONS:
                    count += 1
            
            return count
        except Exception:
            return 0
    
    @property
    def files_actually_exist(self) -> bool:
        """
        Check if library files actually exist on disk.
        
        CRITICAL: Use this instead of trusting total_files in database.
        
        Returns:
            True if directory exists and contains files
        """
        return self.directory_exists and self.actual_file_count > 0
    
    @property
    def database_matches_reality(self) -> bool:
        """
        Check if database record matches physical reality.
        
        Returns:
            True if database file count matches actual files
        """
        actual = self.actual_file_count
        recorded = self.total_files or 0
        return actual == recorded
    
    @property
    def is_truly_available(self) -> bool:
        """
        Check if library is TRULY available for use.
        
        This is the CORRECT way to check availability:
        - Database says it's active
        - Database says it has files
        - Files ACTUALLY exist on disk
        
        Returns:
            True only if library is genuinely ready to use
        """
        # Check database status
        if self.library_status != 'active':
            return False
        
        # Check database file count
        if not self.total_files or self.total_files == 0:
            return False
        
        # CRITICAL: Verify files actually exist
        if not self.files_actually_exist:
            return False
        
        return True
    
    def sync_with_reality(self) -> dict:
        """
        Synchronize database record with physical reality.
        
        Updates total_files and validation_status to match actual files.
        
        Returns:
            Dictionary with sync results
        """
        actual_files = self.actual_file_count
        recorded_files = self.total_files or 0
        
        result = {
            'changed': False,
            'actual_files': actual_files,
            'recorded_files': recorded_files
        }
        
        if actual_files != recorded_files:
            self.total_files = actual_files
            
            if actual_files == 0:
                self.validation_status = 'needs_download'
                self.library_status = 'missing'
            elif self.total_concepts == 0:
                self.validation_status = 'needs_indexing'
                self.library_status = 'active'
            
            result['changed'] = True
        
        return result
    
    def __repr__(self):
        return f"<TaxonomyLibrary(name={self.taxonomy_name}, version={self.taxonomy_version})>"


class TaxonomyConcept(Base):
    """Individual concepts defined within taxonomies."""
    __tablename__ = 'taxonomy_concepts'
    
    concept_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    library_id = Column(UUID(as_uuid=True), ForeignKey('taxonomy_libraries.library_id', ondelete='CASCADE'), nullable=False, index=True)
    concept_qname = Column(Text, nullable=False, index=True)
    concept_local_name = Column(String(MAX_LOCAL_NAME_LENGTH), nullable=False, index=True)
    concept_namespace = Column(Text, nullable=False)
    concept_type = Column(String(MAX_CONCEPT_TYPE_LENGTH))
    period_type = Column(String(MAX_PERIOD_TYPE_LENGTH))
    balance_type = Column(String(MAX_PERIOD_TYPE_LENGTH))
    abstract_concept = Column(Boolean, default=False)
    concept_label = Column(Text)
    concept_definition = Column(Text)
    concept_documentation = Column(Text)
    data_type = Column(String(MAX_CONCEPT_TYPE_LENGTH))
    usage_frequency = Column(Integer, default=DEFAULT_COUNT)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    library = relationship("TaxonomyLibrary", back_populates="concepts")
    
    __table_args__ = (
        Index('taxonomy_concepts_library_id_idx', 'library_id'),
        Index('taxonomy_concepts_qname_idx', 'concept_qname'),
        Index('taxonomy_concepts_local_name_idx', 'concept_local_name'),
    )
    
    def __repr__(self):
        return f"<TaxonomyConcept(qname={self.concept_qname})>"


class TaxonomyFile(Base):
    """Registry of taxonomy files within libraries."""
    __tablename__ = 'taxonomy_files'
    
    file_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    library_id = Column(UUID(as_uuid=True), ForeignKey('taxonomy_libraries.library_id', ondelete='CASCADE'), nullable=False, index=True)
    file_name = Column(String(MAX_FILE_NAME_LENGTH), nullable=False)
    file_type = Column(String(MAX_FILE_TYPE_LENGTH), nullable=False)
    file_path = Column(Text, nullable=False)
    file_size_bytes = Column(BigInteger)
    file_hash_sha256 = Column(String(MAX_SHA256_LENGTH))
    concepts_defined = Column(Integer, default=DEFAULT_COUNT)
    file_status = Column(String(MAX_STATUS_LENGTH), default=DEFAULT_FILE_STATUS)
    last_validated_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    library = relationship("TaxonomyLibrary", back_populates="files")
    
    __table_args__ = (
        Index('taxonomy_files_library_id_idx', 'library_id'),
        UniqueConstraint('library_id', 'file_path', name='library_file_path_unique'),
    )
    
    def __repr__(self):
        return f"<TaxonomyFile(name={self.file_name})>"


class LibraryHealthCheck(Base):
    """Records of library validation checks."""
    __tablename__ = 'library_health_checks'
    
    check_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    library_id = Column(UUID(as_uuid=True), ForeignKey('taxonomy_libraries.library_id', ondelete='CASCADE'), nullable=False, index=True)
    checked_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())  # NOT check_timestamp
    check_type = Column(String(MAX_CHECK_TYPE_LENGTH), nullable=False)
    check_status = Column(String(MAX_STATUS_LENGTH), nullable=False)
    issues_found = Column(Integer, default=DEFAULT_COUNT)
    critical_issues = Column(Integer, default=DEFAULT_COUNT)
    check_results = Column(JSONB)  # NOT check_details
    check_duration_seconds = Column(DECIMAL(10, 6))
    
    library = relationship("TaxonomyLibrary", back_populates="health_checks")
    
    __table_args__ = (
        Index('library_health_checks_library_id_idx', 'library_id'),
    )
    
    def __repr__(self):
        return f"<LibraryHealthCheck(library_id={self.library_id}, status={self.check_status})>"


__all__ = [
    'TaxonomyLibrary',
    'TaxonomyConcept',
    'TaxonomyFile',
    'LibraryHealthCheck'
]