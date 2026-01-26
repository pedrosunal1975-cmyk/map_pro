# Path: verification/engine/markets/__init__.py
"""
Verification Markets Package

Market-specific verification logic.
ONLY place for market-specific code in verification module.

Markets:
- sec/: SEC-specific checks and thresholds
- esef/: ESEF/IFRS-specific checks and thresholds

Main Components:
- StatementIdentifier: Identifies main financial statements from all declared statements
- BaseStatementIdentifier: Abstract base for market-specific implementations
"""

from verification.engine.markets.base import (
    StatementCategory,
    StatementInfo,
    MainStatements,
    BaseStatementIdentifier,
)
from verification.engine.markets.sec.statement_identifier import SECStatementIdentifier
from verification.engine.markets.esef.statement_identifier import ESEFStatementIdentifier


def get_statement_identifier(market: str) -> BaseStatementIdentifier:
    """
    Factory to get the appropriate statement identifier for a market.

    Args:
        market: Market type ('sec', 'esef')

    Returns:
        Market-specific StatementIdentifier instance

    Raises:
        ValueError: If market is not supported
    """
    market_lower = market.lower()

    if market_lower == 'sec':
        return SECStatementIdentifier()
    elif market_lower == 'esef':
        return ESEFStatementIdentifier()
    else:
        raise ValueError(f"Unsupported market: {market}. Supported: sec, esef")


__all__ = [
    # Base classes
    'StatementCategory',
    'StatementInfo',
    'MainStatements',
    'BaseStatementIdentifier',
    # Implementations
    'SECStatementIdentifier',
    'ESEFStatementIdentifier',
    # Factory
    'get_statement_identifier',
]
