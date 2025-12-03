"""
SEC Index Parser
================

Parses SEC EDGAR index.json files to extract filing document information.
Each SEC filing has an index.json manifest that lists all files in the package.

Index.json Structure:
{
    "directory": {
        "name": "0000320193-24-000001",
        "item": [
            {"name": "aapl-20240630.htm", "size": "12345"},
            {"name": "aapl-20240630_htm.zip", "size": "567890"},
            ...
        ]
    }
}

Save location: markets/sec/sec_downloader/sec_index_parser.py
"""

import json
from typing import Dict, Any, List, Optional
from pathlib import Path

from core.system_logger import get_logger
from markets.sec.sec_searcher.sec_constants import MIN_JSON_SIZE_BYTES

logger = get_logger(__name__, 'market')


class SECIndexParser:
    """
    Parser for SEC EDGAR index.json files.
    
    Extracts document listings from filing manifests and validates structure.
    """
    
    def __init__(self, min_json_size: int = MIN_JSON_SIZE_BYTES):
        """
        Initialize parser.
        
        Args:
            min_json_size: Minimum valid JSON size in bytes
        """
        self.min_json_size = min_json_size
        logger.debug("SEC index parser initialized")
    
    def parse(self, json_content: str) -> Optional[Dict[str, Any]]:
        """
        Parse index.json content.
        
        Args:
            json_content: Raw JSON string
            
        Returns:
            Parsed index dictionary or None if invalid
        """
        try:
            # Validate size
            if len(json_content) < self.min_json_size:
                logger.warning(
                    f"Index JSON too small: {len(json_content)} bytes "
                    f"(minimum: {self.min_json_size})"
                )
                return None
            
            # Parse JSON
            index_data = json.loads(json_content)
            
            # Validate structure
            if not self.validate_structure(index_data):
                logger.warning("Index JSON has invalid structure")
                return None
            
            logger.debug(
                f"Parsed index.json: {len(self.get_documents(index_data))} documents"
            )
            
            return index_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse index.json: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error parsing index.json: {e}")
            return None
    
    def parse_from_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Parse index.json from file.
        
        Args:
            file_path: Path to index.json file
            
        Returns:
            Parsed index dictionary or None if invalid
        """
        try:
            if not file_path.exists():
                logger.error(f"Index file not found: {file_path}")
                return None
            
            content = file_path.read_text(encoding='utf-8')
            return self.parse(content)
            
        except Exception as e:
            logger.error(f"Failed to read index file {file_path}: {e}")
            return None
    
    def validate_structure(self, index_data: Dict[str, Any]) -> bool:
        """
        Validate index.json structure.
        
        Args:
            index_data: Parsed JSON data
            
        Returns:
            True if structure is valid
        """
        try:
            # Check for directory section
            if 'directory' not in index_data:
                logger.debug("Missing 'directory' in index.json")
                return False
            
            directory = index_data['directory']
            
            # Check for item list
            if 'item' not in directory:
                logger.debug("Missing 'item' list in directory")
                return False
            
            # Check item is a list
            if not isinstance(directory['item'], list):
                logger.debug("'item' is not a list")
                return False
            
            # Validate at least one item
            if len(directory['item']) == 0:
                logger.debug("Empty document list")
                return False
            
            # Validate item structure (each should have 'name')
            for item in directory['item']:
                if not isinstance(item, dict) or 'name' not in item:
                    logger.debug("Invalid item structure in document list")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating index structure: {e}")
            return False
    
    def get_documents(self, index_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract document list from index.
        
        Args:
            index_data: Parsed index data
            
        Returns:
            List of document dictionaries
        """
        try:
            return index_data.get('directory', {}).get('item', [])
        except Exception as e:
            logger.error(f"Failed to extract documents: {e}")
            return []
    
    def get_filing_name(self, index_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract filing name from index.
        
        Args:
            index_data: Parsed index data
            
        Returns:
            Filing name (usually accession number) or None
        """
        try:
            return index_data.get('directory', {}).get('name')
        except Exception as e:
            logger.error(f"Failed to extract filing name: {e}")
            return None
    
    def find_documents_by_extension(
        self,
        index_data: Dict[str, Any],
        extensions: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Find documents with specific extensions.
        
        Args:
            index_data: Parsed index data
            extensions: List of extensions (e.g., ['.zip', '.xml'])
            
        Returns:
            List of matching documents
        """
        documents = self.get_documents(index_data)
        
        # Normalize extensions to lowercase
        extensions = [ext.lower() for ext in extensions]
        
        matching = []
        for doc in documents:
            doc_name = doc.get('name', '').lower()
            if any(doc_name.endswith(ext) for ext in extensions):
                matching.append(doc)
        
        return matching
    
    def find_documents_by_pattern(
        self,
        index_data: Dict[str, Any],
        patterns: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Find documents matching specific patterns.
        
        Args:
            index_data: Parsed index data
            patterns: List of patterns to match (e.g., ['_htm.zip', '_xbrl.zip'])
            
        Returns:
            List of matching documents with priority scores
        """
        documents = self.get_documents(index_data)
        
        # Normalize patterns to lowercase
        patterns = [p.lower() for p in patterns]
        
        matching = []
        for doc in documents:
            doc_name = doc.get('name', '').lower()
            
            for priority, pattern in enumerate(patterns):
                if pattern in doc_name:
                    matching.append({
                        'document': doc,
                        'pattern': pattern,
                        'priority': priority  # Lower is better
                    })
                    break  # Only match first pattern
        
        # Sort by priority
        matching.sort(key=lambda x: x['priority'])
        
        return matching
    
    def get_document_size(self, document: Dict[str, Any]) -> Optional[int]:
        """
        Extract document size.
        
        Args:
            document: Document dictionary from index
            
        Returns:
            Size in bytes or None if not available
        """
        try:
            size_str = document.get('size')
            if size_str:
                return int(size_str)
            return None
        except (ValueError, TypeError):
            return None
    
    def get_statistics(self, index_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get statistics about the index.
        
        Args:
            index_data: Parsed index data
            
        Returns:
            Dictionary with statistics
        """
        documents = self.get_documents(index_data)
        
        # Count file types
        extensions = {}
        total_size = 0
        
        for doc in documents:
            name = doc.get('name', '')
            if '.' in name:
                ext = '.' + name.split('.')[-1].lower()
                extensions[ext] = extensions.get(ext, 0) + 1
            
            size = self.get_document_size(doc)
            if size:
                total_size += size
        
        return {
            'total_documents': len(documents),
            'file_types': extensions,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'filing_name': self.get_filing_name(index_data)
        }


# Convenience function for quick parsing
def parse_index_json(json_content: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to parse index.json content.
    
    Args:
        json_content: Raw JSON string
        
    Returns:
        Parsed index dictionary or None if invalid
    """
    parser = SECIndexParser()
    return parser.parse(json_content)


def parse_index_json_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Convenience function to parse index.json file.
    
    Args:
        file_path: Path to index.json file
        
    Returns:
        Parsed index dictionary or None if invalid
    """
    parser = SECIndexParser()
    return parser.parse_from_file(file_path)