"""
OAI-PMH XML parser.

Parses OAI-PMH XML responses into typed objects.
Schema-agnostic: handles any metadata format by flattening to key-value pairs.
"""

from typing import Tuple, Optional, List, NamedTuple

from lxml import etree

from .record import Record, RecordSet
from .metadata import Metadata, MetadataValue
from .exceptions import OAI_ERROR_MAP, OAIProtocolError


class HeaderInfo(NamedTuple):
    """Parsed OAI-PMH record header."""
    identifier: str
    datestamp: str
    set_specs: List[str]
    deleted: bool


class OAIParser:
    """
    Parses OAI-PMH XML responses into typed objects.

    Handles any metadata format by flattening XML to key-value pairs.
    Only leaf elements (with text, no children) become metadata values.

    Example:
        >>> parser = OAIParser()
        >>> result = parser.parse_records(xml_content)
        >>> for record in result:
        ...     print(record.title)
    """

    OAI_NS = 'http://www.openarchives.org/OAI/2.0/'
    XML_LANG_ATTR = '{http://www.w3.org/XML/1998/namespace}lang'

    def __init__(self, preserve_raw: bool = False) -> None:
        """
        Initialize parser.

        Args:
            preserve_raw: If True, stores original XML in record.raw_xml
        """
        self.preserve_raw = preserve_raw
        self._parser = etree.XMLParser(resolve_entities=False)

    def _oai(self, tag: str) -> str:
        """Build OAI namespace-qualified tag."""
        return f'{{{self.OAI_NS}}}{tag}'

    def _parse_xml(self, xml_content: str):
        """Parse XML string to lxml element."""
        if isinstance(xml_content, str):
            xml_content = xml_content.encode('utf-8')
        return etree.fromstring(xml_content, self._parser)

    def _check_oai_errors(self, root) -> None:
        """
        Check for OAI-PMH error elements in response and raise appropriate exception.

        OAI-PMH returns errors in XML body, not as HTTP status codes.
        The error element contains a 'code' attribute and optional message text.

        Args:
            root: Parsed lxml root element

        Raises:
            OAIProtocolError: If an error element is found in the response
        """
        errors = root.findall(self._oai('error'))
        if errors:
            # Get first error (most responses only have one)
            error = errors[0]
            code = error.get('code', 'unknown')
            message = error.text.strip() if error.text else ''

            # Get specific exception class or use base OAIProtocolError
            exc_class = OAI_ERROR_MAP.get(code, OAIProtocolError)

            if exc_class == OAIProtocolError:
                raise OAIProtocolError(code, message)
            else:
                raise exc_class(message)

    def _parse_clark_notation(self, tag: str) -> Tuple[Optional[str], str]:
        """
        Parse Clark notation {namespace}localname.

        Returns:
            Tuple of (namespace_uri, local_name). namespace_uri is None if not present.
        """
        if tag.startswith('{'):
            ns_uri, local_name = tag[1:].split('}', 1)
            return ns_uri, local_name
        return None, tag

    def _parse_header(self, header) -> HeaderInfo:
        """
        Parse OAI-PMH record header element.

        Args:
            header: lxml Element for the header

        Returns:
            HeaderInfo namedtuple with identifier, datestamp, set_specs, deleted
        """
        status = header.get('status', '')
        identifier = header.findtext(self._oai('identifier'), '')
        datestamp = header.findtext(self._oai('datestamp'), '')
        set_specs = [
            elem.text for elem in header.findall(self._oai('setSpec'))
            if elem.text
        ]
        return HeaderInfo(
            identifier=identifier,
            datestamp=datestamp,
            set_specs=set_specs,
            deleted=(status == 'deleted')
        )

    def _extract_resumption_token(self, root) -> Optional[str]:
        """Extract resumption token if present."""
        token_elem = root.find(f'.//{self._oai("resumptionToken")}')
        if token_elem is not None and token_elem.text:
            return token_elem.text.strip()
        return None

    def _extract_pagination_info(self, root) -> Tuple[Optional[int], Optional[int]]:
        """Extract completeListSize and cursor from resumptionToken."""
        token_elem = root.find(f'.//{self._oai("resumptionToken")}')
        if token_elem is None:
            return None, None

        complete_size = token_elem.get('completeListSize')
        cursor = token_elem.get('cursor')

        return (
            int(complete_size) if complete_size else None,
            int(cursor) if cursor else None
        )

    # ==================== Record parsing ====================

    def parse_records(self, xml_content: str) -> RecordSet:
        """
        Parse ListRecords or GetRecord response.

        Args:
            xml_content: Raw XML string from OAI-PMH response

        Returns:
            RecordSet containing parsed records and pagination info

        Raises:
            OAIProtocolError: If the response contains an OAI-PMH error
        """
        root = self._parse_xml(xml_content)
        self._check_oai_errors(root)

        records = []
        for record_elem in root.findall(f'.//{self._oai("record")}'):
            record = self._parse_record(record_elem)
            if record:
                records.append(record)

        resumption_token = self._extract_resumption_token(root)
        complete_list_size, cursor = self._extract_pagination_info(root)

        return RecordSet(
            records=records,
            resumption_token=resumption_token,
            complete_list_size=complete_list_size,
            cursor=cursor
        )

    def _parse_record(self, record_elem) -> Optional[Record]:
        """Parse a single record element."""
        header_elem = record_elem.find(self._oai('header'))
        if header_elem is None:
            return None

        header = self._parse_header(header_elem)

        # Parse metadata (any format)
        metadata = Metadata()
        metadata_elem = record_elem.find(self._oai('metadata'))
        if metadata_elem is not None and not header.deleted:
            self._extract_metadata(metadata_elem, metadata)

        raw_xml = None
        if self.preserve_raw:
            raw_xml = etree.tostring(record_elem, encoding='unicode')

        return Record(
            identifier=header.identifier,
            datestamp=header.datestamp,
            metadata=metadata,
            set_specs=header.set_specs,
            deleted=header.deleted,
            raw_xml=raw_xml
        )

    def _extract_metadata(self, elem, metadata: Metadata) -> None:
        """
        Recursively extract metadata from ANY XML structure.

        Strategy: Only leaf elements (with text, no children) become values.
        Non-leaf elements are traversed but not stored.
        """
        for child in list(elem):
            children = list(child)
            has_text = child.text and child.text.strip()

            if has_text and not children:
                # Leaf node with text - extract as metadata value
                value = self._create_metadata_value(child)
                key = self._get_qualified_name(child)
                metadata.add(key, value)

            if children:
                # Non-leaf - recurse
                self._extract_metadata(child, metadata)

    def _create_metadata_value(self, elem) -> MetadataValue:
        """Create MetadataValue from element."""
        ns_uri, local_name = self._parse_clark_notation(elem.tag)

        return MetadataValue(
            value=elem.text.strip() if elem.text else '',
            namespace=ns_uri,
            prefix=elem.prefix,
            language=elem.get(self.XML_LANG_ATTR)
        )

    def _get_qualified_name(self, elem) -> str:
        """Get prefix:localname or just localname."""
        _, local_name = self._parse_clark_notation(elem.tag)

        if elem.prefix:
            return f"{elem.prefix}:{local_name}"
        return local_name

    # ==================== Verb-specific parsers ====================

    def parse_identify(self, xml_content: str) -> dict:
        """
        Parse Identify response.

        Returns:
            Dict with repository information.

        Raises:
            OAIProtocolError: If the response contains an OAI-PMH error
        """
        root = self._parse_xml(xml_content)
        self._check_oai_errors(root)
        identify = root.find(self._oai('Identify'))

        if identify is None:
            raise ValueError("Identify element not found in response")

        admin_emails = [
            elem.text for elem in identify.findall(self._oai('adminEmail'))
            if elem.text
        ]

        return {
            'repository_name': identify.findtext(self._oai('repositoryName')),
            'base_url': identify.findtext(self._oai('baseURL')),
            'protocol_version': identify.findtext(self._oai('protocolVersion')),
            'admin_emails': admin_emails,
            'earliest_datestamp': identify.findtext(self._oai('earliestDatestamp')),
            'deleted_record': identify.findtext(self._oai('deletedRecord')),
            'granularity': identify.findtext(self._oai('granularity')),
        }

    def parse_sets(self, xml_content: str) -> dict:
        """
        Parse ListSets response.

        Returns:
            Dict with 'sets' (list of set dicts) and 'resumption_token'.

        Raises:
            OAIProtocolError: If the response contains an OAI-PMH error
        """
        root = self._parse_xml(xml_content)
        self._check_oai_errors(root)
        list_sets = root.find(self._oai('ListSets'))

        if list_sets is None:
            raise ValueError("ListSets element not found in response")

        sets = [
            {
                'set_spec': set_elem.findtext(self._oai('setSpec')),
                'set_name': set_elem.findtext(self._oai('setName')),
            }
            for set_elem in list_sets.findall(self._oai('set'))
        ]

        return {
            'sets': sets,
            'resumption_token': self._extract_resumption_token(root),
        }

    def parse_metadata_formats(self, xml_content: str) -> dict:
        """
        Parse ListMetadataFormats response.

        Returns:
            Dict with 'formats' (list of format dicts) and 'resumption_token'.

        Raises:
            OAIProtocolError: If the response contains an OAI-PMH error
        """
        root = self._parse_xml(xml_content)
        self._check_oai_errors(root)
        list_formats = root.find(self._oai('ListMetadataFormats'))

        if list_formats is None:
            raise ValueError("ListMetadataFormats element not found in response")

        formats = [
            {
                'prefix': fmt.findtext(self._oai('metadataPrefix')),
                'schema': fmt.findtext(self._oai('schema')),
                'namespace': fmt.findtext(self._oai('metadataNamespace')),
            }
            for fmt in list_formats.findall(self._oai('metadataFormat'))
        ]

        return {
            'formats': formats,
            'resumption_token': self._extract_resumption_token(root),
        }

    def parse_identifiers(self, xml_content: str) -> RecordSet:
        """
        Parse ListIdentifiers response.

        Returns:
            RecordSet with records containing only header info (no metadata).

        Raises:
            OAIProtocolError: If the response contains an OAI-PMH error
        """
        root = self._parse_xml(xml_content)
        self._check_oai_errors(root)

        records = [
            Record(
                identifier=header.identifier,
                datestamp=header.datestamp,
                metadata=Metadata(),
                set_specs=header.set_specs,
                deleted=header.deleted,
            )
            for header_elem in root.findall(f'.//{self._oai("header")}')
            for header in [self._parse_header(header_elem)]
        ]

        resumption_token = self._extract_resumption_token(root)
        complete_list_size, cursor = self._extract_pagination_info(root)

        return RecordSet(
            records=records,
            resumption_token=resumption_token,
            complete_list_size=complete_list_size,
            cursor=cursor
        )
