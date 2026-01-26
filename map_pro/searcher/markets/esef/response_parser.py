# Path: searcher/markets/esef/response_parser.py
"""
ESEF Response Parser

Parses JSON-API responses from filings.xbrl.org.
Extracts filing and entity data into standardized format.
"""

from typing import Optional

from searcher.core.logger import get_logger
from searcher.constants import LOG_PROCESS
from searcher.markets.esef.constants import (
    KEY_DATA,
    KEY_INCLUDED,
    KEY_META,
    ATTR_ATTRIBUTES,
    ATTR_RELATIONSHIPS,
    FIELD_ENTITY,
    FIELD_ENTITY_DATA,
)

logger = get_logger(__name__, 'markets')


class ESEFResponseParser:
    """
    Parses filings.xbrl.org JSON-API responses.

    Handles:
    - Filing list responses
    - Single filing responses
    - Entity relationship resolution
    - Pagination metadata extraction
    """

    def parse_filings_response(self, response: dict) -> list[dict]:
        """
        Parse filings list response.

        Args:
            response: JSON-API response dict

        Returns:
            list[dict]: Parsed filing records
        """
        if not response:
            return []

        # Extract data array
        data = response.get(KEY_DATA, [])
        if not data:
            return []

        # Build entity lookup from included resources
        entity_lookup = self._build_entity_lookup(response.get(KEY_INCLUDED, []))

        # Parse each filing
        filings = []
        for item in data:
            filing = self._parse_filing_item(item, entity_lookup)
            if filing:
                filings.append(filing)

        logger.debug(f"{LOG_PROCESS} Parsed {len(filings)} filings")
        return filings

    def _parse_filing_item(
        self,
        item: dict,
        entity_lookup: dict
    ) -> Optional[dict]:
        """
        Parse single filing item from response.

        Args:
            item: Filing item from data array
            entity_lookup: Entity ID -> entity data lookup

        Returns:
            dict: Parsed filing or None
        """
        if not item:
            return None

        # Get filing ID and type
        filing_id = item.get('id')
        filing_type = item.get('type')

        # Get attributes
        attrs = item.get(ATTR_ATTRIBUTES, {})

        # Extract core fields
        filing = {
            'filing_id': filing_id,
            'filing_type': filing_type,
            'country': attrs.get('country'),
            'date_added': attrs.get('date_added'),
            'period_end': attrs.get('period_end'),
            'report_url': attrs.get('report_url'),
            'viewer_url': attrs.get('viewer_url'),
            'json_url': attrs.get('json_url'),
            'package_url': attrs.get('package_url'),
            'report_type': attrs.get('report_type'),
            'oam_id': attrs.get('oam_id'),
            'lei': attrs.get('lei'),
            'entity_name': attrs.get('entity_name'),
            'processed': attrs.get('processed'),
        }

        # Resolve entity relationship if available
        relationships = item.get(ATTR_RELATIONSHIPS, {})
        entity_rel = relationships.get(FIELD_ENTITY, {})
        entity_data = entity_rel.get(FIELD_ENTITY_DATA, {})

        if entity_data:
            entity_id = entity_data.get('id')
            entity_type = entity_data.get('type')

            # Look up full entity data from included
            if entity_id and entity_id in entity_lookup:
                entity = entity_lookup[entity_id]
                filing['entity'] = entity
            else:
                filing['entity'] = {
                    'id': entity_id,
                    'type': entity_type
                }

        return filing

    def _build_entity_lookup(self, included: list) -> dict:
        """
        Build entity lookup from included resources.

        Args:
            included: Included resources array from response

        Returns:
            dict: Entity ID -> entity data mapping
        """
        lookup = {}

        for item in included:
            item_type = item.get('type')
            item_id = item.get('id')

            if item_type == 'entity' and item_id:
                attrs = item.get(ATTR_ATTRIBUTES, {})
                lookup[item_id] = {
                    'id': item_id,
                    'name': attrs.get('name'),
                    'lei': attrs.get('lei'),
                    'country': attrs.get('country'),
                    'identifier': attrs.get('identifier'),
                }

        return lookup

    def parse_pagination(self, response: dict) -> dict:
        """
        Parse pagination metadata from response.

        Args:
            response: JSON-API response dict

        Returns:
            dict: Pagination info with total_pages, total_count, etc.
        """
        meta = response.get(KEY_META, {})

        return {
            'total_count': meta.get('total_count', 0),
            'total_pages': meta.get('total_pages', 0),
            'current_page': meta.get('current_page', 1),
            'page_size': meta.get('page_size', 25),
        }

    def get_filing_download_url(self, filing: dict) -> Optional[str]:
        """
        Get the best download URL for a filing.

        Priority:
        1. report_url - Direct iXBRL file
        2. package_url - ZIP package with all files

        Args:
            filing: Parsed filing dict

        Returns:
            str: Download URL or None
        """
        # Prefer direct report URL (iXBRL file)
        report_url = filing.get('report_url')
        if report_url:
            return report_url

        # Fallback to package URL (ZIP)
        package_url = filing.get('package_url')
        if package_url:
            return package_url

        return None


__all__ = ['ESEFResponseParser']
