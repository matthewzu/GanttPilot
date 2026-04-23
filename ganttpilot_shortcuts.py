#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GanttPilot - Keyboard Shortcut Manager / 键盘快捷键管理

Centralized management of keyboard shortcuts: registration, lookup,
conflict detection, and persistence via Config.
"""

from __future__ import annotations

import re
import tkinter as tk
from tkinter import ttk


# ── Format conversion helpers ────────────────────────────────

# Mapping from tkinter modifier names to display names
_TK_MOD_TO_DISPLAY = {
    "Control": "Ctrl",
    "Alt": "Alt",
    "Shift": "Shift",
}

_DISPLAY_MOD_TO_TK = {v: k for k, v in _TK_MOD_TO_DISPLAY.items()}


def tk_event_to_display(event_str: str) -> str:
    """Convert a tkinter event string to a human-readable display format.

    Examples:
        '<Control-n>'  -> 'Ctrl+N'
        '<Alt-Up>'     -> 'Alt+Up'
        '<F2>'         -> 'F2'
        '<Control-Shift-s>' -> 'Ctrl+Shift+S'
        '<Delete>'     -> 'Delete'
    """
    if not event_str:
        return ""
    # Strip angle brackets
    inner = event_str.strip("<>")
    parts = inner.split("-")
    display_parts = []
    for part in parts:
        if part in _TK_MOD_TO_DISPLAY:
            display_parts.append(_TK_MOD_TO_DISPLAY[part])
        else:
            # Capitalize single-letter keys, keep others as-is
            if len(part) == 1:
                display_parts.append(part.upper())
            else:
                display_parts.append(part)
    return "+".join(display_parts)


def display_to_tk_event(display_str: str) -> str:
    """Convert a human-readable display string to a tkinter event string.

    Examples:
        'Ctrl+N'       -> '<Control-n>'
        'Alt+Up'       -> '<Alt-Up>'
        'F2'           -> '<F2>'
        'Ctrl+Shift+S' -> '<Control-Shift-s>'
        'Delete'       -> '<Delete>'
    """
    if not display_str:
        return ""
    parts = display_str.split("+")
    tk_parts = []
    for part in parts:
        stripped = part.strip()
        if stripped in _DISPLAY_MOD_TO_TK:
            tk_parts.append(_DISPLAY_MOD_TO_TK[stripped])
        else:
            # Single letter keys are lowercased in tkinter events
            if len(stripped) == 1:
                tk_parts.append(stripped.lower())
            else:
                tk_parts.append(stripped)
    return "<" + "-".join(tk_parts) + ">"


# ── Valid tkinter event pattern for basic validation ─────────
_VALID_TK_EVENT_RE = re.compile(
    r"^<(?:(?:Control|Alt|Shift)-)*(?:[a-zA-Z0-9]|F[0-9]{1,2}|Up|Down|Left|Right|Delete|Insert|Home|End|"
    r"Page_Up|Page_Down|Return|Escape|Tab|BackSpace|space)>$"
)


def _is_valid_tk_event(event_str: str) -> bool:
    """Check if a string looks like a valid tkinter key event."""
    return bool(_VALID_TK_EVENT_RE.match(event_str))


# ── ShortcutManager ──────────────────────────────────────────

class ShortcutManager:
    """Centralized keyboard shortcut registration, lookup, conflict detection, and persistence."""

    DEFAULT_SHORTCUTS = {
        "undo":      "<Control-z>",
        "redo":      "<Control-y>",
        "copy":      "<Control-c>",
        "paste":     "<Control-v>",
        "add":       "<Control-n>",
        "edit":      "<F2>",
        "delete":    "<Delete>",
        "move_up":   "<Alt-Up>",
        "move_down": "<Alt-Down>",
        "duplicate": "<Control-d>",
        "sync":      "<Control-s>",
        "refresh":   "<F5>",
    }

    # Map action_id -> toolbar button key in TOOLBAR_STATE dict
    _ACTION_TO_TOOLBAR_KEY = {
        "add":       "add",
        "edit":      "edit",
        "delete":    "delete",
        "move_up":   "up",
        "move_down": "down",
        "duplicate": "dup",
        "copy":      "copy",
        "paste":     "paste",
    }

    def __init__(self, root, config):
        """Initialize ShortcutManager.

        Args:
            root: tkinter root window (Tk instance).
            config: Config instance for persistence.
        """
        self.root = root
        self.bindings: dict[str, str] = {}      # action_id -> tkinter event string
        self.handlers: dict[str, callable] = {}  # action_id -> callback
        self._gui = None  # reference to GanttPilotGUI, set externally
        self.load_from_config(config)

    def load_from_config(self, config):
        """Load shortcut bindings from Config, falling back to defaults.

        Invalid or unknown entries in config are silently ignored.
        """
        # Start with defaults
        self.bindings = dict(self.DEFAULT_SHORTCUTS)
        saved = config.get("shortcuts")
        if isinstance(saved, dict):
            for action_id, key_event in saved.items():
                if action_id in self.DEFAULT_SHORTCUTS and isinstance(key_event, str):
                    if key_event == "" or _is_valid_tk_event(key_event):
                        self.bindings[action_id] = key_event

    def save_to_config(self, config):
        """Persist current bindings to Config's shortcuts field."""
        config.set("shortcuts", dict(self.bindings))

    # ── Registration ─────────────────────────────────────────

    def register_all(self):
        """Bind all shortcuts to the tkinter root window."""
        for action_id, key_event in self.bindings.items():
            if key_event:
                # Use a closure to capture action_id
                self.root.bind(key_event, self._make_handler(action_id))

    def unregister_all(self):
        """Unbind all currently registered shortcuts from the tkinter root."""
        for action_id, key_event in self.bindings.items():
            if key_event:
                try:
                    self.root.unbind(key_event)
                except Exception:
                    pass

    def _make_handler(self, action_id):
        """Create a bound event handler for a specific action_id."""
        def handler(event):
            return self._on_key(action_id, event)
        return handler

    # ── Action handlers ──────────────────────────────────────

    def set_action_handler(self, action_id, handler):
        """Register a callback for an action_id."""
        self.handlers[action_id] = handler

    def get_shortcut(self, action_id) -> str:
        """Get the tkinter event string for an action_id. Returns '' if unbound."""
        return self.bindings.get(action_id, "")

    def get_display_string(self, action_id) -> str:
        """Get human-readable shortcut string (e.g. 'Ctrl+N'). Returns '' if unbound."""
        key_event = self.bindings.get(action_id, "")
        return tk_event_to_display(key_event)

    # ── Shortcut modification ────────────────────────────────

    def set_shortcut(self, action_id, key_event):
        """Set a shortcut binding. Returns conflicting action_id or None.

        If key_event is empty string, clears the binding for that action.
        """
        if key_event:
            conflict = self.check_conflict(action_id, key_event)
            if conflict:
                return conflict
        self.bindings[action_id] = key_event
        return None

    def check_conflict(self, action_id, key_event) -> str | None:
        """Check if key_event conflicts with another action.

        Returns the conflicting action_id, or None if no conflict.
        """
        if not key_event:
            return None
        normalized = key_event.lower()
        for aid, evt in self.bindings.items():
            if aid != action_id and evt and evt.lower() == normalized:
                return aid
        return None

    def reset_to_defaults(self):
        """Reset all bindings to DEFAULT_SHORTCUTS."""
        self.bindings = dict(self.DEFAULT_SHORTCUTS)

    def get_all_bindings(self) -> dict:
        """Return a copy of all action_id -> key_event mappings."""
        return dict(self.bindings)

    # ── Focus-aware key dispatch ─────────────────────────────

    def _on_key(self, action_id, event):
        """Unified key event handler with focus awareness and state checking.

        1. Skip if focus is in a text input widget (Entry/Text).
        2. Skip if the corresponding toolbar button is disabled.
        3. Execute the registered handler.
        """
        # 1. Check focus — let text widgets handle their own keys
        focused = self.root.focus_get()
        if isinstance(focused, (tk.Entry, tk.Text, ttk.Entry)):
            return  # Don't consume — let the widget handle it

        # 2. Check if the action's toolbar button is enabled
        if not self._is_action_enabled(action_id):
            return "break"

        # 3. Dispatch to handler
        handler = self.handlers.get(action_id)
        if handler:
            try:
                handler()
            except Exception:
                pass
        return "break"

    def _is_action_enabled(self, action_id):
        """Check whether the toolbar button for this action is currently enabled.

        Actions without a toolbar mapping (undo, redo, sync, refresh) are
        always considered enabled.
        """
        toolbar_key = self._ACTION_TO_TOOLBAR_KEY.get(action_id)
        if toolbar_key is None:
            # No toolbar button for this action — always enabled
            return True

        gui = self._gui
        if gui is None:
            return True

        # Map toolbar key to the actual button widget
        btn_map = {
            "add":    getattr(gui, "tb_add_btn", None),
            "edit":   getattr(gui, "tb_edit_btn", None),
            "delete": getattr(gui, "tb_delete_btn", None),
            "up":     getattr(gui, "tb_up_btn", None),
            "down":   getattr(gui, "tb_down_btn", None),
            "dup":    getattr(gui, "tb_dup_btn", None),
            "copy":   getattr(gui, "tb_copy_btn", None),
            "paste":  getattr(gui, "tb_paste_btn", None),
        }
        btn = btn_map.get(toolbar_key)
        if btn is None:
            return True
        try:
            return str(btn.cget("state")) != str(tk.DISABLED)
        except Exception:
            return True
