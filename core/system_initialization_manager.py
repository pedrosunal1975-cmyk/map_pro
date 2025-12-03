# File: /map_pro/core/system_initialization_manager.py

"""
System Initialization Manager
==============================

Manages the initialization sequence for the Map Pro system.
Coordinates infrastructure setup, database initialization, and component registration.

Responsibilities:
- Core infrastructure initialization
- Database setup and migrations
- System validation
- Component registration
- Initialization status tracking
"""

from typing import Dict, Any
from datetime import datetime, timezone

from .system_logger import get_logger, map_pro_logger
from .database_coordinator import db_coordinator
from .data_paths import map_pro_paths
from .system_validator import SystemValidator
from .component_manager import ComponentManager
from database.migrations.migration_manager import migration_manager

logger = get_logger(__name__, 'core')


class SystemInitializationManager:
    """
    Manages system initialization workflow.
    
    Initialization Steps:
    1. Core infrastructure (directories, logging)
    2. Database connections and migrations
    3. System readiness validation
    4. Component registration and initialization
    """
    
    def __init__(
        self,
        component_manager: ComponentManager,
        system_validator: SystemValidator
    ):
        """
        Initialize the initialization manager.
        
        Args:
            component_manager: Component lifecycle manager
            system_validator: System validation checker
        """
        self.component_manager = component_manager
        self.system_validator = system_validator
        
        # Track initialization status
        self.status = {
            'started_at': None,
            'completed_at': None,
            'success': False,
            'error': None,
            'stages': {}
        }
        
        logger.debug("System initialization manager created")
    
    async def initialize_system(self) -> bool:
        """
        Execute complete system initialization sequence.
        
        Returns:
            True if initialization successful, False otherwise
        """
        logger.info("Starting Map Pro system initialization")
        self.status['started_at'] = datetime.now(timezone.utc)
        
        try:
            # Step 1: Core infrastructure
            if not await self._initialize_core_infrastructure():
                logger.error("Core infrastructure initialization failed")
                return False
            
            # Step 2: Databases
            if not await self._initialize_databases():
                logger.error("Database initialization failed")
                return False
            
            # Step 3: System validation
            if not await self._validate_system_readiness():
                logger.error("System validation failed")
                return False
            
            # Step 4: Components
            if not await self._initialize_components():
                logger.error("Component initialization failed")
                return False
            
            # Mark as successful
            self.status['completed_at'] = datetime.now(timezone.utc)
            self.status['success'] = True
            
            logger.info("Map Pro system initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"System initialization failed: {e}")
            self.status['error'] = str(e)
            self.status['success'] = False
            return False
    
    async def _initialize_core_infrastructure(self) -> bool:
        """
        Initialize core infrastructure components.
        
        Includes:
        - Data directory structure
        - Logging system setup
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("Initializing core infrastructure")
        
        try:
            # Initialize data directories
            if not self._initialize_data_directories():
                return False
            
            # Initialize logging system
            if not self._initialize_logging():
                return False
            
            self.status['stages']['core_infrastructure'] = 'completed'
            logger.info("Core infrastructure initialization completed")
            return True
            
        except Exception as e:
            logger.error(f"Core infrastructure initialization failed: {e}")
            self.status['stages']['core_infrastructure'] = f'failed: {e}'
            return False
    
    def _initialize_data_directories(self) -> bool:
        """
        Initialize data directory structure.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            map_pro_paths.ensure_data_directories()
            logger.info("Data directories initialized successfully")
            self.status['stages']['data_paths'] = 'completed'
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize directory structure: {e}")
            self.status['stages']['data_paths'] = f'failed: {e}'
            return False
    
    def _initialize_logging(self) -> bool:
        """
        Initialize logging system.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            log_status = map_pro_logger.get_log_status()
            
            if log_status.get('initialization_error'):
                logger.warning(
                    f"Logging initialization issues: "
                    f"{log_status['initialization_error']}"
                )
            
            self.status['stages']['logging'] = 'completed'
            logger.debug("Logging system initialized")
            return True
            
        except Exception as e:
            logger.error(f"Logging initialization failed: {e}")
            self.status['stages']['logging'] = f'failed: {e}'
            return False
    
    async def _initialize_databases(self) -> bool:
        """
        Initialize database connections and run migrations.
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("Initializing databases")
        
        try:
            # Initialize database coordinator
            if not self._initialize_database_coordinator():
                return False
            
            # Run migrations for all databases
            if not self._run_database_migrations():
                return False
            
            self.status['stages']['databases'] = 'completed'
            logger.info("Database initialization completed")
            return True
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            self.status['stages']['databases'] = f'failed: {e}'
            return False
    
    def _initialize_database_coordinator(self) -> bool:
        """
        Initialize the database coordinator.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not db_coordinator.initialize():
                logger.error("Failed to initialize database coordinator")
                return False
            
            self.status['stages']['database_coordinator'] = 'completed'
            logger.debug("Database coordinator initialized")
            return True
            
        except Exception as e:
            logger.error(f"Database coordinator initialization failed: {e}")
            return False
    
    def _run_database_migrations(self) -> bool:
        """
        Run migrations for all databases.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            for db_name in migration_manager.database_names:
                if not migration_manager.initialize_database(db_name):
                    logger.error(f"Failed to initialize database: {db_name}")
                    return False
            
            self.status['stages']['database_migrations'] = 'completed'
            logger.debug("Database migrations completed")
            return True
            
        except Exception as e:
            logger.error(f"Database migration failed: {e}")
            return False
    
    async def _validate_system_readiness(self) -> bool:
        """
        Validate that system is ready for operation.
        
        Returns:
            True if validation passes, False otherwise
        """
        logger.info("Validating system readiness")
        
        try:
            validation_result = self.system_validator.validate_startup_requirements()
            
            if not validation_result.get('ready', False):
                blocking_issues = validation_result.get('blocking_issues', [])
                logger.error(f"System validation failed: {blocking_issues}")
                return False
            
            # Log warnings if any
            warnings = validation_result.get('warnings')
            if warnings:
                logger.warning(f"System validation warnings: {warnings}")
            
            self.status['stages']['validation'] = 'completed'
            logger.info("System readiness validation completed")
            return True
            
        except Exception as e:
            logger.error(f"System validation failed: {e}")
            self.status['stages']['validation'] = f'failed: {e}'
            return False
    
    async def _initialize_components(self) -> bool:
        """
        Register and initialize system components.
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("Initializing system components")
        
        try:
            # Register core components
            self._register_core_components()
            
            # Register all engines
            self._register_engines()
            
            # Initialize all registered components
            if not await self.component_manager.initialize_components():
                logger.error("Failed to initialize components")
                return False
            
            self.status['stages']['components'] = 'completed'
            logger.info("Component initialization completed")
            return True
            
        except Exception as e:
            logger.error(f"Component initialization failed: {e}")
            self.status['stages']['components'] = f'failed: {e}'
            return False
    
    def _register_core_components(self) -> None:
        """Register core system components."""
        logger.debug("Registering core components")
        
        self.component_manager.register_component(
            'database_coordinator',
            db_coordinator,
            []
        )
        
        logger.debug("Core components registered")
    
    def _register_engines(self) -> None:
        """
        Register all engines with the component manager.
        
        Engines are registered using their factory functions from their
        respective modules. Non-critical failures are logged but don't
        stop the registration process.
        """
        logger.info("Starting engine registration process")
        
        engine_configs = [
            ('searcher', 'engines.searcher', 'create_searcher_engine'),
            ('downloader', 'engines.downloader', 'create_downloader_engine'),
            ('extractor', 'engines.extractor', 'create_extractor_engine'),
            ('parser', 'engines.parser', 'create_parser_engine'),
            ('mapper', 'engines.mapper', 'create_mapping_engine'),
            ('librarian', 'engines.librarian.library_coordinator', 'create_librarian_engine'),
        ]
        
        for engine_name, module_path, factory_function in engine_configs:
            self._register_single_engine(engine_name, module_path, factory_function)
        
        # Log registration summary
        self._log_engine_registration_summary()
    
    def _register_single_engine(
        self,
        engine_name: str,
        module_path: str,
        factory_function: str
    ) -> None:
        """
        Register a single engine.
        
        Args:
            engine_name: Name of the engine
            module_path: Python module path
            factory_function: Factory function name
        """
        try:
            logger.info(f"Attempting to register engine: {engine_name}")
            
            # Import the module
            module = __import__(module_path, fromlist=[factory_function])
            
            # Get the factory function
            factory = getattr(module, factory_function)
            
            # Create engine instance
            engine_instance = factory()
            
            # Register with component manager
            self.component_manager.register_component(
                engine_name,
                engine_instance,
                dependencies=['database_coordinator'],
                critical=False
            )
            
            logger.info(f"Successfully registered engine: {engine_name}")
            
        except Exception as e:
            logger.error(f"Failed to register engine {engine_name}: {e}")
            # Continue with other engines - non-critical failure
    
    def _log_engine_registration_summary(self) -> None:
        """Log summary of engine registration."""
        try:
            registered_engines = [
                name 
                for name, info in self.component_manager.registry.components.items()
                if hasattr(info.component_instance, 'job_processor')
            ]
            
            logger.info(
                f"Successfully registered {len(registered_engines)} engines: "
                f"{registered_engines}"
            )
            logger.info("Engine registration completed")
            
        except Exception as e:
            logger.error(f"Failed to log engine registration summary: {e}")
    
    def get_initialization_status(self) -> Dict[str, Any]:
        """
        Get current initialization status.
        
        Returns:
            Dictionary with initialization status details
        """
        return self.status.copy()


__all__ = ['SystemInitializationManager']