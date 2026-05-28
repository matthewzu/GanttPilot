#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GanttPilot MCP Server - 通过 Model Context Protocol 暴露项目管理功能

Usage:
    python ganttpilot_mcp.py [--data-dir PATH]

MCP config example (.kiro/settings/mcp.json):
    {
        "mcpServers": {
            "ganttpilot": {
                "command": "python",
                "args": ["path/to/ganttpilot_mcp.py"],
                "autoApprove": ["list_projects", "get_project", "get_tracking"]
            }
        }
    }
"""

from __future__ import annotations

import os
import sys

# Ensure the GanttPilot directory is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP
from ganttpilot_core import DataStore

# ── Initialize ───────────────────────────────────────────────
DATA_DIR = os.environ.get(
    "GANTTPILOT_DATA_DIR",
    os.path.join(os.path.expanduser("~"), ".ganttpilot", "data"),
)

mcp = FastMCP("GanttPilot", instructions="GanttPilot 项目管理 MCP Server，提供项目、需求、计划、活动的增删改查。")
store = DataStore(DATA_DIR)


def _reload():
    """Reload data from disk to pick up external changes."""
    store.load()


# ── Project tools ────────────────────────────────────────────

@mcp.tool()
def list_projects() -> list[dict]:
    """列出所有项目（名称、描述、标签）"""
    _reload()
    return [
        {"name": p["name"], "description": p.get("description", ""), "tags": p.get("tags", [])}
        for p in store.list_projects()
    ]


@mcp.tool()
def get_project(project_name: str) -> dict | None:
    """获取项目详情（包含需求、里程碑完整结构）"""
    _reload()
    proj = store.get_project(project_name)
    if not proj:
        return {"error": f"项目 '{project_name}' 不存在"}
    # Return a clean copy without sensitive fields
    return {
        "name": proj["name"],
        "description": proj.get("description", ""),
        "tags": proj.get("tags", []),
        "requirements": proj.get("requirements", []),
        "milestones": proj.get("milestones", []),
    }


@mcp.tool()
def add_project(name: str, description: str = "", tags: str = "") -> dict:
    """创建新项目。tags 用逗号分隔，如 '前端,后端,测试'"""
    _reload()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    result = store.add_project(name, description=description, tags=tag_list)
    if result is None:
        return {"error": f"项目 '{name}' 已存在"}
    store.save()
    return {"status": "ok", "name": name}


@mcp.tool()
def delete_project(project_name: str) -> dict:
    """删除项目"""
    _reload()
    if store.delete_project(project_name):
        return {"status": "ok"}
    return {"error": f"项目 '{project_name}' 不存在"}


# ── Requirement tools ────────────────────────────────────────

@mcp.tool()
def list_requirements(project_name: str) -> list[dict]:
    """列出项目的所有需求"""
    _reload()
    return store.list_requirements(project_name)


@mcp.tool()
def add_requirement(project_name: str, category: str, subject: str, description: str = "") -> dict:
    """添加需求"""
    _reload()
    result = store.add_requirement(project_name, category, subject, description)
    if result is None:
        return {"error": f"项目 '{project_name}' 不存在"}
    return {"status": "ok", "id": result["id"], "subject": subject}


@mcp.tool()
def update_requirement(project_name: str, req_id: str, category: str, subject: str, description: str = "") -> dict:
    """更新需求"""
    _reload()
    if store.update_requirement(project_name, req_id, category, subject, description):
        return {"status": "ok"}
    return {"error": "需求不存在"}


@mcp.tool()
def delete_requirement(project_name: str, req_id: str) -> dict:
    """删除需求"""
    _reload()
    if store.delete_requirement(project_name, req_id):
        return {"status": "ok"}
    return {"error": "需求不存在"}


# ── Task tools ───────────────────────────────────────────────

@mcp.tool()
def list_tasks(project_name: str, req_id: str) -> list[dict]:
    """列出需求下的所有任务"""
    _reload()
    return store.list_tasks(project_name, req_id)


@mcp.tool()
def add_task(project_name: str, req_id: str, subject: str, effort_days: float = 0, description: str = "") -> dict:
    """添加任务到需求下"""
    _reload()
    result = store.add_task(project_name, req_id, subject, effort_days, description)
    if result is None:
        return {"error": "需求不存在"}
    return {"status": "ok", "id": result["id"], "subject": subject}


@mcp.tool()
def update_task(project_name: str, req_id: str, task_id: str, subject: str, effort_days: float = 0, description: str = "") -> dict:
    """更新任务"""
    _reload()
    if store.update_task(project_name, req_id, task_id, subject, effort_days, description):
        return {"status": "ok"}
    return {"error": "任务不存在"}


@mcp.tool()
def delete_task(project_name: str, req_id: str, task_id: str) -> dict:
    """删除任务"""
    _reload()
    if store.delete_task(project_name, req_id, task_id):
        return {"status": "ok"}
    return {"error": "任务不存在"}


# ── Milestone tools ──────────────────────────────────────────

@mcp.tool()
def list_milestones(project_name: str) -> list[dict]:
    """列出项目的所有里程碑"""
    _reload()
    return store.list_milestones(project_name)


@mcp.tool()
def add_milestone(project_name: str, milestone_name: str, description: str = "", deadline: str = "") -> dict:
    """添加里程碑。deadline 格式 YYYYMMDD"""
    _reload()
    result = store.add_milestone(project_name, milestone_name, description=description, deadline=deadline)
    if result is None:
        return {"error": f"里程碑 '{milestone_name}' 已存在或项目不存在"}
    return {"status": "ok", "name": milestone_name}


@mcp.tool()
def delete_milestone(project_name: str, milestone_name: str) -> dict:
    """删除里程碑"""
    _reload()
    if store.delete_milestone(project_name, milestone_name):
        return {"status": "ok"}
    return {"error": "里程碑不存在"}


# ── Plan tools ───────────────────────────────────────────────

@mcp.tool()
def list_plans(project_name: str, milestone_name: str) -> list[dict]:
    """列出里程碑下的所有计划"""
    _reload()
    return store.list_plans(project_name, milestone_name)


@mcp.tool()
def add_plan(
    project_name: str,
    milestone_name: str,
    content: str,
    executor: str,
    start_date: str,
    end_date: str,
    linked_task_id: str = "",
) -> dict:
    """添加计划。日期格式 YYYYMMDD。linked_task_id 可关联任务。"""
    _reload()
    result = store.add_plan(
        project_name, milestone_name, content, executor,
        start_date, end_date, linked_task_id=linked_task_id,
    )
    if result is None:
        return {"error": "里程碑不存在"}
    return {"status": "ok", "id": result["id"], "content": content}


@mcp.tool()
def finish_plan(project_name: str, milestone_name: str, plan_id: str) -> dict:
    """完结计划（标记为已完成）"""
    _reload()
    if store.finish_plan(project_name, milestone_name, plan_id):
        return {"status": "ok"}
    return {"error": "计划不存在"}


@mcp.tool()
def reopen_plan(project_name: str, milestone_name: str, plan_id: str) -> dict:
    """重开计划"""
    _reload()
    if store.reopen_plan(project_name, milestone_name, plan_id):
        return {"status": "ok"}
    return {"error": "计划不存在"}


@mcp.tool()
def set_plan_progress(project_name: str, milestone_name: str, plan_id: str, progress: int) -> dict:
    """设置计划进度（0-100）"""
    _reload()
    if store.set_plan_progress(project_name, milestone_name, plan_id, progress):
        return {"status": "ok"}
    return {"error": "计划不存在"}


@mcp.tool()
def delete_plan(project_name: str, milestone_name: str, plan_id: str) -> dict:
    """删除计划"""
    _reload()
    if store.delete_plan(project_name, milestone_name, plan_id):
        return {"status": "ok"}
    return {"error": "计划不存在"}


# ── Activity tools ───────────────────────────────────────────

@mcp.tool()
def add_activity(
    project_name: str,
    milestone_name: str,
    plan_id: str,
    executor: str,
    date: str,
    hours: float,
    content: str,
    tag: str = "",
    description: str = "",
) -> dict:
    """添加活动（工时记录）。date 格式 YYYYMMDD。"""
    _reload()
    result = store.add_activity(
        project_name, milestone_name, plan_id,
        executor, date, hours, content, tag=tag, description=description,
    )
    if result is None:
        return {"error": "计划不存在"}
    return {"status": "ok", "id": result["id"]}


@mcp.tool()
def delete_activity(project_name: str, milestone_name: str, plan_id: str, activity_id: str) -> dict:
    """删除活动"""
    _reload()
    if store.delete_activity(project_name, milestone_name, plan_id, activity_id):
        return {"status": "ok"}
    return {"error": "活动不存在"}


# ── Report / Tracking tools ──────────────────────────────────

@mcp.tool()
def get_time_report(project_name: str) -> dict:
    """获取项目工时统计报告（按执行者汇总）"""
    _reload()
    return store.get_time_report(project_name)


@mcp.tool()
def get_tracking(project_name: str) -> list[dict]:
    """获取需求跟踪数据（需求→任务→关联计划→进度→差异）"""
    _reload()
    from ganttpilot_gui import build_tracking_data
    proj = store.get_project(project_name)
    if not proj:
        return [{"error": f"项目 '{project_name}' 不存在"}]
    return build_tracking_data(proj)


# ── Entry point ──────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GanttPilot MCP Server")
    parser.add_argument("--data-dir", default=None, help="Data directory path")
    args = parser.parse_args()
    if args.data_dir:
        store.data_dir = args.data_dir
        store.load()
    mcp.run()
