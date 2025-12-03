"""
Map Pro Stream Handler
======================

Memory-efficient streaming downloads for large files.
Never loads entire file into memory - uses chunked streaming.
"""

import asyncio
from pathlib import Path
from typing import Optional, Callable
import aiofiles

from core.system_logger import get_logger

logger = get_logger(__name__, 'engine')


class StreamHandler:
    """
    Handles streaming downloads with memory efficiency.
    
    Downloads large files in chunks without loading into RAM.
    Supports progress callbacks for UI integration.
    """
    
    def __init__(
        self,
        chunk_size: int = 8192,  # 8KB chunks
        progress_callback: Optional[Callable[[int, int], None]] = None
    ):
        """
        Initialize stream handler.
        
        Args:
            chunk_size: Size of chunks to read/write (bytes)
            progress_callback: Callback function(bytes_downloaded, total_bytes)
        """
        self.chunk_size = chunk_size
        self.progress_callback = progress_callback
        self.logger = logger
    
    async def stream_to_file(
        self,
        response,  # aiohttp.ClientResponse
        file_path: Path,
        total_size: Optional[int] = None
    ) -> int:
        """
        Stream response content to file.
        
        Args:
            response: aiohttp response object
            file_path: Destination file path
            total_size: Total file size if known (for progress)
            
        Returns:
            Total bytes downloaded
        """
        bytes_downloaded = 0
        
        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Open file for writing (async)
            async with aiofiles.open(file_path, 'wb') as f:
                # Stream chunks
                async for chunk in response.content.iter_chunked(self.chunk_size):
                    if chunk:
                        await f.write(chunk)
                        bytes_downloaded += len(chunk)
                        
                        # Call progress callback if provided
                        if self.progress_callback and total_size:
                            self.progress_callback(bytes_downloaded, total_size)
            
            self.logger.debug(
                f"Stream completed: {file_path.name}",
                bytes_downloaded=bytes_downloaded,
                mb=f"{bytes_downloaded / (1024 * 1024):.2f}MB"
            )
            
            return bytes_downloaded
            
        except Exception as e:
            self.logger.error(f"Stream failed for {file_path.name}: {e}")
            # Clean up partial file
            if file_path.exists():
                file_path.unlink()
            raise
    
    async def stream_with_progress(
        self,
        response,
        file_path: Path,
        total_size: Optional[int] = None
    ) -> int:
        """
        Stream with detailed progress tracking.
        
        Args:
            response: aiohttp response object
            file_path: Destination file path
            total_size: Total file size if known
            
        Returns:
            Total bytes downloaded
        """
        bytes_downloaded = 0
        last_progress_log = 0
        
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(file_path, 'wb') as f:
                async for chunk in response.content.iter_chunked(self.chunk_size):
                    if chunk:
                        await f.write(chunk)
                        bytes_downloaded += len(chunk)
                        
                        # Progress callback
                        if self.progress_callback and total_size:
                            self.progress_callback(bytes_downloaded, total_size)
                        
                        # Log progress at intervals (every 10MB)
                        if total_size and bytes_downloaded - last_progress_log >= 10 * 1024 * 1024:
                            progress_pct = (bytes_downloaded / total_size) * 100
                            self.logger.debug(
                                f"Download progress: {file_path.name}",
                                progress=f"{progress_pct:.1f}%",
                                downloaded_mb=f"{bytes_downloaded / (1024 * 1024):.1f}MB"
                            )
                            last_progress_log = bytes_downloaded
            
            return bytes_downloaded
            
        except Exception as e:
            self.logger.error(f"Streaming download failed: {e}")
            if file_path.exists():
                file_path.unlink()
            raise