#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Property test: linked task dropdown display format.

Feature: requirement-tracking, Property 3: linked task dropdown display format
**Validates: Requirement 4.4**

Display text should be `[category]req_subject / task_subject` when category is non-empty,
and `req_subject / task_subject` when category is empty.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hypothesis import given, settings
from hypothesis import strategies as st

from ganttpilot_gui import format_linked_task_display


# Strategy: non-empty category string (no brackets to avoid ambiguity)
non_empty_category = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "S"), blacklist_characters="[]"),
    min_size=1, max_size=20
)

# Strategy: non-empty subject string
non_empty_subject = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "S")),
    min_size=1, max_size=50
)


@given(category=non_empty_category, req_subject=non_empty_subject, task_subject=non_empty_subject)
@settings(max_examples=100)
def test_linked_task_display_with_category(category, req_subject, task_subject):
    """When category is non-empty, display should be [category]req_subject / task_subject."""
    result = format_linked_task_display(category, req_subject, task_subject)
    expected = f"[{category}]{req_subject} / {task_subject}"
    assert result == expected, f"Expected '{expected}', got '{result}'"


@given(req_subject=non_empty_subject, task_subject=non_empty_subject)
@settings(max_examples=100)
def test_linked_task_display_without_category(req_subject, task_subject):
    """When category is empty, display should be req_subject / task_subject."""
    result = format_linked_task_display("", req_subject, task_subject)
    expected = f"{req_subject} / {task_subject}"
    assert result == expected, f"Expected '{expected}', got '{result}'"
