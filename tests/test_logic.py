"""logic.py (ApiClientOrchestrator) 單元測試"""
import pytest
from unittest.mock import patch, MagicMock
from logic import ApiClientOrchestrator
from core.http_client import HttpResponse


class TestApiClientOrchestrator:
    @pytest.fixture
    def orchestrator(self):
        return ApiClientOrchestrator()

    def test_build_proxies_disabled(self, orchestrator):
        """When proxy is disabled, proxies dict should be empty"""
        from config.settings import config_manager
        config_manager.app_config.proxy_enabled = False
        result = orchestrator._build_proxies()
        assert result == {}

    def test_build_proxies_enabled(self, orchestrator):
        from config.settings import config_manager
        config_manager.app_config.proxy_enabled = True
        config_manager.app_config.http_proxy = "http://proxy:8080"
        config_manager.app_config.https_proxy = "https://proxy:8443"
        
        result = orchestrator._build_proxies()
        assert result["http"] == "http://proxy:8080"
        assert result["https"] == "https://proxy:8443"
        
        # Cleanup
        config_manager.app_config.proxy_enabled = False
        config_manager.app_config.http_proxy = None
        config_manager.app_config.https_proxy = None

    @patch('logic.HttpClient')
    def test_send_request_new_success(self, mock_client_class):
        mock_response = HttpResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            content='{"result": "ok"}',
            elapsed_time=0.5,
            content_size=16,
            request_id="test-req-1"
        )
        mock_client = MagicMock()
        mock_client.send.return_value = mock_response
        mock_client_class.return_value = mock_client

        orch = ApiClientOrchestrator()
        orch._client = mock_client

        result = orch.send_request_new(
            method="GET",
            url="http://example.com/api",
            headers_text="Accept: application/json",
            body_text="",
            timeout=10,
            retry_count=0
        )
        assert result.status_code == 200
        assert "result" in result.content

    @patch('logic.HttpClient')
    def test_send_request_new_with_retry(self, mock_client_class):
        mock_response = HttpResponse(
            status_code=200,
            headers={},
            content="ok",
            elapsed_time=1.0,
            content_size=2,
            request_id="test-req-2"
        )
        mock_client = MagicMock()
        mock_client.send.return_value = mock_response
        mock_client_class.return_value = mock_client

        orch = ApiClientOrchestrator()
        orch._client = mock_client

        result = orch.send_request_new(
            method="POST",
            url="http://example.com/data",
            headers_text="Content-Type: application/json",
            body_text='{"key":"value"}',
            timeout=30,
            retry_count=2
        )
        assert result.status_code == 200

    def test_close(self, orchestrator):
        """close() should not raise"""
        orchestrator.close()
