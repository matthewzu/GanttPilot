#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GanttPilot - CLI Interface / 命令行界面"""

import sys
import os
from ganttpilot_i18n import t
from ganttpilot_config import Config
from ganttpilot_core import DataStore
from ganttpilot_git import GitSync
from ganttpilot_gantt import generate_gantt_uml, generate_gantt_markdown, generate_gantt_url
from version import VERSION


class CLI:
    def __init__(self, language=None):
        self.config = Config()
        self.lang = language or self.config.language
        self.config.language = self.lang

        # Ensure data dir
        if not self.config.data_dir:
            self.config.data_dir = os.path.join(os.path.expanduser("~"), ".ganttpilot", "data")
        os.makedirs(self.config.data_dir, exist_ok=True)

        self.store = DataStore(self.config.data_dir)
        self.git = GitSync(
            self.config.data_dir,
            self.config.remote_url,
            self.config.remote_username,
            self.config.remote_password,
        )
        # Init data repo
        self.git.init_repo()

    def _t(self, key, *args):
        return t(key, self.lang, *args)

    def _input(self, prompt):
        try:
            return input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return ""

    def _commit(self, message):
        """Commit changes to data repo"""
        try:
            self.git.commit(message)
        except Exception:
            pass

    def _sync(self):
        """Sync with remote"""
        if self.config.remote_url:
            print(self._t("syncing"))
            try:
                self.git.sync()
                print(self._t("sync_done"))
            except Exception as e:
                print(self._t("sync_fail", str(e)))
        else:
            print(self._t("no_remote"))

    # ── Commands ─────────────────────────────────────────────
    def cmd_help(self):
        cmds = {
            "zh": [
                "项目管理:",
                "  project add <名称>          - 添加项目",
                "  project delete <名称>       - 删除项目",
                "  project list                - 列出项目",
                "  project report <名称>       - 生成报告(Markdown+PlantUML)",
                "",
                "里程碑管理:",
                "  milestone add <项目> <名称> [描述]  - 添加里程碑",
                "  milestone delete <项目> <名称>      - 删除里程碑",
                "  milestone list <项目>               - 列出里程碑",
                "",
                "计划管理:",
                "  plan add <项目> <里程碑> <执行者> <内容> <开始YYYYMMDD> <结束YYYYMMDD> [skip_weekends=1] [skip_dates=D1,D2]",
                "  plan delete <项目> <里程碑> <计划ID>",
                "  plan finish <项目> <里程碑> <计划ID>",
                "  plan reopen <项目> <里程碑> <计划ID>",
                "  plan list <项目> <里程碑>",
                "",
                "活动管理:",
                "  activity add <项目> <里程碑> <计划ID> <执行者> <日期YYYYMMDD> <小时数> <内容>",
                "  activity delete <项目> <里程碑> <计划ID> <活动ID>",
                "",
                "其他:",
                "  sync       - 与远端仓库同步",
                "  config     - 显示/修改配置",
                "  gantt <项目>  - 在浏览器中查看甘特图",
                "  report <项目> - 生成工时报告",
                "  lang       - 切换语言",
                "  help       - 显示帮助",
                "  exit/quit  - 退出",
            ],
            "en": [
                "Project Management:",
                "  project add <name>          - Add project",
                "  project delete <name>       - Delete project",
                "  project list                - List projects",
                "  project report <name>       - Generate report (Markdown+PlantUML)",
                "",
                "Milestone Management:",
                "  milestone add <project> <name> [description]  - Add milestone",
                "  milestone delete <project> <name>              - Delete milestone",
                "  milestone list <project>                       - List milestones",
                "",
                "Plan Management:",
                "  plan add <project> <milestone> <executor> <content> <startYYYYMMDD> <endYYYYMMDD> [skip_weekends=1] [skip_dates=D1,D2]",
                "  plan delete <project> <milestone> <plan_id>",
                "  plan finish <project> <milestone> <plan_id>",
                "  plan reopen <project> <milestone> <plan_id>",
                "  plan list <project> <milestone>",
                "",
                "Activity Management:",
                "  activity add <project> <milestone> <plan_id> <executor> <dateYYYYMMDD> <hours> <content>",
                "  activity delete <project> <milestone> <plan_id> <activity_id>",
                "",
                "Other:",
                "  sync        - Sync with remote repository",
                "  config      - Show/edit configuration",
                "  gantt <project> - Open Gantt chart in browser",
                "  report <project> - Generate time report",
                "  lang        - Toggle language",
                "  help        - Show help",
                "  exit/quit   - Exit",
            ],
        }
        for line in cmds.get(self.lang, cmds["en"]):
            print(line)

    def cmd_project(self, args):
        if not args:
            return self.cmd_help()
        action = args[0]
        if action == "list":
            projects = self.store.list_projects()
            if not projects:
                print(self._t("no_projects"))
            else:
                for p in projects:
                    ms_count = len(p.get("milestones", []))
                    print(f"  {p['name']}  ({ms_count} {self._t('milestone')})")
        elif action == "add" and len(args) >= 2:
            name = " ".join(args[1:])
            result = self.store.add_project(name)
            if result:
                print(self._t("project_added", name))
                self._commit(f"Add project: {name}")
            else:
                print(self._t("error") + f": {name}")
        elif action == "delete" and len(args) >= 2:
            name = " ".join(args[1:])
            if self.store.delete_project(name):
                print(self._t("project_deleted", name))
                self._commit(f"Delete project: {name}")
            else:
                print(self._t("not_found", name))
        elif action == "report" and len(args) >= 2:
            name = " ".join(args[1:])
            proj = self.store.get_project(name)
            if proj:
                md = generate_gantt_markdown(proj, self.lang)
                report_path = os.path.join(self.config.data_dir, f"{name}_report.md")
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(md)
                print(f"Report saved: {report_path}")
                self._commit(f"Generate report: {name}")
            else:
                print(self._t("not_found", name))
        else:
            self.cmd_help()

    def cmd_milestone(self, args):
        if not args:
            return self.cmd_help()
        action = args[0]
        if action == "list" and len(args) >= 2:
            proj_name = args[1]
            milestones = self.store.list_milestones(proj_name)
            if not milestones:
                print(self._t("no_projects"))
            else:
                for ms in milestones:
                    desc = f" - {ms['description']}" if ms.get("description") else ""
                    plans_count = len(ms.get("plans", []))
                    print(f"  {ms['name']}{desc}  ({plans_count} {self._t('plan')})")
        elif action == "add" and len(args) >= 3:
            proj_name = args[1]
            ms_name = args[2]
            desc = " ".join(args[3:]) if len(args) > 3 else ""
            result = self.store.add_milestone(proj_name, ms_name, desc)
            if result:
                print(self._t("milestone_added", ms_name))
                self._commit(f"Add milestone: {ms_name} to {proj_name}")
            else:
                print(self._t("error"))
        elif action == "delete" and len(args) >= 3:
            proj_name, ms_name = args[1], args[2]
            if self.store.delete_milestone(proj_name, ms_name):
                print(self._t("milestone_deleted", ms_name))
                self._commit(f"Delete milestone: {ms_name} from {proj_name}")
            else:
                print(self._t("not_found", ms_name))
        else:
            self.cmd_help()

    def cmd_plan(self, args):
        if not args:
            return self.cmd_help()
        action = args[0]
        if action == "list" and len(args) >= 3:
            proj_name, ms_name = args[1], args[2]
            plans = self.store.list_plans(proj_name, ms_name)
            if not plans:
                print(self._t("no_projects"))
            else:
                for p in plans:
                    status = self._t("plan_status_finished") if p["status"] == "finished" else self._t("plan_status_active")
                    acts = len(p.get("activities", []))
                    print(f"  [{p['id']}] {p['content']} ({p['executor']}) {p['start_date']}-{p['end_date']} [{status}] {acts} {self._t('activity')}")
        elif action == "add" and len(args) >= 7:
            proj, ms, executor, content = args[1], args[2], args[3], args[4]
            start, end = args[5], args[6]
            skip_weekends = True
            skip_dates = []
            for extra in args[7:]:
                if extra.startswith("skip_weekends="):
                    skip_weekends = extra.split("=")[1] in ("1", "true", "yes")
                elif extra.startswith("skip_dates="):
                    skip_dates = extra.split("=")[1].split(",")
            result = self.store.add_plan(proj, ms, content, executor, start, end, skip_weekends, skip_dates)
            if result:
                print(self._t("plan_added", content) + f" [ID: {result['id']}]")
                self._commit(f"Add plan: {content} to {ms}/{proj}")
            else:
                print(self._t("error"))
        elif action == "delete" and len(args) >= 4:
            proj, ms, plan_id = args[1], args[2], args[3]
            if self.store.delete_plan(proj, ms, plan_id):
                print(self._t("plan_deleted", plan_id))
                self._commit(f"Delete plan: {plan_id}")
            else:
                print(self._t("not_found", plan_id))
        elif action == "finish" and len(args) >= 4:
            proj, ms, plan_id = args[1], args[2], args[3]
            if self.store.finish_plan(proj, ms, plan_id):
                print(self._t("plan_finished", plan_id))
                self._commit(f"Finish plan: {plan_id}")
            else:
                print(self._t("not_found", plan_id))
        elif action == "reopen" and len(args) >= 4:
            proj, ms, plan_id = args[1], args[2], args[3]
            if self.store.reopen_plan(proj, ms, plan_id):
                print(self._t("plan_reopened", plan_id))
                self._commit(f"Reopen plan: {plan_id}")
            else:
                print(self._t("not_found", plan_id))
        else:
            self.cmd_help()

    def cmd_activity(self, args):
        if not args:
            return self.cmd_help()
        action = args[0]
        if action == "add" and len(args) >= 8:
            proj, ms, plan_id = args[1], args[2], args[3]
            executor, date, hours = args[4], args[5], float(args[6])
            content = " ".join(args[7:])
            result = self.store.add_activity(proj, ms, plan_id, executor, date, hours, content)
            if result:
                print(self._t("activity_added") + f" [ID: {result['id']}]")
                self._commit(f"Add activity: {content}")
            else:
                print(self._t("error"))
        elif action == "delete" and len(args) >= 5:
            proj, ms, plan_id, act_id = args[1], args[2], args[3], args[4]
            if self.store.delete_activity(proj, ms, plan_id, act_id):
                print(self._t("activity_deleted"))
                self._commit(f"Delete activity: {act_id}")
            else:
                print(self._t("not_found", act_id))
        else:
            self.cmd_help()

    def cmd_gantt(self, args):
        if not args:
            print(self._t("input_required", self._t("project_name")))
            return
        name = " ".join(args)
        proj = self.store.get_project(name)
        if proj:
            from ganttpilot_gantt import open_gantt_in_browser
            url = open_gantt_in_browser(proj, self.lang)
            print(f"URL: {url}")
        else:
            print(self._t("not_found", name))

    def cmd_report(self, args):
        if not args:
            print(self._t("input_required", self._t("project_name")))
            return
        name = " ".join(args)
        report = self.store.get_time_report(name)
        if not report:
            print(self._t("not_found", name))
            return
        print(f"\n{self._t('time_report')}: {name}")
        print(f"{'─' * 50}")
        print(f"  {self._t('participant'):<20} {self._t('total_hours'):<12} {self._t('total_days')}")
        print(f"  {'─' * 44}")
        for ex, data in sorted(report.items()):
            if ex == "by_tag":
                continue
            print(f"  {ex:<20} {data['hours']:<12.1f} {data['days']:.2f}")

    def cmd_config(self, args=None):
        print(f"  {self._t('language')}: {self.config.language}")
        print(f"  {self._t('font_size')}: {self.config.font_size}")
        print(f"  {self._t('config_dir')}: {self.config.config_dir}")
        print(f"  {self._t('data_dir')}: {self.config.data_dir}")
        print(f"  {self._t('remote_url')}: {self.config.remote_url or '-'}")
        print(f"  {self._t('username')}: {self.config.remote_username or '-'}")

    def cmd_lang(self):
        self.lang = "en" if self.lang == "zh" else "zh"
        self.config.language = self.lang
        self.config.save()
        print(f"Language: {self.lang}")

    def run(self):
        """Main REPL loop"""
        # Sync on start
        if self.config.remote_url:
            self._sync()

        print(f"GanttPilot v{VERSION} - {self._t('cli_welcome')}")
        print(self._t("cli_help"))
        print()

        while True:
            try:
                line = self._input("GanttPilot> ")
            except (EOFError, KeyboardInterrupt):
                break
            if not line:
                continue

            parts = line.split()
            cmd = parts[0].lower()
            args = parts[1:]

            if cmd in ("exit", "quit", "q"):
                # Sync on exit
                if self.config.remote_url:
                    self._sync()
                self.config.save()
                print(self._t("cli_bye"))
                break
            elif cmd == "help":
                self.cmd_help()
            elif cmd == "project":
                self.cmd_project(args)
            elif cmd == "milestone":
                self.cmd_milestone(args)
            elif cmd == "plan":
                self.cmd_plan(args)
            elif cmd == "activity":
                self.cmd_activity(args)
            elif cmd == "gantt":
                self.cmd_gantt(args)
            elif cmd == "report":
                self.cmd_report(args)
            elif cmd == "sync":
                self._sync()
            elif cmd == "config":
                self.cmd_config(args)
            elif cmd == "lang":
                self.cmd_lang()
            else:
                print(self._t("cli_unknown_cmd", cmd))


def main(language=None):
    cli = CLI(language=language)
    cli.run()
