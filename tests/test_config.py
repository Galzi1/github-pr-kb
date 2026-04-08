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


def test_settings_reads_generate_model(monkeypatch):
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class IsolatedSettings(BaseSettings):
        model_config = SettingsConfigDict(env_file=".env")
        github_token: str
        anthropic_generate_model: str | None = None
        min_confidence: float = 0.5

    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
    monkeypatch.setenv("ANTHROPIC_GENERATE_MODEL", "claude-sonnet-test")

    settings = IsolatedSettings()
    assert settings.anthropic_generate_model == "claude-sonnet-test"


def test_settings_parses_min_confidence(monkeypatch):
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class IsolatedSettings(BaseSettings):
        model_config = SettingsConfigDict(env_file=".env")
        github_token: str
        anthropic_generate_model: str | None = None
        min_confidence: float = 0.5

    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
    monkeypatch.setenv("MIN_CONFIDENCE", "0.65")

    settings = IsolatedSettings()
    assert settings.min_confidence == pytest.approx(0.65)
