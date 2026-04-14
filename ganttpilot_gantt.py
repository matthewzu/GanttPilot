#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GanttPilot - Gantt Chart Rendering / 甘特图渲染

DrawBackend abstraction with CanvasBackend (GUI) and PillowBackend (PNG export).
Also generates PlantUML @startgantt markup for browser viewing.
"""

import zlib
import webbrowser
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, Sequence, Tuple


# ── Executor color palette ───────────────────────────────────
EXECUTOR_PALETTE = [
    "#7BC67E",  # green
    "#F5A623",  # orange
    "#E74C8B",  # pink/magenta
    "#4A90D9",  # blue
    "#9B59B6",  # purple
    "#1ABC9C",  # teal
    "#E67E22",  # dark orange
    "#3498DB",  # light blue
    "#E74C3C",  # red
    "#2ECC71",  # emerald
    "#F39C12",  # yellow
    "#8E44AD",  # deep purple
]
COLOR_FINISHED = "#95A5A6"
COLOR_MILESTONE_BG = "#D5D8DC"
COLOR_MILESTONE_FG = "#2C3E50"
COLOR_TODAY = "#FF4444"
COLOR_GRID = "#E8E8E8"
COLOR_WEEKEND_BG = "#F5E6E6"  # light pink like reference
COLOR_HEADER_BG = "#FAFAFA"
COLOR_LABEL_BG = "#F8F8F8"
COLOR_BORDER = "#CCCCCC"
COLOR_ARROW = "#666666"


def darken_color(hex_color, factor=0.6):
    """Darken a hex color by multiplying each RGB channel by factor."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return "#000000"
    r = int(int(hex_color[0:2], 16) * factor)
    g = int(int(hex_color[2:4], 16) * factor)
    b = int(int(hex_color[4:6], 16) * factor)
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def _parse_date(s):
    try:
        return datetime.strptime(s, "%Y%m%d").date()
    except ValueError:
        return None


def _date_range(start, end):
    days = (end - start).days + 1
    return [start + timedelta(days=i) for i in range(days)]


def _weekday_short(d, lang="zh"):
    names_en = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
    names_zh = ["一", "二", "三", "四", "五", "六", "日"]
    names = names_zh if lang == "zh" else names_en
    return names[d.weekday()]


# ── DrawBackend abstract base class ─────────────────────────

class DrawBackend(ABC):
    """甘特图绘制后端抽象接口"""

    @abstractmethod
    def set_size(self, width: int, height: int) -> None:
        """设置画布/图片尺寸"""
        ...

    @abstractmethod
    def clear(self) -> None:
        """清除所有已绘制内容"""
        ...

    @abstractmethod
    def rectangle(self, x1: float, y1: float, x2: float, y2: float,
                  fill: str = "", outline: str = "", width: int = 0) -> None:
        """绘制矩形"""
        ...

    @abstractmethod
    def line(self, x1: float, y1: float, x2: float, y2: float,
             fill: str = "#000000", width: int = 1,
             dash: Optional[Tuple[int, ...]] = None) -> None:
        """绘制线段"""
        ...

    @abstractmethod
    def text(self, x: float, y: float, text: str,
             font_size: int = 10, fill: str = "#000000",
             anchor: str = "nw", bold: bool = False) -> None:
        """绘制文本"""
        ...

    @abstractmethod
    def polygon(self, points: Sequence[Tuple[float, float]],
                fill: str = "", outline: str = "", width: int = 1) -> None:
        """绘制多边形"""
        ...


# ── CanvasBackend ────────────────────────────────────────────

