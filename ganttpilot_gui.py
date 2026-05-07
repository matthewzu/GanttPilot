#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GanttPilot - GUI Interface (tkinter) / 图形界面

All CRUD operations via right-click context menus on the tree.
"""

import copy
import os
import re
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog, colorchooser
import webbrowser
import urllib.request
import json

from ganttpilot_i18n import t
from ganttpilot_config import Config
from ganttpilot_core import DataStore, parse_time_slots, calculate_hours_from_slots
from ganttpilot_git import GitSync
from ganttpilot_gantt import GanttRenderer, CanvasBackend, generate_gantt_markdown
from ganttpilot_shortcuts import ShortcutManager, tk_event_to_display
from version import VERSION

import shutil
import stat

GITHUB_REPO = "matthewzu/GanttPilot"

# ── Toolbar button state mapping ─────────────────────────────
TOOLBAR_STATE = {
    None:                  {"add": False, "edit": False, "delete": False, "up": False, "down": False, "dup": False, "copy": False, "paste": False},
    "project":             {"add": False, "edit": True,  "delete": False, "up": False, "down": False, "dup": True,  "copy": True,  "paste": False},
    "req_analysis":        {"add": True,  "edit": False, "delete": False, "up": False, "down": False, "dup": False, "copy": False, "paste": True},
    "requirement":         {"add": True,  "edit": True,  "delete": True,  "up": True,  "down": True,  "dup": True,  "copy": True,  "paste": True},
    "task":                {"add": False, "edit": True,  "delete": True,  "up": True,  "down": True,  "dup": True,  "copy": True,  "paste": False},
    "plan_execution":      {"add": True,  "edit": False, "delete": False, "up": False, "down": False, "dup": False, "copy": False, "paste": True},
    "milestone":           {"add": True,  "edit": True,  "delete": True,  "up": True,  "down": True,  "dup": True,  "copy": True,  "paste": True},
    "plan":                {"add": True,  "edit": True,  "delete": True,  "up": True,  "down": True,  "dup": True,  "copy": True,  "paste": True},
    "activity":            {"add": False, "edit": True,  "delete": True,  "up": True,  "down": True,  "dup": True,  "copy": True,  "paste": False},
}


def format_requirement_display(category, subject):
    """Format requirement display text: [category]subject if category non-empty, else just subject."""
    if category:
        return f"[{category}]{subject}"
    return subject


def format_linked_task_display(category, req_subject, task_subject):
    """Format linked task dropdown display: [category]req_subject / task_subject.

    When category is empty, format is 'req_subject / task_subject'.
    """
    if category:
        return f"[{category}]{req_subject} / {task_subject}"
    return f"{req_subject} / {task_subject}"


def build_tracking_data(project):
    """Build tracking data for the requirement tracking tab.

    Pure function that can be tested without GUI.

    Returns a list of dicts, each representing a row in the tracking table.
    Requirement rows have kind='requirement', task rows have kind='task'.
    """
    rows = []
    if not project:
        return rows

    # Build a lookup: task_id -> (plan_content, plan_progress, actual_hours)
    task_plan_map = {}  # task_id -> (plan_content, progress, actual_hours)
    for ms in project.get("milestones", []):
        for plan in ms.get("plans", []):
            linked = plan.get("linked_task_id", "")
            if linked:
                actual_h = sum(a.get("hours", 0) for a in plan.get("activities", []))
                task_plan_map[linked] = (plan.get("content", ""), plan.get("progress", 0), actual_h)

    for req in project.get("requirements", []):
        # Requirement group header row
        rows.append({
            "kind": "requirement",
            "req_category": req.get("category", ""),
            "req_subject": req.get("subject", ""),
            "task_subject": "",
            "effort_days": "",
            "linked_plan": "",
            "plan_progress": "",
            "actual_hours": "",
        })
        for task in req.get("tasks", []):
            task_id = task.get("id", "")
            plan_info = task_plan_map.get(task_id)
            linked_plan = plan_info[0] if plan_info else ""
            plan_progress = f"{plan_info[1]}%" if plan_info else ""
            actual_hours = f"{plan_info[2]:.1f}h" if plan_info else ""
            effort_d = task.get("effort_days", 0) or 0
            effort_h_str = f"{effort_d * 8:.1f}h" if effort_d else ""
            rows.append({
                "kind": "task",
                "req_category": "",
                "req_subject": "",
                "task_subject": task.get("subject", ""),
                "effort_days": effort_h_str,
                "linked_plan": linked_plan,
                "plan_progress": plan_progress,
                "actual_hours": actual_hours,
            })
    return rows


def _force_rmtree(path):
    """Remove a directory tree, handling Windows read-only files (e.g. .git pack files)."""
    def _on_error(func, fpath, exc_info):
        try:
            os.chmod(fpath, stat.S_IWRITE)
            func(fpath)
        except Exception:
            pass
    shutil.rmtree(path, onerror=_on_error)


def _center_dialog(dialog, parent, width, height):
    """将对话框居中于父窗口。

    Args:
        dialog: Toplevel 对话框窗口
        parent: 父窗口（主窗口或其他 Toplevel）
        width: 对话框宽度
        height: 对话框高度
    """
    parent.update_idletasks()
    px = parent.winfo_x()
    py = parent.winfo_y()
    pw = parent.winfo_width()
    ph = parent.winfo_height()

    x = px + (pw - width) // 2
    y = py + (ph - height) // 2

    # 确保不超出屏幕边界
    x = max(0, x)
    y = max(0, y)

    dialog.geometry(f"{width}x{height}+{x}+{y}")


def validate_priv_branch_name(name, main_branch="main"):
    """校验私有分支名称。

    Args:
        name: 用户输入的分支名称
        main_branch: 远端主分支名称

    Returns:
        (bool, str): (是否合法, 错误信息key)
    """
    if not name:
        return True, ""  # 空值允许（将自动生成）

    # 禁止 "priv" 作为分支名
    if name == "priv":
        return False, "priv_branch_invalid_priv"

    # 禁止与主分支同名
    if name == main_branch:
        return False, "priv_branch_same_as_main"

    # Git 分支名格式校验
    if re.search(r'[\s~^:?*\[\]\\]', name):
        return False, "priv_branch_invalid_chars"
    if name.startswith('.') or name.startswith('/'):
        return False, "priv_branch_invalid_chars"
    if name.endswith('.') or name.endswith('/') or name.endswith('.lock'):
        return False, "priv_branch_invalid_chars"
    if '..' in name:
        return False, "priv_branch_invalid_chars"
    if name.startswith('-'):
        return False, "priv_branch_invalid_chars"

    return True, ""


class UpdateChecker:
    def __init__(self, current_version, language, callback,
                 no_update_callback=None, fail_callback=None):
        self.current_version = current_version
        self.language = language
        self.callback = callback
        self.no_update_callback = no_update_callback
        self.fail_callback = fail_callback

    def check(self):
        threading.Thread(target=self._do_check, daemon=True).start()

    def _do_check(self):
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            req = urllib.request.Request(url, headers={"User-Agent": "GanttPilot"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            # Skip draft or prerelease
            if data.get("draft") or data.get("prerelease"):
                if self.no_update_callback:
                    self.no_update_callback()
                return
            tag = data.get("tag_name", "").lstrip("v")
            if tag and tag != self.current_version:
                # Find platform-specific asset URL
                asset_url = None
                asset_size = 0
                platform = sys.platform
                for asset in data.get("assets", []):
                    # Skip assets still being uploaded
                    if asset.get("state") != "uploaded":
                        continue
                    name = asset.get("name", "").lower()
                    matched = False
                    if platform == "win32" and name.endswith(".exe"):
                        matched = True
                    elif platform == "darwin" and name.endswith(".dmg"):
                        matched = True
                    elif platform.startswith("linux") and not name.endswith((".exe", ".dmg")):
                        matched = True
                    if matched:
                        asset_url = asset["browser_download_url"]
                        asset_size = asset.get("size", 0)
                dl_url = data.get("html_url", f"https://github.com/{GITHUB_REPO}/releases")
                self.callback(tag, dl_url, asset_url, asset_size)
            else:
                # No update available (current version is latest)
                if self.no_update_callback:
                    self.no_update_callback()
        except Exception:
            # Network failure or other error
            if self.fail_callback:
                self.fail_callback()


class UndoManager:
    """Snapshot-based undo/redo manager using deep copy."""

    def __init__(self, store):
        self.store = store
        self.undo_stack = []
        self.redo_stack = []

    def save_snapshot(self):
        """Save current data state to undo stack, clear redo stack."""
        self.undo_stack.append(copy.deepcopy(self.store.data))
        self.redo_stack.clear()

    def undo(self):
        """Undo: push current state to redo stack, pop from undo stack."""
        if not self.undo_stack:
            return False
        self.redo_stack.append(copy.deepcopy(self.store.data))
        self.store.data = self.undo_stack.pop()
        return True

    def redo(self):
        """Redo: push current state to undo stack, pop from redo stack."""
        if not self.redo_stack:
            return False
        self.undo_stack.append(copy.deepcopy(self.store.data))
        self.store.data = self.redo_stack.pop()
        return True

    def can_undo(self):
        return len(self.undo_stack) > 0

    def can_redo(self):
        return len(self.redo_stack) > 0


class GanttPilotGUI:
    """Main GUI — tree with right-click menus, gantt canvas, time report."""

    def __init__(self, root):
        self.root = root
        self.config = Config()
        self.lang = self.config.language

        if not self.config.data_dir:
            self.config.data_dir = os.path.join(os.path.expanduser("~"), ".ganttpilot", "data")
        os.makedirs(self.config.data_dir, exist_ok=True)

        self.store = DataStore(self.config.data_dir)
        self.undo_manager = UndoManager(self.store)
        self.current_project = None
        self.gantt_zoom = 10  # independent gantt zoom level (font size for gantt)
        self._active_dialog = None
        self._focus_restore_id = None

        self.root.title(self._t("app_title") + f" v{VERSION}")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._set_icon()
        self._apply_saved_geometry()

        self.create_widgets()
        self.refresh_project_list()

        # ── ShortcutManager setup ────────────────────────────
        self.shortcut_manager = ShortcutManager(self.root, self.config)
        self.shortcut_manager._gui = self

        # Register all action handlers
        self.shortcut_manager.set_action_handler("add", self.toolbar_add)
        self.shortcut_manager.set_action_handler("edit", self.toolbar_edit)
        self.shortcut_manager.set_action_handler("delete", self.toolbar_delete)
        self.shortcut_manager.set_action_handler("move_up", self.toolbar_move_up)
        self.shortcut_manager.set_action_handler("move_down", self.toolbar_move_down)
        self.shortcut_manager.set_action_handler("duplicate", self.toolbar_duplicate)
        self.shortcut_manager.set_action_handler("copy", self.toolbar_copy)
        self.shortcut_manager.set_action_handler("paste", self.toolbar_paste)
        self.shortcut_manager.set_action_handler("undo", self.do_undo)
        self.shortcut_manager.set_action_handler("redo", self.do_redo)
        self.shortcut_manager.set_action_handler("sync", self.do_sync)
        self.shortcut_manager.set_action_handler("refresh", self._full_refresh)

        # Bind new shortcuts via ShortcutManager (add, edit, delete, move_up,
        # move_down, duplicate, sync, refresh).  Then re-bind undo/redo/copy/paste
        # directly so their special focus-aware handlers take precedence.
        self.shortcut_manager.register_all()

        # Direct bindings for undo/redo/copy/paste — these override
        # ShortcutManager's bindings because do_undo/do_redo have their own
        # focus detection (they handle tk.Text edit_undo/edit_redo specially).
        self.root.bind("<Control-z>", self.do_undo)
        self.root.bind("<Control-y>", self.do_redo)
        self.root.bind("<Control-c>", self.toolbar_copy)
        self.root.bind("<Control-v>", self.toolbar_paste)

        # Focus restoration: bring modal dialog back to front when main window gets focus
        self.root.bind("<FocusIn>", self._on_main_focus)

        # Tooltips for undo/redo buttons
        self._show_tooltip(self.undo_btn, self._tooltip_with_shortcut(self._t("undo"), "undo"))
        self._show_tooltip(self.redo_btn, self._tooltip_with_shortcut(self._t("redo"), "redo"))

        # Tooltips for unified toolbar buttons
        self._show_tooltip(self.tb_add_btn, self._tooltip_with_shortcut(self._t("add"), "add"))
        self._show_tooltip(self.tb_edit_btn, self._tooltip_with_shortcut(self._t("edit"), "edit"))
        self._show_tooltip(self.tb_delete_btn, self._tooltip_with_shortcut(self._t("delete"), "delete"))
        self._show_tooltip(self.tb_copy_btn, self._tooltip_with_shortcut(self._t("copy"), "copy"))
        self._show_tooltip(self.tb_paste_btn, self._tooltip_with_shortcut(self._t("paste"), "paste"))
        self._show_tooltip(self.tb_dup_btn, self._tooltip_with_shortcut(self._t("duplicate"), "duplicate"))
        self._show_tooltip(self.tb_up_btn, self._tooltip_with_shortcut(self._t("move_up"), "move_up"))
        self._show_tooltip(self.tb_down_btn, self._tooltip_with_shortcut(self._t("move_down"), "move_down"))

        # Start background fetch for all projects with remote_url
        threading.Thread(target=self._startup_sync, daemon=True).start()
        UpdateChecker(VERSION, self.lang, self._show_update_notification).check()

        # Start periodic background check for main branch updates
        pull_interval = max(1, self.config.get("pull_interval", 5))
        self._bg_check_interval_ms = pull_interval * 60 * 1000
        self.root.after(self._bg_check_interval_ms, self._periodic_remote_check)

    def _t(self, key, *args):
        return t(key, self.lang, *args)

    def _on_main_focus(self, event=None):
        """Handle <FocusIn> on main window — debounce and restore dialog focus."""
        if self._focus_restore_id is not None:
            self.root.after_cancel(self._focus_restore_id)
        self._focus_restore_id = self.root.after(50, self._restore_dialog_focus)

    def _has_active_dialog(self):
        """Return True if a modal dialog is already open (prevents duplicates)."""
        dlg = self._active_dialog
        if dlg is not None:
            try:
                if dlg.winfo_exists():
                    dlg.lift()
                    dlg.focus_force()
                    return True
            except Exception:
                pass
            self._active_dialog = None
        return False

    def _restore_dialog_focus(self):
        """Bring active modal dialog to front if it still exists."""
        self._focus_restore_id = None
        dlg = self._active_dialog
        if dlg is not None:
            try:
                if dlg.winfo_exists():
                    dlg.deiconify()
                    dlg.lift()
                    dlg.focus_force()
                    try:
                        dlg.grab_set()
                    except Exception:
                        pass
            except Exception:
                pass

    def _apply_saved_geometry(self):
        geo = self.config.get("window_geometry", "1200x700")
        pos = self.config.get("window_position", "100,100")
        maximized = self.config.get("window_maximized", False)
        try:
            x, y = pos.split(",")
            self.root.geometry(f"{geo}+{x}+{y}")
        except Exception:
            self.root.geometry(geo)
        if maximized:
            self.root.state("zoomed")

    def _set_icon(self):
        """Set window icon from ganttpilot.ico"""
        try:
            ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ganttpilot.ico")
            if os.path.exists(ico_path):
                self.root.iconbitmap(ico_path)
        except Exception:
            pass

    def _startup_sync(self):
        """Fetch remote updates for all projects (pull-only, no push)."""
        try:
            updated_projects = []
            for proj in self.store.list_projects():
                if proj.get("remote_url"):
                    try:
                        gs = self._get_project_git(proj)
                        if not gs.is_repo():
                            continue
                        gs.init_repo()
                        gs.fetch_remote()
                        if getattr(gs, '_main_updated', False):
                            updated_projects.append(proj)
                    except Exception:
                        pass
            self.store.load()
            self.root.after(0, self.refresh_project_list)
            self.root.after(0, self.check_remote_updates)
            if updated_projects:
                self.root.after(0, lambda: self._prompt_rebase(updated_projects))
        except Exception:
            pass

    def _periodic_remote_check(self):
        """Periodically fetch remote and check for main branch updates in background."""
        def _do():
            try:
                updated_projects = []
                for proj in self.store.list_projects():
                    if proj.get("remote_url"):
                        try:
                            gs = self._get_project_git(proj)
                            if not gs.is_repo():
                                continue
                            gs.fetch_remote()
                            if getattr(gs, '_main_updated', False):
                                updated_projects.append(proj)
                        except Exception:
                            pass
                self.root.after(0, self.check_remote_updates)
                if updated_projects:
                    self.root.after(0, lambda: self._prompt_rebase(updated_projects))
            except Exception:
                pass
        threading.Thread(target=_do, daemon=True).start()
        # Schedule next check
        self.root.after(self._bg_check_interval_ms, self._periodic_remote_check)

    def _prompt_rebase(self, updated_projects):
        """Prompt user to rebase private branch after main was updated.

        Args:
            updated_projects: list of project dicts whose main branch was updated.
        """
        for proj in updated_projects:
            answer = messagebox.askyesno(
                self._t("update_check"),
                self._t("rebase_prompt"),
            )
            if not answer:
                continue
            try:
                gs = self._get_project_git(proj)
                gs.manual_rebase()
                self.status_var.set(self._t("rebase_success"))
                self._full_refresh()
            except RuntimeError as e:
                messagebox.showerror(self._t("error"), self._t("rebase_conflict"))

    def manual_update_check(self):
        """手动触发更新检测，禁用按钮直到检测完成。"""
        self.update_check_btn.configure(state=tk.DISABLED)
        self.status_var.set(self._t("checking_update"))

        def on_result(new_version, download_url, asset_url=None, asset_size=0):
            self.root.after(0, lambda: self.update_check_btn.configure(state=tk.NORMAL))
            if new_version:
                self.root.after(0, lambda: self._show_update_notification(new_version, download_url, asset_url, asset_size))

        def on_no_update():
            self.root.after(0, lambda: self.update_check_btn.configure(state=tk.NORMAL))
            self.root.after(0, lambda: self.status_var.set(self._t("no_update")))

        def on_fail():
            self.root.after(0, lambda: self.update_check_btn.configure(state=tk.NORMAL))
            self.root.after(0, lambda: self.status_var.set(self._t("check_update_fail")))

        UpdateChecker(VERSION, self.lang, on_result, no_update_callback=on_no_update, fail_callback=on_fail).check()

    def _show_update_notification(self, new_version, download_url, asset_url=None, asset_size=0):
        def show():
            if not asset_url:
                # No platform-specific asset ready yet
                msg = self._t("update_not_ready", new_version) if hasattr(self, '_t') else \
                    f"v{new_version} 发布资源尚未就绪，请稍后重试。"
                messagebox.showinfo(self._t("update_check"), msg)
                return
            if not messagebox.askyesno(self._t("update_check"), self._t("update_available", new_version)):
                return
            self.status_var.set(self._t("downloading_update"))
            self.root.update()
            threading.Thread(target=lambda: self._download_update(asset_url, new_version, asset_size), daemon=True).start()
        self.root.after(0, show)

    def _download_update(self, asset_url, new_version, expected_size=0):
        """Download update with progress reporting and integrity checks."""
        try:
            import time
            req = urllib.request.Request(asset_url, headers={"User-Agent": "GanttPilot"})
            with urllib.request.urlopen(req, timeout=300) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunks = []
                start_time = time.time()
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    downloaded += len(chunk)
                    elapsed = time.time() - start_time
                    speed = downloaded / elapsed if elapsed > 0 else 0
                    # Format progress
                    dl_mb = downloaded / 1048576
                    if total > 0:
                        total_mb = total / 1048576
                        pct = downloaded * 100 // total
                        msg = f"{pct}%  {dl_mb:.1f}/{total_mb:.1f}MB  {speed/1024:.0f}KB/s"
                    else:
                        msg = f"{dl_mb:.1f}MB  {speed/1024:.0f}KB/s"
                    self.root.after(0, lambda m=msg: self.status_var.set(m))
                data = b"".join(chunks)

            # --- Integrity checks ---
            # 1. Size check against Content-Length
            if total > 0 and len(data) != total:
                raise RuntimeError(
                    f"Size mismatch: expected {total} bytes, got {len(data)}" if self.lang == "en"
                    else f"大小不匹配: 预期 {total} 字节, 实际 {len(data)}")
            # 2. Size check against GitHub asset size
            if expected_size > 0 and len(data) != expected_size:
                raise RuntimeError(
                    f"Size mismatch with release: expected {expected_size} bytes, got {len(data)}" if self.lang == "en"
                    else f"与发布信息不匹配: 预期 {expected_size} 字节, 实际 {len(data)}")
            # 3. Minimum size sanity check (< 100KB is suspicious for an app binary)
            if len(data) < 102400:
                raise RuntimeError(
                    f"Downloaded file too small ({len(data)} bytes), possibly incomplete" if self.lang == "en"
                    else f"下载文件过小 ({len(data)} 字节)，可能不完整")
            # 4. Binary header validation
            if sys.platform == "win32" and data[:2] != b"MZ":
                raise RuntimeError(
                    "Invalid executable (not a valid PE file)" if self.lang == "en"
                    else "无效的可执行文件 (非有效 PE 格式)")
            elif sys.platform == "darwin" and data[:4] not in (b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbe"):
                raise RuntimeError(
                    "Invalid executable (not a valid Mach-O file)" if self.lang == "en"
                    else "无效的可执行文件 (非有效 Mach-O 格式)")
            elif sys.platform.startswith("linux") and data[:4] != b"\x7fELF":
                raise RuntimeError(
                    "Invalid executable (not a valid ELF file)" if self.lang == "en"
                    else "无效的可执行文件 (非有效 ELF 格式)")

            # Determine exe path
            exe_path = sys.executable
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
            else:
                ext = ".exe" if sys.platform == "win32" else ""
                exe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"GanttPilot{ext}")

            tmp_path = exe_path + ".new"
            with open(tmp_path, "wb") as f:
                f.write(data)

            if sys.platform != "win32":
                os.chmod(tmp_path, 0o755)

            if getattr(sys, 'frozen', False):
                old_path = exe_path + ".old"
                try:
                    os.remove(old_path)
                except OSError:
                    pass
                os.rename(exe_path, old_path)
                os.rename(tmp_path, exe_path)
                msg = f"v{new_version} downloaded. Restart to apply." if self.lang == "en" else f"v{new_version} 已下载，重启生效。"
            else:
                msg = f"v{new_version} downloaded to {exe_path}" if self.lang == "en" else f"v{new_version} 已下载到 {exe_path}"

            self.root.after(0, lambda: self.status_var.set(msg))
            self.root.after(0, lambda: messagebox.showinfo(self._t("update_check"), msg))
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"Update failed: {e}"))

    def _commit(self, message):
        """Commit changes for the current project's git repo."""
        if not self.current_project:
            return
        proj = self.store.get_project(self.current_project)
        if not proj:
            return
        try:
            gs = self._get_project_git(proj)
            gs.commit(message)
            self.refresh_history()
            self.refresh_branch_selector()
        except Exception:
            pass

    def _get_project_git(self, proj):
        """Construct a GitSync for a specific project directory."""
        proj_dir = os.path.join(self.config.data_dir, proj["name"])
        return GitSync(
            proj_dir,
            proj.get("remote_url", ""),
            proj.get("remote_username", ""),
            proj.get("remote_password", ""),
            proj.get("remote_branch", "main"),
            committer_name=proj.get("committer_name", ""),
            committer_email=proj.get("committer_email", ""),
            priv_branch=proj.get("priv_branch", ""),
        )

    # ── Widgets ──────────────────────────────────────────────
    def create_widgets(self):
        self.paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Left: tree only (no buttons)
        left_frame = ttk.Frame(self.paned, width=320)
        self.paned.add(left_frame, weight=1)

        # Minimal toolbar: lang, undo/redo, font, config, help
        toolbar = ttk.Frame(left_frame)
        toolbar.pack(fill=tk.X, pady=(0, 2))
        ttk.Button(toolbar, text="EN/中", command=self.toggle_language, width=5).pack(side=tk.LEFT, padx=1)
        self.undo_btn = ttk.Button(toolbar, text="↩", command=self.do_undo, width=3, state=tk.DISABLED)
        self.undo_btn.pack(side=tk.LEFT, padx=1)
        self.redo_btn = ttk.Button(toolbar, text="↪", command=self.do_redo, width=3, state=tk.DISABLED)
        self.redo_btn.pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="A+", command=self.increase_font, width=3).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="A-", command=self.decrease_font, width=3).pack(side=tk.LEFT, padx=1)

        # Unified toolbar buttons: Add, Edit, Delete | Copy, Paste, Duplicate | Move Up, Move Down
        self.tb_add_btn = ttk.Button(toolbar, text="+", command=self.toolbar_add, width=4, state=tk.DISABLED)
        self.tb_add_btn.pack(side=tk.LEFT, padx=1)
        self.tb_edit_btn = ttk.Button(toolbar, text="✏", command=self.toolbar_edit, width=4, state=tk.DISABLED)
        self.tb_edit_btn.pack(side=tk.LEFT, padx=1)
        self.tb_delete_btn = ttk.Button(toolbar, text="✕", command=self.toolbar_delete, width=4, state=tk.DISABLED)
        self.tb_delete_btn.pack(side=tk.LEFT, padx=1)
        self.tb_copy_btn = ttk.Button(toolbar, text="📋", command=self.toolbar_copy, width=4, state=tk.DISABLED)
        self.tb_copy_btn.pack(side=tk.LEFT, padx=1)
        self.tb_paste_btn = ttk.Button(toolbar, text="📌", command=self.toolbar_paste, width=4, state=tk.DISABLED)
        self.tb_paste_btn.pack(side=tk.LEFT, padx=1)
        self.tb_dup_btn = ttk.Button(toolbar, text="⧉", command=self.toolbar_duplicate, width=4, state=tk.DISABLED)
        self.tb_dup_btn.pack(side=tk.LEFT, padx=1)
        self.tb_up_btn = ttk.Button(toolbar, text="↑", command=self.toolbar_move_up, width=4, state=tk.DISABLED)
        self.tb_up_btn.pack(side=tk.LEFT, padx=1)
        self.tb_down_btn = ttk.Button(toolbar, text="↓", command=self.toolbar_move_down, width=4, state=tk.DISABLED)
        self.tb_down_btn.pack(side=tk.LEFT, padx=1)

        ttk.Button(toolbar, text="⚙", command=self.open_config_dialog, width=3).pack(side=tk.RIGHT, padx=1)
        self.update_check_btn = ttk.Button(toolbar, text="⟳", command=self.manual_update_check, width=3)
        self.update_check_btn.pack(side=tk.RIGHT, padx=1)
        ttk.Button(toolbar, text="?", command=self.show_help, width=3).pack(side=tk.RIGHT, padx=1)

        # Tree
        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(tree_frame, show="tree", selectmode="browse")
        sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Button-3>", self.on_tree_right_click)
        # Bind Alt+Up/Down directly on tree to ensure move shortcuts work
        # (Treeview default bindings can interfere with root-level shortcuts)
        def _tree_move_up(event):
            self.toolbar_move_up()
            return "break"
        def _tree_move_down(event):
            self.toolbar_move_down()
            return "break"
        self.tree.bind("<Alt-Up>", _tree_move_up)
        self.tree.bind("<Alt-Down>", _tree_move_down)

        # Right: branch selector + notebook (gantt + history) + report
        right_frame = ttk.Frame(self.paned)
        self.paned.add(right_frame, weight=3)

        # Branch selector above notebook
        branch_frame = ttk.Frame(right_frame)
        branch_frame.pack(fill=tk.X, pady=(0, 2))
        self.branch_label = ttk.Label(branch_frame, text=self._t("branch"))
        self.branch_label.pack(side=tk.LEFT, padx=(0, 4))
        self.branch_selector = ttk.Combobox(branch_frame, state="readonly", width=30)
        self.branch_selector.pack(side=tk.LEFT, padx=2)
        self.branch_selector.bind("<<ComboboxSelected>>", self.on_branch_changed)

        # Update banner (hidden by default) — between branch selector and notebook
        self.update_banner = ttk.Frame(right_frame)
        self.update_banner_label = ttk.Label(self.update_banner, text=self._t("main_updated"))
        self.update_banner_label.pack(side=tk.LEFT, padx=(4, 8))
        self.update_banner_btn = ttk.Button(self.update_banner, text=self._t("sync_main"),
                                            command=self.do_manual_rebase)
        self.update_banner_btn.pack(side=tk.LEFT, padx=2)
        # Don't pack update_banner — it starts hidden

        # Vertical PanedWindow: top = notebook (gantt + history), bottom = report
        self.right_vpaned = ttk.PanedWindow(right_frame, orient=tk.VERTICAL)
        self.right_vpaned.pack(fill=tk.BOTH, expand=True)

        # Notebook with gantt chart and history tabs
        self.right_notebook = ttk.Notebook(self.right_vpaned)
        self.right_vpaned.add(self.right_notebook, weight=7)

        # Tab 1: Gantt Chart
        gantt_tab_frame = ttk.Frame(self.right_notebook)
        self.right_notebook.add(gantt_tab_frame, text=self._t("gantt_chart"))

        # Gantt zoom toolbar
        gantt_toolbar = ttk.Frame(gantt_tab_frame)
        gantt_toolbar.pack(fill=tk.X, pady=(0, 2))
        ttk.Label(gantt_toolbar, text="🔍").pack(side=tk.LEFT, padx=2)
        ttk.Button(gantt_toolbar, text="+", command=self.gantt_zoom_in, width=2).pack(side=tk.LEFT, padx=1)
        ttk.Button(gantt_toolbar, text="-", command=self.gantt_zoom_out, width=2).pack(side=tk.LEFT, padx=1)

        self.gantt_canvas = tk.Canvas(gantt_tab_frame, bg="white")
        gy = ttk.Scrollbar(gantt_tab_frame, orient=tk.VERTICAL, command=self.gantt_canvas.yview)
        gx = ttk.Scrollbar(gantt_tab_frame, orient=tk.HORIZONTAL, command=self.gantt_canvas.xview)
        self.gantt_canvas.configure(yscrollcommand=gy.set, xscrollcommand=gx.set)
        gy.pack(side=tk.RIGHT, fill=tk.Y)
        gx.pack(side=tk.BOTTOM, fill=tk.X)
        self.gantt_canvas.pack(fill=tk.BOTH, expand=True)

        # Tab 2: Requirement Tracking (between Gantt and History)
        tracking_tab_frame = ttk.Frame(self.right_notebook)
        self.right_notebook.add(tracking_tab_frame, text=self._t("tracking_tab"))

        tracking_cols = ("req_category", "req_subject", "task_subject", "effort_days", "linked_plan", "plan_progress", "actual_hours")
        self.tracking_tree = ttk.Treeview(tracking_tab_frame, columns=tracking_cols, show="headings")
        self.tracking_tree.heading("req_category", text=self._t("req_category"))
        self.tracking_tree.heading("req_subject", text=self._t("req_subject"))
        self.tracking_tree.heading("task_subject", text=self._t("task_subject"))
        self.tracking_tree.heading("effort_days", text=self._t("planned_hours"))
        self.tracking_tree.heading("linked_plan", text=self._t("linked_plan"))
        self.tracking_tree.heading("plan_progress", text=self._t("plan_progress"))
        self.tracking_tree.heading("actual_hours", text=self._t("actual_hours"))
        self.tracking_tree.column("req_category", width=100, anchor="center")
        self.tracking_tree.column("req_subject", width=150, anchor="center")
        self.tracking_tree.column("task_subject", width=150, anchor="center")
        self.tracking_tree.column("effort_days", width=100, anchor="center")
        self.tracking_tree.column("linked_plan", width=150, anchor="center")
        self.tracking_tree.column("plan_progress", width=100, anchor="center")
        self.tracking_tree.column("actual_hours", width=100, anchor="center")
        tracking_sb = ttk.Scrollbar(tracking_tab_frame, orient=tk.VERTICAL, command=self.tracking_tree.yview)
        self.tracking_tree.configure(yscrollcommand=tracking_sb.set)
        tracking_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tracking_tree.pack(fill=tk.BOTH, expand=True)
        self.tracking_tree.tag_configure("req_header", font=("", self.config.font_size, "bold"), background="#d0d0e8")

        # Tab 3: History
        history_tab_frame = ttk.Frame(self.right_notebook)
        self.right_notebook.add(history_tab_frame, text=self._t("history"))

        # History tab uses PanedWindow for resizable split
        history_paned = ttk.PanedWindow(history_tab_frame, orient=tk.VERTICAL)
        history_paned.pack(fill=tk.BOTH, expand=True)

        history_top = ttk.Frame(history_paned)
        history_paned.add(history_top, weight=6)

        history_cols = ("commit_author", "commit_date", "commit_message")
        self.history_tree = ttk.Treeview(history_top, columns=history_cols, show="headings")
        self.history_tree.heading("commit_author", text=self._t("commit_author"))
        self.history_tree.heading("commit_date", text=self._t("commit_date"))
        self.history_tree.heading("commit_message", text=self._t("commit_message"))
        self.history_tree.column("commit_author", width=120, anchor="center")
        self.history_tree.column("commit_date", width=160, anchor="center")
        self.history_tree.column("commit_message", width=400, anchor="w")
        hy = ttk.Scrollbar(history_top, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=hy.set)
        hy.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_tree.pack(fill=tk.BOTH, expand=True)
        self.history_tree.bind("<<TreeviewSelect>>", self.on_history_select)
        self.history_tree.bind("<Button-3>", self.on_history_right_click)

        # Diff detail area (bottom pane of history PanedWindow)
        history_bottom = ttk.Frame(history_paned)
        history_paned.add(history_bottom, weight=4)

        self.history_diff_text = tk.Text(history_bottom, height=10, wrap=tk.WORD, state=tk.DISABLED)
        hd_sb = ttk.Scrollbar(history_bottom, orient=tk.VERTICAL, command=self.history_diff_text.yview)
        self.history_diff_text.configure(yscrollcommand=hd_sb.set)
        hd_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_diff_text.pack(fill=tk.BOTH, expand=True)

        # Refresh history when switching to history tab
        self.right_notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # Time report (bottom pane of vertical PanedWindow)
        report_frame = ttk.Frame(self.right_vpaned)
        self.right_vpaned.add(report_frame, weight=3)
        report_label = ttk.Label(report_frame, text=self._t("time_report"))
        report_label.pack(anchor=tk.W, pady=(2, 2))

        # Report mode selector
        report_mode_frame = ttk.Frame(report_frame)
        report_mode_frame.pack(fill=tk.X, pady=(0, 2))
        self.report_mode_label = ttk.Label(report_mode_frame, text=self._t("report_mode"))
        self.report_mode_label.pack(side=tk.LEFT, padx=(0, 4))
        self.report_mode_combo = ttk.Combobox(report_mode_frame, state="readonly", width=20)
        self.report_mode_combo["values"] = [
            self._t("report_by_project"),
            self._t("report_by_milestone"),
            self._t("report_by_plan"),
            self._t("report_by_tag"),
        ]
        self.report_mode_combo.current(0)
        self.report_mode_combo.pack(side=tk.LEFT, padx=2)
        self.report_mode_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_report())

        cols = ("group", "executor", "hours", "days", "percentage")
        self.report_tree = ttk.Treeview(report_frame, columns=cols, show="headings", height=5)
        self.report_tree.heading("group", text=self._t("group_col"))
        self.report_tree.heading("executor", text=self._t("executor"))
        self.report_tree.heading("hours", text=self._t("total_hours"))
        self.report_tree.heading("days", text=self._t("total_days"))
        self.report_tree.heading("percentage", text=self._t("percentage"))
        self.report_tree.column("group", width=0, stretch=False, minwidth=0)
        self.report_tree.column("executor", width=140, anchor="center")
        self.report_tree.column("hours", width=90, anchor="center")
        self.report_tree.column("days", width=90, anchor="center")
        self.report_tree.column("percentage", width=80, anchor="center")
        self.report_tree.pack(fill=tk.BOTH, expand=True, pady=(0, 4))
        self.report_tree.tag_configure("group_header", font=("", self.config.font_size, "bold"), background="#d0d0e8")

        # Status bar
        self.status_var = tk.StringVar(value=f"GanttPilot v{VERSION}")
        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).pack(fill=tk.X, side=tk.BOTTOM)

        self.update_fonts()

    # ── Right-click context menu ─────────────────────────────
    def on_tree_right_click(self, event):
        item = self.tree.identify_row(event.y)
        menu = tk.Menu(self.root, tearoff=0)

        if not item:
            # Right-click on empty area
            menu.add_command(label=f"+ {self._t('project')}", command=self.add_project)
            menu.add_separator()
            menu.add_command(label=self._t("load_example"), command=self.load_example)
            menu.add_separator()
            menu.add_command(label=self._t("push"), command=self.do_sync, accelerator=self._accel("sync"))
            menu.add_command(label=self._t("pull"), command=self.do_pull)
            menu.add_command(label=self._t("refresh"), command=self._full_refresh, accelerator=self._accel("refresh"))
        else:
            self.tree.selection_set(item)
            values = self.tree.item(item, "values")
            if not values:
                return
            kind = values[0]

            if kind == "project":
                proj_name = values[1]
                menu.add_command(label=f"✏ {self._t('edit_project')}", command=self.edit_project, accelerator=self._accel("edit"))
                menu.add_command(label=f"🔗 {self._t('git_config')}", command=self.config_project_git)
                menu.add_separator()
                menu.add_command(label=f"📋 {self._t('copy')}", command=self.toolbar_copy, accelerator=self._accel("copy"))
                menu.add_command(label=f"⧉ {self._t('duplicate')}", command=self.toolbar_duplicate, accelerator=self._accel("duplicate"))
                menu.add_separator()
                menu.add_command(label=self._t("report"), command=self.generate_report)
                menu.add_command(label=self._t("push"), command=self.do_sync, accelerator=self._accel("sync"))
                menu.add_command(label=self._t("pull"), command=self.do_pull)
                menu.add_command(label=self._t("refresh"), command=self._full_refresh, accelerator=self._accel("refresh"))
                menu.add_separator()
                menu.add_command(label=self._t("delete"), command=self.delete_selected, accelerator=self._accel("delete"))

            elif kind == "req_analysis":
                menu.add_command(label=f"+ {self._t('add_requirement')}", command=self.add_requirement, accelerator=self._accel("add"))
                if self._can_paste_here(kind):
                    menu.add_separator()
                    menu.add_command(label=f"📌 {self._t('paste')}", command=self.toolbar_paste, accelerator=self._accel("paste"))

            elif kind == "requirement":
                menu.add_command(label=f"+ {self._t('add_task')}", command=self.add_task, accelerator=self._accel("add"))
                menu.add_separator()
                menu.add_command(label=f"✏ {self._t('edit_requirement')}", command=self.edit_requirement, accelerator=self._accel("edit"))
                menu.add_separator()
                menu.add_command(label=f"📋 {self._t('copy')}", command=self.toolbar_copy, accelerator=self._accel("copy"))
                if self._can_paste_here(kind):
                    menu.add_command(label=f"📌 {self._t('paste')}", command=self.toolbar_paste, accelerator=self._accel("paste"))
                menu.add_command(label=f"⧉ {self._t('duplicate')}", command=self.toolbar_duplicate, accelerator=self._accel("duplicate"))
                menu.add_separator()
                menu.add_command(label=self._t("delete"), command=self.delete_selected, accelerator=self._accel("delete"))

            elif kind == "task":
                menu.add_command(label=f"✏ {self._t('edit_task')}", command=self.edit_task, accelerator=self._accel("edit"))
                menu.add_separator()
                menu.add_command(label=f"📋 {self._t('copy')}", command=self.toolbar_copy, accelerator=self._accel("copy"))
                menu.add_command(label=f"⧉ {self._t('duplicate')}", command=self.toolbar_duplicate, accelerator=self._accel("duplicate"))
                menu.add_separator()
                menu.add_command(label=self._t("delete"), command=self.delete_selected, accelerator=self._accel("delete"))

            elif kind == "plan_execution":
                menu.add_command(label=f"+ {self._t('milestone')}", command=self.add_milestone, accelerator=self._accel("add"))
                if self._can_paste_here(kind):
                    menu.add_separator()
                    menu.add_command(label=f"📌 {self._t('paste')}", command=self.toolbar_paste, accelerator=self._accel("paste"))

            elif kind == "milestone":
                menu.add_command(label=f"+ {self._t('plan')}", command=self.add_plan, accelerator=self._accel("add"))
                menu.add_separator()
                menu.add_command(label=f"✏ {self._t('edit_milestone')}", command=self.edit_milestone, accelerator=self._accel("edit"))
                menu.add_command(label="🎨 " + self._t("color"), command=self.pick_color_milestone)
                menu.add_separator()
                menu.add_command(label=f"📋 {self._t('copy')}", command=self.toolbar_copy, accelerator=self._accel("copy"))
                if self._can_paste_here(kind):
                    menu.add_command(label=f"📌 {self._t('paste')}", command=self.toolbar_paste, accelerator=self._accel("paste"))
                menu.add_command(label=f"⧉ {self._t('duplicate')}", command=self.toolbar_duplicate, accelerator=self._accel("duplicate"))
                menu.add_separator()
                menu.add_command(label=self._t("delete"), command=self.delete_selected, accelerator=self._accel("delete"))

            elif kind == "plan":
                menu.add_command(label=f"+ {self._t('activity')}", command=self.add_activity, accelerator=self._accel("add"))
                menu.add_separator()
                menu.add_command(label=f"✏ {self._t('content')}", command=self.edit_plan, accelerator=self._accel("edit"))
                menu.add_command(label="🎨 " + self._t("color"), command=self.pick_color_plan)
                menu.add_separator()
                menu.add_command(label=f"📋 {self._t('copy')}", command=self.toolbar_copy, accelerator=self._accel("copy"))
                if self._can_paste_here(kind):
                    menu.add_command(label=f"📌 {self._t('paste')}", command=self.toolbar_paste, accelerator=self._accel("paste"))
                menu.add_command(label=f"⧉ {self._t('duplicate')}", command=self.toolbar_duplicate, accelerator=self._accel("duplicate"))
                menu.add_separator()
                menu.add_command(label=self._t("finish"), command=self.finish_selected_plan)
                menu.add_command(label=self._t("reopen"), command=self.reopen_selected_plan)
                menu.add_command(label=self._t("set_progress"), command=self.set_progress)
                menu.add_separator()
                menu.add_command(label=self._t("delete"), command=self.delete_selected, accelerator=self._accel("delete"))

            elif kind == "activity":
                menu.add_command(label=f"✏ {self._t('edit_activity')}", command=self.edit_activity, accelerator=self._accel("edit"))
                menu.add_separator()
                menu.add_command(label=f"📋 {self._t('copy')}", command=self.toolbar_copy, accelerator=self._accel("copy"))
                menu.add_command(label=f"⧉ {self._t('duplicate')}", command=self.toolbar_duplicate, accelerator=self._accel("duplicate"))
                menu.add_separator()
                menu.add_command(label=self._t("delete"), command=self.delete_selected, accelerator=self._accel("delete"))

        menu.tk_popup(event.x_root, event.y_root)

    # ── Tree data ────────────────────────────────────────────
    def refresh_project_list(self):
        # Save expanded state and selection before refresh
        expanded = set()
        selected_values = None
        sel = self.tree.selection()
        if sel:
            selected_values = self.tree.item(sel[0], "values")
        for item in self._iter_tree_items(""):
            if self.tree.item(item, "open"):
                vals = self.tree.item(item, "values")
                if vals:
                    expanded.add(tuple(vals))

        self.tree.delete(*self.tree.get_children())
        for proj in self.store.list_projects():
            pn = self.tree.insert("", tk.END, text=f"📁 {proj['name']}",
                                  values=("project", proj["name"]), open=True)

            # ── 📋 需求分析 (Requirement Analysis) ──
            ra_node = self.tree.insert(pn, tk.END,
                text=f"📋 {self._t('requirement_analysis')}",
                values=("req_analysis", proj["name"]))
            for req in proj.get("requirements", []):
                req_text = format_requirement_display(req.get("category", ""), req.get("subject", ""))
                req_node = self.tree.insert(ra_node, tk.END,
                    text=f"📝 {req_text}",
                    values=("requirement", proj["name"], req["id"]))
                for task in req.get("tasks", []):
                    effort = task.get("effort_days", 0)
                    task_text = f"🔧 {task['subject']} ({effort}d)"
                    self.tree.insert(req_node, tk.END, text=task_text,
                        values=("task", proj["name"], req["id"], task["id"]))

            # ── 📊 计划执行 (Plan Execution) ──
            pe_node = self.tree.insert(pn, tk.END,
                text=f"📊 {self._t('plan_execution')}",
                values=("plan_execution", proj["name"]))
            for ms in proj.get("milestones", []):
                dl = f" [{ms['deadline']}]" if ms.get("deadline") else ""
                mn = self.tree.insert(pe_node, tk.END, text=f"📌 {ms['name']}{dl}",
                                      values=("milestone", proj["name"], ms["name"]))
                for plan in ms.get("plans", []):
                    icon = "✅" if plan["status"] == "finished" else "📋"
                    txt = f"{icon} {plan['content']} ({plan['executor']}) [{plan['start_date']}-{plan['end_date']}]"
                    plan_n = self.tree.insert(mn, tk.END, text=txt,
                                             values=("plan", proj["name"], ms["name"], plan["id"]))
                    for act in plan.get("activities", []):
                        tag = act.get("tag", "")
                        hours = act.get("hours", 0)
                        tag_part = f" [{tag}]" if tag else ""
                        atxt = f"⏱ {act['date']} {act['executor']} {hours}h - {act['content']}{tag_part}"
                        self.tree.insert(plan_n, tk.END, text=atxt,
                                         values=("activity", proj["name"], ms["name"], plan["id"], act["id"]))

        # Restore expanded state
        for item in self._iter_tree_items(""):
            vals = self.tree.item(item, "values")
            if vals and tuple(vals) in expanded:
                self.tree.item(item, open=True)

        # Restore selection
        if selected_values:
            for item in self._iter_tree_items(""):
                if self.tree.item(item, "values") == selected_values:
                    self.tree.selection_set(item)
                    self.tree.see(item)
                    break

    def _iter_tree_items(self, parent):
        """Recursively iterate all tree items."""
        for item in self.tree.get_children(parent):
            yield item
            yield from self._iter_tree_items(item)

    def on_tree_select(self, event):
        sel = self.tree.selection()
        if not sel:
            self._update_toolbar_state(None, None)
            return
        values = self.tree.item(sel[0], "values")
        if not values:
            self._update_toolbar_state(None, None)
            return
        kind = values[0]
        # Update toolbar state based on selected node type
        self._update_toolbar_state(kind, sel[0])
        proj_name = values[1] if len(values) >= 2 else None
        if proj_name and proj_name != self.current_project:
            self.current_project = proj_name
            self.refresh_branch_selector()
            self.check_remote_updates()
            self.refresh_gantt()
            self.refresh_time_report()
            self.refresh_history()

    def _update_toolbar_state(self, kind, item):
        """Update toolbar button enabled/disabled state based on selected node type."""
        state = TOOLBAR_STATE.get(kind, TOOLBAR_STATE[None])
        self.tb_add_btn.configure(state=tk.NORMAL if state["add"] else tk.DISABLED)
        self.tb_edit_btn.configure(state=tk.NORMAL if state["edit"] else tk.DISABLED)
        self.tb_delete_btn.configure(state=tk.NORMAL if state["delete"] else tk.DISABLED)

        # For up/down, check if node is first/last among siblings
        up_enabled = state["up"]
        down_enabled = state["down"]
        if item and (up_enabled or down_enabled):
            parent = self.tree.parent(item)
            siblings = self.tree.get_children(parent)
            if siblings:
                idx = list(siblings).index(item)
                if idx == 0:
                    up_enabled = False
                if idx >= len(siblings) - 1:
                    down_enabled = False
        self.tb_up_btn.configure(state=tk.NORMAL if up_enabled else tk.DISABLED)
        self.tb_down_btn.configure(state=tk.NORMAL if down_enabled else tk.DISABLED)

        # Duplicate / Copy / Paste
        self.tb_dup_btn.configure(state=tk.NORMAL if state["dup"] else tk.DISABLED)
        self.tb_copy_btn.configure(state=tk.NORMAL if state["copy"] else tk.DISABLED)
        # Paste enabled only if clipboard type is compatible with current selection
        paste_enabled = state["paste"] and self._can_paste_here(kind)
        self.tb_paste_btn.configure(state=tk.NORMAL if paste_enabled else tk.DISABLED)

    def _full_refresh(self):
        self.store.load()
        self.refresh_project_list()
        self.refresh_branch_selector()
        self.check_remote_updates()
        # Re-apply the selected branch view (handles both current and non-current branches)
        selected = self.branch_selector.get()
        if selected and self.current_project:
            self.on_branch_changed()
        else:
            self.refresh_gantt()
            self.refresh_time_report()
            self.refresh_history()

    def refresh_gantt(self):
        if not self.current_project:
            return
        proj = self.store.get_project(self.current_project)
        if not proj:
            return
        backend = CanvasBackend(self.gantt_canvas)
        renderer = GanttRenderer(backend, proj, self.lang, self.gantt_zoom,
                                 self.config.get("compress_threshold", 300),
                                 self.config.get("max_chart_width", 4000))
        renderer.draw()
        self.status_var.set(f"{self._t('gantt_chart')}: {self.current_project}")

    def refresh_time_report(self):
        self.refresh_report()

    def refresh_report(self):
        """Refresh the report tree based on the selected report mode."""
        for item in self.report_tree.get_children():
            self.report_tree.delete(item)
        if not self.current_project:
            return

        modes = self.report_mode_combo["values"]
        selected = self.report_mode_combo.get()

        # Determine mode index (fallback to 0 = by project)
        try:
            mode_idx = list(modes).index(selected)
        except ValueError:
            mode_idx = 0

        # Show/hide group column based on mode
        if mode_idx == 0:
            self.report_tree.column("group", width=0, stretch=False, minwidth=0)
        else:
            self.report_tree.column("group", width=140, stretch=True, minwidth=80)

        if mode_idx == 0:
            # By Project — flat executor list with total row on top
            report = self.store.get_time_report(self.current_project)
            # Calculate project total
            proj_total_hours = sum(data['hours'] for ex, data in report.items() if ex != "by_tag")
            proj_total_days = round(proj_total_hours / 8.0, 2)
            # Insert total row first
            self.report_tree.insert("", tk.END,
                                    values=("", self._t("group_total"), f"{proj_total_hours:.1f}", f"{proj_total_days:.2f}", ""),
                                    tags=("group_header",))
            for ex, data in sorted(report.items()):
                if ex == "by_tag":
                    continue
                pct = f"{data['hours'] / proj_total_hours * 100:.1f}%" if proj_total_hours > 0 else "0.0%"
                self.report_tree.insert("", tk.END, values=("", ex, f"{data['hours']:.1f}", f"{data['days']:.2f}", pct))
        else:
            # Grouped modes
            if mode_idx == 1:
                report = self.store.get_time_report_by_milestone(self.current_project)
            elif mode_idx == 2:
                report = self.store.get_time_report_by_plan(self.current_project)
            else:
                report = self.store.get_time_report_by_tag(self.current_project)

            for group_name, executors in sorted(report.items()):
                label = group_name if group_name else "-"
                # Calculate group total
                group_total_hours = sum(data['hours'] for data in executors.values())
                group_total_days = round(group_total_hours / 8.0, 2)
                # Group header row with total
                self.report_tree.insert("", tk.END,
                                        values=(label, self._t("group_total"), f"{group_total_hours:.1f}", f"{group_total_days:.2f}", ""),
                                        tags=("group_header",))
                for ex, data in sorted(executors.items()):
                    pct = f"{data['hours'] / group_total_hours * 100:.1f}%" if group_total_hours > 0 else "0.0%"
                    self.report_tree.insert("", tk.END, values=("", ex, f"{data['hours']:.1f}", f"{data['days']:.2f}", pct))

    # ── Tracking tab ──────────────────────────────────────────
    def refresh_tracking(self):
        """Refresh the requirement tracking tab with current project data."""
        for item in self.tracking_tree.get_children():
            self.tracking_tree.delete(item)
        if not self.current_project:
            return
        proj = self.store.get_project(self.current_project)
        if not proj:
            return
        rows = build_tracking_data(proj)
        for row in rows:
            if row["kind"] == "requirement":
                self.tracking_tree.insert(
                    "", tk.END,
                    values=(row["req_category"], row["req_subject"], "", "", "", "", ""),
                    tags=("req_header",),
                )
            else:
                self.tracking_tree.insert(
                    "", tk.END,
                    values=("", "", row["task_subject"], row["effort_days"],
                            row["linked_plan"], row["plan_progress"],
                            row["actual_hours"]),
                )

    # ── History tab ─────────────────────────────────────────
    def _on_tab_changed(self, event):
        """Refresh content when user switches tabs."""
        try:
            idx = self.right_notebook.index(self.right_notebook.select())
            if idx == 1:  # Tracking tab
                self.refresh_tracking()
            elif idx == 2:  # History tab
                self.refresh_history()
        except Exception:
            pass

    def refresh_history(self):
        """Refresh the history tree with git log from the current project."""
        # Clear existing items
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        # Clear diff area
        self.history_diff_text.configure(state=tk.NORMAL)
        self.history_diff_text.delete("1.0", tk.END)
        self.history_diff_text.configure(state=tk.DISABLED)

        if not self.current_project:
            self.history_tree.insert("", tk.END, values=("", "", self._t("no_history")))
            return

        proj = self.store.get_project(self.current_project)
        if not proj:
            self.history_tree.insert("", tk.END, values=("", "", self._t("no_history")))
            return

        try:
            gs = self._get_project_git(proj)
            if not gs.is_repo():
                self.history_tree.insert("", tk.END, values=("", "", self._t("no_history")))
                return

            records = gs.get_log()
            if not records:
                self.history_tree.insert("", tk.END, values=("", "", self._t("no_history")))
                return

            for rec in records:
                self.history_tree.insert("", tk.END,
                    values=(rec.get("author", ""), rec.get("date", ""), rec.get("message", "")),
                    tags=(rec.get("hash", ""),))
        except Exception:
            self.history_tree.insert("", tk.END, values=("", "", self._t("no_history")))

    # ── Branch selector ────────────────────────────────────
    def refresh_branch_selector(self):
        """Refresh the branch selector combobox for the current project."""
        if not self.current_project:
            self.branch_selector.set("")
            self.branch_selector["values"] = []
            self.branch_selector.configure(state="disabled")
            return

        proj = self.store.get_project(self.current_project)
        if not proj:
            self.branch_selector.set("")
            self.branch_selector["values"] = []
            self.branch_selector.configure(state="disabled")
            return

        try:
            gs = self._get_project_git(proj)
            if not gs.is_repo():
                self.branch_selector.set("")
                self.branch_selector["values"] = []
                self.branch_selector.configure(state="disabled")
                return

            branches = gs.list_branches()
            current = gs.get_current_branch()
            # Store actual branch names for lookup
            self._branch_actual_names = branches
            # Build display names: remote branches get a prefix
            remote_prefix = self._t("remote_prefix")
            display_names = []
            for b in branches:
                if b.startswith("origin/"):
                    display_names.append(f"{remote_prefix} {b}")
                else:
                    display_names.append(b)
            self.branch_selector.configure(state="readonly")
            self.branch_selector["values"] = display_names
            if current and current in branches:
                idx = branches.index(current)
                self.branch_selector.set(display_names[idx])
            elif display_names:
                self.branch_selector.set(display_names[0])
            else:
                self.branch_selector.set("")
        except Exception:
            self.branch_selector.set("")
            self.branch_selector["values"] = []
            self.branch_selector.configure(state="disabled")

    def check_remote_updates(self):
        """Check if remote main branch has new commits and show/hide the update banner."""
        if not self.current_project:
            self.update_banner.pack_forget()
            return

        proj = self.store.get_project(self.current_project)
        if not proj or not proj.get("remote_url"):
            self.update_banner.pack_forget()
            return

        try:
            gs = self._get_project_git(proj)
            if not gs.is_repo():
                self.update_banner.pack_forget()
                return

            if gs.has_remote_updates():
                # Show banner between branch_frame and notebook
                self.update_banner.pack(fill=tk.X, pady=(0, 2), before=self.right_vpaned)
            else:
                self.update_banner.pack_forget()
        except Exception:
            self.update_banner.pack_forget()

    def do_manual_rebase(self):
        """Handle click on the sync-main button in the update banner."""
        if not self.current_project:
            return

        proj = self.store.get_project(self.current_project)
        if not proj:
            return

        try:
            gs = self._get_project_git(proj)
            gs.manual_rebase()
            # Success — hide banner, refresh views
            self.update_banner.pack_forget()
            self._full_refresh()
            self.status_var.set(self._t("rebase_success"))
        except RuntimeError:
            messagebox.showerror(self._t("error"), self._t("rebase_conflict"))

    def on_branch_changed(self, event=None):
        """Handle branch selection change — load data from selected branch."""
        selected = self.branch_selector.get()
        if not selected or not self.current_project:
            return

        # Strip remote prefix to get actual branch name
        remote_prefix = self._t("remote_prefix") + " "
        if selected.startswith(remote_prefix):
            selected = selected[len(remote_prefix):]

        proj = self.store.get_project(self.current_project)
        if not proj:
            return

        try:
            gs = self._get_project_git(proj)
            current = gs.get_current_branch()

            if selected == current:
                # Current working branch — load data normally
                self.store.load()
                self.refresh_gantt()
                self.refresh_time_report()
                self.refresh_history()
                return

            # Different branch — read project.json from that branch
            # For local branches, prefer origin/ version if available (local main
            # is rarely updated directly; origin/main is fetched and up-to-date).
            read_branch = selected
            if not selected.startswith("origin/"):
                remote_ref = f"origin/{selected}"
                remote_content = gs.read_file_from_branch(remote_ref, "project.json")
                if remote_content is not None:
                    read_branch = remote_ref

            content = gs.read_file_from_branch(read_branch, "project.json")
            if content is None:
                self.status_var.set(f"Cannot load project.json from branch: {selected}")
                return

            branch_proj = json.loads(content)
            # Temporarily replace project data for display
            backend = CanvasBackend(self.gantt_canvas)
            renderer = GanttRenderer(backend, branch_proj, self.lang, self.gantt_zoom,
                                     self.config.get("compress_threshold", 300),
                                     self.config.get("max_chart_width", 4000))
            renderer.draw()

            # Refresh history for the selected branch
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)
            self.history_diff_text.configure(state=tk.NORMAL)
            self.history_diff_text.delete("1.0", tk.END)
            self.history_diff_text.configure(state=tk.DISABLED)

            records = gs.get_log(branch=selected)
            if not records:
                self.history_tree.insert("", tk.END, values=("", "", self._t("no_history")))
            else:
                for rec in records:
                    self.history_tree.insert("", tk.END,
                        values=(rec.get("author", ""), rec.get("date", ""), rec.get("message", "")),
                        tags=(rec.get("hash", ""),))

            # Refresh time report from branch data
            for item in self.report_tree.get_children():
                self.report_tree.delete(item)
            # Calculate time report from branch project data
            report = {}
            tag_hours = {}
            for ms in branch_proj.get("milestones", []):
                for plan in ms.get("plans", []):
                    for act in plan.get("activities", []):
                        ex = act.get("executor", "")
                        h = float(act.get("hours", 0))
                        if ex not in report:
                            report[ex] = {"hours": 0, "days": 0}
                        report[ex]["hours"] += h
                        report[ex]["days"] = report[ex]["hours"] / 8.0
                        tag = act.get("tag", "")
                        if tag not in tag_hours:
                            tag_hours[tag] = 0
                        tag_hours[tag] += h
            for ex, data in sorted(report.items()):
                branch_total = sum(d['hours'] for d in report.values())
                pct = f"{data['hours'] / branch_total * 100:.1f}%" if branch_total > 0 else "0.0%"
                self.report_tree.insert("", tk.END, values=("", ex, f"{data['hours']:.1f}", f"{data['days']:.2f}", pct))
            if tag_hours:
                self.report_tree.insert("", tk.END, values=("", "", "", "", ""))
                self.report_tree.insert("", tk.END, values=(self._t("tag_summary"), "", "", "", ""))
                for tag, hours in sorted(tag_hours.items()):
                    label = tag if tag else "-"
                    self.report_tree.insert("", tk.END, values=(f"  [{label}]", "", f"{hours:.1f}", f"{hours / 8.0:.2f}", ""))

            self.status_var.set(f"{self._t('gantt_chart')}: {self.current_project} ({selected})")
        except Exception as e:
            self.status_var.set(f"Branch load error: {e}")

    def on_history_select(self, event):
        """Show diff detail when a commit is selected in the history tree."""
        sel = self.history_tree.selection()
        if not sel:
            return
        tags = self.history_tree.item(sel[0], "tags")
        commit_hash = tags[0] if tags else ""
        if not commit_hash or not self.current_project:
            return

        proj = self.store.get_project(self.current_project)
        if not proj:
            return

        try:
            gs = self._get_project_git(proj)
            diff_text = gs.get_commit_diff(commit_hash)
        except Exception:
            diff_text = ""

        self.history_diff_text.configure(state=tk.NORMAL)
        self.history_diff_text.delete("1.0", tk.END)
        self.history_diff_text.insert("1.0", diff_text)
        self.history_diff_text.configure(state=tk.DISABLED)

    def on_history_right_click(self, event):
        """Show context menu on history tree right-click."""
        item = self.history_tree.identify_row(event.y)
        if not item or not self.current_project:
            return
        self.history_tree.selection_set(item)
        tags = self.history_tree.item(item, "tags")
        commit_hash = tags[0] if tags else ""
        if not commit_hash:
            return
        message = self.history_tree.item(item, "values")[2] if self.history_tree.item(item, "values") else ""

        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(
            label=self._t("revert_commit"),
            command=lambda: self._do_revert_commit(commit_hash, message))
        menu.add_command(
            label=self._t("reset_to_here"),
            command=lambda: self._do_reset_to_commit(commit_hash, message))
        menu.tk_popup(event.x_root, event.y_root)

    def _do_reset_to_commit(self, commit_hash, message):
        """Reset current branch to the selected commit."""
        if not messagebox.askyesno(self._t("warning"), self._t("confirm_reset", message)):
            return
        proj = self.store.get_project(self.current_project)
        if not proj:
            return
        try:
            gs = self._get_project_git(proj)
            gs.reset_to_commit(commit_hash)
            self.store.load()
            self.refresh_project_list()
            self.refresh_gantt()
            self.refresh_time_report()
            self.refresh_history()
            self.status_var.set(self._t("reset_done", commit_hash[:7]))
        except Exception as e:
            messagebox.showerror(self._t("error"), self._t("reset_failed", str(e)))

    def _do_revert_commit(self, commit_hash, message):
        """Revert a specific commit (create inverse commit)."""
        if not messagebox.askyesno(self._t("warning"), self._t("confirm_revert", message)):
            return
        proj = self.store.get_project(self.current_project)
        if not proj:
            return
        try:
            gs = self._get_project_git(proj)
            gs.revert_commit(commit_hash)
            self.store.load()
            self.refresh_project_list()
            self.refresh_gantt()
            self.refresh_time_report()
            self.refresh_history()
            self.status_var.set(self._t("revert_done", commit_hash[:7]))
        except Exception as e:
            messagebox.showerror(self._t("error"), self._t("revert_failed", str(e)))

    # ── CRUD via context menu ────────────────────────────────
    def add_project(self):
        if self._has_active_dialog():
            return
        dlg = ProjectCreateDialog(self.root, self._t, self.lang)
        self._active_dialog = dlg.top
        self.root.wait_window(dlg.top)
        self._active_dialog = None
        if not dlg.result:
            return
        name = dlg.result["name"]
        description = dlg.result.get("description", "")
        remote_url = dlg.result.get("remote_url", "")
        remote_branch = dlg.result.get("remote_branch", "main")
        remote_username = dlg.result.get("remote_username", "")
        remote_password = dlg.result.get("remote_password", "")
        committer_name = dlg.result.get("committer_name", "")
        committer_email = dlg.result.get("committer_email", "")
        priv_branch = dlg.result.get("priv_branch", "")
        self.undo_manager.save_snapshot()
        if remote_url:
            # Clone from remote
            self.status_var.set(self._t("cloning"))
            self.root.update()
            # Clone to a temp name first, then reconcile with project.json name
            tmp_dir = os.path.join(self.config.data_dir, f"_clone_tmp_{name}")
            try:
                # Clean up any leftover temp dir from a previous failed clone
                if os.path.exists(tmp_dir):
                    _force_rmtree(tmp_dir)
                gs = GitSync(tmp_dir, remote_url,
                             username=remote_username,
                             password=remote_password,
                             main_branch=remote_branch,
                             committer_name=committer_name,
                             committer_email=committer_email,
                             priv_branch=priv_branch)
                gs.clone_repo(remote_url, tmp_dir, remote_branch)
                # Read the actual project name from cloned project.json
                pj_file = os.path.join(tmp_dir, "project.json")
                if os.path.exists(pj_file):
                    with open(pj_file, "r", encoding="utf-8") as f:
                        pj_data = json.load(f)
                    real_name = pj_data.get("name", name)
                    # Update project.json with full Git config fields
                    pj_data["remote_url"] = remote_url
                    pj_data["remote_username"] = remote_username
                    pj_data["remote_password"] = remote_password
                    pj_data["remote_branch"] = remote_branch
                    pj_data["committer_name"] = committer_name
                    pj_data["committer_email"] = committer_email
                    pj_data["priv_branch"] = priv_branch
                    with open(pj_file, "w", encoding="utf-8") as f:
                        json.dump(pj_data, f, ensure_ascii=False, indent=2)
                else:
                    # Empty repo — create initial project.json
                    real_name = name
                    from ganttpilot_core import _new_id
                    pj_data = {
                        "id": _new_id(),
                        "name": name,
                        "description": description,
                        "remote_url": remote_url,
                        "remote_username": remote_username,
                        "remote_password": remote_password,
                        "remote_branch": remote_branch,
                        "committer_name": committer_name,
                        "committer_email": committer_email,
                        "priv_branch": priv_branch,
                        "requirements": [],
                        "milestones": [],
                    }
                    with open(pj_file, "w", encoding="utf-8") as f:
                        json.dump(pj_data, f, ensure_ascii=False, indent=2)
                    # Commit the new project.json
                    gs_tmp = GitSync(tmp_dir, remote_url,
                                     username=remote_username,
                                     password=remote_password,
                                     main_branch=remote_branch,
                                     committer_name=committer_name,
                                     committer_email=committer_email,
                                     priv_branch=priv_branch)
                    gs_tmp.init_repo()
                    gs_tmp.commit(f"Initialize project: {name}")
                # Rename temp dir to the real project name
                final_dir = os.path.join(self.config.data_dir, real_name)
                if os.path.exists(final_dir):
                    # Check if it's an orphaned directory (no matching project in store)
                    if not self.store.get_project(real_name):
                        _force_rmtree(final_dir)
                    else:
                        _force_rmtree(tmp_dir)
                        messagebox.showerror(self._t("error"), self._t("name_duplicate", real_name))
                        return
                shutil.move(tmp_dir, final_dir)
                self.store.load()
                self.refresh_project_list()
                self.refresh_gantt()
                self.status_var.set(self._t("project_added", real_name))
                self._update_undo_redo_buttons()
            except Exception as e:
                # Clean up temp dir on failure
                if os.path.exists(tmp_dir):
                    _force_rmtree(tmp_dir)
                messagebox.showerror(self._t("error"), self._t("clone_failed", str(e)))
                self.status_var.set(self._t("clone_failed", str(e)))
        else:
            result = self.store.add_project(
                name, description=description,
                remote_branch=remote_branch,
                committer_name=committer_name,
                committer_email=committer_email,
                priv_branch=priv_branch,
            )
            if result:
                self._commit(f"Add project: {name}")
                self.refresh_project_list()
                self.status_var.set(self._t("project_added", name))
                self._update_undo_redo_buttons()

    def add_milestone(self):
        proj = self._get_selected_project()
        if not proj:
            return
        if self._has_active_dialog():
            return
        dlg = MilestoneCreateDialog(self.root, self._t, self.lang)
        self._active_dialog = dlg.top
        self.root.wait_window(dlg.top)
        self._active_dialog = None
        if not dlg.result:
            return
        name = dlg.result["name"]
        desc = dlg.result.get("description", "")
        color = dlg.result.get("color", "")
        deadline = dlg.result.get("deadline", "")
        self.undo_manager.save_snapshot()
        result = self.store.add_milestone(proj, name, desc, color, deadline)
        if result:
            self._commit(f"Add milestone: {name} to {proj}")
            self.refresh_project_list()
            self.refresh_gantt()
            self._update_undo_redo_buttons()

    def add_plan(self):
        proj, ms = self._get_selected_project_milestone()
        if not proj or not ms:
            return
        if self._has_active_dialog():
            return
        dlg = PlanDialog(self.root, self._t, self.lang, project_name=proj, store=self.store)
        self._active_dialog = dlg.top
        self.root.wait_window(dlg.top)
        self._active_dialog = None
        if dlg.result:
            r = dlg.result
            self.undo_manager.save_snapshot()
            result = self.store.add_plan(proj, ms, r["content"], r["executor"],
                                         r["start_date"], r["end_date"],
                                         r["skip_non_workdays"], r["skip_dates"], r.get("color", ""),
                                         linked_task_id=r.get("linked_task_id", ""))
            if result:
                self._commit(f"Add plan: {r['content']} to {ms}/{proj}")
                self.refresh_project_list()
                self.refresh_gantt()
                self.refresh_time_report()
                self._update_undo_redo_buttons()

    def add_activity(self):
        proj, ms, plan_id = self._get_selected_plan()
        if not plan_id:
            return
        # Get project tags for tag selection
        proj_data = self.store.get_project(proj)
        project_tags = proj_data.get("tags", []) if proj_data else []
        if self._has_active_dialog():
            return
        dlg = ActivityDialog(self.root, self._t, self.lang, project_tags=project_tags)
        self._active_dialog = dlg.top
        self.root.wait_window(dlg.top)
        self._active_dialog = None
        if dlg.result:
            r = dlg.result
            self.undo_manager.save_snapshot()
            result = self.store.add_activity(proj, ms, plan_id, r["executor"], r["date"], r["hours"], r["content"],
                                             time_slots=r.get("time_slots", ""), tag=r.get("tag", ""),
                                             description=r.get("description", ""))
            if result:
                self._commit(f"Add activity: {r['content']}")
                self.refresh_project_list()
                self.refresh_time_report()
                self._update_undo_redo_buttons()

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        if not values:
            return
        kind = values[0]
        text = self.tree.item(sel[0], "text")
        if not messagebox.askyesno(self._t("warning"), self._t("confirm_delete", text)):
            return
        self.undo_manager.save_snapshot()
        if kind == "project":
            proj_name = values[1]
            proj_dir = os.path.join(self.config.data_dir, proj_name)
            self.store.delete_project(proj_name)
            self.current_project = None
            # Remove project directory from disk (after clearing current_project so no git ops)
            if os.path.isdir(proj_dir):
                _force_rmtree(proj_dir)
        elif kind == "requirement":
            self.store.delete_requirement(values[1], values[2])
            self._commit(f"Delete requirement: {values[2]}")
        elif kind == "task":
            self.store.delete_task(values[1], values[2], values[3])
            self._commit(f"Delete task: {values[3]}")
        elif kind == "milestone":
            self.store.delete_milestone(values[1], values[2])
            self._commit(f"Delete milestone: {values[2]}")
        elif kind == "plan":
            self.store.delete_plan(values[1], values[2], values[3])
            self._commit(f"Delete plan: {values[3]}")
        elif kind == "activity":
            self.store.delete_activity(values[1], values[2], values[3], values[4])
            self._commit(f"Delete activity: {values[4]}")
        self.refresh_project_list()
        self.refresh_gantt()
        self.refresh_time_report()
        self._update_undo_redo_buttons()

    def finish_selected_plan(self):
        proj, ms, plan_id = self._get_selected_plan()
        if not plan_id:
            return
        if not messagebox.askyesno(self._t("warning"), self._t("confirm_finish", plan_id)):
            return
        self.undo_manager.save_snapshot()
        if self.store.finish_plan(proj, ms, plan_id):
            self._commit(f"Finish plan: {plan_id}")
            self.refresh_project_list()
            self.refresh_gantt()
            self._update_undo_redo_buttons()

    def reopen_selected_plan(self):
        proj, ms, plan_id = self._get_selected_plan()
        if not plan_id:
            return
        if not messagebox.askyesno(self._t("warning"), self._t("confirm_reopen", plan_id)):
            return
        self.undo_manager.save_snapshot()
        if self.store.reopen_plan(proj, ms, plan_id):
            self._commit(f"Reopen plan: {plan_id}")
            self.refresh_project_list()
            self.refresh_gantt()
            self._update_undo_redo_buttons()

    def set_progress(self):
        proj, ms, plan_id = self._get_selected_plan()
        if not plan_id:
            return
        if self._has_active_dialog():
            return
        dlg = ProgressDialog(self.root, self._t, self.lang)
        self._active_dialog = dlg.top
        self.root.wait_window(dlg.top)
        self._active_dialog = None
        if dlg.result is not None:
            self.undo_manager.save_snapshot()
            self.store.set_plan_progress(proj, ms, plan_id, dlg.result)
            self._commit(f"Set progress: {plan_id} -> {dlg.result}%")
            self.refresh_project_list()
            self.refresh_gantt()
            self._update_undo_redo_buttons()

    def load_example(self):
        fname = "demo_project_en.json" if self.lang == "en" else "demo_project.json"
        example_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples", fname)
        if not os.path.exists(example_path):
            messagebox.showerror(self._t("error"), self._t("file_not_found", example_path))
            return
        try:
            with open(example_path, "r", encoding="utf-8") as f:
                proj_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            messagebox.showerror(self._t("error"), str(e))
            return
        self.undo_manager.save_snapshot()
        # Check if project already exists
        existing = self.store.get_project(proj_data.get("name", ""))
        if existing:
            # Remove existing before re-importing
            self.store.delete_project(proj_data["name"])
        self.store.data["projects"].append(proj_data)
        self.store.save()
        proj_name = proj_data.get("name", "")
        self.current_project = proj_name
        self._commit(f"Load example: {proj_name}")
        self.refresh_project_list()
        self.refresh_gantt()
        self.status_var.set(self._t("example_loaded"))
        self._update_undo_redo_buttons()

    def edit_milestone(self):
        proj = self._get_selected_project()
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        if not values or values[0] != "milestone":
            return
        ms_name = values[2]
        ms = self.store._find_milestone(proj, ms_name)
        if not ms:
            return
        if self._has_active_dialog():
            return
        dlg = MilestoneEditDialog(self.root, self._t, self.lang, ms)
        self._active_dialog = dlg.top
        self.root.wait_window(dlg.top)
        self._active_dialog = None
        if dlg.result:
            new_name = dlg.result["name"]
            new_desc = dlg.result["description"]
            new_deadline = dlg.result.get("deadline", "")
            self.undo_manager.save_snapshot()
            if not self.store.update_milestone(proj, ms_name, new_name, new_desc, new_deadline):
                messagebox.showerror(self._t("error"), self._t("name_duplicate", new_name))
                return
            self._commit(f"Edit milestone: {ms_name} -> {new_name}")
            self.refresh_project_list()
            self.refresh_gantt()
            self._update_undo_redo_buttons()

    def edit_project(self):
        proj_name = self._get_selected_project()
        if not proj_name:
            return
        proj = self.store.get_project(proj_name)
        if not proj:
            return
        if self._has_active_dialog():
            return
        dlg = ProjectEditDialog(self.root, self._t, self.lang, proj)
        self._active_dialog = dlg.top
        self.root.wait_window(dlg.top)
        self._active_dialog = None
        if dlg.result:
            new_name = dlg.result["name"]
            new_desc = dlg.result.get("description", "")
            new_tags = dlg.result.get("tags", [])
            self.undo_manager.save_snapshot()
            # Update description and tags
            proj["description"] = new_desc
            proj["tags"] = new_tags
            # Rename if needed
            if new_name != proj_name:
                if not self.store.rename_project(proj_name, new_name):
                    messagebox.showerror(self._t("error"), self._t("name_duplicate", new_name))
                    return
                self.current_project = new_name
            self.store.save()
            self._commit(f"Edit project: {proj_name}")
            self.refresh_project_list()
            self.refresh_gantt()
            self._update_undo_redo_buttons()

    def edit_activity(self):
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        if not values or values[0] != "activity":
            return
        proj_name, ms_name, plan_id, act_id = values[1], values[2], values[3], values[4]
        plan = self.store._find_plan(proj_name, ms_name, plan_id)
        if not plan:
            return
        activity = None
        for a in plan.get("activities", []):
            if a["id"] == act_id:
                activity = a
                break
        if not activity:
            return
        # Get project tags for tag selection
        proj_data = self.store.get_project(proj_name)
        project_tags = proj_data.get("tags", []) if proj_data else []
        if self._has_active_dialog():
            return
        dlg = ActivityEditDialog(self.root, self._t, self.lang, activity, project_tags=project_tags)
        self._active_dialog = dlg.top
        self.root.wait_window(dlg.top)
        self._active_dialog = None
        if dlg.result:
            r = dlg.result
            self.undo_manager.save_snapshot()
            self.store.update_activity(proj_name, ms_name, plan_id, act_id,
                                       r["executor"], r["date"], r["hours"], r["content"],
                                       time_slots=r.get("time_slots", ""), tag=r.get("tag", ""),
                                       description=r.get("description", ""))
            self._commit(f"Edit activity: {act_id}")
            self.refresh_project_list()
            self.refresh_time_report()
            self._update_undo_redo_buttons()

    def config_project_git(self):
        proj_name = self._get_selected_project()
        if not proj_name:
            return
        proj = self.store.get_project(proj_name)
        if not proj:
            return
        if self._has_active_dialog():
            return
        dlg = ProjectGitConfigDialog(self.root, self._t, self.lang, proj)
        self._active_dialog = dlg.top
        self.root.wait_window(dlg.top)
        self._active_dialog = None
        if dlg.result:
            self.undo_manager.save_snapshot()
            proj["remote_url"] = dlg.result["remote_url"]
            proj["remote_branch"] = dlg.result["remote_branch"]
            proj["remote_username"] = dlg.result["remote_username"]
            proj["remote_password"] = dlg.result["remote_password"]
            proj["committer_name"] = dlg.result["committer_name"]
            proj["committer_email"] = dlg.result["committer_email"]
            proj["priv_branch"] = dlg.result["priv_branch"]
            self.store.save()
            self._commit(f"Configure Git for project: {proj_name}")
            self._update_undo_redo_buttons()

    def edit_plan(self):
        proj, ms, plan_id = self._get_selected_plan()
        if not plan_id:
            return
        plan = self.store._find_plan(proj, ms, plan_id)
        if not plan:
            return
        if self._has_active_dialog():
            return
        dlg = PlanEditDialog(self.root, self._t, self.lang, plan, project_name=proj, store=self.store)
        self._active_dialog = dlg.top
        self.root.wait_window(dlg.top)
        self._active_dialog = None
        if dlg.result:
            self.undo_manager.save_snapshot()
            for k, v in dlg.result.items():
                plan[k] = v
            self.store.save()
            self._commit(f"Edit plan: {plan['content']}")
            self.refresh_project_list()
            self.refresh_gantt()
            self._update_undo_redo_buttons()

    def pick_color_milestone(self):
        proj = self._get_selected_project()
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        if not values or values[0] != "milestone":
            return
        ms = self.store._find_milestone(proj, values[2])
        if not ms:
            return
        color = colorchooser.askcolor(initialcolor=ms.get("color") or "#D5D8DC", parent=self.root)
        if color[1]:
            self.undo_manager.save_snapshot()
            ms["color"] = color[1]
            self.store.save()
            self._commit(f"Set milestone color: {values[2]}")
            self.refresh_gantt()
            self._update_undo_redo_buttons()

    def pick_color_plan(self):
        proj, ms, plan_id = self._get_selected_plan()
        if not plan_id:
            return
        plan = self.store._find_plan(proj, ms, plan_id)
        if not plan:
            return
        color = colorchooser.askcolor(initialcolor=plan.get("color") or "#4A90D9", parent=self.root)
        if color[1]:
            self.undo_manager.save_snapshot()
            plan["color"] = color[1]
            self.store.save()
            self._commit(f"Set plan color: {plan['content']}")
            self.refresh_gantt()
            self._update_undo_redo_buttons()

    def generate_report(self):
        if not self.current_project:
            return
        proj = self.store.get_project(self.current_project)
        if not proj:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".md", filetypes=[("Markdown", "*.md")],
            initialfile=f"{self.current_project}_report.md",
        )
        if not path:
            return

        # Try to render PNG with PillowBackend
        png_filename = None
        try:
            from ganttpilot_gantt import PillowBackend
            backend = PillowBackend()
            renderer = GanttRenderer(backend, proj, self.lang, self.gantt_zoom,
                                     self.config.get("compress_threshold", 300),
                                     self.config.get("max_chart_width", 4000))
            renderer.draw()
            png_path = os.path.splitext(path)[0] + "_gantt.png"
            backend.save(png_path)
            png_filename = os.path.basename(png_path)
        except ImportError:
            png_filename = None
        except Exception as e:
            png_filename = None
            self.status_var.set(f"PNG error: {e}")

        md = generate_gantt_markdown(proj, self.lang, png_filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(md)
        self._commit(f"Generate report: {self.current_project}")
        self.status_var.set(f"Report saved: {path}")

    # ── Selection helpers ────────────────────────────────────
    def _get_selected_project(self):
        sel = self.tree.selection()
        if not sel:
            return None
        values = self.tree.item(sel[0], "values")
        if values and len(values) >= 2:
            return values[1]
        return None

    def _get_selected_project_milestone(self):
        sel = self.tree.selection()
        if not sel:
            return None, None
        values = self.tree.item(sel[0], "values")
        if not values:
            return None, None
        if values[0] in ("milestone", "plan", "activity") and len(values) >= 3:
            return values[1], values[2]
        return self._get_selected_project(), None

    def _get_selected_plan(self):
        sel = self.tree.selection()
        if not sel:
            return None, None, None
        values = self.tree.item(sel[0], "values")
        if not values:
            return None, None, None
        if values[0] in ("plan", "activity") and len(values) >= 4:
            return values[1], values[2], values[3]
        return None, None, None

    # ── Toolbar action dispatch ──────────────────────────────
    def toolbar_add(self):
        """Dispatch add action based on selected node type."""
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        if not values:
            return
        kind = values[0]
        if kind == "req_analysis":
            self.add_requirement()
        elif kind == "requirement":
            self.add_task()
        elif kind == "plan_execution":
            self.add_milestone()
        elif kind == "milestone":
            self.add_plan()
        elif kind == "plan":
            self.add_activity()

    def toolbar_edit(self):
        """Dispatch edit action based on selected node type."""
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        if not values:
            return
        kind = values[0]
        if kind == "project":
            self.edit_project()
        elif kind == "requirement":
            self.edit_requirement()
        elif kind == "task":
            self.edit_task()
        elif kind == "milestone":
            self.edit_milestone()
        elif kind == "plan":
            self.edit_plan()
        elif kind == "activity":
            self.edit_activity()

    def toolbar_delete(self):
        """Dispatch delete action based on selected node type."""
        self.delete_selected()

    def toolbar_move_up(self):
        """Move selected node up among siblings."""
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        if not values:
            return
        kind = values[0]
        self.undo_manager.save_snapshot()
        moved = False
        if kind == "requirement":
            moved = self.store.move_requirement(values[1], values[2], "up")
        elif kind == "task":
            moved = self.store.move_task(values[1], values[2], values[3], "up")
        elif kind == "milestone":
            moved = self.store.move_milestone(values[1], values[2], "up")
        elif kind == "plan":
            moved = self.store.move_plan(values[1], values[2], values[3], "up")
        elif kind == "activity":
            moved = self.store.move_activity(values[1], values[2], values[3], values[4], "up")
        if moved:
            self._commit(f"Move up: {kind}")
            self.refresh_project_list()
            sel = self.tree.selection()
            if sel:
                vals = self.tree.item(sel[0], "values")
                self._update_toolbar_state(vals[0] if vals else None, sel[0])
            self._update_undo_redo_buttons()

    def toolbar_move_down(self):
        """Move selected node down among siblings."""
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        if not values:
            return
        kind = values[0]
        self.undo_manager.save_snapshot()
        moved = False
        if kind == "requirement":
            moved = self.store.move_requirement(values[1], values[2], "down")
        elif kind == "task":
            moved = self.store.move_task(values[1], values[2], values[3], "down")
        elif kind == "milestone":
            moved = self.store.move_milestone(values[1], values[2], "down")
        elif kind == "plan":
            moved = self.store.move_plan(values[1], values[2], values[3], "down")
        elif kind == "activity":
            moved = self.store.move_activity(values[1], values[2], values[3], values[4], "down")
        if moved:
            self._commit(f"Move down: {kind}")
            self.refresh_project_list()
            sel = self.tree.selection()
            if sel:
                vals = self.tree.item(sel[0], "values")
                self._update_toolbar_state(vals[0] if vals else None, sel[0])
            self._update_undo_redo_buttons()

    # ── Duplicate / Copy / Paste ──────────────────────────────────

    def _can_paste_here(self, kind):
        """Check if clipboard content can be pasted at the current selection."""
        cb = self.store.clipboard_get()
        if not cb:
            return False
        cb_type = cb["type"]
        # Mapping: clipboard type → valid parent node types for paste
        valid_parents = {
            "project":     (None,),
            "requirement": ("req_analysis", "requirement"),
            "task":        ("requirement",),
            "milestone":   ("plan_execution", "milestone"),
            "plan":        ("milestone", "plan"),
            "activity":    ("plan", "activity"),
        }
        return kind in valid_parents.get(cb_type, ())

    def toolbar_duplicate(self):
        """Duplicate the selected node (with all children) in-place."""
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        if not values:
            return
        kind = values[0]
        self.undo_manager.save_snapshot()
        result = None
        label = ""
        if kind == "project":
            result = self.store.duplicate_project(values[1])
            label = result["name"] if result else ""
        elif kind == "requirement":
            result = self.store.duplicate_requirement(values[1], values[2])
            label = result["subject"] if result else ""
        elif kind == "task":
            result = self.store.duplicate_task(values[1], values[2], values[3])
            label = result["subject"] if result else ""
        elif kind == "milestone":
            result = self.store.duplicate_milestone(values[1], values[2])
            label = result["name"] if result else ""
        elif kind == "plan":
            result = self.store.duplicate_plan(values[1], values[2], values[3])
            label = result.get("content", "") if result else ""
        elif kind == "activity":
            result = self.store.duplicate_activity(values[1], values[2], values[3], values[4])
            label = "activity" if result else ""
        if result:
            self._commit(f"Duplicate {kind}: {label}")
            self.refresh_project_list()
            self.refresh_gantt()
            self.refresh_time_report()
            self.status_var.set(self._t("duplicated", label))
            self._update_undo_redo_buttons()

    def toolbar_copy(self, event=None):
        """Copy the selected node to clipboard."""
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        if not values:
            return
        kind = values[0]
        label = ""
        if kind == "project":
            self.store.clipboard_copy("project", values[1])
            label = values[1]
        elif kind == "requirement":
            self.store.clipboard_copy("requirement", values[1], values[2])
            label = values[2]
        elif kind == "task":
            self.store.clipboard_copy("task", values[1], values[2], values[3])
            label = values[3]
        elif kind == "milestone":
            self.store.clipboard_copy("milestone", values[1], values[2])
            label = values[2]
        elif kind == "plan":
            self.store.clipboard_copy("plan", values[1], values[2], values[3])
            label = values[3]
        elif kind == "activity":
            self.store.clipboard_copy("activity", values[1], values[2], values[3], values[4])
            label = values[4]
        else:
            return
        self.status_var.set(self._t("copied", label))
        # Refresh toolbar state so paste button updates
        self._update_toolbar_state(kind, sel[0])

    def toolbar_paste(self, event=None):
        """Paste clipboard content at the selected location."""
        cb = self.store.clipboard_get()
        if not cb:
            self.status_var.set(self._t("nothing_to_paste"))
            return
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        if not values:
            return
        kind = values[0]
        if not self._can_paste_here(kind):
            self.status_var.set(self._t("paste_type_mismatch"))
            return
        cb_type = cb["type"]
        proj_name = values[1] if len(values) >= 2 else None
        self.undo_manager.save_snapshot()
        result = None
        # Determine target parent IDs based on current selection and clipboard type
        if cb_type == "project":
            result = self.store.clipboard_paste(None)
        elif cb_type == "requirement":
            result = self.store.clipboard_paste(proj_name)
        elif cb_type == "task":
            # Pasting task: target must be a requirement node
            if kind == "requirement":
                result = self.store.clipboard_paste(proj_name, (values[2],))
        elif cb_type == "milestone":
            result = self.store.clipboard_paste(proj_name)
        elif cb_type == "plan":
            # Pasting plan: target must be a milestone node
            if kind == "milestone":
                result = self.store.clipboard_paste(proj_name, (values[2],))
            elif kind == "plan":
                result = self.store.clipboard_paste(proj_name, (values[2],))
        elif cb_type == "activity":
            # Pasting activity: target must be a plan node
            if kind == "plan":
                result = self.store.clipboard_paste(proj_name, (values[2], values[3]))
            elif kind == "activity":
                result = self.store.clipboard_paste(proj_name, (values[2], values[3]))
        if result:
            label = result.get("name", result.get("subject", result.get("content", "item")))
            self._commit(f"Paste {cb_type}: {label}")
            self.refresh_project_list()
            self.refresh_gantt()
            self.refresh_time_report()
            self.status_var.set(self._t("pasted", label))
            self._update_undo_redo_buttons()

    # ── Requirement / Task CRUD ──────────────────────────────
    def add_requirement(self):
        proj_name = self._get_selected_project()
        if not proj_name:
            return
        if self._has_active_dialog():
            return
        dlg = RequirementDialog(self.root, self._t, self.lang)
        self._active_dialog = dlg.top
        self.root.wait_window(dlg.top)
        self._active_dialog = None
        if dlg.result:
            r = dlg.result
            self.undo_manager.save_snapshot()
            result = self.store.add_requirement(proj_name, r["category"], r["subject"], r["description"])
            if result:
                self._commit(f"Add requirement: {r['subject']}")
                self.refresh_project_list()
                self.status_var.set(self._t("requirement_added", r["subject"]))
                self._update_undo_redo_buttons()

    def edit_requirement(self):
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        if not values or values[0] != "requirement":
            return
        proj_name, req_id = values[1], values[2]
        req = self.store.get_requirement(proj_name, req_id)
        if not req:
            return
        if self._has_active_dialog():
            return
        dlg = RequirementEditDialog(self.root, self._t, self.lang, req)
        self._active_dialog = dlg.top
        self.root.wait_window(dlg.top)
        self._active_dialog = None
        if dlg.result:
            r = dlg.result
            self.undo_manager.save_snapshot()
            self.store.update_requirement(proj_name, req_id, r["category"], r["subject"], r["description"])
            self._commit(f"Edit requirement: {r['subject']}")
            self.refresh_project_list()
            self._update_undo_redo_buttons()

    def add_task(self):
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        if not values or values[0] != "requirement":
            return
        proj_name, req_id = values[1], values[2]
        if self._has_active_dialog():
            return
        dlg = TaskDialog(self.root, self._t, self.lang)
        self._active_dialog = dlg.top
        self.root.wait_window(dlg.top)
        self._active_dialog = None
        if dlg.result:
            r = dlg.result
            self.undo_manager.save_snapshot()
            result = self.store.add_task(proj_name, req_id, r["subject"], r["effort_days"], r["description"])
            if result:
                self._commit(f"Add task: {r['subject']}")
                self.refresh_project_list()
                self.status_var.set(self._t("task_added", r["subject"]))
                self._update_undo_redo_buttons()

    def edit_task(self):
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        if not values or values[0] != "task":
            return
        proj_name, req_id, task_id = values[1], values[2], values[3]
        req = self.store.get_requirement(proj_name, req_id)
        if not req:
            return
        task = None
        for t in req.get("tasks", []):
            if t["id"] == task_id:
                task = t
                break
        if not task:
            return
        if self._has_active_dialog():
            return
        dlg = TaskEditDialog(self.root, self._t, self.lang, task)
        self._active_dialog = dlg.top
        self.root.wait_window(dlg.top)
        self._active_dialog = None
        if dlg.result:
            r = dlg.result
            self.undo_manager.save_snapshot()
            self.store.update_task(proj_name, req_id, task_id, r["subject"], r["effort_days"], r["description"])
            self._commit(f"Edit task: {r['subject']}")
            self.refresh_project_list()
            self._update_undo_redo_buttons()

    # ── Config / Font / Language ─────────────────────────────
    def toggle_language(self):
        self.lang = "en" if self.lang == "zh" else "zh"
        self.config.language = self.lang
        self.config.save()
        self.root.title(self._t("app_title") + f" v{VERSION}")
        self.report_tree.heading("executor", text=self._t("executor"))
        self.report_tree.heading("hours", text=self._t("total_hours"))
        self.report_tree.heading("days", text=self._t("total_days"))
        self.report_tree.heading("percentage", text=self._t("percentage"))
        # Update notebook tab labels
        self.right_notebook.tab(0, text=self._t("gantt_chart"))
        self.right_notebook.tab(1, text=self._t("history"))
        # Update branch label
        self.branch_label.configure(text=self._t("branch"))
        # Update banner labels
        self.update_banner_label.configure(text=self._t("main_updated"))
        self.update_banner_btn.configure(text=self._t("sync_main"))
        # Update report mode selector
        self.report_mode_label.configure(text=self._t("report_mode"))
        current_idx = self.report_mode_combo.current()
        self.report_mode_combo["values"] = [
            self._t("report_by_project"),
            self._t("report_by_milestone"),
            self._t("report_by_plan"),
            self._t("report_by_tag"),
        ]
        self.report_mode_combo.current(current_idx if current_idx >= 0 else 0)
        # Update history tree headings
        self.history_tree.heading("commit_author", text=self._t("commit_author"))
        self.history_tree.heading("commit_date", text=self._t("commit_date"))
        self.history_tree.heading("commit_message", text=self._t("commit_message"))
        self.refresh_gantt()

    def increase_font(self):
        self.config.font_size = self.config.font_size + 1
        self.update_fonts()

    def decrease_font(self):
        self.config.font_size = self.config.font_size - 1
        self.update_fonts()

    def gantt_zoom_in(self):
        self.gantt_zoom = min(30, self.gantt_zoom + 1)
        self.refresh_gantt()

    def gantt_zoom_out(self):
        self.gantt_zoom = max(6, self.gantt_zoom - 1)
        self.refresh_gantt()

    def update_fonts(self):
        size = self.config.font_size
        style = ttk.Style()
        style.configure("Treeview", font=("", size), rowheight=int(size * 2.2))
        style.configure("Treeview.Heading", font=("", size, "bold"))
        # Update the default font used by new widgets (dialogs will pick this up)
        import tkinter.font as tkfont
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(size=size)
        text_font = tkfont.nametofont("TkTextFont")
        text_font.configure(size=size)
        if self.current_project:
            self.refresh_gantt()

    def open_config_dialog(self):
        if self._has_active_dialog():
            return
        dlg = ConfigDialog(self.root, self.config, self._t, self.lang,
                           shortcut_manager=self.shortcut_manager)
        self._active_dialog = dlg.top
        self.root.wait_window(dlg.top)
        self._active_dialog = None
        if dlg.saved:
            self.store = DataStore(self.config.data_dir)
            self.undo_manager = UndoManager(self.store)
            self.refresh_project_list()
            # Update tooltips with potentially changed shortcuts
            self._show_tooltip(self.undo_btn, self._tooltip_with_shortcut(self._t("undo"), "undo"))
            self._show_tooltip(self.redo_btn, self._tooltip_with_shortcut(self._t("redo"), "redo"))
            self._show_tooltip(self.tb_add_btn, self._tooltip_with_shortcut(self._t("add"), "add"))
            self._show_tooltip(self.tb_edit_btn, self._tooltip_with_shortcut(self._t("edit"), "edit"))
            self._show_tooltip(self.tb_delete_btn, self._tooltip_with_shortcut(self._t("delete"), "delete"))
            self._show_tooltip(self.tb_copy_btn, self._tooltip_with_shortcut(self._t("copy"), "copy"))
            self._show_tooltip(self.tb_paste_btn, self._tooltip_with_shortcut(self._t("paste"), "paste"))
            self._show_tooltip(self.tb_dup_btn, self._tooltip_with_shortcut(self._t("duplicate"), "duplicate"))
            self._show_tooltip(self.tb_up_btn, self._tooltip_with_shortcut(self._t("move_up"), "move_up"))
            self._show_tooltip(self.tb_down_btn, self._tooltip_with_shortcut(self._t("move_down"), "move_down"))
            # Update pull interval from config
            pull_interval = max(1, self.config.get("pull_interval", 5))
            self._bg_check_interval_ms = pull_interval * 60 * 1000

    def show_help(self):
        help_body = self._t("help_text")
        footer = f"v{VERSION}  |  GitHub: https://github.com/{GITHUB_REPO}"
        messagebox.showinfo(self._t("help"), help_body + footer)

    def do_sync(self):
        if not self.current_project:
            self.status_var.set(self._t("select_project"))
            return
        proj = self.store.get_project(self.current_project)
        if not proj or not proj.get("remote_url"):
            self.status_var.set(self._t("no_remote"))
            return

        # Check git installed
        installed, _ = GitSync.check_git_installed()
        if not installed:
            messagebox.showwarning(self._t("warning"), self._t("git_not_installed"))
            return

        # Check committer configured
        if not proj.get("committer_name") or not proj.get("committer_email"):
            messagebox.showwarning(self._t("warning"), self._t("committer_not_configured"))
            return

        self.status_var.set(self._t("pushing"))
        self.root.update()
        try:
            gs = self._get_project_git(proj)
            proj_dir = os.path.join(self.config.data_dir, proj["name"])
            # If project directory was deleted, re-clone from remote
            if not gs.is_repo():
                remote_url = proj.get("remote_url", "")
                remote_branch = proj.get("remote_branch", "main")
                if os.path.exists(proj_dir):
                    _force_rmtree(proj_dir)
                gs.clone_repo(remote_url, proj_dir, remote_branch)
                gs = self._get_project_git(proj)
            gs.init_repo()
            gs.sync()
            self._full_refresh()
            # Show PR hint in status bar
            priv = proj.get("priv_branch") or f"priv_{proj['committer_name']}"
            main = proj.get("remote_branch", "main")
            self.status_var.set(self._t("sync_pr_hint", priv, priv, main))
            # Prompt rebase if main was updated during sync
            if getattr(gs, '_main_updated', False):
                self._prompt_rebase([proj])
        except Exception as e:
            self.status_var.set(self._t("push_fail", str(e)))

    def do_pull(self):
        """Pull (fetch + reload) from remote without pushing."""
        if not self.current_project:
            self.status_var.set(self._t("select_project"))
            return
        proj = self.store.get_project(self.current_project)
        if not proj or not proj.get("remote_url"):
            self.status_var.set(self._t("no_remote"))
            return

        installed, _ = GitSync.check_git_installed()
        if not installed:
            messagebox.showwarning(self._t("warning"), self._t("git_not_installed"))
            return

        self.status_var.set(self._t("pulling"))
        self.root.update()
        try:
            gs = self._get_project_git(proj)
            if not gs.is_repo():
                # Clone if repo doesn't exist locally
                remote_url = proj.get("remote_url", "")
                remote_branch = proj.get("remote_branch", "main")
                proj_dir = os.path.join(self.config.data_dir, proj["name"])
                if os.path.exists(proj_dir):
                    _force_rmtree(proj_dir)
                gs.clone_repo(remote_url, proj_dir, remote_branch)
                gs = self._get_project_git(proj)
            gs.init_repo()
            gs.fetch_remote()
            self._full_refresh()
            self.status_var.set(self._t("pull_done"))
            # Prompt rebase if main was updated during fetch
            if getattr(gs, '_main_updated', False):
                self._prompt_rebase([proj])
        except Exception as e:
            self.status_var.set(self._t("pull_fail", str(e)))

    def on_close(self):
        is_maximized = self.root.state() == "zoomed"
        self.config.set("window_maximized", is_maximized)
        if not is_maximized:
            geo = self.root.geometry()
            try:
                size_part, x, y = geo.replace("+", " ").split()
                self.config.set("window_geometry", size_part)
                self.config.set("window_position", f"{x},{y}")
            except Exception:
                pass
        self.config.save()
        self.root.destroy()

    def _bg_sync_project(self, proj_name):
        """Sync a project in a background thread (non-blocking)."""
        proj = self.store.get_project(proj_name)
        if not proj or not proj.get("remote_url"):
            return
        def _do():
            try:
                gs = self._get_project_git(proj)
                if not gs.is_repo():
                    return  # Skip background sync if repo was deleted
                gs.init_repo()
                gs.sync()
            except Exception:
                pass
        threading.Thread(target=_do, daemon=True).start()

    # ── Undo / Redo ──────────────────────────────────────────
    def _update_undo_redo_buttons(self):
        self.undo_btn.configure(state=tk.NORMAL if self.undo_manager.can_undo() else tk.DISABLED)
        self.redo_btn.configure(state=tk.NORMAL if self.undo_manager.can_redo() else tk.DISABLED)

    def do_undo(self, event=None):
        focus_widget = self.root.focus_get()
        if isinstance(focus_widget, tk.Text):
            try:
                focus_widget.edit_undo()
            except tk.TclError:
                pass
            return "break"
        if isinstance(focus_widget, (ttk.Entry, tk.Entry)):
            return  # Let Entry handle Ctrl+Z natively (don't block with "break")
        if self.undo_manager.undo():
            self.store.save()
            self.refresh_project_list()
            self.refresh_gantt()
            self.refresh_time_report()
            self._update_undo_redo_buttons()
            self.status_var.set(self._t("undo_done"))
        else:
            self.status_var.set(self._t("no_undo"))

    def do_redo(self, event=None):
        focus_widget = self.root.focus_get()
        if isinstance(focus_widget, tk.Text):
            try:
                focus_widget.edit_redo()
            except tk.TclError:
                pass
            return "break"
        if isinstance(focus_widget, (ttk.Entry, tk.Entry)):
            return  # Let Entry handle Ctrl+Y natively (don't block with "break")
        if self.undo_manager.redo():
            self.store.save()
            self.refresh_project_list()
            self.refresh_gantt()
            self.refresh_time_report()
            self._update_undo_redo_buttons()
            self.status_var.set(self._t("redo_done"))
        else:
            self.status_var.set(self._t("no_redo"))

    def _tooltip_with_shortcut(self, text, action_id):
        """Return tooltip text with shortcut info appended if available.

        Format: "操作名称 (快捷键)" when shortcut exists, otherwise just "操作名称".
        """
        display = self.shortcut_manager.get_display_string(action_id)
        if display:
            return f"{text} ({display})"
        return text

    def _accel(self, action_id):
        """Return accelerator display string for a menu item, or empty string if unbound."""
        return self.shortcut_manager.get_display_string(action_id)

    def _show_tooltip(self, widget, text):
        def on_enter(event):
            tip = tk.Toplevel(widget)
            tip.wm_overrideredirect(True)
            tip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            lbl = tk.Label(tip, text=text, background="#ffffe0", relief=tk.SOLID, borderwidth=1, font=("", 9))
            lbl.pack()
            widget._tooltip = tip
        def on_leave(event):
            tip = getattr(widget, "_tooltip", None)
            if tip:
                tip.destroy()
                widget._tooltip = None
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)


