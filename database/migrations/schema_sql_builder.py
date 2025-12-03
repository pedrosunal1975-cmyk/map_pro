"""
Schema SQL Template Builder
============================

Builds SQL schema templates using constants for field definitions.

Save location: database/migrations/schema_sql_builder.py

Responsibilities:
- Generate common table templates
- Build index definitions
- Create constraint definitions
- Provide reusable SQL fragments

Design Pattern: Template Method Pattern
"""

from database.migrations import schema_constants as sc


class SchemaTemplate:
    """
    Provides template methods for common SQL schema patterns.
    
    All field sizes and defaults come from schema_constants to
    eliminate magic numbers and ensure consistency.
    """
    
    @staticmethod
    def system_config_table() -> str:
        """
        Generate system_config table SQL (used in all databases).
        
        Returns:
            SQL CREATE TABLE statement
        """
        return f"""
        CREATE TABLE IF NOT EXISTS system_config (
            config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            config_key {sc.SIZE_CONFIG_KEY} NOT NULL UNIQUE,
            config_value TEXT NOT NULL,
            config_type {sc.SIZE_CONFIG_TYPE} DEFAULT '{sc.DEFAULT_CONFIG_TYPE}',
            module_owner {sc.SIZE_MODULE_OWNER},
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """.replace(f"{sc.SIZE_CONFIG_KEY}", f"VARCHAR({sc.SIZE_CONFIG_KEY})") \
           .replace(f"{sc.SIZE_CONFIG_TYPE}", f"VARCHAR({sc.SIZE_CONFIG_TYPE})") \
           .replace(f"{sc.SIZE_MODULE_OWNER}", f"VARCHAR({sc.SIZE_MODULE_OWNER})")
    
    @staticmethod
    def decimal_field(precision: int, scale: int) -> str:
        """
        Format DECIMAL field definition.
        
        Args:
            precision: Total digits
            scale: Decimal places
            
        Returns:
            SQL DECIMAL type definition
        """
        return f"DECIMAL({precision},{scale})"
    
    @staticmethod
    def init_config_values(database_type: str) -> str:
        """
        Generate initial system_config INSERT statement.
        
        Args:
            database_type: Name of the database (core, parsed, library, mapped)
            
        Returns:
            SQL INSERT statement
        """
        values = [
            (
                'schema_version',
                sc.SCHEMA_VERSION,
                'string',
                sc.MODULE_OWNER_MIGRATION
            ),
            (
                'database_type',
                database_type,
                'string',
                sc.MODULE_OWNER_MIGRATION
            ),
            (
                'initialized_at',
                "NOW()::text",
                'timestamp',
                sc.MODULE_OWNER_MIGRATION
            )
        ]
        
        # Add market-specific config for core database
        if database_type == sc.DATABASE_NAME_CORE:
            values.append((
                'market_registry_mode',
                sc.DEFAULT_MARKET_REGISTRY_MODE,
                'string',
                sc.MODULE_OWNER_MARKET
            ))
        
        value_strings = []
        for key, value, value_type, owner in values:
            if value == "NOW()::text":
                value_strings.append(f"('{key}', {value}, '{value_type}', '{owner}')")
            else:
                value_strings.append(f"('{key}', '{value}', '{value_type}', '{owner}')")
        
        return f"""
        INSERT INTO system_config (config_key, config_value, config_type, module_owner) 
        VALUES 
            {', '.join(value_strings)}
        ON CONFLICT (config_key) DO NOTHING;
        """


__all__ = ['SchemaTemplate']