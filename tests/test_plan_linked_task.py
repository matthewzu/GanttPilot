#!/usr/bin/env python3
"""Unit tests for Task 1.4: get_all_tasks_for_project and add_plan linked_task_id."""

import pytest
from ganttpilot_core import DataStore


@pytest.fixture
def data_dir(tmp_path):
    return str(tmp_path / "data")


@pytest.fixture
def store(data_dir):
    ds = DataStore(data_dir)
    ds.add_project("TestProject")
    return ds


class TestGetAllTasksForProject:
    def test_empty_project(self, store):
        result = store.get_all_tasks_for_project("TestProject")
        assert result == []

    def test_nonexistent_project(self, store):
        result = store.get_all_tasks_for_project("NoProject")
        assert result == []

    def test_requirement_with_no_tasks(self, store):
        store.add_requirement("TestProject", "HVP", "Login", "desc")
        result = store.get_all_tasks_for_project("TestProject")
        assert result == []

    def test_single_requirement_single_task(self, store):
        req = store.add_requirement("TestProject", "HVP", "Login", "desc")
        task = store.add_task("TestProject", req["id"], "UI", 3.0, "Build UI")
        result = store.get_all_tasks_for_project("TestProject")
        assert len(result) == 1
        r, t = result[0]
        assert r["id"] == req["id"]
        assert t["id"] == task["id"]

    def test_multiple_requirements_multiple_tasks(self, store):
        req1 = store.add_requirement("TestProject", "HVP", "Login", "d1")
        req2 = store.add_requirement("TestProject", "MVP", "Dashboard", "d2")
        store.add_task("TestProject", req1["id"], "T1", 1.0, "d")
        store.add_task("TestProject", req1["id"], "T2", 2.0, "d")
        store.add_task("TestProject", req2["id"], "T3", 3.0, "d")
        result = store.get_all_tasks_for_project("TestProject")
        assert len(result) == 3
        # Verify ordering: req1's tasks first, then req2's
        assert result[0][0]["id"] == req1["id"]
        assert result[1][0]["id"] == req1["id"]
        assert result[2][0]["id"] == req2["id"]

    def test_returns_tuples_of_req_and_task(self, store):
        req = store.add_requirement("TestProject", "Cat", "Subj", "desc")
        store.add_task("TestProject", req["id"], "Task1", 5.0, "task desc")
        result = store.get_all_tasks_for_project("TestProject")
        r, t = result[0]
        assert r["category"] == "Cat"
        assert r["subject"] == "Subj"
        assert t["subject"] == "Task1"
        assert t["effort_days"] == 5.0


class TestAddPlanLinkedTaskId:
    def test_add_plan_with_linked_task_id(self, store):
        store.add_milestone("TestProject", "MS1")
        plan = store.add_plan("TestProject", "MS1", "Plan1", "dev",
                              "20250101", "20250131", linked_task_id="task123")
        assert plan is not None
        assert plan["linked_task_id"] == "task123"

    def test_add_plan_default_linked_task_id_empty(self, store):
        store.add_milestone("TestProject", "MS1")
        plan = store.add_plan("TestProject", "MS1", "Plan1", "dev",
                              "20250101", "20250131")
        assert plan["linked_task_id"] == ""

    def test_add_plan_still_has_planned_hours_for_compat(self, store):
        store.add_milestone("TestProject", "MS1")
        plan = store.add_plan("TestProject", "MS1", "Plan1", "dev",
                              "20250101", "20250131")
        assert "planned_hours" in plan
        assert plan["planned_hours"] == 0

    def test_add_plan_linked_task_id_persists(self, store, data_dir):
        store.add_milestone("TestProject", "MS1")
        store.add_plan("TestProject", "MS1", "Plan1", "dev",
                       "20250101", "20250131", linked_task_id="abc123")
        # Reload from disk
        store2 = DataStore(data_dir)
        plans = store2.list_plans("TestProject", "MS1")
        assert len(plans) == 1
        assert plans[0]["linked_task_id"] == "abc123"

    def test_existing_callers_not_broken(self, store):
        """Existing callers that don't pass linked_task_id should still work."""
        store.add_milestone("TestProject", "MS1")
        plan = store.add_plan("TestProject", "MS1", "Plan1", "dev",
                              "20250101", "20250131", True, None, "blue")
        assert plan is not None
        assert plan["linked_task_id"] == ""
        assert plan["color"] == "blue"
