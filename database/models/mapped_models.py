# File: /map_pro/database/models/mapped_models.py

"""
Map Pro Mapped Database Models
==============================

SQLAlchemy models for the mapped database (map_pro_mapped).
Handles final mapped financial statements and mapping sessions.

Architecture: Maps to PostgreSQL mapped database schema.
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

MAX_SESSION_NAME_LENGTH = 255
MAX_SESSION_TYPE_LENGTH = 50
MAX_ALGORITHM_NAME_LENGTH = 100
MAX_ALGORITHM_VERSION_LENGTH = 50
DECIMAL_PRECISION_CONFIDENCE = 5
DECIMAL_SCALE_CONFIDENCE = 4
DEFAULT_CONFIDENCE_THRESHOLD = 0.85
DEFAULT_ENTITY_COUNT = 0
DEFAULT_FACT_COUNT = 0
MAX_SESSION_STATUS_LENGTH = 20
DEFAULT_SESSION_STATUS = 'running'
MAX_STATEMENT_TYPE_LENGTH = 50
MAX_CURRENCY_CODE_LENGTH = 3
MAX_MAPPING_STATUS_LENGTH = 20
DEFAULT_MAPPING_STATUS = 'pending'
MAX_MAPPED_BY_LENGTH = 100
MAX_TARGET_CONCEPT_LENGTH = 255
MAX_MAPPING_STRATEGY_LENGTH = 50
MAX_FACT_DATA_TYPE_LENGTH = 50
MAX_UNIT_OF_MEASURE_LENGTH = 50
MAX_METRIC_TYPE_LENGTH = 50
MAX_METRIC_NAME_LENGTH = 100
DECIMAL_PRECISION_METRIC_VALUE = 10
DECIMAL_SCALE_METRIC_VALUE = 4
MAX_THRESHOLD_STATUS_LENGTH = 20
MAX_QUALITY_ASSESSMENT_LENGTH = 20


class MappingSession(Base):
    """Mapping session coordination for batch operations."""
    __tablename__ = 'mapping_sessions'
    
    mapping_session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    session_name = Column(String(MAX_SESSION_NAME_LENGTH))
    session_type = Column(String(MAX_SESSION_TYPE_LENGTH))
    mapping_algorithm = Column(String(MAX_ALGORITHM_NAME_LENGTH))
    algorithm_version = Column(String(MAX_ALGORITHM_VERSION_LENGTH))
    taxonomies_used = Column(JSONB)
    confidence_threshold = Column(DECIMAL(DECIMAL_PRECISION_CONFIDENCE, DECIMAL_SCALE_CONFIDENCE), default=DEFAULT_CONFIDENCE_THRESHOLD)
    entities_planned = Column(Integer, default=DEFAULT_ENTITY_COUNT)
    entities_completed = Column(Integer, default=DEFAULT_ENTITY_COUNT)
    facts_successfully_mapped = Column(Integer, default=DEFAULT_FACT_COUNT)
    facts_failed_mapping = Column(Integer, default=DEFAULT_FACT_COUNT)
    average_mapping_confidence = Column(DECIMAL(DECIMAL_PRECISION_CONFIDENCE, DECIMAL_SCALE_CONFIDENCE))
    session_status = Column(String(MAX_SESSION_STATUS_LENGTH), default=DEFAULT_SESSION_STATUS)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    mapped_statements = relationship("MappedStatement", back_populates="mapping_session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<MappingSession(id={self.mapping_session_id}, name={self.session_name}, status={self.session_status})>"


class MappedStatement(Base):
    """Final mapped financial statements."""
    __tablename__ = 'mapped_statements'
    
    statement_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    entity_universal_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    filing_universal_id = Column(UUID(as_uuid=True), nullable=False)
    parsed_document_id = Column(UUID(as_uuid=True), index=True)
    mapping_session_id = Column(UUID(as_uuid=True), ForeignKey('mapping_sessions.mapping_session_id'), index=True)
    statement_type = Column(String(MAX_STATEMENT_TYPE_LENGTH), nullable=False)
    reporting_period_start = Column(Date)
    reporting_period_end = Column(Date)
    reporting_currency = Column(String(MAX_CURRENCY_CODE_LENGTH))
    total_mapped_facts = Column(Integer, default=DEFAULT_FACT_COUNT)
    total_unmapped_facts = Column(Integer, default=DEFAULT_FACT_COUNT)
    mapping_confidence_score = Column(DECIMAL(DECIMAL_PRECISION_CONFIDENCE, DECIMAL_SCALE_CONFIDENCE))
    mapping_status = Column(String(MAX_MAPPING_STATUS_LENGTH), default=DEFAULT_MAPPING_STATUS)
    statement_json_path = Column(Text)
    mapped_at = Column(DateTime(timezone=True), server_default=func.now())
    mapped_by = Column(String(MAX_MAPPED_BY_LENGTH))
    
    mapping_session = relationship("MappingSession", back_populates="mapped_statements")
    mapped_facts = relationship("MappedFact", back_populates="statement", cascade="all, delete-orphan")
    quality_metrics = relationship("MappingQualityMetric", back_populates="statement", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_mapped_statements_entity', 'entity_universal_id'),
        Index('idx_mapped_statements_period', 'reporting_period_end'),
    )
    
    def __repr__(self):
        return f"<MappedStatement(type={self.statement_type}, period={self.reporting_period_end})>"


class MappedFact(Base):
    """Individual mapped facts within statements."""
    __tablename__ = 'mapped_facts'
    
    mapped_fact_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    statement_id = Column(UUID(as_uuid=True), ForeignKey('mapped_statements.statement_id', ondelete='CASCADE'), nullable=False, index=True)
    source_concept_qname = Column(Text)
    target_concept_name = Column(String(MAX_TARGET_CONCEPT_LENGTH), nullable=False)
    mapping_strategy = Column(String(MAX_MAPPING_STRATEGY_LENGTH))
    mapping_confidence = Column(DECIMAL(DECIMAL_PRECISION_CONFIDENCE, DECIMAL_SCALE_CONFIDENCE))
    fact_value = Column(Text)
    fact_data_type = Column(String(MAX_FACT_DATA_TYPE_LENGTH))
    period_start = Column(Date)
    period_end = Column(Date)
    period_instant = Column(Date)
    unit_of_measure = Column(String(MAX_UNIT_OF_MEASURE_LENGTH))
    decimals = Column(Integer)
    dimension_info = Column(JSONB)
    mapping_notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    statement = relationship("MappedStatement", back_populates="mapped_facts")
    
    __table_args__ = (
        Index('idx_mapped_facts_statement', 'statement_id'),
        Index('idx_mapped_facts_concept', 'target_concept_name'),
    )
    
    def __repr__(self):
        return f"<MappedFact(concept={self.target_concept_name}, value={self.fact_value})>"


class MappingQualityMetric(Base):
    """Quality metrics for mapped statements."""
    __tablename__ = 'mapping_quality_metrics'
    
    metric_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    statement_id = Column(UUID(as_uuid=True), ForeignKey('mapped_statements.statement_id', ondelete='CASCADE'), nullable=False, index=True)
    metric_type = Column(String(MAX_METRIC_TYPE_LENGTH), nullable=False)
    metric_name = Column(String(MAX_METRIC_NAME_LENGTH), nullable=False)
    metric_value = Column(DECIMAL(DECIMAL_PRECISION_METRIC_VALUE, DECIMAL_SCALE_METRIC_VALUE))
    threshold_status = Column(String(MAX_THRESHOLD_STATUS_LENGTH))
    quality_assessment = Column(String(MAX_QUALITY_ASSESSMENT_LENGTH))
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    statement = relationship("MappedStatement", back_populates="quality_metrics")
    
    __table_args__ = (
        Index('idx_quality_metrics_statement', 'statement_id'),
    )
    
    def __repr__(self):
        return f"<MappingQualityMetric(name={self.metric_name}, value={self.metric_value})>"