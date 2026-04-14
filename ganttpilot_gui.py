#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GanttPilot - GUI Interface (tkinter) / 图形界面

All CRUD operations via right-click context menus on the tree.
"""

import copy
import os
import re
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog, colorchooser
import webbrowser
import urllib.request
import json

from ganttpilot_i18n import t
from ganttpilot_config import Config
from ganttpilot_core import DataStore
from ganttpilot_git import GitSync
from ganttpilot_gantt import GanttRenderer, generate_gantt_uml, generate_gantt_markdown
from version import VERSION

GITHUB_REPO = "matthewzu/GanttPilot"


class UpdateChecker:
    def __init__(self, current_version, language, callback):
        self.current_version = current_version
        self.language = language
        self.callback = callback

    def check(self):
        threading.Thread(target=self._do_check, daemon=True).start()

    def _do_check(self):
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            req = urllib.request.Request(url, headers={"User-Agent": "GanttPilot"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            tag = data.get("tag_name", "").lstrip("v")
            if tag and tag != self.current_version:
                # Find platform-specific asset URL
                asset_url = None
                platform = sys.platform
                for asset in data.get("assets", []):
                    name = asset.get("name", "").lower()
                    if platform == "win32" and name.endswith(".exe"):
                        asset_url = asset["browser_download_url"]
                    elif platform == "darwin" and name.endswith(".dmg"):
                        asset_url = asset["browser_download_url"]
                    elif platform.startswith("linux") and not name.endswith((".exe", ".dmg")):
                        asset_url = asset["browser_download_url"]
                dl_url = data.get("html_url", f"https://github.com/{GITHUB_REPO}/releases")
                self.callback(tag, dl_url, asset_url)
        except Exception:
            pass


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

        self.root.title(self._t("app_title") + f" v{VERSION}")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._set_icon()
        self._apply_saved_geometry()

        self.create_widgets()
        self.refresh_project_list()

        # Keyboard shortcuts for undo/redo
        self.root.bind("<Control-z>", self.do_undo)
        self.root.bind("<Control-y>", self.do_redo)

        # Tooltips for undo/redo buttons
        self._show_tooltip(self.undo_btn, self._t("undo_tooltip"))
        self._show_tooltip(self.redo_btn, self._t("redo_tooltip"))

        # Start background sync for all projects with remote_url
        threading.Thread(target=self._startup_sync, daemon=True).start()
        UpdateChecker(VERSION, self.lang, self._show_update_notification).check()

    def _t(self, key, *args):
        return t(key, self.lang, *args)

    def _apply_saved_geometry(self):
        geo = self.config.get("window_geometry", "1200x700")
        pos = self.config.get("window_position", "100,100")
        try:
            x, y = pos.split(",")
            self.root.geometry(f"{geo}+{x}+{y}")
        except Exception:
            self.root.geometry(geo)

    def _set_icon(self):
        """Set window icon from ganttpilot.ico"""
        try:
            ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ganttpilot.ico")
            if os.path.exists(ico_path):
                self.root.iconbitmap(ico_path)
        except Exception:
            pass

    def _startup_sync(self):
        """Sync all projects that have remote_url configured."""
        try:
            for proj in self.store.list_projects():
                if proj.get("remote_url"):
                    try:
                        gs = self._get_project_git(proj)
                        gs.init_repo()
                        gs.sync()
                    except Exception:
                        pass
            self.store.load()
            self.root.after(0, self.refresh_project_list)
        except Exception:
            pass

    def _show_update_notification(self, new_version, download_url, asset_url=None):
        def show():
            if not messagebox.askyesno(self._t("update_check"), self._t("update_available", new_version)):
                return
            if asset_url:
                # Auto-download in background
                self.status_var.set(self._t("downloading_update"))
                self.root.update()
                threading.Thread(target=lambda: self._download_update(asset_url, new_version), daemon=True).start()
            else:
                webbrowser.open(download_url)
        self.root.after(0, show)

    def _download_update(self, asset_url, new_version):
        """Download update with progress reporting."""
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
        ttk.Button(toolbar, text="⚙", command=self.open_config_dialog, width=3).pack(side=tk.RIGHT, padx=1)
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

        # Right: gantt + report
        right_frame = ttk.Frame(self.paned)
        self.paned.add(right_frame, weight=3)

        gantt_canvas_frame = ttk.Frame(right_frame)
        gantt_canvas_frame.pack(fill=tk.BOTH, expand=True)

        # Gantt zoom toolbar
        gantt_toolbar = ttk.Frame(gantt_canvas_frame)
        gantt_toolbar.pack(fill=tk.X, pady=(0, 2))
        ttk.Label(gantt_toolbar, text="🔍").pack(side=tk.LEFT, padx=2)
        ttk.Button(gantt_toolbar, text="+", command=self.gantt_zoom_in, width=2).pack(side=tk.LEFT, padx=1)
        ttk.Button(gantt_toolbar, text="-", command=self.gantt_zoom_out, width=2).pack(side=tk.LEFT, padx=1)

        self.gantt_canvas = tk.Canvas(gantt_canvas_frame, bg="white")
        gy = ttk.Scrollbar(gantt_canvas_frame, orient=tk.VERTICAL, command=self.gantt_canvas.yview)
        gx = ttk.Scrollbar(gantt_canvas_frame, orient=tk.HORIZONTAL, command=self.gantt_canvas.xview)
        self.gantt_canvas.configure(yscrollcommand=gy.set, xscrollcommand=gx.set)
        gy.pack(side=tk.RIGHT, fill=tk.Y)
        gx.pack(side=tk.BOTTOM, fill=tk.X)
        self.gantt_canvas.pack(fill=tk.BOTH, expand=True)

        # Time report
        report_label = ttk.Label(right_frame, text=self._t("time_report"))
        report_label.pack(anchor=tk.W, pady=(6, 2))
        cols = ("executor", "hours", "days")
        self.report_tree = ttk.Treeview(right_frame, columns=cols, show="headings", height=5)
        self.report_tree.heading("executor", text=self._t("executor"))
        self.report_tree.heading("hours", text=self._t("total_hours"))
        self.report_tree.heading("days", text=self._t("total_days"))
        self.report_tree.column("executor", width=150, anchor="center")
        self.report_tree.column("hours", width=100, anchor="center")
        self.report_tree.column("days", width=100, anchor="center")
        self.report_tree.pack(fill=tk.X, pady=(0, 4))

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
            menu.add_command(label=self._t("sync"), command=self.do_sync)
            menu.add_command(label=self._t("refresh"), command=self._full_refresh)
        else:
            self.tree.selection_set(item)
            values = self.tree.item(item, "values")
            if not values:
                return
            kind = values[0]

            if kind == "project":
                proj_name = values[1]
                menu.add_command(label=f"+ {self._t('milestone')}", command=self.add_milestone)
                menu.add_separator()
                menu.add_command(label=self._t("report"), command=self.generate_report)
                menu.add_command(label=f"✏ {self._t('edit_project')}", command=self.edit_project)
                menu.add_command(label=f"🔗 {self._t('git_config')}", command=self.config_project_git)
                menu.add_separator()
                menu.add_command(label=self._t("refresh"), command=self._full_refresh)
                menu.add_command(label=self._t("sync"), command=self.do_sync)
                menu.add_separator()
                menu.add_command(label=self._t("delete"), command=self.delete_selected)

            elif kind == "milestone":
                menu.add_command(label=f"+ {self._t('plan')}", command=self.add_plan)
                menu.add_separator()
                menu.add_command(label=f"✏ {self._t('edit_milestone')}", command=self.edit_milestone)
                menu.add_command(label="🎨 " + self._t("color"), command=self.pick_color_milestone)
                menu.add_separator()
                menu.add_command(label=self._t("delete"), command=self.delete_selected)

            elif kind == "plan":
                menu.add_command(label=f"+ {self._t('activity')}", command=self.add_activity)
                menu.add_separator()
                menu.add_command(label=f"✏ {self._t('content')}", command=self.edit_plan)
                menu.add_command(label="🎨 " + self._t("color"), command=self.pick_color_plan)
                menu.add_command(label=self._t("finish"), command=self.finish_selected_plan)
                menu.add_command(label=self._t("set_progress"), command=self.set_progress)
                menu.add_separator()
                menu.add_command(label=self._t("delete"), command=self.delete_selected)

            elif kind == "activity":
                menu.add_command(label=f"✏ {self._t('edit_activity')}", command=self.edit_activity)
                menu.add_command(label=self._t("delete"), command=self.delete_selected)

        menu.tk_popup(event.x_root, event.y_root)

    # ── Tree data ────────────────────────────────────────────
    def refresh_project_list(self):
        self.tree.delete(*self.tree.get_children())
        for proj in self.store.list_projects():
            pn = self.tree.insert("", tk.END, text=f"📁 {proj['name']}",
                                  values=("project", proj["name"]), open=True)
            for ms in proj.get("milestones", []):
                dl = f" [{ms['deadline']}]" if ms.get("deadline") else ""
                mn = self.tree.insert(pn, tk.END, text=f"📌 {ms['name']}{dl}",
                                      values=("milestone", proj["name"], ms["name"]))
                for plan in ms.get("plans", []):
                    icon = "✅" if plan["status"] == "finished" else "📋"
                    txt = f"{icon} {plan['content']} ({plan['executor']}) [{plan['start_date']}-{plan['end_date']}]"
                    plan_n = self.tree.insert(mn, tk.END, text=txt,
                                             values=("plan", proj["name"], ms["name"], plan["id"]))
                    for act in plan.get("activities", []):
                        atxt = f"⏱ {act['date']} {act['executor']} {act['hours']}h - {act['content']}"
                        self.tree.insert(plan_n, tk.END, text=atxt,
                                         values=("activity", proj["name"], ms["name"], plan["id"], act["id"]))

    def on_tree_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        if not values:
            return
        proj_name = values[1] if len(values) >= 2 else None
        if proj_name and proj_name != self.current_project:
            # Background sync the previous project before switching
            prev = self.current_project
            if prev:
                self._bg_sync_project(prev)
            self.current_project = proj_name
            self.refresh_gantt()
            self.refresh_time_report()

    def _full_refresh(self):
        self.store.load()
        self.refresh_project_list()
        self.refresh_gantt()
        self.refresh_time_report()

    def refresh_gantt(self):
        if not self.current_project:
            return
        proj = self.store.get_project(self.current_project)
        if not proj:
            return
        renderer = GanttRenderer(self.gantt_canvas, proj, self.lang, self.gantt_zoom)
        renderer.draw()
        self.status_var.set(f"{self._t('gantt_chart')}: {self.current_project}")

    def refresh_time_report(self):
        for item in self.report_tree.get_children():
            self.report_tree.delete(item)
        if not self.current_project:
            return
        report = self.store.get_time_report(self.current_project)
        for ex, data in sorted(report.items()):
            self.report_tree.insert("", tk.END, values=(ex, f"{data['hours']:.1f}", f"{data['days']:.2f}"))

    # ── CRUD via context menu ────────────────────────────────
    def add_project(self):
        dlg = ProjectCreateDialog(self.root, self._t, self.lang)
        self.root.wait_window(dlg.top)
        if not dlg.result:
            return
        name = dlg.result["name"]
        description = dlg.result.get("description", "")
        remote_url = dlg.result.get("remote_url", "")
        remote_branch = dlg.result.get("remote_branch", "main")
        self.undo_manager.save_snapshot()
        if remote_url:
            # Clone from remote
            self.status_var.set(self._t("cloning"))
            self.root.update()
            # Clone to a temp name first, then reconcile with project.json name
            tmp_dir = os.path.join(self.config.data_dir, f"_clone_tmp_{name}")
            try:
                gs = GitSync(tmp_dir, remote_url, main_branch=remote_branch)
                gs.clone_repo(remote_url, tmp_dir, remote_branch)
                # Read the actual project name from cloned project.json
                pj_file = os.path.join(tmp_dir, "project.json")
                if os.path.exists(pj_file):
                    with open(pj_file, "r", encoding="utf-8") as f:
                        pj_data = json.load(f)
                    real_name = pj_data.get("name", name)
                else:
                    # Empty repo — create initial project.json
                    real_name = name
                    from ganttpilot_core import _new_id
                    pj_data = {
                        "id": _new_id(),
                        "name": name,
                        "description": description,
                        "remote_url": remote_url,
                        "remote_username": "",
                        "remote_password": "",
                        "remote_branch": remote_branch,
                        "milestones": [],
                    }
                    with open(pj_file, "w", encoding="utf-8") as f:
                        json.dump(pj_data, f, ensure_ascii=False, indent=2)
                    # Commit the new project.json
                    gs_tmp = GitSync(tmp_dir, remote_url, main_branch=remote_branch)
                    gs_tmp.init_repo()
                    gs_tmp.commit(f"Initialize project: {name}")
                # Rename temp dir to the real project name
                final_dir = os.path.join(self.config.data_dir, real_name)
                if os.path.exists(final_dir):
                    import shutil
                    shutil.rmtree(tmp_dir)
                    messagebox.showerror(self._t("error"), self._t("name_duplicate", real_name))
                    return
                os.rename(tmp_dir, final_dir)
                self.store.load()
                self.refresh_project_list()
                self.refresh_gantt()
                self.status_var.set(self._t("project_added", real_name))
                self._update_undo_redo_buttons()
            except Exception as e:
                # Clean up temp dir on failure
                if os.path.exists(tmp_dir):
                    import shutil
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                messagebox.showerror(self._t("error"), self._t("clone_failed", str(e)))
                self.status_var.set(self._t("clone_failed", str(e)))
        else:
            result = self.store.add_project(name, description=description)
            if result:
                self._commit(f"Add project: {name}")
                self.refresh_project_list()
                self.status_var.set(self._t("project_added", name))
                self._update_undo_redo_buttons()

    def add_milestone(self):
        proj = self._get_selected_project()
        if not proj:
            return
        dlg = MilestoneCreateDialog(self.root, self._t, self.lang)
        self.root.wait_window(dlg.top)
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
        dlg = PlanDialog(self.root, self._t, self.lang)
        self.root.wait_window(dlg.top)
        if dlg.result:
            r = dlg.result
            self.undo_manager.save_snapshot()
            result = self.store.add_plan(proj, ms, r["content"], r["executor"],
                                         r["start_date"], r["end_date"],
                                         r["skip_non_workdays"], r["skip_dates"], r.get("color", ""))
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
        dlg = ActivityDialog(self.root, self._t, self.lang)
        self.root.wait_window(dlg.top)
        if dlg.result:
            r = dlg.result
            self.undo_manager.save_snapshot()
            result = self.store.add_activity(proj, ms, plan_id, r["executor"], r["date"], r["hours"], r["content"])
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
            self.store.delete_project(values[1])
            self._commit(f"Delete project: {values[1]}")
            self.current_project = None
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

    def set_progress(self):
        proj, ms, plan_id = self._get_selected_plan()
        if not plan_id:
            return
        dlg = ProgressDialog(self.root, self._t, self.lang)
        self.root.wait_window(dlg.top)
        if dlg.result is not None:
            self.undo_manager.save_snapshot()
            self.store.set_plan_progress(proj, ms, plan_id, dlg.result)
            self._commit(f"Set progress: {plan_id} -> {dlg.result}%")
            self.refresh_project_list()
            self.refresh_gantt()
            self._update_undo_redo_buttons()

    def load_example(self):
        example_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples", "demo_project.json")
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
        dlg = MilestoneEditDialog(self.root, self._t, self.lang, ms)
        self.root.wait_window(dlg.top)
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
        dlg = ProjectEditDialog(self.root, self._t, self.lang, proj)
        self.root.wait_window(dlg.top)
        if dlg.result:
            new_name = dlg.result["name"]
            new_desc = dlg.result.get("description", "")
            self.undo_manager.save_snapshot()
            # Update description
            proj["description"] = new_desc
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
        dlg = ActivityEditDialog(self.root, self._t, self.lang, activity)
        self.root.wait_window(dlg.top)
        if dlg.result:
            r = dlg.result
            self.undo_manager.save_snapshot()
            self.store.update_activity(proj_name, ms_name, plan_id, act_id,
                                       r["executor"], r["date"], r["hours"], r["content"])
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
        dlg = ProjectGitConfigDialog(self.root, self._t, self.lang, proj)
        self.root.wait_window(dlg.top)
        if dlg.result:
            self.undo_manager.save_snapshot()
            proj["remote_url"] = dlg.result["remote_url"]
            proj["remote_branch"] = dlg.result["remote_branch"]
            proj["remote_username"] = dlg.result["remote_username"]
            proj["remote_password"] = dlg.result["remote_password"]
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
        dlg = PlanEditDialog(self.root, self._t, self.lang, plan)
        self.root.wait_window(dlg.top)
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
        md = generate_gantt_markdown(proj, self.lang)
        path = filedialog.asksaveasfilename(
            defaultextension=".md", filetypes=[("Markdown", "*.md")],
            initialfile=f"{self.current_project}_report.md",
        )
        if path:
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

    # ── Config / Font / Language ─────────────────────────────
    def toggle_language(self):
        self.lang = "en" if self.lang == "zh" else "zh"
        self.config.language = self.lang
        self.config.save()
        self.root.title(self._t("app_title") + f" v{VERSION}")
        self.report_tree.heading("executor", text=self._t("executor"))
        self.report_tree.heading("hours", text=self._t("total_hours"))
        self.report_tree.heading("days", text=self._t("total_days"))
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
        if self.current_project:
            self.refresh_gantt()

    def open_config_dialog(self):
        dlg = ConfigDialog(self.root, self.config, self._t, self.lang)
        self.root.wait_window(dlg.top)
        if dlg.saved:
            self.store = DataStore(self.config.data_dir)
            self.undo_manager = UndoManager(self.store)
            self.refresh_project_list()

    def show_help(self):
        txt = {
            "zh": (f"GanttPilot v{VERSION} - 协作式项目管理器\n\n"
                   "右键点击树状图进行所有操作：\n"
                   "• 空白处右键 → 添加项目 / 加载示例 / 同步 / 刷新\n"
                   "• 项目右键 → 添加里程碑 / 编辑项目 / Git配置 / 生成报告 / 同步 / 删除\n"
                   "• 里程碑右键 → 添加计划 / 编辑里程碑 / 设置颜色 / 删除\n"
                   "• 计划右键 → 添加活动 / 编辑属性 / 设置颜色 / 设置进度 / 终结 / 删除\n"
                   "• 活动右键 → 编辑活动 / 删除\n\n"
                   "快捷键：Ctrl+Z 撤销 / Ctrl+Y 恢复\n"
                   "甘特图：🔍+/- 独立缩放\n\n"
                   "跳过日期格式：20260501 (添加节假日), -20260510 (让周末变工作日)\n\n"
                   f"GitHub: https://github.com/{GITHUB_REPO}"),
            "en": (f"GanttPilot v{VERSION} - Collaborative Project Manager\n\n"
                   "Right-click the tree for all operations:\n"
                   "• Empty area → Add project / Load example / Sync / Refresh\n"
                   "• Project → Add milestone / Edit / Git config / Report / Sync / Delete\n"
                   "• Milestone → Add plan / Edit / Color / Delete\n"
                   "• Plan → Add activity / Edit / Color / Set progress / Finish / Delete\n"
                   "• Activity → Edit / Delete\n\n"
                   "Shortcuts: Ctrl+Z Undo / Ctrl+Y Redo\n"
                   "Gantt: 🔍+/- independent zoom\n\n"
                   "Skip dates: 20260501 (add holiday), -20260510 (make weekend a workday)\n\n"
                   f"GitHub: https://github.com/{GITHUB_REPO}"),
        }
        messagebox.showinfo(self._t("help"), txt.get(self.lang, txt["en"]))

    def do_sync(self):
        if not self.current_project:
            self.status_var.set(self._t("select_project"))
            return
        proj = self.store.get_project(self.current_project)
        if not proj or not proj.get("remote_url"):
            self.status_var.set(self._t("no_remote"))
            return
        self.status_var.set(self._t("syncing"))
        self.root.update()
        try:
            gs = self._get_project_git(proj)
            gs.init_repo()
            gs.sync()
            self.store.load()
            self.refresh_project_list()
            self.refresh_gantt()
            self.refresh_time_report()
            self.status_var.set(self._t("sync_done"))
        except Exception as e:
            self.status_var.set(self._t("sync_fail", str(e)))

    def on_close(self):
        geo = self.root.geometry()
        try:
            size_part, x, y = geo.replace("+", " ").split()
            self.config.set("window_geometry", size_part)
            self.config.set("window_position", f"{x},{y}")
        except Exception:
            pass
        self.config.save()
        # Background sync current project (non-blocking)
        if self.current_project:
            self._bg_sync_project(self.current_project)
        self.root.destroy()

    def _bg_sync_project(self, proj_name):
        """Sync a project in a background thread (non-blocking)."""
        proj = self.store.get_project(proj_name)
        if not proj or not proj.get("remote_url"):
            return
        def _do():
            try:
                gs = self._get_project_git(proj)
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
        if self.undo_manager.redo():
            self.store.save()
            self.refresh_project_list()
            self.refresh_gantt()
            self.refresh_time_report()
            self._update_undo_redo_buttons()
            self.status_var.set(self._t("redo_done"))
        else:
            self.status_var.set(self._t("no_redo"))

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
    def __init__(self, parent, t_func, lang):
        self.result = None
        self.top = tk.Toplevel(parent)
        self.top.title(t_func("add") + " " + t_func("plan"))
        self.top.geometry("420x400")
        self.top.transient(parent)
        self.top.grab_set()

        fields = [
            ("content", t_func("content")),
            ("executor", t_func("executor")),
            ("start_date", t_func("start_date") + " (YYYYMMDD)"),
            ("end_date", t_func("end_date") + " (YYYYMMDD)"),
            ("skip_dates", t_func("skip_dates") + " (D1,D2,...)"),
            ("planned_hours", t_func("hours") + " (计划)"),
            ("color", "🎨 Color (#hex)"),
        ]
        self.entries = {}
        for i, (key, label) in enumerate(fields):
            ttk.Label(self.top, text=label).grid(row=i, column=0, padx=8, pady=3, sticky=tk.W)
            entry = ttk.Entry(self.top, width=30)
            entry.grid(row=i, column=1, padx=8, pady=3)
            self.entries[key] = entry

        self.skip_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.top, text=t_func("skip_non_workdays"), variable=self.skip_var).grid(
            row=len(fields), column=0, columnspan=2, padx=8, pady=3, sticky=tk.W)
        ttk.Button(self.top, text="OK", command=self._ok).grid(
            row=len(fields) + 1, column=0, columnspan=2, pady=10)

    def _ok(self):
        content = self.entries["content"].get().strip()
        executor = self.entries["executor"].get().strip()
        start = self.entries["start_date"].get().strip()
        end = self.entries["end_date"].get().strip()
        skip_str = self.entries["skip_dates"].get().strip()
        color = self.entries["color"].get().strip()
        skip_dates = [d.strip() for d in skip_str.split(",") if d.strip()] if skip_str else []
        try:
            planned_hours = float(self.entries["planned_hours"].get().strip() or "0")
        except ValueError:
            planned_hours = 0
        if content and executor and start and end:
            self.result = {
                "content": content, "executor": executor,
                "start_date": start, "end_date": end,
                "skip_non_workdays": self.skip_var.get(),
                "skip_dates": skip_dates, "color": color,
                "planned_hours": planned_hours,
            }
            self.top.destroy()


class PlanEditDialog:
    """Dialog for editing an existing plan's properties"""
    def __init__(self, parent, t_func, lang, plan):
        self.result = None
        self.top = tk.Toplevel(parent)
        self.top.title("✏ " + t_func("plan"))
        self.top.geometry("420x400")
        self.top.transient(parent)
        self.top.grab_set()

        fields = [
            ("content", t_func("content"), plan.get("content", "")),
            ("executor", t_func("executor"), plan.get("executor", "")),
            ("start_date", t_func("start_date"), plan.get("start_date", "")),
            ("end_date", t_func("end_date"), plan.get("end_date", "")),
            ("skip_dates", t_func("skip_dates"), ",".join(plan.get("skip_dates", []))),
            ("planned_hours", t_func("hours") + " (计划)", str(plan.get("planned_hours", 0))),
            ("color", "🎨 Color", plan.get("color", "")),
        ]
        self.entries = {}
        for i, (key, label, val) in enumerate(fields):
            ttk.Label(self.top, text=label).grid(row=i, column=0, padx=8, pady=3, sticky=tk.W)
            entry = ttk.Entry(self.top, width=30)
            entry.insert(0, val)
            entry.grid(row=i, column=1, padx=8, pady=3)
            self.entries[key] = entry

        self.skip_var = tk.BooleanVar(value=plan.get("skip_non_workdays", True))
        ttk.Checkbutton(self.top, text=t_func("skip_non_workdays"), variable=self.skip_var).grid(
            row=len(fields), column=0, columnspan=2, padx=8, pady=3, sticky=tk.W)
        ttk.Button(self.top, text="OK", command=self._ok).grid(
            row=len(fields) + 1, column=0, columnspan=2, pady=10)

    def _ok(self):
        skip_str = self.entries["skip_dates"].get().strip()
        try:
            planned_hours = float(self.entries["planned_hours"].get().strip() or "0")
        except ValueError:
            planned_hours = 0
        self.result = {
            "content": self.entries["content"].get().strip(),
            "executor": self.entries["executor"].get().strip(),
            "start_date": self.entries["start_date"].get().strip(),
            "end_date": self.entries["end_date"].get().strip(),
            "skip_dates": [d.strip() for d in skip_str.split(",") if d.strip()] if skip_str else [],
            "skip_non_workdays": self.skip_var.get(),
            "color": self.entries["color"].get().strip(),
            "planned_hours": planned_hours,
        }
        self.top.destroy()


