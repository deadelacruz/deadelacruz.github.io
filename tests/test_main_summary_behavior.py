"""
Tests for main() summary behavior edge cases.
"""
import os
from unittest.mock import patch

import update_news
from update_news import main, MSG_INFO_NO_API_CALLS, MSG_OK_UPDATE_COMPLETE, MSG_WARNING_UPDATE_ERRORS


def test_main_no_api_calls_and_no_errors_is_not_reported_as_failure():
    """When a run succeeds without API calls, summary should be success (not warning with 0 errors)."""
    config = {
        "api": {
            "combine_topics_in_single_request": False,
            "max_api_calls": 45,
            "topic_delay_seconds": 0,
        },
        "date_range": {
            "lookback_days": 1,
            "exclude_today": True,
            "exclude_today_offset_days": 1,
            "retention_days": 30,
        },
        "metrics": {"export_to_json": False},
        "news_sources": {
            "demo-topic": {
                "name": "Demo Topic",
                "title_query": "Demo",
            }
        },
    }

    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("NEWSAPI_KEY", None)
        with patch("update_news.load_config", return_value=config), \
             patch("update_news.load_existing_news", return_value=[]), \
             patch("update_news.update_news_file", return_value=True), \
             patch.object(update_news.logger, "warning") as mock_warning, \
             patch.object(update_news.logger, "info") as mock_info:
            main()

    # Ensure we don't report "0 error(s)" as a failure summary.
    zero_error_warning = MSG_WARNING_UPDATE_ERRORS.format(count=0)
    assert not any(
        zero_error_warning in str(call.args[0]) for call in mock_warning.call_args_list if call.args
    )

    # Ensure success summary is printed for the no-API-call success path.
    assert any(MSG_OK_UPDATE_COMPLETE in str(call.args[0]) for call in mock_info.call_args_list if call.args)
    assert any(MSG_INFO_NO_API_CALLS in str(call.args[0]) for call in mock_info.call_args_list if call.args)
