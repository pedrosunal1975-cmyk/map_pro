"""
Map Pro Schema Initializer - Market-Agnostic
============================================

Generates SQL schemas for Map Pro's four-database PostgreSQL architecture.
100% market-agnostic - NO hardcoded market data or SEC-specific fields.

Architecture: Pure SQL generation focused on schema definition.
All magic numbers extracted to schema_constants module.

Location: database/migrations/schema_initializer.py

Responsibilities:
- Database-specific schema SQL generation
- Initial system configuration seeding
- Schema consistency across databases

Does NOT handle:
- SQL execution (migration_executor handles this)
- Schema validation (schema_validator handles this)
- Migration coordination (migration_manager handles this)
- Hardcoded market data (markets register themselves)

Dependencies:
- database.migrations.schema_constants (all sizing constants)
- database.migrations.schema_sql_builder (SQL templates)
- core.system_logger (logging)
"""

from typing import Optional
from core.system_logger import get_logger
from database.migrations import schema_constants as sc
from database.migrations.schema_sql_builder import SchemaTemplate


logger = get_logger(__name__, 'core')


class SchemaInitializer:
    """
    Generates initialization SQL for Map Pro databases.
    
    All field sizes, precision values, and defaults are sourced from
    schema_constants to eliminate magic numbers and ensure consistency.
    
    Attributes:
        template: SchemaTemplate instance for common SQL patterns
    """
    
    def __init__(self):
        """Initialize schema initializer with SQL template builder."""
        self.template = SchemaTemplate()
        logger.info("Schema initializer initialized")
    
    def get_init_sql(self, db_name: str) -> Optional[str]:
        """
        Get initialization SQL for specific database.
        
        Args:
            db_name: Name of database (core, parsed, library, mapped)
            
        Returns:
            SQL initialization script or None if database unknown
        """
        init_sqls = {
            sc.DATABASE_NAME_CORE: self.get_core_init_sql(),
            sc.DATABASE_NAME_PARSED: self.get_parsed_init_sql(),
            sc.DATABASE_NAME_LIBRARY: self.get_library_init_sql(),
            sc.DATABASE_NAME_MAPPED: self.get_mapped_init_sql()
        }
        return init_sqls.get(db_name)
    
    def get_core_init_sql(self) -> str:
        """
        Get core database initialization SQL (100% market-agnostic).
        
        Returns:
            SQL script for core database schema
        """
        return f"""
        {self.template.system_config_table()}
        
        CREATE TABLE IF NOT EXISTS markets (
            market_id VARCHAR({sc.SIZE_MARKET_ID}) PRIMARY KEY,
            market_name VARCHAR({sc.SIZE_MARKET_NAME}) NOT NULL,
            market_country VARCHAR({sc.SIZE_MARKET_COUNTRY}) NOT NULL,
            api_base_url TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            rate_limit_per_minute INTEGER DEFAULT {sc.DEFAULT_RATE_LIMIT_PER_MINUTE},
            user_agent_required BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE TABLE IF NOT EXISTS entities (
            entity_universal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            market_type VARCHAR({sc.SIZE_MARKET_ID}) NOT NULL REFERENCES markets(market_id),
            market_entity_id VARCHAR({sc.SIZE_MARKET_ENTITY_ID}) NOT NULL,
            primary_name VARCHAR({sc.SIZE_PRIMARY_NAME}) NOT NULL,
            entity_status VARCHAR({sc.SIZE_ENTITY_STATUS}) DEFAULT '{sc.DEFAULT_STATUS_ACTIVE}',
            data_directory_path TEXT,
            last_filing_date DATE,
            total_filings_count INTEGER DEFAULT {sc.DEFAULT_COUNTER_VALUE},
            identifiers JSONB,
            search_history JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            
            CONSTRAINT entities_market_entity_unique UNIQUE (market_type, market_entity_id),
            CONSTRAINT entities_filing_count_positive CHECK (total_filings_count >= {sc.MIN_FILING_COUNT})
        );
        
        CREATE TABLE IF NOT EXISTS filings (
            filing_universal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            entity_universal_id UUID NOT NULL REFERENCES entities(entity_universal_id) ON DELETE CASCADE,
            market_filing_id VARCHAR({sc.SIZE_MARKET_FILING_ID}) NOT NULL,
            filing_type VARCHAR({sc.SIZE_FILING_TYPE}) NOT NULL,
            filing_date DATE NOT NULL,
            period_start_date DATE,
            period_end_date DATE,
            filing_title TEXT,
            download_status VARCHAR({sc.SIZE_FILING_STATUS}) DEFAULT '{sc.DEFAULT_STATUS_PENDING}',
            extraction_status VARCHAR({sc.SIZE_FILING_STATUS}) DEFAULT '{sc.DEFAULT_STATUS_PENDING}',
            filing_directory_path TEXT,
            original_url TEXT,
            download_size_mb {self.template.decimal_field(sc.PRECISION_FILE_SIZE_MB, sc.SCALE_FILE_SIZE_MB)},
            download_completed_at TIMESTAMP WITH TIME ZONE,
            extraction_completed_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE TABLE IF NOT EXISTS documents (
            document_universal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            filing_universal_id UUID NOT NULL REFERENCES filings(filing_universal_id) ON DELETE CASCADE,
            document_name VARCHAR({sc.SIZE_DOCUMENT_NAME}) NOT NULL,
            document_type VARCHAR({sc.SIZE_DOCUMENT_TYPE}),
            file_size_bytes BIGINT,
            file_hash_sha256 VARCHAR({sc.SIZE_FILE_HASH_SHA256}),
            download_path TEXT,
            extraction_path TEXT,
            is_xbrl_instance BOOLEAN DEFAULT FALSE,
            parsing_eligible BOOLEAN DEFAULT FALSE,
            parsed_status VARCHAR({sc.SIZE_FILING_STATUS}) DEFAULT '{sc.DEFAULT_STATUS_PENDING}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE TABLE IF NOT EXISTS processing_jobs (
            job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            job_type VARCHAR({sc.SIZE_JOB_TYPE}) NOT NULL,
            job_status VARCHAR({sc.SIZE_JOB_STATUS}) DEFAULT '{sc.DEFAULT_STATUS_QUEUED}',
            job_priority INTEGER DEFAULT {sc.DEFAULT_JOB_PRIORITY},
            entity_universal_id UUID REFERENCES entities(entity_universal_id) ON DELETE CASCADE,
            filing_universal_id UUID REFERENCES filings(filing_universal_id) ON DELETE CASCADE,
            job_parameters JSONB,
            result_data JSONB,
            started_at TIMESTAMP WITH TIME ZONE,
            completed_at TIMESTAMP WITH TIME ZONE,
            error_message TEXT,
            retry_count INTEGER DEFAULT {sc.DEFAULT_RETRY_COUNT},
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_entities_market_type ON entities(market_type);
        CREATE INDEX IF NOT EXISTS idx_entities_status ON entities(entity_status);
        CREATE INDEX IF NOT EXISTS idx_filings_entity ON filings(entity_universal_id);
        CREATE INDEX IF NOT EXISTS idx_filings_date ON filings(filing_date DESC);
        CREATE INDEX IF NOT EXISTS idx_filings_market_filing_id ON filings(market_filing_id);
        CREATE INDEX IF NOT EXISTS idx_documents_filing ON documents(filing_universal_id);
        CREATE INDEX IF NOT EXISTS idx_documents_xbrl ON documents(is_xbrl_instance);
        CREATE INDEX IF NOT EXISTS idx_jobs_status_priority ON processing_jobs(job_status, job_priority);
        CREATE INDEX IF NOT EXISTS idx_jobs_entity ON processing_jobs(entity_universal_id);
        CREATE INDEX IF NOT EXISTS idx_jobs_filing ON processing_jobs(filing_universal_id);
        
        {self.template.init_config_values(sc.DATABASE_NAME_CORE)}
        """
    
    def get_parsed_init_sql(self) -> str:
        """
        Get parsed database initialization SQL (100% market-agnostic).
        
        Returns:
            SQL script for parsed database schema
        """
        return f"""
        {self.template.system_config_table()}
        
        CREATE TABLE IF NOT EXISTS parsing_sessions (
            session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_name VARCHAR({sc.SIZE_SESSION_NAME}),
            session_type VARCHAR({sc.SIZE_SESSION_TYPE}),
            market_type VARCHAR({sc.SIZE_MARKET_ID}),
            parser_engine VARCHAR({sc.SIZE_PARSER_ENGINE}) DEFAULT '{sc.DEFAULT_PARSER_ENGINE}',
            parser_version VARCHAR({sc.SIZE_PARSER_VERSION}),
            documents_to_parse INTEGER DEFAULT {sc.DEFAULT_COUNTER_VALUE},
            documents_completed INTEGER DEFAULT {sc.DEFAULT_COUNTER_VALUE},
            total_facts_extracted INTEGER DEFAULT {sc.DEFAULT_COUNTER_VALUE},
            session_status VARCHAR({sc.SIZE_JOB_STATUS}) DEFAULT '{sc.DEFAULT_STATUS_RUNNING}',
            started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            completed_at TIMESTAMP WITH TIME ZONE,
            session_config JSONB,
            performance_metrics JSONB
        );
        
        CREATE TABLE IF NOT EXISTS parsed_documents (
            parsed_document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            entity_universal_id UUID NOT NULL,
            filing_universal_id UUID NOT NULL,
            parsing_session_id UUID REFERENCES parsing_sessions(session_id),
            document_name VARCHAR({sc.SIZE_DOCUMENT_NAME}),
            source_file_path TEXT,
            facts_json_path TEXT,
            parsing_engine VARCHAR({sc.SIZE_PARSER_ENGINE}),
            facts_extracted INTEGER DEFAULT {sc.DEFAULT_COUNTER_VALUE},
            contexts_extracted INTEGER DEFAULT {sc.DEFAULT_COUNTER_VALUE},
            units_extracted INTEGER DEFAULT {sc.DEFAULT_COUNTER_VALUE},
            parsing_duration_seconds {self.template.decimal_field(sc.PRECISION_DURATION_SECONDS, sc.SCALE_DURATION_SECONDS)},
            parsing_warnings_count INTEGER DEFAULT {sc.DEFAULT_COUNTER_VALUE},
            parsing_errors_count INTEGER DEFAULT {sc.DEFAULT_COUNTER_VALUE},
            validation_status VARCHAR({sc.SIZE_FILING_STATUS}) DEFAULT '{sc.DEFAULT_STATUS_PENDING}',
            facts_file_size_mb {self.template.decimal_field(sc.PRECISION_FILE_SIZE_MB, sc.SCALE_FILE_SIZE_MB)},
            facts_file_hash VARCHAR({sc.SIZE_FILE_HASH_SHA256}),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_parsed_docs_entity ON parsed_documents(entity_universal_id);
        CREATE INDEX IF NOT EXISTS idx_parsed_docs_filing ON parsed_documents(filing_universal_id);
        CREATE INDEX IF NOT EXISTS idx_parsed_docs_session ON parsed_documents(parsing_session_id);
        CREATE INDEX IF NOT EXISTS idx_parsing_sessions_market ON parsing_sessions(market_type);
        
        {self.template.init_config_values(sc.DATABASE_NAME_PARSED)}
        """

    def get_library_init_sql(self) -> str:
        """
        Get library database initialization SQL (100% market-agnostic).
        
        Returns:
            SQL script for library database schema
        """
        return f"""
        {self.template.system_config_table()}
        
        CREATE TABLE IF NOT EXISTS taxonomy_libraries (
            library_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            taxonomy_name VARCHAR({sc.SIZE_TAXONOMY_NAME}) NOT NULL,
            taxonomy_version VARCHAR({sc.SIZE_PARSER_VERSION}) NOT NULL,
            taxonomy_authority VARCHAR({sc.SIZE_TAXONOMY_AUTHORITY}) NOT NULL,
            base_namespace TEXT NOT NULL,
            library_status VARCHAR({sc.SIZE_FILING_STATUS}) DEFAULT '{sc.DEFAULT_STATUS_ACTIVE}',
            download_source_url TEXT,
            library_directory_path TEXT,
            total_concepts INTEGER DEFAULT {sc.DEFAULT_COUNTER_VALUE},
            total_files INTEGER DEFAULT {sc.DEFAULT_COUNTER_VALUE},
            library_size_mb {self.template.decimal_field(sc.PRECISION_FILE_SIZE_MB, sc.SCALE_FILE_SIZE_MB)},
            download_date DATE,
            last_validated_at TIMESTAMP WITH TIME ZONE,
            validation_status VARCHAR({sc.SIZE_FILING_STATUS}) DEFAULT '{sc.DEFAULT_STATUS_PENDING}',
            is_required_by_markets JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            
            CONSTRAINT taxonomy_name_version_unique UNIQUE (taxonomy_name, taxonomy_version)
        );
        
        CREATE TABLE IF NOT EXISTS taxonomy_concepts (
            concept_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            library_id UUID NOT NULL REFERENCES taxonomy_libraries(library_id) ON DELETE CASCADE,
            concept_qname TEXT NOT NULL,
            concept_local_name VARCHAR({sc.SIZE_CONCEPT_LOCAL_NAME}) NOT NULL,
            concept_namespace TEXT NOT NULL,
            concept_type VARCHAR({sc.SIZE_CONCEPT_TYPE}),
            period_type VARCHAR({sc.SIZE_PERIOD_TYPE}),
            balance_type VARCHAR({sc.SIZE_BALANCE_TYPE}),
            abstract_concept BOOLEAN DEFAULT FALSE,
            concept_label TEXT,
            concept_definition TEXT,
            concept_documentation TEXT,
            data_type VARCHAR({sc.SIZE_DATA_TYPE}),
            usage_frequency INTEGER DEFAULT {sc.DEFAULT_COUNTER_VALUE},
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE TABLE IF NOT EXISTS taxonomy_files (
            file_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            library_id UUID NOT NULL REFERENCES taxonomy_libraries(library_id) ON DELETE CASCADE,
            file_name VARCHAR({sc.SIZE_FILE_NAME}) NOT NULL,
            file_type VARCHAR({sc.SIZE_FILE_TYPE}) NOT NULL,
            file_path TEXT NOT NULL,
            file_size_bytes BIGINT,
            file_hash_sha256 VARCHAR({sc.SIZE_FILE_HASH_SHA256}),
            concepts_defined INTEGER DEFAULT {sc.DEFAULT_COUNTER_VALUE},
            file_status VARCHAR({sc.SIZE_FILING_STATUS}) DEFAULT 'healthy',
            last_validated_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE TABLE IF NOT EXISTS library_health_checks (
            check_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            library_id UUID NOT NULL REFERENCES taxonomy_libraries(library_id) ON DELETE CASCADE,
            check_type VARCHAR({sc.SIZE_CHECK_TYPE}) NOT NULL,
            check_status VARCHAR({sc.SIZE_FILING_STATUS}) DEFAULT '{sc.DEFAULT_STATUS_PENDING}',
            issues_found INTEGER DEFAULT {sc.DEFAULT_COUNTER_VALUE},
            critical_issues INTEGER DEFAULT {sc.DEFAULT_COUNTER_VALUE},
            check_results JSONB,
            checked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            check_duration_seconds {self.template.decimal_field(sc.PRECISION_SHORT_DURATION, sc.SCALE_SHORT_DURATION)}
        );
        
        CREATE INDEX IF NOT EXISTS idx_concepts_qname ON taxonomy_concepts(concept_qname);
        CREATE INDEX IF NOT EXISTS idx_concepts_library ON taxonomy_concepts(library_id);
        CREATE INDEX IF NOT EXISTS idx_concepts_local_name ON taxonomy_concepts(concept_local_name);
        CREATE INDEX IF NOT EXISTS idx_concepts_namespace ON taxonomy_concepts(concept_namespace);
        CREATE INDEX IF NOT EXISTS idx_files_library ON taxonomy_files(library_id);
        CREATE INDEX IF NOT EXISTS idx_files_type ON taxonomy_files(file_type);
        CREATE INDEX IF NOT EXISTS idx_health_checks_library ON library_health_checks(library_id);
        CREATE INDEX IF NOT EXISTS idx_libraries_status ON taxonomy_libraries(library_status);
        CREATE INDEX IF NOT EXISTS idx_libraries_authority ON taxonomy_libraries(taxonomy_authority);
        
        {self.template.init_config_values(sc.DATABASE_NAME_LIBRARY)}
        """

    def get_mapped_init_sql(self) -> str:
        """
        Get mapped database initialization SQL (100% market-agnostic).
        
        Returns:
            SQL script for mapped database schema
        """
        return f"""
        {self.template.system_config_table()}
        
        CREATE TABLE IF NOT EXISTS mapping_sessions (
            mapping_session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_name VARCHAR({sc.SIZE_SESSION_NAME}),
            session_type VARCHAR({sc.SIZE_SESSION_TYPE}),
            mapping_algorithm VARCHAR({sc.SIZE_MAPPING_ALGORITHM}),
            algorithm_version VARCHAR({sc.SIZE_PARSER_VERSION}),
            taxonomies_used JSONB,
            confidence_threshold {self.template.decimal_field(sc.PRECISION_CONFIDENCE, sc.SCALE_CONFIDENCE)} DEFAULT {sc.DEFAULT_CONFIDENCE_THRESHOLD},
            entities_planned INTEGER DEFAULT {sc.DEFAULT_COUNTER_VALUE},
            entities_completed INTEGER DEFAULT {sc.DEFAULT_COUNTER_VALUE},
            facts_successfully_mapped INTEGER DEFAULT {sc.DEFAULT_COUNTER_VALUE},
            facts_failed_mapping INTEGER DEFAULT {sc.DEFAULT_COUNTER_VALUE},
            average_mapping_confidence {self.template.decimal_field(sc.PRECISION_CONFIDENCE, sc.SCALE_CONFIDENCE)},
            session_status VARCHAR({sc.SIZE_JOB_STATUS}) DEFAULT '{sc.DEFAULT_STATUS_RUNNING}',
            started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            completed_at TIMESTAMP WITH TIME ZONE
        );
        
        CREATE TABLE IF NOT EXISTS mapped_statements (
            statement_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            entity_universal_id UUID NOT NULL,
            filing_universal_id UUID NOT NULL,
            mapping_session_id UUID REFERENCES mapping_sessions(mapping_session_id),
            statement_type VARCHAR({sc.SIZE_FILING_TYPE}) NOT NULL,
            reporting_period_end DATE,
            reporting_currency VARCHAR({sc.SIZE_CURRENCY_CODE}),
            total_mapped_facts INTEGER DEFAULT {sc.DEFAULT_COUNTER_VALUE},
            total_unmapped_facts INTEGER DEFAULT {sc.DEFAULT_COUNTER_VALUE},
            mapping_confidence_score {self.template.decimal_field(sc.PRECISION_CONFIDENCE, sc.SCALE_CONFIDENCE)},
            mapping_status VARCHAR({sc.SIZE_FILING_STATUS}) DEFAULT '{sc.DEFAULT_STATUS_PENDING}',
            statement_json_path TEXT,
            mapped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            mapped_by VARCHAR({sc.SIZE_MAPPED_BY})
        );
        
        CREATE TABLE IF NOT EXISTS mapped_facts (
            mapped_fact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            statement_id UUID NOT NULL REFERENCES mapped_statements(statement_id) ON DELETE CASCADE,
            source_concept_qname TEXT,
            target_concept_name VARCHAR({sc.SIZE_TARGET_CONCEPT_NAME}) NOT NULL,
            mapping_strategy VARCHAR({sc.SIZE_MAPPING_STRATEGY}),
            mapping_confidence {self.template.decimal_field(sc.PRECISION_CONFIDENCE, sc.SCALE_CONFIDENCE)},
            fact_value TEXT,
            fact_data_type VARCHAR({sc.SIZE_DATA_TYPE}),
            period_start DATE,
            period_end DATE,
            period_instant DATE,
            unit_of_measure VARCHAR({sc.SIZE_UNIT_OF_MEASURE}),
            decimals INTEGER,
            dimension_info JSONB,
            mapping_notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE TABLE IF NOT EXISTS mapping_quality_metrics (
            metric_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            statement_id UUID NOT NULL REFERENCES mapped_statements(statement_id) ON DELETE CASCADE,
            metric_type VARCHAR({sc.SIZE_METRIC_TYPE}) NOT NULL,
            metric_name VARCHAR({sc.SIZE_METRIC_NAME}) NOT NULL,
            metric_value {self.template.decimal_field(sc.PRECISION_QUALITY_METRIC, sc.SCALE_QUALITY_METRIC)},
            threshold_status VARCHAR({sc.SIZE_FILING_STATUS}),
            quality_assessment VARCHAR({sc.SIZE_FILING_STATUS}),
            calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_mapped_statements_entity ON mapped_statements(entity_universal_id);
        CREATE INDEX IF NOT EXISTS idx_mapped_statements_period ON mapped_statements(reporting_period_end);
        CREATE INDEX IF NOT EXISTS idx_mapped_statements_session ON mapped_statements(mapping_session_id);
        CREATE INDEX IF NOT EXISTS idx_mapped_statements_type ON mapped_statements(statement_type);
        CREATE INDEX IF NOT EXISTS idx_mapped_facts_statement ON mapped_facts(statement_id);
        CREATE INDEX IF NOT EXISTS idx_mapped_facts_concept ON mapped_facts(target_concept_name);
        CREATE INDEX IF NOT EXISTS idx_quality_metrics_statement ON mapping_quality_metrics(statement_id);
        CREATE INDEX IF NOT EXISTS idx_mapping_sessions_status ON mapping_sessions(session_status);
        
        {self.template.init_config_values(sc.DATABASE_NAME_MAPPED)}
        """


__all__ = ['SchemaInitializer']