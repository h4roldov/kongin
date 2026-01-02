"""
DSpace REST API client.

Provides authentication and item upload functionality.
Supports DSpace versions 7, 8, 9, 10 and future versions with compatible API.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

import requests

from .record import Record
from .exporters.dspace import DSpaceExporter
from .exceptions import OAIClientError


class DSpaceAuthError(OAIClientError):
    """Authentication with DSpace failed."""


class DSpaceUploadError(OAIClientError):
    """Upload to DSpace failed."""


@dataclass
class DSpaceClient:
    """
    Client for DSpace 7+ REST API.

    Handles authentication and item creation.

    Example:
        >>> client = DSpaceClient('https://demo.dspace.org', 'admin@demo.org', 'password')
        >>> collections = client.list_collections()
        >>> client.create_item(record, collections[0]['uuid'])
    """

    base_url: str
    email: str
    password: str
    verify_ssl: bool = True
    _session: requests.Session = field(default_factory=requests.Session, repr=False)
    _authenticated: bool = field(default=False, repr=False)
    _exporter: DSpaceExporter = field(default_factory=DSpaceExporter, repr=False)

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip('/')
        self._session.verify = self.verify_ssl
        self._session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

    def _ensure_authenticated(self) -> None:
        """Authenticate if not already done."""
        if not self._authenticated:
            self._authenticate()

    def _authenticate(self) -> None:
        """
        Login to DSpace and store authentication token.

        Raises:
            DSpaceAuthError: If authentication fails.
        """
        try:
            # DSpace 7+ uses POST with form data for login
            response = self._session.post(
                f"{self.base_url}/api/authn/login",
                data={"user": self.email, "password": self.password},
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            response.raise_for_status()

            # Token is returned in Authorization header
            token = response.headers.get("Authorization")
            if not token:
                # Some DSpace versions return DSPACE-XSRF-TOKEN in cookie
                xsrf = response.cookies.get("DSPACE-XSRF-TOKEN")
                if xsrf:
                    self._session.headers["X-XSRF-TOKEN"] = xsrf
            else:
                self._session.headers["Authorization"] = token

            self._authenticated = True

        except requests.RequestException as e:
            raise DSpaceAuthError(f"Authentication failed: {e}") from e

    def list_collections(self, page: int = 0, size: int = 100) -> List[Dict[str, Any]]:
        """
        Get available collections.

        Args:
            page: Page number (0-indexed)
            size: Page size

        Returns:
            List of collection dicts with uuid, name, handle.
        """
        self._ensure_authenticated()

        response = self._session.get(
            f"{self.base_url}/api/core/collections",
            params={'page': page, 'size': size}
        )
        response.raise_for_status()

        data = response.json()
        collections = data.get('_embedded', {}).get('collections', [])

        return [{
            'uuid': c['uuid'],
            'name': c.get('name', ''),
            'handle': c.get('handle', ''),
        } for c in collections]

    def list_communities(self, page: int = 0, size: int = 100) -> List[Dict[str, Any]]:
        """
        Get available communities.

        Args:
            page: Page number (0-indexed)
            size: Page size

        Returns:
            List of community dicts with uuid, name, handle.
        """
        self._ensure_authenticated()

        response = self._session.get(
            f"{self.base_url}/api/core/communities",
            params={'page': page, 'size': size}
        )
        response.raise_for_status()

        data = response.json()
        communities = data.get('_embedded', {}).get('communities', [])

        return [{
            'uuid': c['uuid'],
            'name': c.get('name', ''),
            'handle': c.get('handle', ''),
        } for c in communities]

    def create_item(
        self,
        record: Record,
        collection_id: str,
        custom_mapping: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create an item in a collection.

        Args:
            record: Record to upload
            collection_id: UUID of target collection
            custom_mapping: Optional custom field mapping

        Returns:
            Created item data from DSpace.

        Raises:
            DSpaceUploadError: If upload fails.
        """
        self._ensure_authenticated()

        exporter = DSpaceExporter(custom_mapping) if custom_mapping else self._exporter
        item_data = exporter.export_record(record)

        try:
            response = self._session.post(
                f"{self.base_url}/api/core/collections/{collection_id}/items",
                json=item_data
            )
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            raise DSpaceUploadError(
                f"Failed to upload '{record.title}': {e}"
            ) from e

    def upload_records(
        self,
        records: List[Record],
        collection_id: str,
        custom_mapping: Optional[Dict[str, str]] = None,
        on_progress: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Upload multiple records to a collection.

        Args:
            records: List of records to upload
            collection_id: UUID of target collection
            custom_mapping: Optional custom field mapping
            on_progress: Optional callback(current, total) for progress updates

        Returns:
            List of created item data from DSpace.
        """
        results = []
        total = len(records)

        for i, record in enumerate(records):
            result = self.create_item(record, collection_id, custom_mapping)
            results.append(result)

            if on_progress:
                on_progress(i + 1, total)

        return results

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