# ── Dialogs ──────────────────────────────────────────────────

class PlanDialog:
    """Dialog for adding a plan"""
    def __init__(self, parent, t_func, lang, project_name=None, store=None):
        self.result = None
        self.top = tk.Toplevel(parent)
        self.top.title(t_func("add") + " " + t_func("plan"))
        _center_dialog(self.top, parent, 420, 400)
        self.top.transient(parent)
        self.top.grab_set()
        self.top.focus_set()
        self.top.bind("<Escape>", lambda e: self.top.destroy())
        self.top.columnconfigure(1, weight=1)

        fields = [
            ("content", t_func("content")),
            ("executor", t_func("executor")),
            ("start_date", t_func("start_date") + " (YYYYMMDD)"),
            ("end_date", t_func("end_date") + " (YYYYMMDD)"),
            ("skip_dates", t_func("skip_dates") + " (D1,D2,...)"),
            ("color", "🎨 Color (#hex)"),
        ]
        self.entries = {}
        row = 0
        for key, label in fields:
            ttk.Label(self.top, text=label).grid(row=row, column=0, padx=8, pady=3, sticky=tk.W)
            entry = ttk.Entry(self.top, width=30)
            entry.grid(row=row, column=1, padx=8, pady=3, sticky=tk.EW)
            self.entries[key] = entry
            row += 1
            if key == "skip_dates":
                ttk.Label(self.top, text=t_func("skip_dates_hint"), foreground="gray", font=("", 8)).grid(
                    row=row, column=1, padx=8, pady=(0, 2), sticky=tk.W)
                row += 1

        # Linked task dropdown
        row_lt = row
        ttk.Label(self.top, text=t_func("linked_task")).grid(row=row_lt, column=0, padx=8, pady=3, sticky=tk.W)
        self._task_options = []  # list of (task_id, display_text)
        self._task_display_list = [""]  # first item is empty (no linked task)
        if store and project_name:
            for req, task in store.get_all_tasks_for_project(project_name):
                display = format_linked_task_display(
                    req.get("category", ""), req.get("subject", ""), task.get("subject", ""))
                self._task_options.append((task["id"], display))
                self._task_display_list.append(display)
        self.linked_task_combo = ttk.Combobox(self.top, values=self._task_display_list, state="readonly", width=28)
        self.linked_task_combo.current(0)
        self.linked_task_combo.grid(row=row_lt, column=1, padx=8, pady=3, sticky=tk.EW)

        self.skip_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.top, text=t_func("skip_non_workdays"), variable=self.skip_var).grid(
            row=row_lt + 1, column=0, columnspan=2, padx=8, pady=3, sticky=tk.W)
        # CalcPaper hint
        hint = ttk.Label(self.top, text="💡 可使用 CalcPaper 进行工期推算" if lang == "zh" else "💡 Use CalcPaper for schedule estimation",
                         foreground="gray", cursor="hand2")
        hint.grid(row=row_lt + 2, column=0, columnspan=2, padx=8, pady=(2, 0), sticky=tk.W)
        hint.bind("<Button-1>", lambda e: __import__("webbrowser").open("https://github.com/matthewzu/CalcPaper"))
        ttk.Button(self.top, text="OK", command=self._ok).grid(
            row=row_lt + 3, column=0, columnspan=2, pady=10)

    def _ok(self):
        content = self.entries["content"].get().strip()
        executor = self.entries["executor"].get().strip()
        start = self.entries["start_date"].get().strip()
        end = self.entries["end_date"].get().strip()
        skip_str = self.entries["skip_dates"].get().strip()
        color = self.entries["color"].get().strip()
        skip_dates = [d.strip() for d in skip_str.replace("\uff0c", ",").split(",") if d.strip()] if skip_str else []
        # Resolve linked task ID from dropdown selection
        linked_task_id = ""
        selected = self.linked_task_combo.get()
        if selected:
            for tid, display in self._task_options:
                if display == selected:
                    linked_task_id = tid
                    break
        if content and executor and start and end:
            self.result = {
                "content": content, "executor": executor,
                "start_date": start, "end_date": end,
                "skip_non_workdays": self.skip_var.get(),
                "skip_dates": skip_dates, "color": color,
                "linked_task_id": linked_task_id,
            }
            self.top.destroy()


