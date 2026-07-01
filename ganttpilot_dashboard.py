#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GanttPilot - Dashboard Data Aggregation / 仪表盘数据聚合

Pure functions for computing dashboard summary data from project dictionaries.
No GUI dependencies — all functions are independently testable.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MilestoneCard:
    """里程碑概览卡片数据。"""
    name: str
    deadline: str               # YYYYMMDD or ""
    total_plans: int
    finished_plans: int
    completion_rate: float      # 0.0 ~ 1.0
    is_completed: bool          # 所有计划均为 finished 且至少有一个计划
    is_overdue: bool            # 超过 deadline 且有未完结计划


@dataclass
class ProgressSummary:
    """项目进度汇总数据。"""
    total_plans: int
    finished_plans: int
    active_plans: int
    overall_completion_rate: float  # 0.0 ~ 1.0


@dataclass
class HourStats:
    """工时统计数据。"""
    total_planned_hours: float
    total_actual_hours: float
    variance: float                 # actual - planned（所有计划）
    finished_planned_hours: float
    finished_actual_hours: float


@dataclass
class ExecutorEntry:
    """执行者工作量条目。"""
    executor: str
    actual_hours: float
    percentage: float               # 占总实际工时的比例 0.0 ~ 1.0


@dataclass
class DashboardData:
    """仪表盘聚合数据。"""
    milestone_cards: list = field(default_factory=list)
    progress_summary: ProgressSummary = None
    hour_stats: HourStats = None
    executor_distribution: list = field(default_factory=list)


def compute_plan_actual_hours(plan):
    """计算单个计划的实际工时（所有活动 hours 之和）。

    Args:
        plan: 计划字典，包含 activities 列表

    Returns:
        float: 实际工时总和，异常数据视为 0
    """
    total = 0.0
    try:
        activities = plan.get("activities", [])
        if not isinstance(activities, list):
            return 0.0
        for activity in activities:
            if not isinstance(activity, dict):
                continue
            try:
                hours = float(activity.get("hours", 0))
                total += hours
            except (TypeError, ValueError):
                continue
    except (AttributeError, TypeError):
        return 0.0
    return total


def compute_plan_planned_hours(plan, task_effort_map):
    """计算单个计划的计划工时。

    优先使用 plan["planned_hours"]；若为 0 且有 linked_task_id，
    回退到对应任务的 effort_days × 8。

    Args:
        plan: 计划字典
        task_effort_map: {task_id: effort_days} 映射

    Returns:
        float: 计划工时，异常数据视为 0
    """
    try:
        planned = float(plan.get("planned_hours", 0))
    except (TypeError, ValueError, AttributeError):
        planned = 0.0

    if planned != 0.0:
        return planned

    # 回退：尝试通过 linked_task_id 获取 effort_days × 8
    try:
        linked_task_id = plan.get("linked_task_id", "")
        if linked_task_id and isinstance(task_effort_map, dict):
            effort_days = task_effort_map.get(linked_task_id, 0)
            return float(effort_days) * 8.0
    except (TypeError, ValueError, AttributeError):
        pass

    return 0.0


def _build_task_effort_map(project):
    """从项目字典构建 {task_id: effort_days} 映射。

    Args:
        project: 项目字典

    Returns:
        dict: task_id -> effort_days
    """
    task_map = {}
    try:
        requirements = project.get("requirements", [])
        if not isinstance(requirements, list):
            return task_map
        for req in requirements:
            if not isinstance(req, dict):
                continue
            tasks = req.get("tasks", [])
            if not isinstance(tasks, list):
                continue
            for task in tasks:
                if not isinstance(task, dict):
                    continue
                task_id = task.get("id", "")
                if task_id:
                    try:
                        task_map[task_id] = float(task.get("effort_days", 0))
                    except (TypeError, ValueError):
                        task_map[task_id] = 0.0
    except (AttributeError, TypeError):
        pass
    return task_map


def _is_valid_deadline_past(deadline_str):
    """判断 deadline 是否为有效日期且早于今天。

    Args:
        deadline_str: YYYYMMDD 格式的字符串

    Returns:
        bool: 是否逾期
    """
    if not deadline_str or not isinstance(deadline_str, str):
        return False
    try:
        deadline_date = datetime.strptime(deadline_str.strip(), "%Y%m%d").date()
        return deadline_date < datetime.now().date()
    except (ValueError, TypeError):
        return False


