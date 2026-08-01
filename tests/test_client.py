import json
from unittest.mock import patch

import pytest
import responses

from simplifiapi.client import Client, SIMPLIFI_ENDPOINT


class TestClientInit:
    def test_init_creates_session(self):
        client = Client()
        assert client.session is not None


class TestVerifyToken:
    def test_verify_token_success(self):
        client = Client()
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://services.quicken.com/userprofiles/me",
                json={"id": "user-123"},
                status=200,
            )
            result = client.verify_token("test-token")
            assert result is True
            assert client.session.headers["Authorization"] == "Bearer test-token"

    def test_verify_token_failure(self):
        client = Client()
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://services.quicken.com/userprofiles/me",
                json={"error": "invalid_token"},
                status=401,
            )
            result = client.verify_token("bad-token")
            assert result is False

    def test_verify_token_non_json_response(self):
        client = Client()
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://services.quicken.com/userprofiles/me",
                body="Internal Server Error",
                status=500,
            )
            result = client.verify_token("test-token")
            assert result is False


class TestGetToken:
    def test_get_token_success_no_mfa(self):
        client = Client()
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.POST,
                "https://services.quicken.com/oauth/authorize",
                json={"status": "OK", "code": "auth-code-123"},
                status=200,
            )
            rsps.add(
                responses.POST,
                "https://services.quicken.com/oauth/token",
                json={"accessToken": "token-abc"},
                status=200,
            )
            token = client.get_token("user@example.com", "password")
            assert token == "token-abc"

    def test_get_token_with_mfa_success(self):
        client = Client()
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.POST,
                "https://services.quicken.com/oauth/authorize",
                json={"status": "MFA code sent", "mfaChannel": "email"},
                status=200,
            )
            rsps.add(
                responses.POST,
                "https://services.quicken.com/oauth/authorize",
                json={"status": "User passed MFA", "code": "auth-code-456"},
                status=200,
            )
            rsps.add(
                responses.POST,
                "https://services.quicken.com/oauth/token",
                json={"accessToken": "token-mfa"},
                status=200,
            )
            with patch("builtins.input", return_value="123456"):
                token = client.get_token("user@example.com", "password")
            assert token == "token-mfa"

    def test_get_token_mfa_failure(self):
        client = Client()
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.POST,
                "https://services.quicken.com/oauth/authorize",
                json={"status": "MFA code sent", "mfaChannel": "email"},
                status=200,
            )
            rsps.add(
                responses.POST,
                "https://services.quicken.com/oauth/authorize",
                json={"status": "MFA failed", "error": "bad code"},
                status=200,
            )
            with patch("builtins.input", return_value="wrong"):
                token = client.get_token("user@example.com", "password")
            assert token is None

    def test_get_token_authorize_http_error(self):
        client = Client()
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.POST,
                "https://services.quicken.com/oauth/authorize",
                body="Service Unavailable",
                status=503,
            )
            with pytest.raises(Exception):
                client.get_token("user@example.com", "password")

    def test_get_token_token_endpoint_error(self):
        client = Client()
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.POST,
                "https://services.quicken.com/oauth/authorize",
                json={"status": "OK", "code": "auth-code"},
                status=200,
            )
            rsps.add(
                responses.POST,
                "https://services.quicken.com/oauth/token",
                body="Bad Gateway",
                status=502,
            )
            with pytest.raises(Exception):
                client.get_token("user@example.com", "password")

    def test_get_token_authorize_body_structure(self):
        client = Client()
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.POST,
                "https://services.quicken.com/oauth/authorize",
                json={"status": "OK", "code": "auth-code"},
                status=200,
            )
            rsps.add(
                responses.POST,
                "https://services.quicken.com/oauth/token",
                json={"accessToken": "token"},
                status=200,
            )
            client.get_token("user@example.com", "mypassword")
            authorize_request = json.loads(rsps.calls[0].request.body)
            assert authorize_request["clientId"] == "acme_web"
            assert authorize_request["username"] == "user@example.com"
            assert authorize_request["password"] == "mypassword"
            assert "threatMetrixSessionId" in authorize_request

    def test_get_token_token_body_structure(self):
        client = Client()
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.POST,
                "https://services.quicken.com/oauth/authorize",
                json={"status": "OK", "code": "auth-code-xyz"},
                status=200,
            )
            rsps.add(
                responses.POST,
                "https://services.quicken.com/oauth/token",
                json={"accessToken": "token"},
                status=200,
            )
            client.get_token("user@example.com", "pass")
            token_request = json.loads(rsps.calls[1].request.body)
            assert token_request["clientId"] == "acme_web"
            assert token_request["grantType"] == "authorization_code"
            assert token_request["code"] == "auth-code-xyz"