class PlanEditDialog:
    """Dialog for editing an existing plan's properties"""
    def __init__(self, parent, t_func, lang, plan, project_name=None, store=None):
        self.result = None
        self.top = tk.Toplevel(parent)
        self.top.title("✏ " + t_func("plan"))
        _center_dialog(self.top, parent, 420, 400)
        self.top.transient(parent)
        self.top.grab_set()
        self.top.focus_set()
        self.top.bind("<Escape>", lambda e: self.top.destroy())
        self.top.columnconfigure(1, weight=1)

        fields = [
            ("content", t_func("content"), plan.get("content", "")),
            ("executor", t_func("executor"), plan.get("executor", "")),
            ("start_date", t_func("start_date"), plan.get("start_date", "")),
            ("end_date", t_func("end_date"), plan.get("end_date", "")),
            ("skip_dates", t_func("skip_dates"), ",".join(plan.get("skip_dates", []))),
            ("color", "🎨 Color", plan.get("color", "")),
        ]
        self.entries = {}
        row = 0
        for key, label, val in fields:
            ttk.Label(self.top, text=label).grid(row=row, column=0, padx=8, pady=3, sticky=tk.W)
            entry = ttk.Entry(self.top, width=30)
            entry.insert(0, val)
            entry.grid(row=row, column=1, padx=8, pady=3, sticky=tk.EW)
            self.entries[key] = entry
            row += 1
            if key == "skip_dates":
                ttk.Label(self.top, text=t_func("skip_dates_hint"), foreground="gray", font=("", 8)).grid(
                    row=row, column=1, padx=8, pady=(0, 2), sticky=tk.W)
                row += 1

        # Linked task dropdown
        row_lt = row
        ttk.Label(self.top, text=t_func("linked_task")).grid(row=row_lt, column=0, padx=8, pady=3, sticky=tk.W)
        self._task_options = []  # list of (task_id, display_text)
        self._task_display_list = [""]  # first item is empty (no linked task)
        if store and project_name:
            for req, task in store.get_all_tasks_for_project(project_name):
                display = format_linked_task_display(
                    req.get("category", ""), req.get("subject", ""), task.get("subject", ""))
                self._task_options.append((task["id"], display))
                self._task_display_list.append(display)
        self.linked_task_combo = ttk.Combobox(self.top, values=self._task_display_list, state="readonly", width=28)
        # Pre-select current linked task
        current_linked = plan.get("linked_task_id", "")
        selected_idx = 0
        if current_linked:
            for i, (tid, display) in enumerate(self._task_options):
                if tid == current_linked:
                    selected_idx = i + 1  # +1 because index 0 is empty
                    break
        self.linked_task_combo.current(selected_idx)
        self.linked_task_combo.grid(row=row_lt, column=1, padx=8, pady=3, sticky=tk.EW)

        self.skip_var = tk.BooleanVar(value=plan.get("skip_non_workdays", True))
        ttk.Checkbutton(self.top, text=t_func("skip_non_workdays"), variable=self.skip_var).grid(
            row=row_lt + 1, column=0, columnspan=2, padx=8, pady=3, sticky=tk.W)
        # CalcPaper hint
        hint = ttk.Label(self.top, text="💡 可使用 CalcPaper 进行工期推算" if lang == "zh" else "💡 Use CalcPaper for schedule estimation",
                         foreground="gray", cursor="hand2")
        hint.grid(row=row_lt + 2, column=0, columnspan=2, padx=8, pady=(2, 0), sticky=tk.W)
        hint.bind("<Button-1>", lambda e: __import__("webbrowser").open("https://github.com/matthewzu/CalcPaper"))
        ttk.Button(self.top, text="OK", command=self._ok).grid(
            row=row_lt + 3, column=0, columnspan=2, pady=10)

    def _ok(self):
        skip_str = self.entries["skip_dates"].get().strip()
        # Resolve linked task ID from dropdown selection
        linked_task_id = ""
        selected = self.linked_task_combo.get()
        if selected:
            for tid, display in self._task_options:
                if display == selected:
                    linked_task_id = tid
                    break
        self.result = {
            "content": self.entries["content"].get().strip(),
            "executor": self.entries["executor"].get().strip(),
            "start_date": self.entries["start_date"].get().strip(),
            "end_date": self.entries["end_date"].get().strip(),
            "skip_dates": [d.strip() for d in skip_str.replace("\uff0c", ",").split(",") if d.strip()] if skip_str else [],
            "skip_non_workdays": self.skip_var.get(),
            "color": self.entries["color"].get().strip(),
            "linked_task_id": linked_task_id,
        }
        self.top.destroy()


