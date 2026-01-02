"""
Kongin - A Python OAI-PMH client for harvesting repositories.

Quick usage:
    >>> import kongin
    >>> records = kongin.harvest('https://repo.example.org/oai')
    >>> for r in records:
    ...     print(r.title)

Full usage:
    >>> from kongin import OAIClient
    >>> client = OAIClient('https://repo.example.org/oai')
    >>> for record in client.list_records(metadata_prefix='oai_dc'):
    ...     print(record.title, record.creators)
    ...     item = record.to_dspace()
"""

from typing import Iterator, Optional, List

from .client import OAIClient, OAIResponse
from .record import Record, RecordSet
from .metadata import Metadata, MetadataValue
from .parser import OAIParser
from .exceptions import (
    OAIClientError,
    OAIRequestError,
    OAIResponseError,
    OAIProtocolError,
    BadArgumentError,
    BadVerbError,
    BadResumptionTokenError,
    CannotDisseminateFormatError,
    IdDoesNotExistError,
    NoRecordsMatchError,
    NoMetadataFormatsError,
    NoSetHierarchyError,
)
from .exporters import DSpaceExporter
from .dspace_client import DSpaceClient, DSpaceAuthError, DSpaceUploadError

__version__ = '0.4.0'

__all__ = [
    # Convenience functions
    'harvest',
    'connect',
    'export_to_dspace',

    # Main client
    'OAIClient',
    'OAIResponse',

    # Records
    'Record',
    'RecordSet',

    # Metadata
    'Metadata',
    'MetadataValue',

    # Parser
    'OAIParser',

    # Exporters
    'DSpaceExporter',

    # Exceptions
    'OAIClientError',
    'OAIRequestError',
    'OAIResponseError',
    'OAIProtocolError',
    'BadArgumentError',
    'BadVerbError',
    'BadResumptionTokenError',
    'CannotDisseminateFormatError',
    'IdDoesNotExistError',
    'NoRecordsMatchError',
    'NoMetadataFormatsError',
    'NoSetHierarchyError',

    # DSpace client
    'DSpaceClient',
    'DSpaceAuthError',
    'DSpaceUploadError',
]


# ==================== Convenience Functions ====================

def connect(url: str, **kwargs) -> OAIClient:
    """
    Create an OAI-PMH client connection.

    Args:
        url: OAI-PMH endpoint URL
        **kwargs: Additional arguments passed to OAIClient

    Returns:
        OAIClient instance

    Example:
        >>> import kongin
        >>> client = kongin.connect('https://repo.example.org/oai')
        >>> info = client.identify()
    """
    return OAIClient(url, **kwargs)


def harvest(
    url: str,
    metadata_prefix: str = 'oai_dc',
    set_spec: Optional[str] = None,
    from_date: Optional[str] = None,
    until_date: Optional[str] = None,
    limit: Optional[int] = None,
    **kwargs
) -> List[Record]:
    """
    Harvest records from an OAI-PMH repository.

    Args:
        url: OAI-PMH endpoint URL
        metadata_prefix: Metadata format (default: oai_dc)
        set_spec: Optional set to harvest from
        from_date: Optional start date (YYYY-MM-DD)
        until_date: Optional end date (YYYY-MM-DD)
        limit: Optional maximum number of records to return
        **kwargs: Additional arguments passed to OAIClient

    Returns:
        List of Record objects

    Example:
        >>> import kongin
        >>> records = kongin.harvest('https://repo.example.org/oai')
        >>> for r in records:
        ...     print(r.title)

        >>> # With options
        >>> records = kongin.harvest(
        ...     'https://repo.example.org/oai',
        ...     metadata_prefix='xoai',
        ...     set_spec='articles',
        ...     limit=100
        ... )
    """
    client = OAIClient(url, **kwargs)
    records = []

    for i, record in enumerate(client.list_records(
        metadata_prefix=metadata_prefix,
        set_spec=set_spec,
        from_date=from_date,
        until_date=until_date
    )):
        records.append(record)
        if limit and i + 1 >= limit:
            break

    return records


def export_to_dspace(
    records: List[Record],
    filepath: Optional[str] = None,
    custom_mapping: Optional[dict] = None
) -> str:
    """
    Export records to DSpace JSON format.

    Args:
        records: List of Record objects to export
        filepath: Optional file path to save JSON
        custom_mapping: Optional custom field mapping

    Returns:
        JSON string

    Example:
        >>> import kongin
        >>> records = kongin.harvest('https://repo.example.org/oai', limit=10)
        >>> json_data = kongin.export_to_dspace(records)
        >>> # Or save to file
        >>> kongin.export_to_dspace(records, 'output.json')
    """
    exporter = DSpaceExporter(custom_mapping)

    if filepath:
        exporter.save_json(records, filepath)

    return exporter.to_json(records)
