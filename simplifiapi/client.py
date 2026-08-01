"""API client for Quicken Simplifi.

Provides the :class:`Client` class which handles authentication (OAuth with MFA
support), session management, paginated data retrieval, and exposes methods for
fetching datasets, accounts, transactions, tags, and categories.

Authentication flow
-------------------
1. ``POST /oauth/authorize`` with email/password.
2. If MFA is required, prompt for the code and retry.
3. Exchange the authorization code for an access token via
   ``POST /oauth/token``.
4. Verify the token against ``/userprofiles/me`` and store it as the default
   ``Authorization`` header on the session.

Pagination
----------
All list endpoints are paginated. :meth:`Client._unpaginate` follows the
``nextLink`` field in the ``metaData`` block of each response until no more
pages remain, collecting all ``resources`` into a single list.

Hardcoded credentials
---------------------
The ``clientId`` and ``clientSecret`` values used here were reverse-engineered
from the official Quicken Simplifi web application. They belong to the
``acme_web`` OAuth client and may change at any time.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any
from urllib.parse import urljoin

import requests

logger = logging.getLogger("simplifiapi")

SIMPLIFI_ENDPOINT = "https://services.quicken.com"


class Client:
    """HTTP client for the Quicken Simplifi API.

    Wraps a :class:`requests.Session` and provides methods for
    authentication and data retrieval. All API calls are authenticated
    automatically once :meth:`verify_token` has succeeded.

    Example::

        from simplifiapi.client import Client

        client = Client()
        token = client.get_token("user@example.com", "password")
        if client.verify_token(token):
            datasets = client.get_datasets()
            accounts = client.get_accounts(datasets[0]["id"])
    """

    def __init__(self) -> None:
        """Create a new Client with a fresh HTTP session."""
        self.session = requests.Session()

    def get_token(self, email: str, password: str) -> str | None:
        """Authenticate with email/password and return an access token.

        Performs the two-step Simplifi OAuth flow:
            1. Authorize: send credentials, handle MFA if required.
            2. Exchange the authorization code for an access token.

        Args:
            email: Quicken Simplifi account email address.
            password: Quicken Simplifi account password.

        Returns:
            The access token string, or ``None`` if authentication failed
            (e.g. wrong MFA code).

        Raises:
            requests.HTTPError: If the API returns an HTTP error response.
        """
        body: dict[str, Any] = {
            "clientId": "acme_web",
            "mfaChannel": None,
            "mfaCode": None,
            "password": password,
            "redirectUri": "https://app.simplifimoney.com/login",
            "responseType": "code",
            "threatMetrixRequestId": None,
            "threatMetrixSessionId": str(uuid.uuid4()),
            "username": email,
        }
        r = self.session.post(
            url="https://services.quicken.com/oauth/authorize", json=body
        )
        r.raise_for_status()
        data: dict[str, Any] = r.json()
        status: str | None = data.get("status")
        if status == "MFA code sent":
            mfaChannel: str | None = data.get("mfaChannel")
            logger.warning(f"MFA Channel: {mfaChannel}")
            mfaCode: str = input("MFA Code: ")
            body["mfaChannel"] = mfaChannel
            body["mfaCode"] = mfaCode
            r = self.session.post(
                url="https://services.quicken.com/oauth/authorize", json=body
            )
            r.raise_for_status()
            data = r.json()
            status = data.get("status")
            if status != "User passed MFA":
                logger.error("Login failed.")
                try:
                    logger.error(r.json())
                except Exception:
                    logger.error(r.text)
                return None
        code: str | None = r.json().get("code")

        r = self.session.post(
            url="https://services.quicken.com/oauth/token",
            json={
                "clientId": "acme_web",
                "clientSecret": "BCDCxXwdWYcj@bK6",
                "grantType": "authorization_code",
                "code": code,
                "redirectUri": "https://app.simplifimoney.com/login",
            },
        )
        r.raise_for_status()
        token: str | None = r.json().get("accessToken")

        logger.info("Token retrieved")

        return token

    def verify_token(self, token: str) -> bool:
        """Verify that a token is valid and update the session headers.

        Calls ``/userprofiles/me`` with the given token.  On success, the
        ``Authorization`` header is stored on the session so subsequent API
        calls are authenticated automatically.

        Args:
            token: The access token to verify.

        Returns:
            ``True`` if the token is valid, ``False`` otherwise.
        """
        headers: dict[str, str] = {"Authorization": f"Bearer {token}"}

        r = self.session.get(
            url="https://services.quicken.com/userprofiles/me", headers=headers
        )
        if r.status_code != 200:
            logger.error(f"Error code: {r.status_code}")
            try:
                logger.error(r.json())
            except Exception:
                logger.error(r.text)
            return False
        data: dict[str, Any] = r.json()
        userId: str | None = data.get("id")
        logger.warning(f"User {userId} logged in.")

        self.session.headers.update(headers)

        return True

    def _unpaginate(self, path: str, **kargs: Any) -> list[dict[str, Any]]:
        """Follow a paginated endpoint and collect all resources.

        Starts at ``path`` and follows the ``nextLink`` field in the
        ``metaData`` block of each JSON response until no more pages
        remain.  All ``resources`` arrays are concatenated into the
        returned list.

        Args:
            path: Initial API path (e.g. ``"/transactions"``).
            **kargs: Additional keyword arguments forwarded to
                :meth:`requests.Session.get` (e.g. ``params``,
                ``headers``).

        Returns:
            A flat list of all resource dicts from every page.
        """
        nextLink: str | None = path
        data: list[dict[str, Any]] = []
        while nextLink:
            logger.warning(f"Fetching {nextLink}")
            r = self.session.get(url=urljoin(SIMPLIFI_ENDPOINT, nextLink), **kargs)
            r.raise_for_status()
            resp: dict[str, Any] = r.json()
            data.extend(resp.get("resources", []))
            nextLink = resp.get("metaData", {}).get("nextLink")
        return data

    def get_datasets(self, limit: int = 1000) -> list[dict[str, Any]]:
        """Retrieve available datasets.

        Args:
            limit: Maximum number of datasets to return per page.

        Returns:
            List of dataset objects, each containing an ``"id"`` field
            required by other data-retrieval methods.
        """
        return self._unpaginate(
            path="/datasets",
            params={
                "limit": limit,
            },
        )

    def get_accounts(self, datasetId: str) -> list[dict[str, Any]]:
        """Retrieve accounts for a dataset.

        Args:
            datasetId: Dataset identifier from :meth:`get_datasets`.

        Returns:
            List of account objects (checking, savings, credit cards, etc.).
        """
        return self._unpaginate(
            path="/accounts",
            headers={
                "Qcs-Dataset-Id": datasetId,
            },
            params={
                "limit": 1000,
            },
        )

    def get_transactions(self, datasetId: str) -> list[dict[str, Any]]:
        """Retrieve transactions for a dataset.

        Args:
            datasetId: Dataset identifier from :meth:`get_datasets`.

        Returns:
            List of transaction objects.
        """
        return self._unpaginate(
            path="/transactions",
            headers={
                "Qcs-Dataset-Id": datasetId,
            },
            params={
                "limit": 1000,
            },
        )

    def get_tags(self, datasetId: str) -> list[dict[str, Any]]:
        """Retrieve tags for a dataset.

        Args:
            datasetId: Dataset identifier from :meth:`get_datasets`.

        Returns:
            List of tag objects.
        """
        return self._unpaginate(
            path="/tags",
            headers={
                "Qcs-Dataset-Id": datasetId,
            },
            params={
                "limit": 1000,
            },
        )

    def get_categories(self, datasetId: str) -> list[dict[str, Any]]:
        """Retrieve categories for a dataset.

        Args:
            datasetId: Dataset identifier from :meth:`get_datasets`.

        Returns:
            List of category objects.
        """
        return self._unpaginate(
            path="/categories",
            headers={
                "Qcs-Dataset-Id": datasetId,
            },
            params={
                "limit": 1000,
            },
        )