class ActivityDialog:
    """Dialog for adding an activity"""
    def __init__(self, parent, t_func, lang, project_tags=None):
        self.result = None
        self.t_func = t_func
        self.project_tags = project_tags or []
        self.top = tk.Toplevel(parent)
        self.top.title(t_func("add") + " " + t_func("activity"))
        _center_dialog(self.top, parent, 420, 420)
        self.top.transient(parent)
        self.top.grab_set()
        self.top.focus_set()
        self.top.bind("<Escape>", lambda e: self.top.destroy())
        self.top.columnconfigure(1, weight=1)

        row = 0
        fields = [
            ("executor", t_func("executor")),
            ("date", t_func("date") + " (YYYYMMDD, " + t_func("optional") + ")"),
            ("content", t_func("content")),
        ]
        self.entries = {}
        for key, label in fields:
            ttk.Label(self.top, text=label).grid(row=row, column=0, padx=8, pady=4, sticky=tk.W)
            entry = ttk.Entry(self.top, width=30)
            entry.grid(row=row, column=1, padx=8, pady=4, sticky=tk.EW)
            self.entries[key] = entry
            row += 1

        # Effort hours field
        ttk.Label(self.top, text=t_func("effort_hours")).grid(row=row, column=0, padx=8, pady=4, sticky=tk.W)
        hours_entry = ttk.Entry(self.top, width=30)
        hours_entry.grid(row=row, column=1, padx=8, pady=4, sticky=tk.EW)
        self.entries["effort_hours"] = hours_entry
        row += 1
        ttk.Label(self.top, text=t_func("effort_hours_hint"), foreground="gray", font=("", 8)).grid(
            row=row, column=1, padx=8, pady=(0, 2), sticky=tk.W)
        row += 1

        # Time slots field
        ttk.Label(self.top, text=t_func("time_slots")).grid(row=row, column=0, padx=8, pady=4, sticky=tk.W)
        ts_entry = ttk.Entry(self.top, width=30)
        ts_entry.grid(row=row, column=1, padx=8, pady=4, sticky=tk.EW)
        self.entries["time_slots"] = ts_entry
        row += 1
        ttk.Label(self.top, text=t_func("time_slots_hint"), foreground="gray", font=("", 8)).grid(
            row=row, column=1, padx=8, pady=(0, 2), sticky=tk.W)
        row += 1

        # Mutual exclusion hint
        ttk.Label(self.top, text=t_func("time_slots_or_hours_hint"), foreground="orange", font=("", 8)).grid(
            row=row, column=0, columnspan=2, padx=8, pady=(0, 2), sticky=tk.W)
        row += 1

        # Tag field — Combobox if project has tags, otherwise Entry
        ttk.Label(self.top, text=t_func("tag")).grid(row=row, column=0, padx=8, pady=4, sticky=tk.W)
        if self.project_tags:
            tag_combo = ttk.Combobox(self.top, width=28, values=[""] + self.project_tags)
            tag_combo.grid(row=row, column=1, padx=8, pady=4, sticky=tk.EW)
            self.entries["tag"] = tag_combo
        else:
            tag_entry = ttk.Entry(self.top, width=30)
            tag_entry.grid(row=row, column=1, padx=8, pady=4, sticky=tk.EW)
            self.entries["tag"] = tag_entry
        row += 1

        # Description field (multi-line text with scrollbar)
        ttk.Label(self.top, text=t_func("description")).grid(row=row, column=0, padx=8, pady=4, sticky=tk.NW)
        desc_frame = ttk.Frame(self.top)
        desc_frame.grid(row=row, column=1, padx=8, pady=4, sticky=tk.NSEW)
        self.top.rowconfigure(row, weight=1)
        self.desc_text = tk.Text(desc_frame, width=30, height=4, wrap=tk.WORD, undo=True)
        desc_sb = ttk.Scrollbar(desc_frame, orient=tk.VERTICAL, command=self.desc_text.yview)
        self.desc_text.configure(yscrollcommand=desc_sb.set)
        self.desc_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        desc_sb.pack(side=tk.RIGHT, fill=tk.Y)
        row += 1

        ttk.Button(self.top, text="OK", command=self._ok).grid(
            row=row, column=0, columnspan=2, pady=12)

    def _ok(self):
        executor = self.entries["executor"].get().strip()
        date = self.entries["date"].get().strip()
        content = self.entries["content"].get().strip()
        effort_hours_str = self.entries["effort_hours"].get().strip()
        time_slots = self.entries["time_slots"].get().strip()
        tag = self.entries["tag"].get().strip()
        description = self.desc_text.get("1.0", tk.END).strip()
        # Mutual exclusion: cannot fill both
        if effort_hours_str and time_slots:
            messagebox.showwarning("", self.t_func("hours_conflict"))
            return
        # Validate effort_hours if provided
        if effort_hours_str:
            try:
                hours = float(effort_hours_str)
            except ValueError:
                messagebox.showwarning("", self.t_func("invalid_hours"))
                return
            if hours < 0:
                messagebox.showwarning("", self.t_func("hours_non_negative"))
                return
        else:
            hours = 0.0
        # Validate time_slots if provided
        if time_slots:
            try:
                parse_time_slots(time_slots)
            except ValueError:
                messagebox.showwarning("", self.t_func("invalid_time_slots"))
                return
            hours = calculate_hours_from_slots(time_slots)
        if executor and content:
            self.result = {"executor": executor, "date": date, "hours": hours,
                           "content": content, "time_slots": time_slots, "tag": tag,
                           "description": description}
            self.top.destroy()


