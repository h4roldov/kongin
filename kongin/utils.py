"""
Utility functions for Kongin.
"""

import re
from typing import Optional


def normalize_date(date_str: Optional[str]) -> Optional[str]:
    """
    Normalize date string to OAI-PMH format.

    Accepts various date formats and returns YYYY-MM-DD or
    YYYY-MM-DDThh:mm:ssZ format.

    Args:
        date_str: Date string in various formats

    Returns:
        Normalized date string or None if input is None
    """
    if not date_str:
        return None

    # Already in correct format
    if len(date_str) == 10 or 'T' in date_str:
        return date_str

    # Try to parse common formats
    from datetime import datetime

    formats = [
        '%Y-%m-%d',
        '%Y/%m/%d',
        '%d-%m-%Y',
        '%d/%m/%Y',
        '%Y%m%d',
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue

    # Return as-is if no format matches
    return date_str


def validate_metadata_prefix(prefix: str) -> bool:
    """
    Validate that a metadata prefix looks reasonable.

    Args:
        prefix: Metadata prefix to validate

    Returns:
        True if valid, False otherwise
    """
    if not prefix:
        return False

    # Must be alphanumeric with underscores
    return all(c.isalnum() or c == '_' for c in prefix)


# OAI-PMH date format patterns
DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')
DATETIME_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')


def validate_oai_date(date_str: str) -> bool:
    """
    Validate OAI-PMH date format.

    OAI-PMH supports two granularities:
    - Day: YYYY-MM-DD
    - Second: YYYY-MM-DDThh:mm:ssZ

    Args:
        date_str: Date string to validate

    Returns:
        True if valid OAI-PMH date format
    """
    if not date_str:
        return False
    return bool(DATE_PATTERN.match(date_str) or DATETIME_PATTERN.match(date_str))


def get_date_granularity(date_str: str) -> Optional[str]:
    """
    Get granularity of an OAI-PMH date.

    Args:
        date_str: Date string

    Returns:
        'day' for YYYY-MM-DD, 'second' for YYYY-MM-DDThh:mm:ssZ, None if invalid
    """
    if not date_str:
        return None
    if DATE_PATTERN.match(date_str):
        return 'day'
    if DATETIME_PATTERN.match(date_str):
        return 'second'
    return None


def validate_date_range(
    from_date: Optional[str],
    until_date: Optional[str]
) -> None:
    """
    Validate OAI-PMH date range parameters.

    OAI-PMH requires:
    - Both dates must be valid OAI-PMH format
    - Both dates must use the same granularity
    - from_date must be <= until_date

    Args:
        from_date: Start date (optional)
        until_date: End date (optional)

    Raises:
        ValueError: If date range is invalid
    """
    # No validation needed if neither date is provided
    if not from_date and not until_date:
        return

    # Validate individual date formats
    if from_date and not validate_oai_date(from_date):
        raise ValueError(
            f"Invalid from date format: {from_date}. "
            "Use YYYY-MM-DD or YYYY-MM-DDThh:mm:ssZ"
        )

    if until_date and not validate_oai_date(until_date):
        raise ValueError(
            f"Invalid until date format: {until_date}. "
            "Use YYYY-MM-DD or YYYY-MM-DDThh:mm:ssZ"
        )

    # If both dates provided, check granularity and order
    if from_date and until_date:
        from_granularity = get_date_granularity(from_date)
        until_granularity = get_date_granularity(until_date)

        if from_granularity != until_granularity:
            raise ValueError(
                "from and until dates must use the same granularity. "
                f"Got {from_granularity} and {until_granularity}"
            )

        # Compare dates (string comparison works for ISO format)
        if from_date > until_date:
            raise ValueError(
                f"from date ({from_date}) must be <= until date ({until_date})"
            )
