#!/usr/bin/env python3
# Feature: requirement-tracking, Property 5: 旧数据向后兼容
"""Property-based test: backward compatibility with old project data.

Validates: Requirements 7.5, 7.6, 1.4

For any old-format project JSON that does NOT contain a "requirements" field
and whose plans do NOT contain a "linked_task_id" field, loading via DataStore
should automatically initialise an empty requirements list and set
linked_task_id to "" on every plan, while preserving all original milestones,
plans and activities data.
"""

import json
import os
import tempfile
import shutil

from hypothesis import given, settings
from hypothesis import strategies as st

from ganttpilot_core import DataStore

# ── Strategies ──────────────────────────────────────────────

_safe_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"),
    min_size=1,
    max_size=30,
)

_project_name = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
    min_size=1,
    max_size=20,
).filter(lambda s: s.strip() == s and len(s.strip()) > 0)

_date_str = st.from_regex(r"20[0-9]{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])", fullmatch=True)

_positive_float = st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False)

activity_strategy = st.fixed_dictionaries({
    "id": st.from_regex(r"[a-f0-9]{8}", fullmatch=True),
    "executor": _safe_text,
    "date": _date_str,
    "hours": _positive_float,
    "content": _safe_text,
})

# Old-format plan: has planned_hours but NO linked_task_id
old_plan_strategy = st.fixed_dictionaries({
    "id": st.from_regex(r"[a-f0-9]{8}", fullmatch=True),
    "content": _safe_text,
    "executor": _safe_text,
    "start_date": _date_str,
    "end_date": _date_str,
    "planned_hours": _positive_float,
    "status": st.sampled_from(["active", "finished"]),
    "progress": st.integers(min_value=0, max_value=100),
    "actual_end_date": st.just(""),
    "activities": st.lists(activity_strategy, min_size=0, max_size=3),
})

milestone_strategy = st.fixed_dictionaries({
    "id": st.from_regex(r"[a-f0-9]{8}", fullmatch=True),
    "name": _safe_text,
    "description": _safe_text,
    "plans": st.lists(old_plan_strategy, min_size=0, max_size=3),
})

# Old-format project: has milestones but NO requirements field
old_project_strategy = st.fixed_dictionaries({
    "id": st.from_regex(r"[a-f0-9]{8}", fullmatch=True),
    "name": _project_name,
    "description": _safe_text,
    "milestones": st.lists(milestone_strategy, min_size=0, max_size=3),
})


@settings(max_examples=100, deadline=None)
@given(old_project=old_project_strategy)
def test_backward_compat_old_data(old_project):
    """Property 5: Backward compatibility with old project data.

    Old projects loaded via DataStore automatically get an empty
    requirements list and all plans get linked_task_id = "".
    Original milestones, plans and activities data is preserved.

    Validates: Requirements 7.5, 7.6, 1.4
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        _run_backward_compat(tmp_dir, old_project)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _run_backward_compat(tmp_dir, old_project):
    project_name = old_project["name"]

    # Write old-format JSON directly to per-project directory
    proj_dir = os.path.join(tmp_dir, project_name)
    os.makedirs(proj_dir, exist_ok=True)
    proj_file = os.path.join(proj_dir, "project.json")
    with open(proj_file, "w", encoding="utf-8") as f:
        json.dump(old_project, f, ensure_ascii=False, indent=2)

    # Load via DataStore
    ds = DataStore(tmp_dir)
    loaded = ds.get_project(project_name)
    assert loaded is not None, f"Project '{project_name}' not found after load"

    # ── Requirement 7.5: requirements field auto-initialised ──
    assert "requirements" in loaded, "Loaded project missing 'requirements' key"
    assert loaded["requirements"] == [], "Old project should have empty requirements list"

    # ── Requirement 1.4: original milestones/plans/activities preserved ──
    assert len(loaded["milestones"]) == len(old_project["milestones"]), (
        "Milestone count mismatch after load"
    )

    for orig_ms, loaded_ms in zip(old_project["milestones"], loaded["milestones"]):
        assert loaded_ms["name"] == orig_ms["name"]
        assert loaded_ms["description"] == orig_ms["description"]
        assert len(loaded_ms["plans"]) == len(orig_ms["plans"]), (
            f"Plan count mismatch in milestone '{orig_ms['name']}'"
        )

        for orig_plan, loaded_plan in zip(orig_ms["plans"], loaded_ms["plans"]):
            # ── Requirement 7.6: linked_task_id auto-initialised ──
            assert "linked_task_id" in loaded_plan, (
                "Loaded plan missing 'linked_task_id' key"
            )
            assert loaded_plan["linked_task_id"] == "", (
                "Old plan's linked_task_id should be empty string"
            )

            # Original plan data preserved
            assert loaded_plan["id"] == orig_plan["id"]
            assert loaded_plan["content"] == orig_plan["content"]
            assert loaded_plan["executor"] == orig_plan["executor"]
            assert loaded_plan["start_date"] == orig_plan["start_date"]
            assert loaded_plan["end_date"] == orig_plan["end_date"]
            assert loaded_plan["status"] == orig_plan["status"]

            # Activities preserved
            assert len(loaded_plan["activities"]) == len(orig_plan["activities"]), (
                f"Activity count mismatch in plan '{orig_plan['content']}'"
            )
            for orig_act, loaded_act in zip(
                orig_plan["activities"], loaded_plan["activities"]
            ):
                assert loaded_act["id"] == orig_act["id"]
                assert loaded_act["executor"] == orig_act["executor"]
                assert loaded_act["date"] == orig_act["date"]
                assert loaded_act["content"] == orig_act["content"]