class ActivityDialog:
    """Dialog for adding an activity"""
    def __init__(self, parent, t_func, lang):
        self.result = None
        self.top = tk.Toplevel(parent)
        self.top.title(t_func("add") + " " + t_func("activity"))
        self.top.geometry("400x240")
        self.top.transient(parent)
        self.top.grab_set()

        fields = [
            ("executor", t_func("executor")),
            ("date", t_func("date") + " (YYYYMMDD)"),
            ("hours", t_func("hours")),
            ("content", t_func("content")),
        ]
        self.entries = {}
        for i, (key, label) in enumerate(fields):
            ttk.Label(self.top, text=label).grid(row=i, column=0, padx=8, pady=4, sticky=tk.W)
            entry = ttk.Entry(self.top, width=30)
            entry.grid(row=i, column=1, padx=8, pady=4)
            self.entries[key] = entry
        ttk.Button(self.top, text="OK", command=self._ok).grid(
            row=len(fields), column=0, columnspan=2, pady=12)

    def _ok(self):
        executor = self.entries["executor"].get().strip()
        date = self.entries["date"].get().strip()
        hours_str = self.entries["hours"].get().strip()
        content = self.entries["content"].get().strip()
        try:
            hours = float(hours_str)
        except ValueError:
            return
        if executor and date and content:
            self.result = {"executor": executor, "date": date, "hours": hours, "content": content}
            self.top.destroy()


