# File: shared/validators/partition_validator.py
"""
Map Pro Partition Separation Validator
=====================================

Validates that data/program partition separation is maintained according to Map Pro architecture rules.

VALIDATION RULES:
1. NO data files (.json, .db, .log, .csv, .xlsx, .zip, .xml, .xbrl, .html, .htm, .txt)
   in program partition
2. NO program files (.py, .pyc, .pyo, .pyd, .so)
   in data partition
3. ALL business data, logs, outputs, configurations must be in data partition
4. ALL executable code, scripts, modules must be in program partition

Uses data_paths.py for all path operations - no hardcoded paths.
"""

from typing import Dict, List
from core.data_paths import map_pro_paths


class PartitionValidator:
    """Validates data/program partition separation using central path authority."""

    def __init__(self):
        self.paths = map_pro_paths

        self.data_file_extensions = {
            '.json', '.db', '.log', '.csv', '.xlsx', '.zip',
            '.xml', '.xbrl', '.html', '.htm', '.txt'
        }

        self.program_file_extensions = {
            '.py', '.pyc', '.pyo', '.pyd', '.so'
        }

    def validate_partitions(self) -> Dict[str, List[str]]:
        """Check both partitions for violations according to Map Pro rules."""
        violations = {
            'data_in_program': [],
            'programs_in_data': []
        }

        excluded_dirs = {
            'venv', '.venv', 'env', '.env', '__pycache__',
            '.git', '.pytest_cache', 'node_modules'
        }

        if self.paths.program_root.exists():
            for file_path in self.paths.program_root.rglob("*"):
                if any(excluded in file_path.parts for excluded in excluded_dirs):
                    continue

                if file_path.is_file() and file_path.suffix.lower() in self.data_file_extensions:
                    violations['data_in_program'].append(str(file_path))

        if self.paths.data_root.exists():
            for file_path in self.paths.data_root.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in self.program_file_extensions:
                    violations['programs_in_data'].append(str(file_path))

        return violations

    def generate_report(self) -> str:
        """Generate partition violation report with architectural guidance."""
        violations = self.validate_partitions()

        if not violations['data_in_program'] and not violations['programs_in_data']:
            return "[OK] Data/Program partition separation is correctly maintained"

        report = "[WARNING] CRITICAL: Partition separation violations found:\n\n"

        if violations['data_in_program']:
            report += "RULE VIOLATION: Data files found in program partition\n"
            report += f"Program partition: {self.paths.program_root}\n"
            report += "These files must be moved to data partition:\n"
            for violation in violations['data_in_program']:
                report += f"  - {violation}\n"
            report += f"Correct location: {self.paths.data_root}\n\n"

        if violations['programs_in_data']:
            report += "RULE VIOLATION: Program files found in data partition\n"
            report += f"Data partition: {self.paths.data_root}\n"
            report += "These files must be moved to program partition:\n"
            for violation in violations['programs_in_data']:
                report += f"  - {violation}\n"
            report += f"Correct location: {self.paths.program_root}\n\n"

        report += "ARCHITECTURAL REMINDER:\n"
        report += "- ALL business data, logs, outputs, configs -> data partition\n"
        report += "- ALL executable code, scripts, modules -> program partition\n"
        report += "- Use data_paths.py for all file operations\n"

        return report

    def check_compliance(self) -> bool:
        """Return True if partition separation is compliant, False otherwise."""
        violations = self.validate_partitions()
        return len(violations['data_in_program']) == 0 and len(violations['programs_in_data']) == 0