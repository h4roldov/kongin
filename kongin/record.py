"""
Record and RecordSet classes for OAI-PMH responses.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Iterator, TYPE_CHECKING

from .metadata import Metadata

if TYPE_CHECKING:
    from .exporters.dspace import DSpaceExporter

# Properties that are explicitly defined for IDE autocompletion
_METADATA_PROPERTIES = frozenset({
    'title', 'titles', 'creators', 'contributors', 'subjects',
    'description', 'descriptions', 'publisher', 'date', 'dates',
    'types', 'identifiers', 'languages', 'rights', 'sources', 'relations'
})


@dataclass
class Record:
    """
    A single OAI-PMH record with typed metadata access.

    Provides both structured access (record.title) and
    flexible dict access (record.metadata['oaire:citationVolume']).

    Common metadata properties are available directly on the record:
    - title, titles, creators, contributors, subjects
    - description, descriptions, publisher, date, dates
    - types, identifiers, languages, rights, sources, relations

    Example:
        >>> record.title
        'Article Title'
        >>> record.creators
        ['Author One', 'Author Two']
        >>> record.metadata.get('oaire:citationVolume')
        '15'
    """
    identifier: str
    datestamp: str
    metadata: Metadata
    set_specs: List[str] = field(default_factory=list)
    deleted: bool = False
    raw_xml: Optional[str] = None

    def __getattr__(self, name: str):
        """Delegate metadata property access to the metadata object."""
        if name in _METADATA_PROPERTIES:
            return getattr(self.metadata, name)
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    def to_dict(self) -> dict:
        """
        Flat dictionary representation.

        Returns:
            Dict with identifier, datestamp, set_specs, deleted, and metadata.
        """
        return {
            'identifier': self.identifier,
            'datestamp': self.datestamp,
            'set_specs': self.set_specs,
            'deleted': self.deleted,
            'metadata': self.metadata.to_dict()
        }

    def to_flat_dict(self) -> dict:
        """
        Flattened dictionary with single values.

        Returns:
            Dict with identifier, datestamp, and flat metadata (first values only).
        """
        result = {
            'identifier': self.identifier,
            'datestamp': self.datestamp,
        }
        result.update(self.metadata.to_flat_dict())
        return result

    def to_dspace(self, custom_mapping: Optional[dict] = None) -> dict:
        """
        Export in DSpace 7+ REST API format.

        Args:
            custom_mapping: Optional dict mapping source fields to DSpace fields.

        Returns:
            Dict compatible with POST /api/core/items
        """
        from .exporters.dspace import DSpaceExporter
        return DSpaceExporter.record_to_item(self, custom_mapping)


@dataclass
class RecordSet:
    """
    Container for OAI-PMH record results with pagination support.

    Example:
        >>> result = client.list_records_page(metadata_prefix='oai_dc')
        >>> for record in result:
        ...     print(record.title)
        >>> if result.has_more:
        ...     next_page = client.resume(result.resumption_token)
    """
    records: List[Record] = field(default_factory=list)
    resumption_token: Optional[str] = None
    complete_list_size: Optional[int] = None
    cursor: Optional[int] = None

    def __iter__(self) -> Iterator[Record]:
        return iter(self.records)

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> Record:
        return self.records[index]

    def __bool__(self) -> bool:
        return len(self.records) > 0

    @property
    def has_more(self) -> bool:
        """True if there are more pages to fetch."""
        return self.resumption_token is not None and self.resumption_token != ''

    def to_dict_list(self) -> List[dict]:
        """Export all records as flat dictionaries."""
        return [r.to_dict() for r in self.records]

    def to_dspace_items(self, custom_mapping: Optional[dict] = None) -> List[dict]:
        """Export all records in DSpace format."""
        return [r.to_dspace(custom_mapping) for r in self.records]
