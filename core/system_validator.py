"""
Map Pro System Validator
========================

Central validation coordinator for Map Pro system integrity and compliance.
Orchestrates validation across the system without implementing specific checks.

Architecture: Core oversight/coordination - delegates specific validation to specialized components.
"""

from typing import Dict, Any

from .data_paths import map_pro_paths
from .system_logger import get_logger
from .validation_checks import ValidationChecks
from .alert_manager import create_alert

logger = get_logger(__name__, 'core')


class SystemValidator:
    """
    Central coordinator for Map Pro system validation.
    
    Responsibilities:
    - System validation orchestration
    - Validation lifecycle management
    - Integration with validation components
    - Result aggregation and reporting
    
    Does NOT handle:
    - Specific validation implementations (validation_checks handles this)
    - Individual compliance rules (compliance_validator handles this)
    - Alert generation logic (alert_manager handles this)
    """
    
    def __init__(self):
        self.validation_checks = ValidationChecks()
        self.validation_results = {}
        
        logger.info("System validator initializing")
    
    def run_startup_validation(self) -> Dict[str, Any]:
        """
        Run comprehensive system validation during startup.
        
        Returns:
            Dictionary with validation results and overall status
        """
        logger.info("Starting system startup validation")
        
        validation_results = {
            'validation_type': 'startup',
            'overall_status': 'unknown',
            'validation_timestamp': str(map_pro_paths.data_root),
            'checks': {}
        }
        
        try:
            # Delegate all validation checks to validation_checks component
            validation_results['checks'] = self.validation_checks.run_all_startup_checks()
            
            # Determine overall status
            validation_results['overall_status'] = self._determine_overall_status(validation_results['checks'])
            
            # Generate alerts for critical issues
            self._process_validation_alerts(validation_results['checks'])
            
            logger.info(f"Startup validation completed with status: {validation_results['overall_status']}")
            
        except Exception as e:
            logger.error(f"Startup validation failed: {e}")
            validation_results['overall_status'] = 'error'
            validation_results['error'] = str(e)
        
        self.validation_results = validation_results
        return validation_results
    
    def validate_startup_requirements(self) -> Dict[str, Any]:
        """
        Validate startup requirements and return system coordinator compatible format.
        
        This method bridges the gap between system_coordinator expectations and 
        the validation system's actual implementation.
        
        Returns:
            Dictionary with 'ready', 'blocking_issues', and 'warnings' keys
        """
        logger.info("Validating startup requirements for system coordinator")
        
        try:
            # Run the full startup validation
            full_validation = self.run_startup_validation()
            
            # Convert to system coordinator expected format
            overall_status = full_validation.get('overall_status', 'error')
            checks = full_validation.get('checks', {})
            
            # Determine if system is ready
            ready = overall_status in ['pass', 'warning']
            
            # Extract blocking issues (errors and failures)
            blocking_issues = []
            warnings = []
            
            for check_name, check_result in checks.items():
                status = check_result.get('status', 'unknown')
                
                if status == 'error':
                    error_msg = check_result.get('error', f'{check_name} validation error')
                    blocking_issues.append(f"{check_name}: {error_msg}")
                elif status == 'fail':
                    details = check_result.get('details', {})
                    blocking_issues.append(f"{check_name}: validation failed - {details}")
                elif status == 'warning':
                    # Extract detailed warning message if available
                    warning_msg = self._format_warning_message(check_name, check_result)
                    warnings.append(warning_msg)
            
            # If we have blocking issues, system is not ready
            if blocking_issues:
                ready = False
            
            result = {
                'ready': ready,
                'blocking_issues': blocking_issues,
                'warnings': warnings,
                'validation_details': full_validation  # Include full details for debugging
            }
            
            logger.info(f"Startup requirements validation: ready={ready}, "
                       f"blocking_issues={len(blocking_issues)}, warnings={len(warnings)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Startup requirements validation failed: {e}")
            return {
                'ready': False,
                'blocking_issues': [f'Validation system error: {str(e)}'],
                'warnings': [],
                'validation_details': {'error': str(e)}
            }
    
    def run_runtime_validation(self) -> Dict[str, Any]:
        """
        Run lighter validation checks during runtime.
        
        Returns:
            Runtime validation results
        """
        logger.debug("Running runtime validation")
        
        runtime_results = {
            'validation_type': 'runtime',
            'timestamp': str(map_pro_paths.data_root),
            'checks': {}
        }
        
        try:
            # Delegate runtime checks to validation_checks component
            runtime_results['checks'] = self.validation_checks.run_runtime_checks()
            runtime_results['overall_status'] = self._determine_overall_status(runtime_results['checks'])
            
        except Exception as e:
            logger.error(f"Runtime validation failed: {e}")
            runtime_results['overall_status'] = 'error'
            runtime_results['error'] = str(e)
        
        return runtime_results
    
    def validate_engine_readiness(self, engine_name: str) -> Dict[str, Any]:
        """
        Validate that system is ready for specific engine to start.
        
        Args:
            engine_name: Name of engine requesting validation
            
        Returns:
            Engine readiness validation results
        """
        logger.info(f"Validating readiness for engine: {engine_name}")
        
        try:
            return self.validation_checks.check_engine_readiness(engine_name)
        except Exception as e:
            logger.error(f"Engine readiness validation failed for {engine_name}: {e}")
            return {
                'engine_name': engine_name,
                'ready': False,
                'blocking_issues': [f'Validation error: {str(e)}'],
                'warnings': []
            }
    
    def _determine_overall_status(self, checks: Dict[str, Any]) -> str:
        """Determine overall validation status based on individual checks."""
        has_error = any(check.get('status') == 'error' for check in checks.values())
        has_failure = any(check.get('status') == 'fail' for check in checks.values())
        has_warning = any(check.get('status') == 'warning' for check in checks.values())
        
        if has_error:
            return 'error'
        elif has_failure:
            return 'fail'
        elif has_warning:
            return 'warning'
        else:
            return 'pass'
    
    def _format_warning_message(self, check_name: str, check_result: Dict[str, Any]) -> str:
        """
        Format warning message from validation check result.
        
        Extracts detailed warning message if available, otherwise falls back to generic format.
        
        Args:
            check_name: Name of the validation check
            check_result: Validation result dictionary
            
        Returns:
            Formatted warning message string
        """
        # Try to get detailed warning_message from validators
        warning_message = check_result.get('warning_message')
        
        if warning_message:
            # Use the detailed message provided by the validator
            return f"{check_name}: {warning_message}"
        
        # Fallback to generic message with status
        message = check_result.get('message', 'warning')
        return f"{check_name}: {message}"
    
    def _process_validation_alerts(self, checks: Dict[str, Any]):
        """Generate alerts for validation failures."""
        for check_name, check_result in checks.items():
            status = check_result.get('status')
            
            if status == 'fail':
                create_alert(
                    f"validation_{check_name}",
                    f"System validation failed for {check_name}: {check_result}",
                    'critical'
                )
            elif status == 'error':
                create_alert(
                    f"validation_error_{check_name}",
                    f"System validation error in {check_name}: {check_result.get('error')}",
                    'critical'
                )
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of last validation results."""
        if not self.validation_results:
            return {'status': 'no_validation_run'}
        
        return {
            'last_validation_status': self.validation_results.get('overall_status'),
            'checks_run': len(self.validation_results.get('checks', {})),
            'validation_available': True
        }


# Global system validator instance
system_validator = SystemValidator()


def run_startup_validation() -> Dict[str, Any]:
    """Convenience function to run startup validation."""
    return system_validator.run_startup_validation()


def validate_engine_readiness(engine_name: str) -> Dict[str, Any]:
    """Convenience function to validate engine readiness."""
    return system_validator.validate_engine_readiness(engine_name)


def get_validation_summary() -> Dict[str, Any]:
    """Convenience function to get validation summary."""
    return system_validator.get_validation_summary()