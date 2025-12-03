# File: shared/validators/system_compliance_validator.py
"""
Map Pro System Compliance Validator
===================================

Validates system compliance with Map Pro architectural principles and standards.
Provides specialized compliance checking without coordination logic.

Architecture: Specialized validator focused on architectural compliance rules.
"""

from typing import Dict, Any, List
from pathlib import Path
import logging

from core.data_paths import map_pro_paths
from shared.exceptions.custom_exceptions import ComplianceViolationError

logger = logging.getLogger(__name__)

DEFAULT_ARCHITECTURAL_RULES = {
    'max_file_lines': 400,
    'require_init_files': True,
    'enforce_naming_conventions': True
}


class SystemComplianceValidator:
    """
    Validates Map Pro system compliance with architectural standards.

    Responsibilities:
    - Architectural principle compliance checking
    - System standard validation
    - Compliance rule enforcement
    - Violation detection and reporting

    Does NOT handle:
    - System coordination (system_validator handles this)
    - Alert generation (alert_manager handles this)
    - General validation logic (validation_checks handles this)
    """

    def __init__(self):
        try:
            from shared.constants.system_constants import ARCHITECTURAL_RULES
            self.compliance_rules = ARCHITECTURAL_RULES
        except ImportError:
            logger.warning("ARCHITECTURAL_RULES not found, using defaults")
            self.compliance_rules = DEFAULT_ARCHITECTURAL_RULES

    def validate_architectural_compliance(self) -> Dict[str, Any]:
        """
        Validate compliance with Map Pro architectural principles.

        Returns:
            Compliance validation results
        """
        result = {
            'status': 'pass',
            'violations': [],
            'compliance_score': 1.0,
            'details': {}
        }

        try:
            violations = []

            violations.extend(self._check_core_design_compliance())
            violations.extend(self._check_naming_compliance())
            violations.extend(self._check_file_organization_compliance())

            if violations:
                result['status'] = 'fail' if any(v['severity'] == 'critical' for v in violations) else 'warning'
                result['violations'] = violations
                result['compliance_score'] = self._calculate_compliance_score(violations)

            result['details'] = {
                'rules_checked': len(self.compliance_rules),
                'violations_found': len(violations),
                'critical_violations': len([v for v in violations if v['severity'] == 'critical'])
            }

        except Exception as e:
            logger.error(f"Error during compliance validation: {e}")
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    def _check_core_design_compliance(self) -> List[Dict[str, Any]]:
        """Check compliance with core design principles."""
        violations = []

        core_files = list(map_pro_paths.core.glob('*.py'))

        for core_file in core_files:
            if core_file.name.startswith('__'):
                continue

            try:
                line_count = self._count_file_lines(core_file)
                if line_count > 400:
                    violations.append({
                        'rule': 'file_size_limit',
                        'severity': 'warning',
                        'message': f'Core file {core_file.name} exceeds 400 lines ({line_count} lines)',
                        'file': str(core_file)
                    })
            except (IOError, OSError) as e:
                logger.warning(f"Could not read file {core_file}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error counting lines in {core_file}: {e}")

        return violations

    def _check_naming_compliance(self) -> List[Dict[str, Any]]:
        """Check compliance with naming conventions."""
        violations = []

        markets_path = map_pro_paths.markets

        if markets_path.exists():
            for market_dir in markets_path.iterdir():
                if market_dir.is_dir() and market_dir.name not in ['__pycache__', 'base']:
                    market_name = market_dir.name

                    expected_files = [
                        f"{market_name}_searcher.py",
                        f"{market_name}_downloader.py",
                        f"{market_name}_parser.py",
                        f"{market_name}_mapper.py",
                        f"{market_name}_workflow.py",
                        f"{market_name}_validators.py"
                    ]

                    for expected_file in expected_files:
                        if not (market_dir / expected_file).exists():
                            violations.append({
                                'rule': 'market_naming_convention',
                                'severity': 'warning',
                                'message': f'Missing expected market file: {expected_file} in {market_name}',
                                'market': market_name,
                                'missing_file': expected_file
                            })

        return violations

    def _check_file_organization_compliance(self) -> List[Dict[str, Any]]:
        """Check compliance with file organization standards."""
        violations = []

        required_init_dirs = [
            map_pro_paths.core,
            map_pro_paths.engines,
            map_pro_paths.markets,
            map_pro_paths.shared
        ]

        for directory in required_init_dirs:
            if directory.exists():
                init_file = directory / '__init__.py'
                if not init_file.exists():
                    violations.append({
                        'rule': 'init_file_required',
                        'severity': 'warning',
                        'message': f'Missing __init__.py in {directory.name}',
                        'directory': str(directory)
                    })

        return violations

    def _count_file_lines(self, file_path: Path) -> int:
        """Count non-empty lines in a Python file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines()]
            return len([line for line in lines if line and not line.startswith('#')])

    def _calculate_compliance_score(self, violations: List[Dict[str, Any]]) -> float:
        """Calculate compliance score based on violations."""
        if not violations:
            return 1.0

        total_weight = 0
        for violation in violations:
            if violation['severity'] == 'critical':
                total_weight += 1.0
            elif violation['severity'] == 'warning':
                total_weight += 0.5

        max_possible_weight = len(violations)
        return max(0.0, 1.0 - (total_weight / max(max_possible_weight, 1.0)))

    def validate_engine_compliance(self, engine_name: str) -> Dict[str, Any]:
        """
        Validate specific engine compliance with architectural standards.

        Args:
            engine_name: Name of engine to validate

        Returns:
            Engine-specific compliance results
        """
        result = {
            'engine_name': engine_name,
            'status': 'pass',
            'violations': [],
            'details': {}
        }

        try:
            engine_path = map_pro_paths.engines / engine_name

            if not engine_path.exists():
                result['status'] = 'fail'
                result['violations'].append({
                    'rule': 'engine_directory_exists',
                    'severity': 'critical',
                    'message': f'Engine directory does not exist: {engine_path}'
                })
                return result

            coordinator_file = engine_path / f"{engine_name}_coordinator.py"
            if not coordinator_file.exists():
                result['violations'].append({
                    'rule': 'coordinator_file_required',
                    'severity': 'critical',
                    'message': f'Missing coordinator file: {coordinator_file.name}',
                    'engine': engine_name
                })
                result['status'] = 'fail'

            result['details'] = {
                'engine_path': str(engine_path),
                'violations_found': len(result['violations'])
            }

        except Exception as e:
            logger.error(f"Error validating engine {engine_name}: {e}")
            result['status'] = 'error'
            result['error'] = str(e)

        return result