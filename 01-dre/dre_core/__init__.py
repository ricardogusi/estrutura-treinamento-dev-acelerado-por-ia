"""DRE core package."""

from .validation import (
    DreValidationError,
    validate_schema,
    normalize_payload,
    compute_totals,
    compute_margins,
)

__all__ = [
    "DreValidationError",
    "validate_schema",
    "normalize_payload",
    "compute_totals",
    "compute_margins",
]
