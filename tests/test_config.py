from pathlib import Path
from pubmedsoso.config import Config


def test_config_defaults():
    config = Config()
    assert config.page_size == 50
    assert config.request_timeout == 30
    assert config.max_retries == 3
    assert config.web_port == 8000
    assert config.min_request_interval == 1.0


def test_config_custom_values():
    config = Config(
        page_size=20,
        web_port=9000,
    )
    assert config.page_size == 20
    assert config.web_port == 9000


def test_config_env_override(monkeypatch):
    monkeypatch.setenv("PUBMEDSOSO_WEB_PORT", "9000")
    config = Config.from_env()
    assert config.web_port == 9000


def test_config_paths_are_path_objects():
    config = Config()
    assert isinstance(config.db_dir, Path)
    assert isinstance(config.export_dir, Path)
