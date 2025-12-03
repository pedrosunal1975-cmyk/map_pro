# engines/downloader/download_database_operations.py
"""
Download Database Operations
=============================

Handles all database operations for the download coordinator.
Separates database concerns from business logic.

Responsibilities:
- Filing retrieval and queries
- Status updates
- Job creation (extraction jobs)

Design Pattern: Repository Pattern
Benefits: Testable, mockable, clear separation of concerns
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from core.data_paths import map_pro_paths
from database.models.core_models import Filing, ProcessingJob
from shared.constants.job_constants import JobType, JobStatus
from shared.exceptions.custom_exceptions import EngineError


class DownloadDatabaseOperations:
    """
    Encapsulates all database operations for download coordinator.
    
    This class follows the Repository pattern to isolate database access
    and make the coordinator more testable.
    """
    
    def __init__(self, logger):
        """
        Initialize database operations handler.
        
        Args:
            logger: Logger instance for operation tracking
        """
        self.logger = logger
    
    def get_filing_by_id(self, filing_id: str, session) -> Filing:
        """
        Retrieve filing from database by universal ID.
        
        Args:
            filing_id: Filing universal identifier
            session: Active database session
            
        Returns:
            Filing object
            
        Raises:
            EngineError: If filing not found in database
        """
        filing = session.query(Filing).filter(
            Filing.filing_universal_id == filing_id
        ).first()
        
        if not filing:
            error_msg = f"Filing {filing_id} not found in database"
            self.logger.error(error_msg)
            raise EngineError(error_msg)
        
        self.logger.debug(f"Retrieved filing: {filing_id}")
        return filing
    
    def update_filing_status(
        self,
        filing: Filing,
        status: str,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update filing download status.
        
        Args:
            filing: Filing database object
            status: New status value (e.g., 'downloading', 'completed', 'failed')
            error_message: Optional error message for failed downloads
        """
        filing.download_status = status
        
        if error_message:
            self.logger.error(
                f"Filing {filing.filing_universal_id} status: {status} - {error_message}"
            )
        else:
            self.logger.debug(
                f"Filing {filing.filing_universal_id} status updated: {status}"
            )
    
    def update_successful_download(
        self,
        filing: Filing,
        save_path: Path,
        file_size_mb: float
    ) -> None:
        """
        Update filing with successful download information.
        
        Args:
            filing: Filing database object
            save_path: Path where file was saved
            file_size_mb: Size of downloaded file in megabytes
        """
        filing.download_status = 'completed'
        
        # Store as relative path for portability
        try:
            relative_path = save_path.parent.relative_to(map_pro_paths.data_root)
            filing.filing_directory_path = str(relative_path)
            self.logger.debug(f"Stored relative filing_directory_path: {relative_path}")
        except ValueError:
            # Path is not relative to data_root, store absolute as fallback
            filing.filing_directory_path = str(save_path.parent)
            self.logger.warning(
                f"Could not make path relative to data_root, storing absolute: "
                f"{save_path.parent}"
            )
        
        filing.download_size_mb = file_size_mb
        filing.download_completed_at = datetime.now(timezone.utc)
        
        self.logger.info(
            f"Updated filing {filing.filing_universal_id}: "
            f"{file_size_mb:.2f}MB at {save_path.parent}"
        )
    
    def create_extraction_job(self, filing_id: str, session) -> bool:
        """
        Create extraction job for ZIP file.
        
        Note: Does not commit session - caller's context manager handles commits.
        
        Args:
            filing_id: Filing universal identifier
            session: Active database session
            
        Returns:
            True if job created successfully, False otherwise
        """
        try:
            extraction_job = ProcessingJob(
                job_type=JobType.EXTRACT_FILES.value,
                job_status=JobStatus.QUEUED.value,
                filing_universal_id=filing_id,
                job_parameters={'filing_universal_id': str(filing_id)}
            )
            
            session.add(extraction_job)
            self.logger.info(f"Queued extraction job for filing {filing_id}")
            return True
            
        except Exception as e:
            # Non-critical failure - download was successful
            self.logger.error(
                f"Failed to create extraction job for filing {filing_id}: {e}"
            )
            return False