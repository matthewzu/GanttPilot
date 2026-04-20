#!/usr/bin/env python3
"""Unit tests for Task CRUD methods in DataStore."""

import pytest
from ganttpilot_core import DataStore


@pytest.fixture
def data_dir(tmp_path):
    return str(tmp_path / "data")


@pytest.fixture
def store(data_dir):
    ds = DataStore(data_dir)
    ds.add_project("TestProject")
    ds.add_requirement("TestProject", "HVP", "Login", "Login feature")
    return ds


@pytest.fixture
def req_id(store):
    reqs = store.list_requirements("TestProject")
    return reqs[0]["id"]


class TestAddTask:
    def test_add_task_returns_dict(self, store, req_id):
        task = store.add_task("TestProject", req_id, "Implement UI", 3.0, "Build login UI")
        assert task is not None
        assert task["subject"] == "Implement UI"
        assert task["effort_days"] == 3.0
        assert task["description"] == "Build login UI"
        assert "id" in task

    def test_add_task_persists(self, store, req_id):
        store.add_task("TestProject", req_id, "Task1", 1.0, "desc")
        tasks = store.list_tasks("TestProject", req_id)
        assert len(tasks) == 1

    def test_add_task_effort_days_is_float(self, store, req_id):
        task = store.add_task("TestProject", req_id, "Task1", 2, "desc")
        assert isinstance(task["effort_days"], float)
        assert task["effort_days"] == 2.0

    def test_add_task_nonexistent_requirement(self, store):
        task = store.add_task("TestProject", "nonexistent", "Task1", 1.0, "desc")
        assert task is None

    def test_add_task_nonexistent_project(self, store):
        task = store.add_task("NoProject", "any_id", "Task1", 1.0, "desc")
        assert task is None

    def test_add_multiple_tasks(self, store, req_id):
        store.add_task("TestProject", req_id, "Task1", 1.0, "d1")
        store.add_task("TestProject", req_id, "Task2", 2.0, "d2")
        tasks = store.list_tasks("TestProject", req_id)
        assert len(tasks) == 2


class TestUpdateTask:
    def test_update_task_success(self, store, req_id):
        task = store.add_task("TestProject", req_id, "Task1", 1.0, "desc")
        result = store.update_task("TestProject", req_id, task["id"], "Updated", 5.0, "new desc")
        assert result is True
        tasks = store.list_tasks("TestProject", req_id)
        updated = [t for t in tasks if t["id"] == task["id"]][0]
        assert updated["subject"] == "Updated"
        assert updated["effort_days"] == 5.0
        assert updated["description"] == "new desc"

    def test_update_task_nonexistent_task_id(self, store, req_id):
        result = store.update_task("TestProject", req_id, "nonexistent", "A", 1.0, "B")
        assert result is False

    def test_update_task_nonexistent_requirement(self, store):
        result = store.update_task("TestProject", "nonexistent", "tid", "A", 1.0, "B")
        assert result is False

    def test_update_task_nonexistent_project(self, store):
        result = store.update_task("NoProject", "rid", "tid", "A", 1.0, "B")
        assert result is False

    def test_update_task_effort_days_converted_to_float(self, store, req_id):
        task = store.add_task("TestProject", req_id, "Task1", 1.0, "desc")
        store.update_task("TestProject", req_id, task["id"], "Task1", 3, "desc")
        tasks = store.list_tasks("TestProject", req_id)
        updated = [t for t in tasks if t["id"] == task["id"]][0]
        assert isinstance(updated["effort_days"], float)


class TestDeleteTask:
    def test_delete_task_success(self, store, req_id):
        task = store.add_task("TestProject", req_id, "Task1", 1.0, "desc")
        result = store.delete_task("TestProject", req_id, task["id"])
        assert result is True
        assert len(store.list_tasks("TestProject", req_id)) == 0

    def test_delete_task_nonexistent_task_id(self, store, req_id):
        result = store.delete_task("TestProject", req_id, "nonexistent")
        assert result is False

    def test_delete_task_nonexistent_requirement(self, store):
        result = store.delete_task("TestProject", "nonexistent", "tid")
        assert result is False

    def test_delete_task_nonexistent_project(self, store):
        result = store.delete_task("NoProject", "rid", "tid")
        assert result is False

    def test_delete_one_of_multiple(self, store, req_id):
        t1 = store.add_task("TestProject", req_id, "Task1", 1.0, "d1")
        t2 = store.add_task("TestProject", req_id, "Task2", 2.0, "d2")
        store.delete_task("TestProject", req_id, t1["id"])
        tasks = store.list_tasks("TestProject", req_id)
        assert len(tasks) == 1
        assert tasks[0]["id"] == t2["id"]


class TestListTasks:
    def test_list_empty(self, store, req_id):
        tasks = store.list_tasks("TestProject", req_id)
        assert tasks == []

    def test_list_after_add(self, store, req_id):
        store.add_task("TestProject", req_id, "T1", 1.0, "d1")
        store.add_task("TestProject", req_id, "T2", 2.0, "d2")
        tasks = store.list_tasks("TestProject", req_id)
        assert len(tasks) == 2

    def test_list_nonexistent_requirement(self, store):
        tasks = store.list_tasks("TestProject", "nonexistent")
        assert tasks == []

    def test_list_nonexistent_project(self, store):
        tasks = store.list_tasks("NoProject", "rid")
        assert tasks == []
