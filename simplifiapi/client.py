from __future__ import annotations

import logging
import uuid
from typing import Any
from urllib.parse import urljoin

import requests

logger = logging.getLogger("simplifiapi")

SIMPLIFI_ENDPOINT = "https://services.quicken.com"


class Client:
    def __init__(self) -> None:
        self.session = requests.Session()

    def get_token(self, email: str, password: str) -> str | None:
        # Step 1: Oauth authorize
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

        # Step 2: Get token
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

        # Update session
        self.session.headers.update(headers)

        return True

    def _unpaginate(self, path: str, **kargs: Any) -> list[dict[str, Any]]:
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
        return self._unpaginate(
            path="/datasets",
            params={
                "limit": limit,
            },
        )

    def get_accounts(self, datasetId: str) -> list[dict[str, Any]]:
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
        return self._unpaginate(
            path="/categories",
            headers={
                "Qcs-Dataset-Id": datasetId,
            },
            params={
                "limit": 1000,
            },
        )
