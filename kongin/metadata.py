"""
Metadata containers for OAI-PMH records.

Provides typed access to metadata fields while remaining schema-agnostic.
"""

from dataclasses import dataclass
from typing import Optional, List, Iterator, Dict, Tuple
from collections import defaultdict


@dataclass
class MetadataValue:
    """
    Single metadata value with namespace awareness.

    Attributes:
        value: The actual text content
        namespace: Full namespace URI (e.g., 'http://purl.org/dc/terms/')
        prefix: Namespace prefix (e.g., 'dcterms')
        language: XML lang attribute if present
    """
    value: str
    namespace: Optional[str] = None
    prefix: Optional[str] = None
    language: Optional[str] = None

    def __str__(self) -> str:
        return self.value


# Standard DC prefixes to check for convenience properties
_DC_PREFIXES: Tuple[str, ...] = ('dc', 'dcterms', '')


class Metadata:
    """
    Flat metadata container with typed access.

    Stores values keyed by qualified name (prefix:localname).
    Provides list access since Dublin Core fields are repeatable.

    Example:
        >>> metadata.get('dc:title')
        'Article Title'
        >>> metadata.get_all('dc:creator')
        ['Author One', 'Author Two']
        >>> metadata.title  # Convenience property
        'Article Title'
    """

    def __init__(self) -> None:
        self._data: Dict[str, List[MetadataValue]] = defaultdict(list)

    def add(self, key: str, value: MetadataValue) -> None:
        """Add a value to a metadata field."""
        self._data[key].append(value)

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get first value for a key (convenience for single-value fields)."""
        values = self._data.get(key, [])
        return values[0].value if values else default

    def get_all(self, key: str) -> List[str]:
        """Get all values for a key as strings."""
        return [v.value for v in self._data.get(key, [])]

    def get_values(self, key: str) -> List[MetadataValue]:
        """Get all MetadataValue objects for a key."""
        return self._data.get(key, [])

    def keys(self) -> Iterator[str]:
        """All metadata keys."""
        return iter(self._data.keys())

    def items(self) -> Iterator[Tuple[str, List[str]]]:
        """Iterate over (key, values) pairs."""
        for key in self._data:
            yield key, self.get_all(key)

    def __getitem__(self, key: str) -> List[str]:
        """Dict-like access returns list of string values."""
        return self.get_all(key)

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __len__(self) -> int:
        return len(self._data)

    def __bool__(self) -> bool:
        return len(self._data) > 0

    def to_dict(self) -> Dict[str, List[str]]:
        """Export as simple dict for JSON serialization."""
        return {k: self.get_all(k) for k in self._data}

    def to_flat_dict(self) -> Dict[str, str]:
        """Export as flat dict (first value only for each key)."""
        return {k: self.get(k) for k in self._data}

    # ==================== Helper methods ====================

    def _get_first(self, local_name: str, extra_keys: Tuple[str, ...] = ()) -> Optional[str]:
        """Get first value checking dc/dcterms prefixes and extra keys."""
        for prefix in _DC_PREFIXES:
            key = f'{prefix}:{local_name}' if prefix else local_name
            value = self.get(key)
            if value:
                return value
        for key in extra_keys:
            value = self.get(key)
            if value:
                return value
        return None

    def _get_all_from(self, local_name: str, extra_keys: Tuple[str, ...] = ()) -> List[str]:
        """Get all values checking dc/dcterms prefixes and extra keys."""
        result: List[str] = []
        for prefix in _DC_PREFIXES:
            key = f'{prefix}:{local_name}' if prefix else local_name
            result.extend(self.get_all(key))
        for key in extra_keys:
            result.extend(self.get_all(key))
        return result

    # ==================== Convenience properties ====================

    @property
    def title(self) -> Optional[str]:
        """First title value."""
        return self._get_first('title')

    @property
    def titles(self) -> List[str]:
        """All title values."""
        return self._get_all_from('title')

    @property
    def creators(self) -> List[str]:
        """All creator/author values."""
        return self._get_all_from('creator')

    @property
    def contributors(self) -> List[str]:
        """All contributor values."""
        return self._get_all_from('contributor')

    @property
    def subjects(self) -> List[str]:
        """All subject/keyword values."""
        return self._get_all_from('subject')

    @property
    def description(self) -> Optional[str]:
        """First description or abstract."""
        return self._get_first('description', ('dcterms:abstract',))

    @property
    def descriptions(self) -> List[str]:
        """All descriptions."""
        return self._get_all_from('description', ('dcterms:abstract',))

    @property
    def publisher(self) -> Optional[str]:
        """First publisher."""
        return self._get_first('publisher')

    @property
    def date(self) -> Optional[str]:
        """First date value."""
        return self._get_first('date', ('dcterms:issued',))

    @property
    def dates(self) -> List[str]:
        """All date values."""
        return self._get_all_from('date', ('dcterms:issued',))

    @property
    def types(self) -> List[str]:
        """All type values."""
        return self._get_all_from('type')

    @property
    def identifiers(self) -> List[str]:
        """All identifier values (DOI, URI, ISBN, etc.)."""
        return self._get_all_from('identifier')

    @property
    def languages(self) -> List[str]:
        """All language values."""
        return self._get_all_from('language')

    @property
    def rights(self) -> List[str]:
        """All rights values."""
        return self._get_all_from('rights', ('dcterms:license',))

    @property
    def sources(self) -> List[str]:
        """All source values."""
        return self._get_all_from('source')

    @property
    def relations(self) -> List[str]:
        """All relation values."""
        return self._get_all_from('relation')
