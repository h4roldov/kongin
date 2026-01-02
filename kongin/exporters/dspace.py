"""
DSpace REST API exporter.

Converts OAI-PMH records to JSON format compatible with DSpace REST API.
Supports DSpace versions 7, 8, 9, 10 and future versions with compatible API.
"""

from typing import Dict, List, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..record import Record


class DSpaceExporter:
    """
    Export OAI-PMH records to DSpace 7+ REST API format.

    Produces JSON compatible with:
    - POST /api/core/items (direct item creation)
    - PATCH /api/submission/workspaceitems (workspace submission)

    Example:
        >>> exporter = DSpaceExporter()
        >>> item = exporter.export_record(record)
        >>> # Or with custom field mapping:
        >>> exporter = DSpaceExporter({'oaire:version': 'local.version'})
    """

    # Default mapping from common OAI-PMH prefixes to DSpace metadata fields
    DEFAULT_MAPPING = {
        # Dublin Core
        'dc:title': 'dc.title',
        'dcterms:title': 'dc.title',
        'title': 'dc.title',

        'dc:creator': 'dc.contributor.author',
        'dcterms:creator': 'dc.contributor.author',
        'creator': 'dc.contributor.author',

        'dc:contributor': 'dc.contributor.other',
        'dcterms:contributor': 'dc.contributor.other',
        'contributor': 'dc.contributor.other',

        'dc:subject': 'dc.subject',
        'dcterms:subject': 'dc.subject',
        'subject': 'dc.subject',

        'dc:description': 'dc.description',
        'dcterms:description': 'dc.description',
        'description': 'dc.description',
        'dcterms:abstract': 'dc.description.abstract',

        'dc:publisher': 'dc.publisher',
        'dcterms:publisher': 'dc.publisher',
        'publisher': 'dc.publisher',

        'dc:date': 'dc.date.issued',
        'dcterms:date': 'dc.date.issued',
        'dcterms:issued': 'dc.date.issued',
        'date': 'dc.date.issued',

        'dc:type': 'dc.type',
        'dcterms:type': 'dc.type',
        'type': 'dc.type',

        'dc:format': 'dc.format',
        'dcterms:format': 'dc.format',
        'format': 'dc.format',

        'dc:identifier': 'dc.identifier',
        'dcterms:identifier': 'dc.identifier.uri',
        'identifier': 'dc.identifier',

        'dc:source': 'dc.source',
        'dcterms:source': 'dc.source',
        'source': 'dc.source',

        'dc:language': 'dc.language.iso',
        'dcterms:language': 'dc.language.iso',
        'language': 'dc.language.iso',

        'dc:rights': 'dc.rights',
        'dcterms:rights': 'dc.rights',
        'dcterms:license': 'dc.rights.license',
        'dcterms:accessRights': 'dc.rights.accessRights',
        'rights': 'dc.rights',

        'dc:relation': 'dc.relation',
        'dcterms:relation': 'dc.relation',
        'relation': 'dc.relation',

        'dc:coverage': 'dc.coverage',
        'dcterms:coverage': 'dc.coverage',
        'dcterms:spatial': 'dc.coverage.spatial',
        'dcterms:temporal': 'dc.coverage.temporal',

        # OpenAIRE
        'oaire:resourceType': 'dc.type',
        'oaire:version': 'dc.description.version',
        'oaire:citationTitle': 'oaire.citation.title',
        'oaire:citationVolume': 'oaire.citation.volume',
        'oaire:citationIssue': 'oaire.citation.issue',
        'oaire:citationStartPage': 'oaire.citation.startPage',
        'oaire:citationEndPage': 'oaire.citation.endPage',
        'oaire:file': 'dc.identifier.uri',
        'oaire:fundingStream': 'oaire.fundingStream',
        'oaire:awardNumber': 'oaire.awardNumber',
        'oaire:awardTitle': 'oaire.awardTitle',
        'oaire:awardURI': 'oaire.awardURI',

        # DataCite
        'datacite:identifier': 'dc.identifier',
        'datacite:creator': 'dc.contributor.author',
        'datacite:title': 'dc.title',
        'datacite:subject': 'dc.subject',
        'datacite:date': 'dc.date.issued',
        'datacite:rights': 'dc.rights',
    }

    def __init__(self, custom_mapping: Optional[Dict[str, str]] = None):
        """
        Initialize exporter with optional custom field mapping.

        Args:
            custom_mapping: Dict mapping source fields to DSpace fields.
                           Extends/overrides default mapping.

        Example:
            >>> exporter = DSpaceExporter({
            ...     'local:category': 'local.category',
            ...     'oaire:citationVolume': 'local.citation.volume',
            ... })
        """
        self.field_mapping = self.DEFAULT_MAPPING.copy()
        if custom_mapping:
            self.field_mapping.update(custom_mapping)

    @classmethod
    def record_to_item(
        cls,
        record: 'Record',
        custom_mapping: Optional[Dict[str, str]] = None
    ) -> dict:
        """
        Convert a single Record to DSpace item JSON.

        Args:
            record: Record to convert
            custom_mapping: Optional custom field mapping

        Returns:
            Dict suitable for POST /api/core/items
        """
        exporter = cls(custom_mapping)
        return exporter.export_record(record)

    def export_record(self, record: 'Record') -> dict:
        """
        Convert a Record to DSpace item JSON.

        Args:
            record: Record to convert

        Returns:
            Dict suitable for POST /api/core/items
        """
        metadata = self._build_metadata(record)

        return {
            'name': record.title or '',
            'metadata': metadata,
            'inArchive': True,
            'discoverable': True,
            'withdrawn': False,
            'type': 'item'
        }

    def _build_metadata(self, record: 'Record') -> Dict[str, List[dict]]:
        """Build DSpace metadata structure from Record."""
        result: Dict[str, List[dict]] = {}

        for source_key in record.metadata.keys():
            # Map to DSpace field name
            target_key = self.field_mapping.get(source_key)

            if target_key is None:
                # No mapping - normalize source key to DSpace format
                target_key = self._normalize_field_name(source_key)

            values = record.metadata.get_values(source_key)

            for value in values:
                if target_key not in result:
                    result[target_key] = []

                result[target_key].append({
                    'value': value.value,
                    'language': value.language,
                    'authority': None,
                    'confidence': -1
                })

        return result

    def _normalize_field_name(self, key: str) -> str:
        """
        Normalize field name for DSpace.

        Converts prefix:localname to schema.element format.
        Unknown prefixes are preserved as-is.

        Examples:
            'dcterms:creator' -> already mapped
            'custom:field' -> 'custom.field'
            'localfield' -> 'local.localfield'
        """
        if ':' in key:
            prefix, local = key.split(':', 1)
            # Convert common namespace prefixes
            if prefix in ('dc', 'dcterms'):
                return f"dc.{local}"
            return f"{prefix}.{local}"
        return f"local.{key}"

    def export_records(self, records: List['Record']) -> List[dict]:
        """
        Export multiple records to DSpace item format.

        Args:
            records: List of Records to convert

        Returns:
            List of dicts suitable for DSpace batch import
        """
        return [self.export_record(r) for r in records]

    def to_workspace_patch(
        self,
        record: 'Record',
        section: str = 'traditionalpageone'
    ) -> List[dict]:
        """
        Generate JSON PATCH operations for workspace item submission.

        Args:
            record: Record to convert
            section: Submission section name

        Returns:
            List of patch operations for PATCH /api/submission/workspaceitems/{id}
        """
        operations = []
        metadata = self._build_metadata(record)

        for field_name, values in metadata.items():
            operations.append({
                'op': 'add',
                'path': f'/sections/{section}/{field_name}',
                'value': values
            })

        return operations

    def to_json(self, records: List['Record'], indent: int = 2) -> str:
        """
        Export records to JSON string.

        Args:
            records: List of Records to export
            indent: JSON indentation level

        Returns:
            JSON string
        """
        import json
        items = self.export_records(records)
        return json.dumps(items, indent=indent, ensure_ascii=False)

    def save_json(
        self,
        records: List['Record'],
        filepath: str,
        indent: int = 2
    ) -> None:
        """
        Export records to JSON file.

        Args:
            records: List of Records to export
            filepath: Output file path
            indent: JSON indentation level
        """
        import json
        items = self.export_records(records)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(items, f, indent=indent, ensure_ascii=False)
