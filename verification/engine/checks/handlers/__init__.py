# Path: verification/engine/checks/handlers/__init__.py
"""
Value and attribute handlers for XBRL verification.

Contains:
- sign_weight_handler: iXBRL sign attribute and calculation weight handling
- dimension_handler: XBRL dimensional structure parsing
- instance_document_finder: Instance document location
"""

from .sign_weight_handler import (
    SignWeightHandler,
    SignInfo,
    SignSource,
    create_sign_weight_handler_from_filing,
    infer_sign_from_concept_name,
)
from .dimension_handler import (
    DimensionHandler,
    Dimension,
    DimensionMember,
    RoleDimensions,
    ContextDimensions,
)
from .instance_document_finder import (
    InstanceDocumentFinder,
    INSTANCE_DOCUMENT_PATTERNS,
    INSTANCE_DOCUMENT_EXCLUSIONS,
)

__all__ = [
    # Sign weight handler
    'SignWeightHandler',
    'SignInfo',
    'SignSource',
    'create_sign_weight_handler_from_filing',
    'infer_sign_from_concept_name',
    # Dimension handler
    'DimensionHandler',
    'Dimension',
    'DimensionMember',
    'RoleDimensions',
    'ContextDimensions',
    # Instance document finder
    'InstanceDocumentFinder',
    'INSTANCE_DOCUMENT_PATTERNS',
    'INSTANCE_DOCUMENT_EXCLUSIONS',
]
