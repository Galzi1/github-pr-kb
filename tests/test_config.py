import os

import pytest


def test_settings_requires_github_token(monkeypatch):
    """Missing GITHUB_TOKEN must raise ValidationError — not fail silently."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    from pydantic import ValidationError
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class IsolatedSettings(BaseSettings):
        model_config = SettingsConfigDict(env_file=".env")
        github_token: str

    with pytest.raises(ValidationError):
        IsolatedSettings()


def test_env_example_exists():
    """.env.example must exist at project root."""
    assert os.path.isfile(".env.example"), ".env.example not found at project root"


def test_env_example_documents_github_token():
    """.env.example must mention GITHUB_TOKEN."""
    with open(".env.example") as f:
        content = f.read()
    assert "GITHUB_TOKEN" in content, "GITHUB_TOKEN not documented in .env.example"
