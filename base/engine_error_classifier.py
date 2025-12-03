# File: /map_pro/engines/base/engine_error_classifier.py

"""
Map Pro Engine Error Classifier
================================

Classifies engine processing errors into system errors vs data quality issues.
Extends the base error classification system with engine-specific patterns.

This helps distinguish between:
- System errors: Infrastructure problems requiring engineering attention
- Data errors: Data quality issues that are expected in real-world data

Architecture: Specialized component for engine-level error classification.
"""

from enum import Enum
from typing import Optional, Dict, Any

from core.system_logger import get_logger

logger = get_logger(__name__, 'engine')


class EngineErrorType(Enum):
    """Enumeration of engine error types."""
    SYSTEM_ERROR = "system_error"
    DATA_ERROR = "data_error"
    DATABASE_CONSTRAINT = "database_constraint"
    DATABASE_CONNECTION = "database_connection"
    CODE_BUG = "code_bug"
    DEPENDENCY_MISSING = "dependency_missing"
    FILE_SYSTEM = "file_system"
    MALFORMED_XBRL = "malformed_xbrl"
    XBRL_VALIDATION = "xbrl_validation"
    XBRL_STRUCTURE = "xbrl_structure"
    DATA_QUALITY = "data_quality"
    UNKNOWN = "unknown"


SYSTEM_ERROR_PATTERNS = {
    'duplicate key': EngineErrorType.DATABASE_CONSTRAINT,
    'foreign key': EngineErrorType.DATABASE_CONSTRAINT,
    'uniqueviolation': EngineErrorType.DATABASE_CONSTRAINT,
    'integrityerror': EngineErrorType.DATABASE_CONSTRAINT,
    'unique constraint': EngineErrorType.DATABASE_CONSTRAINT,
    'violates foreign key': EngineErrorType.DATABASE_CONSTRAINT,
    'no attribute': EngineErrorType.CODE_BUG,
    'nonetype': EngineErrorType.CODE_BUG,
    'unsupported operand': EngineErrorType.CODE_BUG,
    'attributeerror': EngineErrorType.CODE_BUG,
    'typeerror': EngineErrorType.CODE_BUG,
    'indexerror': EngineErrorType.CODE_BUG,
    'keyerror': EngineErrorType.CODE_BUG,
    'operationalerror': EngineErrorType.DATABASE_CONNECTION,
    'connection refused': EngineErrorType.DATABASE_CONNECTION,
    'connection to server': EngineErrorType.DATABASE_CONNECTION,
    'could not connect': EngineErrorType.DATABASE_CONNECTION,
    'connection timeout': EngineErrorType.DATABASE_CONNECTION,
    'module not found': EngineErrorType.DEPENDENCY_MISSING,
    'import error': EngineErrorType.DEPENDENCY_MISSING,
    'no module named': EngineErrorType.DEPENDENCY_MISSING,
    'no such file': EngineErrorType.FILE_SYSTEM,
    'permission denied': EngineErrorType.FILE_SYSTEM,
    'file not found': EngineErrorType.FILE_SYSTEM,
    'directory not found': EngineErrorType.FILE_SYSTEM,
}

DATA_ERROR_PATTERNS = {
    'xml parse': EngineErrorType.MALFORMED_XBRL,
    'xmlsyntaxerror': EngineErrorType.MALFORMED_XBRL,
    'xml syntax': EngineErrorType.MALFORMED_XBRL,
    'malformed xml': EngineErrorType.MALFORMED_XBRL,
    'schema validation': EngineErrorType.XBRL_VALIDATION,
    'xbrl validation': EngineErrorType.XBRL_VALIDATION,
    'taxonomy error': EngineErrorType.XBRL_VALIDATION,
    'fact extraction failed': EngineErrorType.XBRL_STRUCTURE,
    'context not found': EngineErrorType.XBRL_STRUCTURE,
    'unit not found': EngineErrorType.XBRL_STRUCTURE,
    'missing context': EngineErrorType.XBRL_STRUCTURE,
    'invalid date': EngineErrorType.DATA_QUALITY,
    'missing required': EngineErrorType.DATA_QUALITY,
    'malformed': EngineErrorType.DATA_QUALITY,
    'invalid format': EngineErrorType.DATA_QUALITY,
    'data validation failed': EngineErrorType.DATA_QUALITY,
}


