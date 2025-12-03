"""
Performance Reporter
===================

File: tools/monitoring/performance_reporter.py

Generates formatted performance reports.
"""

from typing import Dict, Any, List


class PerformanceReporter:
    """
    Generate performance reports.
    
    Responsibilities:
    - Format analysis data into readable reports
    - Generate engine comparison reports
    - Create summary statistics
    """
    
    def generate_report(self, analysis: Dict[str, Any]) -> str:
        """
        Generate comprehensive performance report.
        
        Args:
            analysis: Performance analysis results
            
        Returns:
            Formatted performance report string
        """
        report_lines = []
        
        # Header
        report_lines.extend(self._generate_header(analysis))
        
        # Job Statistics
        report_lines.extend(self._generate_job_statistics(analysis))
        
        # Engine Performance
        report_lines.extend(self._generate_engine_performance(analysis))
        
        # Bottlenecks
        report_lines.extend(self._generate_bottlenecks(analysis))
        
        # Recommendations
        report_lines.extend(self._generate_recommendations(analysis))
        
        # Footer
        report_lines.append("=" * 70)
        
        return '\n'.join(report_lines)
    
    def _generate_header(self, analysis: Dict[str, Any]) -> List[str]:
        """
        Generate report header.
        
        Args:
            analysis: Performance analysis results
            
        Returns:
            List of header lines
        """
        return [
            "=" * 70,
            "MAP PRO PERFORMANCE ANALYSIS REPORT",
            f"Generated: {analysis['timestamp']}",
            f"Analysis Window: {analysis['window_hours']} hours",
            "=" * 70,
            ""
        ]
    
    def _generate_job_statistics(self, analysis: Dict[str, Any]) -> List[str]:
        """
        Generate job statistics section.
        
        Args:
            analysis: Performance analysis results
            
        Returns:
            List of statistics lines
        """
        job_stats = analysis.get('job_statistics', {})
        
        return [
            "JOB STATISTICS:",
            f"  Total Jobs:    {job_stats.get('total_jobs', 0)}",
            f"  Completed:     {job_stats.get('completed', 0)}",
            f"  Failed:        {job_stats.get('failed', 0)}",
            f"  Running:       {job_stats.get('running', 0)}",
            f"  Queued:        {job_stats.get('queued', 0)}",
            f"  Success Rate:  {job_stats.get('success_rate', 0)*100:.2f}%",
            ""
        ]
    
    def _generate_engine_performance(self, analysis: Dict[str, Any]) -> List[str]:
        """
        Generate engine performance section.
        
        Args:
            analysis: Performance analysis results
            
        Returns:
            List of engine performance lines
        """
        lines = ["ENGINE PERFORMANCE:"]
        
        engine_perf = analysis.get('engine_performance', {})
        for engine_name, engine_data in engine_perf.items():
            overall = engine_data.get('overall', {})
            lines.extend([
                f"  {engine_name.upper()}:",
                f"    Jobs Completed:    {overall.get('total_jobs_completed', 0)}",
                f"    Avg Process Time:  {overall.get('average_processing_time', 'N/A')}s",
                f"    Failure Rate:      {overall.get('average_failure_rate', 0)*100:.2f}%"
            ])
        
        lines.append("")
        return lines
    
    def _generate_bottlenecks(self, analysis: Dict[str, Any]) -> List[str]:
        """
        Generate bottlenecks section.
        
        Args:
            analysis: Performance analysis results
            
        Returns:
            List of bottleneck lines
        """
        bottlenecks = analysis.get('bottlenecks', [])
        
        if bottlenecks:
            lines = ["BOTTLENECKS DETECTED:"]
            for bottleneck in bottlenecks:
                lines.append(
                    f"  [{bottleneck['severity'].upper()}] "
                    f"{bottleneck['description']}"
                )
        else:
            lines = ["BOTTLENECKS: None detected"]
        
        lines.append("")
        return lines
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """
        Generate recommendations section.
        
        Args:
            analysis: Performance analysis results
            
        Returns:
            List of recommendation lines
        """
        lines = ["RECOMMENDATIONS:"]
        
        for rec in analysis.get('recommendations', []):
            lines.append(f"  * {rec}")
        
        lines.append("")
        return lines
    
    def generate_engine_comparison(
        self,
        engine_perf: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare performance across all engines.
        
        Args:
            engine_perf: Engine performance data
            
        Returns:
            Dictionary with comparative engine metrics
        """
        comparison = {
            'engines': {},
            'fastest': None,
            'slowest': None,
            'most_reliable': None,
            'least_reliable': None
        }
        
        # Extract key metrics for comparison
        for engine_name, engine_data in engine_perf.items():
            overall = engine_data.get('overall', {})
            comparison['engines'][engine_name] = {
                'avg_time': overall.get('average_processing_time'),
                'failure_rate': overall.get('average_failure_rate', 0),
                'jobs_completed': overall.get('total_jobs_completed', 0)
            }
        
        # Find fastest/slowest (by processing time)
        valid_engines = {
            k: v for k, v in comparison['engines'].items()
            if v['avg_time'] is not None
        }
        
        if valid_engines:
            comparison['fastest'] = min(
                valid_engines.items(),
                key=lambda x: x[1]['avg_time']
            )[0]
            comparison['slowest'] = max(
                valid_engines.items(),
                key=lambda x: x[1]['avg_time']
            )[0]
        
        # Find most/least reliable (by failure rate)
        if comparison['engines']:
            comparison['most_reliable'] = min(
                comparison['engines'].items(),
                key=lambda x: x[1]['failure_rate']
            )[0]
            
            comparison['least_reliable'] = max(
                comparison['engines'].items(),
                key=lambda x: x[1]['failure_rate']
            )[0]
        
        return comparison