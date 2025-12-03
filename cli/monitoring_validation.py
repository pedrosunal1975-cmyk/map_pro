"""
Validation Handler for Monitoring Commands.

Handles system validation and issue fixing.

Location: tools/cli/monitoring_validation.py
"""

from typing import Dict, Any

from core.system_logger import get_logger
from core.system_validator import system_validator

from .monitoring_constants import MonitoringIcons


logger = get_logger(__name__, 'maintenance')


class ValidationHandler:
    """
    Handles system validation operations.
    
    Features:
    - Full system validation
    - Issue detection
    - Automatic fixing (optional)
    - Detailed issue reporting
    
    Example:
        >>> handler = ValidationHandler()
        >>> handler.run(fix_issues=True)
    """
    
    def __init__(self):
        """Initialize validation handler."""
        self.logger = logger
    
    def run(self, fix_issues: bool = False) -> int:
        """
        Run system validation.
        
        Args:
            fix_issues: Attempt to fix issues automatically
            
        Returns:
            0 if valid, 1 if validation failed
        """
        try:
            action_text = "Validating and fixing" if fix_issues else "Validating"
            print(f"\n{MonitoringIcons.VALIDATION} {action_text} system configuration...")
            
            validation_result = system_validator.run_full_validation()
            
            if validation_result.get('valid', False):
                print(f"{MonitoringIcons.HEALTHY} System validation passed")
                return 0
            else:
                return self._handle_failures(validation_result, fix_issues)
        
        except Exception as e:
            print(f"{MonitoringIcons.ERROR} Validation failed: {e}")
            self.logger.error(f"Validation failed: {e}", exc_info=True)
            return 1
    
    def _handle_failures(self, validation_result: Dict[str, Any], fix_issues: bool) -> int:
        """
        Handle validation failures.
        
        Args:
            validation_result: Validation result dictionary
            fix_issues: Whether to attempt fixes
            
        Returns:
            1 to indicate validation failed
        """
        print(f"{MonitoringIcons.ERROR} System validation failed")
        
        issues = validation_result.get('issues', [])
        for issue in issues:
            self._display_issue(issue)
            
            if fix_issues and issue.get('fixable', False):
                self._attempt_fix(issue)
        
        return 1
    
    def _display_issue(self, issue: Dict[str, Any]) -> None:
        """
        Display a single validation issue.
        
        Args:
            issue: Issue dictionary
        """
        severity = issue.get('severity', 'unknown')
        message = issue.get('message', 'Unknown issue')
        component = issue.get('component', 'System')
        
        severity_icon = {
            'critical': MonitoringIcons.CRITICAL,
            'warning': MonitoringIcons.WARNING,
            'info': MonitoringIcons.INFO
        }.get(severity, '[?]')
        
        print(f"  {severity_icon} {component}: {message}")
    
    def _attempt_fix(self, issue: Dict[str, Any]) -> None:
        """
        Attempt to fix a validation issue.
        
        Args:
            issue: Issue to fix
        """
        try:
            fix_result = system_validator.fix_issue(issue)
            if fix_result.get('fixed', False):
                action = fix_result.get('action', 'Unknown action')
                print(f"    {MonitoringIcons.HEALTHY} Fixed: {action}")
            else:
                error = fix_result.get('error', 'Unknown error')
                print(f"    {MonitoringIcons.ERROR} Fix failed: {error}")
        except Exception as fix_error:
            print(f"    {MonitoringIcons.ERROR} Fix error: {fix_error}")
            self.logger.error(f"Fix attempt failed: {fix_error}", exc_info=True)


__all__ = ['ValidationHandler']