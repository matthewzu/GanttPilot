#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GanttPilot - CustomTkinter Integration Layer / CTk 集成层

Provides widget factory functions that use CustomTkinter when available,
falling back to standard tkinter/ttk widgets when not installed.
"""

import tkinter as tk
from tkinter import ttk

# ── CustomTkinter with graceful fallback ──────────────────────
try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False


def init_appearance(mode="System"):
    """Initialize CustomTkinter appearance mode and color theme."""
    if CTK_AVAILABLE:
        ctk.set_appearance_mode(mode)
        ctk.set_default_color_theme("dark-blue")


def set_appearance_mode(mode):
    """Change appearance mode at runtime."""
    if CTK_AVAILABLE:
        ctk.set_appearance_mode(mode)


def create_root():
    """Create the main application window (CTk or Tk)."""
    if CTK_AVAILABLE:
        return ctk.CTk()
    return tk.Tk()


def get_appearance_mode():
    """Get current appearance mode ('dark' or 'light')."""
    if CTK_AVAILABLE:
        return ctk.get_appearance_mode().lower()
    return "light"


def get_canvas_bg():
    """Return canvas background color based on current appearance mode."""
    if get_appearance_mode() == "dark":
        return "#1E1E1E"
    return "white"


def get_treeview_colors():
    """Return color dict for Treeview dark/light mode styling."""
    if get_appearance_mode() == "dark":
        return {
            "background": "#1E1E1E",
            "foreground": "#D4D4D4",
            "fieldbackground": "#1E1E1E",
            "selectbackground": "#264F78",
            "selectforeground": "#FFFFFF",
        }
    return {
        "background": "white",
        "foreground": "black",
        "fieldbackground": "white",
        "selectbackground": "#0078D4",
        "selectforeground": "white",
    }


def get_group_header_colors():
    """Return (background, foreground) for Treeview group header tags."""
    if get_appearance_mode() == "dark":
        return ("#2D3748", "#E2E8F0")
    return ("#d0d0e8", "#000000")


def make_frame(parent, **kwargs):
    """Create a CTkFrame or ttk.Frame."""
    if CTK_AVAILABLE:
        ctk_kwargs = {}
        if "width" in kwargs:
            ctk_kwargs["width"] = kwargs["width"]
        if "height" in kwargs:
            ctk_kwargs["height"] = kwargs["height"]
        # Default to transparent for layout frames (no visible border/bg)
        ctk_kwargs.setdefault("fg_color", "transparent")
        return ctk.CTkFrame(parent, **ctk_kwargs)
    return ttk.Frame(parent, **kwargs)


def make_button(parent, text="", command=None, width=None, state=None, toolbar=False, **kwargs):
    """Create a CTkButton or ttk.Button.

    Args:
        toolbar: If True, use compact transparent style suitable for toolbar icons.
    """
    if CTK_AVAILABLE:
        ctk_kwargs = {"text": text}
        if command:
            ctk_kwargs["command"] = command
        if toolbar:
            # Compact transparent buttons for toolbar — no blue background
            char_w = max(len(text) + 1, width or 3)
            ctk_kwargs["width"] = char_w * 9
            ctk_kwargs["height"] = 28
            ctk_kwargs["fg_color"] = "transparent"
            ctk_kwargs["text_color"] = ("gray10", "gray90")
            ctk_kwargs["hover_color"] = ("gray80", "gray30")
            ctk_kwargs["corner_radius"] = 4
        elif width is not None:
            ctk_kwargs["width"] = width * 8
        if state == tk.DISABLED:
            ctk_kwargs["state"] = "disabled"
        return ctk.CTkButton(parent, **ctk_kwargs)
    ttk_kwargs = {"text": text}
    if command:
        ttk_kwargs["command"] = command
    if width is not None:
        ttk_kwargs["width"] = width
    if state is not None:
        ttk_kwargs["state"] = state
    return ttk.Button(parent, **ttk_kwargs)


def make_label(parent, text="", **kwargs):
    """Create a CTkLabel or ttk.Label."""
    if CTK_AVAILABLE:
        ctk_kwargs = {"text": text}
        if "foreground" in kwargs:
            ctk_kwargs["text_color"] = kwargs["foreground"]
        if "font" in kwargs:
            ctk_kwargs["font"] = kwargs["font"]
        if "anchor" in kwargs:
            ctk_kwargs["anchor"] = kwargs["anchor"]
        return ctk.CTkLabel(parent, **ctk_kwargs)
    return ttk.Label(parent, text=text, **kwargs)


def make_entry(parent, width=None, textvariable=None, state=None, show=None, **kwargs):
    """Create a CTkEntry or ttk.Entry."""
    if CTK_AVAILABLE:
        ctk_kwargs = {}
        if width is not None:
            ctk_kwargs["width"] = width * 8
        if textvariable is not None:
            ctk_kwargs["textvariable"] = textvariable
        if state == "readonly":
            ctk_kwargs["state"] = "disabled"
        if show:
            ctk_kwargs["show"] = show
        return ctk.CTkEntry(parent, **ctk_kwargs)
    ttk_kwargs = {}
    if width is not None:
        ttk_kwargs["width"] = width
    if textvariable is not None:
        ttk_kwargs["textvariable"] = textvariable
    if state is not None:
        ttk_kwargs["state"] = state
    if show:
        ttk_kwargs["show"] = show
    return ttk.Entry(parent, **ttk_kwargs)


def make_combobox(parent, values=None, state="readonly", width=None, **kwargs):
    """Create a CTkComboBox or ttk.Combobox."""
    if CTK_AVAILABLE:
        ctk_kwargs = {}
        if values is not None:
            ctk_kwargs["values"] = values
        if state == "readonly":
            ctk_kwargs["state"] = state
        if width is not None:
            ctk_kwargs["width"] = width * 8
        return ctk.CTkComboBox(parent, **ctk_kwargs)
    ttk_kwargs = {}
    if values is not None:
        ttk_kwargs["values"] = values
    if state is not None:
        ttk_kwargs["state"] = state
    if width is not None:
        ttk_kwargs["width"] = width
    return ttk.Combobox(parent, **ttk_kwargs)


def make_textbox(parent, width=None, height=None, **kwargs):
    """Create a CTkTextbox or tk.Text."""
    if CTK_AVAILABLE:
        ctk_kwargs = {}
        if width is not None:
            ctk_kwargs["width"] = width * 8
        if height is not None:
            ctk_kwargs["height"] = height * 20
        if "undo" in kwargs:
            ctk_kwargs["undo"] = kwargs["undo"]
        return ctk.CTkTextbox(parent, **ctk_kwargs)
    tk_kwargs = {}
    if width is not None:
        tk_kwargs["width"] = width
    if height is not None:
        tk_kwargs["height"] = height
    if "undo" in kwargs:
        tk_kwargs["undo"] = kwargs["undo"]
    if "wrap" in kwargs:
        tk_kwargs["wrap"] = kwargs["wrap"]
    return tk.Text(parent, **tk_kwargs)


def make_scrollbar(parent, orient=tk.VERTICAL, command=None, **kwargs):
    """Create a CTkScrollbar or ttk.Scrollbar."""
    if CTK_AVAILABLE:
        ctk_kwargs = {"orientation": "vertical" if orient == tk.VERTICAL else "horizontal"}
        if command is not None:
            ctk_kwargs["command"] = command
        return ctk.CTkScrollbar(parent, **ctk_kwargs)
    ttk_kwargs = {"orient": orient}
    if command is not None:
        ttk_kwargs["command"] = command
    return ttk.Scrollbar(parent, **ttk_kwargs)


def make_separator(parent, orient=tk.VERTICAL):
    """Create a thin frame as separator (CTk) or ttk.Separator."""
    if CTK_AVAILABLE:
        if orient == tk.VERTICAL:
            return ctk.CTkFrame(parent, width=2, height=20,
                                fg_color=("gray70", "gray40"))
        return ctk.CTkFrame(parent, height=2,
                            fg_color=("gray70", "gray40"))
    return ttk.Separator(parent, orient=orient)


def make_toplevel(parent, title=""):
    """Create a CTkToplevel or tk.Toplevel."""
    if CTK_AVAILABLE:
        top = ctk.CTkToplevel(parent)
        top.title(title)
        return top
    top = tk.Toplevel(parent)
    top.title(title)
    return top


def set_button_state(btn, enabled):
    """Set button state for both CTk and ttk buttons."""
    if CTK_AVAILABLE:
        btn.configure(state="normal" if enabled else "disabled")
    else:
        btn.configure(state=tk.NORMAL if enabled else tk.DISABLED)


def apply_treeview_theme():
    """Apply dark/light mode styling to ttk.Treeview widgets."""
    colors = get_treeview_colors()
    style = ttk.Style()
    style.configure("Treeview",
                    background=colors["background"],
                    foreground=colors["foreground"],
                    fieldbackground=colors["fieldbackground"])
    style.map("Treeview",
              background=[("selected", colors["selectbackground"])],
              foreground=[("selected", colors["selectforeground"])])
