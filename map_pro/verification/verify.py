#!/usr/bin/env python3
# Path: verification/verify.py
"""
Verification Module CLI

Main entry point for the verification module.
Validates mapped financial statements for quality assessment.

Usage:
    python verify.py

The CLI will:
1. Show available companies with mapped statements
2. Allow selection of filing to verify
3. Run verification checks
4. Display results and save reports
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from verification.core.config_loader import ConfigLoader
from verification.core.data_paths import ensure_data_paths
from verification.engine.coordinator import VerificationCoordinator, VerificationResult
from verification.loaders.mapped_data import MappedDataLoader, MappedFilingEntry
from verification.loaders.mapped_reader import MappedReader
from verification.output.report_generator import ReportGenerator
from verification.output.summary_exporter import SummaryExporter
from verification.output.statement_simplifier import StatementSimplifier


class VerificationCLI:
    """
    Command-line interface for verification module.

    Provides interactive selection and verification of mapped filings.
    """

    def __init__(self):
        """Initialize CLI components."""
        self.config = ConfigLoader()
        self.coordinator = VerificationCoordinator(self.config)
        self.report_generator = ReportGenerator(self.config)
        self.summary_exporter = SummaryExporter(self.config)
        self.simplifier = StatementSimplifier(self.config)
        self.mapped_reader = MappedReader()

    def run(self) -> None:
        """Run the verification CLI."""
        self._print_header()

        # Ensure directories exist
        ensure_data_paths()

        while True:
            # Get available filings
            filings = self.coordinator.get_available_filings()

            if not filings:
                print("\nNo mapped statements found.")
                print("Please run the mapper module first to create mapped statements.")
                break

            # Show menu
            selection = self._show_filing_menu(filings)

            if selection == 0:
                print("\nExiting verification module.")
                break

            if selection == -1:
                # Verify all
                self._verify_all(filings)
            elif 1 <= selection <= len(filings):
                # Verify selected filing
                filing = filings[selection - 1]
                self._verify_filing(filing)

            # Ask to continue
            if not self._ask_continue():
                print("\nExiting verification module.")
                break

    def _print_header(self) -> None:
        """Print CLI header."""
        sep = '=' * 60
        print(sep)
        print('VERIFICATION MODULE')
        print('Financial Statement Quality Assessment')
        print(sep)

    def _show_filing_menu(self, filings: list[MappedFilingEntry]) -> int:
        """
        Show filing selection menu.

        Args:
            filings: List of available filings

        Returns:
            Selected option number (0 to exit, -1 for all)
        """
        print('\nAvailable Companies with Mapped Statements:')
        print('-' * 50)

        for i, filing in enumerate(filings, 1):
            print(f'  {i:2}. {filing.market} | {filing.company} | {filing.form} | {filing.date}')

        print('-' * 50)
        print('  -1. Verify ALL filings')
        print('   0. Exit')
        print()

        while True:
            try:
                choice = input('Enter selection: ').strip()
                selection = int(choice)

                if selection == 0 or selection == -1:
                    return selection
                if 1 <= selection <= len(filings):
                    return selection

                print(f'Invalid selection. Please enter 0-{len(filings)} or -1.')

            except ValueError:
                print('Please enter a valid number.')

    def _verify_filing(self, filing: MappedFilingEntry) -> None:
        """
        Verify a single filing.

        Args:
            filing: Filing to verify
        """
        sep = '=' * 60

        print(f'\n{sep}')
        print(f'VERIFYING: {filing.company} | {filing.form} | {filing.date}')
        print(sep)

        # Run verification
        result = self.coordinator.verify_filing(filing)

        # Display results
        self._display_results(result)

        # Save outputs
        self._save_outputs(filing, result)

    def _verify_all(self, filings: list[MappedFilingEntry]) -> None:
        """
        Verify all filings.

        Args:
            filings: List of filings to verify
        """
        print(f'\nVerifying {len(filings)} filings...\n')

        results = []
        for i, filing in enumerate(filings, 1):
            print(f'[{i}/{len(filings)}] {filing.company} | {filing.form}...')

            result = self.coordinator.verify_filing(filing)
            results.append(result)

            # Save outputs
            self._save_outputs(filing, result, quiet=True)

            print(f'        Quality: {result.quality.level if result.quality else "N/A"} '
                  f'(Score: {result.scores.overall_score:.1f})')

        # Show summary
        self._display_batch_summary(results)

    def _display_results(self, result: VerificationResult) -> None:
        """Display verification results."""
        sep = '=' * 60

        print(f'\n{sep}')
        print('VERIFICATION RESULTS')
        print(sep)

        # Scores
        if result.scores:
            print(f'Horizontal Score: {result.scores.horizontal_score:6.1f}/100')
            print(f'Vertical Score:   {result.scores.vertical_score:6.1f}/100')
            print(f'Library Score:    {result.scores.library_score:6.1f}/100')
            print(f'Overall Score:    {result.scores.overall_score:6.1f}/100')
            print()

        # Quality
        if result.quality:
            print(f'Quality Level: {result.quality.level}')
            print(f'               {result.quality.description}')
            print()

        # Issues
        if result.issues_summary:
            print('Issues Found:')
            critical = result.issues_summary.get('critical', 0)
            warnings = result.issues_summary.get('warnings', 0)
            info = result.issues_summary.get('info', 0)

            if critical > 0:
                print(f'  - CRITICAL: {critical}')
            if warnings > 0:
                print(f'  - Warnings: {warnings}')
            if info > 0:
                print(f'  - Info:     {info}')

            if critical == 0 and warnings == 0:
                print('  No significant issues found.')

            print()

        # Failed checks
        failed = self._get_failed_checks(result)
        if failed:
            print('Failed Checks:')
            for check in failed[:5]:
                print(f'  - [{check.severity.upper()}] {check.message}')
            if len(failed) > 5:
                print(f'  ... and {len(failed) - 5} more')
            print()

        # Recommendation
        print(f'Recommendation: {result.recommendation}')
        print(sep)

    def _display_batch_summary(self, results: list[VerificationResult]) -> None:
        """Display summary of batch verification."""
        sep = '=' * 60

        print(f'\n{sep}')
        print('BATCH VERIFICATION SUMMARY')
        print(sep)

        print(f'Total filings verified: {len(results)}')
        print()

        # Count by quality level
        quality_counts = {}
        for result in results:
            level = result.quality.level if result.quality else 'UNKNOWN'
            quality_counts[level] = quality_counts.get(level, 0) + 1

        print('By Quality Level:')
        for level, count in sorted(quality_counts.items()):
            print(f'  {level}: {count}')

        print()

        # Average score
        scores = [r.scores.overall_score for r in results if r.scores]
        if scores:
            avg_score = sum(scores) / len(scores)
            print(f'Average Overall Score: {avg_score:.1f}/100')

        print(sep)

    def _save_outputs(
        self,
        filing: MappedFilingEntry,
        result: VerificationResult,
        quiet: bool = False
    ) -> None:
        """
        Save verification outputs.

        Args:
            filing: Filing that was verified
            result: Verification result
            quiet: If True, don't print output paths
        """
        # Generate report
        report_path = self.report_generator.generate_report(result)
        if not quiet:
            print(f'\n[OUTPUT] Report saved: {report_path}')

        # Generate summary
        summary_path = self.summary_exporter.export_summary(result)
        if not quiet:
            print(f'[OUTPUT] Summary saved: {summary_path}')

        # Ask about simplified statements
        if not quiet:
            if self._ask_yes_no('\nGenerate simplified statements?'):
                statements = self.mapped_reader.read_statements(filing)
                if statements:
                    paths = self.simplifier.export_simplified(filing, statements)
                    print(f'[OUTPUT] Simplified statements saved: {len(paths)} files')

    def _get_failed_checks(self, result: VerificationResult) -> list:
        """Get failed checks sorted by severity."""
        failed = []

        for check in result.horizontal_results:
            if not check.passed:
                failed.append(check)

        for check in result.vertical_results:
            if not check.passed:
                failed.append(check)

        for check in result.library_results:
            if not check.passed:
                failed.append(check)

        severity_order = {'critical': 0, 'warning': 1, 'info': 2}
        failed.sort(key=lambda c: severity_order.get(c.severity, 3))

        return failed

    def _ask_continue(self) -> bool:
        """Ask if user wants to continue."""
        return self._ask_yes_no('\nVerify another filing?')

    def _ask_yes_no(self, prompt: str) -> bool:
        """Ask a yes/no question."""
        while True:
            response = input(f'{prompt} [y/n]: ').strip().lower()
            if response in ['y', 'yes']:
                return True
            if response in ['n', 'no']:
                return False
            print('Please enter y or n.')


def main():
    """Main entry point."""
    try:
        cli = VerificationCLI()
        cli.run()
    except KeyboardInterrupt:
        print('\n\nVerification cancelled.')
        sys.exit(0)
    except Exception as e:
        print(f'\nError: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
