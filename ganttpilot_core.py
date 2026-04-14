#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GanttPilot - Core Data Model & Business Logic / 核心数据模型与业务逻辑

Data is stored as JSON files in the data directory:
  data_dir/
    {project_name}/
      project.json   — single project object with milestones, plans, activities
"""

import json
import os
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


class DataStore:
    """Manages project data with per-project directory storage.

    Each project is stored in data_dir/{project_name}/project.json.
    Internally maintains self.data = {"projects": [...]} as a unified view.
    """

    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.data = {"projects": []}
        self.load()

    def load(self):
        os.makedirs(self.data_dir, exist_ok=True)

        # ── Migration: old projects.json → per-project directories (Task 1.4) ──
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

        # ── Load from per-project subdirectories (Task 1.1) ──
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
                    with open(proj_file, "r", encoding="utf-8") as f:
                        proj = json.load(f)
                    # Fill missing project-level defaults
                    if "description" not in proj:
                        proj["description"] = ""
                    # Fill missing progress/actual_end_date defaults for each plan
                    for ms in proj.get("milestones", []):
                        for plan in ms.get("plans", []):
                            if "progress" not in plan:
                                plan["progress"] = 0
                            if "actual_end_date" not in plan:
                                plan["actual_end_date"] = ""
                            if "planned_hours" not in plan:
                                plan["planned_hours"] = 0
                            # Auto-fix finished plans with progress=0
                            if plan.get("status") == "finished" and plan["progress"] == 0:
                                plan["progress"] = 100
                    projects.append(proj)
                except (json.JSONDecodeError, IOError) as e:
                    warnings.warn(f"Skipping project in '{entry}': {e}")
        self.data = {"projects": projects}

    def save(self):
        os.makedirs(self.data_dir, exist_ok=True)
        for proj in self.data.get("projects", []):
            proj_dir = os.path.join(self.data_dir, proj["name"])
            os.makedirs(proj_dir, exist_ok=True)
            proj_file = os.path.join(proj_dir, "project.json")
            with open(proj_file, "w", encoding="utf-8") as f:
                json.dump(proj, f, ensure_ascii=False, indent=2)

    # ── Project ──────────────────────────────────────────────
    def list_projects(self):
        return self.data.get("projects", [])

    def get_project(self, name):
        for p in self.data["projects"]:
            if p["name"] == name:
                return p
        return None

    def add_project(self, name, remote_url="", remote_username="", remote_password="", description=""):
        if self.get_project(name):
            return None
        proj = {
            "id": _new_id(),
            "name": name,
            "description": description,
            "remote_url": remote_url,
            "remote_username": remote_username,
            "remote_password": remote_password,
            "milestones": [],
        }
        self.data["projects"].append(proj)
        # Create project subdirectory and write project.json
        proj_dir = os.path.join(self.data_dir, name)
        os.makedirs(proj_dir, exist_ok=True)
        proj_file = os.path.join(proj_dir, "project.json")
        with open(proj_file, "w", encoding="utf-8") as f:
            json.dump(proj, f, ensure_ascii=False, indent=2)
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

    # ── Plan ─────────────────────────────────────────────────
    def list_plans(self, project_name, milestone_name):
        ms = self._find_milestone(project_name, milestone_name)
        return ms["plans"] if ms else []

    def add_plan(self, project_name, milestone_name, content, executor,
                 start_date, end_date, skip_non_workdays=True, skip_dates=None, color=""):
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
                     executor, date, hours, content):
        plan = self._find_plan(project_name, milestone_name, plan_id)
        if not plan:
            return None
        activity = {
            "id": _new_id(),
            "executor": executor,
            "date": date,
            "hours": hours,
            "content": content,
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
                        activity_id, executor, date, hours, content):
        """Update activity attributes and persist."""
        plan = self._find_plan(project_name, milestone_name, plan_id)
        if not plan:
            return False
        for act in plan["activities"]:
            if act["id"] == activity_id:
                act["executor"] = executor
                act["date"] = date
                act["hours"] = hours
                act["content"] = content
                self.save()
                return True
        return False

    # ── Query helpers ────────────────────────────────────────
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
        """Returns {executor: {"hours": float, "days": float}} for a project"""
        report = {}
        for ms_name, plan in self.get_all_plans_for_project(project_name):
            for act in plan.get("activities", []):
                ex = act["executor"]
                if ex not in report:
                    report[ex] = {"hours": 0.0, "days": 0.0}
                report[ex]["hours"] += act.get("hours", 0)
        for ex in report:
            report[ex]["days"] = round(report[ex]["hours"] / 8.0, 2)
        return report
