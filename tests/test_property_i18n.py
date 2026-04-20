#!/usr/bin/env python3
# Feature: requirement-tracking, Property 12: 国际化键值完整性
"""Property-based test: i18n key completeness.

Validates: Requirement 8.1

All new translation keys for the requirement tracking feature
exist in both zh and en dictionaries and are non-empty strings.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from ganttpilot_i18n import TEXTS

# All translation keys added for the requirement tracking feature
REQUIREMENT_TRACKING_KEYS = [
    "requirement_analysis",
    "plan_execution",
    "requirement",
    "task",
    "category",
    "subject",
    "effort_days",
    "linked_task",
    "tracking_tab",
    "req_category",
    "req_subject",
    "task_subject",
    "linked_plan",
    "plan_progress",
    "move_up",
    "move_down",
    "edit",
    "add_requirement",
    "edit_requirement",
    "add_task",
    "edit_task",
    "edit_plan",
    "requirement_added",
    "requirement_deleted",
    "task_added",
    "task_deleted",
    "subject_required",
    "invalid_effort",
    "effort_non_negative",
    "report_req_analysis",
    "report_req_tracking",
    "task_count",
    "help_text",
]


@settings(max_examples=100)
@given(key=st.sampled_from(REQUIREMENT_TRACKING_KEYS))
def test_i18n_key_completeness(key):
    """Property 12: 国际化键值完整性

    For every new translation key added for the requirement tracking
    feature, both zh and en dictionaries contain the key and its value
    is a non-empty string.

    **Validates: Requirement 8.1**
    """
    for lang in ("zh", "en"):
        assert key in TEXTS[lang], (
            f"Translation key '{key}' missing in TEXTS['{lang}']"
        )
        value = TEXTS[lang][key]
        assert isinstance(value, str), (
            f"TEXTS['{lang}']['{key}'] is not a string: {type(value)}"
        )
        assert len(value) > 0, (
            f"TEXTS['{lang}']['{key}'] is an empty string"
        )
