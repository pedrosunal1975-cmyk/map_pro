"""
Engine Display Formatting.

Consistent console output formatting for engine commands.

Location: tools/cli/engine_display.py
"""

from typing import Dict, Any, List


class ExitCode:
    """Standard exit codes for CLI operations."""
    SUCCESS = 0
    ERROR = 1
    PARTIAL_SUCCESS = 2
    ENGINE_NOT_FOUND = 10
    ALREADY_RUNNING = 11
    NOT_AVAILABLE = 12


class ConsoleFormatter:
    """Consistent console output formatting."""
    
    @staticmethod
    def success(message: str) -> str:
        """Format success message."""
        return f"[OK] {message}"
    
    @staticmethod
    def error(message: str) -> str:
        """Format error message."""
        return f"[FAIL] {message}"
    
    @staticmethod
    def warning(message: str) -> str:
        """Format warning message."""
        return f"[WARNING]  {message}"
    
    @staticmethod
    def info(message: str) -> str:
        """Format info message."""
        return f"[INFO]️  {message}"
    
    @staticmethod
    def header(message: str) -> str:
        """Format section header."""
        return f"\n[STATS] {message}"
    
    @staticmethod
    def separator(length: int = 50) -> str:
        """Format separator line."""
        return "  " + "-" * length
    
    @staticmethod
    def status_icon(running: bool) -> str:
        """Get status icon for running state."""
        return "[OK]" if running else "[FAIL]"
    
    @staticmethod
    def health_icon(healthy: bool) -> str:
        """Get health icon."""
        return "[OK]" if healthy else "[WARNING]"


class EngineDisplay:
    """Display formatting for engine information."""
    
    def __init__(self):
        """Initialize engine display."""
        self.formatter = ConsoleFormatter()
    
    def print_engine_list(self, engines: List[str], status_map: Dict[str, Dict[str, Any]]) -> None:
        """
        Print list of engines with status.
        
        Args:
            engines: List of engine names
            status_map: Dictionary mapping engine names to status
        """
        print(self.formatter.header("Available Engines:"))
        
        for engine_name in engines:
            status = status_map.get(engine_name, {})
            running = status.get('running', False)
            active_jobs = status.get('active_jobs', 0)
            status_text = status.get('status', 'unknown')
            
            icon = self.formatter.status_icon(running)
            print(f"  {icon} {engine_name.upper()}")
            print(f"      Status: {status_text}")
            print(f"      Jobs: {active_jobs} active")
    
    def print_engine_status(self, engine_name: str, status: Dict[str, Any]) -> None:
        """
        Print detailed engine status.
        
        Args:
            engine_name: Engine name
            status: Status dictionary
        """
        running = status.get('running', False)
        icon = self.formatter.status_icon(running)
        
        print(f"\n  {icon} {engine_name.upper()}")
        print(f"      Running: {running}")
        print(f"      Status: {status.get('status', 'unknown')}")
        print(f"      Active Jobs: {status.get('active_jobs', 0)}")
        print(f"      Completed: {status.get('completed_jobs', 0)}")
        print(f"      Failed: {status.get('failed_jobs', 0)}")
    
    def print_health_status(self, engine_name: str, health: Dict[str, Any]) -> None:
        """
        Print engine health status.
        
        Args:
            engine_name: Engine name
            health: Health dictionary
        """
        healthy = health.get('healthy', False)
        icon = self.formatter.health_icon(healthy)
        
        print(f"\n  {icon} {engine_name.upper()}")
        print(f"      Health: {health.get('status', 'unknown')}")
        
        issues = health.get('issues', [])
        if issues:
            for issue in issues:
                print(f"      {self.formatter.warning(issue)}")
    
    def print_performance_metrics(self, engine_name: str, metrics: Dict[str, Any]) -> None:
        """
        Print performance metrics.
        
        Args:
            engine_name: Engine name
            metrics: Performance metrics dictionary
        """
        print(f"\n  ⚡ {engine_name.upper()}")
        print(f"      Throughput: {metrics.get('throughput', 0)} jobs/hour")
        print(f"      Avg Processing Time: {metrics.get('avg_time', 0):.2f}s")
        print(f"      Success Rate: {metrics.get('success_rate', 0):.1f}%")
    
    def print_jobs(self, engine_name: str, jobs: List[Dict[str, Any]], limit: int) -> None:
        """
        Print job list.
        
        Args:
            engine_name: Engine name
            jobs: List of job dictionaries
            limit: Display limit
        """
        print(self.formatter.header(f"Jobs for {engine_name} (limit: {limit}):"))
        
        if not jobs:
            print("  No jobs found")
            return
        
        print("  ID | Status | Created | Progress")
        print(self.formatter.separator())
        
        for job in jobs:
            job_id = job.get('id', 'N/A')[:8]  # Truncate ID
            status = job.get('status', 'unknown')
            created = job.get('created_at', 'N/A')
            progress = job.get('progress', 0)
            
            print(f"  {job_id} | {status:10s} | {created} | {progress}%")


class LibraryDisplay:
    """Display formatting for library information."""
    
    def __init__(self):
        """Initialize library display."""
        self.formatter = ConsoleFormatter()
    
    def print_analysis_results(self, result: Dict[str, Any]) -> None:
        """
        Print library dependency analysis results.
        
        Args:
            result: Analysis result dictionary
        """
        report = result.get('analysis_report', {})
        
        print(self.formatter.success("Analysis completed successfully"))
        print(self.formatter.header("Results:"))
        print(f"   Namespaces detected: {len(result.get('namespaces_detected', []))}")
        print(f"   Libraries required: {report.get('libraries_required_count', 0)}")
        print(f"   Libraries available: {report.get('available_count', 0)}")
        print(f"   Libraries downloaded: {report.get('downloaded_count', 0)}")
        print(f"   Failed downloads: {report.get('failed_count', 0)}")
        print(f"   Completion: {report.get('completion_percentage', 0):.1f}%")
        
        # Show manual downloads if needed
        manual_downloads = report.get('manual_downloads', [])
        if manual_downloads:
            print(self.formatter.warning("\nManual downloads required:"))
            for lib in manual_downloads:
                print(f"   - {lib.get('taxonomy_name', 'unknown')}-{lib.get('version', 'unknown')}")
        
        # Show recommendations
        recommendations = report.get('recommendations', [])
        if recommendations:
            print(self.formatter.info("\nRecommendations:"))
            for rec in recommendations:
                print(f"   * {rec}")


class MessageDisplay:
    """General message display utilities."""
    
    def __init__(self):
        """Initialize message display."""
        self.formatter = ConsoleFormatter()
    
    def success(self, message: str) -> None:
        """Print success message."""
        print(self.formatter.success(message))
    
    def error(self, message: str) -> None:
        """Print error message."""
        print(self.formatter.error(message))
    
    def warning(self, message: str) -> None:
        """Print warning message."""
        print(self.formatter.warning(message))
    
    def info(self, message: str) -> None:
        """Print info message."""
        print(self.formatter.info(message))


__all__ = [
    'ExitCode',
    'ConsoleFormatter',
    'EngineDisplay',
    'LibraryDisplay',
    'MessageDisplay'
]