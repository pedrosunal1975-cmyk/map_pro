"""
Map Pro Base Engine
==================

Base class for all Map Pro engines providing common functionality and patterns.
All engines (searcher, downloader, extractor, parser, librarian, mapper) inherit from this.

Architecture: Foundation class that provides oversight patterns without implementation logic.
"""

import time
import threading
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from datetime import datetime, timezone
from sqlalchemy import text

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from core.data_paths import map_pro_paths
from shared.exceptions.custom_exceptions import EngineError, DatabaseError
from .job_processor import JobProcessor
from .status_reporter import StatusReporter
from .error_handler import ErrorHandler


class BaseEngine(ABC):
    """
    Abstract base class for all Map Pro engines.
    
    Responsibilities:
    - Engine lifecycle management (start/stop/status)
    - Database session coordination
    - Common logging and error handling patterns
    - Job processing coordination
    - Status reporting to core system
    
    Does NOT handle:
    - Specific job processing logic (subclasses implement this)
    - Market-specific operations (market modules handle this)
    - Database schema operations (migration system handles this)
    """
    
    def __init__(self, engine_name: str):
        """
        Initialize base engine with common infrastructure.
        
        Args:
            engine_name: Unique identifier for this engine (e.g., 'searcher', 'parser')
        """
        self.engine_name = engine_name
        self.logger = get_logger(f"engines.{engine_name}", 'engine')
        
        # Engine state management
        self.is_running = False
        self.is_initialized = False
        self._shutdown_requested = False
        self._main_thread = None
        self._thread_lock = threading.Lock()
        
        # Initialize components
        self.job_processor = JobProcessor(self)
        self.status_reporter = StatusReporter(self)
        self.error_handler = ErrorHandler(self)
        
        # Engine metrics
        self.start_time = None
        self.jobs_processed = 0
        self.jobs_failed = 0
        self.last_activity = None
        
        self.logger.info(f"Initialized {engine_name} engine")
    
    @abstractmethod
    def get_primary_database(self) -> str:
        """
        Return the primary database name this engine works with.
        
        Returns:
            Database name ('core', 'parsed', 'library', 'mapped')
        """
        pass
    
    @abstractmethod
    def get_supported_job_types(self) -> List[str]:
        """
        Return list of job types this engine can process.
        
        Returns:
            List of job type strings (e.g., ['search_entity', 'find_filings'])
        """
        pass
    
    @abstractmethod
    async def process_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single job. Must be implemented by subclasses.
        
        Args:
            job_data: Job information including type, parameters, entity_id, etc.
            
        Returns:
            Dictionary with processing results and status
            
        Raises:
            EngineError: If job processing fails
        """
        pass
    
    def initialize(self) -> bool:
        """
        Initialize engine resources and validate readiness.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self.logger.info(f"Initializing {self.engine_name} engine")
            
            # Validate database connectivity
            if not self._validate_database_connectivity():
                return False
            
            # Validate required paths exist
            if not self._validate_required_paths():
                return False
            
            # Engine-specific initialization
            if not self._engine_specific_initialization():
                return False
            
            self.is_initialized = True
            self.logger.info(f"{self.engine_name} engine initialized successfully")
            return True
            
        except Exception as e:
            self.error_handler.handle_initialization_error(e)
            return False
    
    def start(self) -> bool:
        """
        Start the engine in a separate thread.
        
        Returns:
            True if started successfully, False otherwise
        """
        with self._thread_lock:
            if self.is_running:
                self.logger.warning(f"{self.engine_name} engine already running")
                return False
            
            if not self.is_initialized:
                if not self.initialize():
                    return False
            
            try:
                self.is_running = True
                self._shutdown_requested = False
                self.start_time = datetime.now(timezone.utc)
                
                # Start main processing thread
                self._main_thread = threading.Thread(
                    target=self._main_loop,
                    name=f"MapPro-{self.engine_name}",
                    daemon=False
                )
                self._main_thread.start()
                
                self.logger.info(f"{self.engine_name} engine started")
                return True
                
            except Exception as e:
                self.is_running = False
                self.error_handler.handle_startup_error(e)
                return False
    
    def stop(self, timeout: int = 30) -> bool:
        """
        Stop the engine gracefully.
        
        Args:
            timeout: Maximum seconds to wait for graceful shutdown
            
        Returns:
            True if stopped successfully, False if forced shutdown
        """
        with self._thread_lock:
            if not self.is_running:
                self.logger.info(f"{self.engine_name} engine already stopped")
                return True
            
            self.logger.info(f"Stopping {self.engine_name} engine")
            self._shutdown_requested = True
            
            # Wait for graceful shutdown
            if self._main_thread and self._main_thread.is_alive():
                self._main_thread.join(timeout=timeout)
                
                if self._main_thread.is_alive():
                    self.logger.warning(f"{self.engine_name} engine forced shutdown after timeout")
                    return False
            
            self.is_running = False
            self.logger.info(f"{self.engine_name} engine stopped")
            return True
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive engine status information.
        
        Returns:
            Dictionary with engine status details
        """
        status = {
            'engine_name': self.engine_name,
            'is_running': self.is_running,
            'is_initialized': self.is_initialized,
            'primary_database': self.get_primary_database(),
            'supported_job_types': self.get_supported_job_types(),
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'uptime_seconds': (datetime.now(timezone.utc) - self.start_time).total_seconds() if self.start_time else 0,
            'jobs_processed': self.jobs_processed,
            'jobs_failed': self.jobs_failed,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'thread_alive': self._main_thread.is_alive() if self._main_thread else False
        }
        
        # Add engine-specific status
        try:
            engine_status = self._get_engine_specific_status()
            status.update(engine_status)
        except Exception as e:
            status['status_error'] = str(e)
        
        return status
    
    @contextmanager
    def get_session(self, database_name: Optional[str] = None):
        """
        Get database session with automatic cleanup.
        
        Args:
            database_name: Database to connect to, defaults to primary database
            
        Yields:
            Database session
        """
        db_name = database_name or self.get_primary_database()
        
        # FIXED: Use yield from to properly delegate to the underlying context manager
        with db_coordinator.get_session(db_name) as session:
            yield session
    
    def _main_loop(self):
        """Main processing loop - runs in separate thread."""
        self.logger.info(f"{self.engine_name} engine main loop started")
        
        try:
            while self.is_running and not self._shutdown_requested:
                try:
                    # Process pending jobs
                    processed = self.job_processor.process_pending_jobs()
                    
                    if processed > 0:
                        self.last_activity = datetime.now(timezone.utc)
                        self.jobs_processed += processed
                    
                    # Report status periodically
                    self.status_reporter.report_status()
                    
                    # Sleep between iterations
                    time.sleep(self._get_loop_interval())
                    
                except Exception as e:
                    self.jobs_failed += 1
                    self.error_handler.handle_processing_error(e)
                    time.sleep(self._get_error_recovery_interval())
                    
        except Exception as e:
            self.error_handler.handle_critical_error(e)
        finally:
            self.logger.info(f"{self.engine_name} engine main loop stopped")
    
    def _validate_database_connectivity(self) -> bool:
        """Validate that required databases are accessible."""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            self.logger.error(f"Database connectivity validation failed: {e}")
            return False
    
    def _validate_required_paths(self) -> bool:
        """Validate that required file system paths exist."""
        try:
            # Engine-specific log directory
            log_path = map_pro_paths.get_engine_log_path(self.engine_name)
            log_path.mkdir(parents=True, exist_ok=True)
            
            # Temporary workspace
            temp_path = map_pro_paths.get_temp_workspace_path(self.engine_name)
            temp_path.mkdir(parents=True, exist_ok=True)
            
            return True
        except Exception as e:
            self.logger.error(f"Path validation failed: {e}")
            return False
    
    def _engine_specific_initialization(self) -> bool:
        """
        Override in subclasses for engine-specific initialization.
        
        Returns:
            True if initialization successful, False otherwise
        """
        return True
    
    def _get_engine_specific_status(self) -> Dict[str, Any]:
        """
        Override in subclasses to provide additional status information.
        
        Returns:
            Dictionary with engine-specific status details
        """
        return {}
    
    def _get_loop_interval(self) -> float:
        """
        Get sleep interval between main loop iterations.
        
        Returns:
            Sleep time in seconds
        """
        return 10.0  # Default 10 seconds, override in subclasses if needed
    
    def _get_error_recovery_interval(self) -> float:
        """
        Get sleep interval after errors before retrying.
        
        Returns:
            Sleep time in seconds
        """
        return 30.0  # Default 30 seconds recovery time