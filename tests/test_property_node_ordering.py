#!/usr/bin/env python3
# Feature: requirement-tracking, Property 9: 节点排序保持列表完整性
"""Property-based test: node ordering preserves list integrity.

Validates: Requirements 10.10, 10.11

For any sibling node list, moving a node up or down should only swap it
with its adjacent node. The list length should remain unchanged and all
elements should still be present (only order changes).
"""

import shutil
import tempfile

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from ganttpilot_core import DataStore


# ── Strategies ──────────────────────────────────────────────

_nonempty_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"),
    min_size=1,
    max_size=30,
)
_direction = st.sampled_from(["up", "down"])
_date_str = st.from_regex(
    r"20[0-9]{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])", fullmatch=True
)


@settings(max_examples=100)
@given(
    num_reqs=st.integers(min_value=2, max_value=10),
    target_index=st.data(),
    direction=_direction,
)
def test_move_requirement_preserves_list(num_reqs, target_index, direction):
    """Property 9 (requirement): Moving a requirement preserves list integrity.

    After moving a requirement up or down, the list length is unchanged
    and all requirement IDs are still present.

    Validates: Requirements 10.10, 10.11
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        ds = DataStore(tmp_dir)
        ds.add_project("TestProject")

        # Create N requirements
        reqs = []
        for i in range(num_reqs):
            req = ds.add_requirement("TestProject", "", f"Req{i}", "")
            assert req is not None
            reqs.append(req)

        idx = target_index.draw(st.integers(min_value=0, max_value=num_reqs - 1))
        target_req = reqs[idx]

        ids_before = set(r["id"] for r in ds.list_requirements("TestProject"))
        len_before = len(ds.list_requirements("TestProject"))

        # Move the requirement
        ds.move_requirement("TestProject", target_req["id"], direction)

        reqs_after = ds.list_requirements("TestProject")
        ids_after = set(r["id"] for r in reqs_after)

        # List length unchanged
        assert len(reqs_after) == len_before
        # All elements still present
        assert ids_after == ids_before
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@settings(max_examples=100)
@given(
    num_tasks=st.integers(min_value=2, max_value=10),
    target_index=st.data(),
    direction=_direction,
)
def test_move_task_preserves_list(num_tasks, target_index, direction):
    """Property 9 (task): Moving a task preserves list integrity.

    After moving a task up or down, the list length is unchanged
    and all task IDs are still present.

    Validates: Requirements 10.10, 10.11
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        ds = DataStore(tmp_dir)
        ds.add_project("TestProject")

        req = ds.add_requirement("TestProject", "", "HostReq", "")
        assert req is not None

        tasks = []
        for i in range(num_tasks):
            task = ds.add_task("TestProject", req["id"], f"Task{i}", float(i + 1), "")
            assert task is not None
            tasks.append(task)

        idx = target_index.draw(st.integers(min_value=0, max_value=num_tasks - 1))
        target_task = tasks[idx]

        ids_before = set(t["id"] for t in ds.list_tasks("TestProject", req["id"]))
        len_before = len(ds.list_tasks("TestProject", req["id"]))

        ds.move_task("TestProject", req["id"], target_task["id"], direction)

        tasks_after = ds.list_tasks("TestProject", req["id"])
        ids_after = set(t["id"] for t in tasks_after)

        assert len(tasks_after) == len_before
        assert ids_after == ids_before
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@settings(max_examples=100)
@given(
    num_milestones=st.integers(min_value=2, max_value=10),
    target_index=st.data(),
    direction=_direction,
)
def test_move_milestone_preserves_list(num_milestones, target_index, direction):
    """Property 9 (milestone): Moving a milestone preserves list integrity.

    After moving a milestone up or down, the list length is unchanged
    and all milestone names are still present.

    Validates: Requirements 10.10, 10.11
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        ds = DataStore(tmp_dir)
        ds.add_project("TestProject")

        ms_names = []
        for i in range(num_milestones):
            name = f"MS{i}"
            ds.add_milestone("TestProject", name)
            ms_names.append(name)

        idx = target_index.draw(st.integers(min_value=0, max_value=num_milestones - 1))
        target_name = ms_names[idx]

        names_before = set(m["name"] for m in ds.list_milestones("TestProject"))
        len_before = len(ds.list_milestones("TestProject"))

        ds.move_milestone("TestProject", target_name, direction)

        ms_after = ds.list_milestones("TestProject")
        names_after = set(m["name"] for m in ms_after)

        assert len(ms_after) == len_before
        assert names_after == names_before
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@settings(max_examples=100)
@given(
    num_plans=st.integers(min_value=2, max_value=10),
    target_index=st.data(),
    direction=_direction,
)
def test_move_plan_preserves_list(num_plans, target_index, direction):
    """Property 9 (plan): Moving a plan preserves list integrity.

    After moving a plan up or down, the list length is unchanged
    and all plan IDs are still present.

    Validates: Requirements 10.10, 10.11
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        ds = DataStore(tmp_dir)
        ds.add_project("TestProject")
        ds.add_milestone("TestProject", "MS1")

        plans = []
        for i in range(num_plans):
            plan = ds.add_plan(
                "TestProject", "MS1", f"Plan{i}", "exec",
                "20250101", "20250131",
            )
            assert plan is not None
            plans.append(plan)

        idx = target_index.draw(st.integers(min_value=0, max_value=num_plans - 1))
        target_plan = plans[idx]

        ids_before = set(p["id"] for p in ds.list_plans("TestProject", "MS1"))
        len_before = len(ds.list_plans("TestProject", "MS1"))

        ds.move_plan("TestProject", "MS1", target_plan["id"], direction)

        plans_after = ds.list_plans("TestProject", "MS1")
        ids_after = set(p["id"] for p in plans_after)

        assert len(plans_after) == len_before
        assert ids_after == ids_before
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
