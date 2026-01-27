# Path: verification/engine/markets/esef/__init__.py
"""
ESEF Market Package

ESEF/IFRS-specific verification checks and thresholds.

Components:
- ESEFStatementIdentifier: Identifies main IFRS statements from ESEF filings
"""

from verification.engine.markets.esef.statement_identifier import ESEFStatementIdentifier

__all__ = ['ESEFStatementIdentifier']