class CanvasBackend(DrawBackend):
    """tkinter Canvas 绘制后端，用于 GUI 实时渲染"""

    def __init__(self, canvas) -> None:
        self._canvas = canvas

    def set_size(self, width: int, height: int) -> None:
        self._canvas.configure(scrollregion=(0, 0, width, height))

    def clear(self) -> None:
        self._canvas.delete("all")

    def rectangle(self, x1, y1, x2, y2, fill="", outline="", width=0):
        self._canvas.create_rectangle(x1, y1, x2, y2,
                                       fill=fill, outline=outline, width=width)

    def line(self, x1, y1, x2, y2, fill="#000000", width=1, dash=None):
        kwargs = {"fill": fill, "width": width}
        if dash:
            kwargs["dash"] = dash
        self._canvas.create_line(x1, y1, x2, y2, **kwargs)

    def text(self, x, y, text, font_size=10, fill="#000000", anchor="nw", bold=False):
        font = ("", font_size, "bold") if bold else ("", font_size)
        self._canvas.create_text(x, y, anchor=anchor, text=text,
                                  font=font, fill=fill)

    def polygon(self, points, fill="", outline="", width=1):
        flat = [coord for pt in points for coord in pt]
        self._canvas.create_polygon(*flat, fill=fill, outline=outline, width=width)


# ── PillowBackend ────────────────────────────────────────────

class PillowBackend(DrawBackend):
    """Pillow ImageDraw 绘制后端，用于 PNG 导出"""

    def __init__(self, width: int = 800, height: int = 600) -> None:
        from PIL import Image, ImageDraw, ImageFont
        self._Image = Image
        self._ImageDraw = ImageDraw
        self._ImageFont = ImageFont
        self._image = Image.new("RGB", (width, height), "white")
        self._draw = ImageDraw.Draw(self._image)

    def set_size(self, width: int, height: int) -> None:
        self._image = self._Image.new("RGB", (width, height), "white")
        self._draw = self._ImageDraw.Draw(self._image)

    def clear(self) -> None:
        w, h = self._image.size
        self._draw.rectangle([0, 0, w, h], fill="white")

    def rectangle(self, x1, y1, x2, y2, fill="", outline="", width=0):
        fill = fill if fill else None
        outline = outline if outline else None
        self._draw.rectangle([x1, y1, x2, y2],
                              fill=fill, outline=outline, width=max(width, 0))

    def line(self, x1, y1, x2, y2, fill="#000000", width=1, dash=None):
        # Pillow 不原生支持 dash，直接画实线
        self._draw.line([x1, y1, x2, y2], fill=fill, width=width)

    def text(self, x, y, text, font_size=10, fill="#000000", anchor="nw", bold=False):
        # 将 tkinter anchor 映射为 Pillow anchor
        anchor_map = {
            "nw": "la", "n": "ma", "ne": "ra",
            "w": "lm", "center": "mm", "e": "rm",
            "sw": "ld", "s": "md", "se": "rd",
        }
        pil_anchor = anchor_map.get(anchor, "la")
        font = self._get_font(font_size, bold)
        self._draw.text((x, y), text, fill=fill, font=font, anchor=pil_anchor)

    def polygon(self, points, fill="", outline="", width=1):
        fill = fill if fill else None
        outline = outline if outline else None
        self._draw.polygon(points, fill=fill, outline=outline, width=width)

    def save(self, path: str) -> None:
        """保存图片到文件"""
        self._image.save(path)

    def _get_font(self, size: int, bold: bool = False):
        """获取字体，优先使用系统中文字体，回退到默认字体"""
        import sys as _sys
        font_paths = []
        if _sys.platform == "win32":
            font_paths = [
                "C:/Windows/Fonts/msyh.ttc",      # 微软雅黑
                "C:/Windows/Fonts/msyhbd.ttc",     # 微软雅黑粗体
                "C:/Windows/Fonts/simhei.ttf",     # 黑体
            ]
        elif _sys.platform == "darwin":
            font_paths = [
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/STHeiti Light.ttc",
            ]
        else:
            font_paths = [
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            ]

        if bold:
            # 尝试粗体字体
            bold_paths = [p for p in font_paths if "bd" in p.lower() or "bold" in p.lower()]
            for fp in bold_paths:
                try:
                    return self._ImageFont.truetype(fp, size)
                except (OSError, IOError):
                    continue

        for fp in font_paths:
            try:
                return self._ImageFont.truetype(fp, size)
            except (OSError, IOError):
                continue

        # 回退到 Pillow 默认字体
        try:
            return self._ImageFont.truetype("arial.ttf", size)
        except (OSError, IOError):
            return self._ImageFont.load_default()



