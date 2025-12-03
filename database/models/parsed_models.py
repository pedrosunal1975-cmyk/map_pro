# File: /map_pro/database/models/parsed_models.py

"""
Map Pro Parsed Database Models
==============================

SQLAlchemy models for the parsed database (map_pro_parsed).
Handles parsed XBRL documents, facts, and parsing sessions.

Architecture: Maps to PostgreSQL parsed database schema.
"""

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date, Text,
    DECIMAL, BigInteger, UUID, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
import uuid as uuid_module

from .core_models import Base

DEFAULT_PARSER_ENGINE = 'arelle'
DEFAULT_SESSION_STATUS = 'running'
DEFAULT_VALIDATION_STATUS = 'pending'
DEFAULT_COUNT = 0

MAX_SESSION_NAME_LENGTH = 255
MAX_SESSION_TYPE_LENGTH = 50
MAX_MARKET_TYPE_LENGTH = 10
MAX_PARSER_LENGTH = 50
MAX_STATUS_LENGTH = 20
MAX_DOCUMENT_NAME_LENGTH = 255
MAX_LOCAL_NAME_LENGTH = 255
MAX_SHA256_LENGTH = 64
MAX_METRIC_TYPE_LENGTH = 50
MAX_METRIC_NAME_LENGTH = 100

DURATION_PRECISION = 10
DURATION_SCALE = 3
SIZE_PRECISION = 10
SIZE_SCALE = 2
METRIC_PRECISION = 10
METRIC_SCALE = 4


class ParsingSession(Base):
    """Parsing session management for batch operations."""
    __tablename__ = 'parsing_sessions'
    
    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    session_name = Column(String(MAX_SESSION_NAME_LENGTH))
    session_type = Column(String(MAX_SESSION_TYPE_LENGTH))
    market_type = Column(String(MAX_MARKET_TYPE_LENGTH))
    parser_engine = Column(String(MAX_PARSER_LENGTH), default=DEFAULT_PARSER_ENGINE)
    parser_version = Column(String(MAX_PARSER_LENGTH))
    documents_to_parse = Column(Integer, default=DEFAULT_COUNT)
    documents_completed = Column(Integer, default=DEFAULT_COUNT)
    total_facts_extracted = Column(Integer, default=DEFAULT_COUNT)
    session_status = Column(String(MAX_STATUS_LENGTH), default=DEFAULT_SESSION_STATUS)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    session_config = Column(JSONB)
    performance_metrics = Column(JSONB)
    
    parsed_documents = relationship("ParsedDocument", back_populates="parsing_session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ParsingSession(id={self.session_id}, name={self.session_name}, status={self.session_status})>"


class ParsedDocument(Base):
    """Registry of parsed XBRL documents."""
    __tablename__ = 'parsed_documents'
    
    parsed_document_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    entity_universal_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    filing_universal_id = Column(UUID(as_uuid=True), nullable=False)
    parsing_session_id = Column(UUID(as_uuid=True), ForeignKey('parsing_sessions.session_id'), index=True)
    document_name = Column(String(MAX_DOCUMENT_NAME_LENGTH))
    source_file_path = Column(Text)
    facts_json_path = Column(Text)
    parsing_engine = Column(String(MAX_PARSER_LENGTH))
    facts_extracted = Column(Integer, default=DEFAULT_COUNT)
    contexts_extracted = Column(Integer, default=DEFAULT_COUNT)
    units_extracted = Column(Integer, default=DEFAULT_COUNT)
    parsing_duration_seconds = Column(DECIMAL(DURATION_PRECISION, DURATION_SCALE))
    parsing_warnings_count = Column(Integer, default=DEFAULT_COUNT)
    parsing_errors_count = Column(Integer, default=DEFAULT_COUNT)
    validation_status = Column(String(MAX_STATUS_LENGTH), default=DEFAULT_VALIDATION_STATUS)
    facts_file_size_mb = Column(DECIMAL(SIZE_PRECISION, SIZE_SCALE))
    facts_file_hash = Column(String(MAX_SHA256_LENGTH))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    parsing_session = relationship("ParsingSession", back_populates="parsed_documents")
    facts_summary = relationship("RawFactsSummary", back_populates="parsed_document", cascade="all, delete-orphan")
    quality_metrics = relationship("ParsingQualityMetric", back_populates="parsed_document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ParsedDocument(id={self.parsed_document_id}, facts={self.facts_extracted})>"


class RawFactsSummary(Base):
    """High-level summary of concepts found in parsed facts."""
    __tablename__ = 'raw_facts_summary'
    
    summary_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    parsed_document_id = Column(UUID(as_uuid=True), ForeignKey('parsed_documents.parsed_document_id', ondelete='CASCADE'), nullable=False)
    concept_namespace = Column(Text, nullable=False)
    concept_local_name = Column(String(MAX_LOCAL_NAME_LENGTH), nullable=False)
    concept_qname = Column(Text, nullable=False, index=True)
    fact_count = Column(Integer, nullable=False)
    has_numeric_values = Column(Boolean, default=False)
    has_text_values = Column(Boolean, default=False)
    date_ranges = Column(JSONB)
    sample_values = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    parsed_document = relationship("ParsedDocument", back_populates="facts_summary")
    
    __table_args__ = (
        Index('idx_facts_summary_concept', 'concept_qname'),
    )
    
    def __repr__(self):
        return f"<RawFactsSummary(concept={self.concept_local_name}, count={self.fact_count})>"


class ParsingQualityMetric(Base):
    """Quality metrics for parsed data."""
    __tablename__ = 'parsing_quality_metrics'
    
    metric_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    parsed_document_id = Column(UUID(as_uuid=True), ForeignKey('parsed_documents.parsed_document_id', ondelete='CASCADE'), nullable=False, index=True)
    metric_type = Column(String(MAX_METRIC_TYPE_LENGTH), nullable=False)
    metric_name = Column(String(MAX_METRIC_NAME_LENGTH), nullable=False)
    metric_value = Column(DECIMAL(METRIC_PRECISION, METRIC_SCALE))
    threshold_status = Column(String(MAX_STATUS_LENGTH))
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    parsed_document = relationship("ParsedDocument", back_populates="quality_metrics")
    
    __table_args__ = (
        Index('idx_quality_metrics_doc', 'parsed_document_id'),
    )
    
    def __repr__(self):
        return f"<ParsingQualityMetric(name={self.metric_name}, value={self.metric_value})>"