#!/usr/bin/env python3
# Feature: requirement-tracking, Property 4: 节点创建后字段完整性
"""Property-based test: newly created nodes contain all required fields.

Validates: Requirements 7.2, 7.3, 2.3, 3.3, 4.2, 4.5

For any newly created requirement node, it should contain id, category,
subject, description, and tasks fields. For any newly created task node,
it should contain id, subject, effort_days (float type), and description.
For any newly created plan node, it should contain linked_task_id field.
Category and linked_task_id are allowed to be empty strings.
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
_positive_float = st.floats(
    min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False
)
_date_str = st.from_regex(r"20[0-9]{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])", fullmatch=True)


@settings(max_examples=100, deadline=None)
@given(
    category=_text,
    subject=_nonempty_text,
    description=_text,
)
def test_requirement_node_field_completeness(category, subject, description):
    """Property 4 (requirement): New requirement nodes contain all required fields.

    After creating a requirement with random data, the returned node must
    contain: id, category, subject, description, and tasks (list).
    Category can be an empty string.

    Validates: Requirements 7.2, 2.3
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        ds = DataStore(tmp_dir)
        ds.add_project("TestProject")

        req = ds.add_requirement("TestProject", category, subject, description)
        assert req is not None

        # All required fields must exist
        assert "id" in req
        assert "category" in req
        assert "subject" in req
        assert "description" in req
        assert "tasks" in req

        # Type checks
        assert isinstance(req["id"], str) and len(req["id"]) > 0
        assert isinstance(req["category"], str)
        assert isinstance(req["subject"], str)
        assert isinstance(req["description"], str)
        assert isinstance(req["tasks"], list)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@settings(max_examples=100, deadline=None)
@given(
    subject=_nonempty_text,
    effort_days=_positive_float,
    description=_text,
)
def test_task_node_field_completeness(subject, effort_days, description):
    """Property 4 (task): New task nodes contain all required fields.

    After creating a task with random data, the returned node must
    contain: id, subject, effort_days (float type), and description.

    Validates: Requirements 7.3, 3.3
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        ds = DataStore(tmp_dir)
        ds.add_project("TestProject")

        # Create a requirement first to host the task
        req = ds.add_requirement("TestProject", "", "HostReq", "")
        assert req is not None

        task = ds.add_task("TestProject", req["id"], subject, effort_days, description)
        assert task is not None

        # All required fields must exist
        assert "id" in task
        assert "subject" in task
        assert "effort_days" in task
        assert "description" in task

        # Type checks
        assert isinstance(task["id"], str) and len(task["id"]) > 0
        assert isinstance(task["subject"], str)
        assert isinstance(task["effort_days"], float)
        assert isinstance(task["description"], str)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@settings(max_examples=100, deadline=None)
@given(
    content=_nonempty_text,
    executor=_nonempty_text,
    start_date=_date_str,
    end_date=_date_str,
    linked_task_id=_text,
)
def test_plan_node_field_completeness(content, executor, start_date, end_date, linked_task_id):
    """Property 4 (plan): New plan nodes contain linked_task_id field.

    After creating a plan with random data, the returned node must
    contain the linked_task_id field. It is allowed to be an empty string.

    Validates: Requirements 4.2, 4.5
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        ds = DataStore(tmp_dir)
        ds.add_project("TestProject")
        ds.add_milestone("TestProject", "MS1")

        plan = ds.add_plan(
            "TestProject", "MS1", content, executor,
            start_date, end_date,
            linked_task_id=linked_task_id,
        )
        assert plan is not None

        # linked_task_id field must exist
        assert "linked_task_id" in plan
        assert isinstance(plan["linked_task_id"], str)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
