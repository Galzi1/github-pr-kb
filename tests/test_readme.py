from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README_PATH = REPO_ROOT / "README.md"
ENV_EXAMPLE_PATH = REPO_ROOT / ".env.example"


def _readme() -> str:
    return README_PATH.read_text(encoding="utf-8")


def _env_example() -> str:
    return ENV_EXAMPLE_PATH.read_text(encoding="utf-8")


def test_readme_is_automation_first() -> None:
    text = _readme()

    assert "## Automate with GitHub Actions" in text
    assert "## Run locally" in text
    assert text.index("## Automate with GitHub Actions") < text.index("## Run locally")
    assert ".github/workflows/github-pr-kb.yml" in text
    assert "workflow_dispatch" in text
    assert "KB_TOOL_REPOSITORY" in text
    assert "KB_TOOL_REF" in text
    assert "Galzi1/github-pr-kb" in text
    assert "copy only the workflow file" in text
    assert "do not need this tool's source tree checked into your repository" in text
    assert "### PAT quickstart" in text
    assert "### GitHub App" in text
    assert text.index("KB_VARIABLES_TOKEN") < text.index("KB_VARIABLES_APP_ID")


def test_readme_distinguishes_local_and_workflow_credentials() -> None:
    text = _readme()

    assert "GITHUB_TOKEN" in text
    assert "ANTHROPIC_API_KEY" in text
    assert "KB_VARIABLES_TOKEN" in text
    assert "KB_VARIABLES_APP_ID" in text
    assert "KB_VARIABLES_APP_PRIVATE_KEY" in text
    assert "GH_TOKEN" in text
    assert "gh api" in text
    assert "gh pr" in text
    assert "local/runtime credentials" in text
    assert "workflow repository-variable credentials" in text


def test_readme_documents_install_local_usage_and_git_boundaries() -> None:
    text = _readme()

    assert "### Install uv" in text
    assert text.index("### Install uv") < text.index("uv sync --all-groups --frozen")
    assert "https://docs.astral.sh/uv/getting-started/installation/" in text
    assert 'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"' in text
    assert "curl -LsSf https://astral.sh/uv/install.sh | sh" in text
    assert ".venv/Scripts/python.exe -m pytest tests/" in text
    assert ".venv/bin/python -m pytest tests/" in text
    for token in (
        "GITHUB_TOKEN",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_MODEL",
        "ANTHROPIC_GENERATE_MODEL",
        "KB_OUTPUT_DIR",
        "MIN_CONFIDENCE",
    ):
        assert token in text
    assert "github-pr-kb extract --repo owner/name" in text
    assert "github-pr-kb classify" in text
    assert "github-pr-kb generate" in text
    assert ".github-pr-kb/cache/" in text
    assert "kb/.manifest.json" in text
    assert "Committed vs not committed" in text
    assert ".env.example" in text


def test_env_example_matches_local_config_surface_only() -> None:
    text = _env_example()

    for token in (
        "GITHUB_TOKEN",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_MODEL",
        "ANTHROPIC_GENERATE_MODEL",
        "KB_OUTPUT_DIR",
        "MIN_CONFIDENCE",
    ):
        assert token in text
    assert "KB_VARIABLES_TOKEN=" not in text
    assert "KB_VARIABLES_APP_ID=" not in text
    assert "KB_VARIABLES_APP_PRIVATE_KEY=" not in text
    assert "repository secrets" in text
