"""
Map Pro File Size Monitor
Enforces the mandatory 500-line limit for all Python files
"""

from pathlib import Path
from typing import List, Tuple
from core.data_paths import map_pro_paths


class FileSizeChecker:
    def __init__(self):
        self.project_root = map_pro_paths.program_root
        self.max_lines = 500  
        
        # Directories to exclude from scanning
        self.excluded_dirs = {
            'venv',      # Virtual environment
            '.venv',     # Alternative venv name
            'env',       # Another common venv name
            '__pycache__',  # Python cache
            '.git',      # Git repository
            'build',     # Build artifacts
            'dist',      # Distribution files
            '.tox',      # Tox testing
            '.pytest_cache'  # Pytest cache
        }
    
    def scan_project(self) -> List[Tuple[str, int, int]]:
        """
        Scan all Python files for line count violations.
        
        Returns:
            List of tuples: (file_path, line_count, limit)
        """
        violations = []
        
        for py_file in self.project_root.rglob("*.py"):
            # Skip if file is in an excluded directory
            if self._is_excluded(py_file):
                continue
            
            line_count = self._count_lines(py_file)
            if line_count > self.max_lines:
                violations.append((str(py_file), line_count, self.max_lines))
        
        return violations
    
    def _is_excluded(self, file_path: Path) -> bool:
        """
        Check if file is in an excluded directory.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file should be excluded from scanning
        """
        # Get all parent directory names
        parts = file_path.relative_to(self.project_root).parts
        
        # Check if any excluded directory is in the path
        return any(excluded_dir in parts for excluded_dir in self.excluded_dirs)
    
    def _count_lines(self, file_path: Path) -> int:
        """Count non-empty lines in Python file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f.readlines()]
                return len([line for line in lines if line and not line.startswith('#')])
        except Exception:
            return 0
    
    def generate_report(self) -> str:
        """Generate violation report with splitting suggestions"""
        violations = self.scan_project()
        
        if not violations:
            return f"[OK] All Python files comply with {self.max_lines}-line limit"
        
        report = f"[WARNING] Found {len(violations)} files exceeding {self.max_lines}-line limit:\n\n"
        
        for file_path, line_count, limit in violations:
            excess_lines = line_count - limit
            suggested_splits = (excess_lines // 200) + 2
            
            report += f"File: {file_path}\n"
            report += f"Lines: {line_count} (exceeds by {excess_lines})\n"
            report += f"Suggestion: Split into {suggested_splits} files\n\n"
        
        return report