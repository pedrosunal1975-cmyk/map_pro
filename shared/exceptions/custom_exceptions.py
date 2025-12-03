# File: shared/exceptions/custom_exceptions.py
"""
Map Pro Custom Exceptions
=========================

Custom exception classes for the Map Pro system.
Provides specialized exception types for different system components.
"""


class MapProError(Exception):
    """Base exception class for all Map Pro errors."""
    pass


class SystemError(MapProError):
    """Exception raised for system-level errors."""
    pass


class ComponentError(MapProError):
    """Exception raised for component-related errors."""
    pass


class ConfigurationError(MapProError):
    """Exception raised for configuration-related errors."""
    pass


class ValidationError(MapProError):
    """Exception raised for validation failures."""
    pass


class ComplianceViolationError(MapProError):
    """Exception raised for compliance violations."""
    pass


class PartitionViolationError(ComplianceViolationError):
    """Exception raised when data/program partition rules are violated."""
    pass


class DatabaseError(MapProError):
    """Exception raised for database-related errors."""
    pass


class EngineError(MapProError):
    """Exception raised for engine-related errors."""
    pass


class CriticalEngineError(EngineError):
    """Exception raised for critical engine errors that may require shutdown."""
    pass


class JobProcessingError(EngineError):
    """Exception raised during job processing operations."""
    pass


class StatusReportingError(EngineError):
    """Exception raised during status reporting operations."""
    pass


class SearchError(MapProError):
    """Exception raised during entity search operations."""
    pass


class DownloadError(MapProError):
    """Exception raised during file download operations."""
    pass


class ExtractionError(MapProError):
    """Exception raised during file extraction operations."""
    pass


class ParsingError(MapProError):
    """Exception raised during XBRL parsing operations."""
    pass


class MappingError(MapProError):
    """Exception raised during fact mapping operations."""
    pass


class TaxonomyError(MapProError):
    """Exception raised for taxonomy-related errors."""
    pass


class LibraryError(MapProError):
    """Exception raised for library-related errors."""
    pass


class MarketError(MapProError):
    """Exception raised for market-specific errors."""
    pass


class IntegrationError(MapProError):
    """Exception raised for integration-related errors."""
    pass


class AlertError(MapProError):
    """Exception raised for alert system errors."""
    pass


class MonitoringError(MapProError):
    """Exception raised for monitoring system errors."""
    pass


class NetworkError(MapProError):
    """Exception raised for network-related errors."""
    pass


class TimeoutError(MapProError):
    """Exception raised when operations exceed time limits."""
    pass


class FileSystemError(MapProError):
    """Exception raised for file system operations errors."""
    pass


class DataIntegrityError(MapProError):
    """Exception raised for data integrity violations."""
    pass


class AuthenticationError(MapProError):
    """Exception raised for authentication failures."""
    pass