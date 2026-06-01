"""core/http_client.py 單元測試"""
import pytest
from unittest.mock import patch, MagicMock
from core.http_client import HttpClient, HttpRequest, HttpResponse


class TestHttpRequest:
    def test_basic_construction(self):
        req = HttpRequest(
            method="GET",
            url="http://example.com",
            headers={"Accept": "application/json"},
            body=None,
            timeout=30
        )
        assert req.method == "GET"
        assert req.url == "http://example.com"
        assert req.headers["Accept"] == "application/json"

    def test_post_with_body(self):
        req = HttpRequest(
            method="POST",
            url="http://example.com/api",
            headers={"Content-Type": "application/json"},
            body='{"key": "value"}',
            timeout=60
        )
        assert req.body == '{"key": "value"}'


class TestHttpResponse:
    def test_basic_construction(self):
        resp = HttpResponse(
            status_code=200,
            headers={"Content-Type": "text/plain"},
            content="hello",
            elapsed_time=0.1,
            content_size=5,
            request_id="test-id-1"
        )
        assert resp.status_code == 200
        assert resp.content == "hello"
        assert resp.elapsed_time == 0.1
        assert resp.is_success is True

    def test_error_response(self):
        resp = HttpResponse(
            status_code=500,
            headers={},
            content="Internal Server Error",
            elapsed_time=2.0,
            content_size=21,
            request_id="test-id-2"
        )
        assert resp.status_code == 500
        assert resp.is_server_error is True


class TestHttpClient:
    def test_init_defaults(self):
        client = HttpClient()
        assert client.verify_ssl is True

    def test_init_custom(self):
        client = HttpClient(
            verify_ssl=False,
            proxies={"http": "http://proxy:8080"}
        )
        assert client.verify_ssl is False
        assert client.proxies["http"] == "http://proxy:8080"

    @patch('core.http_client.requests.Session')
    def test_send_get(self, mock_session_class):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = '{"data": 1}'
        mock_response.elapsed.total_seconds.return_value = 0.3
        mock_response.content = b'{"data": 1}'
        
        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = HttpClient()
        client.session = mock_session
        
        request = HttpRequest(
            method="GET",
            url="http://example.com/api",
            headers={},
            body=None,
            timeout=30
        )
        response = client.send(request)
        
        assert response.status_code == 200
        assert "data" in response.content
