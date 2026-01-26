# Path: verification/output/report_generator.py
"""
Report Generator for Verification Module

Creates comprehensive verification report files:
- report.json: Combined verification report (all sources)
- report_xbrl.json: XBRL-sourced verification results (company formulas)
- report_taxonomy.json: Taxonomy-sourced verification results (standard formulas)
"""

import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..core.config_loader import ConfigLoader
from ..engine.coordinator import VerificationResult
from ..engine.checks.horizontal_checker import CheckResult
from ..constants import (
    LOG_OUTPUT,
    REPORT_FILE,
    REPORT_XBRL_FILE,
    REPORT_TAXONOMY_FILE,
)


class ReportGenerator:
    """
    Creates verification report JSON files.

    Generates comprehensive reports including:
    - Filing information
    - Verification scores
    - Quality classification
    - Detailed check results
    - Issues summary
    - Recommendations

    Also generates separate reports for XBRL-sourced and taxonomy-sourced
    verification results.

    Example:
        generator = ReportGenerator()
        paths = generator.generate_all_reports(verification_result)
        for path in paths:
            print(f"Report saved to: {path}")
    """

    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize report generator.

        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        self.output_dir = self.config.get('output_dir')
        self.logger = logging.getLogger('output.report_generator')

    def generate_all_reports(
        self,
        result: VerificationResult,
        output_dir: Optional[Path] = None
    ) -> dict[str, Path]:
        """
        Generate all verification reports (combined, XBRL, taxonomy).

        Args:
            result: VerificationResult from coordinator
            output_dir: Optional custom output directory

        Returns:
            Dictionary mapping report type to file path
        """
        paths = {}

        # Determine output directory
        if output_dir is None:
            output_dir = self._get_default_output_dir(result)

        # Generate combined report
        combined_path = self.generate_report(result, output_dir / REPORT_FILE)
        paths['combined'] = combined_path

        # Generate XBRL-sourced report (if there are XBRL results)
        if result.xbrl_calculation_results:
            xbrl_path = self.generate_xbrl_report(result, output_dir / REPORT_XBRL_FILE)
            paths['xbrl'] = xbrl_path
        else:
            self.logger.info(f"{LOG_OUTPUT} No XBRL calculation results - skipping report_xbrl.json")

        # Generate taxonomy-sourced report (if there are taxonomy results)
        if result.taxonomy_calculation_results:
            taxonomy_path = self.generate_taxonomy_report(result, output_dir / REPORT_TAXONOMY_FILE)
            paths['taxonomy'] = taxonomy_path
        else:
            self.logger.info(f"{LOG_OUTPUT} No taxonomy calculation results - skipping report_taxonomy.json")

        return paths

    def generate_report(
        self,
        result: VerificationResult,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Generate combined verification report JSON.

        Args:
            result: VerificationResult from coordinator
            output_path: Optional custom output path

        Returns:
            Path to generated report file
        """
        self.logger.info(f"{LOG_OUTPUT} Generating combined report for {result.filing_id}")

        # Determine output path
        if output_path is None:
            output_path = self._get_default_output_path(result, REPORT_FILE)

        # Build report structure
        report = self._build_report(result)

        # Write report
        self._write_report(report, output_path)

        self.logger.info(f"{LOG_OUTPUT} Combined report saved to: {output_path}")

        return output_path

    def generate_xbrl_report(
        self,
        result: VerificationResult,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Generate XBRL-sourced verification report.

        Contains only results from company XBRL calculation linkbase.

        Args:
            result: VerificationResult from coordinator
            output_path: Optional custom output path

        Returns:
            Path to generated report file
        """
        self.logger.info(f"{LOG_OUTPUT} Generating XBRL report for {result.filing_id}")

        # Determine output path
        if output_path is None:
            output_path = self._get_default_output_path(result, REPORT_XBRL_FILE)

        # Build XBRL-specific report
        report = self._build_xbrl_report(result)

        # Write report
        self._write_report(report, output_path)

        self.logger.info(f"{LOG_OUTPUT} XBRL report saved to: {output_path}")

        return output_path

    def generate_taxonomy_report(
        self,
        result: VerificationResult,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Generate taxonomy-sourced verification report.

        Contains only results from standard taxonomy calculation linkbase.

        Args:
            result: VerificationResult from coordinator
            output_path: Optional custom output path

        Returns:
            Path to generated report file
        """
        self.logger.info(f"{LOG_OUTPUT} Generating taxonomy report for {result.filing_id}")

        # Determine output path
        if output_path is None:
            output_path = self._get_default_output_path(result, REPORT_TAXONOMY_FILE)

        # Build taxonomy-specific report
        report = self._build_taxonomy_report(result)

        # Write report
        self._write_report(report, output_path)

        self.logger.info(f"{LOG_OUTPUT} Taxonomy report saved to: {output_path}")

        return output_path

    def _get_default_output_dir(self, result: VerificationResult) -> Path:
        """Get default output directory for reports."""
        if not self.output_dir:
            raise ValueError("Output directory not configured")

        # Create directory structure: output_dir/market/company/form/date/
        report_dir = (
            self.output_dir /
            result.market /
            result.company /
            result.form /
            result.date
        )
        report_dir.mkdir(parents=True, exist_ok=True)

        return report_dir

    def _get_default_output_path(self, result: VerificationResult, filename: str) -> Path:
        """Get default output path for a specific report file."""
        report_dir = self._get_default_output_dir(result)
        return report_dir / filename

    def _build_report(self, result: VerificationResult) -> dict:
        """Build combined report dictionary from verification result."""
        report = {
            'report_type': 'combined',
            'filing_info': {
                'filing_id': result.filing_id,
                'market': result.market,
                'company': result.company,
                'form': result.form,
                'date': result.date,
            },
            'verification_timestamp': result.verified_at.isoformat() if result.verified_at else None,
            'processing_time_seconds': result.processing_time_seconds,
        }

        # Add scores
        if result.scores:
            report['scores'] = {
                'horizontal_score': round(result.scores.horizontal_score, 2),
                'vertical_score': round(result.scores.vertical_score, 2),
                'library_score': round(result.scores.library_score, 2),
                'overall_score': round(result.scores.overall_score, 2),
            }

            report['check_counts'] = {
                'horizontal_checks': result.scores.horizontal_checks,
                'vertical_checks': result.scores.vertical_checks,
                'library_checks': result.scores.library_checks,
            }

        # Add quality classification
        if result.quality:
            report['quality'] = {
                'level': result.quality.level,
                'description': result.quality.description,
                'confidence': round(result.quality.confidence, 2),
            }

        # Add issues summary
        report['issues_summary'] = result.issues_summary

        # Add recommendation
        report['recommendation'] = result.recommendation

        # Add statement information
        if result.statement_info:
            report['statement_info'] = result.statement_info

        # Add taxonomy status
        if result.taxonomy_status:
            report['taxonomy_status'] = result.taxonomy_status

        # Add formula registry summary
        if result.formula_registry_summary:
            report['formula_registry_summary'] = result.formula_registry_summary

        # Add detailed check results
        report['check_results'] = {
            'horizontal': self._serialize_check_results(result.horizontal_results),
            'vertical': self._serialize_check_results(result.vertical_results),
            'library': self._serialize_check_results(result.library_results),
        }

        return report

    def _build_xbrl_report(self, result: VerificationResult) -> dict:
        """Build XBRL-sourced report dictionary."""
        report = {
            'report_type': 'xbrl',
            'verification_source': 'company_xbrl',
            'description': 'Verification results using company XBRL calculation linkbase',
            'filing_info': {
                'filing_id': result.filing_id,
                'market': result.market,
                'company': result.company,
                'form': result.form,
                'date': result.date,
            },
            'verification_timestamp': result.verified_at.isoformat() if result.verified_at else None,
        }

        # Add formula registry info for XBRL
        if result.formula_registry_summary:
            report['formula_source'] = {
                'company_trees': result.formula_registry_summary.get('company_trees', 0),
                'company_roles': result.formula_registry_summary.get('company_roles', []),
            }

        # Calculate XBRL-specific stats
        xbrl_results = result.xbrl_calculation_results
        if xbrl_results:
            passed = sum(1 for r in xbrl_results if r.passed)
            failed = sum(1 for r in xbrl_results if not r.passed)
            total = len(xbrl_results)

            report['summary'] = {
                'total_checks': total,
                'passed': passed,
                'failed': failed,
                'pass_rate': round(passed / total * 100, 2) if total > 0 else 0.0,
            }

        # Add detailed XBRL check results
        report['calculation_results'] = self._serialize_check_results(xbrl_results)

        return report

    def _build_taxonomy_report(self, result: VerificationResult) -> dict:
        """Build taxonomy-sourced report dictionary."""
        report = {
            'report_type': 'taxonomy',
            'verification_source': 'standard_taxonomy',
            'description': 'Verification results using standard taxonomy calculation linkbase',
            'filing_info': {
                'filing_id': result.filing_id,
                'market': result.market,
                'company': result.company,
                'form': result.form,
                'date': result.date,
            },
            'verification_timestamp': result.verified_at.isoformat() if result.verified_at else None,
        }

        # Add formula registry info for taxonomy
        if result.formula_registry_summary:
            report['formula_source'] = {
                'taxonomy_trees': result.formula_registry_summary.get('taxonomy_trees', 0),
                'taxonomy_roles': result.formula_registry_summary.get('taxonomy_roles', []),
                'taxonomy_id': result.formula_registry_summary.get('taxonomy_id'),
            }

        # Calculate taxonomy-specific stats
        taxonomy_results = result.taxonomy_calculation_results
        if taxonomy_results:
            passed = sum(1 for r in taxonomy_results if r.passed)
            failed = sum(1 for r in taxonomy_results if not r.passed)
            total = len(taxonomy_results)

            report['summary'] = {
                'total_checks': total,
                'passed': passed,
                'failed': failed,
                'pass_rate': round(passed / total * 100, 2) if total > 0 else 0.0,
            }

        # Add detailed taxonomy check results
        report['calculation_results'] = self._serialize_check_results(taxonomy_results)

        return report

    def _serialize_check_results(self, results: list[CheckResult]) -> list[dict]:
        """Convert check results to serializable format."""
        serialized = []

        for result in results:
            item = {
                'check_name': result.check_name,
                'check_type': result.check_type,
                'passed': result.passed,
                'severity': result.severity,
                'message': result.message,
            }

            if result.expected_value is not None:
                item['expected_value'] = result.expected_value

            if result.actual_value is not None:
                item['actual_value'] = result.actual_value

            if result.difference is not None:
                item['difference'] = result.difference

            if result.details:
                item['details'] = result.details

            serialized.append(item)

        return serialized

    def _write_report(self, report: dict, output_path: Path) -> None:
        """Write report to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)


__all__ = ['ReportGenerator']
