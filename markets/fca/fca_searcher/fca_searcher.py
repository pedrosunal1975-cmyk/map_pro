"""
FCA Searcher Implementation (STUB)
==================================

Minimal stub implementation for UK FCA to validate market-agnostic abstraction.
This reveals if SEC-specific assumptions leaked into the base classes.

NOTE: This is a STUB. FCA doesn't have a public API like SEC EDGAR.
Real implementation would require different data sources.
"""

from typing import Dict, Any, List, Optional
from datetime import date, datetime, timezone

from markets.base.market_interface import MarketInterface
from markets.base.success_evaluator import success_evaluator
from core.system_logger import get_logger
from shared.exceptions.custom_exceptions import EngineError

from .fca_validators import FCAValidator, identify_identifier_type
from .fca_constants import (
    FCA_FILING_TYPES,
    MAJOR_FILING_TYPES,
    ANNUAL_FILINGS,
    INTERIM_FILINGS
)

logger = get_logger(__name__, 'market')


class FCASearcher(MarketInterface):
    """
    FCA (UK Financial Conduct Authority) market implementation (STUB).
    
    This is a minimal stub to validate the market-agnostic abstraction.
    Key differences from SEC:
    - Uses company registration numbers instead of CIK
    - Different filing types (Annual Report vs 10-K)
    - Files are direct XBRL, not ZIP archives
    - No public API like EDGAR (would need Companies House API)
    """
    
    def __init__(self):
        """Initialize FCA searcher."""
        super().__init__('fca')
        
        # Stub data for testing
        self._stub_companies = {
            '00000001': {
                'name': 'Test UK Company Ltd',
                'company_number': '00000001',
                'status': 'Active'
            }
        }
        
        self.logger.info("FCA searcher initialized (STUB)")
    
    async def search_company(self, company_identifier: str) -> Optional[Dict[str, Any]]:
        """
        Search for company in FCA database (STUB).
        
        NOTE: This is stub data. Real implementation would call Companies House API.
        
        Args:
            company_identifier: Company number or name
            
        Returns:
            Standardized company information or None
        """
        try:
            identifier_type = identify_identifier_type(company_identifier)
            
            if identifier_type == 'company_number':
                company_number = FCAValidator.normalize_company_number(company_identifier)
                
                # Stub: Return mock data
                if company_number in self._stub_companies:
                    stub_data = self._stub_companies[company_number]
                    
                    company_info = {
                        'market_entity_id': company_number,
                        'name': stub_data['name'],
                        'ticker': None,  # UK companies don't always have tickers
                        'identifiers': {
                            'company_number': company_number,
                        },
                        'jurisdiction': 'GB',
                        'entity_type': 'Limited Company',
                        'status': stub_data['status'].lower(),
                        'discovered_at': datetime.now(timezone.utc),
                        'source_url': f"https://find-and-update.company-information.service.gov.uk/company/{company_number}",
                        'additional_info': {
                            'note': 'STUB DATA - Real implementation would use Companies House API'
                        }
                    }
                    
                    return company_info
                else:
                    self.logger.warning(f"Company number '{company_number}' not found (stub data)")
                    return None
            else:
                # Name search not implemented in stub
                self.logger.info(f"Name search not implemented in stub: {company_identifier}")
                return None
        
        except Exception as e:
            self.logger.error(f"Company search failed for '{company_identifier}': {e}")
            raise EngineError(f"FCA company search failed: {str(e)}")
    
    async def find_filings(
        self,
        market_entity_id: str,
        search_criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find filings for a company (STUB).
        
        NOTE: Returns stub data. Real implementation would access FCA filing database.
        
        Args:
            market_entity_id: UK company number
            search_criteria: Optional filters
            
        Returns:
            List of standardized filing information
        """
        try:
            # Validate company number
            if not FCAValidator.validate_company_number(market_entity_id):
                raise ValueError(f"Invalid UK company number: {market_entity_id}")
            
            company_number = FCAValidator.normalize_company_number(market_entity_id)
            
            # Stub: Return mock filings
            stub_filings = [
                {
                    'market_filing_id': f"{company_number}-2024-ANNUAL",
                    'filing_type': 'ANNUAL',
                    'filing_date': date(2024, 12, 31),
                    'title': 'Annual Report 2024',
                    'url': f"https://fca.example.com/filings/{company_number}/2024-annual.ixbrl",
                    'format': '.ixbrl',  # FCA uses iXBRL, not ZIP
                    'source_url': f"https://fca.example.com/company/{company_number}",
                    'additional_info': {
                        'note': 'STUB DATA - Real implementation would fetch actual filings'
                    }
                }
            ]
            
            self.logger.info(f"Found {len(stub_filings)} filings for company {company_number} (stub)")
            
            return stub_filings
        
        except Exception as e:
            self.logger.error(f"Filing search failed for company {market_entity_id}: {e}")
            raise EngineError(f"FCA filing search failed: {str(e)}")
    
    def validate_identifier(self, company_identifier: str) -> bool:
        """
        Validate company identifier for FCA.
        
        Args:
            company_identifier: Identifier to validate
            
        Returns:
            True if valid format
        """
        if not company_identifier:
            return False
        
        identifier_type = identify_identifier_type(company_identifier)
        return identifier_type is not None
    
    def get_supported_filing_types(self) -> List[str]:
        """
        Get list of supported FCA filing types.
        
        Returns:
            List of filing type codes
        """
        return MAJOR_FILING_TYPES
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get FCA market capabilities.
        
        Returns:
            Capabilities dictionary
        """
        return {
            'market_name': 'fca',
            'market_description': 'UK Financial Conduct Authority',
            'supported_identifiers': ['company_number', 'name'],
            'requires_authentication': False,
            'rate_limit_per_minute': 300,
            'supports_date_range_search': True,
            'supports_filing_type_filter': True,
            'default_filing_types': MAJOR_FILING_TYPES,
            'api_base_url': 'https://api.fca.org.uk',  # Placeholder
            'documentation_url': 'https://www.fca.org.uk/',
            'filing_categories': {
                'annual': ANNUAL_FILINGS,
                'interim': INTERIM_FILINGS
            },
            'notes': 'STUB IMPLEMENTATION - Real FCA integration would use Companies House API'
        }
    
    async def close(self):
        """Close resources."""
        self.logger.info("FCA searcher closed")


# Convenience function
def create_fca_searcher() -> FCASearcher:
    """Create FCA searcher instance."""
    return FCASearcher()