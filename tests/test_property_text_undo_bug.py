#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Property test: Bug Condition - 文本框内 Ctrl+Z/Y 未执行文本级撤销/重做.

Feature: text-undo-redo-fix, Property 1: Bug Condition
**Validates: Requirements 1.1, 1.2, 1.3, 2.1, 2.2, 2.3**

This test verifies the bug condition exists BEFORE the fix is applied:
- All 6 dialog classes' tk.Text controls should have undo=True
- do_undo method should detect tk.Text focus before executing global UndoManager
- do_redo method should detect tk.Text focus before executing global UndoManager

On unfixed code, these tests are EXPECTED TO FAIL (proving the bug exists).
After the fix, these tests should PASS (confirming the fix is correct).
"""

import inspect
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hypothesis import given, settings
from hypothesis import strategies as st

from ganttpilot_gui import (
    ProjectEditDialog,
    MilestoneEditDialog,
    RequirementDialog,
    RequirementEditDialog,
    TaskDialog,
    TaskEditDialog,
    GanttPilotGUI,
)

# The 6 dialog classes that contain tk.Text description fields
TEXT_DIALOG_CLASSES = [
    ProjectEditDialog,
    MilestoneEditDialog,
    RequirementDialog,
    RequirementEditDialog,
    TaskDialog,
    TaskEditDialog,
]

dialog_class_strategy = st.sampled_from(TEXT_DIALOG_CLASSES)


@given(dialog_class=dialog_class_strategy)
@settings(max_examples=20)
def test_property_1a_text_undo_enabled(dialog_class):
    """Property 1a: For all 6 dialog classes, tk.Text controls should have undo=True.

    **Validates: Requirements 1.1, 1.2, 1.3**

    Checks that the __init__ source code contains undo=True in the tk.Text() call.
    On unfixed code this FAILS — tk.Text is created without undo=True.
    """
    source = inspect.getsource(dialog_class.__init__)

    # Verify tk.Text( call exists in the source
    assert "tk.Text(" in source, (
        f"{dialog_class.__name__}.__init__ does not create a tk.Text widget"
    )

    # Verify undo=True is present in the source
    assert "undo=True" in source, (
        f"{dialog_class.__name__}.__init__: tk.Text() is created without undo=True — "
        f"tkinter built-in text undo/redo is disabled, Ctrl+Z/Y cannot perform text-level undo"
    )


def test_property_1b_do_undo_text_focus_detection():
    """Property 1b: do_undo method should contain tk.Text focus detection logic.

    **Validates: Requirements 2.1, 2.2, 2.3**

    Checks that do_undo source contains isinstance + tk.Text or focus_get checks
    to route Ctrl+Z to text-level undo when focus is in a tk.Text widget.
    On unfixed code this FAILS — do_undo unconditionally calls UndoManager.undo().
    """
    source = inspect.getsource(GanttPilotGUI.do_undo)

    has_isinstance_check = "isinstance" in source and "tk.Text" in source
    has_focus_get_check = "focus_get" in source

    assert has_isinstance_check or has_focus_get_check, (
        "GanttPilotGUI.do_undo does not check if focus is in a tk.Text widget — "
        "Ctrl+Z always triggers global UndoManager instead of text-level undo. "
        "Expected isinstance(..., tk.Text) or focus_get() check in method source."
    )


def test_property_1c_do_redo_text_focus_detection():
    """Property 1c: do_redo method should contain tk.Text focus detection logic.

    **Validates: Requirements 2.1, 2.2, 2.3**

    Checks that do_redo source contains isinstance + tk.Text or focus_get checks
    to route Ctrl+Y to text-level redo when focus is in a tk.Text widget.
    On unfixed code this FAILS — do_redo unconditionally calls UndoManager.redo().
    """
    source = inspect.getsource(GanttPilotGUI.do_redo)

    has_isinstance_check = "isinstance" in source and "tk.Text" in source
    has_focus_get_check = "focus_get" in source

    assert has_isinstance_check or has_focus_get_check, (
        "GanttPilotGUI.do_redo does not check if focus is in a tk.Text widget — "
        "Ctrl+Y always triggers global UndoManager instead of text-level redo. "
        "Expected isinstance(..., tk.Text) or focus_get() check in method source."
    )