class TestUnpaginate:
    def test_unpaginate_single_page(self):
        client = Client()
        client.session.headers["Authorization"] = "Bearer test"
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://services.quicken.com/test-path",
                json={
                    "resources": [{"id": 1}, {"id": 2}],
                    "metaData": {},
                },
                status=200,
            )
            result = client._unpaginate("/test-path")
            assert result == [{"id": 1}, {"id": 2}]

    def test_unpaginate_multiple_pages(self):
        client = Client()
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://services.quicken.com/page1",
                json={
                    "resources": [{"id": 1}],
                    "metaData": {"nextLink": "/page2"},
                },
                status=200,
            )
            rsps.add(
                responses.GET,
                "https://services.quicken.com/page2",
                json={
                    "resources": [{"id": 2}],
                    "metaData": {},
                },
                status=200,
            )
            result = client._unpaginate("/page1")
            assert result == [{"id": 1}, {"id": 2}]

    def test_unpaginate_empty_resources(self):
        client = Client()
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://services.quicken.com/empty-path",
                json={
                    "resources": [],
                    "metaData": {},
                },
                status=200,
            )
            result = client._unpaginate("/empty-path")
            assert result == []

    def test_unpaginate_missing_metadata(self):
        client = Client()
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://services.quicken.com/no-meta",
                json={
                    "resources": [{"id": 1}],
                },
                status=200,
            )
            result = client._unpaginate("/no-meta")
            assert result == [{"id": 1}]

    def test_unpaginate_http_error(self):
        client = Client()
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://services.quicken.com/error-path",
                body="Server Error",
                status=500,
            )
            with pytest.raises(Exception):
                client._unpaginate("/error-path")


class TestGetDatasets:
    def test_get_datasets_sends_limit_param(self):
        client = Client()
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://services.quicken.com/datasets",
                json={"resources": [], "metaData": {}},
                status=200,
            )
            client.get_datasets(limit=500)
            assert "limit" in rsps.calls[0].request.url
            assert "500" in rsps.calls[0].request.url


class TestGetMethods:
    def test_get_accounts_sets_dataset_header(self):
        client = Client()
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://services.quicken.com/accounts",
                json={"resources": [], "metaData": {}},
                status=200,
            )
            client.get_accounts("dataset-42")
            req_headers = rsps.calls[0].request.headers
            assert req_headers["Qcs-Dataset-Id"] == "dataset-42"

    def test_get_transactions_returns_list(self):
        client = Client()
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://services.quicken.com/transactions",
                json={"resources": [{"txId": "1"}], "metaData": {}},
                status=200,
            )
            result = client.get_transactions("ds-id")
            assert result == [{"txId": "1"}]

    def test_get_tags(self):
        client = Client()
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://services.quicken.com/tags",
                json={"resources": [{"name": "food"}], "metaData": {}},
                status=200,
            )
            result = client.get_tags("ds-id")
            assert result == [{"name": "food"}]

    def test_get_categories(self):
        client = Client()
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://services.quicken.com/categories",
                json={"resources": [{"name": "Groceries"}], "metaData": {}},
                status=200,
            )
            result = client.get_categories("ds-id")
            assert result == [{"name": "Groceries"}]
