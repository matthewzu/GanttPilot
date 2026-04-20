#!/usr/bin/env python3
# Feature: requirement-tracking, Property 13: 添加需求增长列表
"""Property-based test: adding a requirement grows the list by 1.

Validates: Requirements 1.3

For any project and valid requirement data (subject non-empty),
adding a requirement should increase the requirements list length
by exactly 1, and the new requirement's fields should match the input.
"""

import shutil
import tempfile

from hypothesis import given, settings
from hypothesis import strategies as st

from ganttpilot_core import DataStore


# ── Strategies ──────────────────────────────────────────────

_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"),
    min_size=0,
    max_size=50,
)
_nonempty_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"),
    min_size=1,
    max_size=50,
)


@settings(max_examples=100)
@given(
    category=_text,
    subject=_nonempty_text,
    description=_text,
)
def test_add_requirement_grows_list(category, subject, description):
    """Property 13: Adding a requirement grows the list by 1.

    After adding a requirement with random data, the requirements list
    length should increase by exactly 1 and the new requirement's fields
    should match the provided input.

    Validates: Requirements 1.3
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        project_name = "TestProject"

        ds = DataStore(tmp_dir)
        ds.add_project(project_name)

        initial_count = len(ds.list_requirements(project_name))

        req = ds.add_requirement(project_name, category, subject, description)
        assert req is not None

        new_count = len(ds.list_requirements(project_name))
        assert new_count == initial_count + 1

        # Verify the new requirement's fields match input
        assert req["category"] == category
        assert req["subject"] == subject
        assert req["description"] == description
        assert "id" in req
        assert isinstance(req["tasks"], list)
        assert len(req["tasks"]) == 0
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
