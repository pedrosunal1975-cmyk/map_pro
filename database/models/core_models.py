# File: /map_pro/database/models/core_models.py

"""
Map Pro Core Database Models
============================

SQLAlchemy models for the core database (map_pro_core).
Handles entities, filings, documents, jobs, and system configuration.

Architecture: Uses PostgreSQL native features with minimal ORM complexity.
"""

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date, Text, 
    DECIMAL, BigInteger, UUID, CheckConstraint, Index,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timezone
import uuid as uuid_module

Base = declarative_base()

MAX_CONFIG_KEY_LENGTH = 100
MAX_CONFIG_TYPE_LENGTH = 20
MAX_MODULE_OWNER_LENGTH = 50
MAX_MARKET_ID_LENGTH = 10
MAX_MARKET_NAME_LENGTH = 100
MAX_MARKET_COUNTRY_CODE_LENGTH = 3
DEFAULT_RATE_LIMIT_PER_MINUTE = 10
MAX_ENTITY_MARKET_ID_LENGTH = 50
MAX_ENTITY_NAME_LENGTH = 255
MAX_TICKER_SYMBOL_LENGTH = 20
MAX_ENTITY_STATUS_LENGTH = 20
DEFAULT_ENTITY_STATUS = 'active'
DEFAULT_FILINGS_COUNT = 0
MAX_MARKET_FILING_ID_LENGTH = 100
MAX_FILING_TYPE_LENGTH = 50
DEFAULT_FILING_STATUS = 'pending'
DECIMAL_PRECISION_SIZE_MB = 10
DECIMAL_SCALE_SIZE_MB = 2
MAX_DOCUMENT_NAME_LENGTH = 255
MAX_DOCUMENT_TYPE_LENGTH = 50
MAX_FILE_HASH_LENGTH = 64
DEFAULT_FACTS_COUNT = 0
MAX_JOB_TYPE_LENGTH = 50
MAX_JOB_STATUS_LENGTH = 20
DEFAULT_JOB_STATUS = 'queued'
DEFAULT_JOB_PRIORITY = 5
DEFAULT_RETRY_COUNT = 0


class SystemConfig(Base):
    """System configuration storage."""
    __tablename__ = 'system_config'
    
    config_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    config_key = Column(String(MAX_CONFIG_KEY_LENGTH), nullable=False, unique=True)
    config_value = Column(Text, nullable=False)
    config_type = Column(String(MAX_CONFIG_TYPE_LENGTH), default='string')
    module_owner = Column(String(MAX_MODULE_OWNER_LENGTH))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Market(Base):
    """Market registry for all supported regulatory markets."""
    __tablename__ = 'markets'
    
    market_id = Column(String(MAX_MARKET_ID_LENGTH), primary_key=True)
    market_name = Column(String(MAX_MARKET_NAME_LENGTH), nullable=False)
    market_country = Column(String(MAX_MARKET_COUNTRY_CODE_LENGTH), nullable=False)
    api_base_url = Column(Text)
    is_active = Column(Boolean, default=True)
    rate_limit_per_minute = Column(Integer, default=DEFAULT_RATE_LIMIT_PER_MINUTE)
    user_agent_required = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    entities = relationship("Entity", back_populates="market")


class Entity(Base):
    """Company entities across all markets."""
    __tablename__ = 'entities'
    
    entity_universal_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    market_type = Column(String(MAX_MARKET_ID_LENGTH), ForeignKey('markets.market_id'), nullable=False)
    market_entity_id = Column(String(MAX_ENTITY_MARKET_ID_LENGTH), nullable=False)
    primary_name = Column(String(MAX_ENTITY_NAME_LENGTH), nullable=False)
    ticker_symbol = Column(String(MAX_TICKER_SYMBOL_LENGTH))
    entity_status = Column(String(MAX_ENTITY_STATUS_LENGTH), default=DEFAULT_ENTITY_STATUS)
    data_directory_path = Column(Text)
    last_filing_date = Column(Date)
    total_filings_count = Column(Integer, default=DEFAULT_FILINGS_COUNT)
    identifiers = Column(JSONB)
    search_history = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('market_type', 'market_entity_id', name='entities_market_entity_unique'),
        CheckConstraint('total_filings_count >= 0', name='entities_filing_count_positive'),
        Index('idx_entities_market_type', 'market_type'),
        Index('idx_entities_status', 'entity_status'),
    )
    
    market = relationship("Market", back_populates="entities")
    filings = relationship("Filing", back_populates="entity")
    processing_jobs = relationship("ProcessingJob", back_populates="entity")