class ConfigDialog:
    """Dialog for editing global configuration"""
    def __init__(self, parent, config, t_func, lang):
        self.config = config
        self.saved = False
        self.top = tk.Toplevel(parent)
        self.top.title(t_func("config"))
        self.top.geometry("580x300")
        self.top.transient(parent)
        self.top.grab_set()

        fields = [
            ("data_dir", t_func("data_dir"), config.data_dir),
            ("remote_url", t_func("remote_url"), config.remote_url),
            ("remote_username", t_func("username"), config.remote_username),
            ("remote_password", t_func("password"), config.remote_password),
            ("config_dir", t_func("config_dir"), config.config_dir),
        ]
        path_fields = {"data_dir", "config_dir"}
        self.entries = {}
        for i, (key, label, val) in enumerate(fields):
            ttk.Label(self.top, text=label).grid(row=i, column=0, padx=8, pady=4, sticky=tk.W)
            entry = ttk.Entry(self.top, width=35)
            entry.insert(0, val or "")
            if key == "remote_password":
                entry.configure(show="*")
            entry.grid(row=i, column=1, padx=4, pady=4)
            self.entries[key] = entry
            if key in path_fields:
                ttk.Button(self.top, text="📂", width=3,
                           command=lambda e=entry: self._browse_dir(e)).grid(row=i, column=2, padx=2, pady=4)
        ttk.Button(self.top, text=t_func("save_config"), command=self._save).grid(
            row=len(fields), column=0, columnspan=3, pady=12)

    def _browse_dir(self, entry):
        current = entry.get().strip()
        path = filedialog.askdirectory(initialdir=current or None, parent=self.top)
        if path:
            entry.delete(0, tk.END)
            entry.insert(0, path)

    def _save(self):
        for key, entry in self.entries.items():
            self.config.set(key, entry.get().strip())
        self.config.save()
        self.saved = True
        self.top.destroy()


