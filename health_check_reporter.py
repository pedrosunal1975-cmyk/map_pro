"""
Health Check Reporter
====================

File: tools/health_check_reporter.py

Generates and prints health check reports.
"""

from typing import Dict, List


class HealthCheckReporter:
    """
    Generate health check reports.
    
    Responsibilities:
    - Format issue information
    - Print comprehensive reports
    - Provide recommendations
    """
    
    def __init__(self, max_items: int = 5):
        """
        Initialize reporter.
        
        Args:
            max_items: Maximum items to show in detail per section
        """
        self.max_items = max_items
    
    def print_report(self, issues: Dict[str, List[Dict]]) -> None:
        """
        Print comprehensive health check report.
        
        Args:
            issues: Dictionary of issues found
        """
        print("\n" + "=" * 70)
        print("DATABASE HEALTH CHECK REPORT")
        print("=" * 70)
        
        total_issues = sum(len(v) for v in issues.values())
        
        if total_issues == 0:
            self._print_success_message()
            return
        
        print(f"\n[WARNING] Found {total_issues} total issues:\n")
        
        # Print parsed database issues
        self._print_parsed_issues(issues)
        
        # Print mapped database issues
        self._print_mapped_issues(issues)
        
        # Print recommendations
        self._print_recommendations()
    
    def _print_success_message(self) -> None:
        """Print success message when no issues found."""
        print("\n[OK] No issues found! Database and filesystem are synchronized.")
    
    def _print_parsed_issues(self, issues: Dict[str, List[Dict]]) -> None:
        """
        Print parsed database issues.
        
        Args:
            issues: Dictionary of issues
        """
        if issues.get('missing_parsed_records'):
            self._print_missing_parsed_records(
                issues['missing_parsed_records']
            )
        
        if issues.get('phantom_parsed_records'):
            self._print_phantom_parsed_records(
                issues['phantom_parsed_records']
            )
        
        if issues.get('path_mismatches'):
            self._print_path_mismatches(issues['path_mismatches'])
    
    def _print_missing_parsed_records(
        self,
        missing_records: List[Dict]
    ) -> None:
        """
        Print missing parsed records section.
        
        Args:
            missing_records: List of missing record issues
        """
        print(f"[PARSED DB] Missing Records: {len(missing_records)}")
        print("  Files exist in filesystem but no database record:")
        
        for issue in missing_records[:self.max_items]:
            print(f"    - {issue['company']} ({issue['filing_type']})")
            print(f"      Filing ID: {issue['filing_id']}")
            print(f"      File: {issue['file_path']}")
        
        if len(missing_records) > self.max_items:
            remaining = len(missing_records) - self.max_items
            print(f"    ... and {remaining} more")
        
        print()
    
    def _print_phantom_parsed_records(
        self,
        phantom_records: List[Dict]
    ) -> None:
        """
        Print phantom parsed records section.
        
        Args:
            phantom_records: List of phantom record issues
        """
        print(f"[PARSED DB] Phantom Records: {len(phantom_records)}")
        print("  Database records exist but files are missing:")
        
        for issue in phantom_records[:self.max_items]:
            print(f"    - {issue['document_name']}")
            print(f"      Record ID: {issue['record_id']}")
            print(f"      Missing File: {issue['missing_file']}")
        
        if len(phantom_records) > self.max_items:
            remaining = len(phantom_records) - self.max_items
            print(f"    ... and {remaining} more")
        
        print()
    
    def _print_path_mismatches(self, path_mismatches: List[Dict]) -> None:
        """
        Print path mismatches section.
        
        Args:
            path_mismatches: List of path mismatch issues
        """
        print(f"[PARSED DB] Path Mismatches: {len(path_mismatches)}")
        print("  Database paths don't match filesystem:")
        
        display_count = min(3, len(path_mismatches))
        
        for issue in path_mismatches[:display_count]:
            print(f"    - Filing ID: {issue['filing_id']}")
            print(f"      DB Path: {issue['db_path']}")
            print(f"      File Path: {issue['file_path']}")
        
        if len(path_mismatches) > display_count:
            remaining = len(path_mismatches) - display_count
            print(f"    ... and {remaining} more")
        
        print()
    
    def _print_mapped_issues(self, issues: Dict[str, List[Dict]]) -> None:
        """
        Print mapped database issues.
        
        Args:
            issues: Dictionary of issues
        """
        if issues.get('missing_mapped_records'):
            print(
                f"[MAPPED DB] Missing Records: "
                f"{len(issues['missing_mapped_records'])}"
            )
            print("  Statement files exist but no database records")
            print()
        
        if issues.get('phantom_mapped_records'):
            print(
                f"[MAPPED DB] Phantom Records: "
                f"{len(issues['phantom_mapped_records'])}"
            )
            print("  Database records exist but files are missing")
            print()
    
    def _print_recommendations(self) -> None:
        """Print recommendations section."""
        print("=" * 70)
        print("\nRECOMMENDATIONS:")
        print("  1. Run with --repair to fix these issues")
        print("  2. After repair, run --check again to verify")
        print("  3. Use --stats to see overall database statistics")
        print("=" * 70 + "\n")