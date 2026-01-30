# Path: verification/engine/checks/context/context_classification.py
"""
Context Classification for XBRL Verification

Classifies XBRL contexts as dimensional or default based on their structure.
"""

import logging
from typing import Optional

from ..core.constants import DIMENSIONAL_CONTEXT_INDICATORS


class ContextClassifier:
    """
    Classify XBRL context types.

    Determines if a context is dimensional (contains axis/member qualifiers)
    or default (no dimensional qualifiers).

    Example:
        classifier = ContextClassifier()

        # Dimensional context
        is_dim = classifier.is_dimensional('Duration_1_1_2024_To_12_31_2024_axis_member')
        # -> True

        # Default context
        is_dim = classifier.is_dimensional('Duration_1_1_2024_To_12_31_2024')
        # -> False
    """

    def __init__(self):
        self.logger = logging.getLogger('process.context_classifier')

    def is_dimensional(self, context_id: str) -> bool:
        """
        Check if a context is dimensional.

        Dimensional contexts contain axis and member identifiers.

        Args:
            context_id: The XBRL context identifier

        Returns:
            True if context is dimensional
        """
        if not context_id:
            return False

        context_lower = context_id.lower()

        for indicator in DIMENSIONAL_CONTEXT_INDICATORS:
            if indicator in context_lower:
                return True

        return False

    def is_default(self, context_id: str) -> bool:
        """
        Check if a context is default (non-dimensional).

        Args:
            context_id: The XBRL context identifier

        Returns:
            True if context is default (non-dimensional)
        """
        return not self.is_dimensional(context_id)


__all__ = [
    'ContextClassifier',
]