class ConfigDialog:
    """Dialog for editing global configuration"""

    # i18n key mapping for action display names
    _ACTION_I18N_KEYS = {
        "add": "shortcut_add",
        "edit": "shortcut_edit",
        "delete": "shortcut_delete",
        "move_up": "shortcut_move_up",
        "move_down": "shortcut_move_down",
        "duplicate": "shortcut_duplicate",
        "copy": "shortcut_copy",
        "paste": "shortcut_paste",
        "undo": "shortcut_undo",
        "redo": "shortcut_redo",
        "sync": "shortcut_sync",
        "refresh": "shortcut_refresh",
    }

    def __init__(self, parent, config, t_func, lang, shortcut_manager=None):
        self.config = config
        self.saved = False
        self.t_func = t_func
        self.lang = lang
        self.shortcut_manager = shortcut_manager
        self.top = tk.Toplevel(parent)
        self.top.title(t_func("config"))
        _center_dialog(self.top, parent, 620, 520)
        self.top.transient(parent)
        self.top.grab_set()
        self.top.focus_set()
        self.top.bind("<Escape>", lambda e: self.top.destroy())
        self.top.columnconfigure(1, weight=1)

        fields = [
            ("data_dir", t_func("data_dir"), config.data_dir),
            ("config_dir", t_func("config_dir"), config.config_dir),
            ("compress_threshold", t_func("compress_threshold") if lang == "en" else "报告图片压缩阈值(天)", str(config.get("compress_threshold", 300))),
            ("max_chart_width", t_func("max_chart_width") if lang == "en" else "报告图片最大宽度(px)", str(config.get("max_chart_width", 4000))),
            ("pull_interval", t_func("pull_interval"), str(config.get("pull_interval", 5))),
        ]
        path_fields = {"data_dir", "config_dir"}
        self.entries = {}
        for i, (key, label, val) in enumerate(fields):
            ttk.Label(self.top, text=label).grid(row=i, column=0, padx=8, pady=4, sticky=tk.W)
            entry = ttk.Entry(self.top, width=35)
            entry.insert(0, val or "")
            entry.grid(row=i, column=1, padx=4, pady=4, sticky=tk.EW)
            self.entries[key] = entry
            if key in path_fields:
                ttk.Button(self.top, text="📂", width=3,
                           command=lambda e=entry: self._browse_dir(e)).grid(row=i, column=2, padx=2, pady=4)

        next_row = len(fields)

        # ── Shortcut configuration section ───────────────────
        if self.shortcut_manager is not None:
            self._pending_bindings = dict(self.shortcut_manager.get_all_bindings())
            self._build_shortcut_section(next_row)
            next_row = next_row + 1  # LabelFrame occupies one row

        ttk.Button(self.top, text=t_func("save_config"), command=self._save).grid(
            row=next_row, column=0, columnspan=3, pady=12)

    def _build_shortcut_section(self, start_row):
        """Build the shortcut configuration LabelFrame with Treeview."""
        frame = ttk.LabelFrame(self.top, text=self.t_func("shortcut_config"))
        frame.grid(row=start_row, column=0, columnspan=3, padx=8, pady=6, sticky=tk.NSEW)
        self.top.rowconfigure(start_row, weight=1)

        # Treeview for action -> shortcut display
        cols = ("action", "shortcut")
        self.shortcut_tree = ttk.Treeview(frame, columns=cols, show="headings", height=8, selectmode="browse")
        action_header = "Action" if self.lang == "en" else "操作"
        shortcut_header = "Shortcut" if self.lang == "en" else "快捷键"
        self.shortcut_tree.heading("action", text=action_header)
        self.shortcut_tree.heading("shortcut", text=shortcut_header)
        self.shortcut_tree.column("action", width=160, anchor="w")
        self.shortcut_tree.column("shortcut", width=160, anchor="center")

        sb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.shortcut_tree.yview)
        self.shortcut_tree.configure(yscrollcommand=sb.set)
        self.shortcut_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0), pady=4)
        sb.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 2), pady=4)

        # Populate rows
        self._populate_shortcut_tree()

        # Bind key capture on the Treeview
        self.shortcut_tree.bind("<Key>", self._on_shortcut_key)

        # Buttons frame on the right
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=4)
        ttk.Button(btn_frame, text=self.t_func("shortcut_reset"),
                   command=self._reset_shortcuts).pack(pady=4)

    def _populate_shortcut_tree(self):
        """Fill the shortcut Treeview with current pending bindings."""
        for item in self.shortcut_tree.get_children():
            self.shortcut_tree.delete(item)
        for action_id in self._ACTION_I18N_KEYS:
            i18n_key = self._ACTION_I18N_KEYS[action_id]
            display_name = self.t_func(i18n_key)
            key_event = self._pending_bindings.get(action_id, "")
            display_shortcut = tk_event_to_display(key_event)
            self.shortcut_tree.insert("", tk.END, iid=action_id,
                                      values=(display_name, display_shortcut))

    def _on_shortcut_key(self, event):
        """Capture key press on the shortcut Treeview to update binding."""
        selection = self.shortcut_tree.selection()
        if not selection:
            return
        action_id = selection[0]

        # Delete/BackSpace clears the shortcut
        if event.keysym in ("Delete", "BackSpace"):
            self._pending_bindings[action_id] = ""
            self._refresh_shortcut_row(action_id)
            return "break"

        # Ignore bare modifier keys
        if event.keysym in ("Control_L", "Control_R", "Alt_L", "Alt_R",
                            "Shift_L", "Shift_R", "Caps_Lock", "Num_Lock",
                            "Meta_L", "Meta_R"):
            return "break"

        # Ignore Tab/Escape to allow normal dialog navigation
        if event.keysym in ("Tab", "Escape"):
            return

        # Build tkinter event string from the event
        parts = []
        if event.state & 0x4:  # Control
            parts.append("Control")
        if event.state & 0x20000 or event.state & 0x8:  # Alt
            parts.append("Alt")
        if event.state & 0x1:  # Shift
            parts.append("Shift")

        keysym = event.keysym
        # Normalize single-char keysyms to lowercase for tkinter format
        if len(keysym) == 1:
            keysym = keysym.lower()

        parts.append(keysym)
        new_event = "<" + "-".join(parts) + ">"

        # Check for conflicts
        for aid, evt in self._pending_bindings.items():
            if aid != action_id and evt and evt.lower() == new_event.lower():
                conflict_name = self.t_func(self._ACTION_I18N_KEYS.get(aid, aid))
                display_key = tk_event_to_display(new_event)
                messagebox.showwarning(
                    self.t_func("warning"),
                    self.t_func("shortcut_conflict", display_key, conflict_name),
                    parent=self.top,
                )
                return "break"

        self._pending_bindings[action_id] = new_event
        self._refresh_shortcut_row(action_id)
        return "break"

    def _refresh_shortcut_row(self, action_id):
        """Update a single row in the shortcut Treeview."""
        i18n_key = self._ACTION_I18N_KEYS.get(action_id, action_id)
        display_name = self.t_func(i18n_key)
        key_event = self._pending_bindings.get(action_id, "")
        display_shortcut = tk_event_to_display(key_event)
        self.shortcut_tree.item(action_id, values=(display_name, display_shortcut))

    def _reset_shortcuts(self):
        """Reset all pending shortcut bindings to defaults."""
        self._pending_bindings = dict(ShortcutManager.DEFAULT_SHORTCUTS)
        self._populate_shortcut_tree()

    def _browse_dir(self, entry):
        current = entry.get().strip()
        path = filedialog.askdirectory(initialdir=current or None, parent=self.top)
        if path:
            entry.delete(0, tk.END)
            entry.insert(0, path)

    def _save(self):
        for key, entry in self.entries.items():
            val = entry.get().strip()
            if key in ("compress_threshold", "max_chart_width", "pull_interval"):
                try:
                    val = int(val)
                except ValueError:
                    continue
            self.config.set(key, val)

        # Save shortcut bindings if shortcut_manager is available
        if self.shortcut_manager is not None:
            self.shortcut_manager.unregister_all()
            for action_id, key_event in self._pending_bindings.items():
                self.shortcut_manager.bindings[action_id] = key_event
            self.shortcut_manager.save_to_config(self.config)
            self.shortcut_manager.register_all()

        self.config.save()
        self.saved = True
        self.top.destroy()


