#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GanttPilot - Git Sync Management / Git同步管理

Work branch: 'priv' (all local commits go here)
Remote branch: configurable main branch (default 'main')

Sync flow:
  1. Commit any pending changes on priv
  2. Ensure remote is configured
  3. Fetch from origin
  4. Checkout main_branch, pull --rebase from origin/main_branch
  5. Checkout priv, rebase onto main_branch
  6. Checkout main_branch, merge --ff-only priv
  7. Push main_branch to origin
  8. Checkout priv (back to work branch)
"""

import os
import subprocess
import sys

# Hide console window on Windows when calling git
_SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


class GitSync:
    """Manages git operations on a project directory"""

    WORK_BRANCH = "priv"

    def __init__(self, data_dir, remote_url="", username="", password="", main_branch="main"):
        self.data_dir = data_dir
        self.remote_url = remote_url
        self.username = username
        self.password = password
        self.main_branch = main_branch or "main"

    def clone_repo(self, remote_url, target_dir, main_branch="main"):
        """Clone a remote repository to target_dir, checkout main_branch, create priv branch."""
        result = subprocess.run(
            ["git", "clone", remote_url, target_dir],
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

    def _run(self, *args, check=True):
        """Run a git command in the data directory"""
        result = subprocess.run(
            ["git"] + list(args),
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
        if not self._branch_exists(self.WORK_BRANCH):
            # If no commits yet, make an initial commit
            status = self._run("status", "--porcelain", check=False)
            if not self._run("log", "--oneline", "-1", check=False).stdout.strip():
                # No commits — create initial
                self._run("add", "-A", check=False)
                self._run("commit", "--allow-empty", "-m", "Initial commit")
            try:
                self._run("checkout", "-b", self.WORK_BRANCH)
            except RuntimeError:
                self._run("checkout", self.WORK_BRANCH)
        else:
            self._run("checkout", self.WORK_BRANCH, check=False)

    def commit(self, message):
        """Stage all changes and commit on priv branch"""
        if not self.is_repo():
            self.init_repo()
        # Ensure we're on priv
        self._run("checkout", self.WORK_BRANCH, check=False)
        self._run("add", "-A")
        status = self._run("status", "--porcelain", check=False)
        if not status.stdout.strip():
            return False
        self._run("commit", "-m", message)
        return True

    def _remote_branch_exists(self, branch):
        """Check if a remote branch exists on origin"""
        result = self._run("ls-remote", "--heads", "origin", branch, check=False)
        return branch in result.stdout

    def sync(self):
        """Sync with bare remote repo.

        Flow:
          1. Commit pending changes on priv
          2. Fetch from origin
          3. Pull remote main (create local main if needed)
          4. Rebase priv onto main
          5. Fast-forward merge priv into main
          6. Push main to origin
          7. Back to priv
        """
        if not self.remote_url or not self.is_repo():
            return False

        mb = self.main_branch
        wb = self.WORK_BRANCH

        # 1. Commit pending on priv
        self._run("checkout", wb, check=False)
        self._run("add", "-A", check=False)
        status = self._run("status", "--porcelain", check=False)
        if status.stdout.strip():
            self._run("commit", "-m", "Auto-commit before sync")

        # 2. Configure remote, fetch
        self._ensure_remote()
        self._run("fetch", "origin", check=False)

        # 3. Ensure local main exists and is up to date
        remote_has_main = self._remote_branch_exists(mb)
        if not self._branch_exists(mb):
            if remote_has_main:
                self._run("checkout", "-b", mb, f"origin/{mb}")
            else:
                # Remote empty — create main from priv
                self._run("checkout", "-b", mb, wb)
        else:
            self._run("checkout", mb)
            if remote_has_main:
                self._run("pull", "--rebase", "origin", mb, check=False)

        # 4. Rebase priv onto main
        self._run("checkout", wb)
        rebase_result = self._run("rebase", mb, check=False)
        if rebase_result.returncode != 0:
            self._run("rebase", "--abort", check=False)
            self._run("merge", mb, "--no-edit", check=False)

        # 5. Merge priv into main (fast-forward)
        self._run("checkout", mb)
        self._run("merge", wb, "--ff-only", check=False)

        # 6. Push main to origin
        self._run("push", "-u", "origin", mb)

        # 7. Back to priv
        self._run("checkout", wb)
        return True
