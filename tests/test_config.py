"""config/settings.py 單元測試"""
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from config.settings import AppConfig, Environment, ConfigManager


class TestAppConfig:
    def test_default_values(self):
        config = AppConfig()
        assert config.default_timeout == 30
        assert config.retry_count == 3
        assert config.verify_ssl is True
        assert config.proxy_enabled is False
        assert config.log_level == "INFO"

    def test_custom_values(self):
        config = AppConfig(default_timeout=60, verify_ssl=False)
        assert config.default_timeout == 60
        assert config.verify_ssl is False


class TestEnvironment:
    def test_defaults(self):
        env = Environment(name="test", base_url="http://localhost")
        assert env.variables == {}
        assert env.headers == {}
        assert env.auth_type is None
        assert env.auth_value is None
        assert env.description == ""

    def test_full_env(self):
        env = Environment(
            name="prod",
            base_url="https://api.example.com",
            variables={"api_key": "123"},
            headers={"X-App": "test"},
            auth_type="bearer",
            auth_value="token-abc",
            description="Production"
        )
        assert env.name == "prod"
        assert env.variables["api_key"] == "123"


class TestConfigManager:
    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset ConfigManager singleton between tests"""
        ConfigManager._instance = None
        yield
        ConfigManager._instance = None

    def test_singleton(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ConfigManager, '_config_dir', tmp_path)
        monkeypatch.setattr(ConfigManager, '_config_file', tmp_path / "config.json")
        monkeypatch.setattr(ConfigManager, '_environments_file', tmp_path / "environments.json")
        
        mgr1 = ConfigManager()
        mgr2 = ConfigManager()
        assert mgr1 is mgr2

    def test_load_config_from_file(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"default_timeout": 99, "log_level": "DEBUG"}))
        
        monkeypatch.setattr(ConfigManager, '_config_dir', tmp_path)
        monkeypatch.setattr(ConfigManager, '_config_file', config_file)
        monkeypatch.setattr(ConfigManager, '_environments_file', tmp_path / "environments.json")
        
        mgr = ConfigManager()
        assert mgr.app_config.default_timeout == 99
        assert mgr.app_config.log_level == "DEBUG"

    def test_load_environments_from_file(self, tmp_path, monkeypatch):
        env_file = tmp_path / "environments.json"
        env_file.write_text(json.dumps({
            "TestEnv": {
                "base_url": "http://test.local",
                "variables": {"v1": "val1"},
                "headers": {},
                "auth_type": "bearer",
                "auth_value": "tok",
                "description": "Test"
            }
        }))
        
        monkeypatch.setattr(ConfigManager, '_config_dir', tmp_path)
        monkeypatch.setattr(ConfigManager, '_config_file', tmp_path / "config.json")
        monkeypatch.setattr(ConfigManager, '_environments_file', env_file)
        
        mgr = ConfigManager()
        assert "TestEnv" in mgr.environments
        assert mgr.environments["TestEnv"].base_url == "http://test.local"

    def test_save_config(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.json"
        monkeypatch.setattr(ConfigManager, '_config_dir', tmp_path)
        monkeypatch.setattr(ConfigManager, '_config_file', config_file)
        monkeypatch.setattr(ConfigManager, '_environments_file', tmp_path / "environments.json")
        
        mgr = ConfigManager()
        mgr.app_config.default_timeout = 120
        mgr.save_config()
        
        saved = json.loads(config_file.read_text())
        assert saved["default_timeout"] == 120

    def test_set_current_environment(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.json"
        monkeypatch.setattr(ConfigManager, '_config_dir', tmp_path)
        monkeypatch.setattr(ConfigManager, '_config_file', config_file)
        monkeypatch.setattr(ConfigManager, '_environments_file', tmp_path / "environments.json")
        
        mgr = ConfigManager()
        # Default environments are created
        mgr.set_current_environment("Development")
        assert mgr.current_environment == "Development"
        
        # Non-existent env should set to None
        mgr.set_current_environment("NonExistent")
        assert mgr.current_environment is None

    def test_resolve_url_with_base(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ConfigManager, '_config_dir', tmp_path)
        monkeypatch.setattr(ConfigManager, '_config_file', tmp_path / "config.json")
        monkeypatch.setattr(ConfigManager, '_environments_file', tmp_path / "environments.json")
        
        mgr = ConfigManager()
        mgr.set_current_environment("Development")
        
        resolved = mgr.resolve_url("/api/test")
        assert resolved == "http://localhost:8080/api/test"

    def test_resolve_url_absolute_unchanged(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ConfigManager, '_config_dir', tmp_path)
        monkeypatch.setattr(ConfigManager, '_config_file', tmp_path / "config.json")
        monkeypatch.setattr(ConfigManager, '_environments_file', tmp_path / "environments.json")
        
        mgr = ConfigManager()
        mgr.set_current_environment("Development")
        
        resolved = mgr.resolve_url("https://other.com/path")
        assert resolved == "https://other.com/path"

    def test_apply_environment_variables(self, tmp_path, monkeypatch):
        env_file = tmp_path / "environments.json"
        env_file.write_text(json.dumps({
            "Dev": {
                "base_url": "http://localhost",
                "variables": {"host": "localhost", "port": "3000"},
                "headers": {},
                "description": ""
            }
        }))
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"current_environment": "Dev"}))
        
        monkeypatch.setattr(ConfigManager, '_config_dir', tmp_path)
        monkeypatch.setattr(ConfigManager, '_config_file', config_file)
        monkeypatch.setattr(ConfigManager, '_environments_file', env_file)
        
        mgr = ConfigManager()
        result = mgr.apply_environment_variables("{{host}}:{{port}}/api")
        assert result == "localhost:3000/api"

    def test_apply_environment_variables_unknown_kept(self, tmp_path, monkeypatch):
        env_file = tmp_path / "environments.json"
        env_file.write_text(json.dumps({
            "Dev": {
                "base_url": "http://localhost",
                "variables": {"host": "localhost"},
                "headers": {},
                "description": ""
            }
        }))
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"current_environment": "Dev"}))

        monkeypatch.setattr(ConfigManager, '_config_dir', tmp_path)
        monkeypatch.setattr(ConfigManager, '_config_file', config_file)
        monkeypatch.setattr(ConfigManager, '_environments_file', env_file)

        mgr = ConfigManager()
        result = mgr.apply_environment_variables("{{host}}/{{missing}}")
        assert result == "localhost/{{missing}}"

    def test_env_overrides(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ConfigManager, '_config_dir', tmp_path)
        monkeypatch.setattr(ConfigManager, '_config_file', tmp_path / "config.json")
        monkeypatch.setattr(ConfigManager, '_environments_file', tmp_path / "environments.json")
        monkeypatch.setenv("API_CLIENT_TIMEOUT", "999")
        
        mgr = ConfigManager()
        assert mgr.app_config.default_timeout == 999

    def test_add_remove_environment(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ConfigManager, '_config_dir', tmp_path)
        monkeypatch.setattr(ConfigManager, '_config_file', tmp_path / "config.json")
        monkeypatch.setattr(ConfigManager, '_environments_file', tmp_path / "environments.json")
        
        mgr = ConfigManager()
        new_env = Environment(name="Custom", base_url="http://custom.local")
        mgr.add_environment(new_env)
        assert "Custom" in mgr.environments
        
        mgr.remove_environment("Custom")
        assert "Custom" not in mgr.environments