class ProjectEditDialog:
    """Dialog for editing a project name, description and tags"""
    def __init__(self, parent, t_func, lang, project):
        self.result = None
        self.t_func = t_func
        self.top = tk.Toplevel(parent)
        self.top.title("✏ " + t_func("edit_project"))
        _center_dialog(self.top, parent, 400, 300)
        self.top.transient(parent)
        self.top.grab_set()
        self.top.focus_set()
        self.top.bind("<Escape>", lambda e: self.top.destroy())
        self.top.columnconfigure(1, weight=1)
        self.top.rowconfigure(1, weight=1)

        ttk.Label(self.top, text=t_func("project_name")).grid(row=0, column=0, padx=8, pady=6, sticky=tk.W)
        self.name_entry = ttk.Entry(self.top, width=30)
        self.name_entry.insert(0, project.get("name", ""))
        self.name_entry.grid(row=0, column=1, padx=8, pady=6, sticky=tk.EW)

        ttk.Label(self.top, text=t_func("description")).grid(row=1, column=0, padx=8, pady=6, sticky=tk.NW)
        desc_frame = ttk.Frame(self.top)
        desc_frame.grid(row=1, column=1, padx=8, pady=6, sticky=tk.NSEW)
        self.desc_text = tk.Text(desc_frame, width=30, height=6, wrap=tk.WORD, undo=True)
        desc_sb = ttk.Scrollbar(desc_frame, orient=tk.VERTICAL, command=self.desc_text.yview)
        self.desc_text.configure(yscrollcommand=desc_sb.set)
        self.desc_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        desc_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.desc_text.insert("1.0", project.get("description", ""))

        # Project tags
        ttk.Label(self.top, text=t_func("project_tags")).grid(row=2, column=0, padx=8, pady=6, sticky=tk.W)
        self.tags_entry = ttk.Entry(self.top, width=30)
        existing_tags = project.get("tags", [])
        self.tags_entry.insert(0, ",".join(existing_tags) if existing_tags else "")
        self.tags_entry.grid(row=2, column=1, padx=8, pady=6, sticky=tk.EW)
        ttk.Label(self.top, text=t_func("project_tags_hint"), foreground="gray", font=("", 8)).grid(
            row=3, column=1, padx=8, pady=(0, 2), sticky=tk.W)

        ttk.Button(self.top, text="OK", command=self._ok).grid(row=4, column=0, columnspan=2, pady=10)

    def _ok(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("", self.t_func("name_required"))
            return
        tags_str = self.tags_entry.get().strip()
        tags_str = tags_str.replace("\uff0c", ",")  # Chinese comma → ASCII comma
        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []
        self.result = {"name": name, "description": self.desc_text.get("1.0", tk.END).strip(), "tags": tags}
        self.top.destroy()


class MilestoneEditDialog:
    """Dialog for editing milestone name, description and deadline"""
    def __init__(self, parent, t_func, lang, milestone):
        self.result = None
        self.top = tk.Toplevel(parent)
        self.top.title("✏ " + t_func("edit_milestone"))
        _center_dialog(self.top, parent, 400, 250)
        self.top.transient(parent)
        self.top.grab_set()
        self.top.focus_set()
        self.top.bind("<Escape>", lambda e: self.top.destroy())

        self.top.columnconfigure(1, weight=1)
        self.top.rowconfigure(2, weight=1)

        ttk.Label(self.top, text=t_func("milestone_name")).grid(row=0, column=0, padx=8, pady=5, sticky=tk.W)
        self.name_entry = ttk.Entry(self.top, width=30)
        self.name_entry.insert(0, milestone.get("name", ""))
        self.name_entry.grid(row=0, column=1, padx=8, pady=5, sticky=tk.EW)

        ttk.Label(self.top, text=t_func("end_date") + " (YYYYMMDD)").grid(row=1, column=0, padx=8, pady=5, sticky=tk.W)
        self.deadline_entry = ttk.Entry(self.top, width=30)
        self.deadline_entry.insert(0, milestone.get("deadline", ""))
        self.deadline_entry.grid(row=1, column=1, padx=8, pady=5, sticky=tk.EW)

        ttk.Label(self.top, text=t_func("description")).grid(row=2, column=0, padx=8, pady=5, sticky=tk.NW)
        self.desc_text = tk.Text(self.top, width=30, height=4, wrap=tk.WORD, undo=True)
        self.desc_text.insert("1.0", milestone.get("description", ""))
        self.desc_text.grid(row=2, column=1, padx=8, pady=5, sticky=tk.NSEW)

        ttk.Button(self.top, text="OK", command=self._ok).grid(row=3, column=0, columnspan=2, pady=(5, 8))

    def _ok(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("", "Name is required")
            return
        self.result = {
            "name": name,
            "description": self.desc_text.get("1.0", tk.END).strip(),
            "deadline": self.deadline_entry.get().strip(),
        }
        self.top.destroy()


class ActivityEditDialog:
    """Dialog for editing an existing activity"""
    def __init__(self, parent, t_func, lang, activity, project_tags=None):
        self.result = None
        self.t_func = t_func
        self.project_tags = project_tags or []
        self.top = tk.Toplevel(parent)
        self.top.title("✏ " + t_func("edit_activity"))
        _center_dialog(self.top, parent, 420, 440)
        self.top.transient(parent)
        self.top.grab_set()
        self.top.focus_set()
        self.top.bind("<Escape>", lambda e: self.top.destroy())
        self.top.columnconfigure(1, weight=1)

        row = 0
        fields = [
            ("executor", t_func("executor"), activity.get("executor", "")),
            ("date", t_func("date") + " (YYYYMMDD, " + t_func("optional") + ")", activity.get("date", "")),
            ("content", t_func("content"), activity.get("content", "")),
        ]
        self.entries = {}
        for key, label, val in fields:
            ttk.Label(self.top, text=label).grid(row=row, column=0, padx=8, pady=4, sticky=tk.W)
            entry = ttk.Entry(self.top, width=30)
            entry.insert(0, val)
            entry.grid(row=row, column=1, padx=8, pady=4, sticky=tk.EW)
            self.entries[key] = entry
            row += 1

        # Determine if existing activity used direct hours (no time_slots)
        existing_ts = activity.get("time_slots", "")
        existing_hours = activity.get("hours", 0.0)

        # Effort hours field
        ttk.Label(self.top, text=t_func("effort_hours")).grid(row=row, column=0, padx=8, pady=4, sticky=tk.W)
        hours_entry = ttk.Entry(self.top, width=30)
        if not existing_ts and existing_hours:
            hours_entry.insert(0, str(existing_hours))
        hours_entry.grid(row=row, column=1, padx=8, pady=4, sticky=tk.EW)
        self.entries["effort_hours"] = hours_entry
        row += 1
        ttk.Label(self.top, text=t_func("effort_hours_hint"), foreground="gray", font=("", 8)).grid(
            row=row, column=1, padx=8, pady=(0, 2), sticky=tk.W)
        row += 1

        # Time slots field
        ttk.Label(self.top, text=t_func("time_slots")).grid(row=row, column=0, padx=8, pady=4, sticky=tk.W)
        ts_entry = ttk.Entry(self.top, width=30)
        ts_entry.insert(0, existing_ts)
        ts_entry.grid(row=row, column=1, padx=8, pady=4, sticky=tk.EW)
        self.entries["time_slots"] = ts_entry
        row += 1
        ttk.Label(self.top, text=t_func("time_slots_hint"), foreground="gray", font=("", 8)).grid(
            row=row, column=1, padx=8, pady=(0, 2), sticky=tk.W)
        row += 1

        # Mutual exclusion hint
        ttk.Label(self.top, text=t_func("time_slots_or_hours_hint"), foreground="orange", font=("", 8)).grid(
            row=row, column=0, columnspan=2, padx=8, pady=(0, 2), sticky=tk.W)
        row += 1

        # Tag field — Combobox if project has tags, otherwise Entry
        ttk.Label(self.top, text=t_func("tag")).grid(row=row, column=0, padx=8, pady=4, sticky=tk.W)
        if self.project_tags:
            tag_combo = ttk.Combobox(self.top, width=28, values=[""] + self.project_tags)
            tag_combo.set(activity.get("tag", ""))
            tag_combo.grid(row=row, column=1, padx=8, pady=4, sticky=tk.EW)
            self.entries["tag"] = tag_combo
        else:
            tag_entry = ttk.Entry(self.top, width=30)
            tag_entry.insert(0, activity.get("tag", ""))
            tag_entry.grid(row=row, column=1, padx=8, pady=4, sticky=tk.EW)
            self.entries["tag"] = tag_entry
        row += 1

        # Description field (multi-line text with scrollbar)
        ttk.Label(self.top, text=t_func("description")).grid(row=row, column=0, padx=8, pady=4, sticky=tk.NW)
        desc_frame = ttk.Frame(self.top)
        desc_frame.grid(row=row, column=1, padx=8, pady=4, sticky=tk.NSEW)
        self.top.rowconfigure(row, weight=1)
        self.desc_text = tk.Text(desc_frame, width=30, height=4, wrap=tk.WORD, undo=True)
        desc_sb = ttk.Scrollbar(desc_frame, orient=tk.VERTICAL, command=self.desc_text.yview)
        self.desc_text.configure(yscrollcommand=desc_sb.set)
        self.desc_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        desc_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.desc_text.insert("1.0", activity.get("description", ""))
        row += 1

        ttk.Button(self.top, text="OK", command=self._ok).grid(
            row=row, column=0, columnspan=2, pady=12)

    def _ok(self):
        executor = self.entries["executor"].get().strip()
        date = self.entries["date"].get().strip()
        content = self.entries["content"].get().strip()
        effort_hours_str = self.entries["effort_hours"].get().strip()
        time_slots = self.entries["time_slots"].get().strip()
        tag = self.entries["tag"].get().strip()
        description = self.desc_text.get("1.0", tk.END).strip()
        if not executor or not content:
            return
        # Validate date format (only if date is provided)
        if date and (len(date) != 8 or not date.isdigit()):
            messagebox.showwarning("", self.t_func("invalid_date"))
            return
        # Mutual exclusion: cannot fill both
        if effort_hours_str and time_slots:
            messagebox.showwarning("", self.t_func("hours_conflict"))
            return
        # Validate effort_hours if provided
        if effort_hours_str:
            try:
                hours = float(effort_hours_str)
            except ValueError:
                messagebox.showwarning("", self.t_func("invalid_hours"))
                return
            if hours < 0:
                messagebox.showwarning("", self.t_func("hours_non_negative"))
                return
        else:
            hours = 0.0
        # Validate time_slots if provided
        if time_slots:
            try:
                parse_time_slots(time_slots)
            except ValueError:
                messagebox.showwarning("", self.t_func("invalid_time_slots"))
                return
            hours = calculate_hours_from_slots(time_slots)
        self.result = {"executor": executor, "date": date, "hours": hours,
                       "content": content, "time_slots": time_slots, "tag": tag,
                       "description": description}
        self.top.destroy()


class ProjectGitConfigDialog:
    """Dialog for configuring project Git remote"""
    def __init__(self, parent, t_func, lang, project):
        self.result = None
        self.t_func = t_func
        self.lang = lang
        self.top = tk.Toplevel(parent)
        self.top.title("🔗 " + t_func("git_config"))
        _center_dialog(self.top, parent, 500, 380)
        self.top.transient(parent)
        self.top.grab_set()
        self.top.focus_set()
        self.top.bind("<Escape>", lambda e: self.top.destroy())
        self.top.columnconfigure(1, weight=1)

        fields = [
            ("remote_url", t_func("remote_url"), project.get("remote_url", "")),
            ("remote_branch", t_func("remote_branch") if lang == "en" else "远端主分支", project.get("remote_branch", "main")),
            ("remote_username", t_func("username"), project.get("remote_username", "")),
            ("remote_password", t_func("password"), project.get("remote_password", "")),
            ("committer_name", t_func("committer_name"), project.get("committer_name", "")),
            ("committer_email", t_func("committer_email"), project.get("committer_email", "")),
            ("priv_branch", t_func("priv_branch"), project.get("priv_branch", "")),
        ]
        self.entries = {}
        for i, (key, label, val) in enumerate(fields):
            ttk.Label(self.top, text=label).grid(row=i, column=0, padx=8, pady=5, sticky=tk.W)
            entry = ttk.Entry(self.top, width=40)
            entry.insert(0, val)
            if key == "remote_password":
                entry.configure(show="*")
            entry.grid(row=i, column=1, padx=8, pady=5, sticky=tk.EW)
            self.entries[key] = entry

        ttk.Button(self.top, text="OK", command=self._ok).grid(
            row=len(fields), column=0, columnspan=2, pady=10)

    def _ok(self):
        url = self.entries["remote_url"].get().strip()
        if url and not (re.match(r'^(https?://|git@)', url) or os.path.isabs(url)):
            messagebox.showwarning("", self.t_func("invalid_url"))
            return

        committer_name = self.entries["committer_name"].get().strip()
        committer_email = self.entries["committer_email"].get().strip()
        priv_branch = self.entries["priv_branch"].get().strip()

        # Auto-detect git user if committer fields are empty
        if not committer_name or not committer_email:
            detected_name, detected_email = GitSync.detect_git_user()
            if detected_name or detected_email:
                name_to_use = committer_name or detected_name
                email_to_use = committer_email or detected_email
                if messagebox.askyesno(
                    self.t_func("git_config"),
                    self.t_func("detect_git_user_confirm", name_to_use, email_to_use),
                ):
                    committer_name = name_to_use
                    committer_email = email_to_use
                else:
                    return
            else:
                # Auto-detect failed and fields still empty — block save
                if not committer_name or not committer_email:
                    messagebox.showwarning(self.t_func("warning"), self.t_func("committer_required"))
                    return

        # Validate private branch name
        main_branch = self.entries["remote_branch"].get().strip() or "main"
        valid, err_key = validate_priv_branch_name(priv_branch, main_branch)
        if not valid:
            messagebox.showwarning("", self.t_func(err_key))
            return

        # Show priv_branch default hint
        if not priv_branch and committer_name:
            default_branch = f"priv_{committer_name}"
            messagebox.showinfo(
                self.t_func("git_config"),
                self.t_func("priv_branch_auto", default_branch),
            )

        self.result = {
            "remote_url": url,
            "remote_branch": main_branch,
            "remote_username": self.entries["remote_username"].get().strip(),
            "remote_password": self.entries["remote_password"].get().strip(),
            "committer_name": committer_name,
            "committer_email": committer_email,
            "priv_branch": priv_branch,
        }
        self.top.destroy()


class PlaceholderEntry(ttk.Entry):
    """带占位提示文字的 Entry 控件"""

    def __init__(self, master, placeholder="", **kwargs):
        self._show_char = kwargs.pop("show", None)
        super().__init__(master, **kwargs)
        self.placeholder = placeholder
        self._is_placeholder = True
        self._show_placeholder()
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)

    def _show_placeholder(self):
        """显示占位提示文字（灰色）"""
        self.configure(show="")
        self.delete(0, tk.END)
        self.insert(0, self.placeholder)
        self.configure(foreground="gray")
        self._is_placeholder = True

    def _on_focus_in(self, event=None):
        """获得焦点时清除占位文字"""
        if self._is_placeholder:
            self.delete(0, tk.END)
            self.configure(foreground="")
            if self._show_char:
                self.configure(show=self._show_char)
            self._is_placeholder = False

    def _on_focus_out(self, event=None):
        """失去焦点且为空时恢复占位文字"""
        if not self.get():
            self.configure(show="")
            self._show_placeholder()

    def get_value(self) -> str:
        """获取实际值（排除占位文字）"""
        if self._is_placeholder:
            return ""
        return self.get()


def validate_remote_url(url: str) -> bool:
    """验证远端仓库地址格式：https://、http://、git@ 开头，或绝对路径"""
    if not url:
        return False
    return bool(re.match(r'^(https?://|git@)', url)) or os.path.isabs(url)


class ProjectCreateDialog:
    """Dialog for creating a new project with local/collaboration mode support."""

    DIALOG_SIZE_LOCAL = "450x200"
    DIALOG_SIZE_COLLAB = "500x480"

    def __init__(self, parent, t_func, lang):
        self.result = None
        self.t = t_func
        self.t_func = t_func  # backward compat alias
        self.lang = lang
        self.parent = parent

        self.top = tk.Toplevel(parent)
        self.top.title(t_func("add") + " " + t_func("project"))
        _center_dialog(self.top, parent, 450, 200)
        self.top.transient(parent)
        self.top.grab_set()
        self.top.focus_set()
        self.top.bind("<Escape>", lambda e: self.top.destroy())

        # ── Mode state variable ──
        self.mode_var = tk.StringVar(value="local")

        # ── Build UI sections ──
        self._build_mode_selector()
        self._build_local_fields()
        self._build_collab_fields()

        # ── OK button ──
        self.btn_frame = ttk.Frame(self.top)
        self.btn_frame.pack(pady=8)
        ttk.Button(self.btn_frame, text="OK", command=self._ok).pack()

        # ── Initialize display state ──
        self._on_mode_change()

    # ──────────────────────────────────────────────
    # Task 4.1: Mode selector
    # ──────────────────────────────────────────────
    def _build_mode_selector(self):
        """构建单选按钮组：本地模式 / 协作模式"""
        mode_frame = ttk.Frame(self.top)
        mode_frame.pack(fill=tk.X, padx=8, pady=(8, 4))

        ttk.Radiobutton(
            mode_frame, text=self.t("mode_local"),
            variable=self.mode_var, value="local",
            command=self._on_mode_change
        ).pack(side=tk.LEFT, padx=(0, 16))

        ttk.Radiobutton(
            mode_frame, text=self.t("mode_collab"),
            variable=self.mode_var, value="collab",
            command=self._on_mode_change
        ).pack(side=tk.LEFT)

    # ──────────────────────────────────────────────
    # Task 4.2: Local mode fields
    # ──────────────────────────────────────────────
    def _build_local_fields(self):
        """项目名称 + 描述（始终显示）"""
        self.local_frame = ttk.Frame(self.top)
        self.local_frame.pack(fill=tk.X, padx=8, pady=2)
        self.local_frame.columnconfigure(1, weight=1)

        # Project name (required)
        ttk.Label(self.local_frame, text=self.t("project_name")).grid(
            row=0, column=0, padx=4, pady=4, sticky=tk.W)
        self.name_entry = PlaceholderEntry(
            self.local_frame, placeholder=self.t("ph_project_name"), width=35)
        self.name_entry.grid(row=0, column=1, padx=4, pady=4, sticky=tk.EW)

        # Description (optional)
        desc_label = self.t("description") + " " + self.t("desc_optional")
        ttk.Label(self.local_frame, text=desc_label).grid(
            row=1, column=0, padx=4, pady=4, sticky=tk.W)
        self.desc_entry = PlaceholderEntry(
            self.local_frame, placeholder=self.t("ph_description"), width=35)
        self.desc_entry.grid(row=1, column=1, padx=4, pady=4, sticky=tk.EW)

    # ──────────────────────────────────────────────
    # Task 4.3: Collaboration mode fields
    # ──────────────────────────────────────────────
    def _build_collab_fields(self):
        """Git 配置字段组（仅协作模式显示）"""
        self.collab_frame = ttk.Frame(self.top)
        self.collab_frame.columnconfigure(1, weight=1)

        row = 0
        # 1. Remote URL
        ttk.Label(self.collab_frame, text=self.t("remote_url")).grid(
            row=row, column=0, padx=4, pady=3, sticky=tk.W)
        self.url_entry = PlaceholderEntry(
            self.collab_frame, placeholder=self.t("ph_remote_url"), width=35)
        self.url_entry.grid(row=row, column=1, padx=4, pady=3, sticky=tk.EW)

        # 2. Remote branch (prefilled "main")
        row += 1
        ttk.Label(self.collab_frame, text=self.t("remote_branch")).grid(
            row=row, column=0, padx=4, pady=3, sticky=tk.W)
        self.branch_entry = PlaceholderEntry(
            self.collab_frame, placeholder=self.t("ph_remote_branch"), width=35)
        # Pre-fill with "main"
        self.branch_entry.delete(0, tk.END)
        self.branch_entry.insert(0, "main")
        self.branch_entry.configure(foreground="")
        self.branch_entry._is_placeholder = False
        self.branch_entry.grid(row=row, column=1, padx=4, pady=3, sticky=tk.EW)

        # 3. Username
        row += 1
        ttk.Label(self.collab_frame, text=self.t("username")).grid(
            row=row, column=0, padx=4, pady=3, sticky=tk.W)
        self.username_entry = PlaceholderEntry(
            self.collab_frame, placeholder=self.t("ph_username"), width=35)
        self.username_entry.grid(row=row, column=1, padx=4, pady=3, sticky=tk.EW)

        # 4. Password/Token (masked)
        row += 1
        ttk.Label(self.collab_frame, text=self.t("password")).grid(
            row=row, column=0, padx=4, pady=3, sticky=tk.W)
        self.password_entry = PlaceholderEntry(
            self.collab_frame, placeholder=self.t("ph_password"),
            width=35, show="*")
        self.password_entry.grid(row=row, column=1, padx=4, pady=3, sticky=tk.EW)

        # 5. Committer name
        row += 1
        ttk.Label(self.collab_frame, text=self.t("committer_name")).grid(
            row=row, column=0, padx=4, pady=3, sticky=tk.W)
        self.committer_name_entry = PlaceholderEntry(
            self.collab_frame, placeholder=self.t("ph_committer_name"), width=35)
        self.committer_name_entry.grid(row=row, column=1, padx=4, pady=3, sticky=tk.EW)

        # 6. Committer email
        row += 1
        ttk.Label(self.collab_frame, text=self.t("committer_email")).grid(
            row=row, column=0, padx=4, pady=3, sticky=tk.W)
        self.committer_email_entry = PlaceholderEntry(
            self.collab_frame, placeholder=self.t("ph_committer_email"), width=35)
        self.committer_email_entry.grid(row=row, column=1, padx=4, pady=3, sticky=tk.EW)

        # 7. Private branch name
        row += 1
        ttk.Label(self.collab_frame, text=self.t("priv_branch")).grid(
            row=row, column=0, padx=4, pady=3, sticky=tk.W)
        self.priv_branch_entry = PlaceholderEntry(
            self.collab_frame, placeholder=self.t("ph_priv_branch"), width=35)
        self.priv_branch_entry.grid(row=row, column=1, padx=4, pady=3, sticky=tk.EW)

    # ──────────────────────────────────────────────
    # Task 4.4: Mode switching logic
    # ──────────────────────────────────────────────
    def _on_mode_change(self):
        """模式切换回调：显示/隐藏协作模式字段组，调整对话框尺寸"""
        if self.mode_var.get() == "collab":
            self.collab_frame.pack(fill=tk.X, padx=8, pady=2,
                                   before=self.btn_frame)
            _center_dialog(self.top, self.parent, 500, 480)
        else:
            self.collab_frame.pack_forget()
            _center_dialog(self.top, self.parent, 450, 200)

    # ──────────────────────────────────────────────
    # Task 4.5: Validation and confirm logic
    # ──────────────────────────────────────────────
    def _detect_git_user(self):
        """尝试自动检测系统 Git 用户信息"""
        try:
            name = subprocess.check_output(
                ["git", "config", "user.name"],
                stderr=subprocess.DEVNULL
            ).decode().strip()
        except Exception:
            name = ""
        try:
            email = subprocess.check_output(
                ["git", "config", "user.email"],
                stderr=subprocess.DEVNULL
            ).decode().strip()
        except Exception:
            email = ""
        return name, email

    def _ok(self):
        name = self.name_entry.get_value().strip()
        mode = self.mode_var.get()

        # If collaboration mode and no name given, derive from URL
        if mode == "collab":
            remote_url = self.url_entry.get_value().strip()
            if not name and remote_url:
                url_path = remote_url.rstrip("/")
                if url_path.endswith(".git"):
                    url_path = url_path[:-4]
                name = os.path.basename(url_path)

        # Validate project name
        if not name:
            messagebox.showwarning(self.t("warning"), self.t("name_required"))
            return

        if mode == "local":
            # Local mode: simple result
            self.result = {
                "name": name,
                "description": self.desc_entry.get_value().strip(),
                "remote_url": "",
                "remote_branch": "main",
            }
            self.top.destroy()
        else:
            # Collaboration mode: validate and build full result
            remote_url = self.url_entry.get_value().strip()
            if not remote_url:
                messagebox.showwarning(self.t("warning"), self.t("url_required"))
                return
            if not validate_remote_url(remote_url):
                messagebox.showwarning(self.t("warning"), self.t("invalid_url_format"))
                return

            committer_name = self.committer_name_entry.get_value().strip()
            committer_email = self.committer_email_entry.get_value().strip()

            # Auto-detect git user if committer info is empty
            if not committer_name or not committer_email:
                detected_name, detected_email = self._detect_git_user()
                if detected_name and detected_email:
                    msg = self.t("detect_git_user_confirm").format(
                        detected_name, detected_email)
                    if messagebox.askyesno(self.t("warning"), msg):
                        if not committer_name:
                            committer_name = detected_name
                        if not committer_email:
                            committer_email = detected_email
                    else:
                        return
                else:
                    messagebox.showwarning(
                        self.t("warning"), self.t("committer_required"))
                    return

            priv_branch = self.priv_branch_entry.get_value().strip()
            main_branch = self.branch_entry.get_value().strip() or "main"

            # Validate private branch name
            valid, err_key = validate_priv_branch_name(priv_branch, main_branch)
            if not valid:
                messagebox.showwarning("", self.t(err_key))
                return

            self.result = {
                "name": name,
                "description": self.desc_entry.get_value().strip(),
                "remote_url": remote_url,
                "remote_branch": main_branch,
                "remote_username": self.username_entry.get_value().strip(),
                "remote_password": self.password_entry.get_value().strip(),
                "committer_name": committer_name,
                "committer_email": committer_email,
                "priv_branch": priv_branch,
            }
            self.top.destroy()


class MilestoneCreateDialog:
    """Dialog for creating a new milestone with all fields."""
    def __init__(self, parent, t_func, lang):
        self.result = None
        self.t_func = t_func
        self.top = tk.Toplevel(parent)
        self.top.title(t_func("add") + " " + t_func("milestone"))
        _center_dialog(self.top, parent, 450, 280)
        self.top.transient(parent)
        self.top.grab_set()
        self.top.focus_set()
        self.top.bind("<Escape>", lambda e: self.top.destroy())

        self.top.columnconfigure(1, weight=1)
        self.top.rowconfigure(3, weight=1)

        ttk.Label(self.top, text=t_func("milestone_name") + " *").grid(row=0, column=0, padx=8, pady=5, sticky=tk.W)
        self.name_entry = ttk.Entry(self.top, width=30)
        self.name_entry.grid(row=0, column=1, padx=8, pady=5, sticky=tk.EW)

        ttk.Label(self.top, text=t_func("end_date") + " (YYYYMMDD)").grid(row=1, column=0, padx=8, pady=5, sticky=tk.W)
        self.deadline_entry = ttk.Entry(self.top, width=30)
        self.deadline_entry.grid(row=1, column=1, padx=8, pady=5, sticky=tk.EW)

        ttk.Label(self.top, text="🎨 " + t_func("color")).grid(row=2, column=0, padx=8, pady=5, sticky=tk.W)
        self.color_entry = ttk.Entry(self.top, width=30)
        self.color_entry.grid(row=2, column=1, padx=8, pady=5, sticky=tk.EW)

        ttk.Label(self.top, text=t_func("description")).grid(row=3, column=0, padx=8, pady=5, sticky=tk.NW)
        self.desc_text = tk.Text(self.top, width=30, height=4, wrap=tk.WORD)
        self.desc_text.grid(row=3, column=1, padx=8, pady=5, sticky=tk.NSEW)

        ttk.Button(self.top, text="OK", command=self._ok).grid(row=4, column=0, columnspan=2, pady=(5, 8))

    def _ok(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning(self.t_func("warning"), self.t_func("name_required"))
            return
        self.result = {
            "name": name,
            "description": self.desc_text.get("1.0", tk.END).strip(),
            "deadline": self.deadline_entry.get().strip(),
            "color": self.color_entry.get().strip(),
        }
        self.top.destroy()


class RequirementDialog:
    """Dialog for adding a requirement"""
    def __init__(self, parent, t_func, lang):
        self.result = None
        self.t_func = t_func
        self.top = tk.Toplevel(parent)
        self.top.title(t_func("add_requirement"))
        _center_dialog(self.top, parent, 420, 280)
        self.top.transient(parent)
        self.top.grab_set()
        self.top.focus_set()
        self.top.bind("<Escape>", lambda e: self.top.destroy())
        self.top.columnconfigure(1, weight=1)
        self.top.rowconfigure(2, weight=1)

        ttk.Label(self.top, text=t_func("category")).grid(row=0, column=0, padx=8, pady=5, sticky=tk.W)
        self.category_entry = ttk.Entry(self.top, width=30)
        self.category_entry.grid(row=0, column=1, padx=8, pady=5, sticky=tk.EW)

        ttk.Label(self.top, text=t_func("subject") + " *").grid(row=1, column=0, padx=8, pady=5, sticky=tk.W)
        self.subject_entry = ttk.Entry(self.top, width=30)
        self.subject_entry.grid(row=1, column=1, padx=8, pady=5, sticky=tk.EW)

        ttk.Label(self.top, text=t_func("description")).grid(row=2, column=0, padx=8, pady=5, sticky=tk.NW)
        desc_frame = ttk.Frame(self.top)
        desc_frame.grid(row=2, column=1, padx=8, pady=5, sticky=tk.NSEW)
        self.desc_text = tk.Text(desc_frame, width=30, height=6, wrap=tk.WORD, undo=True)
        desc_sb = ttk.Scrollbar(desc_frame, orient=tk.VERTICAL, command=self.desc_text.yview)
        self.desc_text.configure(yscrollcommand=desc_sb.set)
        self.desc_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        desc_sb.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Button(self.top, text="OK", command=self._ok).grid(row=3, column=0, columnspan=2, pady=10)

    def _ok(self):
        subject = self.subject_entry.get().strip()
        if not subject:
            messagebox.showwarning("", self.t_func("subject_required"))
            return
        self.result = {
            "category": self.category_entry.get().strip(),
            "subject": subject,
            "description": self.desc_text.get("1.0", tk.END).strip(),
        }
        self.top.destroy()


class RequirementEditDialog:
    """Dialog for editing an existing requirement"""
    def __init__(self, parent, t_func, lang, requirement):
        self.result = None
        self.t_func = t_func
        self.top = tk.Toplevel(parent)
        self.top.title(t_func("edit_requirement"))
        _center_dialog(self.top, parent, 420, 280)
        self.top.transient(parent)
        self.top.grab_set()
        self.top.focus_set()
        self.top.bind("<Escape>", lambda e: self.top.destroy())
        self.top.columnconfigure(1, weight=1)
        self.top.rowconfigure(2, weight=1)

        ttk.Label(self.top, text=t_func("category")).grid(row=0, column=0, padx=8, pady=5, sticky=tk.W)
        self.category_entry = ttk.Entry(self.top, width=30)
        self.category_entry.insert(0, requirement.get("category", ""))
        self.category_entry.grid(row=0, column=1, padx=8, pady=5, sticky=tk.EW)

        ttk.Label(self.top, text=t_func("subject") + " *").grid(row=1, column=0, padx=8, pady=5, sticky=tk.W)
        self.subject_entry = ttk.Entry(self.top, width=30)
        self.subject_entry.insert(0, requirement.get("subject", ""))
        self.subject_entry.grid(row=1, column=1, padx=8, pady=5, sticky=tk.EW)

        ttk.Label(self.top, text=t_func("description")).grid(row=2, column=0, padx=8, pady=5, sticky=tk.NW)
        desc_frame = ttk.Frame(self.top)
        desc_frame.grid(row=2, column=1, padx=8, pady=5, sticky=tk.NSEW)
        self.desc_text = tk.Text(desc_frame, width=30, height=6, wrap=tk.WORD, undo=True)
        desc_sb = ttk.Scrollbar(desc_frame, orient=tk.VERTICAL, command=self.desc_text.yview)
        self.desc_text.configure(yscrollcommand=desc_sb.set)
        self.desc_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        desc_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.desc_text.insert("1.0", requirement.get("description", ""))

        ttk.Button(self.top, text="OK", command=self._ok).grid(row=3, column=0, columnspan=2, pady=10)

    def _ok(self):
        subject = self.subject_entry.get().strip()
        if not subject:
            messagebox.showwarning("", self.t_func("subject_required"))
            return
        self.result = {
            "category": self.category_entry.get().strip(),
            "subject": subject,
            "description": self.desc_text.get("1.0", tk.END).strip(),
        }
        self.top.destroy()


class TaskDialog:
    """Dialog for adding a task"""
    def __init__(self, parent, t_func, lang):
        self.result = None
        self.t_func = t_func
        self.top = tk.Toplevel(parent)
        self.top.title(t_func("add_task"))
        _center_dialog(self.top, parent, 420, 280)
        self.top.transient(parent)
        self.top.grab_set()
        self.top.focus_set()
        self.top.bind("<Escape>", lambda e: self.top.destroy())
        self.top.columnconfigure(1, weight=1)
        self.top.rowconfigure(2, weight=1)

        ttk.Label(self.top, text=t_func("subject") + " *").grid(row=0, column=0, padx=8, pady=5, sticky=tk.W)
        self.subject_entry = ttk.Entry(self.top, width=30)
        self.subject_entry.grid(row=0, column=1, padx=8, pady=5, sticky=tk.EW)

        ttk.Label(self.top, text=t_func("effort_days")).grid(row=1, column=0, padx=8, pady=5, sticky=tk.W)
        self.effort_entry = ttk.Entry(self.top, width=30)
        self.effort_entry.insert(0, "0")
        self.effort_entry.grid(row=1, column=1, padx=8, pady=5, sticky=tk.EW)

        ttk.Label(self.top, text=t_func("description")).grid(row=2, column=0, padx=8, pady=5, sticky=tk.NW)
        desc_frame = ttk.Frame(self.top)
        desc_frame.grid(row=2, column=1, padx=8, pady=5, sticky=tk.NSEW)
        self.desc_text = tk.Text(desc_frame, width=30, height=6, wrap=tk.WORD, undo=True)
        desc_sb = ttk.Scrollbar(desc_frame, orient=tk.VERTICAL, command=self.desc_text.yview)
        self.desc_text.configure(yscrollcommand=desc_sb.set)
        self.desc_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        desc_sb.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Button(self.top, text="OK", command=self._ok).grid(row=3, column=0, columnspan=2, pady=10)

    def _ok(self):
        subject = self.subject_entry.get().strip()
        if not subject:
            messagebox.showwarning("", self.t_func("subject_required"))
            return
        try:
            effort = float(self.effort_entry.get().strip())
        except ValueError:
            messagebox.showwarning("", self.t_func("invalid_effort"))
            return
        if effort < 0:
            messagebox.showwarning("", self.t_func("effort_non_negative"))
            return
        self.result = {
            "subject": subject,
            "effort_days": effort,
            "description": self.desc_text.get("1.0", tk.END).strip(),
        }
        self.top.destroy()


class TaskEditDialog:
    """Dialog for editing an existing task"""
    def __init__(self, parent, t_func, lang, task):
        self.result = None
        self.t_func = t_func
        self.top = tk.Toplevel(parent)
        self.top.title(t_func("edit_task"))
        _center_dialog(self.top, parent, 420, 280)
        self.top.transient(parent)
        self.top.grab_set()
        self.top.focus_set()
        self.top.bind("<Escape>", lambda e: self.top.destroy())
        self.top.columnconfigure(1, weight=1)
        self.top.rowconfigure(2, weight=1)

        ttk.Label(self.top, text=t_func("subject") + " *").grid(row=0, column=0, padx=8, pady=5, sticky=tk.W)
        self.subject_entry = ttk.Entry(self.top, width=30)
        self.subject_entry.insert(0, task.get("subject", ""))
        self.subject_entry.grid(row=0, column=1, padx=8, pady=5, sticky=tk.EW)

        ttk.Label(self.top, text=t_func("effort_days")).grid(row=1, column=0, padx=8, pady=5, sticky=tk.W)
        self.effort_entry = ttk.Entry(self.top, width=30)
        self.effort_entry.insert(0, str(task.get("effort_days", 0)))
        self.effort_entry.grid(row=1, column=1, padx=8, pady=5, sticky=tk.EW)

        ttk.Label(self.top, text=t_func("description")).grid(row=2, column=0, padx=8, pady=5, sticky=tk.NW)
        desc_frame = ttk.Frame(self.top)
        desc_frame.grid(row=2, column=1, padx=8, pady=5, sticky=tk.NSEW)
        self.desc_text = tk.Text(desc_frame, width=30, height=6, wrap=tk.WORD, undo=True)
        desc_sb = ttk.Scrollbar(desc_frame, orient=tk.VERTICAL, command=self.desc_text.yview)
        self.desc_text.configure(yscrollcommand=desc_sb.set)
        self.desc_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        desc_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.desc_text.insert("1.0", task.get("description", ""))

        ttk.Button(self.top, text="OK", command=self._ok).grid(row=3, column=0, columnspan=2, pady=10)

    def _ok(self):
        subject = self.subject_entry.get().strip()
        if not subject:
            messagebox.showwarning("", self.t_func("subject_required"))
            return
        try:
            effort = float(self.effort_entry.get().strip())
        except ValueError:
            messagebox.showwarning("", self.t_func("invalid_effort"))
            return
        if effort < 0:
            messagebox.showwarning("", self.t_func("effort_non_negative"))
            return
        self.result = {
            "subject": subject,
            "effort_days": effort,
            "description": self.desc_text.get("1.0", tk.END).strip(),
        }
        self.top.destroy()


class ProgressDialog:
    """Dialog for setting plan progress (0-100 integer)."""
    def __init__(self, parent, t_func, lang):
        self.result = None
        self.t_func = t_func
        self.top = tk.Toplevel(parent)
        self.top.title(t_func("set_progress"))
        _center_dialog(self.top, parent, 350, 130)
        self.top.transient(parent)
        self.top.grab_set()
        self.top.focus_set()
        self.top.bind("<Escape>", lambda e: self.top.destroy())
        self.top.columnconfigure(1, weight=1)

        ttk.Label(self.top, text=t_func("progress_input")).grid(row=0, column=0, padx=8, pady=10, sticky=tk.W)
        self.progress_entry = ttk.Entry(self.top, width=10)
        self.progress_entry.grid(row=0, column=1, padx=8, pady=10, sticky=tk.EW)

        ttk.Button(self.top, text="OK", command=self._ok).grid(row=1, column=0, columnspan=2, pady=10)

    def _ok(self):
        val = self.progress_entry.get().strip()
        try:
            progress = int(val)
            if 0 <= progress <= 100:
                self.result = progress
                self.top.destroy()
                return
        except ValueError:
            pass
        messagebox.showwarning(self.t_func("warning"), self.t_func("invalid_progress"))


def main():
    root = tk.Tk()
    app = GanttPilotGUI(root)
    root.mainloop()
