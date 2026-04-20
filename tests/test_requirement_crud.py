#!/usr/bin/env python3
"""Unit tests for Requirement CRUD methods in DataStore."""

import os
import json
import shutil
import tempfile
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


class TestAddRequirement:
    def test_add_requirement_returns_dict(self, store):
        req = store.add_requirement("TestProject", "HVP", "Login", "User login feature")
        assert req is not None
        assert req["category"] == "HVP"
        assert req["subject"] == "Login"
        assert req["description"] == "User login feature"
        assert req["tasks"] == []
        assert "id" in req

    def test_add_requirement_persists(self, store):
        store.add_requirement("TestProject", "HVP", "Login", "desc")
        reqs = store.list_requirements("TestProject")
        assert len(reqs) == 1

    def test_add_requirement_empty_category(self, store):
        req = store.add_requirement("TestProject", "", "Feature", "desc")
        assert req is not None
        assert req["category"] == ""

    def test_add_requirement_nonexistent_project(self, store):
        req = store.add_requirement("NoProject", "HVP", "Login", "desc")
        assert req is None

    def test_add_multiple_requirements(self, store):
        store.add_requirement("TestProject", "HVP", "Login", "desc1")
        store.add_requirement("TestProject", "MVP", "Dashboard", "desc2")
        reqs = store.list_requirements("TestProject")
        assert len(reqs) == 2


class TestUpdateRequirement:
    def test_update_requirement_success(self, store):
        req = store.add_requirement("TestProject", "HVP", "Login", "desc")
        result = store.update_requirement("TestProject", req["id"], "MVP", "Updated", "new desc")
        assert result is True
        updated = store.get_requirement("TestProject", req["id"])
        assert updated["category"] == "MVP"
        assert updated["subject"] == "Updated"
        assert updated["description"] == "new desc"

    def test_update_requirement_nonexistent_id(self, store):
        result = store.update_requirement("TestProject", "nonexistent", "A", "B", "C")
        assert result is False

    def test_update_requirement_nonexistent_project(self, store):
        result = store.update_requirement("NoProject", "id", "A", "B", "C")
        assert result is False

    def test_update_preserves_tasks(self, store):
        req = store.add_requirement("TestProject", "HVP", "Login", "desc")
        req["tasks"].append({"id": "t1", "subject": "task1", "effort_days": 1.0, "description": ""})
        store.save()
        store.update_requirement("TestProject", req["id"], "MVP", "Updated", "new")
        updated = store.get_requirement("TestProject", req["id"])
        assert len(updated["tasks"]) == 1


class TestDeleteRequirement:
    def test_delete_requirement_success(self, store):
        req = store.add_requirement("TestProject", "HVP", "Login", "desc")
        result = store.delete_requirement("TestProject", req["id"])
        assert result is True
        assert store.get_requirement("TestProject", req["id"]) is None

    def test_delete_requirement_cascades_tasks(self, store):
        req = store.add_requirement("TestProject", "HVP", "Login", "desc")
        req["tasks"].append({"id": "t1", "subject": "task1", "effort_days": 1.0, "description": ""})
        store.save()
        store.delete_requirement("TestProject", req["id"])
        assert len(store.list_requirements("TestProject")) == 0

    def test_delete_requirement_nonexistent_id(self, store):
        result = store.delete_requirement("TestProject", "nonexistent")
        assert result is False

    def test_delete_requirement_nonexistent_project(self, store):
        result = store.delete_requirement("NoProject", "id")
        assert result is False


class TestListRequirements:
    def test_list_empty(self, store):
        reqs = store.list_requirements("TestProject")
        assert reqs == []

    def test_list_after_add(self, store):
        store.add_requirement("TestProject", "A", "Req1", "d1")
        store.add_requirement("TestProject", "B", "Req2", "d2")
        reqs = store.list_requirements("TestProject")
        assert len(reqs) == 2

    def test_list_nonexistent_project(self, store):
        reqs = store.list_requirements("NoProject")
        assert reqs == []


class TestGetRequirement:
    def test_get_existing(self, store):
        req = store.add_requirement("TestProject", "HVP", "Login", "desc")
        found = store.get_requirement("TestProject", req["id"])
        assert found is not None
        assert found["id"] == req["id"]

    def test_get_nonexistent(self, store):
        found = store.get_requirement("TestProject", "nonexistent")
        assert found is None

    def test_get_nonexistent_project(self, store):
        found = store.get_requirement("NoProject", "id")
        assert found is None
