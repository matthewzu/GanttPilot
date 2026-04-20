#!/usr/bin/env python3
"""Unit tests for node ordering (move) methods in DataStore."""

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


# ── _swap_in_list helper ────────────────────────────────────

class TestSwapInList:
    def test_swap_down(self):
        lst = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        assert DataStore._swap_in_list(lst, "id", "a", "down") is True
        assert [x["id"] for x in lst] == ["b", "a", "c"]

    def test_swap_up(self):
        lst = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        assert DataStore._swap_in_list(lst, "id", "b", "up") is True
        assert [x["id"] for x in lst] == ["b", "a", "c"]

    def test_swap_up_at_first_returns_false(self):
        lst = [{"id": "a"}, {"id": "b"}]
        assert DataStore._swap_in_list(lst, "id", "a", "up") is False
        assert [x["id"] for x in lst] == ["a", "b"]

    def test_swap_down_at_last_returns_false(self):
        lst = [{"id": "a"}, {"id": "b"}]
        assert DataStore._swap_in_list(lst, "id", "b", "down") is False
        assert [x["id"] for x in lst] == ["a", "b"]

    def test_swap_not_found_returns_false(self):
        lst = [{"id": "a"}]
        assert DataStore._swap_in_list(lst, "id", "z", "up") is False

    def test_swap_invalid_direction_returns_false(self):
        lst = [{"id": "a"}, {"id": "b"}]
        assert DataStore._swap_in_list(lst, "id", "a", "left") is False

    def test_swap_with_name_key(self):
        lst = [{"name": "x"}, {"name": "y"}]
        assert DataStore._swap_in_list(lst, "name", "y", "up") is True
        assert [x["name"] for x in lst] == ["y", "x"]


# ── move_requirement ────────────────────────────────────────

class TestMoveRequirement:
    def test_move_down(self, store):
        r1 = store.add_requirement("TestProject", "A", "Req1", "d1")
        r2 = store.add_requirement("TestProject", "B", "Req2", "d2")
        assert store.move_requirement("TestProject", r1["id"], "down") is True
        reqs = store.list_requirements("TestProject")
        assert reqs[0]["id"] == r2["id"]
        assert reqs[1]["id"] == r1["id"]

    def test_move_up(self, store):
        r1 = store.add_requirement("TestProject", "A", "Req1", "d1")
        r2 = store.add_requirement("TestProject", "B", "Req2", "d2")
        assert store.move_requirement("TestProject", r2["id"], "up") is True
        reqs = store.list_requirements("TestProject")
        assert reqs[0]["id"] == r2["id"]
        assert reqs[1]["id"] == r1["id"]

    def test_move_up_at_first(self, store):
        r1 = store.add_requirement("TestProject", "A", "Req1", "d1")
        assert store.move_requirement("TestProject", r1["id"], "up") is False

    def test_move_down_at_last(self, store):
        r1 = store.add_requirement("TestProject", "A", "Req1", "d1")
        assert store.move_requirement("TestProject", r1["id"], "down") is False

    def test_move_nonexistent_project(self, store):
        assert store.move_requirement("NoProject", "id", "up") is False

    def test_move_nonexistent_req(self, store):
        assert store.move_requirement("TestProject", "nope", "up") is False

    def test_move_persists(self, store, data_dir):
        r1 = store.add_requirement("TestProject", "A", "Req1", "d1")
        r2 = store.add_requirement("TestProject", "B", "Req2", "d2")
        store.move_requirement("TestProject", r1["id"], "down")
        # Reload from disk
        store2 = DataStore(data_dir)
        reqs = store2.list_requirements("TestProject")
        assert reqs[0]["id"] == r2["id"]
        assert reqs[1]["id"] == r1["id"]


# ── move_task ────────────────────────────────────────────────

