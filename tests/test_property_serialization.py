#!/usr/bin/env python3
# Feature: requirement-tracking, Property 1: 序列化往返一致性
"""Property-based test: serialization round-trip consistency.

Validates: Requirements 11.3, 11.1, 11.2, 7.1

For any valid project data containing requirements and tasks,
serializing (save) then deserializing (load) should produce
equivalent data.
"""

import math
import tempfile
import shutil

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
_positive_float = st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False)

task_strategy = st.fixed_dictionaries(
    {
        "subject": _nonempty_text,
        "effort_days": _positive_float,
        "description": _text,
    }
)

requirement_strategy = st.fixed_dictionaries(
    {
        "category": _text,
        "subject": _nonempty_text,
        "description": _text,
        "tasks": st.lists(task_strategy, min_size=0, max_size=5),
    }
)


def _floats_equal(a, b):
    """Compare floats accounting for floating-point representation."""
    if a == b:
        return True
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)


@settings(max_examples=100)
@given(requirements=st.lists(requirement_strategy, min_size=1, max_size=5))
def test_serialization_round_trip(requirements):
    """Property 1: Serialization round-trip consistency.

    A project with requirements and tasks, once saved to disk and
    reloaded via a fresh DataStore, should contain equivalent data.

    Validates: Requirements 11.3, 11.1, 11.2, 7.1
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        _run_round_trip(tmp_dir, requirements)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _run_round_trip(tmp_dir, requirements):
    data_dir = tmp_dir
    project_name = "RoundTripProject"

    # ── Build: create project and populate via DataStore API ──
    ds = DataStore(data_dir)
    ds.add_project(project_name)

    added_reqs = []
    for req_data in requirements:
        req = ds.add_requirement(
            project_name,
            req_data["category"],
            req_data["subject"],
            req_data["description"],
        )
        assert req is not None
        added_tasks = []
        for task_data in req_data["tasks"]:
            task = ds.add_task(
                project_name,
                req["id"],
                task_data["subject"],
                task_data["effort_days"],
                task_data["description"],
            )
            assert task is not None
            added_tasks.append(task)
        added_reqs.append((req, added_tasks))

    # ── Reload: create a new DataStore pointing to the same directory ──
    ds2 = DataStore(data_dir)
    reloaded_project = ds2.get_project(project_name)
    assert reloaded_project is not None

    reloaded_reqs = reloaded_project["requirements"]
    assert len(reloaded_reqs) == len(added_reqs)

    for (orig_req, orig_tasks), reloaded_req in zip(added_reqs, reloaded_reqs):
        # Requirement fields match
        assert reloaded_req["id"] == orig_req["id"]
        assert reloaded_req["category"] == orig_req["category"]
        assert reloaded_req["subject"] == orig_req["subject"]
        assert reloaded_req["description"] == orig_req["description"]

        # Tasks match
        assert len(reloaded_req["tasks"]) == len(orig_tasks)
        for orig_task, reloaded_task in zip(orig_tasks, reloaded_req["tasks"]):
            assert reloaded_task["id"] == orig_task["id"]
            assert reloaded_task["subject"] == orig_task["subject"]
            assert reloaded_task["description"] == orig_task["description"]
            assert _floats_equal(
                reloaded_task["effort_days"], orig_task["effort_days"]
            ), (
                f"effort_days mismatch: {reloaded_task['effort_days']} "
                f"!= {orig_task['effort_days']}"
            )
