"""
OAI-PMH client for harvesting metadata from repositories.

Fully compliant with OAI-PMH v2.0 specification:
https://www.openarchives.org/OAI/openarchivesprotocol.html
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Iterator, List
import time
import warnings

import requests

from .parser import OAIParser
from .record import Record, RecordSet
from .exceptions import OAIRequestError, OAIResponseError
from .utils import validate_date_range


@dataclass
class OAIResponse:
    """
    Raw response wrapper for backward compatibility.

    Provides access to raw XML and parsed records.
    """
    params: dict
    http_response: requests.Response
    _parser: OAIParser = field(default_factory=OAIParser, repr=False)

    @property
    def raw(self) -> str:
        """Raw XML response text."""
        return self.http_response.text

    @property
    def text(self) -> str:
        """Alias for raw."""
        return self.http_response.text

    @property
    def records(self) -> RecordSet:
        """Parse response as records."""
        return self._parser.parse_records(self.http_response.text)

    @property
    def dict(self) -> dict:
        """Parse to dictionary structure."""
        result = self.records
        return {
            'records': result.to_dict_list(),
            'resumption_token': result.resumption_token,
            'complete_list_size': result.complete_list_size,
        }


@dataclass
class OAIClient:
    """
    OAI-PMH client for harvesting metadata from repositories.

    Fully compliant with OAI-PMH v2.0 specification.
    Provides both high-level typed API and low-level raw access.

    Example:
        >>> client = OAIClient('https://repo.example.org/oai')
        >>> for record in client.list_records(metadata_prefix='oai_dc'):
        ...     print(record.title, record.creators)
        >>> dspace_json = record.to_dspace()
    """

    url: str
    http_method: str = 'GET'
    timeout: int = 30
    max_retries: int = 3
    retry_on_503: bool = True
    requests_args: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.url:
            raise ValueError("URL must not be empty")
        if not self.url.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        if self.http_method not in ('GET', 'POST'):
            raise ValueError("HTTP method must be 'GET' or 'POST'")

        self._parser = OAIParser()
        self._session = requests.Session()

    def _request(self, **params) -> requests.Response:
        """
        Execute OAI-PMH request.

        Args:
            **params: OAI-PMH parameters (verb, metadataPrefix, etc.)

        Returns:
            requests.Response object

        Raises:
            OAIRequestError: If request fails after retries
        """
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                if self.http_method == 'GET':
                    response = self._session.get(
                        self.url,
                        params=params,
                        timeout=self.timeout,
                        **self.requests_args
                    )
                else:
                    response = self._session.post(
                        self.url,
                        data=params,
                        timeout=self.timeout,
                        **self.requests_args
                    )

                # Handle HTTP 503 Service Unavailable with Retry-After
                if response.status_code == 503 and self.retry_on_503:
                    retry_after = response.headers.get('Retry-After')
                    if retry_after and attempt < self.max_retries:
                        try:
                            wait_seconds = int(retry_after)
                        except ValueError:
                            wait_seconds = 60  # Default wait
                        time.sleep(min(wait_seconds, 300))  # Max 5 minutes
                        continue

                response.raise_for_status()
                return response

            except requests.RequestException as e:
                last_error = e
                if attempt < self.max_retries:
                    continue
                raise OAIRequestError(f"Request failed: {e}") from e

        raise OAIRequestError(f"Request failed after {self.max_retries} retries: {last_error}")

    def _build_list_params(
        self,
        verb: str,
        metadata_prefix: str,
        set_spec: Optional[str],
        from_date: Optional[str],
        until_date: Optional[str],
    ) -> Dict[str, str]:
        """Build params dict for ListRecords/ListIdentifiers."""
        # Validate date range
        validate_date_range(from_date, until_date)

        params = {'verb': verb, 'metadataPrefix': metadata_prefix}
        if set_spec:
            params['set'] = set_spec
        if from_date:
            params['from'] = from_date
        if until_date:
            params['until'] = until_date
        return params

    # ==================== High-level API ====================

    def identify(self) -> dict:
        """
        Get repository information (OAI-PMH Identify verb).

        Returns:
            Dict with repository_name, base_url, protocol_version,
            admin_emails, earliest_datestamp, deleted_record, granularity.

        Raises:
            OAIProtocolError: If the repository returns an error
        """
        response = self._request(verb='Identify')
        return self._parser.parse_identify(response.text)

    def list_sets(self) -> Iterator[dict]:
        """
        Iterate over all sets with automatic pagination (OAI-PMH ListSets verb).

        Yields:
            Dicts with set_spec and set_name.

        Raises:
            NoSetHierarchyError: If the repository does not support sets
        """
        params: Dict[str, str] = {'verb': 'ListSets'}

        while True:
            response = self._request(**params)
            result = self._parser.parse_sets(response.text)

            yield from result['sets']

            if not result.get('resumption_token'):
                break

            params = {'verb': 'ListSets', 'resumptionToken': result['resumption_token']}

    def list_sets_page(self, resumption_token: Optional[str] = None) -> dict:
        """
        Get a single page of sets.

        Args:
            resumption_token: Token from previous page

        Returns:
            Dict with 'sets' list and 'resumption_token'.
        """
        if resumption_token:
            params = {'verb': 'ListSets', 'resumptionToken': resumption_token}
        else:
            params = {'verb': 'ListSets'}

        response = self._request(**params)
        return self._parser.parse_sets(response.text)

    def list_metadata_formats(self, identifier: Optional[str] = None) -> Iterator[dict]:
        """
        Iterate over metadata formats with automatic pagination.

        Args:
            identifier: Optional record identifier to check formats for.

        Yields:
            Dicts with prefix, schema, and namespace.

        Raises:
            IdDoesNotExistError: If the identifier does not exist
            NoMetadataFormatsError: If no formats are available
        """
        params: Dict[str, str] = {'verb': 'ListMetadataFormats'}
        if identifier:
            params['identifier'] = identifier

        while True:
            response = self._request(**params)
            result = self._parser.parse_metadata_formats(response.text)

            yield from result['formats']

            if not result.get('resumption_token'):
                break

            params = {'verb': 'ListMetadataFormats', 'resumptionToken': result['resumption_token']}

    def list_metadata_formats_page(
        self,
        identifier: Optional[str] = None,
        resumption_token: Optional[str] = None
    ) -> dict:
        """
        Get a single page of metadata formats.

        Args:
            identifier: Optional record identifier
            resumption_token: Token from previous page

        Returns:
            Dict with 'formats' list and 'resumption_token'.
        """
        if resumption_token:
            params = {'verb': 'ListMetadataFormats', 'resumptionToken': resumption_token}
        else:
            params: Dict[str, str] = {'verb': 'ListMetadataFormats'}
            if identifier:
                params['identifier'] = identifier

        response = self._request(**params)
        return self._parser.parse_metadata_formats(response.text)

    def get_record(
        self,
        identifier: str,
        metadata_prefix: str = 'oai_dc'
    ) -> Record:
        """
        Retrieve a single record (OAI-PMH GetRecord verb).

        Args:
            identifier: Record identifier (e.g., 'oai:repo.example.org:123')
            metadata_prefix: Metadata format (default: oai_dc)

        Returns:
            Record object with typed metadata access.

        Raises:
            IdDoesNotExistError: If the identifier does not exist
            CannotDisseminateFormatError: If the format is not supported
        """
        if not identifier:
            raise ValueError("identifier is required")
        if not metadata_prefix:
            raise ValueError("metadata_prefix is required")

        response = self._request(
            verb='GetRecord',
            identifier=identifier,
            metadataPrefix=metadata_prefix
        )
        result = self._parser.parse_records(response.text)
        if not result.records:
            raise OAIResponseError(f"Record not found: {identifier}")
        return result.records[0]

    def list_records(
        self,
        metadata_prefix: str = 'oai_dc',
        set_spec: Optional[str] = None,
        from_date: Optional[str] = None,
        until_date: Optional[str] = None,
    ) -> Iterator[Record]:
        """
        Iterate over all records, handling pagination automatically.

        Args:
            metadata_prefix: Metadata format (default: oai_dc)
            set_spec: Optional set to harvest from
            from_date: Optional start date (YYYY-MM-DD or YYYY-MM-DDThh:mm:ssZ)
            until_date: Optional end date

        Yields:
            Record objects with typed metadata access.

        Raises:
            NoRecordsMatchError: If no records match the criteria
            CannotDisseminateFormatError: If the format is not supported
        """
        if not metadata_prefix:
            raise ValueError("metadata_prefix is required")

        params = self._build_list_params(
            'ListRecords', metadata_prefix, set_spec, from_date, until_date
        )

        while True:
            response = self._request(**params)
            result = self._parser.parse_records(response.text)

            yield from result

            if not result.has_more:
                break

            params = {'verb': 'ListRecords', 'resumptionToken': result.resumption_token}

    def list_records_page(
        self,
        metadata_prefix: str = 'oai_dc',
        set_spec: Optional[str] = None,
        from_date: Optional[str] = None,
        until_date: Optional[str] = None,
        resumption_token: Optional[str] = None,
    ) -> RecordSet:
        """
        Retrieve a single page of records.

        Args:
            metadata_prefix: Metadata format (default: oai_dc)
            set_spec: Optional set to harvest from
            from_date: Optional start date
            until_date: Optional end date
            resumption_token: Token from previous page (overrides other params)

        Returns:
            RecordSet with records and pagination info.
        """
        if resumption_token:
            # Warn if other params are also provided (per OAI-PMH spec)
            if any([set_spec, from_date, until_date]):
                warnings.warn(
                    "resumption_token provided; set_spec, from_date, until_date ignored",
                    UserWarning,
                    stacklevel=2
                )
            params = {'verb': 'ListRecords', 'resumptionToken': resumption_token}
        else:
            if not metadata_prefix:
                raise ValueError("metadata_prefix is required")
            params = self._build_list_params(
                'ListRecords', metadata_prefix, set_spec, from_date, until_date
            )

        response = self._request(**params)
        return self._parser.parse_records(response.text)

    def list_identifiers(
        self,
        metadata_prefix: str = 'oai_dc',
        set_spec: Optional[str] = None,
        from_date: Optional[str] = None,
        until_date: Optional[str] = None,
    ) -> Iterator[Record]:
        """
        Iterate over record identifiers (OAI-PMH ListIdentifiers verb).

        Similar to list_records but returns only header info (no metadata).

        Args:
            metadata_prefix: Metadata format (default: oai_dc)
            set_spec: Optional set to list from
            from_date: Optional start date
            until_date: Optional end date

        Yields:
            Record objects with identifier, datestamp, set_specs, deleted.
            Note: metadata will be empty.

        Raises:
            NoRecordsMatchError: If no records match the criteria
        """
        if not metadata_prefix:
            raise ValueError("metadata_prefix is required")

        params = self._build_list_params(
            'ListIdentifiers', metadata_prefix, set_spec, from_date, until_date
        )

        while True:
            response = self._request(**params)
            result = self._parser.parse_identifiers(response.text)

            yield from result

            if not result.has_more:
                break

            params = {'verb': 'ListIdentifiers', 'resumptionToken': result.resumption_token}

    def resume(self, resumption_token: str) -> RecordSet:
        """
        Resume pagination with a resumption token.

        Args:
            resumption_token: Token from previous page

        Returns:
            RecordSet with next page of records.
        """
        if not resumption_token:
            raise ValueError("resumption_token is required")
        return self.list_records_page(resumption_token=resumption_token)

    # ==================== Low-level / Backward Compatibility ====================

    def harvest(self, **kwargs) -> OAIResponse:
        """
        Raw harvest method for backward compatibility.

        Returns OAIResponse with raw XML access.
        Prefer list_records() for typed access.

        Args:
            **kwargs: OAI-PMH parameters (verb, metadataPrefix, set, etc.)

        Returns:
            OAIResponse with raw XML and parsed records.
        """
        response = self._request(**kwargs)
        return OAIResponse(params=kwargs, http_response=response)

    # ==================== Context Manager ====================

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
