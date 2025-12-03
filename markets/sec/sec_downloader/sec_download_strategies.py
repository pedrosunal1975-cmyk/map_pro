"""
SEC Download Strategies
=======================

Strategy pattern for identifying and downloading XBRL ZIP files.
Different strategies can be tried in sequence until one succeeds.

Strategy Hierarchy:
1. IndexBasedStrategy - Parse index.json (preferred)
2. PatternBasedStrategy - Try common filename patterns  
3. FallbackStrategy - Last resort attempts

Save location: markets/sec/sec_downloader/sec_download_strategies.py
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from core.system_logger import get_logger

logger = get_logger(__name__, 'market')


@dataclass
class ZIPIdentificationResult:
    """Result of ZIP identification attempt."""
    success: bool
    zip_url: Optional[str] = None
    strategy_used: Optional[str] = None
    attempts: int = 0
    error_message: Optional[str] = None
    fallback_urls: List[str] = None
    
    def __post_init__(self):
        """Initialize fallback URLs list."""
        if self.fallback_urls is None:
            self.fallback_urls = []


class ZIPIdentificationStrategy(ABC):
    """
    Abstract base class for ZIP identification strategies.
    
    Each strategy implements a different approach to finding the XBRL ZIP file.
    """
    
    def __init__(self, name: str):
        """
        Initialize strategy.
        
        Args:
            name: Strategy name for logging
        """
        self.name = name
        self.logger = logger
    
    @abstractmethod
    async def identify(
        self,
        cik: str,
        accession_number: str,
        filing_data: Optional[Dict[str, Any]] = None
    ) -> ZIPIdentificationResult:
        """
        Attempt to identify XBRL ZIP file.
        
        Args:
            cik: Company CIK
            accession_number: Accession number
            filing_data: Optional additional filing data
            
        Returns:
            ZIPIdentificationResult
        """
        pass
    
    def _create_success_result(
        self,
        zip_url: str,
        attempts: int = 1,
        fallback_urls: Optional[List[str]] = None
    ) -> ZIPIdentificationResult:
        """Create successful result."""
        return ZIPIdentificationResult(
            success=True,
            zip_url=zip_url,
            strategy_used=self.name,
            attempts=attempts,
            fallback_urls=fallback_urls or []
        )
    
    def _create_failure_result(
        self,
        error_message: str,
        attempts: int = 1
    ) -> ZIPIdentificationResult:
        """Create failure result."""
        return ZIPIdentificationResult(
            success=False,
            strategy_used=self.name,
            attempts=attempts,
            error_message=error_message
        )


class IndexBasedStrategy(ZIPIdentificationStrategy):
    """
    Strategy that uses index.json to find ZIP file.
    
    This is the preferred strategy for newer filings that have index.json.
    """
    
    def __init__(self, api_client, index_parser, file_identifier):
        """
        Initialize strategy.
        
        Args:
            api_client: SEC API client for fetching index.json
            index_parser: Parser for index.json
            file_identifier: File identifier for finding ZIP
        """
        super().__init__('index_based')
        self.api_client = api_client
        self.index_parser = index_parser
        self.file_identifier = file_identifier
    
    async def identify(
        self,
        cik: str,
        accession_number: str,
        filing_data: Optional[Dict[str, Any]] = None
    ) -> ZIPIdentificationResult:
        """
        Identify ZIP using index.json.
        
        Args:
            cik: Company CIK
            accession_number: Accession number
            filing_data: Optional filing data (not used)
            
        Returns:
            ZIPIdentificationResult
        """
        try:
            self.logger.debug(f"Trying index-based strategy for {accession_number}")
            
            # Step 1: Fetch index.json
            index_json = await self.api_client.get_filing_index(cik, accession_number)
            
            if not index_json:
                return self._create_failure_result(
                    "Failed to fetch index.json",
                    attempts=1
                )
            
            # Step 2: Parse index.json
            index_data = self.index_parser.parse(index_json)
            
            if not index_data:
                return self._create_failure_result(
                    "Failed to parse index.json",
                    attempts=1
                )
            
            # Step 3: Identify ZIP file
            zip_url = self.file_identifier.identify_from_index(
                index_data,
                cik,
                accession_number
            )
            
            if not zip_url:
                return self._create_failure_result(
                    "No XBRL ZIP found in index.json",
                    attempts=1
                )
            
            self.logger.info(f"Index-based strategy succeeded: {zip_url.split('/')[-1]}")
            
            return self._create_success_result(zip_url, attempts=1)
            
        except Exception as e:
            self.logger.error(f"Index-based strategy error: {e}")
            return self._create_failure_result(str(e), attempts=1)


class PatternBasedStrategy(ZIPIdentificationStrategy):
    """
    Strategy that uses common filename patterns.
    
    Fallback for older filings or when index.json is unavailable.
    """
    
    def __init__(self, file_identifier):
        """
        Initialize strategy.
        
        Args:
            file_identifier: File identifier for generating URLs
        """
        super().__init__('pattern_based')
        self.file_identifier = file_identifier
    
    async def identify(
        self,
        cik: str,
        accession_number: str,
        filing_data: Optional[Dict[str, Any]] = None
    ) -> ZIPIdentificationResult:
        """
        Identify ZIP using filename patterns.
        
        Args:
            cik: Company CIK
            accession_number: Accession number
            filing_data: Optional filing data (not used)
            
        Returns:
            ZIPIdentificationResult
        """
        try:
            self.logger.debug(f"Trying pattern-based strategy for {accession_number}")
            
            # Generate potential URLs
            pattern_urls = self.file_identifier.identify_from_pattern(
                cik,
                accession_number
            )
            
            if not pattern_urls:
                return self._create_failure_result(
                    "No pattern URLs generated",
                    attempts=0
                )
            
            # Use first (most likely) URL
            primary_url = pattern_urls[0]
            fallback_urls = pattern_urls[1:]
            
            self.logger.info(
                f"Pattern-based strategy: {primary_url.split('/')[-1]} "
                f"({len(fallback_urls)} fallbacks available)"
            )
            
            return self._create_success_result(
                primary_url,
                attempts=1,
                fallback_urls=fallback_urls
            )
            
        except Exception as e:
            self.logger.error(f"Pattern-based strategy error: {e}")
            return self._create_failure_result(str(e), attempts=1)


class FallbackStrategy(ZIPIdentificationStrategy):
    """
    Last resort strategy using most common pattern.
    
    Always succeeds with at least one URL to try.
    """
    
    def __init__(self, file_identifier):
        """
        Initialize strategy.
        
        Args:
            file_identifier: File identifier
        """
        super().__init__('fallback')
        self.file_identifier = file_identifier
    
    async def identify(
        self,
        cik: str,
        accession_number: str,
        filing_data: Optional[Dict[str, Any]] = None
    ) -> ZIPIdentificationResult:
        """
        Generate fallback ZIP URL.
        
        Args:
            cik: Company CIK
            accession_number: Accession number
            filing_data: Optional filing data
            
        Returns:
            ZIPIdentificationResult (always succeeds)
        """
        try:
            self.logger.debug(f"Using fallback strategy for {accession_number}")
            
            # Use most common pattern: {accession}_htm.zip
            accession_underscore = accession_number.replace('-', '_')
            filename = f"{accession_underscore}_htm.zip"
            
            url = self.file_identifier._construct_url(cik, accession_number, filename)
            
            self.logger.warning(
                f"Fallback strategy: using {filename} (may not exist)"
            )
            
            return self._create_success_result(url, attempts=1)
            
        except Exception as e:
            # Even fallback failed - this shouldn't happen
            self.logger.error(f"Fallback strategy error: {e}")
            return self._create_failure_result(str(e), attempts=1)


class StrategyChain:
    """
    Chain of strategies to try in sequence.
    
    Tries strategies until one succeeds or all fail.
    """
    
    def __init__(self, strategies: List[ZIPIdentificationStrategy]):
        """
        Initialize strategy chain.
        
        Args:
            strategies: List of strategies to try (in order)
        """
        self.strategies = strategies
        self.logger = logger
    
    async def execute(
        self,
        cik: str,
        accession_number: str,
        filing_data: Optional[Dict[str, Any]] = None
    ) -> ZIPIdentificationResult:
        """
        Execute strategies until one succeeds.
        
        Args:
            cik: Company CIK
            accession_number: Accession number
            filing_data: Optional filing data
            
        Returns:
            Result from first successful strategy or last failure
        """
        total_attempts = 0
        last_result = None
        
        for strategy in self.strategies:
            self.logger.debug(f"Trying strategy: {strategy.name}")
            
            result = await strategy.identify(cik, accession_number, filing_data)
            total_attempts += result.attempts
            
            if result.success:
                result.attempts = total_attempts
                self.logger.info(
                    f"Strategy chain succeeded with {strategy.name} "
                    f"after {total_attempts} total attempts"
                )
                return result
            
            last_result = result
            self.logger.debug(f"Strategy {strategy.name} failed: {result.error_message}")
        
        # All strategies failed
        if last_result:
            last_result.attempts = total_attempts
            self.logger.warning(
                f"All {len(self.strategies)} strategies failed for {accession_number}"
            )
            return last_result
        
        # No strategies (shouldn't happen)
        return ZIPIdentificationResult(
            success=False,
            error_message="No strategies configured"
        )


def create_default_strategy_chain(api_client, index_parser, file_identifier) -> StrategyChain:
    """
    Create default strategy chain for SEC downloads.
    
    Order:
    1. IndexBasedStrategy (preferred)
    2. PatternBasedStrategy (fallback)
    3. FallbackStrategy (last resort)
    
    Args:
        api_client: SEC API client
        index_parser: Index parser
        file_identifier: File identifier
        
    Returns:
        Configured StrategyChain
    """
    strategies = [
        IndexBasedStrategy(api_client, index_parser, file_identifier),
        PatternBasedStrategy(file_identifier),
        FallbackStrategy(file_identifier)
    ]
    
    return StrategyChain(strategies)