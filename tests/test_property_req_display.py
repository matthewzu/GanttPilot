#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Property test: requirement display format.

Feature: requirement-tracking, Property 2: requirement display format
**Validates: Requirements 2.4, 2.5**

Category non-empty shows `[category]subject`, empty shows just subject.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hypothesis import given, settings
from hypothesis import strategies as st

from ganttpilot_gui import format_requirement_display


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


@given(category=non_empty_category, subject=non_empty_subject)
@settings(max_examples=100)
def test_category_non_empty_shows_bracket_format(category, subject):
    """When category is non-empty, display should be [category]subject."""
    result = format_requirement_display(category, subject)
    assert result == f"[{category}]{subject}", (
        f"Expected '[{category}]{subject}', got '{result}'"
    )


@given(subject=non_empty_subject)
@settings(max_examples=100)
def test_category_empty_shows_subject_only(subject):
    """When category is empty, display should be just subject."""
    result = format_requirement_display("", subject)
    assert result == subject, (
        f"Expected '{subject}', got '{result}'"
    )
