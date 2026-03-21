"""
Regression tests for previously reported review findings.
"""
import os
from pathlib import Path
from unittest.mock import patch

import update_news
from update_news import (
    COMBINED_METRICS_TOPIC,
    MSG_WARNING_UPDATE_ERRORS,
    MetricsTracker,
    fetch_combined_from_newsapi,
    main,
    run_cli,
)


def test_main_returns_failure_when_no_news_sources():
    """Finding #1: no sources should return non-zero status."""
    with patch("update_news.load_config", return_value={}):
        assert main() == 1


def test_run_cli_exits_non_zero_when_main_returns_failure():
    """Finding #1: CLI wrapper should propagate non-zero exit code."""
    with patch("update_news.main", return_value=1):
        with patch("sys.exit") as mock_exit:
            run_cli()
            mock_exit.assert_called_with(1)


def test_main_summary_does_not_double_count_topic_failure_and_api_error():
    """Finding #2: one logical topic failure should not be reported as two errors."""
    config = {
        "api": {
            "combine_topics_in_single_request": False,
            "max_api_calls": 45,
            "topic_delay_seconds": 0,
        },
        "metrics": {"export_to_json": False},
        "news_sources": {
            "demo-topic": {
                "name": "Demo Topic",
                "title_query": "Demo",
            }
        },
    }

    def failing_process_topic(topic, topic_config, api_key, config, metrics, api_call_count, rate_limited_flag):
        metrics.record_api_call(topic, 12.0, success=False)
        return False, False

    with patch.dict(os.environ, {"NEWSAPI_KEY": "demo-key"}, clear=False):
        with patch("update_news.load_config", return_value=config), \
             patch("update_news.process_topic", side_effect=failing_process_topic), \
             patch.object(update_news.logger, "warning") as mock_warning:
            exit_code = main()

    assert exit_code == 0
    expected_warning = MSG_WARNING_UPDATE_ERRORS.format(count=1)
    assert any(expected_warning in str(call.args[0]) for call in mock_warning.call_args_list if call.args)


def test_fetch_combined_uses_dedicated_metrics_topic_bucket():
    """Finding #3: combined mode should not attribute API call to the first real topic."""
    topics_config = {
        "deep-learning": {"name": "Deep Learning", "title_query": "Deep Learning"},
        "machine-learning": {"name": "Machine Learning", "title_query": "Machine Learning"},
    }
    metrics = MetricsTracker()
    api_call_count = {"total": 0}
    captured = {}

    def fake_fetch_articles_page(url, params, page, config, metrics_obj, topic):
        captured["topic"] = topic
        return {"status": "ok", "totalResults": 0, "articles": []}, True, False, False

    with patch("update_news.calculate_date_range", return_value=("2026-03-20", "2026-03-21")), \
         patch("update_news.fetch_articles_page", side_effect=fake_fetch_articles_page):
        fetch_combined_from_newsapi(topics_config, "test-key", {}, metrics, api_call_count)

    assert captured["topic"] == COMBINED_METRICS_TOPIC


def test_news_items_template_uses_dynamic_topic_lookup():
    """Finding #4: news template should not hardcode topic mapping via case statement."""
    template_path = Path(__file__).resolve().parents[1] / "_includes" / "news_items.html"
    content = template_path.read_text(encoding="utf-8")
    assert "{% case topic %}" not in content
    assert "site.data.news[topic_data_key]" in content


def test_forms_do_not_use_target_blank():
    """Finding #5: forms should submit in same tab without target=_blank."""
    repo_root = Path(__file__).resolve().parents[1]
    contact_form = (repo_root / "_includes" / "contact-getform.html").read_text(encoding="utf-8")
    newsletter_form = (repo_root / "_includes" / "newsletter_subscription.html").read_text(encoding="utf-8")
    assert 'target="_blank"' not in contact_form
    assert 'target="_blank"' not in newsletter_form
