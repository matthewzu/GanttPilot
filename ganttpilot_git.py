#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GanttPilot - Git Sync Management / Git同步管理

Work branch: user-configurable priv_branch (default 'priv_{committer_name}' or 'priv')
Remote branch: configurable main branch (default 'main')

Sync flow:
  1. Checkout priv_branch, commit any pending changes
  2. Fetch from origin
  3. Push priv_branch to origin
  NO merge/push main — use Pull Request instead.
  NO auto-rebase — use manual_rebase() when needed.
"""

import datetime
import json
import logging
import os
import re
import subprocess
import sys
from logging.handlers import TimedRotatingFileHandler

# Hide console window on Windows when calling git
_SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def _setup_app_logger(log_dir, max_days=30):
    """Create a file logger for application operations, auto-cleaning logs older than max_days.
    
    Args:
        log_dir: Directory where ganttpilot.log will be stored (typically config_dir root).
        max_days: Max days to keep rotated log files.
    """
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "ganttpilot.log")

    logger = logging.getLogger("ganttpilot")
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    handler = TimedRotatingFileHandler(
        log_path, when="D", interval=1, backupCount=max_days,
        encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(handler)

    # Clean up stale log files beyond max_days
    _cleanup_old_logs(log_dir, max_days)
    return logger


def _cleanup_old_logs(log_dir, max_days):
    """Remove ganttpilot.log.* files older than max_days."""
    now = datetime.datetime.now()
    cutoff = now - datetime.timedelta(days=max_days)
    for name in os.listdir(log_dir):
        if not name.startswith("ganttpilot.log."):
            continue
        filepath = os.path.join(log_dir, name)
        try:
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
            if mtime < cutoff:
                os.remove(filepath)
        except OSError:
            pass


class GitSync:
    """Manages git operations on a project directory"""

    WORK_BRANCH = "priv"

    def __init__(self, data_dir, remote_url="", username="", password="", main_branch="main",
                 committer_name="", committer_email="", priv_branch="", git_log_max_days=30,
                 log_dir=""):
        self.data_dir = data_dir
        self.remote_url = remote_url
        self.username = username
        self.password = password
        self.main_branch = main_branch or "main"
        self.committer_name = committer_name
        self.committer_email = committer_email
        self._logger = _setup_app_logger(log_dir or data_dir, max_days=git_log_max_days)
        if priv_branch:
            self.priv_branch = priv_branch
        elif committer_name:
            # Sanitize committer name for use as branch name: replace spaces and
            # invalid git branch characters with underscores
            safe_name = re.sub(r'[\s~^:?*\[\]\\]+', '_', committer_name).strip('._/')
            self.priv_branch = f"priv_{safe_name}" if safe_name else self.WORK_BRANCH
        else:
            self.priv_branch = self.WORK_BRANCH

    def clone_repo(self, remote_url, target_dir, main_branch="main"):
        """Clone a remote repository to target_dir, checkout main_branch, create priv branch."""
        # Use authenticated URL if credentials are available
        auth_url = self._auth_url() or remote_url
        result = subprocess.run(
            ["git", "clone", auth_url, target_dir],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=120, creationflags=_SUBPROCESS_FLAGS,
        )
        # git clone writes progress to stderr even on success, so check if .git exists
        if not os.path.isdir(os.path.join(target_dir, ".git")):
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Clone failed")
        try:
            subprocess.run(
                ["git", "checkout", main_branch],
                cwd=target_dir, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=30, check=False,
                creationflags=_SUBPROCESS_FLAGS,
            )
            subprocess.run(
                ["git", "checkout", "-b", self.priv_branch],
                cwd=target_dir, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=30, check=False,
                creationflags=_SUBPROCESS_FLAGS,
            )
            return True
        except Exception as e:
            raise RuntimeError(str(e))

    def _committer_config(self):
        """Return list of (key, value) tuples for committer identity config."""
        config = []
        if self.committer_name:
            config.append(("user.name", self.committer_name))
        if self.committer_email:
            config.append(("user.email", self.committer_email))
        return config or None

    def _run(self, *args, check=True, extra_config=None):
        """Run a git command in the data directory"""
        cmd = ["git"]
        if extra_config:
            for k, v in extra_config:
                cmd += ["-c", f"{k}={v}"]
        cmd += list(args)
        self._logger.debug("CMD: %s", " ".join(cmd))
        result = subprocess.run(
            cmd,
            cwd=self.data_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            creationflags=_SUBPROCESS_FLAGS,
        )
        if result.returncode != 0:
            self._logger.warning("FAIL (rc=%d): %s | stderr: %s",
                                 result.returncode, " ".join(args),
                                 result.stderr.strip())
            if check:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        else:
            self._logger.debug("OK: %s", " ".join(args))
        return result

    def _auth_url(self):
        """Build authenticated remote URL (or return local path as-is)"""
        if not self.remote_url:
            return ""
        url = self.remote_url
        # Local path — no auth needed
        if os.path.isabs(url):
            return url
        if self.username and self.password:
            if url.startswith("https://"):
                url = f"https://{self.username}:{self.password}@{url[8:]}"
            elif url.startswith("http://"):
                url = f"http://{self.username}:{self.password}@{url[7:]}"
        return url

    def _ensure_remote(self):
        """Ensure origin remote is set to the correct URL"""
        auth_url = self._auth_url()
        if not auth_url:
            return
        try:
            self._run("remote", "add", "origin", auth_url)
        except RuntimeError:
            self._run("remote", "set-url", "origin", auth_url)

    def _restore_plain_remote(self):
        """Reset origin to the plain (no-auth) URL so credential helpers work."""
        if not self.remote_url:
            return
        try:
            self._run("remote", "set-url", "origin", self.remote_url)
        except RuntimeError:
            pass

    def _branch_exists(self, branch):
        """Check if a local branch exists"""
        result = self._run("branch", "--list", branch, check=False)
        return branch in result.stdout

    def is_repo(self):
        return os.path.isdir(os.path.join(self.data_dir, ".git"))

    def init_repo(self):
        """Initialize git repo and ensure priv branch exists"""
        if not os.path.isdir(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)
        if not self.is_repo():
            self._run("init")
        # Ensure priv branch exists and is checked out
        if not self._branch_exists(self.priv_branch):
            # Check if current branch is already a priv_* branch (migration case)
            current = self._run("branch", "--show-current", check=False).stdout.strip()
            if current and current.startswith("priv_") and current != self.priv_branch:
                # Rename old branch to the new sanitized name
                self._run("branch", "-m", current, self.priv_branch, check=False)
            elif not self._run("log", "--oneline", "-1", check=False).stdout.strip():
                # No commits — create initial
                self._run("add", "-A", check=False)
                self._run("commit", "--allow-empty", "-m", "Initial commit",
                         extra_config=self._committer_config())
                try:
                    self._run("checkout", "-b", self.priv_branch)
                except RuntimeError:
                    self._run("checkout", self.priv_branch)
            else:
                try:
                    self._run("checkout", "-b", self.priv_branch)
                except RuntimeError:
                    self._run("checkout", self.priv_branch)
        else:
            self._run("checkout", self.priv_branch, check=False)

    def commit(self, message):
        """Stage project data files and commit on priv branch"""
        if not self.is_repo():
            self.init_repo()
        # Ensure we're on priv branch
        self._run("checkout", self.priv_branch, check=False)
        self._run("add", "project.json")
        self._run("add", "requirements", check=False)
        self._run("add", "milestones", check=False)
        self._run("add", "activities", check=False)
        status = self._run("status", "--porcelain", check=False)
        if not status.stdout.strip():
            return False
        self._run("commit", "-m", message, extra_config=self._committer_config())
        return True

    def _remote_branch_exists(self, branch):
        """Check if a remote branch exists on origin"""
        result = self._run("ls-remote", "--heads", "origin", branch, check=False)
        return branch in result.stdout

    @staticmethod
    def check_git_installed():
        """Check if git is installed, return (bool, version_string)"""
        try:
            result = subprocess.run(
                ["git", "--version"], capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=10,
                creationflags=_SUBPROCESS_FLAGS,
            )
            return result.returncode == 0, result.stdout.strip()
        except (FileNotFoundError, OSError):
            return False, ""

    @staticmethod
    def detect_git_user():
        """Detect current environment git user.name and user.email, return (name, email)"""
        name, email = "", ""
        try:
            r = subprocess.run(
                ["git", "config", "user.name"], capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=10,
                creationflags=_SUBPROCESS_FLAGS,
            )
            name = r.stdout.strip()
        except (FileNotFoundError, OSError):
            pass
        try:
            r = subprocess.run(
                ["git", "config", "user.email"], capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=10,
                creationflags=_SUBPROCESS_FLAGS,
            )
            email = r.stdout.strip()
        except (FileNotFoundError, OSError):
            pass
        return name, email

    def sync(self):
        """Sync with remote repo via private branch.

        Flow:
          1. Checkout priv_branch, commit pending changes
          2. Configure remote, fetch from origin
          3. Push priv_branch to origin
          NO merge/push main. NO auto-rebase.
        """
        if not self.remote_url or not self.is_repo():
            return False

        wb = self.priv_branch
        self._logger.info("=== sync start === branch=%s remote=%s", wb, self.remote_url)

        # 1. Commit pending on priv_branch (all project data files)
        self._run("checkout", wb, check=False)
        self._run("add", "project.json", check=False)
        self._run("add", "requirements", check=False)
        self._run("add", "milestones", check=False)
        self._run("add", "activities", check=False)
        status = self._run("status", "--porcelain", check=False)
        if status.stdout.strip():
            self._run("commit", "-m", "Auto-commit before sync",
                      extra_config=self._committer_config(), check=False)

        # 2. Configure remote, fetch
        self._ensure_remote()
        self._run("fetch", "origin", check=False)
        self._main_updated = self._update_local_main()

        # 3. Push priv_branch to origin (fallback to credential helper on auth failure)
        try:
            self._run("push", "-u", "origin", wb)
            self._logger.info("=== sync OK (push succeeded) ===")
        except RuntimeError as e:
            self._logger.warning("push failed with embedded creds, retrying plain: %s", e)
            # Auth with embedded credentials failed; retry with plain URL
            # so that system credential helpers (e.g. Windows Credential Manager) can work.
            self._restore_plain_remote()
            try:
                self._run("push", "-u", "origin", wb)
                self._logger.info("=== sync OK (push succeeded via plain remote) ===")
            except RuntimeError as e2:
                self._logger.error("=== sync FAILED: push error: %s ===", e2)
                raise
        return True

    def fetch_remote(self):
        """Fetch from remote without pushing (pull-only sync).

        Returns:
            bool: True if fetch succeeded
        """
        if not self.remote_url or not self.is_repo():
            return False
        self._ensure_remote()
        result = self._run("fetch", "origin", check=False)
        if result.returncode != 0 and self.username and self.password:
            # Embedded credentials may be stale; retry with plain URL
            self._restore_plain_remote()
            self._run("fetch", "origin", check=False)
        main_updated = self._update_local_main()
        self._main_updated = main_updated
        return True

    def _update_local_main(self):
        """将本地 main 分支快进到 origin/main。

        如果本地 main 可以快进，执行 fast-forward。
        如果本地 main 已分叉（用户不应在 main 上直接提交），强制重置。
        不切换当前分支（使用 update-ref）。

        Returns:
            bool: True if main was updated, False if already up-to-date or skipped.
        """
        # 检查 origin/main 是否存在
        result = self._run("rev-parse", f"origin/{self.main_branch}", check=False)
        if result.returncode != 0:
            return False  # 远端 main 不存在，跳过

        remote_sha = result.stdout.strip()

        # 检查本地 main 是否存在
        local_result = self._run("rev-parse", self.main_branch, check=False)
        if local_result.returncode != 0:
            # 本地 main 不存在，创建指向 origin/main
            self._run("branch", self.main_branch, remote_sha, check=False)
            return True

        local_sha = local_result.stdout.strip()
        if local_sha == remote_sha:
            return False  # 已是最新

        # 直接更新 ref（不需要 checkout main）
        self._run("update-ref", f"refs/heads/{self.main_branch}", remote_sha)
        return True

    def get_log(self, branch=None, max_count=50):
        """获取指定分支的 git log 记录列表。

        Args:
            branch: 分支名，None 表示当前分支
            max_count: 最大返回条数

        Returns:
            list[dict]: 每条记录包含 {hash, author, date, message, diff_summary}
        """
        try:
            # Use NUL (\x00) as field separator and record separator for reliable parsing
            fmt = "%H%x00%an%x00%ai%x00%s%x00"
            cmd = ["log", f"--format={fmt}", "--stat", f"-{max_count}"]
            if branch:
                cmd.append(branch)
            result = self._run(*cmd, check=True)
            output = result.stdout
            if not output.strip():
                return []

            records = []
            current_hash = ""
            current_author = ""
            current_date = ""
            current_message = ""
            diff_lines = []

            for line in output.splitlines():
                if "\x00" in line:
                    # Save previous record if exists
                    if current_hash:
                        records.append({
                            "hash": current_hash,
                            "author": current_author,
                            "date": current_date,
                            "message": current_message,
                            "diff_summary": "\n".join(diff_lines).strip(),
                        })
                    # Parse new record header
                    parts = line.split("\x00")
                    current_hash = parts[0].strip() if len(parts) > 0 else ""
                    current_author = parts[1].strip() if len(parts) > 1 else ""
                    current_date = parts[2].strip() if len(parts) > 2 else ""
                    current_message = parts[3].strip() if len(parts) > 3 else ""
                    diff_lines = []
                else:
                    # Accumulate --stat diff summary lines
                    stripped = line.strip()
                    if stripped:
                        diff_lines.append(stripped)

            # Don't forget the last record
            if current_hash:
                records.append({
                    "hash": current_hash,
                    "author": current_author,
                    "date": current_date,
                    "message": current_message,
                    "diff_summary": "\n".join(diff_lines).strip(),
                })

            return records
        except Exception:
            return []


    def get_commit_diff(self, commit_hash):
        """获取指定 commit 的详细 diff。

        Args:
            commit_hash: commit 的 hash 值

        Returns:
            str: diff 文本
        """
        try:
            result = self._run("show", commit_hash, check=True)
            return result.stdout
        except Exception:
            return ""


    def list_branches(self):
        """列出所有本地和远端分支。

        Returns:
            list[str]: 分支名列表（本地分支在前，远端分支以 'origin/' 前缀）
        """
        try:
            result = self._run("branch", "-a", check=False)
            if result.returncode != 0:
                return []
            branches = []
            for line in result.stdout.splitlines():
                name = line.strip().lstrip("* ").strip()
                if not name:
                    continue
                # Filter out HEAD -> entries
                if "HEAD ->" in name:
                    continue
                # Clean up remotes/ prefix to origin/
                if name.startswith("remotes/"):
                    name = name[len("remotes/"):]
                branches.append(name)
            return branches
        except Exception:
            return []

    def get_current_branch(self):
        """获取当前分支名。

        Returns:
            str: 当前分支名
        """
        try:
            result = self._run("branch", "--show-current", check=False)
            if result.returncode != 0:
                return ""
            return result.stdout.strip()
        except Exception:
            return ""


    def read_file_from_branch(self, branch, filepath):
        """从指定分支读取文件内容（用于加载其他分支的 project.json）。

        Args:
            branch: 分支名
            filepath: 文件路径（相对于仓库根目录）

        Returns:
            str: 文件内容，失败时返回 None
        """
        try:
            result = self._run("show", f"{branch}:{filepath}")
            return result.stdout
        except Exception:
            return None

    def read_project_from_branch(self, branch):
        """从指定分支读取完整项目数据。

        Supports both v2 split format and legacy single-file format.

        Args:
            branch: 分支名

        Returns:
            dict: 完整项目数据，失败时返回 None
        """
        content = self.read_file_from_branch(branch, "project.json")
        if content is None:
            return None
        try:
            proj = json.loads(content)
        except (json.JSONDecodeError, ValueError):
            return None

        # Check if branch uses v2 format (has milestones/ dir)
        ms_check = self._run("ls-tree", "--name-only", f"{branch}", "milestones/", check=False)
        if ms_check.returncode == 0 and ms_check.stdout.strip():
            return self._read_split_from_branch(branch, proj)

        # Legacy format — load activities from separate files if available
        for ms in proj.get("milestones", []):
            for plan in ms.get("plans", []):
                if "activities" not in plan or not plan["activities"]:
                    plan_id = plan.get("id", "")
                    act_content = self.read_file_from_branch(
                        branch, f"activities/{plan_id}.json"
                    )
                    if act_content:
                        try:
                            plan["activities"] = json.loads(act_content)
                        except (json.JSONDecodeError, ValueError):
                            plan.setdefault("activities", [])
                    else:
                        plan.setdefault("activities", [])
        return proj

    def _read_split_from_branch(self, branch, meta):
        """Assemble full project from v2 split files on a branch."""
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

        # Load requirements
        for req_id in meta.get("requirement_order", []):
            content = self.read_file_from_branch(branch, f"requirements/{req_id}.json")
            if content:
                try:
                    proj["requirements"].append(json.loads(content))
                except (json.JSONDecodeError, ValueError):
                    pass

        # Load milestones and activities
        for ms_id in meta.get("milestone_order", []):
            content = self.read_file_from_branch(branch, f"milestones/{ms_id}.json")
            if not content:
                continue
            try:
                ms = json.loads(content)
            except (json.JSONDecodeError, ValueError):
                continue
            # Load activities for each plan
            for plan in ms.get("plans", []):
                plan_id = plan.get("id", "")
                act_content = self.read_file_from_branch(branch, f"activities/{plan_id}.json")
                if act_content:
                    try:
                        plan["activities"] = json.loads(act_content)
                    except (json.JSONDecodeError, ValueError):
                        plan.setdefault("activities", [])
                else:
                    plan.setdefault("activities", [])
            proj["milestones"].append(ms)

        return proj

    def has_remote_updates(self):
        """检查远端主分支是否有新提交（相对于当前私有分支的基点）。

        Returns:
            bool: True 表示远端有新提交
        """
        if not self.remote_url:
            return False
        try:
            # Get the HEAD of origin/main_branch
            remote_head = self._run("rev-parse", f"origin/{self.main_branch}", check=False)
            if remote_head.returncode != 0:
                return False
            remote_sha = remote_head.stdout.strip()

            # Get the merge base between priv_branch and origin/main_branch
            merge_base = self._run("merge-base", self.priv_branch, f"origin/{self.main_branch}", check=False)
            if merge_base.returncode != 0:
                return False
            base_sha = merge_base.stdout.strip()

            # If remote HEAD differs from merge base, there are new commits
            return remote_sha != base_sha
        except Exception:
            return False

    def has_unpushed_commits(self):
        """Check if the private branch has local commits not yet pushed to remote.

        Returns:
            bool: True if there are unpushed commits or uncommitted project.json changes.
        """
        if not self.remote_url or not self.is_repo():
            return False
        try:
            # Check for uncommitted changes to project.json
            status = self._run("status", "--porcelain", "project.json", check=False)
            if status.stdout.strip():
                return True
            # Check if local priv branch is ahead of origin/priv_branch
            result = self._run("rev-list", "--count",
                               f"origin/{self.priv_branch}..{self.priv_branch}", check=False)
            if result.returncode != 0:
                # Remote branch doesn't exist yet — local has unpushed commits
                local_commits = self._run("rev-list", "--count", self.priv_branch, check=False)
                return local_commits.returncode == 0 and int(local_commits.stdout.strip() or "0") > 0
            count = int(result.stdout.strip() or "0")
            return count > 0
        except Exception:
            return False


    def manual_rebase(self):
        """手动将私有分支 rebase 到远端主分支最新提交。

        If the remote main branch uses the split-activities format but the
        local branch still has inline activities, automatically migrate the
        local data before rebasing to avoid format-related conflicts.

        If normal rebase fails (likely due to format migration on main),
        falls back to a squash strategy: take the final data state from the
        private branch, convert to v2 format, and commit on top of main.

        Rebase 成功后自动 force-push 私有分支到远端（使用 --force-with-lease 安全推送）。

        Raises:
            RuntimeError: rebase 冲突时抛出异常（非格式迁移原因）
        """
        # ── Pre-rebase: auto-migrate if main uses new format ──
        self._pre_rebase_migrate()

        result = self._run("rebase", f"origin/{self.main_branch}", check=False)
        if result.returncode != 0:
            self._run("rebase", "--abort", check=False)

            # Check if main has v2 format — if so, use squash strategy
            ms_check = self._run("ls-tree", "--name-only",
                                 f"origin/{self.main_branch}", "milestones/", check=False)
            if ms_check.returncode == 0 and ms_check.stdout.strip():
                self._squash_rebase_with_migration()
            else:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip()
                                   or "Rebase conflict, aborted")
            return

        # Force-push private branch after successful rebase
        self._force_push_priv()

    def _force_push_priv(self):
        """Force-push private branch to remote."""
        wb = self.priv_branch
        try:
            self._run("push", "--force-with-lease", "-u", "origin", wb)
        except RuntimeError:
            self._restore_plain_remote()
            self._run("push", "--force-with-lease", "-u", "origin", wb)

    def _squash_rebase_with_migration(self):
        """Squash-rebase: take private branch's final data, convert to v2, commit onto main.

        Used when normal rebase fails due to format migration on main.
        The private branch's old commits modified a monolithic project.json,
        but main now uses split files — these are structurally incompatible for
        per-commit replay. Instead, we take the end result and apply it as one commit.
        """
        import copy

        # 1. Read the full project data from the current private branch state
        proj_file = os.path.join(self.data_dir, "project.json")
        with open(proj_file, "r", encoding="utf-8") as f:
            proj = json.load(f)

        # If project.json is still old format (has milestones key), read from it
        # Otherwise read from split files
        if "milestones" not in proj:
            # Already in split format on disk, assemble full data
            full_proj = self._assemble_split_data(proj)
        else:
            full_proj = proj

        # 2. Reset private branch to main (discard old commits)
        self._run("reset", "--hard", f"origin/{self.main_branch}")

        # 3. Write full data in v2 split format on top of main
        req_dir = os.path.join(self.data_dir, "requirements")
        ms_dir = os.path.join(self.data_dir, "milestones")
        act_dir = os.path.join(self.data_dir, "activities")
        os.makedirs(req_dir, exist_ok=True)
        os.makedirs(ms_dir, exist_ok=True)
        os.makedirs(act_dir, exist_ok=True)

        for req in full_proj.get("requirements", []):
            with open(os.path.join(req_dir, f"{req['id']}.json"), "w", encoding="utf-8") as f:
                json.dump(req, f, ensure_ascii=False, indent=2)

        for ms in full_proj.get("milestones", []):
            ms_copy = copy.deepcopy(ms)
            for plan in ms_copy.get("plans", []):
                activities = plan.pop("activities", [])
                with open(os.path.join(act_dir, f"{plan['id']}.json"), "w", encoding="utf-8") as f:
                    json.dump(activities, f, ensure_ascii=False, indent=2)
            with open(os.path.join(ms_dir, f"{ms['id']}.json"), "w", encoding="utf-8") as f:
                json.dump(ms_copy, f, ensure_ascii=False, indent=2)

        # Write config-only project.json
        meta = {
            "id": full_proj.get("id", ""),
            "name": full_proj.get("name", ""),
            "description": full_proj.get("description", ""),
            "remote_url": full_proj.get("remote_url", ""),
            "remote_username": full_proj.get("remote_username", ""),
            "remote_password": full_proj.get("remote_password", ""),
            "remote_branch": full_proj.get("remote_branch", "main"),
            "tags": full_proj.get("tags", []),
            "requirement_order": [r["id"] for r in full_proj.get("requirements", [])],
            "milestone_order": [m["id"] for m in full_proj.get("milestones", [])],
        }
        with open(proj_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # 4. Stage and commit
        self._run("add", "-A")
        status = self._run("status", "--porcelain", check=False)
        if status.stdout.strip():
            self._run("commit", "-m", "Rebase with format migration (squashed)",
                      extra_config=self._committer_config())

        # 5. Force-push
        self._force_push_priv()

    def _assemble_split_data(self, meta):
        """Assemble full project dict from v2 split files on disk."""
        proj = dict(meta)
        proj["requirements"] = []
        proj["milestones"] = []

        req_dir = os.path.join(self.data_dir, "requirements")
        if os.path.isdir(req_dir):
            for req_id in meta.get("requirement_order", []):
                rfile = os.path.join(req_dir, f"{req_id}.json")
                if os.path.isfile(rfile):
                    with open(rfile, "r", encoding="utf-8") as f:
                        proj["requirements"].append(json.load(f))

        ms_dir = os.path.join(self.data_dir, "milestones")
        act_dir = os.path.join(self.data_dir, "activities")
        if os.path.isdir(ms_dir):
            for ms_id in meta.get("milestone_order", []):
                mfile = os.path.join(ms_dir, f"{ms_id}.json")
                if os.path.isfile(mfile):
                    with open(mfile, "r", encoding="utf-8") as f:
                        ms = json.load(f)
                    for plan in ms.get("plans", []):
                        act_file = os.path.join(act_dir, f"{plan['id']}.json")
                        if os.path.isfile(act_file):
                            with open(act_file, "r", encoding="utf-8") as f:
                                plan["activities"] = json.load(f)
                        else:
                            plan.setdefault("activities", [])
                    proj["milestones"].append(ms)

        return proj

    def _pre_rebase_migrate(self):
        """If origin/main has the v2 split format but local doesn't, migrate locally first.

        This prevents format-related merge conflicts during rebase when the
        maintainer has already migrated to the split format on main.
        """
        # Check if origin/main has the milestones/ directory (v2 indicator)
        result = self._run("ls-tree", "--name-only",
                           f"origin/{self.main_branch}", "milestones/", check=False)
        if result.returncode != 0 or not result.stdout.strip():
            return  # Main doesn't have v2 format — nothing to migrate

        # Check if local already has milestones/ dir
        milestones_dir = os.path.join(self.data_dir, "milestones")
        if os.path.isdir(milestones_dir):
            return  # Already migrated locally

        # Local has old format, main has v2 — migrate locally before rebase
        proj_file = os.path.join(self.data_dir, "project.json")
        if not os.path.isfile(proj_file):
            return
        try:
            with open(proj_file, "r", encoding="utf-8") as f:
                proj = json.load(f)
        except (json.JSONDecodeError, IOError):
            return

        import copy

        # Create split directories
        req_dir = os.path.join(self.data_dir, "requirements")
        ms_dir = os.path.join(self.data_dir, "milestones")
        act_dir = os.path.join(self.data_dir, "activities")
        os.makedirs(req_dir, exist_ok=True)
        os.makedirs(ms_dir, exist_ok=True)
        os.makedirs(act_dir, exist_ok=True)

        # Write requirements
        for req in proj.get("requirements", []):
            with open(os.path.join(req_dir, f"{req['id']}.json"), "w", encoding="utf-8") as f:
                json.dump(req, f, ensure_ascii=False, indent=2)

        # Write milestones + activities
        for ms in proj.get("milestones", []):
            ms_copy = copy.deepcopy(ms)
            for plan in ms_copy.get("plans", []):
                activities = plan.pop("activities", [])
                with open(os.path.join(act_dir, f"{plan['id']}.json"), "w", encoding="utf-8") as f:
                    json.dump(activities, f, ensure_ascii=False, indent=2)
            with open(os.path.join(ms_dir, f"{ms['id']}.json"), "w", encoding="utf-8") as f:
                json.dump(ms_copy, f, ensure_ascii=False, indent=2)

        # Write updated project.json (config only)
        meta = {
            "id": proj.get("id", ""),
            "name": proj.get("name", ""),
            "description": proj.get("description", ""),
            "remote_url": proj.get("remote_url", ""),
            "remote_username": proj.get("remote_username", ""),
            "remote_password": proj.get("remote_password", ""),
            "remote_branch": proj.get("remote_branch", "main"),
            "tags": proj.get("tags", []),
            "requirement_order": [r["id"] for r in proj.get("requirements", [])],
            "milestone_order": [m["id"] for m in proj.get("milestones", [])],
        }
        with open(proj_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # Stage and commit the migration
        self._run("add", "-A", check=False)
        self._run("commit", "-m", "Auto-migrate to v2 split storage format",
                  extra_config=self._committer_config(), check=False)

    def migrate_and_push_main(self):
        """Maintainer tool: migrate to v2 split format and push to main.

        Flow:
          1. Fetch and update local main
          2. Checkout main branch
          3. Perform migration directly on main
          4. Commit and push main
          5. Switch back to private branch and rebase onto new main

        Raises:
            RuntimeError: if push fails
        """
        if not self.is_repo():
            raise RuntimeError("Not a git repository")

        # Ensure private branch is clean
        self._run("checkout", self.priv_branch, check=False)
        self._run("add", "-A", check=False)
        status = self._run("status", "--porcelain", check=False)
        if status.stdout.strip():
            self._run("commit", "-m", "Auto-commit before format migration",
                      extra_config=self._committer_config(), check=False)

        # Fetch and update local main
        self._ensure_remote()
        self._run("fetch", "origin", check=False)
        self._update_local_main()

        # Checkout main branch
        self._run("checkout", self.main_branch)

        try:
            self._do_migration_on_main()
        except Exception:
            # On any failure, return to priv branch and re-raise
            self._run("checkout", self.priv_branch, check=False)
            raise

        # Push main to origin
        try:
            self._run("push", "origin", self.main_branch)
        except RuntimeError:
            self._restore_plain_remote()
            try:
                self._run("push", "origin", self.main_branch)
            except RuntimeError as e:
                self._run("checkout", self.priv_branch, check=False)
                raise RuntimeError(f"Push to main failed: {e}")

        # Switch back to private branch and rebase onto new main
        self._run("checkout", self.priv_branch, check=False)
        self._run("rebase", self.main_branch, check=False)

    def _do_migration_on_main(self):
        """Perform the actual v2 migration on the currently checked-out main branch."""
        milestones_dir = os.path.join(self.data_dir, "milestones")
        if os.path.isdir(milestones_dir):
            raise RuntimeError("Already in v2 split format")

        proj_file = os.path.join(self.data_dir, "project.json")
        if not os.path.isfile(proj_file):
            raise RuntimeError("project.json not found")

        with open(proj_file, "r", encoding="utf-8") as f:
            proj = json.load(f)

        import copy

        req_dir = os.path.join(self.data_dir, "requirements")
        ms_dir = milestones_dir
        act_dir = os.path.join(self.data_dir, "activities")
        os.makedirs(req_dir, exist_ok=True)
        os.makedirs(ms_dir, exist_ok=True)
        os.makedirs(act_dir, exist_ok=True)

        # Write requirements
        for req in proj.get("requirements", []):
            with open(os.path.join(req_dir, f"{req['id']}.json"), "w", encoding="utf-8") as f:
                json.dump(req, f, ensure_ascii=False, indent=2)

        # Write milestones + activities
        for ms in proj.get("milestones", []):
            ms_copy = copy.deepcopy(ms)
            for plan in ms_copy.get("plans", []):
                activities = plan.pop("activities", [])
                with open(os.path.join(act_dir, f"{plan['id']}.json"), "w", encoding="utf-8") as f:
                    json.dump(activities, f, ensure_ascii=False, indent=2)
            with open(os.path.join(ms_dir, f"{ms['id']}.json"), "w", encoding="utf-8") as f:
                json.dump(ms_copy, f, ensure_ascii=False, indent=2)

        # Write config-only project.json
        meta = {
            "id": proj.get("id", ""),
            "name": proj.get("name", ""),
            "description": proj.get("description", ""),
            "remote_url": proj.get("remote_url", ""),
            "remote_username": proj.get("remote_username", ""),
            "remote_password": proj.get("remote_password", ""),
            "remote_branch": proj.get("remote_branch", "main"),
            "tags": proj.get("tags", []),
            "requirement_order": [r["id"] for r in proj.get("requirements", [])],
            "milestone_order": [m["id"] for m in proj.get("milestones", [])],
        }
        with open(proj_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # Stage and commit on main
        self._run("add", "-A")
        status = self._run("status", "--porcelain", check=False)
        if not status.stdout.strip():
            raise RuntimeError("No changes to commit (already migrated?)")
        self._run("commit", "-m", "Migrate to v2 split storage format",
                  extra_config=self._committer_config())

    def reset_to_commit(self, commit_hash):
        """Reset current branch (hard) to the specified commit.

        Args:
            commit_hash: target commit hash

        Raises:
            RuntimeError: if reset fails
        """
        self._run("reset", "--hard", commit_hash)

    def revert_commit(self, commit_hash):
        """Revert a specific commit by creating a new inverse commit.

        Args:
            commit_hash: commit hash to revert

        Raises:
            RuntimeError: if revert fails (e.g. conflict)
        """
        result = self._run("revert", "--no-edit", commit_hash, check=False,
                           extra_config=self._committer_config())
        if result.returncode != 0:
            # Abort on conflict
            self._run("revert", "--abort", check=False)
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Revert conflict")