class ProjectEditDialog:
    """Dialog for editing a project name and description"""
    def __init__(self, parent, t_func, lang, project):
        self.result = None
        self.t_func = t_func
        self.top = tk.Toplevel(parent)
        self.top.title("✏ " + t_func("edit_project"))
        self.top.geometry("400x160")
        self.top.transient(parent)
        self.top.grab_set()

        ttk.Label(self.top, text=t_func("project_name")).grid(row=0, column=0, padx=8, pady=6, sticky=tk.W)
        self.name_entry = ttk.Entry(self.top, width=30)
        self.name_entry.insert(0, project.get("name", ""))
        self.name_entry.grid(row=0, column=1, padx=8, pady=6)

        ttk.Label(self.top, text=t_func("description")).grid(row=1, column=0, padx=8, pady=6, sticky=tk.W)
        self.desc_entry = ttk.Entry(self.top, width=30)
        self.desc_entry.insert(0, project.get("description", ""))
        self.desc_entry.grid(row=1, column=1, padx=8, pady=6)

        ttk.Button(self.top, text="OK", command=self._ok).grid(row=2, column=0, columnspan=2, pady=10)

    def _ok(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("", self.t_func("name_required"))
            return
        self.result = {"name": name, "description": self.desc_entry.get().strip()}
        self.top.destroy()


class MilestoneEditDialog:
    """Dialog for editing milestone name, description and deadline"""
    def __init__(self, parent, t_func, lang, milestone):
        self.result = None
        self.top = tk.Toplevel(parent)
        self.top.title("✏ " + t_func("edit_milestone"))
        self.top.geometry("400x200")
        self.top.transient(parent)
        self.top.grab_set()

        ttk.Label(self.top, text=t_func("milestone_name")).grid(row=0, column=0, padx=8, pady=5, sticky=tk.W)
        self.name_entry = ttk.Entry(self.top, width=30)
        self.name_entry.insert(0, milestone.get("name", ""))
        self.name_entry.grid(row=0, column=1, padx=8, pady=5)

        ttk.Label(self.top, text=t_func("description")).grid(row=1, column=0, padx=8, pady=5, sticky=tk.W)
        self.desc_entry = ttk.Entry(self.top, width=30)
        self.desc_entry.insert(0, milestone.get("description", ""))
        self.desc_entry.grid(row=1, column=1, padx=8, pady=5)

        ttk.Label(self.top, text=t_func("end_date") + " (YYYYMMDD)").grid(row=2, column=0, padx=8, pady=5, sticky=tk.W)
        self.deadline_entry = ttk.Entry(self.top, width=30)
        self.deadline_entry.insert(0, milestone.get("deadline", ""))
        self.deadline_entry.grid(row=2, column=1, padx=8, pady=5)

        ttk.Button(self.top, text="OK", command=self._ok).grid(row=3, column=0, columnspan=2, pady=10)

    def _ok(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("", "Name is required")
            return
        self.result = {
            "name": name,
            "description": self.desc_entry.get().strip(),
            "deadline": self.deadline_entry.get().strip(),
        }
        self.top.destroy()


class ActivityEditDialog:
    """Dialog for editing an existing activity"""
    def __init__(self, parent, t_func, lang, activity):
        self.result = None
        self.t_func = t_func
        self.top = tk.Toplevel(parent)
        self.top.title("✏ " + t_func("edit_activity"))
        self.top.geometry("400x260")
        self.top.transient(parent)
        self.top.grab_set()

        fields = [
            ("executor", t_func("executor"), activity.get("executor", "")),
            ("date", t_func("date") + " (YYYYMMDD)", activity.get("date", "")),
            ("hours", t_func("hours"), str(activity.get("hours", ""))),
            ("content", t_func("content"), activity.get("content", "")),
        ]
        self.entries = {}
        for i, (key, label, val) in enumerate(fields):
            ttk.Label(self.top, text=label).grid(row=i, column=0, padx=8, pady=4, sticky=tk.W)
            entry = ttk.Entry(self.top, width=30)
            entry.insert(0, val)
            entry.grid(row=i, column=1, padx=8, pady=4)
            self.entries[key] = entry
        ttk.Button(self.top, text="OK", command=self._ok).grid(
            row=len(fields), column=0, columnspan=2, pady=12)

    def _ok(self):
        executor = self.entries["executor"].get().strip()
        date = self.entries["date"].get().strip()
        hours_str = self.entries["hours"].get().strip()
        content = self.entries["content"].get().strip()
        if not executor or not date or not content:
            return
        # Validate date format
        if len(date) != 8 or not date.isdigit():
            messagebox.showwarning("", self.t_func("invalid_date"))
            return
        try:
            hours = float(hours_str)
            if hours <= 0:
                return
        except ValueError:
            return
        self.result = {"executor": executor, "date": date, "hours": hours, "content": content}
        self.top.destroy()


class ProjectGitConfigDialog:
    """Dialog for configuring project Git remote"""
    def __init__(self, parent, t_func, lang, project):
        self.result = None
        self.t_func = t_func
        self.top = tk.Toplevel(parent)
        self.top.title("🔗 " + t_func("git_config"))
        self.top.geometry("500x240")
        self.top.transient(parent)
        self.top.grab_set()

        fields = [
            ("remote_url", t_func("remote_url"), project.get("remote_url", "")),
            ("remote_branch", t_func("remote_branch") if lang == "en" else "远端主分支", project.get("remote_branch", "main")),
            ("remote_username", t_func("username"), project.get("remote_username", "")),
            ("remote_password", t_func("password"), project.get("remote_password", "")),
        ]
        self.entries = {}
        for i, (key, label, val) in enumerate(fields):
            ttk.Label(self.top, text=label).grid(row=i, column=0, padx=8, pady=5, sticky=tk.W)
            entry = ttk.Entry(self.top, width=40)
            entry.insert(0, val)
            if key == "remote_password":
                entry.configure(show="*")
            entry.grid(row=i, column=1, padx=8, pady=5)
            self.entries[key] = entry

        ttk.Button(self.top, text="OK", command=self._ok).grid(
            row=len(fields), column=0, columnspan=2, pady=10)

    def _ok(self):
        url = self.entries["remote_url"].get().strip()
        if url and not (re.match(r'^(https?://|git@)', url) or os.path.isabs(url)):
            messagebox.showwarning("", self.t_func("invalid_url"))
            return
        self.result = {
            "remote_url": url,
            "remote_branch": self.entries["remote_branch"].get().strip() or "main",
            "remote_username": self.entries["remote_username"].get().strip(),
            "remote_password": self.entries["remote_password"].get().strip(),
        }
        self.top.destroy()


class ProjectCreateDialog:
    """Dialog for creating a new project with optional remote clone support."""
    def __init__(self, parent, t_func, lang):
        self.result = None
        self.t_func = t_func
        self.top = tk.Toplevel(parent)
        self.top.title(t_func("add") + " " + t_func("project"))
        self.top.geometry("450x260")
        self.top.transient(parent)
        self.top.grab_set()

        ttk.Label(self.top, text=t_func("project_name")).grid(row=0, column=0, padx=8, pady=5, sticky=tk.W)
        self.name_entry = ttk.Entry(self.top, width=35)
        self.name_entry.grid(row=0, column=1, padx=8, pady=5)

        ttk.Label(self.top, text=t_func("description")).grid(row=1, column=0, padx=8, pady=5, sticky=tk.W)
        self.desc_entry = ttk.Entry(self.top, width=35)
        self.desc_entry.grid(row=1, column=1, padx=8, pady=5)

        ttk.Label(self.top, text=t_func("remote_url")).grid(row=2, column=0, padx=8, pady=5, sticky=tk.W)
        self.url_entry = ttk.Entry(self.top, width=35)
        self.url_entry.grid(row=2, column=1, padx=8, pady=5)

        ttk.Label(self.top, text=t_func("remote_branch")).grid(row=3, column=0, padx=8, pady=5, sticky=tk.W)
        self.branch_entry = ttk.Entry(self.top, width=35)
        self.branch_entry.insert(0, "main")
        self.branch_entry.grid(row=3, column=1, padx=8, pady=5)

        ttk.Button(self.top, text="OK", command=self._ok).grid(row=4, column=0, columnspan=2, pady=10)

    def _ok(self):
        name = self.name_entry.get().strip()
        remote_url = self.url_entry.get().strip()
        # If cloning and no name given, derive from URL
        if not name and remote_url:
            # Extract last path component as project name
            # Use os.path.basename for Windows paths, posixpath for URLs
            url_path = remote_url.rstrip("/")
            if url_path.endswith(".git"):
                url_path = url_path[:-4]
            name = os.path.basename(url_path)
        if not name:
            messagebox.showwarning(self.t_func("warning"), self.t_func("name_required"))
            return
        self.result = {
            "name": name,
            "description": self.desc_entry.get().strip(),
            "remote_url": remote_url,
            "remote_branch": self.branch_entry.get().strip() or "main",
        }
        self.top.destroy()


class MilestoneCreateDialog:
    """Dialog for creating a new milestone with all fields."""
    def __init__(self, parent, t_func, lang):
        self.result = None
        self.t_func = t_func
        self.top = tk.Toplevel(parent)
        self.top.title(t_func("add") + " " + t_func("milestone"))
        self.top.geometry("450x250")
        self.top.transient(parent)
        self.top.grab_set()

        ttk.Label(self.top, text=t_func("milestone_name") + " *").grid(row=0, column=0, padx=8, pady=5, sticky=tk.W)
        self.name_entry = ttk.Entry(self.top, width=30)
        self.name_entry.grid(row=0, column=1, padx=8, pady=5)

        ttk.Label(self.top, text=t_func("description")).grid(row=1, column=0, padx=8, pady=5, sticky=tk.W)
        self.desc_entry = ttk.Entry(self.top, width=30)
        self.desc_entry.grid(row=1, column=1, padx=8, pady=5)

        ttk.Label(self.top, text=t_func("end_date") + " (YYYYMMDD)").grid(row=2, column=0, padx=8, pady=5, sticky=tk.W)
        self.deadline_entry = ttk.Entry(self.top, width=30)
        self.deadline_entry.grid(row=2, column=1, padx=8, pady=5)

        ttk.Label(self.top, text="🎨 " + t_func("color")).grid(row=3, column=0, padx=8, pady=5, sticky=tk.W)
        self.color_entry = ttk.Entry(self.top, width=30)
        self.color_entry.grid(row=3, column=1, padx=8, pady=5)

        ttk.Button(self.top, text="OK", command=self._ok).grid(row=4, column=0, columnspan=2, pady=10)

    def _ok(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning(self.t_func("warning"), self.t_func("name_required"))
            return
        self.result = {
            "name": name,
            "description": self.desc_entry.get().strip(),
            "deadline": self.deadline_entry.get().strip(),
            "color": self.color_entry.get().strip(),
        }
        self.top.destroy()


class ProgressDialog:
    """Dialog for setting plan progress (0-100 integer)."""
    def __init__(self, parent, t_func, lang):
        self.result = None
        self.t_func = t_func
        self.top = tk.Toplevel(parent)
        self.top.title(t_func("set_progress"))
        self.top.geometry("350x130")
        self.top.transient(parent)
        self.top.grab_set()

        ttk.Label(self.top, text=t_func("progress_input")).grid(row=0, column=0, padx=8, pady=10, sticky=tk.W)
        self.progress_entry = ttk.Entry(self.top, width=10)
        self.progress_entry.grid(row=0, column=1, padx=8, pady=10)

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