class Filing(Base):
    """Filing registry with file system tracking."""
    __tablename__ = 'filings'
    
    filing_universal_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    entity_universal_id = Column(UUID(as_uuid=True), ForeignKey('entities.entity_universal_id', ondelete='CASCADE'), nullable=False)
    market_filing_id = Column(String(MAX_MARKET_FILING_ID_LENGTH), nullable=False)
    filing_type = Column(String(MAX_FILING_TYPE_LENGTH), nullable=False)
    filing_date = Column(Date, nullable=False)
    period_start_date = Column(Date)
    period_end_date = Column(Date)
    filing_title = Column(Text)
    download_status = Column(String(MAX_JOB_STATUS_LENGTH), default=DEFAULT_FILING_STATUS)
    extraction_status = Column(String(MAX_JOB_STATUS_LENGTH), default=DEFAULT_FILING_STATUS)
    filing_directory_path = Column(Text)
    original_url = Column(Text)
    download_size_mb = Column(DECIMAL(DECIMAL_PRECISION_SIZE_MB, DECIMAL_SCALE_SIZE_MB))
    download_completed_at = Column(DateTime(timezone=True))
    extraction_completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_filings_entity', 'entity_universal_id'),
        Index('idx_filings_date', 'filing_date'),
    )
    
    entity = relationship("Entity", back_populates="filings")
    documents = relationship("Document", back_populates="filing")
    processing_jobs = relationship("ProcessingJob", back_populates="filing")


class Document(Base):
    """Document tracking within filings."""
    __tablename__ = 'documents'
    
    document_universal_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    filing_universal_id = Column(UUID(as_uuid=True), ForeignKey('filings.filing_universal_id', ondelete='CASCADE'), nullable=False)
    document_name = Column(String(MAX_DOCUMENT_NAME_LENGTH), nullable=False)
    document_type = Column(String(MAX_DOCUMENT_TYPE_LENGTH))
    file_size_bytes = Column(BigInteger)
    file_hash_sha256 = Column(String(MAX_FILE_HASH_LENGTH))
    download_path = Column(Text)
    extraction_path = Column(Text)
    is_xbrl_instance = Column(Boolean, default=False)
    parsing_eligible = Column(Boolean, default=False)
    parsed_status = Column(String(MAX_JOB_STATUS_LENGTH), default=DEFAULT_FILING_STATUS)
    facts_json_path = Column(Text)  
    facts_count = Column(Integer, default=DEFAULT_FACTS_COUNT) 
    parsing_metadata = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_documents_filing', 'filing_universal_id'),
    )
    
    filing = relationship("Filing", back_populates="documents")


class ProcessingJob(Base):
    """Processing job queue for cross-engine coordination."""
    __tablename__ = 'processing_jobs'
    
    job_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    job_type = Column(String(MAX_JOB_TYPE_LENGTH), nullable=False)
    job_status = Column(String(MAX_JOB_STATUS_LENGTH), default=DEFAULT_JOB_STATUS)
    job_priority = Column(Integer, default=DEFAULT_JOB_PRIORITY)
    entity_universal_id = Column(UUID(as_uuid=True), ForeignKey('entities.entity_universal_id', ondelete='CASCADE'))
    filing_universal_id = Column(UUID(as_uuid=True), ForeignKey('filings.filing_universal_id', ondelete='CASCADE'))
    job_parameters = Column(JSONB)
    job_result = Column(JSONB)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    retry_count = Column(Integer, default=DEFAULT_RETRY_COUNT)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_jobs_status_priority', 'job_status', 'job_priority'),
    )
    
    entity = relationship("Entity", back_populates="processing_jobs")
    filing = relationship("Filing", back_populates="processing_jobs")


__all__ = [
    'Base',
    'SystemConfig',
    'Market', 
    'Entity',
    'Filing',
    'Document',
    'ProcessingJob'
]