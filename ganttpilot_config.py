#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GanttPilot - Configuration Management / 配置管理"""

import json
import os


DEFAULT_CONFIG = {
    "language": "zh",
    "font_size": 10,
    "window_geometry": "1200x700",
    "window_position": "100,100",
    "config_dir": "",
    "data_dir": "",
    "remote_url": "",
    "remote_username": "",
    "remote_password": "",
    "committer_name": "",
    "committer_email": "",
    "compress_threshold": 300,
    "max_chart_width": 4000,
    "pull_interval": 5,
}


class Config:
    """Manages local configuration (font, language, window state, paths, git remote)"""

    def __init__(self, config_dir=None):
        if config_dir:
            self.config_dir = config_dir
        else:
            self.config_dir = os.path.join(os.path.expanduser("~"), ".ganttpilot")
        os.makedirs(self.config_dir, exist_ok=True)
        self.config_path = os.path.join(self.config_dir, "config.json")
        self.data = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        """Load config from file, merge with defaults"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self.data.update(saved)
            except (json.JSONDecodeError, IOError):
                pass
        # If config_dir was saved, update it
        if self.data.get("config_dir") and self.data["config_dir"] != self.config_dir:
            self.config_dir = self.data["config_dir"]
            self.config_path = os.path.join(self.config_dir, "config.json")

    def save(self):
        """Save config to file"""
        self.data["config_dir"] = self.config_dir
        os.makedirs(self.config_dir, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value

    @property
    def language(self):
        return self.data.get("language", "zh")

    @language.setter
    def language(self, val):
        self.data["language"] = val

    @property
    def font_size(self):
        return self.data.get("font_size", 10)

    @font_size.setter
    def font_size(self, val):
        self.data["font_size"] = max(6, min(30, val))

    @property
    def data_dir(self):
        return self.data.get("data_dir", "")

    @data_dir.setter
    def data_dir(self, val):
        self.data["data_dir"] = val

    @property
    def remote_url(self):
        return self.data.get("remote_url", "")

    @property
    def remote_username(self):
        return self.data.get("remote_username", "")

    @property
    def remote_password(self):
        return self.data.get("remote_password", "")
