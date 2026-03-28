"""
Automation integrity tests for workflows, scripts, and docs.
These tests cover non-Python automation paths that are easy to regress.
"""
from pathlib import Path
import re
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_workflow_yaml_files_parse():
    """All workflow YAML files should parse successfully."""
    workflow_files = sorted(WORKFLOWS_DIR.glob("*.yml"))
    assert workflow_files, "Expected workflow files under .github/workflows/"

    for workflow_file in workflow_files:
        content = _read(workflow_file)
        parsed = yaml.safe_load(content)
        assert isinstance(parsed, dict), f"{workflow_file.name} should parse to a mapping"


def test_update_news_workflow_uses_news_only_change_gate():
    """Timestamp-only path should be reachable by gating on news file diffs."""
    content = _read(WORKFLOWS_DIR / "update-news.yml")
    assert "git status --porcelain _data/news/" in content
    assert "news_changed=true" in content
    assert "news_changed=false" in content
    assert "_data/news_last_updated.yml)" not in content


def test_update_news_workflow_sets_timezone_on_date_command():
    """Timestamp generation should set TZ directly on date command."""
    content = _read(WORKFLOWS_DIR / "update-news.yml")
    assert "timestamp=$(TZ='Asia/Manila' date +" in content


def test_update_news_timestamp_push_does_not_swallow_failures():
    """Timestamp-only push path should fail after retries, not silently continue."""
    content = _read(WORKFLOWS_DIR / "update-news.yml")
    assert 'git push origin "$BRANCH" || echo "Failed to push timestamp, continuing..."' not in content
    assert "MAX_RETRIES=3" in content
    assert "Failed to push timestamp after $MAX_RETRIES attempts" in content


def test_actions_are_sha_pinned_in_primary_workflows():
    """Pin actions to full SHAs for supply-chain hardening."""
    sha_pattern = re.compile(r"@([0-9a-f]{40})(\s|$)")

    files_to_check = [
        WORKFLOWS_DIR / "update-news.yml",
        WORKFLOWS_DIR / "build-jekyll.yml",
        WORKFLOWS_DIR / "codeql-analysis.yml",
        WORKFLOWS_DIR / "greetings.yml",
    ]

    for workflow_file in files_to_check:
        content = _read(workflow_file)
        uses_lines = [line.strip() for line in content.splitlines() if "uses:" in line]
        for line in uses_lines:
            assert sha_pattern.search(line), f"Expected SHA pin in {workflow_file.name}: {line}"


def test_setup_task_defaults_to_interactive_with_optional_s4u():
    """Task setup should prefer reliable interactive mode unless S4U is explicitly requested."""
    content = _read(REPO_ROOT / "scripts" / "setup-local-news-task.ps1")
    assert "[switch]$UseS4U" in content
    assert "-LogonType Interactive" in content
    assert "if ($UseS4U)" in content


def test_author_external_links_with_blank_target_include_noopener():
    """External links opened in a new tab should include rel protections."""
    content = _read(REPO_ROOT / "_includes" / "author.html")
    assert 'target="_blank"' in content
    assert 'rel="noopener noreferrer"' in content


def test_precommit_excludes_vendor_assets():
    """Pre-commit should not rewrite vendored bower assets."""
    content = _read(REPO_ROOT / ".pre-commit-config.yaml")
    assert "exclude:" in content
    assert "assets/bower_components/" in content


def test_readme_has_no_common_mojibake_sequences():
    """README should not contain common mojibake artifacts."""
    content = _read(REPO_ROOT / "README.md")
    assert not re.search(r"â|ðŸ|ï¸|â†|â‰", content)
