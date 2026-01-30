# Path: verification/engine/markets/sec/__init__.py
"""
SEC Market Package

SEC-specific verification checks and thresholds.

Components:
- SECStatementIdentifier: Identifies main consolidated statements from SEC filings
"""

from verification.engine.markets.sec.statement_identifier import SECStatementIdentifier

__all__ = ['SECStatementIdentifier']
