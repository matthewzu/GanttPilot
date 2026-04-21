#!/usr/bin/env python3
# Feature: requirement-tracking, Property 6: 需求跟踪数据正确性
"""Property-based test: tracking data correctly links requirement→task→plan→progress chain.

Validates: Requirements 6.2, 6.4, 6.5

For any project with requirements, tasks, and linked plans,
build_tracking_data should correctly associate each task with its
requirement group and show linked plan name and progress when applicable.
"""

import tempfile
import shutil

from hypothesis import given, settings
from hypothesis import strategies as st

from ganttpilot_core import DataStore
from ganttpilot_gui import build_tracking_data


# ── Strategies ──────────────────────────────────────────────

_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"),
    min_size=0,
    max_size=30,
)
_nonempty_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"),
    min_size=1,
    max_size=30,
)
_positive_float = st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False)
_progress = st.integers(min_value=0, max_value=100)

task_strategy = st.fixed_dictionaries({
    "subject": _nonempty_text,
    "effort_days": _positive_float,
    "description": _text,
})

requirement_strategy = st.fixed_dictionaries({
    "category": _text,
    "subject": _nonempty_text,
    "description": _text,
    "tasks": st.lists(task_strategy, min_size=1, max_size=3),
})

plan_strategy = st.fixed_dictionaries({
    "content": _nonempty_text,
    "executor": _text,
    "start_date": st.just("20250101"),
    "end_date": st.just("20250131"),
    "progress": _progress,
})


@settings(max_examples=100, deadline=None)
@given(
    requirements=st.lists(requirement_strategy, min_size=1, max_size=3),
    plans=st.lists(plan_strategy, min_size=0, max_size=3),
    link_flags=st.lists(st.booleans(), min_size=0, max_size=20),
)
def test_tracking_data_correctness(requirements, plans, link_flags):
    """Property 6: Tracking data correctly links requirement→task→plan→progress chain.

    Validates: Requirements 6.2, 6.4, 6.5
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        _run_tracking_test(tmp_dir, requirements, plans, link_flags)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _run_tracking_test(tmp_dir, requirements, plans, link_flags):
    ds = DataStore(tmp_dir)
    ds.add_project("TrackingTest")
    ds.add_milestone("TrackingTest", "MS1")

    # Add requirements and tasks, collect task IDs
    all_task_ids = []
    added_reqs = []
    for req_data in requirements:
        req = ds.add_requirement("TrackingTest", req_data["category"],
                                 req_data["subject"], req_data["description"])
        req_tasks = []
        for task_data in req_data["tasks"]:
            task = ds.add_task("TrackingTest", req["id"],
                               task_data["subject"], task_data["effort_days"],
                               task_data["description"])
            all_task_ids.append(task["id"])
            req_tasks.append(task)
        added_reqs.append((req, req_tasks))

    # Add plans, optionally linking to tasks
    linked_tasks = {}  # task_id -> (plan_content, progress)
    flag_idx = 0
    for plan_data in plans:
        linked_task_id = ""
        if all_task_ids and flag_idx < len(link_flags) and link_flags[flag_idx]:
            # Link to a task (cycle through available tasks)
            linked_task_id = all_task_ids[flag_idx % len(all_task_ids)]
            linked_tasks[linked_task_id] = (plan_data["content"], plan_data["progress"])
        flag_idx += 1
        plan = ds.add_plan("TrackingTest", "MS1",
                           plan_data["content"], plan_data["executor"],
                           plan_data["start_date"], plan_data["end_date"],
                           linked_task_id=linked_task_id)
        ds.set_plan_progress("TrackingTest", "MS1", plan["id"], plan_data["progress"])

    # Reload to ensure data is persisted
    ds2 = DataStore(tmp_dir)
    proj = ds2.get_project("TrackingTest")
    rows = build_tracking_data(proj)

    # Verify structure: requirement rows followed by their task rows
    total_reqs = len(added_reqs)
    total_tasks = sum(len(tasks) for _, tasks in added_reqs)
    assert len(rows) == total_reqs + total_tasks

    row_idx = 0
    for req, tasks in added_reqs:
        # Requirement header row
        r = rows[row_idx]
        assert r["kind"] == "requirement"
        assert r["req_category"] == req["category"]
        assert r["req_subject"] == req["subject"]
        row_idx += 1

        # Task rows under this requirement
        for task in tasks:
            t = rows[row_idx]
            assert t["kind"] == "task"
            assert t["task_subject"] == task["subject"]

            # Check linked plan info
            if task["id"] in linked_tasks:
                plan_content, plan_progress = linked_tasks[task["id"]]
                assert t["linked_plan"] == plan_content
                assert t["plan_progress"] == f"{plan_progress}%"
            else:
                assert t["linked_plan"] == ""
                assert t["plan_progress"] == ""
            row_idx += 1
