"""
Map Pro Facts Loader
===================

Handles loading parsed facts with hybrid database + filesystem approach.

Responsibilities:
- Load parsed facts from database
- Fall back to filesystem scan
- Provide diagnostics when loading fails
"""

import json
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from core.data_paths import map_pro_paths
from database.models.parsed_models import ParsedDocument

logger = get_logger(__name__, 'engine')

# Constants
SMALL_CONTENT_READ = 2000


class FactsLoader:
    """
    Loads parsed facts using hybrid database + filesystem approach.
    
    Strategy:
    1. Try database first (fast)
    2. Fall back to filesystem scan (reliable)
    3. Provide detailed diagnostics on failure
    """
    
    def __init__(self):
        """Initialize facts loader."""
        self.logger = logger
    
    def load_parsed_facts(
        self,
        filing_id: str
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Load parsed facts for a filing.
        
        Args:
            filing_id: Filing UUID
            
        Returns:
            Tuple of (facts_list, metadata_dict)
        """
        self.logger.info(f"Loading parsed facts for filing {filing_id}")
        
        # Try database first
        facts, metadata = self._try_database_lookup(filing_id)
        if facts:
            self.logger.info(f"Found {len(facts)} facts via database")
            return facts, metadata
        
        # Fall back to filesystem
        self.logger.warning(f"Database failed, scanning filesystem for {filing_id}")
        facts, metadata = self._try_filesystem_scan(filing_id)
        if facts:
            self.logger.info(f"Found {len(facts)} facts via filesystem")
            return facts, metadata
        
        # Both failed - provide diagnostics
        self.logger.error(f"No facts found for filing {filing_id}")
        self._provide_diagnostics(filing_id)
        return [], {}
    
    def _try_database_lookup(
        self,
        filing_id: str
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Try to find facts via database lookup with retry for transaction visibility.
        
        Args:
            filing_id: Filing UUID
            
        Returns:
            Tuple of (facts, metadata) or ([], {}) if not found
        """
        import time
        
        max_retries = 5
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                with db_coordinator.get_session('parsed') as session:
                    # First, try to find documents with facts
                    docs_with_facts = self._find_documents_with_facts(session, filing_id)
                    if docs_with_facts:
                        self.logger.info(
                            f"Found {len(docs_with_facts)} document(s) with facts "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        return self._load_from_best_document(docs_with_facts)
                    
                    # Then try all documents
                    all_docs = self._find_all_documents(session, filing_id)
                    if all_docs:
                        self.logger.info(
                            f"Found {len(all_docs)} document(s) total "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        return self._handle_all_documents(all_docs)
                    
                    # No documents found
                    if attempt < max_retries - 1:
                        self.logger.warning(
                            f"No parsed documents found for {filing_id} "
                            f"(attempt {attempt + 1}/{max_retries}), waiting {retry_delay}s for "
                            f"database transaction visibility..."
                        )
                        time.sleep(retry_delay)
                    else:
                        self.logger.warning(
                            f"No parsed documents found for {filing_id} after {max_retries} attempts"
                        )
                        return [], {}
                        
            except Exception as e:
                if attempt < max_retries - 1:
                    self.logger.warning(
                        f"Database lookup error (attempt {attempt + 1}/{max_retries}): {e}, "
                        f"retrying in {retry_delay}s..."
                    )
                    time.sleep(retry_delay)
                else:
                    self.logger.error(
                        f"Database lookup failed after {max_retries} attempts: {e}", 
                        exc_info=True
                    )
                    return [], {}
        
        return [], {}
    
    def _find_documents_with_facts(
        self,
        session,
        filing_id: str
    ) -> List:
        """Find documents that have facts extracted."""
        return session.query(ParsedDocument).filter(
            ParsedDocument.filing_universal_id == filing_id,
            ParsedDocument.validation_status == 'completed',
            ParsedDocument.facts_extracted > 0
        ).order_by(ParsedDocument.facts_extracted.desc()).all()
    
    def _find_all_documents(self, session, filing_id: str) -> List:
        """Find all documents for filing."""
        return session.query(ParsedDocument).filter(
            ParsedDocument.filing_universal_id == filing_id
        ).all()
    
    def _load_from_best_document(
        self,
        documents: List
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Load facts from the best document (most facts)."""
        best_doc = documents[0]  # Already sorted by facts_extracted desc
        return self._load_facts_from_document(best_doc)
    
    def _handle_all_documents(
        self,
        all_docs: List
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Handle all documents, finding best one with facts."""
        fact_docs = [d for d in all_docs if d.facts_extracted > 0]
        zero_fact_docs = [d for d in all_docs if d.facts_extracted == 0]
        
        self.logger.info(
            f"Found {len(all_docs)} documents: "
            f"{len(fact_docs)} with facts, {len(zero_fact_docs)} with 0 facts"
        )
        
        if fact_docs:
            best_doc = max(fact_docs, key=lambda d: d.facts_extracted)
            return self._load_facts_from_document(best_doc)
        
        return [], {}
    
    def _load_facts_from_document(
        self,
        parsed_doc
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Load facts from a ParsedDocument database record.
        
        Args:
            parsed_doc: ParsedDocument instance
            
        Returns:
            Tuple of (facts, metadata)
        """
        if not parsed_doc.facts_json_path:
            self.logger.warning(
                f"ParsedDocument {parsed_doc.parsed_document_id} has no facts_json_path"
            )
            return [], {}
        
        json_path = self._resolve_json_path(parsed_doc.facts_json_path)
        
        if not json_path or not json_path.exists():
            self.logger.warning(f"Facts file not found: {json_path}")
            return [], {}
        
        return self._load_facts_from_json_file(json_path)
    
    def _resolve_json_path(self, facts_json_path: str) -> Optional[Path]:
        """
        Resolve JSON path (handle relative/absolute paths).
        
        Args:
            facts_json_path: Path from database
            
        Returns:
            Resolved Path or None
        """
        json_path = Path(facts_json_path)
        
        # If not absolute, make it relative to data_root
        if not json_path.is_absolute():
            json_path = map_pro_paths.data_root / json_path
        
        # Try the path
        if json_path.exists():
            return json_path
        
        # Try alternative path
        alt_path = map_pro_paths.data_root / facts_json_path
        if alt_path.exists():
            return alt_path
        
        self.logger.warning(f"Path not found: {json_path}")
        self.logger.warning(f"Also tried: {alt_path}")
        return None
    
    def _load_facts_from_json_file(
        self,
        json_path: Path
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Load facts from a JSON file.
        
        Args:
            json_path: Path to JSON file
            
        Returns:
            Tuple of (facts, metadata)
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            facts = data.get('facts', [])
            metadata = data.get('metadata', {})
            
            self.logger.debug(f"Loaded {len(facts)} facts from {json_path}")
            return facts, metadata
            
        except Exception as e:
            self.logger.error(f"Failed to read JSON file {json_path}: {e}")
            return [], {}
    
    def _try_filesystem_scan(
        self,
        filing_id: str
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Scan filesystem for facts JSON files.
        
        Complexity reduced by extracting helper methods.
        
        Args:
            filing_id: Filing UUID
            
        Returns:
            Tuple of (facts, metadata) or ([], {})
        """
        try:
            parsed_facts_root = map_pro_paths.data_parsed_facts
            
            if not parsed_facts_root.exists():
                self.logger.warning(f"Parsed facts directory missing: {parsed_facts_root}")
                return [], {}
            
            # Find candidate files
            candidate_files = self._find_candidate_files(parsed_facts_root, filing_id)
            
            if not candidate_files:
                self.logger.warning(f"No JSON files found containing {filing_id}")
                return [], {}
            
            # Try to load from candidates
            return self._load_from_candidates(candidate_files, filing_id)
            
        except Exception as e:
            self.logger.error(f"Filesystem scan failed: {e}", exc_info=True)
            return [], {}
    
    def _find_candidate_files(
        self,
        search_root: Path,
        filing_id: str
    ) -> List[Path]:
        """
        Find candidate JSON files that might contain the filing.
        
        Args:
            search_root: Root directory to search
            filing_id: Filing UUID to search for
            
        Returns:
            List of candidate file paths (priority ordered)
        """
        candidate_files = []
        
        for json_file in search_root.rglob("*.json"):
            try:
                # Priority: filing_id in filename
                if filing_id in json_file.name:
                    candidate_files.insert(0, json_file)
                    continue
                
                # Check file content
                if self._file_contains_filing_id(json_file, filing_id):
                    candidate_files.append(json_file)
                    
            except Exception as e:
                self.logger.debug(f"Skipping file {json_file}: {e}")
                continue
        
        return candidate_files
    
    def _file_contains_filing_id(self, json_file: Path, filing_id: str) -> bool:
        """
        Check if file contains filing ID (fast check).
        
        Args:
            json_file: Path to JSON file
            filing_id: Filing UUID to search for
            
        Returns:
            True if filing_id found in first SMALL_CONTENT_READ bytes
        """
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                content = f.read(SMALL_CONTENT_READ)
                return filing_id in content
        except Exception:
            return False
    
    def _load_from_candidates(
        self,
        candidate_files: List[Path],
        filing_id: str
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Try to load facts from candidate files.
        
        Args:
            candidate_files: List of candidate file paths
            filing_id: Filing UUID (for verification)
            
        Returns:
            Tuple of (facts, metadata) or ([], {})
        """
        for json_file in candidate_files:
            try:
                facts, metadata = self._load_facts_from_json_file(json_file)
                
                # Verify this is the right filing
                if self._verify_filing_match(metadata, filing_id) and facts:
                    self.logger.info(f"Found {len(facts)} facts in {json_file}")
                    return facts, metadata
                    
            except Exception as e:
                self.logger.warning(f"Failed to load {json_file}: {e}")
                continue
        
        self.logger.warning(
            f"Found {len(candidate_files)} candidates but none contained valid facts"
        )
        return [], {}
    
    def _verify_filing_match(self, metadata: Dict[str, Any], filing_id: str) -> bool:
        """
        Verify metadata matches the requested filing.
        
        Args:
            metadata: Metadata dictionary
            filing_id: Expected filing UUID
            
        Returns:
            True if match confirmed
        """
        file_filing_id = metadata.get('filing_id') or metadata.get('filing_universal_id')
        return file_filing_id == filing_id
    
    def _provide_diagnostics(self, filing_id: str) -> None:
        """
        Provide detailed diagnostics when facts can't be found.
        
        Complexity reduced by extracting database and filesystem checks.
        
        Args:
            filing_id: Filing UUID
        """
        self.logger.error(f"\n{'='*60}")
        self.logger.error(f"DIAGNOSTICS for filing {filing_id}")
        self.logger.error(f"{'='*60}")
        
        self._diagnose_database(filing_id)
        self._diagnose_filesystem(filing_id)
        self._provide_suggestions(filing_id)
        
        self.logger.error(f"{'='*60}\n")
    
    def _diagnose_database(self, filing_id: str) -> None:
        """Check database for filing information."""
        try:
            with db_coordinator.get_session('parsed') as session:
                all_docs = session.query(ParsedDocument).filter(
                    ParsedDocument.filing_universal_id == filing_id
                ).all()
                
                if not all_docs:
                    self.logger.error("Database: No ParsedDocument records found")
                else:
                    self.logger.error(f"Database: Found {len(all_docs)} document(s):")
                    for doc in all_docs:
                        self._log_document_info(doc)
                        
        except Exception as e:
            self.logger.error(f"Database check failed: {e}")
    
    def _log_document_info(self, doc) -> None:
        """Log information about a parsed document."""
        path = Path(doc.facts_json_path) if doc.facts_json_path else None
        
        self.logger.error(
            f"  - {doc.document_name}: {doc.facts_extracted} facts, "
            f"status: {doc.validation_status}"
        )
        self.logger.error(f"    Path in DB: {doc.facts_json_path}")
        
        if path:
            exists = path.exists()
            self.logger.error(f"    File exists (as given)? {exists}")
            
            if not exists:
                abs_path = map_pro_paths.data_root / path if not path.is_absolute() else path
                self.logger.error(f"    Absolute path: {abs_path}")
                self.logger.error(f"    File exists (absolute)? {abs_path.exists()}")
    
    def _diagnose_filesystem(self, filing_id: str) -> None:
        """Check filesystem for JSON files."""
        try:
            parsed_facts_root = map_pro_paths.data_parsed_facts
            
            if not parsed_facts_root.exists():
                self.logger.error(f"\nFilesystem: Directory missing: {parsed_facts_root}")
                return
            
            json_files = list(parsed_facts_root.rglob("*.json"))
            self.logger.error(
                f"\nFilesystem: Found {len(json_files)} total JSON files in parsed_facts/"
            )
            
            potential_files = [f for f in json_files if filing_id in str(f)]
            if potential_files:
                self.logger.error(
                    f"Filesystem: {len(potential_files)} file(s) mention this filing ID:"
                )
                for pf in potential_files[:3]:
                    self.logger.error(f"  - {pf}")
                    
        except Exception as e:
            self.logger.error(f"Filesystem check failed: {e}")
    
    def _provide_suggestions(self, filing_id: str) -> None:
        """Provide troubleshooting suggestions."""
        self.logger.error("\nSUGGESTIONS:")
        self.logger.error("  1. Check if parser completed successfully")
        self.logger.error(f"  2. Verify filing ID is correct: {filing_id}")
        self.logger.error("  3. Check if paths in database are absolute or relative")
        self.logger.error("  4. Look for parser error logs")


__all__ = ['FactsLoader']