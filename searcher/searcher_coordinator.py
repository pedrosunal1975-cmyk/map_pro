"""
Map Pro Searcher Engine Coordinator
===================================

Market-agnostic search engine that discovers companies and filings.
Delegates market-specific operations to market plugins under markets/ directory.

Architecture: Core engine that orchestrates search operations without market-specific logic.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from engines.base.engine_base import BaseEngine
from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from shared.constants.job_constants import JobType
from shared.exceptions.custom_exceptions import EngineError
from database.models.core_models import Entity, Filing
from .company_discovery import CompanyDiscovery
from .filing_identification import FilingIdentification
from .search_results_processor import SearchResultsProcessor

logger = get_logger(__name__, 'engine')


class SearcherCoordinator(BaseEngine):
    """
    Market-agnostic searcher engine coordinator.
    
    Responsibilities:
    - Coordinate company discovery across markets
    - Coordinate filing identification
    - Process and save search results
    - Create follow-up jobs for downloader
    
    Does NOT handle:
    - Market-specific API calls (market plugins handle this)
    - Downloading files (downloader engine handles this)
    - Database schema management (migration system handles this)
    """
    
    def __init__(self):
        """Initialize searcher engine with market-agnostic components."""
        super().__init__("searcher")
        
        # Initialize market-agnostic components
        self.company_discovery = CompanyDiscovery()
        self.filing_identification = FilingIdentification()
        self.results_processor = SearchResultsProcessor()
        
        self.logger.info("Searcher coordinator initialized")
    
    def get_primary_database(self) -> str:
        """Return primary database for searcher engine."""
        return 'core'
    
    def get_supported_job_types(self) -> List[str]:
        """Return job types this engine can process."""
        return [
            JobType.SEARCH_ENTITY.value,
            JobType.FIND_FILINGS.value
        ]
    
    async def process_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process search job (company or filings).
        
        Args:
            job_data: Job information from queue
            
        Returns:
            Processing result with discovered entities/filings
        """
        job_type = job_data.get('job_type')
        
        # Convert enum to string if needed
        job_type_str = job_type.value if hasattr(job_type, 'value') else job_type
        
        try:
            # Check if we have any market plugins available
            available_markets = self.company_discovery.get_available_markets()
            if not available_markets:
                return {
                    'success': False,
                    'error': 'No market plugins available - check market plugin configuration',
                    'job_id': job_data.get('job_id')
                }
            
            if job_type_str == JobType.SEARCH_ENTITY.value:
                return await self._process_company_search(job_data)
            
            elif job_type_str == JobType.FIND_FILINGS.value:
                return await self._process_filing_search(job_data)
            
            else:
                raise EngineError(f"Unsupported job type: {job_type}")
                
        except Exception as e:
            self.logger.error(f"Job processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'job_id': job_data.get('job_id')
            }
    
    async def _process_company_search(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process company search job.
        
        Args:
            job_data: Contains company_identifier and market_type
            
        Returns:
            Result with entity_id and next steps
        """
        parameters = job_data.get('parameters', {})
        company_identifier = parameters.get('company_identifier')
        market_type = parameters.get('market_type')
        
        if not company_identifier or not market_type:
            raise EngineError("Missing required parameters: company_identifier or market_type")
        
        self.logger.info(f"Searching for company: {company_identifier} in {market_type}")
        
        # Use company discovery component (delegates to market plugin)
        company_info = await self.company_discovery.discover_company(
            company_identifier=company_identifier,
            market_type=market_type
        )
        
        if not company_info:
            return {
                'success': False,
                'error': f"Company not found: {company_identifier}",
                'job_id': job_data.get('job_id')
            }
        
        # Save entity to database
        entity_id = await self.results_processor.save_entity(company_info, market_type)
        
        self.logger.info(f"Company discovered and saved: {entity_id}")
        
        # Build result 
        result = {
            'success': True,
            'entity_id': entity_id,
            'company_name': company_info.get('name'),
            'market_type': market_type,
            'job_id': job_data.get('job_id')
        }
        
        # PRESERVE search criteria from parameters so they reach FIND_FILINGS job
        if 'search_criteria' in parameters:
            result['search_criteria'] = parameters['search_criteria']
            self.logger.info(f"Passing search criteria to follow-up job: {parameters['search_criteria']}")
        
        return result
    
    async def _process_filing_search(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process filing search job.
        
        Args:
            job_data: Contains entity_id and search criteria
            
        Returns:
            Result with discovered filings
        """
        parameters = job_data.get('parameters', {})
        self.logger.info(f"FIND_FILINGS job received parameters: {list(parameters.keys())}")
        if 'search_criteria' in parameters:
            self.logger.info(f"Search criteria: {parameters['search_criteria']}")
        else:
            self.logger.warning("NO SEARCH CRITERIA RECEIVED - will search all filings!")
        
        entity_id = job_data.get('entity_id') or parameters.get('entity_id')
        
        if not entity_id:
            raise EngineError("Missing required parameter: entity_id")
        
        # Get entity from database to get market info
        with self.get_session() as session:
            entity = session.query(Entity).filter_by(
                entity_universal_id=entity_id
            ).first()
            
            if not entity:
                raise EngineError(f"Entity not found: {entity_id}")
            
            market_type = entity.market_type
            market_entity_id = entity.market_entity_id
        
        self.logger.info(f"Searching filings for entity: {entity_id} ({market_type})")
        
        # Use filing identification component (delegates to market plugin)
        filings_info = await self.filing_identification.identify_filings(
            market_entity_id=market_entity_id,
            market_type=market_type,
            search_criteria=parameters.get('search_criteria', {})
        )
        
        if not filings_info:
            return {
                'success': True,
                'filings_found': 0,
                'entity_id': entity_id,
                'job_id': job_data.get('job_id')
            }
        
        # Save filings to database
        filing_ids = await self.results_processor.save_filings(
            entity_id=entity_id,
            filings_info=filings_info,
            market_type=market_type
        )
        
        self.logger.info(f"Discovered {len(filing_ids)} filings for entity {entity_id}")
        
        return {
            'success': True,
            'filings_found': len(filing_ids),
            'filing_ids': filing_ids,
            'entity_id': entity_id,
            'job_id': job_data.get('job_id')
        }
    
    def _engine_specific_initialization(self) -> bool:
        """Perform searcher-specific initialization."""
        try:
            # Add detailed logging about plugin loading
            self.logger.info("Checking market plugin availability...")
            
            # Check plugin loading status in detail
            self._debug_plugin_loading()
            
            # Get available markets
            available_markets = self.company_discovery.get_available_markets()
            
            if not available_markets:
                self.logger.warning("No market plugins available")
                self.logger.warning("Searcher engine will start but cannot process jobs until plugins are loaded")
                self.logger.info("This is normal during development or if market plugins are disabled")
                
                # Don't fail initialization - allow engine to start
                # Jobs will fail gracefully if no plugins available
                return True
            
            self.logger.info(f"Available markets: {', '.join(available_markets)}")
            return True
            
        except Exception as e:
            self.logger.error(f"Searcher initialization failed: {e}")
            # Still return True to allow system startup
            self.logger.warning("Continuing with limited functionality")
            return True

    def _debug_plugin_loading(self):
        """Debug helper to understand plugin loading issues."""
        try:
            from core.data_paths import map_pro_paths
            
            markets_path = map_pro_paths.markets
            self.logger.info(f"Markets directory: {markets_path}")
            self.logger.info(f"Markets directory exists: {markets_path.exists()}")
            
            if markets_path.exists():
                market_dirs = [d for d in markets_path.iterdir() if d.is_dir() and d.name not in ['base', '__pycache__']]
                self.logger.info(f"Found market directories: {[d.name for d in market_dirs]}")
                
                for market_dir in market_dirs:
                    market_name = market_dir.name
                    searcher_file = market_dir / f"{market_name}_searcher.py"
                    self.logger.info(f"  {market_name}: searcher file exists = {searcher_file.exists()}")
                    
                    if searcher_file.exists():
                        # Try to import and see what happens
                        try:
                            module_path = f"markets.{market_name}.{market_name}_searcher"
                            self.logger.info(f"  {market_name}: attempting import of {module_path}")
                            
                            module = importlib.import_module(module_path)
                            self.logger.info(f"  {market_name}: import successful")
                            
                            # Check for searcher class
                            class_name = f"{market_name.upper()}Searcher"
                            if hasattr(module, class_name):
                                self.logger.info(f"  {market_name}: {class_name} class found")
                                
                                # Try instantiation
                                searcher_class = getattr(module, class_name)
                                searcher_instance = searcher_class()
                                self.logger.info(f"  {market_name}: {class_name} instantiated successfully")
                                
                            else:
                                self.logger.error(f"  {market_name}: {class_name} class NOT found")
                                available_classes = [attr for attr in dir(module) if not attr.startswith('_')]
                                self.logger.error(f"  {market_name}: available classes: {available_classes}")
                                
                        except ImportError as e:
                            self.logger.error(f"  {market_name}: import failed - {e}")
                        except Exception as e:
                            self.logger.error(f"  {market_name}: instantiation failed - {e}")
                            import traceback
                            self.logger.error(f"  {market_name}: traceback:\n{traceback.format_exc()}")
                            
        except Exception as e:
            self.logger.error(f"Debug plugin loading failed: {e}")
            import traceback
            self.logger.error(f"Debug traceback:\n{traceback.format_exc()}")

    
    def _get_engine_specific_status(self) -> Dict[str, Any]:
        """Get searcher-specific status information."""
        try:
            return {
                'available_markets': self.company_discovery.get_available_markets(),
                'component_status': {
                    'company_discovery': 'operational',
                    'filing_identification': 'operational',
                    'results_processor': 'operational'
                }
            }
        except Exception as e:
            return {'status_error': str(e)}
    
    def _get_loop_interval(self) -> int:
        """Get sleep interval between processing loops (in seconds)."""
        return 10  # Check for new jobs every 10 seconds
    
    def _get_error_recovery_interval(self) -> int:
        """Get sleep interval after errors (in seconds)."""
        return 30  # Wait 30 seconds after error before retry


# Convenience function for creating searcher engine instance
def create_searcher_engine() -> SearcherCoordinator:
    """Create and return searcher engine instance."""
    return SearcherCoordinator()