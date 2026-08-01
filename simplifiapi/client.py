import logging
import uuid
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests

logger = logging.getLogger("simplifiapi")

SIMPLIFI_ENDPOINT = "https://services.quicken.com"


class Client:

    def __init__(self) -> None:
        self.session = requests.Session()

    def get_token(self, email: str, password: str) -> Optional[str]:
        # Step 1: Oauth authorize
        body: Dict[str, Any] = {
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
            url="https://services.quicken.com/oauth/authorize", json=body)
        r.raise_for_status()
        data: Dict[str, Any] = r.json()
        status: Optional[str] = data.get("status")
        if (status == "MFA code sent"):
            mfaChannel: Optional[str] = data.get("mfaChannel")
            logger.warning("MFA Channel: {}".format(mfaChannel))
            mfaCode: str = input("MFA Code: ")
            body["mfaChannel"] = mfaChannel
            body["mfaCode"] = mfaCode
            r = self.session.post(
                url="https://services.quicken.com/oauth/authorize", json=body)
            r.raise_for_status()
            data = r.json()
            status = data.get("status")
            if (status != "User passed MFA"):
                logger.error("Login failed.")
                try:
                    logger.error(r.json())
                except Exception:
                    logger.error(r.text)
                return None
        code: Optional[str] = r.json().get("code")

        # Step 2: Get token
        r = self.session.post(url="https://services.quicken.com/oauth/token",
                              json={
                                  "clientId": "acme_web",
                                  "clientSecret": "BCDCxXwdWYcj@bK6",
                                  "grantType": "authorization_code",
                                  "code": code,
                                  "redirectUri": "https://app.simplifimoney.com/login"
                              })
        r.raise_for_status()
        token: Optional[str] = r.json().get("accessToken")

        logger.info("Token retrieved")

        return token

    def verify_token(self, token: str) -> bool:
        headers: Dict[str, str] = {"Authorization": "Bearer {}".format(token)}

        r = self.session.get(url="https://services.quicken.com/userprofiles/me",
                             headers=headers)
        if (r.status_code != 200):
            logger.error("Error code: {}".format(r.status_code))
            try:
                logger.error(r.json())
            except Exception:
                logger.error(r.text)
            return False
        data: Dict[str, Any] = r.json()
        userId: Optional[str] = data.get("id")
        logger.warning("User {} logged in.".format(userId))

        # Update session
        self.session.headers.update(headers)

        return True

    def _unpaginate(self, path: str, **kargs: Any) -> List[Dict[str, Any]]:
        nextLink: Optional[str] = path
        data: List[Dict[str, Any]] = []
        while nextLink:
            logger.warning("Fetching {}".format(nextLink))
            r = self.session.get(url=urljoin(
                SIMPLIFI_ENDPOINT, nextLink), **kargs)
            r.raise_for_status()
            resp: Dict[str, Any] = r.json()
            data.extend(resp.get("resources", []))
            nextLink = resp.get("metaData", {}).get("nextLink")
        return data

    def get_datasets(self, limit: int = 1000) -> List[Dict[str, Any]]:
        return self._unpaginate(path="/datasets",
                                params={
                                    "limit": limit,
                                })

    def get_accounts(self, datasetId: str) -> List[Dict[str, Any]]:
        return self._unpaginate(path="/accounts",
                                headers={
                                     "Qcs-Dataset-Id": datasetId,
                                },
                                params={
                                    "limit": 1000,
                                })

    def get_transactions(self, datasetId: str) -> List[Dict[str, Any]]:
        return self._unpaginate(path="/transactions",
                                headers={
                                     "Qcs-Dataset-Id": datasetId,
                                },
                                params={
                                    "limit": 1000,
                                })

    def get_tags(self, datasetId: str) -> List[Dict[str, Any]]:
        return self._unpaginate(path="/tags",
                                headers={
                                     "Qcs-Dataset-Id": datasetId,
                                },
                                params={
                                    "limit": 1000,
                                })

    def get_categories(self, datasetId: str) -> List[Dict[str, Any]]:
        return self._unpaginate(path="/categories",
                                headers={
                                     "Qcs-Dataset-Id": datasetId,
                                },
                                params={
                                    "limit": 1000,
                                })
