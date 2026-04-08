"""
github_pr_kb.config
~~~~~~~~~~~~~~~~~~~~
Environment configuration via pydantic-settings.
Validates required environment variables on import — fails fast before any CLI logic runs.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    github_token: str
    anthropic_api_key: str | None = None  # Phase 4: required for classify command
    anthropic_model: str | None = None  # Override default classifier model via ANTHROPIC_MODEL
    kb_output_dir: str = "kb"  # Phase 5: KB output directory (D-17)
    anthropic_generate_model: str | None = None
    min_confidence: float = 0.5


# Module-level instantiation: ValidationError raised on import if GITHUB_TOKEN is missing.
# This means any module that imports `settings` will fail immediately if config is bad —
# before any CLI commands or GitHub API calls are attempted.
settings = Settings()
