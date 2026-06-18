#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GanttPilot - Core Data Model & Business Logic / 核心数据模型与业务逻辑

Data is stored per project, with two format generations:

  v2 (fully split — new default):
    data_dir/{project_name}/
      project.json           — config only (id, name, remote, tags, order indices)
      requirements/
        {req_id}.json        — single requirement with its tasks
      milestones/
        {ms_id}.json         — milestone metadata + plans (without activities)
      activities/
        {plan_id}.json       — activities array for one plan

  v0/v1 (legacy — auto-loaded, never written for new projects):
    data_dir/{project_name}/
      project.json           — everything in one file

This split structure minimizes git merge conflicts: edits to different
requirements, milestones, or plans touch different files.
"""

import copy
import json
import os
import re
import uuid
import warnings
from datetime import datetime, timedelta


def _new_id():
    return uuid.uuid4().hex[:8]


def _parse_date(s):
    """Parse YYYYMMDD string to date"""
    return datetime.strptime(s, "%Y%m%d").date()


def _format_date(d):
    """Format date to YYYYMMDD"""
    return d.strftime("%Y%m%d")


def _workdays_between(start, end, skip_dates=None):
    """Count workdays between two dates, optionally skipping extra dates"""
    skip = set()
    if skip_dates:
        for ds in skip_dates:
            try:
                skip.add(_parse_date(ds.strip()))
            except ValueError:
                pass
    count = 0
    current = start
    while current <= end:
        if current.weekday() < 5 and current not in skip:
            count += 1
        current += timedelta(days=1)
    return count


_TIME_SLOT_RE = re.compile(r'^(\d{4})/(\d{4})$')


def parse_time_slots(time_slots_str):
    """解析 Time_Slot_List 字符串为时间段列表。

    Args:
        time_slots_str: 如 "0900/1200,1430/1500"

    Returns:
        list[tuple[str, str]]: 如 [("0900", "1200"), ("1430", "1500")]

    Raises:
        ValueError: 格式不合法时抛出
    """
    if not time_slots_str or not time_slots_str.strip():
        return []

    # Support Chinese comma as separator
    time_slots_str = time_slots_str.replace("\uff0c", ",")

    slots = []
    for part in time_slots_str.split(","):
        part = part.strip()
        m = _TIME_SLOT_RE.match(part)
        if not m:
            raise ValueError(f"Invalid time slot format: '{part}'")
        start, end = m.group(1), m.group(2)
        # Validate HH and MM ranges
        for t_str in (start, end):
            hh, mm = int(t_str[:2]), int(t_str[2:])
            if hh > 23 or mm > 59:
                raise ValueError(f"Time out of range: '{t_str}'")
        # Validate start < end
        if int(start) >= int(end):
            raise ValueError(
                f"Start time must be strictly before end time: '{start}/{end}'"
            )
        slots.append((start, end))
    return slots


def format_time_slots(slots):
    """将时间段列表格式化为 Time_Slot_List 字符串。

    Args:
        slots: list[tuple[str, str]]

    Returns:
        str: 如 "0900/1200,1430/1500"
    """
    return ",".join(f"{s}/{e}" for s, e in slots)


def calculate_hours_from_slots(time_slots_str):
    """从 Time_Slot_List 计算总工时（小时数）。

    Args:
        time_slots_str: 如 "0900/1200,1430/1500"

    Returns:
        float: 总小时数（如 4.5）
    """
    slots = parse_time_slots(time_slots_str)
    if not slots:
        return 0.0
    total_minutes = 0
    for start, end in slots:
        start_min = int(start[:2]) * 60 + int(start[2:])
        end_min = int(end[:2]) * 60 + int(end[2:])
        total_minutes += end_min - start_min
    return total_minutes / 60.0


class DataStore:
    """Manages project data with per-project directory storage.

    Storage layout (v2 — fully split):
      data_dir/
        {project_name}/
          project.json              — config: id, name, description, remote_*, tags,
                                      requirement_order, milestone_order
          requirements/
            {req_id}.json           — single requirement with tasks array
          milestones/
            {ms_id}.json            — milestone with plans array (no activities)
          activities/
            {plan_id}.json          — activities array for one plan

    Backward compatible: loads legacy single-file project.json transparently.
    Internally maintains self.data = {"projects": [...]} as a unified view.
    """

    # Sentinel: the v2 split format is indicated by existence of milestones/ dir
    _SPLIT_MARKER_DIR = "milestones"

    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.data = {"projects": []}
        self._clipboard = None  # {"type": str, "data": dict}
        # Projects that have been explicitly migrated (by name)
        self._migrated_projects = set()
        self.load()

    # ── Persistence ──────────────────────────────────────────

    def _is_split_format(self, proj_dir):
        """Return True if the project directory uses the v2 split layout."""
        return os.path.isdir(os.path.join(proj_dir, self._SPLIT_MARKER_DIR))

    def load(self):
        os.makedirs(self.data_dir, exist_ok=True)

        # ── Migration: ancient projects.json → per-project directories ──
        old_file = os.path.join(self.data_dir, "projects.json")
        if os.path.exists(old_file):
            try:
                with open(old_file, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                for proj in old_data.get("projects", []):
                    proj_dir = os.path.join(self.data_dir, proj["name"])
                    os.makedirs(proj_dir, exist_ok=True)
                    proj_file = os.path.join(proj_dir, "project.json")
                    with open(proj_file, "w", encoding="utf-8") as f:
                        json.dump(proj, f, ensure_ascii=False, indent=2)
                os.remove(old_file)
            except (json.JSONDecodeError, IOError, KeyError) as e:
                warnings.warn(f"Migration of old projects.json failed: {e}")

        # ── Load projects ──
        projects = []
        if os.path.isdir(self.data_dir):
            for entry in sorted(os.listdir(self.data_dir)):
                sub = os.path.join(self.data_dir, entry)
                if not os.path.isdir(sub):
                    continue
                proj_file = os.path.join(sub, "project.json")
                if not os.path.isfile(proj_file):
                    continue
                try:
                    if self._is_split_format(sub):
                        proj = self._load_split(sub, proj_file)
                    else:
                        proj = self._load_legacy(sub, proj_file)
                    projects.append(proj)
                except (json.JSONDecodeError, IOError) as e:
                    warnings.warn(f"Skipping project in '{entry}': {e}")
        self.data = {"projects": projects}

    def _load_split(self, proj_dir, proj_file):
        """Load a project in v2 split format."""
        with open(proj_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

        # Build full project dict from config
        proj = {
            "id": meta.get("id", ""),
            "name": meta.get("name", ""),
            "description": meta.get("description", ""),
            "remote_url": meta.get("remote_url", ""),
            "remote_username": meta.get("remote_username", ""),
            "remote_password": meta.get("remote_password", ""),
            "remote_branch": meta.get("remote_branch", "main"),
            "tags": meta.get("tags", []),
            "requirements": [],
            "milestones": [],
        }

        # Load requirements in order
        req_order = meta.get("requirement_order", [])
        req_dir = os.path.join(proj_dir, "requirements")
        if os.path.isdir(req_dir):
            # Load ordered ones first
            loaded_ids = set()
            for req_id in req_order:
                rfile = os.path.join(req_dir, f"{req_id}.json")
                if os.path.isfile(rfile):
                    with open(rfile, "r", encoding="utf-8") as f:
                        req = json.load(f)
                    proj["requirements"].append(req)
                    loaded_ids.add(req_id)
            # Load any unordered files (safety)
            for fname in sorted(os.listdir(req_dir)):
                if fname.endswith(".json"):
                    rid = fname[:-5]
                    if rid not in loaded_ids:
                        with open(os.path.join(req_dir, fname), "r", encoding="utf-8") as f:
                            proj["requirements"].append(json.load(f))

        # Load milestones in order
        ms_order = meta.get("milestone_order", [])
        ms_dir = os.path.join(proj_dir, "milestones")
        loaded_ms_ids = set()
        for ms_id in ms_order:
            mfile = os.path.join(ms_dir, f"{ms_id}.json")
            if os.path.isfile(mfile):
                with open(mfile, "r", encoding="utf-8") as f:
                    ms = json.load(f)
                self._fill_milestone_defaults(ms, proj_dir)
                proj["milestones"].append(ms)
                loaded_ms_ids.add(ms_id)
        # Load any unordered milestone files (safety)
        for fname in sorted(os.listdir(ms_dir)):
            if fname.endswith(".json"):
                mid = fname[:-5]
                if mid not in loaded_ms_ids:
                    with open(os.path.join(ms_dir, fname), "r", encoding="utf-8") as f:
                        ms = json.load(f)
                    self._fill_milestone_defaults(ms, proj_dir)
                    proj["milestones"].append(ms)

        return proj

    def _load_legacy(self, proj_dir, proj_file):
        """Load a project from legacy single-file format."""
        with open(proj_file, "r", encoding="utf-8") as f:
            proj = json.load(f)

        # Fill missing project-level defaults
        proj.setdefault("description", "")
        proj.pop("committer_name", None)
        proj.pop("committer_email", None)
        proj.pop("priv_branch", None)
        proj.setdefault("requirements", [])

        # Load activities from separate files (v1 split) or inline (v0)
        activities_dir = os.path.join(proj_dir, "activities")
        for ms in proj.get("milestones", []):
            self._fill_milestone_defaults(ms, proj_dir)

        return proj

    def _fill_milestone_defaults(self, ms, proj_dir):
        """Fill default values for plans and load activities."""
        activities_dir = os.path.join(proj_dir, "activities")
        for plan in ms.get("plans", []):
            plan.setdefault("progress", 0)
            plan.setdefault("actual_end_date", "")
            plan.setdefault("planned_hours", 0)
            plan.setdefault("linked_task_id", "")
            if plan.get("status") == "finished" and plan["progress"] == 0:
                plan["progress"] = 100

            # Load activities: prefer separate file, fall back to inline
            plan_id = plan["id"]
            act_file = os.path.join(activities_dir, f"{plan_id}.json")
            if os.path.isfile(act_file):
                try:
                    with open(act_file, "r", encoding="utf-8") as af:
                        plan["activities"] = json.load(af)
                except (json.JSONDecodeError, IOError):
                    plan.setdefault("activities", [])
            else:
                plan.setdefault("activities", [])

            for activity in plan.get("activities", []):
                activity.setdefault("time_slots", "")
                activity.setdefault("tag", "")
                activity.setdefault("description", "")

    def save(self):
        os.makedirs(self.data_dir, exist_ok=True)
        for proj in self.data.get("projects", []):
            proj_dir = os.path.join(self.data_dir, proj["name"])
            os.makedirs(proj_dir, exist_ok=True)

            # Defensive: strip personal fields
            proj.pop("committer_name", None)
            proj.pop("committer_email", None)
            proj.pop("priv_branch", None)

            # Decide format: use v2 split if already split or explicitly migrated
            if (self._is_split_format(proj_dir)
                    or proj["name"] in self._migrated_projects):
                self._save_split(proj, proj_dir)
            else:
                self._save_legacy(proj, proj_dir)

    def _save_split(self, proj, proj_dir):
        """Save project in v2 fully-split format."""
        req_dir = os.path.join(proj_dir, "requirements")
        ms_dir = os.path.join(proj_dir, "milestones")
        act_dir = os.path.join(proj_dir, "activities")
        os.makedirs(req_dir, exist_ok=True)
        os.makedirs(ms_dir, exist_ok=True)
        os.makedirs(act_dir, exist_ok=True)

        # ── Write project.json (config only) ──
        meta = {
            "id": proj.get("id", ""),
            "name": proj["name"],
            "description": proj.get("description", ""),
            "remote_url": proj.get("remote_url", ""),
            "remote_username": proj.get("remote_username", ""),
            "remote_password": proj.get("remote_password", ""),
            "remote_branch": proj.get("remote_branch", "main"),
            "tags": proj.get("tags", []),
            "requirement_order": [r["id"] for r in proj.get("requirements", [])],
            "milestone_order": [m["id"] for m in proj.get("milestones", [])],
        }
        with open(os.path.join(proj_dir, "project.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # ── Write requirements ──
        active_req_ids = set()
        for req in proj.get("requirements", []):
            active_req_ids.add(req["id"])
            with open(os.path.join(req_dir, f"{req['id']}.json"), "w", encoding="utf-8") as f:
                json.dump(req, f, ensure_ascii=False, indent=2)
        # Clean orphaned requirement files
        for fname in os.listdir(req_dir):
            if fname.endswith(".json") and fname[:-5] not in active_req_ids:
                os.remove(os.path.join(req_dir, fname))

        # ── Write milestones + activities ──
        active_ms_ids = set()
        active_plan_ids = set()
        for ms in proj.get("milestones", []):
            active_ms_ids.add(ms["id"])
            # Write milestone (plans without activities)
            ms_copy = copy.deepcopy(ms)
            for plan in ms_copy.get("plans", []):
                plan_id = plan["id"]
                active_plan_ids.add(plan_id)
                activities = plan.pop("activities", [])
                # Write activities to separate file
                with open(os.path.join(act_dir, f"{plan_id}.json"), "w", encoding="utf-8") as f:
                    json.dump(activities, f, ensure_ascii=False, indent=2)
            with open(os.path.join(ms_dir, f"{ms['id']}.json"), "w", encoding="utf-8") as f:
                json.dump(ms_copy, f, ensure_ascii=False, indent=2)

        # Clean orphaned milestone files
        for fname in os.listdir(ms_dir):
            if fname.endswith(".json") and fname[:-5] not in active_ms_ids:
                os.remove(os.path.join(ms_dir, fname))
        # Clean orphaned activity files
        for fname in os.listdir(act_dir):
            if fname.endswith(".json") and fname[:-5] not in active_plan_ids:
                os.remove(os.path.join(act_dir, fname))

    def _save_legacy(self, proj, proj_dir):
        """Save project in legacy single-file format (backward compat)."""
        proj_file = os.path.join(proj_dir, "project.json")
        with open(proj_file, "w", encoding="utf-8") as f:
            json.dump(proj, f, ensure_ascii=False, indent=2)

    # ── Migration ────────────────────────────────────────────

    def needs_migration(self, local_only=False):
        """Check if any project still uses old format (not fully split).

        Args:
            local_only: If True, only check projects without remote_url.

        Returns True if at least one qualifying project is not in v2 split format.
        """
        for proj in self.data.get("projects", []):
            if local_only and proj.get("remote_url"):
                continue
            proj_dir = os.path.join(self.data_dir, proj["name"])
            if not self._is_split_format(proj_dir):
                # Has actual content to migrate?
                if proj.get("milestones") or proj.get("requirements"):
                    return True
        return False

    def migrate_to_split(self, local_only=False):
        """Migrate projects to v2 fully-split format.

        Args:
            local_only: If True, only migrate projects without remote_url.

        Returns the number of projects migrated.
        """
        count = 0
        for proj in self.data.get("projects", []):
            if local_only and proj.get("remote_url"):
                continue
            proj_dir = os.path.join(self.data_dir, proj["name"])
            if not self._is_split_format(proj_dir):
                self._migrated_projects.add(proj["name"])
                count += 1
        self.save()
        return count

    # ── Project ──────────────────────────────────────────────
    def list_projects(self):
        return self.data.get("projects", [])

    def get_project(self, name):
        for p in self.data["projects"]:
            if p["name"] == name:
                return p
        return None

    def add_project(self, name, remote_url="", remote_username="", remote_password="", description="", tags=None,
                    remote_branch="main", priv_branch=""):
        if self.get_project(name):
            return None
        proj = {
            "id": _new_id(),
            "name": name,
            "description": description,
            "remote_url": remote_url,
            "remote_username": remote_username,
            "remote_password": remote_password,
            "remote_branch": remote_branch,
            "tags": tags or [],
            "requirements": [],
            "milestones": [],
        }
        self.data["projects"].append(proj)
        self.save()
        return proj

    def delete_project(self, name):
        before = len(self.data["projects"])
        self.data["projects"] = [p for p in self.data["projects"] if p["name"] != name]
        if len(self.data["projects"]) < before:
            self.save()
            return True
        return False

    # ── Milestone ────────────────────────────────────────────
    def list_milestones(self, project_name):
        proj = self.get_project(project_name)
        return proj["milestones"] if proj else []

    def add_milestone(self, project_name, milestone_name, description="", color="", deadline=""):
        proj = self.get_project(project_name)
        if not proj:
            return None
        for ms in proj["milestones"]:
            if ms["name"] == milestone_name:
                return None
        ms = {"id": _new_id(), "name": milestone_name, "description": description, "color": color, "deadline": deadline, "plans": []}
        proj["milestones"].append(ms)
        self.save()
        return ms

    def delete_milestone(self, project_name, milestone_name):
        proj = self.get_project(project_name)
        if not proj:
            return False
        before = len(proj["milestones"])
        proj["milestones"] = [m for m in proj["milestones"] if m["name"] != milestone_name]
        if len(proj["milestones"]) < before:
            self.save()
            return True
        return False

    def _find_milestone(self, project_name, milestone_name):
        proj = self.get_project(project_name)
        if not proj:
            return None
        for ms in proj["milestones"]:
            if ms["name"] == milestone_name:
                return ms
        return None

    # ── Requirement ──────────────────────────────────────────
    def list_requirements(self, project_name):
        proj = self.get_project(project_name)
        return proj["requirements"] if proj else []

    def get_requirement(self, project_name, req_id):
        proj = self.get_project(project_name)
        if not proj:
            return None
        for req in proj.get("requirements", []):
            if req["id"] == req_id:
                return req
        return None

    def add_requirement(self, project_name, category, subject, description):
        proj = self.get_project(project_name)
        if not proj:
            return None
        req = {
            "id": _new_id(),
            "category": category,
            "subject": subject,
            "description": description,
            "tasks": [],
        }
        proj.setdefault("requirements", []).append(req)
        self.save()
        return req

    def update_requirement(self, project_name, req_id, category, subject, description):
        req = self.get_requirement(project_name, req_id)
        if not req:
            return False
        req["category"] = category
        req["subject"] = subject
        req["description"] = description
        self.save()
        return True

    def delete_requirement(self, project_name, req_id):
        proj = self.get_project(project_name)
        if not proj:
            return False
        reqs = proj.get("requirements", [])
        before = len(reqs)
        proj["requirements"] = [r for r in reqs if r["id"] != req_id]
        if len(proj["requirements"]) < before:
            self.save()
            return True
        return False

    # ── Task ─────────────────────────────────────────────────
    def add_task(self, project_name, req_id, subject, effort_days, description):
        req = self.get_requirement(project_name, req_id)
        if not req:
            return None
        task = {
            "id": _new_id(),
            "subject": subject,
            "effort_days": float(effort_days),
            "description": description,
        }
        req.setdefault("tasks", []).append(task)
        self.save()
        return task

    def update_task(self, project_name, req_id, task_id, subject, effort_days, description):
        req = self.get_requirement(project_name, req_id)
        if not req:
            return False
        for task in req.get("tasks", []):
            if task["id"] == task_id:
                task["subject"] = subject
                task["effort_days"] = float(effort_days)
                task["description"] = description
                self.save()
                return True
        return False

    def delete_task(self, project_name, req_id, task_id):
        req = self.get_requirement(project_name, req_id)
        if not req:
            return False
        tasks = req.get("tasks", [])
        before = len(tasks)
        req["tasks"] = [t for t in tasks if t["id"] != task_id]
        if len(req["tasks"]) < before:
            self.save()
            return True
        return False

    def list_tasks(self, project_name, req_id):
        req = self.get_requirement(project_name, req_id)
        return req.get("tasks", []) if req else []

    # ── Plan ─────────────────────────────────────────────────
    def list_plans(self, project_name, milestone_name):
        ms = self._find_milestone(project_name, milestone_name)
        return ms["plans"] if ms else []

    def add_plan(self, project_name, milestone_name, content, executor,
                 start_date, end_date, skip_non_workdays=True, skip_dates=None,
                 color="", linked_task_id=""):
        ms = self._find_milestone(project_name, milestone_name)
        if not ms:
            return None
        plan = {
            "id": _new_id(),
            "content": content,
            "executor": executor,
            "start_date": start_date,
            "end_date": end_date,
            "skip_non_workdays": skip_non_workdays,
            "skip_dates": skip_dates or [],
            "color": color,
            "linked_task_id": linked_task_id,
            "planned_hours": 0,
            "status": "active",
            "progress": 0,
            "actual_end_date": "",
            "activities": [],
        }
        ms["plans"].append(plan)
        self.save()
        return plan

    def delete_plan(self, project_name, milestone_name, plan_id):
        ms = self._find_milestone(project_name, milestone_name)
        if not ms:
            return False
        before = len(ms["plans"])
        ms["plans"] = [p for p in ms["plans"] if p["id"] != plan_id]
        if len(ms["plans"]) < before:
            self.save()
            return True
        return False

    def finish_plan(self, project_name, milestone_name, plan_id):
        ms = self._find_milestone(project_name, milestone_name)
        if not ms:
            return False
        for plan in ms["plans"]:
            if plan["id"] == plan_id:
                plan["status"] = "finished"
                plan["progress"] = 100
                plan["actual_end_date"] = _format_date(datetime.now().date())
                self.save()
                return True
        return False

    def reopen_plan(self, project_name, milestone_name, plan_id):
        """Reopen a finished plan, resetting status to active."""
        ms = self._find_milestone(project_name, milestone_name)
        if not ms:
            return False
        for plan in ms["plans"]:
            if plan["id"] == plan_id:
                plan["status"] = "active"
                plan["actual_end_date"] = ""
                self.save()
                return True
        return False

    def _find_plan(self, project_name, milestone_name, plan_id):
        ms = self._find_milestone(project_name, milestone_name)
        if not ms:
            return None
        for plan in ms["plans"]:
            if plan["id"] == plan_id:
                return plan
        return None

    def set_plan_progress(self, project_name, milestone_name, plan_id, progress):
        """Set plan progress percentage (0-100) and persist."""
        plan = self._find_plan(project_name, milestone_name, plan_id)
        if not plan:
            return False
        plan["progress"] = progress
        self.save()
        return True

    # ── Activity ─────────────────────────────────────────────
    def add_activity(self, project_name, milestone_name, plan_id,
                     executor, date, hours, content, time_slots="", tag="", description=""):
        plan = self._find_plan(project_name, milestone_name, plan_id)
        if not plan:
            return None
        if time_slots:
            hours = calculate_hours_from_slots(time_slots)
        activity = {
            "id": _new_id(),
            "executor": executor,
            "date": date,
            "hours": hours,
            "content": content,
            "time_slots": time_slots,
            "tag": tag,
            "description": description,
        }
        plan["activities"].append(activity)
        self.save()
        return activity

    def delete_activity(self, project_name, milestone_name, plan_id, activity_id):
        plan = self._find_plan(project_name, milestone_name, plan_id)
        if not plan:
            return False
        before = len(plan["activities"])
        plan["activities"] = [a for a in plan["activities"] if a["id"] != activity_id]
        if len(plan["activities"]) < before:
            self.save()
            return True
        return False

    # ── Rename / Update ──────────────────────────────────────
    def rename_project(self, old_name, new_name):
        """Rename a project: update in-memory data and rename filesystem directory."""
        if not new_name or not new_name.strip():
            return False
        new_name = new_name.strip()
        if old_name == new_name:
            return True
        # Check for duplicate
        if self.get_project(new_name):
            return False
        proj = self.get_project(old_name)
        if not proj:
            return False
        # Rename filesystem directory
        old_dir = os.path.join(self.data_dir, old_name)
        new_dir = os.path.join(self.data_dir, new_name)
        if os.path.isdir(old_dir):
            os.rename(old_dir, new_dir)
        # Update in-memory data
        proj["name"] = new_name
        self.save()
        return True

    def update_milestone(self, project_name, old_ms_name, new_name, description, deadline=""):
        """Update milestone name, description and deadline. Check for duplicates."""
        if not new_name or not new_name.strip():
            return False
        new_name = new_name.strip()
        proj = self.get_project(project_name)
        if not proj:
            return False
        ms = None
        for m in proj["milestones"]:
            if m["name"] == old_ms_name:
                ms = m
                break
        if not ms:
            return False
        if old_ms_name != new_name:
            for m in proj["milestones"]:
                if m["name"] == new_name:
                    return False
        ms["name"] = new_name
        ms["description"] = description
        ms["deadline"] = deadline
        self.save()
        return True

    def update_activity(self, project_name, milestone_name, plan_id,
                        activity_id, executor, date, hours, content,
                        time_slots="", tag="", description=""):
        """Update activity attributes and persist."""
        plan = self._find_plan(project_name, milestone_name, plan_id)
        if not plan:
            return False
        for act in plan["activities"]:
            if act["id"] == activity_id:
                act["executor"] = executor
                act["date"] = date
                act["content"] = content
                act["time_slots"] = time_slots
                act["tag"] = tag
                act["description"] = description
                if time_slots:
                    act["hours"] = calculate_hours_from_slots(time_slots)
                else:
                    act["hours"] = hours
                self.save()
                return True
        return False

    # ── Node ordering ────────────────────────────────────────
    @staticmethod
    def _swap_in_list(lst, id_key, item_id, direction):
        """Swap an item with its sibling in a list.

        Args:
            lst: The list containing items.
            id_key: The key used to identify items (e.g. "id", "name").
            item_id: The value of id_key for the target item.
            direction: "up" or "down".

        Returns:
            True if swapped, False if no-op (already at boundary or not found).
        """
        idx = None
        for i, item in enumerate(lst):
            if item[id_key] == item_id:
                idx = i
                break
        if idx is None:
            return False
        if direction == "up":
            if idx == 0:
                return False
            lst[idx], lst[idx - 1] = lst[idx - 1], lst[idx]
            return True
        elif direction == "down":
            if idx >= len(lst) - 1:
                return False
            lst[idx], lst[idx + 1] = lst[idx + 1], lst[idx]
            return True
        return False

    def move_requirement(self, project_name, req_id, direction):
        """Move a requirement up or down within the project's requirements list."""
        proj = self.get_project(project_name)
        if not proj:
            return False
        if self._swap_in_list(proj.get("requirements", []), "id", req_id, direction):
            self.save()
            return True
        return False

    def move_task(self, project_name, req_id, task_id, direction):
        """Move a task up or down within its requirement's tasks list."""
        req = self.get_requirement(project_name, req_id)
        if not req:
            return False
        if self._swap_in_list(req.get("tasks", []), "id", task_id, direction):
            self.save()
            return True
        return False

    def move_milestone(self, project_name, ms_name, direction):
        """Move a milestone up or down within the project's milestones list."""
        proj = self.get_project(project_name)
        if not proj:
            return False
        if self._swap_in_list(proj.get("milestones", []), "name", ms_name, direction):
            self.save()
            return True
        return False

    def move_plan(self, project_name, ms_name, plan_id, direction):
        """Move a plan up or down within its milestone's plans list."""
        ms = self._find_milestone(project_name, ms_name)
        if not ms:
            return False
        if self._swap_in_list(ms.get("plans", []), "id", plan_id, direction):
            self.save()
            return True
        return False


    def move_activity(self, project_name, ms_name, plan_id, activity_id, direction):
        """Move an activity up or down within its plan's activities list."""
        plan = self._find_plan(project_name, ms_name, plan_id)
        if not plan:
            return False
        if self._swap_in_list(plan.get("activities", []), "id", activity_id, direction):
            self.save()
            return True
        return False


    # ── Query helpers ────────────────────────────────────────
    def get_all_tasks_for_project(self, project_name):
        """Return [(req_dict, task_dict)] for all requirements and their tasks in the project."""
        proj = self.get_project(project_name)
        if not proj:
            return []
        result = []
        for req in proj.get("requirements", []):
            for task in req.get("tasks", []):
                result.append((req, task))
        return result

    def get_all_plans_for_project(self, project_name):
        """Flat list of (milestone_name, plan) for a project"""
        proj = self.get_project(project_name)
        if not proj:
            return []
        result = []
        for ms in proj["milestones"]:
            for plan in ms["plans"]:
                result.append((ms["name"], plan))
        return result

    def get_time_report(self, project_name):
        """Returns {executor: {"hours": float, "days": float}, "by_tag": {tag: float}} for a project"""
        report = {}
        by_tag = {}
        for ms_name, plan in self.get_all_plans_for_project(project_name):
            for act in plan.get("activities", []):
                ex = act["executor"]
                if ex not in report:
                    report[ex] = {"hours": 0.0, "days": 0.0}
                hours = act.get("hours", 0)
                report[ex]["hours"] += hours
                tag = act.get("tag", "")
                if tag not in by_tag:
                    by_tag[tag] = 0.0
                by_tag[tag] += hours
        for ex in report:
            report[ex]["days"] = round(report[ex]["hours"] / 8.0, 2)
        report["by_tag"] = by_tag
        return report

    def get_time_report_by_milestone(self, project_name):
        """按里程碑分组返回工时报告。
        Returns: {milestone_name: {"executors": {executor: {"hours": float, "days": float}}, "planned_hours": float, "finished_actual_hours": float}}
        planned_hours and finished_actual_hours only count finished plans (for overtime/undertime).
        executors includes all activities (for display).
        """
        report = {}
        proj = self.get_project(project_name)
        if not proj:
            return report
        # Build task_id -> effort_days lookup for fallback planned hours
        task_effort_map = {}
        for req in proj.get("requirements", []):
            for task in req.get("tasks", []):
                task_effort_map[task.get("id", "")] = task.get("effort_days", 0)
        for ms in proj.get("milestones", []):
            ms_name = ms["name"]
            if ms_name not in report:
                report[ms_name] = {"executors": {}, "planned_hours": 0.0, "finished_actual_hours": 0.0}
            for plan in ms.get("plans", []):
                # Only accumulate planned hours and actual hours for finished plans
                if plan.get("status") == "finished":
                    p_hours = plan.get("planned_hours", 0)
                    if not p_hours:
                        linked_tid = plan.get("linked_task_id", "")
                        if linked_tid:
                            p_hours = task_effort_map.get(linked_tid, 0) * 8
                    report[ms_name]["planned_hours"] += p_hours
                    report[ms_name]["finished_actual_hours"] += sum(a.get("hours", 0) for a in plan.get("activities", []))
                # All activities count toward executor totals (for display)
                for act in plan.get("activities", []):
                    ex = act["executor"]
                    if ex not in report[ms_name]["executors"]:
                        report[ms_name]["executors"][ex] = {"hours": 0.0, "days": 0.0}
                    report[ms_name]["executors"][ex]["hours"] += act.get("hours", 0)
        for ms_name in report:
            for ex in report[ms_name]["executors"]:
                report[ms_name]["executors"][ex]["days"] = round(report[ms_name]["executors"][ex]["hours"] / 8.0, 2)
        return report

    def get_time_report_by_plan(self, project_name):
        """按计划分组返回工时报告。
        Returns: {plan_content: {"executors": {executor: {"hours": float, "days": float}}, "planned_hours": float, "finished": bool}}
        planned_hours and overtime/undertime only apply to finished plans.
        """
        report = {}
        proj = self.get_project(project_name)
        if not proj:
            return report
        # Build task_id -> effort_days lookup for fallback planned hours
        task_effort_map = {}
        for req in proj.get("requirements", []):
            for task in req.get("tasks", []):
                task_effort_map[task.get("id", "")] = task.get("effort_days", 0)
        for ms in proj.get("milestones", []):
            for plan in ms.get("plans", []):
                plan_content = plan.get("content", "")
                if plan_content not in report:
                    report[plan_content] = {"executors": {}, "planned_hours": 0.0, "finished": True}
                # Accumulate planned hours
                p_hours = plan.get("planned_hours", 0)
                if not p_hours:
                    linked_tid = plan.get("linked_task_id", "")
                    if linked_tid:
                        p_hours = task_effort_map.get(linked_tid, 0) * 8
                report[plan_content]["planned_hours"] += p_hours
                if plan.get("status") != "finished":
                    report[plan_content]["finished"] = False
                for act in plan.get("activities", []):
                    ex = act["executor"]
                    if ex not in report[plan_content]["executors"]:
                        report[plan_content]["executors"][ex] = {"hours": 0.0, "days": 0.0}
                    report[plan_content]["executors"][ex]["hours"] += act.get("hours", 0)
        for plan_content in report:
            for ex in report[plan_content]["executors"]:
                report[plan_content]["executors"][ex]["days"] = round(report[plan_content]["executors"][ex]["hours"] / 8.0, 2)
        return report

    def get_time_report_by_tag(self, project_name):
        """按标签分组返回工时报告。
        Returns: {tag: {executor: {"hours": float, "days": float}}}
        """
        report = {}
        for ms_name, plan in self.get_all_plans_for_project(project_name):
            for act in plan.get("activities", []):
                tag = act.get("tag", "")
                if tag not in report:
                    report[tag] = {}
                ex = act["executor"]
                if ex not in report[tag]:
                    report[tag][ex] = {"hours": 0.0, "days": 0.0}
                report[tag][ex]["hours"] += act.get("hours", 0)
        for tag in report:
            for ex in report[tag]:
                report[tag][ex]["days"] = round(report[tag][ex]["hours"] / 8.0, 2)
        return report

    # ── Deep-copy helper ──────────────────────────────────────────
    @staticmethod
    def _deep_copy_with_new_ids(node):
        """Deep-copy a dict tree, replacing every 'id' field with a new UUID."""
        cloned = copy.deepcopy(node)
        def _regen(obj):
            if isinstance(obj, dict):
                if "id" in obj:
                    obj["id"] = _new_id()
                for v in obj.values():
                    _regen(v)
            elif isinstance(obj, list):
                for item in obj:
                    _regen(item)
        _regen(cloned)
        return cloned

    # ── Duplicate (clone in-place) ────────────────────────────────
    def duplicate_project(self, project_name):
        proj = self.get_project(project_name)
        if not proj:
            return None
        cloned = self._deep_copy_with_new_ids(proj)
        base = project_name + " (Copy)"
        name = base
        i = 2
        while self.get_project(name):
            name = f"{base} {i}"
            i += 1
        cloned["name"] = name
        self.data["projects"].append(cloned)
        proj_dir = os.path.join(self.data_dir, name)
        os.makedirs(proj_dir, exist_ok=True)
        proj_file = os.path.join(proj_dir, "project.json")
        with open(proj_file, "w", encoding="utf-8") as f:
            json.dump(cloned, f, ensure_ascii=False, indent=2)
        return cloned

    def duplicate_requirement(self, project_name, req_id):
        proj = self.get_project(project_name)
        if not proj:
            return None
        req = self.get_requirement(project_name, req_id)
        if not req:
            return None
        cloned = self._deep_copy_with_new_ids(req)
        cloned["subject"] = req["subject"] + " (Copy)"
        proj.setdefault("requirements", []).append(cloned)
        self.save()
        return cloned

    def duplicate_task(self, project_name, req_id, task_id):
        req = self.get_requirement(project_name, req_id)
        if not req:
            return None
        for t in req.get("tasks", []):
            if t["id"] == task_id:
                cloned = self._deep_copy_with_new_ids(t)
                cloned["subject"] = t["subject"] + " (Copy)"
                req["tasks"].append(cloned)
                self.save()
                return cloned
        return None

    def duplicate_milestone(self, project_name, ms_name):
        proj = self.get_project(project_name)
        if not proj:
            return None
        ms = self._find_milestone(project_name, ms_name)
        if not ms:
            return None
        cloned = self._deep_copy_with_new_ids(ms)
        base = ms_name + " (Copy)"
        name = base
        i = 2
        while any(m["name"] == name for m in proj["milestones"]):
            name = f"{base} {i}"
            i += 1
        cloned["name"] = name
        proj["milestones"].append(cloned)
        self.save()
        return cloned

    def duplicate_plan(self, project_name, ms_name, plan_id):
        ms = self._find_milestone(project_name, ms_name)
        if not ms:
            return None
        for p in ms.get("plans", []):
            if p["id"] == plan_id:
                cloned = self._deep_copy_with_new_ids(p)
                cloned["content"] = p["content"] + " (Copy)"
                ms["plans"].append(cloned)
                self.save()
                return cloned
        return None

    def duplicate_activity(self, project_name, ms_name, plan_id, activity_id):
        plan = self._find_plan(project_name, ms_name, plan_id)
        if not plan:
            return None
        for a in plan.get("activities", []):
            if a["id"] == activity_id:
                cloned = self._deep_copy_with_new_ids(a)
                plan["activities"].append(cloned)
                self.save()
                return cloned
        return None

    # ── Copy / Paste (clipboard) ──────────────────────────────────
    # Paste-target compatibility: which node types can be pasted under which parent types
    _PASTE_TARGETS = {
        "project":     None,          # project pastes at root level
        "requirement": "req_analysis", # requirement pastes under req_analysis
        "task":        "requirement",  # task pastes under requirement
        "milestone":   "plan_execution",
        "plan":        "milestone",
        "activity":    "plan",
    }

    def clipboard_copy(self, node_type, project_name, *ids):
        """Copy a node (with children) to the internal clipboard."""
        data = None
        if node_type == "project":
            data = self.get_project(project_name)
        elif node_type == "requirement":
            data = self.get_requirement(project_name, ids[0])
        elif node_type == "task":
            req = self.get_requirement(project_name, ids[0])
            if req:
                data = next((t for t in req.get("tasks", []) if t["id"] == ids[1]), None)
        elif node_type == "milestone":
            data = self._find_milestone(project_name, ids[0])
        elif node_type == "plan":
            data = self._find_plan(project_name, ids[0], ids[1])
        elif node_type == "activity":
            plan = self._find_plan(project_name, ids[0], ids[1])
            if plan:
                data = next((a for a in plan.get("activities", []) if a["id"] == ids[2]), None)
        if data is None:
            return False
        self._clipboard = {"type": node_type, "data": copy.deepcopy(data)}
        return True

    def clipboard_get(self):
        """Return clipboard content or None."""
        return self._clipboard

    def clipboard_paste(self, target_project_name, target_parent_ids=None, after_id=None):
        """Paste clipboard content into the target location.
        target_parent_ids varies by type:
          project     → None
          requirement → None (appends to project requirements)
          task        → (req_id,)
          milestone   → None (appends to project milestones)
          plan        → (ms_name,)
          activity    → (ms_name, plan_id)
        after_id: if provided, insert after the item with this id instead of appending.
        Returns the pasted node or None.
        """
        if not self._clipboard:
            return None
        node_type = self._clipboard["type"]
        is_cut = self._clipboard.get("cut", False)
        if is_cut:
            # For cut, use the data directly (already removed from source)
            cloned = self._deep_copy_with_new_ids(self._clipboard["data"])
        else:
            cloned = self._deep_copy_with_new_ids(self._clipboard["data"])
        target_parent_ids = target_parent_ids or ()

        if node_type == "project":
            base = cloned["name"] + " (Copy)"
            name = base
            i = 2
            while self.get_project(name):
                name = f"{base} {i}"
                i += 1
            cloned["name"] = name
            self.data["projects"].append(cloned)
            self.save()
            return cloned

        proj = self.get_project(target_project_name)
        if not proj:
            return None

        if node_type == "requirement":
            if not is_cut:
                cloned["subject"] = cloned.get("subject", "") + " (Copy)"
            lst = proj.setdefault("requirements", [])
            self._insert_after(lst, cloned, after_id, "id")
        elif node_type == "task":
            req = self.get_requirement(target_project_name, target_parent_ids[0])
            if not req:
                return None
            if not is_cut:
                cloned["subject"] = cloned.get("subject", "") + " (Copy)"
            lst = req.setdefault("tasks", [])
            self._insert_after(lst, cloned, after_id, "id")
        elif node_type == "milestone":
            if not is_cut:
                base = cloned["name"] + " (Copy)"
                name = base
                i = 2
                while any(m["name"] == name for m in proj.get("milestones", [])):
                    name = f"{base} {i}"
                    i += 1
                cloned["name"] = name
            lst = proj.setdefault("milestones", [])
            self._insert_after(lst, cloned, after_id, "name")
        elif node_type == "plan":
            ms = self._find_milestone(target_project_name, target_parent_ids[0])
            if not ms:
                return None
            if not is_cut:
                cloned["content"] = cloned.get("content", "") + " (Copy)"
            lst = ms.setdefault("plans", [])
            self._insert_after(lst, cloned, after_id, "id")
        elif node_type == "activity":
            plan = self._find_plan(target_project_name, target_parent_ids[0], target_parent_ids[1])
            if not plan:
                return None
            lst = plan.setdefault("activities", [])
            self._insert_after(lst, cloned, after_id, "id")
        else:
            return None
        # Clear cut flag after paste
        if is_cut:
            self._clipboard["cut"] = False
        self.save()
        return cloned

    def _insert_after(self, lst, item, after_id, key_field):
        """Insert item into lst after the element whose key_field matches after_id.
        If after_id is None or not found, append to end."""
        if after_id is None:
            lst.append(item)
            return
        for i, existing in enumerate(lst):
            if existing.get(key_field) == after_id:
                lst.insert(i + 1, item)
                return
        lst.append(item)