class EngineErrorClassifier:
    """
    Classifies engine processing errors into system vs data quality issues.
    
    Responsibilities:
    - Classify exceptions into system errors or data errors
    - Determine error severity and required action
    - Provide detailed error categorization
    - Generate error reports with classification
    
    Does NOT handle:
    - Error recovery logic (recovery_manager handles this)
    - Error tracking (error_tracker handles this)
    - Alert generation (error_handler handles this)
    """
    
    def __init__(self):
        """Initialize engine error classifier."""
        logger.debug("Engine error classifier initialized")
    
    def classify_error(
        self, 
        exception: Exception, 
        error_message: Optional[str] = None
    ) -> EngineErrorType:
        """
        Classify error as system error or data quality issue.
        
        Args:
            exception: The exception object
            error_message: Optional error message string (uses str(exception) if not provided)
            
        Returns:
            EngineErrorType enum value
        """
        if error_message is None:
            error_message = str(exception)
        
        exception_name = exception.__class__.__name__.lower()
        message_lower = error_message.lower()
        
        for pattern, error_type in SYSTEM_ERROR_PATTERNS.items():
            if pattern in message_lower or pattern in exception_name:
                logger.debug(f"Classified as {error_type.value} (pattern: {pattern})")
                return error_type
        
        for pattern, error_type in DATA_ERROR_PATTERNS.items():
            if pattern in message_lower or pattern in exception_name:
                logger.debug(f"Classified as {error_type.value} (pattern: {pattern})")
                return error_type
        
        logger.debug(f"Could not classify error: {exception_name}")
        return EngineErrorType.UNKNOWN
    
    def is_system_error(self, error_type: EngineErrorType) -> bool:
        """
        Determine if error is a system error requiring engineering attention.
        
        Args:
            error_type: EngineErrorType enum value
            
        Returns:
            True if system error, False if data error or unknown
        """
        system_errors = {
            EngineErrorType.DATABASE_CONSTRAINT,
            EngineErrorType.DATABASE_CONNECTION,
            EngineErrorType.CODE_BUG,
            EngineErrorType.DEPENDENCY_MISSING,
            EngineErrorType.FILE_SYSTEM,
        }
        
        return error_type in system_errors
    
    def is_data_error(self, error_type: EngineErrorType) -> bool:
        """
        Determine if error is a data quality issue (expected in real-world data).
        
        Args:
            error_type: EngineErrorType enum value
            
        Returns:
            True if data error, False otherwise
        """
        data_errors = {
            EngineErrorType.MALFORMED_XBRL,
            EngineErrorType.XBRL_VALIDATION,
            EngineErrorType.XBRL_STRUCTURE,
            EngineErrorType.DATA_QUALITY,
        }
        
        return error_type in data_errors
    
    def get_log_level(self, error_type: EngineErrorType) -> str:
        """
        Get appropriate log level for error type.
        
        Args:
            error_type: EngineErrorType enum value
            
        Returns:
            Log level string ('error', 'warning', 'info')
        """
        if self.is_system_error(error_type):
            return 'error'
        
        if self.is_data_error(error_type):
            return 'warning'
        
        return 'error'
    
    def get_status_label(self, error_type: EngineErrorType) -> str:
        """
        Get appropriate status label for database records.
        
        Args:
            error_type: EngineErrorType enum value
            
        Returns:
            Status label string for database status fields
        """
        if self.is_system_error(error_type):
            return 'failed_system_error'
        elif self.is_data_error(error_type):
            return 'failed_data_quality'
        else:
            return 'failed'
    
    def should_retry(self, error_type: EngineErrorType) -> bool:
        """
        Determine if error should be retried.
        
        Args:
            error_type: EngineErrorType enum value
            
        Returns:
            True if retry is recommended, False otherwise
        """
        if error_type == EngineErrorType.DATABASE_CONNECTION:
            return True
        
        if error_type == EngineErrorType.FILE_SYSTEM:
            return True
        
        if self.is_system_error(error_type):
            return False
        
        if self.is_data_error(error_type):
            return False
        
        return False
    
    def create_error_report(
        self,
        exception: Exception,
        error_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create comprehensive error report with classification.
        
        Args:
            exception: The exception object
            error_message: Optional error message string
            context: Optional context information
            
        Returns:
            Error report dictionary with classification details
        """
        error_type = self.classify_error(exception, error_message)
        
        report = {
            'error_class': exception.__class__.__name__,
            'error_message': error_message or str(exception),
            'error_type': error_type.value,
            'is_system_error': self.is_system_error(error_type),
            'is_data_error': self.is_data_error(error_type),
            'log_level': self.get_log_level(error_type),
            'status_label': self.get_status_label(error_type),
            'should_retry': self.should_retry(error_type),
            'context': context or {}
        }
        
        return report
    
    def get_user_friendly_message(self, error_type: EngineErrorType) -> str:
        """
        Get user-friendly description of error type.
        
        Args:
            error_type: EngineErrorType enum value
            
        Returns:
            User-friendly error description
        """
        messages = {
            EngineErrorType.SYSTEM_ERROR: "System error - engineering attention required",
            EngineErrorType.DATA_ERROR: "Data quality issue detected",
            EngineErrorType.DATABASE_CONSTRAINT: "Database constraint violation - check for duplicate entries",
            EngineErrorType.DATABASE_CONNECTION: "Database connection issue - will retry",
            EngineErrorType.CODE_BUG: "Programming error detected - engineering attention required",
            EngineErrorType.DEPENDENCY_MISSING: "Required library or module not found",
            EngineErrorType.FILE_SYSTEM: "File system access issue",
            EngineErrorType.MALFORMED_XBRL: "XBRL file contains malformed XML",
            EngineErrorType.XBRL_VALIDATION: "XBRL validation failed against schema",
            EngineErrorType.XBRL_STRUCTURE: "XBRL structure issue - missing or invalid elements",
            EngineErrorType.DATA_QUALITY: "Data quality issue detected",
            EngineErrorType.UNKNOWN: "Unknown error type - will investigate",
        }
        
        return messages.get(error_type, "Unknown error")


engine_error_classifier = EngineErrorClassifier()


def classify_engine_error(exception: Exception, error_message: Optional[str] = None) -> EngineErrorType:
    """Classify engine error."""
    return engine_error_classifier.classify_error(exception, error_message)


def is_system_error(error_type: EngineErrorType) -> bool:
    """Check if error is a system error."""
    return engine_error_classifier.is_system_error(error_type)


def is_data_error(error_type: EngineErrorType) -> bool:
    """Check if error is a data error."""
    return engine_error_classifier.is_data_error(error_type)


def create_engine_error_report(
    exception: Exception,
    error_message: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create comprehensive error report."""
    return engine_error_classifier.create_error_report(exception, error_message, context)


__all__ = [
    'EngineErrorType',
    'EngineErrorClassifier',
    'engine_error_classifier',
    'classify_engine_error',
    'is_system_error',
    'is_data_error',
    'create_engine_error_report',
    'SYSTEM_ERROR_PATTERNS',
    'DATA_ERROR_PATTERNS',
]