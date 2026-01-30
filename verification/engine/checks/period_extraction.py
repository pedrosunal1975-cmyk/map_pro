# Path: verification/engine/checks/period_extraction.py
"""
Period Extraction from XBRL Context IDs

Extracts period information from context_id strings for period matching
and compatibility checks.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

from .constants import (
    DIMENSIONAL_CONTEXT_INDICATORS,
    PERIOD_TYPE_INDICATORS,
    DATE_COMPONENT_PATTERNS,
    PERIOD_EXTRACTION_PATTERNS,
)


# Configuration constants
REGEX_YEAR_PATTERN = r'\d{4}'  # Pattern for extracting 4-digit years
REGEX_FLAGS = re.IGNORECASE  # Case-insensitive pattern matching


@dataclass
class PeriodInfo:
    """
    Extracted period information from a context_id.

    Attributes:
        period_type: 'duration', 'instant', or 'unknown'
        start_date: Start date as 'YYYY-MM-DD' (for duration) or None
        end_date: End date as 'YYYY-MM-DD' (for duration/instant)
        year: Year only if full date not extractable
        period_key: Normalized key for comparison (e.g., 'd_2024-01-01_2024-12-31')
        raw_match: The raw string that matched the pattern
    """
    period_type: str = 'unknown'
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    year: Optional[str] = None
    period_key: str = ''
    raw_match: str = ''


class PeriodExtractor:
    """
    Extract period information from context_id strings.

    Context IDs encode period information in various formats depending on
    the XBRL processor and market. This class uses patterns from constants.py
    to extract period data in a market-agnostic way.

    Example:
        extractor = PeriodExtractor()

        # Duration context
        period = extractor.extract('Duration_1_1_2024_To_12_31_2024_abc123')
        # -> PeriodInfo(period_type='duration', start_date='2024-01-01',
        #               end_date='2024-12-31', period_key='d_2024-01-01_2024-12-31')

        # Instant context
        period = extractor.extract('AsOf_12_31_2024_xyz789')
        # -> PeriodInfo(period_type='instant', end_date='2024-12-31',
        #               period_key='i_2024-12-31')
    """

    def __init__(self):
        self.logger = logging.getLogger('process.period_extractor')
        self._compiled_patterns = self._compile_patterns()

    def _compile_patterns(self) -> list[tuple[str, re.Pattern, list[str]]]:
        """
        Compile regex patterns from constants.py templates.

        Substitutes placeholders with actual regex fragments.
        """
        compiled = []

        # Build substitution map from DATE_COMPONENT_PATTERNS
        subs = {
            'sep': DATE_COMPONENT_PATTERNS['separator'],
            'month': DATE_COMPONENT_PATTERNS['month'],
            'day': DATE_COMPONENT_PATTERNS['day'],
            'year': DATE_COMPONENT_PATTERNS['year'],
            'range': DATE_COMPONENT_PATTERNS['range_indicator'],
        }

        for name, template, groups in PERIOD_EXTRACTION_PATTERNS:
            # Substitute placeholders
            pattern_str = template.format(**subs)

            try:
                pattern = re.compile(pattern_str, REGEX_FLAGS)
                compiled.append((name, pattern, groups))
            except re.error as e:
                self.logger.warning(f"Failed to compile pattern '{name}': {e}")

        return compiled

    def extract(self, context_id: str) -> PeriodInfo:
        """
        Extract period information from a context_id.

        Args:
            context_id: The XBRL context identifier

        Returns:
            PeriodInfo with extracted period data
        """
        if not context_id:
            return PeriodInfo()

        context_lower = context_id.lower()

        # Determine period type from indicators
        period_type = self._detect_period_type(context_lower)

        # Try each pattern until one matches
        for name, pattern, groups in self._compiled_patterns:
            match = pattern.search(context_lower)
            if match:
                return self._build_period_info(name, match, groups, period_type)

        # No pattern matched - return unknown with any year found
        years = re.findall(REGEX_YEAR_PATTERN, context_id)
        if years:
            # Use unique years, sorted
            unique_years = sorted(set(years))
            return PeriodInfo(
                period_type='unknown',
                year=unique_years[0],
                period_key=f"y_{'_'.join(unique_years)}",
                raw_match=context_id,
            )

        return PeriodInfo(raw_match=context_id)

    def _detect_period_type(self, context_lower: str) -> str:
        """Detect period type from context_id using indicators from constants."""
        for indicator, ptype in PERIOD_TYPE_INDICATORS:
            if indicator in context_lower:
                return ptype
        return 'unknown'

    def _build_period_info(
        self,
        pattern_name: str,
        match: re.Match,
        groups: list[str],
        period_type: str
    ) -> PeriodInfo:
        """
        Build PeriodInfo from a regex match.

        Args:
            pattern_name: Name of the pattern that matched
            match: The regex match object
            groups: List of group names for extraction
            period_type: Detected period type

        Returns:
            PeriodInfo with extracted data
        """
        # Extract matched groups
        extracted = {}
        for i, group_name in enumerate(groups):
            if i + 1 <= len(match.groups()):
                extracted[group_name] = match.group(i + 1)

        # Build dates based on pattern type
        if pattern_name.startswith('duration'):
            # Duration pattern - extract start and end dates
            start_date = self._format_date(
                extracted.get('start_year'),
                extracted.get('start_month'),
                extracted.get('start_day')
            )
            end_date = self._format_date(
                extracted.get('end_year'),
                extracted.get('end_month'),
                extracted.get('end_day')
            )
            period_key = f"d_{start_date}_{end_date}" if start_date and end_date else ''

            return PeriodInfo(
                period_type='duration',
                start_date=start_date,
                end_date=end_date,
                year=extracted.get('end_year'),
                period_key=period_key,
                raw_match=match.group(0),
            )

        elif pattern_name.startswith('instant'):
            # Instant pattern - extract single date
            end_date = self._format_date(
                extracted.get('year'),
                extracted.get('month'),
                extracted.get('day')
            )
            period_key = f"i_{end_date}" if end_date else ''

            return PeriodInfo(
                period_type='instant',
                end_date=end_date,
                year=extracted.get('year'),
                period_key=period_key,
                raw_match=match.group(0),
            )

        elif pattern_name == 'year_only':
            # Year-only fallback
            year = extracted.get('year')
            return PeriodInfo(
                period_type=period_type,
                year=year,
                period_key=f"y_{year}" if year else '',
                raw_match=match.group(0),
            )

        return PeriodInfo(period_type=period_type, raw_match=match.group(0))

    def _format_date(
        self,
        year: Optional[str],
        month: Optional[str],
        day: Optional[str]
    ) -> Optional[str]:
        """
        Format date components into YYYY-MM-DD string.

        Args:
            year: Year string
            month: Month string (1-12 or 01-12)
            day: Day string (1-31 or 01-31)

        Returns:
            Formatted date string or None if components missing
        """
        if not all([year, month, day]):
            return None

        try:
            # Pad month and day to 2 digits
            month_int = int(month)
            day_int = int(day)

            return f"{year}-{month_int:02d}-{day_int:02d}"
        except (ValueError, TypeError):
            return None


__all__ = [
    'PeriodInfo',
    'PeriodExtractor',
    'REGEX_YEAR_PATTERN',
    'REGEX_FLAGS',
]
