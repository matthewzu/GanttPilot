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

import os
import subprocess
import sys

# Hide console window on Windows when calling git
_SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


class GitSync:
    """Manages git operations on a project directory"""

    WORK_BRANCH = "priv"

    def __init__(self, data_dir, remote_url="", username="", password="", main_branch="main",
                 committer_name="", committer_email="", priv_branch=""):
        self.data_dir = data_dir
        self.remote_url = remote_url
        self.username = username
        self.password = password
        self.main_branch = main_branch or "main"
        self.committer_name = committer_name
        self.committer_email = committer_email
        self.priv_branch = priv_branch or (f"priv_{committer_name}" if committer_name else self.WORK_BRANCH)

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
                ["git", "checkout", "-b", "priv"],
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
        if check and result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
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
            # If no commits yet, make an initial commit
            status = self._run("status", "--porcelain", check=False)
            if not self._run("log", "--oneline", "-1", check=False).stdout.strip():
                # No commits — create initial
                self._run("add", "-A", check=False)
                self._run("commit", "--allow-empty", "-m", "Initial commit")
            try:
                self._run("checkout", "-b", self.priv_branch)
            except RuntimeError:
                self._run("checkout", self.priv_branch)
        else:
            self._run("checkout", self.priv_branch, check=False)

    def commit(self, message):
        """Stage all changes and commit on priv branch"""
        if not self.is_repo():
            self.init_repo()
        # Ensure we're on priv branch
        self._run("checkout", self.priv_branch, check=False)
        self._run("add", "-A")
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

        # 1. Commit pending on priv_branch
        self._run("checkout", wb, check=False)
        self._run("add", "-A", check=False)
        status = self._run("status", "--porcelain", check=False)
        if status.stdout.strip():
            self._run("commit", "-m", "Auto-commit before sync",
                      extra_config=self._committer_config())

        # 2. Configure remote, fetch
        self._ensure_remote()
        self._run("fetch", "origin", check=False)

        # 3. Push priv_branch to origin
        self._run("push", "-u", "origin", wb)
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


    def manual_rebase(self):
        """手动将私有分支 rebase 到远端主分支最新提交。

        Raises:
            RuntimeError: rebase 冲突时抛出异常
        """
        result = self._run("rebase", f"origin/{self.main_branch}", check=False)
        if result.returncode != 0:
            self._run("rebase", "--abort", check=False)
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Rebase conflict, aborted")




