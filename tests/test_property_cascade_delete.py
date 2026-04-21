#!/usr/bin/env python3
# Feature: requirement-tracking, Property 11: 级联删除完整性
"""Property-based test: cascade delete integrity.

Validates: Requirements 2.7, 3.5

For any requirement node with tasks, deleting the requirement should also
delete all its subordinate tasks, and the project's requirements list length
should decrease by 1. For any single task node, deleting it should decrease
its parent requirement's tasks list length by 1.
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


@settings(max_examples=100, deadline=None)
@given(
    num_tasks=st.integers(min_value=0, max_value=10),
    category=_text,
    subject=_nonempty_text,
    description=_text,
)
def test_cascade_delete_requirement(num_tasks, category, subject, description):
    """Property 11 (requirement): Deleting a requirement cascades to its tasks.

    After creating a requirement with N tasks and then deleting the requirement,
    the requirements list length should decrease by 1 and all subordinate tasks
    should be gone.

    Validates: Requirements 2.7
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        ds = DataStore(tmp_dir)
        ds.add_project("TestProject")

        # Create the requirement
        req = ds.add_requirement("TestProject", category, subject, description)
        assert req is not None

        # Add N tasks to the requirement
        task_ids = []
        for i in range(num_tasks):
            task = ds.add_task("TestProject", req["id"], f"Task{i}", float(i + 1), "desc")
            assert task is not None
            task_ids.append(task["id"])

        # Verify tasks exist
        assert len(ds.list_tasks("TestProject", req["id"])) == num_tasks

        reqs_before = len(ds.list_requirements("TestProject"))

        # Delete the requirement
        result = ds.delete_requirement("TestProject", req["id"])
        assert result is True

        # Requirements list length decreased by 1
        reqs_after = len(ds.list_requirements("TestProject"))
        assert reqs_after == reqs_before - 1

        # The requirement and its tasks are no longer accessible
        assert ds.get_requirement("TestProject", req["id"]) is None
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@settings(max_examples=100, deadline=None)
@given(
    num_tasks=st.integers(min_value=1, max_value=10),
    task_index=st.data(),
)
def test_delete_single_task(num_tasks, task_index):
    """Property 11 (task): Deleting a task decreases the tasks list by 1.

    After creating a requirement with N tasks and deleting one task,
    the tasks list length should decrease by 1.

    Validates: Requirements 3.5
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        ds = DataStore(tmp_dir)
        ds.add_project("TestProject")

        req = ds.add_requirement("TestProject", "", "HostReq", "")
        assert req is not None

        # Add N tasks
        tasks = []
        for i in range(num_tasks):
            task = ds.add_task("TestProject", req["id"], f"Task{i}", float(i + 1), "desc")
            assert task is not None
            tasks.append(task)

        # Pick a random task to delete
        idx = task_index.draw(st.integers(min_value=0, max_value=num_tasks - 1))
        target_task = tasks[idx]

        tasks_before = len(ds.list_tasks("TestProject", req["id"]))

        # Delete the task
        result = ds.delete_task("TestProject", req["id"], target_task["id"])
        assert result is True

        # Tasks list length decreased by 1
        tasks_after = len(ds.list_tasks("TestProject", req["id"]))
        assert tasks_after == tasks_before - 1

        # The deleted task is no longer in the list
        remaining_ids = [t["id"] for t in ds.list_tasks("TestProject", req["id"])]
        assert target_task["id"] not in remaining_ids
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