def aggregate_dashboard(project):
    """从项目字典计算仪表盘聚合数据。纯函数，无副作用。

    Args:
        project: 项目字典（来自 DataStore.get_project）

    Returns:
        DashboardData: 仪表盘聚合数据
    """
    if not project or not isinstance(project, dict):
        return DashboardData(
            milestone_cards=[],
            progress_summary=ProgressSummary(
                total_plans=0, finished_plans=0,
                active_plans=0, overall_completion_rate=0.0
            ),
            hour_stats=HourStats(
                total_planned_hours=0.0, total_actual_hours=0.0,
                variance=0.0, finished_planned_hours=0.0,
                finished_actual_hours=0.0
            ),
            executor_distribution=[],
        )

    task_effort_map = _build_task_effort_map(project)

    milestones = project.get("milestones", [])
    if not isinstance(milestones, list):
        milestones = []

    # Collect all plans across all milestones
    all_plans = []
    milestone_cards = []

    for ms in milestones:
        if not isinstance(ms, dict):
            continue
        ms_name = ms.get("name", "")
        ms_deadline = ms.get("deadline", "")
        plans = ms.get("plans", [])
        if not isinstance(plans, list):
            plans = []

        total_plans = len(plans)
        finished_plans = 0
        for plan in plans:
            if not isinstance(plan, dict):
                continue
            if plan.get("status") == "finished":
                finished_plans += 1

        # Milestone completion rate
        if total_plans > 0:
            completion_rate = finished_plans / total_plans
        else:
            completion_rate = 0.0

        # is_completed: all plans finished AND at least one plan exists
        is_completed = (total_plans > 0 and finished_plans == total_plans)

        # is_overdue: deadline non-empty, deadline < today, AND at least one plan not finished
        has_unfinished = (finished_plans < total_plans) and (total_plans > 0)
        is_overdue = (has_unfinished and _is_valid_deadline_past(ms_deadline))

        milestone_cards.append(MilestoneCard(
            name=ms_name,
            deadline=ms_deadline if isinstance(ms_deadline, str) else "",
            total_plans=total_plans,
            finished_plans=finished_plans,
            completion_rate=completion_rate,
            is_completed=is_completed,
            is_overdue=is_overdue,
        ))

        all_plans.extend(p for p in plans if isinstance(p, dict))

    # Progress summary
    total_plans_count = len(all_plans)
    finished_count = sum(1 for p in all_plans if p.get("status") == "finished")
    active_count = total_plans_count - finished_count

    if total_plans_count > 0:
        progress_sum = 0.0
        for p in all_plans:
            try:
                progress_sum += float(p.get("progress", 0))
            except (TypeError, ValueError):
                pass
        overall_completion_rate = progress_sum / (total_plans_count * 100.0)
    else:
        overall_completion_rate = 0.0

    progress_summary = ProgressSummary(
        total_plans=total_plans_count,
        finished_plans=finished_count,
        active_plans=active_count,
        overall_completion_rate=overall_completion_rate,
    )

    # Hour stats - includes ALL plans (active + finished)
    total_planned_hours = 0.0
    total_actual_hours = 0.0
    finished_planned_hours = 0.0
    finished_actual_hours = 0.0

    for plan in all_plans:
        plan_actual = compute_plan_actual_hours(plan)
        plan_planned = compute_plan_planned_hours(plan, task_effort_map)
        total_actual_hours += plan_actual
        total_planned_hours += plan_planned
        if plan.get("status") == "finished":
            finished_actual_hours += plan_actual
            finished_planned_hours += plan_planned

    variance = total_actual_hours - total_planned_hours

    hour_stats = HourStats(
        total_planned_hours=total_planned_hours,
        total_actual_hours=total_actual_hours,
        variance=variance,
        finished_planned_hours=finished_planned_hours,
        finished_actual_hours=finished_actual_hours,
    )

    # Executor distribution - group by activity executor field
    executor_hours = {}  # executor_name -> total_hours

    for plan in all_plans:
        plan_executor = plan.get("executor", "") or ""
        # For multi-executor plans, use first as fallback for activities without executor
        plan_executor_primary = plan_executor.split(",")[0].strip() if "," in plan_executor else plan_executor
        activities = plan.get("activities", [])
        if not isinstance(activities, list):
            continue
        for activity in activities:
            if not isinstance(activity, dict):
                continue
            try:
                hours = float(activity.get("hours", 0))
            except (TypeError, ValueError):
                hours = 0.0

            # Determine executor: activity executor > plan executor > "未指定"
            act_executor = activity.get("executor", "") or ""
            if act_executor:
                executor_name = act_executor
            elif plan_executor_primary:
                executor_name = plan_executor_primary
            else:
                executor_name = "未指定"

            executor_hours[executor_name] = executor_hours.get(executor_name, 0.0) + hours

    # Build executor entries sorted by hours descending
    executor_distribution = []
    for executor_name, hours in sorted(
        executor_hours.items(), key=lambda x: x[1], reverse=True
    ):
        if total_actual_hours > 0:
            percentage = hours / total_actual_hours
        else:
            percentage = 0.0
        executor_distribution.append(ExecutorEntry(
            executor=executor_name,
            actual_hours=hours,
            percentage=percentage,
        ))

    return DashboardData(
        milestone_cards=milestone_cards,
        progress_summary=progress_summary,
        hour_stats=hour_stats,
        executor_distribution=executor_distribution,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# DashboardTab UI Class
# ═══════════════════════════════════════════════════════════════════════════════

import tkinter as tk
from tkinter import ttk

try:
    from ganttpilot_ctk import get_appearance_mode
except ImportError:
    def get_appearance_mode():
        return "light"

try:
    from ganttpilot_i18n import t
except ImportError:
    def t(key, lang="zh"):
        return key


def _get_dashboard_colors():
    """Return dashboard color scheme based on current appearance mode."""
    if get_appearance_mode() == "dark":
        return {
            "bg": "#1A1A2E",
            "card_bg": "#2D3748",
            "card_fg": "#E2E8F0",
            "section_fg": "#CBD5E0",
            "progress_bg": "#4A5568",
            "progress_fill": "#48BB78",
            "overdue_fg": "#FC8181",
            "completed_fg": "#68D391",
            "variance_positive": "#FC8181",
            "variance_negative": "#68D391",
            "muted_fg": "#A0AEC0",
            "border": "#4A5568",
        }
    return {
        "bg": "#FAFAFA",
        "card_bg": "#FFFFFF",
        "card_fg": "#2D3748",
        "section_fg": "#4A5568",
        "progress_bg": "#E2E8F0",
        "progress_fill": "#48BB78",
        "overdue_fg": "#E53E3E",
        "completed_fg": "#38A169",
        "variance_positive": "#E53E3E",
        "variance_negative": "#38A169",
        "muted_fg": "#718096",
        "border": "#E2E8F0",
    }


class DashboardTab:
    """仪表盘标签页 UI 控制器。"""

    def __init__(self, parent_frame, get_project_fn, get_lang_fn):
        """
        Args:
            parent_frame: ttk.Frame (tab in right_notebook)
            get_project_fn: callable returning current project dict or None
            get_lang_fn: callable returning "zh" or "en"
        """
        self.parent_frame = parent_frame
        self.get_project_fn = get_project_fn
        self.get_lang_fn = get_lang_fn

        # Scrollable canvas setup
        self.canvas = tk.Canvas(parent_frame, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(
            parent_frame, orient=tk.VERTICAL, command=self.canvas.yview
        )
        self.scroll_frame = tk.Frame(self.canvas)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.scroll_frame, anchor="nw"
        )

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Resize canvas window width to match canvas
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        # Mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel, add="+")

    def _on_canvas_resize(self, event):
        """Resize the inner frame to match canvas width."""
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        # Only scroll if mouse is over this canvas
        try:
            widget = event.widget
            while widget:
                if widget == self.canvas:
                    self.canvas.yview_scroll(
                        int(-1 * (event.delta / 120)), "units"
                    )
                    break
                widget = widget.master
        except (AttributeError, tk.TclError):
            pass

    def _t(self, key):
        """Get translated text."""
        return t(key, self.get_lang_fn())

    def refresh(self):
        """Recalculate and refresh dashboard display."""
        # Clear old content
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        colors = _get_dashboard_colors()
        self.canvas.configure(bg=colors["bg"])
        self.scroll_frame.configure(bg=colors["bg"])

        project = self.get_project_fn()
        if project is None:
            self._render_empty_state(colors)
            return

        data = aggregate_dashboard(project)

        # Render sections
        self._render_progress_summary(data.progress_summary, colors)
        self._render_milestone_cards(data.milestone_cards, colors)
        self._render_hour_stats(data.hour_stats, colors)
        self._render_executor_distribution(data.executor_distribution, colors)

    def _render_empty_state(self, colors):
        """Show empty state message when no project is selected."""
        tk.Label(
            self.scroll_frame,
            text=self._t("dashboard_no_project"),
            font=("", 14),
            fg=colors["muted_fg"],
            bg=colors["bg"],
        ).pack(expand=True, fill=tk.BOTH, pady=80)

    def _render_section_title(self, text, colors):
        """Render a section title label."""
        frame = tk.Frame(self.scroll_frame, bg=colors["bg"])
        frame.pack(fill=tk.X, padx=16, pady=(16, 4))
        tk.Label(
            frame,
            text=text,
            font=("", 12, "bold"),
            fg=colors["section_fg"],
            bg=colors["bg"],
            anchor="w",
        ).pack(fill=tk.X)
        return frame

    def _render_progress_summary(self, summary, colors):
        """Render progress summary section with progress bar."""
        self._render_section_title(self._t("dashboard_progress_summary"), colors)

        card = tk.Frame(
            self.scroll_frame, bg=colors["card_bg"],
            highlightbackground=colors["border"], highlightthickness=1
        )
        card.pack(fill=tk.X, padx=16, pady=4)

        # Stats row
        stats_frame = tk.Frame(card, bg=colors["card_bg"])
        stats_frame.pack(fill=tk.X, padx=12, pady=(10, 4))

        stats = [
            (self._t("dashboard_total_plans"), str(summary.total_plans)),
            (self._t("dashboard_finished_plans"), str(summary.finished_plans)),
            (self._t("dashboard_active_plans"), str(summary.active_plans)),
            (self._t("dashboard_overall_rate"),
             f"{summary.overall_completion_rate * 100:.0f}%"),
        ]
        for i, (label, value) in enumerate(stats):
            col_frame = tk.Frame(stats_frame, bg=colors["card_bg"])
            col_frame.pack(side=tk.LEFT, expand=True, fill=tk.X)
            tk.Label(
                col_frame, text=label,
                font=("", 9), fg=colors["muted_fg"], bg=colors["card_bg"],
            ).pack(anchor="w")
            tk.Label(
                col_frame, text=value,
                font=("", 14, "bold"), fg=colors["card_fg"],
                bg=colors["card_bg"],
            ).pack(anchor="w")

        # Progress bar (Canvas-based)
        bar_frame = tk.Frame(card, bg=colors["card_bg"])
        bar_frame.pack(fill=tk.X, padx=12, pady=(4, 10))

        bar_canvas = tk.Canvas(
            bar_frame, height=16, bg=colors["card_bg"], highlightthickness=0
        )
        bar_canvas.pack(fill=tk.X)
        bar_canvas.update_idletasks()

        bar_canvas.bind("<Configure>", lambda e: self._draw_progress_bar(
            bar_canvas, summary.overall_completion_rate, colors
        ))

    def _draw_progress_bar(self, canvas, rate, colors):
        """Draw a rounded progress bar on a canvas."""
        canvas.delete("all")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w <= 1:
            return

        r = h // 2  # corner radius
        # Background
        canvas.create_rectangle(0, 0, w, h, fill=colors["progress_bg"], outline="")
        # Fill
        fill_w = max(0, int(w * min(rate, 1.0)))
        if fill_w > 0:
            canvas.create_rectangle(
                0, 0, fill_w, h, fill=colors["progress_fill"], outline=""
            )

    def _render_milestone_cards(self, cards, colors):
        """Render milestone overview cards."""
        self._render_section_title(self._t("dashboard_milestone_overview"), colors)

        if not cards:
            empty_frame = tk.Frame(self.scroll_frame, bg=colors["bg"])
            empty_frame.pack(fill=tk.X, padx=16, pady=4)
            tk.Label(
                empty_frame,
                text=self._t("dashboard_no_milestones"),
                font=("", 10),
                fg=colors["muted_fg"],
                bg=colors["bg"],
            ).pack(anchor="w")
            return

        # Grid container for cards (3 per row)
        grid_frame = tk.Frame(self.scroll_frame, bg=colors["bg"])
        grid_frame.pack(fill=tk.X, padx=16, pady=4)

        cols = 3
        for i, card_data in enumerate(cards):
            row = i // cols
            col = i % cols
            self._render_single_milestone_card(
                grid_frame, card_data, row, col, colors
            )

        # Configure grid columns to be equal
        for c in range(cols):
            grid_frame.columnconfigure(c, weight=1, uniform="milestone")

    def _render_single_milestone_card(self, parent, card_data, row, col, colors):
        """Render a single milestone card in the grid."""
        # Determine border color based on status
        if card_data.is_completed:
            border_color = colors["completed_fg"]
        elif card_data.is_overdue:
            border_color = colors["overdue_fg"]
        else:
            border_color = colors["border"]

        card = tk.Frame(
            parent, bg=colors["card_bg"],
            highlightbackground=border_color, highlightthickness=2,
        )
        card.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")

        # Name
        tk.Label(
            card, text=card_data.name,
            font=("", 10, "bold"), fg=colors["card_fg"],
            bg=colors["card_bg"], anchor="w",
        ).pack(fill=tk.X, padx=8, pady=(8, 2))

        # Status badge
        if card_data.is_completed:
            badge_text = self._t("dashboard_completed")
            badge_fg = colors["completed_fg"]
        elif card_data.is_overdue:
            badge_text = self._t("dashboard_overdue")
            badge_fg = colors["overdue_fg"]
        else:
            badge_text = f"{card_data.finished_plans}/{card_data.total_plans}"
            badge_fg = colors["card_fg"]

        tk.Label(
            card, text=badge_text,
            font=("", 9), fg=badge_fg, bg=colors["card_bg"], anchor="w",
        ).pack(fill=tk.X, padx=8, pady=0)

        # Completion rate
        rate_text = f"{card_data.completion_rate * 100:.0f}%"
        tk.Label(
            card, text=rate_text,
            font=("", 12, "bold"), fg=colors["card_fg"],
            bg=colors["card_bg"], anchor="w",
        ).pack(fill=tk.X, padx=8, pady=0)

        # Deadline (if exists)
        if card_data.deadline:
            try:
                d = datetime.strptime(card_data.deadline, "%Y%m%d")
                deadline_display = f"{self._t('dashboard_deadline')}: {d.strftime('%Y-%m-%d')}"
            except (ValueError, TypeError):
                deadline_display = ""
            if deadline_display:
                tk.Label(
                    card, text=deadline_display,
                    font=("", 8), fg=colors["muted_fg"],
                    bg=colors["card_bg"], anchor="w",
                ).pack(fill=tk.X, padx=8, pady=(0, 8))
        else:
            # Bottom padding
            tk.Frame(card, height=8, bg=colors["card_bg"]).pack()

    def _render_hour_stats(self, stats, colors):
        """Render hour statistics section."""
        self._render_section_title(self._t("dashboard_hour_stats"), colors)

        card = tk.Frame(
            self.scroll_frame, bg=colors["card_bg"],
            highlightbackground=colors["border"], highlightthickness=1
        )
        card.pack(fill=tk.X, padx=16, pady=4)

        inner = tk.Frame(card, bg=colors["card_bg"])
        inner.pack(fill=tk.X, padx=12, pady=10)

        # Row 1: Planned and Actual
        row1 = tk.Frame(inner, bg=colors["card_bg"])
        row1.pack(fill=tk.X, pady=2)

        tk.Label(
            row1, text=f"{self._t('dashboard_planned_hours')}: ",
            font=("", 10), fg=colors["muted_fg"], bg=colors["card_bg"],
        ).pack(side=tk.LEFT)
        tk.Label(
            row1, text=f"{stats.total_planned_hours:.1f}h",
            font=("", 10, "bold"), fg=colors["card_fg"], bg=colors["card_bg"],
        ).pack(side=tk.LEFT)

        tk.Label(
            row1, text=f"    {self._t('dashboard_actual_hours')}: ",
            font=("", 10), fg=colors["muted_fg"], bg=colors["card_bg"],
        ).pack(side=tk.LEFT)
        tk.Label(
            row1, text=f"{stats.total_actual_hours:.1f}h",
            font=("", 10, "bold"), fg=colors["card_fg"], bg=colors["card_bg"],
        ).pack(side=tk.LEFT)

        # Row 2: Variance
        row2 = tk.Frame(inner, bg=colors["card_bg"])
        row2.pack(fill=tk.X, pady=2)

        tk.Label(
            row2, text=f"{self._t('dashboard_variance')}: ",
            font=("", 10), fg=colors["muted_fg"], bg=colors["card_bg"],
        ).pack(side=tk.LEFT)

        if stats.variance > 0:
            var_text = f"+{stats.variance:.1f}h ({self._t('dashboard_over')})"
            var_color = colors["variance_positive"]
        elif stats.variance < 0:
            var_text = f"{stats.variance:.1f}h ({self._t('dashboard_under')})"
            var_color = colors["variance_negative"]
        else:
            var_text = "0.0h"
            var_color = colors["card_fg"]

        tk.Label(
            row2, text=var_text,
            font=("", 10, "bold"), fg=var_color, bg=colors["card_bg"],
        ).pack(side=tk.LEFT)

    def _render_executor_distribution(self, entries, colors):
        """Render executor distribution section."""
        self._render_section_title(self._t("dashboard_executor_dist"), colors)

        if not entries:
            empty_frame = tk.Frame(self.scroll_frame, bg=colors["bg"])
            empty_frame.pack(fill=tk.X, padx=16, pady=4)
            tk.Label(
                empty_frame,
                text=self._t("dashboard_no_hours_data"),
                font=("", 10),
                fg=colors["muted_fg"],
                bg=colors["bg"],
            ).pack(anchor="w")
            return

        card = tk.Frame(
            self.scroll_frame, bg=colors["card_bg"],
            highlightbackground=colors["border"], highlightthickness=1
        )
        card.pack(fill=tk.X, padx=16, pady=4)

        for i, entry in enumerate(entries):
            row = tk.Frame(card, bg=colors["card_bg"])
            row.pack(fill=tk.X, padx=12, pady=4)

            # Executor name
            name_text = entry.executor if entry.executor else self._t("dashboard_unassigned")
            tk.Label(
                row, text=name_text, width=12, anchor="w",
                font=("", 10), fg=colors["card_fg"], bg=colors["card_bg"],
            ).pack(side=tk.LEFT)

            # Hours
            tk.Label(
                row, text=f"{entry.actual_hours:.1f}h",
                font=("", 10, "bold"), fg=colors["card_fg"],
                bg=colors["card_bg"],
            ).pack(side=tk.LEFT, padx=(8, 4))

            # Percentage
            tk.Label(
                row, text=f"{entry.percentage * 100:.0f}%",
                font=("", 9), fg=colors["muted_fg"], bg=colors["card_bg"],
            ).pack(side=tk.LEFT)

            # Mini bar
            bar_canvas = tk.Canvas(
                row, height=8, width=100,
                bg=colors["progress_bg"], highlightthickness=0,
            )
            bar_canvas.pack(side=tk.LEFT, padx=(8, 0))
            fill_w = int(100 * min(entry.percentage, 1.0))
            if fill_w > 0:
                bar_canvas.create_rectangle(
                    0, 0, fill_w, 8,
                    fill=colors["progress_fill"], outline=""
                )

        # Bottom padding
        tk.Frame(card, height=4, bg=colors["card_bg"]).pack()
