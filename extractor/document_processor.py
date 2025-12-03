# File: /map_pro/engines/extractor/document_processor.py

"""
Document Processor
==================

Handles document record creation and updates after extraction.
"""

from typing import List, Tuple, Optional, Set
from pathlib import Path

from database.models.core_models import Filing, Document


class DocumentProcessor:
    """
    Processes extracted files and creates/updates document records.
    
    Responsibilities:
    - Analyze extracted files
    - Create or update document records
    - Determine parsing eligibility
    - Track XBRL vs linkbase files
    """
    
    # Linkbase file patterns to exclude from parsing
    LINKBASE_PATTERNS: Set[str] = {
        '_cal.xml',   # Calculation linkbase
        '_def.xml',   # Definition linkbase
        '_lab.xml',   # Label linkbase
        '_pre.xml',   # Presentation linkbase
        '_ref.xml',   # Reference linkbase
        '.xsd'        # XML Schema Definition files
    }
    
    # XBRL file extensions
    XBRL_EXTENSIONS: Set[str] = {'.xml', '.xbrl', '.htm', '.html'}
    
    def __init__(self, logger):
        """
        Initialize document processor.
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
    
    def create_document_records(
        self,
        filing: Filing,
        extraction_path: Path,
        extracted_files: List[Path],
        session
    ) -> int:
        """
        Create document records for extracted files.
        
        Args:
            filing: Filing object
            extraction_path: Path where files were extracted
            extracted_files: List of extracted file paths
            session: Database session
            
        Returns:
            Total number of document records created or updated
        """
        documents_created = 0
        documents_updated = 0
        
        for file_path in extracted_files:
            try:
                document, is_new = self._process_document_file(
                    filing=filing,
                    file_path=file_path,
                    extraction_path=extraction_path,
                    session=session
                )
                
                if is_new:
                    documents_created += 1
                else:
                    documents_updated += 1
                
            except Exception as e:
                self.logger.warning(f"Failed to process document record for {file_path}: {e}")
                continue
        
        session.flush()
        
        documents_processed = documents_created + documents_updated
        
        self.logger.info(
            f"Processed {documents_processed} document records for filing {filing.filing_universal_id}: "
            f"{documents_created} new, {documents_updated} updated"
        )
        
        return documents_processed
    
    def _process_document_file(
        self,
        filing: Filing,
        file_path: Path,
        extraction_path: Path,
        session
    ) -> Tuple[Document, bool]:
        """
        Process a single document file.
        
        Args:
            filing: Filing object
            file_path: Path to document file
            extraction_path: Base extraction path
            session: Database session
            
        Returns:
            Tuple of (Document object, is_new boolean)
        """
        # Determine document properties
        is_xbrl, is_linkbase, parsing_eligible = self._analyze_document_file(file_path)
        
        # Get or create document record
        existing_document = self._get_existing_document(
            filing=filing,
            document_name=file_path.name,
            session=session
        )
        
        if existing_document:
            self._update_existing_document(
                document=existing_document,
                file_path=file_path,
                is_xbrl=is_xbrl,
                is_linkbase=is_linkbase,
                parsing_eligible=parsing_eligible
            )
            return existing_document, False
        else:
            new_document = self._create_new_document(
                filing=filing,
                file_path=file_path,
                is_xbrl=is_xbrl,
                is_linkbase=is_linkbase,
                parsing_eligible=parsing_eligible
            )
            session.add(new_document)
            return new_document, True
    
    def _analyze_document_file(self, file_path: Path) -> Tuple[bool, bool, bool]:
        """
        Analyze document file to determine its properties.
        
        Args:
            file_path: Path to document file
            
        Returns:
            Tuple of (is_xbrl, is_linkbase, parsing_eligible)
        """
        # Check if file has XBRL-related extension
        is_xbrl = file_path.suffix.lower() in self.XBRL_EXTENSIONS
        
        # Check if file is a linkbase file
        is_linkbase = self._is_linkbase_file(file_path)
        
        # Only mark as parsing_eligible if it's XBRL AND not a linkbase file
        parsing_eligible = is_xbrl and not is_linkbase
        
        # Log when we filter out linkbase files
        if is_xbrl and is_linkbase:
            self.logger.debug(
                f"Skipping linkbase/schema file for parsing: {file_path.name}"
            )
        
        return is_xbrl, is_linkbase, parsing_eligible
    
    def _is_linkbase_file(self, file_path: Path) -> bool:
        """
        Check if file is a linkbase or schema file.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if linkbase file, False otherwise
        """
        file_name_lower = file_path.name.lower()
        return any(
            file_name_lower.endswith(pattern.lower())
            for pattern in self.LINKBASE_PATTERNS
        )
    
    def _get_existing_document(
        self,
        filing: Filing,
        document_name: str,
        session
    ) -> Optional[Document]:
        """
        Get existing document record if it exists.
        
        Args:
            filing: Filing object
            document_name: Document name
            session: Database session
            
        Returns:
            Existing Document or None
        """
        return session.query(Document).filter_by(
            filing_universal_id=filing.filing_universal_id,
            document_name=document_name
        ).first()
    
    def _update_existing_document(
        self,
        document: Document,
        file_path: Path,
        is_xbrl: bool,
        is_linkbase: bool,
        parsing_eligible: bool
    ):
        """
        Update existing document record.
        
        Args:
            document: Existing document object
            file_path: Path to file
            is_xbrl: Whether file is XBRL
            is_linkbase: Whether file is linkbase
            parsing_eligible: Whether file is eligible for parsing
        """
        self.logger.debug(f"Document already exists, updating: {file_path.name}")
        
        document.document_type = self._get_document_type(file_path)
        document.file_size_bytes = self._get_file_size(file_path)
        document.extraction_path = str(file_path)
        document.is_xbrl_instance = is_xbrl and not is_linkbase
        document.parsing_eligible = parsing_eligible
        
        # Only update parsed_status if not already completed or failed
        if document.parsed_status not in ['completed', 'failed']:
            document.parsed_status = 'pending' if parsing_eligible else 'not_applicable'
    
    def _create_new_document(
        self,
        filing: Filing,
        file_path: Path,
        is_xbrl: bool,
        is_linkbase: bool,
        parsing_eligible: bool
    ) -> Document:
        """
        Create new document record.
        
        Args:
            filing: Filing object
            file_path: Path to file
            is_xbrl: Whether file is XBRL
            is_linkbase: Whether file is linkbase
            parsing_eligible: Whether file is eligible for parsing
            
        Returns:
            New Document object
        """
        return Document(
            filing_universal_id=filing.filing_universal_id,
            document_name=file_path.name,
            document_type=self._get_document_type(file_path),
            file_size_bytes=self._get_file_size(file_path),
            extraction_path=str(file_path),
            is_xbrl_instance=is_xbrl and not is_linkbase,
            parsing_eligible=parsing_eligible,
            parsed_status='pending' if parsing_eligible else 'not_applicable'
        )
    
    def _get_document_type(self, file_path: Path) -> str:
        """
        Get document type from file path extension.
        
        Args:
            file_path: Path to file
            
        Returns:
            Document type string (uppercase)
        """
        if file_path.suffix:
            return file_path.suffix.lstrip('.').upper()
        return 'UNKNOWN'
    
    def _get_file_size(self, file_path: Path) -> Optional[int]:
        """
        Get file size in bytes.
        
        Args:
            file_path: Path to file
            
        Returns:
            File size in bytes or None if file doesn't exist
        """
        if file_path.exists():
            return file_path.stat().st_size
        return None