class GanttRenderer:
    """Renders a Gantt chart via DrawBackend with per-executor coloring."""

    LABEL_WIDTH = 200
    ROW_HEIGHT = 26
    DAY_WIDTH = 28
    HEADER_HEIGHT = 44
    PADDING = 3
    COMPRESS_THRESHOLD = 300  # auto-compress day_width when total_days exceeds this
    MAX_CHART_WIDTH = 4000    # max chart pixel width when compressed

    def __init__(self, backend: DrawBackend, project, lang="zh", font_size=10):
        self.backend = backend
        self.project = project
        self.lang = lang
        self.font_size = font_size
        # Scale layout with font size (base=10)
        scale = font_size / 10.0
        self.label_width = int(GanttRenderer.LABEL_WIDTH * scale)
        self.row_height = int(GanttRenderer.ROW_HEIGHT * scale)
        self.day_width = int(GanttRenderer.DAY_WIDTH * scale)
        self.header_height = int(GanttRenderer.HEADER_HEIGHT * scale)
        self.padding = max(2, int(GanttRenderer.PADDING * scale))
        self.font_size_small = max(7, font_size - 2)
        self.font_size_tiny = max(6, font_size - 3)
        self._executor_colors = {}
        self._color_idx = 0

    def _get_executor_color(self, executor):
        """Assign a consistent color per executor"""
        if not executor:
            return EXECUTOR_PALETTE[0]
        if executor not in self._executor_colors:
            self._executor_colors[executor] = EXECUTOR_PALETTE[self._color_idx % len(EXECUTOR_PALETTE)]
            self._color_idx += 1
        return self._executor_colors[executor]

    def draw(self):
        self.backend.clear()
        if not self.project:
            return

        # Collect tasks
        tasks = []  # (type, label, start, end, status, executor, plan_color, ms_color, deadline, progress, skip_dates, skip_non_workdays)
        for ms in self.project.get("milestones", []):
            ms_color = ms.get("color", "")
            ms_deadline = _parse_date(ms.get("deadline", ""))
            tasks.append(("milestone", ms["name"], None, None, None, "", "", ms_color, ms_deadline, 0, [], False))
            for plan in ms.get("plans", []):
                executor = plan.get("executor", "")
                label = plan["content"]
                start = _parse_date(plan["start_date"])
                end = _parse_date(plan["end_date"])
                status = plan.get("status", "active")
                plan_color = plan.get("color", "")
                progress = plan.get("progress", 0)
                skip_dates_list = plan.get("skip_dates", [])
                skip_non_wd = plan.get("skip_non_workdays", True)
                tasks.append(("task", label, start, end, status, executor, plan_color, ms_color, None, progress, skip_dates_list, skip_non_wd))

        if not tasks:
            self.backend.text(10, 10, "No data", font_size=self.font_size)
            return

        # Date range
        all_dates = []
        for t in tasks:
            if t[2]: all_dates.append(t[2])
            if t[3]: all_dates.append(t[3])
            if t[8]: all_dates.append(t[8])  # milestone deadline
        if not all_dates:
            return

        min_date = min(all_dates) - timedelta(days=2)
        max_date = max(all_dates) + timedelta(days=2)
        total_days = (max_date - min_date).days + 1
        dates = _date_range(min_date, max_date)
        today = datetime.now().date()

        # Auto-compress day_width for long projects
        if total_days > self.COMPRESS_THRESHOLD:
            max_chart = self.MAX_CHART_WIDTH - self.label_width - 10
            self.day_width = max(4, max_chart // total_days)

        chart_x = self.label_width
        chart_width = total_days * self.day_width
        total_width = chart_x + chart_width + 10
        total_height = self.header_height + len(tasks) * self.row_height + 40

        self.backend.set_size(total_width, total_height)

        # ── Weekend columns ──────────────────────────────────
        for i, d in enumerate(dates):
            x = chart_x + i * self.day_width
            if d.weekday() >= 5:
                self.backend.rectangle(
                    x, 0, x + self.day_width, total_height,
                    fill=COLOR_WEEKEND_BG, outline="",
                )

        # ── Grid lines (vertical) ───────────────────────────
        for i, d in enumerate(dates):
            x = chart_x + i * self.day_width
            self.backend.line(x, 0, x, total_height, fill=COLOR_GRID)

        # ── Header row 1: weekday names ──────────────────────
        for i, d in enumerate(dates):
            x = chart_x + i * self.day_width
            wd = _weekday_short(d, self.lang)
            color = "#CC6666" if d.weekday() >= 5 else "#666666"
            self.backend.text(
                x + self.day_width // 2, 6, wd,
                font_size=self.font_size_tiny, fill=color, anchor="n",
            )

        # ── Header row 2: day numbers ────────────────────────
        for i, d in enumerate(dates):
            x = chart_x + i * self.day_width
            color = "#CC6666" if d.weekday() >= 5 else "#333333"
            self.backend.text(
                x + self.day_width // 2, 20, str(d.day),
                font_size=self.font_size_small, fill=color, anchor="n",
            )

        # ── Header separator ─────────────────────────────────
        self.backend.line(0, self.header_height, total_width, self.header_height, fill=COLOR_BORDER)

        # ── Month labels at bottom ───────────────────────────
        bottom_y = self.header_height + len(tasks) * self.row_height + 8
        current_month = None
        month_start_x = chart_x
        for i, d in enumerate(dates):
            month_key = (d.year, d.month)
            x = chart_x + i * self.day_width
            if month_key != current_month:
                if current_month is not None:
                    mid = (month_start_x + x) / 2
                    month_names_en = ["", "January", "February", "March", "April", "May", "June",
                                      "July", "August", "September", "October", "November", "December"]
                    month_names_zh = ["", "1月", "2月", "3月", "4月", "5月", "6月",
                                      "7月", "8月", "9月", "10月", "11月", "12月"]
                    names = month_names_zh if self.lang == "zh" else month_names_en
                    label = f"{names[current_month[1]]} {current_month[0]}"
                    self.backend.text(mid, bottom_y, label,
                                      font_size=self.font_size, fill="#555", anchor="n", bold=True)
                current_month = month_key
                month_start_x = x
        if current_month:
            mid = (month_start_x + chart_x + total_days * self.day_width) / 2
            month_names_en = ["", "January", "February", "March", "April", "May", "June",
                              "July", "August", "September", "October", "November", "December"]
            month_names_zh = ["", "1月", "2月", "3月", "4月", "5月", "6月",
                              "7月", "8月", "9月", "10月", "11月", "12月"]
            names = month_names_zh if self.lang == "zh" else month_names_en
            label = f"{names[current_month[1]]} {current_month[0]}"
            self.backend.text(mid, bottom_y, label,
                              font_size=self.font_size, fill="#555", anchor="n", bold=True)

        # ── Today line ───────────────────────────────────────
        if min_date <= today <= max_date:
            tx = chart_x + (today - min_date).days * self.day_width + self.day_width // 2
            self.backend.line(tx, 0, tx, total_height, fill=COLOR_TODAY, width=2, dash=(4, 2))

        # ── Draw tasks ───────────────────────────────────────
        for row, (kind, label, start, end, status, executor, plan_color, ms_color, deadline, progress, skip_dates_list, skip_non_wd) in enumerate(tasks):
            y = self.header_height + row * self.row_height
            mid_y = y + self.row_height // 2

            # Row separator
            self.backend.line(0, y + self.row_height, total_width, y + self.row_height, fill=COLOR_GRID)

            if kind == "milestone":
                # Milestone row
                self.backend.rectangle(0, y, total_width, y + self.row_height, fill=COLOR_MILESTONE_BG, outline="")
                self.backend.text(8, mid_y, label,
                                  font_size=self.font_size, fill=COLOR_MILESTONE_FG, anchor="w", bold=True)
                # Draw deadline diamond marker
                if deadline and min_date <= deadline <= max_date:
                    dx = chart_x + (deadline - min_date).days * self.day_width + self.day_width // 2
                    sz = self.row_height // 3
                    self.backend.polygon(
                        [(dx, mid_y - sz), (dx + sz, mid_y), (dx, mid_y + sz), (dx - sz, mid_y)],
                        fill="#E74C3C", outline="#C0392B", width=1,
                    )
                    # Date label next to diamond
                    self.backend.text(
                        dx + sz + 4, mid_y, deadline.strftime("%m/%d"),
                        font_size=self.font_size_tiny, fill="#C0392B", anchor="w",
                    )
            else:
                # Label area background
                self.backend.rectangle(0, y, chart_x, y + self.row_height, fill=COLOR_LABEL_BG, outline="")

                # Task label (truncate if needed)
                display = label if len(label) <= 24 else label[:22] + "…"
                self.backend.text(8, mid_y, display,
                                  font_size=self.font_size, fill="#333", anchor="w")

                # Task bar
                if start and end:
                    bx1 = chart_x + (start - min_date).days * self.day_width + 1
                    bx2 = chart_x + (end - min_date).days * self.day_width + self.day_width - 1
                    by1 = y + self.padding + 1
                    by2 = y + self.row_height - self.padding - 1

                    # Color priority: plan_color > executor color > palette
                    if status == "finished":
                        color = COLOR_FINISHED
                    elif plan_color:
                        color = plan_color
                    else:
                        color = self._get_executor_color(executor)

                    # Bar with rounded feel (two rects)
                    self.backend.rectangle(bx1, by1, bx2, by2, fill=color, outline="", width=0)
                    # Slight border
                    self.backend.rectangle(bx1, by1, bx2, by2, fill="", outline=color, width=1)

                    # Progress bar overlay
                    if progress > 0:
                        bar_total_width = bx2 - bx1
                        progress_width = bar_total_width * progress / 100
                        dark_color = darken_color(color, 0.6)
                        self.backend.rectangle(
                            bx1, by1, bx1 + progress_width, by2,
                            fill=dark_color, outline="", width=0,
                        )

                    # Text on bar
                    bar_width = bx2 - bx1
                    bar_mid = (bx1 + bx2) / 2
                    duration = (end - start).days + 1
                    bar_label = f"{label}" if bar_width > 80 else f"{duration}d"
                    if status == "finished":
                        bar_label = "✓ " + bar_label
                    if progress > 0:
                        bar_label = f"{progress}%"

                    # Only show text if bar is wide enough
                    if bar_width > 30:
                        self.backend.text(
                            bar_mid, mid_y, bar_label,
                            font_size=self.font_size_small, fill="white", anchor="center",
                        )

                    # Executor tag after bar
                    if executor and bar_width < 120:
                        self.backend.text(
                            bx2 + 4, mid_y, executor,
                            font_size=self.font_size_tiny, fill="#888", anchor="w",
                        )

                    # Skip date overlay stripes on bar
                    if skip_non_wd or skip_dates_list:
                        extra_skip = set()
                        remove_skip = set()
                        for sd in skip_dates_list:
                            sd = sd.strip()
                            if sd.startswith("-"):
                                d = _parse_date(sd[1:])
                                if d:
                                    remove_skip.add(d)
                            else:
                                d = _parse_date(sd)
                                if d:
                                    extra_skip.add(d)

                        current = start
                        while current <= end:
                            is_skipped = False
                            if current in extra_skip:
                                is_skipped = True
                            elif skip_non_wd and current.weekday() >= 5:
                                if current not in remove_skip:
                                    is_skipped = True

                            if is_skipped:
                                sx = chart_x + (current - min_date).days * self.day_width
                                # Draw visible diagonal hatch lines over the skipped day
                                self.backend.rectangle(
                                    sx, by1, sx + self.day_width, by2,
                                    fill="", outline="", width=0,
                                )
                                # Diagonal lines for hatch pattern
                                for offset in range(0, self.day_width + (by2 - by1), 4):
                                    x1 = sx + offset
                                    y1 = by1
                                    x2 = sx + offset - (by2 - by1)
                                    y2 = by2
                                    # Clip to bar bounds
                                    if x1 > sx + self.day_width:
                                        y1 = by1 + (x1 - sx - self.day_width)
                                        x1 = sx + self.day_width
                                    if x2 < sx:
                                        y2 = by2 - (sx - x2)
                                        x2 = sx
                                    if y1 < by2 and y2 > by1:
                                        self.backend.line(
                                            x1, y1, x2, y2,
                                            fill="#AA0000", width=1,
                                        )
                            current += timedelta(days=1)

        # ── Label column border ──────────────────────────────
        self.backend.line(chart_x, 0, chart_x, total_height, fill=COLOR_BORDER)



# ── PlantUML generation (for browser viewing) ───────────────

_PLANTUML_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"
PLANTUML_SERVER = "https://www.plantuml.com/plantuml/svg/"


def _encode6bit(b):
    return _PLANTUML_ALPHABET[b & 0x3F]


def _encode3bytes(b1, b2, b3):
    c1 = b1 >> 2
    c2 = ((b1 & 0x3) << 4) | (b2 >> 4)
    c3 = ((b2 & 0xF) << 2) | (b3 >> 6)
    c4 = b3 & 0x3F
    return _encode6bit(c1) + _encode6bit(c2) + _encode6bit(c3) + _encode6bit(c4)


def _plantuml_encode(text):
    data = zlib.compress(text.encode("utf-8"))[2:-4]
    encoded = ""
    for i in range(0, len(data), 3):
        if i + 2 < len(data):
            encoded += _encode3bytes(data[i], data[i + 1], data[i + 2])
        elif i + 1 < len(data):
            encoded += _encode3bytes(data[i], data[i + 1], 0)
        else:
            encoded += _encode3bytes(data[i], 0, 0)
    return encoded


def _format_date_plantuml(date_str):
    try:
        d = datetime.strptime(date_str, "%Y%m%d")
        return d.strftime("%Y-%m-%d")
    except ValueError:
        return date_str


def generate_gantt_uml(project, lang="zh"):
    lines = ["@startgantt"]
    lines.append(f"title {project['name']}")
    lines.append("printscale daily")
    lines.append("saturday are closed")
    lines.append("sunday are closed")

    all_starts = []
    for ms in project.get("milestones", []):
        for plan in ms.get("plans", []):
            all_starts.append(plan["start_date"])
    if all_starts:
        lines.append(f"Project starts {_format_date_plantuml(min(all_starts))}")
    lines.append("")

    for ms in project.get("milestones", []):
        for plan in ms.get("plans", []):
            if plan.get("skip_non_workdays", True) and plan.get("skip_dates"):
                for sd in plan["skip_dates"]:
                    sd = sd.strip()
                    if sd.startswith("-"):
                        continue  # minus prefix = make workday, not a PlantUML "is closed"
                    lines.append(f"{_format_date_plantuml(sd)} is closed")

    for ms in project.get("milestones", []):
        lines.append(f"-- {ms['name']} --")
        for plan in ms.get("plans", []):
            executor = plan.get("executor", "")
            label = f"[{plan['content']}]" if not executor else f"[{plan['content']} ({executor})]"
            start = _format_date_plantuml(plan["start_date"])
            end = _format_date_plantuml(plan["end_date"])
            lines.append(f"{label} starts {start} and ends {end}")
            if plan.get("status") == "finished":
                lines.append(f"{label} is 100% completed")
            lines.append("")

    lines.append("@endgantt")
    return "\n".join(lines)


def generate_gantt_url(project, lang="zh"):
    uml = generate_gantt_uml(project, lang)
    return PLANTUML_SERVER + _plantuml_encode(uml)


def open_gantt_in_browser(project, lang="zh"):
    url = generate_gantt_url(project, lang)
    webbrowser.open(url)
    return url


def generate_gantt_markdown(project, lang="zh", png_filename=None):
    """Generate a comprehensive project report in Markdown."""
    zh = lang == "zh"
    lines = [f"# {project['name']}", ""]

    # Gantt chart image (if PNG available) — no PlantUML code block
    if png_filename:
        chart_label = "甘特图" if zh else "Gantt Chart"
        lines.append(f"![{chart_label}]({png_filename})")
        lines.append("")

    # Milestones summary
    lines.append(f"## {'里程碑' if zh else 'Milestones'}")
    lines.append("")
    cr_label = "完成率" if zh else "Completion Rate"
    lines.append(f"| {'名称' if zh else 'Name'} | {'截止日期' if zh else 'Deadline'} | {'描述' if zh else 'Description'} | {'计划数' if zh else 'Plans'} | {cr_label} |")
    lines.append("|---|---|---|---|---|")
    for ms in project.get("milestones", []):
        dl = ms.get("deadline", "") or "-"
        desc = ms.get("description", "") or "-"
        plans = ms.get("plans", [])
        plan_count = len(plans)
        if plan_count > 0:
            avg_progress = sum(p.get("progress", 0) for p in plans) / plan_count
        else:
            avg_progress = 0
        lines.append(f"| {ms['name']} | {dl} | {desc} | {plan_count} | {avg_progress:.0f}% |")
    lines.append("")

    # Plan progress details table
    progress_label = "进度" if zh else "Progress"
    actual_end_label = "实际完成时间" if zh else "Actual End Date"
    status_label = "状态" if zh else "Status"
    ahead_label = "提前完成" if zh else "Ahead of Schedule"
    behind_label = "延期完成" if zh else "Behind Schedule"
    on_time_label = "按时完成" if zh else "On Time"

    has_plans = any(ms.get("plans") for ms in project.get("milestones", []))
    if has_plans:
        lines.append(f"## {'计划进度详情' if zh else 'Plan Progress Details'}")
        lines.append("")
        lines.append(f"| {'里程碑' if zh else 'Milestone'} | {'计划' if zh else 'Plan'} | {'执行者' if zh else 'Executor'} | {'计划工时' if zh else 'Planned Hours'} | {progress_label} | {'结束日期' if zh else 'End Date'} | {actual_end_label} | {status_label} |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for ms in project.get("milestones", []):
            for plan in ms.get("plans", []):
                p_progress = plan.get("progress", 0)
                p_actual = plan.get("actual_end_date", "")
                p_end = plan.get("end_date", "")
                p_hours = plan.get("planned_hours", 0)
                schedule_note = ""
                if p_actual and p_end:
                    if p_actual < p_end:
                        schedule_note = ahead_label
                    elif p_actual > p_end:
                        schedule_note = behind_label
                    else:
                        schedule_note = on_time_label
                hours_str = f"{p_hours:.1f}h" if p_hours else "-"
                lines.append(f"| {ms['name']} | {plan.get('content', '')} | {plan.get('executor', '')} | {hours_str} | {p_progress}% | {p_end} | {p_actual or '-'} | {schedule_note} |")
        lines.append("")

    # Collect all activities grouped by executor
    executor_activities = {}  # {executor: [{"date", "hours", "content", "plan", "milestone"}]}
    for ms in project.get("milestones", []):
        for plan in ms.get("plans", []):
            for act in plan.get("activities", []):
                ex = act["executor"]
                if ex not in executor_activities:
                    executor_activities[ex] = []
                executor_activities[ex].append({
                    "date": act.get("date", ""),
                    "hours": act.get("hours", 0),
                    "content": act.get("content", ""),
                    "plan": plan.get("content", ""),
                    "milestone": ms["name"],
                })

    # Per-executor activity reports
    if executor_activities:
        lines.append(f"## {'执行者工时明细' if zh else 'Executor Activity Details'}")
        lines.append("")
        for ex in sorted(executor_activities.keys()):
            acts = executor_activities[ex]
            total_hours = sum(a["hours"] for a in acts)
            total_days = round(total_hours / 8.0, 2)
            lines.append(f"### {ex}")
            lines.append("")
            lines.append(f"{'总计' if zh else 'Total'}: **{total_hours:.1f}** {'小时' if zh else 'hours'} / **{total_days}** {'天' if zh else 'days'}")
            lines.append("")
            lines.append(f"| {'日期' if zh else 'Date'} | {'小时' if zh else 'Hours'} | {'内容' if zh else 'Content'} | {'所属计划' if zh else 'Plan'} | {'里程碑' if zh else 'Milestone'} |")
            lines.append("|---|---|---|---|---|")
            for a in sorted(acts, key=lambda x: x["date"]):
                lines.append(f"| {a['date']} | {a['hours']:.1f} | {a['content']} | {a['plan']} | {a['milestone']} |")
            lines.append("")

    return "\n".join(lines)