class TestMoveTask:
    def test_move_down(self, store):
        req = store.add_requirement("TestProject", "A", "Req1", "d")
        t1 = store.add_task("TestProject", req["id"], "T1", 1, "d1")
        t2 = store.add_task("TestProject", req["id"], "T2", 2, "d2")
        assert store.move_task("TestProject", req["id"], t1["id"], "down") is True
        tasks = store.list_tasks("TestProject", req["id"])
        assert tasks[0]["id"] == t2["id"]
        assert tasks[1]["id"] == t1["id"]

    def test_move_up(self, store):
        req = store.add_requirement("TestProject", "A", "Req1", "d")
        t1 = store.add_task("TestProject", req["id"], "T1", 1, "d1")
        t2 = store.add_task("TestProject", req["id"], "T2", 2, "d2")
        assert store.move_task("TestProject", req["id"], t2["id"], "up") is True
        tasks = store.list_tasks("TestProject", req["id"])
        assert tasks[0]["id"] == t2["id"]

    def test_move_up_at_first(self, store):
        req = store.add_requirement("TestProject", "A", "Req1", "d")
        t1 = store.add_task("TestProject", req["id"], "T1", 1, "d1")
        assert store.move_task("TestProject", req["id"], t1["id"], "up") is False

    def test_move_down_at_last(self, store):
        req = store.add_requirement("TestProject", "A", "Req1", "d")
        t1 = store.add_task("TestProject", req["id"], "T1", 1, "d1")
        assert store.move_task("TestProject", req["id"], t1["id"], "down") is False

    def test_move_nonexistent_req(self, store):
        assert store.move_task("TestProject", "nope", "tid", "up") is False

    def test_move_nonexistent_task(self, store):
        req = store.add_requirement("TestProject", "A", "Req1", "d")
        assert store.move_task("TestProject", req["id"], "nope", "up") is False


# ── move_milestone ───────────────────────────────────────────

class TestMoveMilestone:
    def test_move_down(self, store):
        store.add_milestone("TestProject", "MS1")
        store.add_milestone("TestProject", "MS2")
        assert store.move_milestone("TestProject", "MS1", "down") is True
        ms_list = store.list_milestones("TestProject")
        assert ms_list[0]["name"] == "MS2"
        assert ms_list[1]["name"] == "MS1"

    def test_move_up(self, store):
        store.add_milestone("TestProject", "MS1")
        store.add_milestone("TestProject", "MS2")
        assert store.move_milestone("TestProject", "MS2", "up") is True
        ms_list = store.list_milestones("TestProject")
        assert ms_list[0]["name"] == "MS2"

    def test_move_up_at_first(self, store):
        store.add_milestone("TestProject", "MS1")
        assert store.move_milestone("TestProject", "MS1", "up") is False

    def test_move_down_at_last(self, store):
        store.add_milestone("TestProject", "MS1")
        assert store.move_milestone("TestProject", "MS1", "down") is False

    def test_move_nonexistent_project(self, store):
        assert store.move_milestone("NoProject", "MS1", "up") is False

    def test_move_nonexistent_milestone(self, store):
        assert store.move_milestone("TestProject", "NoMS", "up") is False

    def test_move_persists(self, store, data_dir):
        store.add_milestone("TestProject", "MS1")
        store.add_milestone("TestProject", "MS2")
        store.move_milestone("TestProject", "MS1", "down")
        store2 = DataStore(data_dir)
        ms_list = store2.list_milestones("TestProject")
        assert ms_list[0]["name"] == "MS2"
        assert ms_list[1]["name"] == "MS1"


# ── move_plan ────────────────────────────────────────────────

class TestMovePlan:
    def test_move_down(self, store):
        store.add_milestone("TestProject", "MS1")
        p1 = store.add_plan("TestProject", "MS1", "Plan1", "exec", "20250101", "20250131")
        p2 = store.add_plan("TestProject", "MS1", "Plan2", "exec", "20250201", "20250228")
        assert store.move_plan("TestProject", "MS1", p1["id"], "down") is True
        plans = store.list_plans("TestProject", "MS1")
        assert plans[0]["id"] == p2["id"]
        assert plans[1]["id"] == p1["id"]

    def test_move_up(self, store):
        store.add_milestone("TestProject", "MS1")
        p1 = store.add_plan("TestProject", "MS1", "Plan1", "exec", "20250101", "20250131")
        p2 = store.add_plan("TestProject", "MS1", "Plan2", "exec", "20250201", "20250228")
        assert store.move_plan("TestProject", "MS1", p2["id"], "up") is True
        plans = store.list_plans("TestProject", "MS1")
        assert plans[0]["id"] == p2["id"]

    def test_move_up_at_first(self, store):
        store.add_milestone("TestProject", "MS1")
        p1 = store.add_plan("TestProject", "MS1", "Plan1", "exec", "20250101", "20250131")
        assert store.move_plan("TestProject", "MS1", p1["id"], "up") is False

    def test_move_down_at_last(self, store):
        store.add_milestone("TestProject", "MS1")
        p1 = store.add_plan("TestProject", "MS1", "Plan1", "exec", "20250101", "20250131")
        assert store.move_plan("TestProject", "MS1", p1["id"], "down") is False

    def test_move_nonexistent_milestone(self, store):
        assert store.move_plan("TestProject", "NoMS", "pid", "up") is False

    def test_move_nonexistent_plan(self, store):
        store.add_milestone("TestProject", "MS1")
        assert store.move_plan("TestProject", "MS1", "nope", "up") is False
