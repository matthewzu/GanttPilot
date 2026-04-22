#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Property test: Preservation - 非文本框焦点时全局撤销/重做行为不变.

Feature: text-undo-redo-fix, Property 2: Preservation
**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

This test verifies that existing behaviors are PRESERVED before and after the fix:
- UndoManager core methods remain unchanged
- Global Ctrl+Z/Y bindings still exist in GanttPilotGUI.__init__
- Toolbar undo/redo buttons still bind to do_undo / do_redo
- Dialog tk.Text controls retain original attributes like wrap=tk.WORD

On unfixed code, these tests should PASS (confirming baseline behavior).
After the fix, these tests should still PASS (confirming no regression).
"""

import inspect
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hypothesis import given, settings
from hypothesis import strategies as st

from ganttpilot_gui import (
    UndoManager,
    GanttPilotGUI,
    ProjectEditDialog,
    MilestoneEditDialog,
    RequirementDialog,
    RequirementEditDialog,
    TaskDialog,
    TaskEditDialog,
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


# --- Property 2a: UndoManager core methods preserved ---

UNDO_MANAGER_METHODS = ["save_snapshot", "undo", "redo", "can_undo", "can_redo"]

undo_method_strategy = st.sampled_from(UNDO_MANAGER_METHODS)


@given(method_name=undo_method_strategy)
@settings(max_examples=20)
def test_property_2a_undo_manager_core_logic_preserved(method_name):
    """Property 2a: UndoManager core method signatures and logic are unchanged.

    **Validates: Requirements 3.1, 3.2**

    Verifies that UndoManager's undo/redo/save_snapshot/can_undo/can_redo methods
    contain the expected core operations (deepcopy, undo_stack, redo_stack).
    """
    method = getattr(UndoManager, method_name)
    source = inspect.getsource(method)

    # All methods should reference the stacks
    assert "undo_stack" in source or "redo_stack" in source, (
        f"UndoManager.{method_name} does not reference undo_stack or redo_stack"
    )

    # save_snapshot must use deepcopy
    if method_name == "save_snapshot":
        assert "deepcopy" in source, (
            "UndoManager.save_snapshot does not use deepcopy — snapshot logic may be broken"
        )
        assert "redo_stack" in source, (
            "UndoManager.save_snapshot does not reference redo_stack — clear logic may be missing"
        )

    # undo must push to redo_stack and pop from undo_stack
    if method_name == "undo":
        assert "redo_stack" in source and "undo_stack" in source, (
            "UndoManager.undo does not reference both stacks"
        )
        assert "deepcopy" in source, (
            "UndoManager.undo does not use deepcopy"
        )

    # redo must push to undo_stack and pop from redo_stack
    if method_name == "redo":
        assert "undo_stack" in source and "redo_stack" in source, (
            "UndoManager.redo does not reference both stacks"
        )
        assert "deepcopy" in source, (
            "UndoManager.redo does not use deepcopy"
        )


# --- Property 2b: Global Ctrl+Z/Y bindings still exist ---

def test_property_2b_global_keybindings_exist():
    """Property 2b: GanttPilotGUI.__init__ still binds <Control-z> and <Control-y>.

    **Validates: Requirements 3.1, 3.2**

    Verifies that the global keyboard shortcuts for undo/redo are still registered
    in the __init__ method, ensuring non-text-widget undo/redo continues to work.
    """
    source = inspect.getsource(GanttPilotGUI.__init__)

    assert 'bind("<Control-z>"' in source or "bind('<Control-z>'" in source, (
        "GanttPilotGUI.__init__ does not bind <Control-z> — global undo shortcut is missing"
    )

    assert 'bind("<Control-y>"' in source or "bind('<Control-y>'" in source, (
        "GanttPilotGUI.__init__ does not bind <Control-y> — global redo shortcut is missing"
    )

    # Verify bindings reference do_undo and do_redo
    assert "do_undo" in source, (
        "GanttPilotGUI.__init__ does not reference do_undo in keybinding setup"
    )
    assert "do_redo" in source, (
        "GanttPilotGUI.__init__ does not reference do_redo in keybinding setup"
    )


# --- Property 2c: Toolbar buttons still bind to do_undo / do_redo ---

def test_property_2c_toolbar_buttons_bind_undo_redo():
    """Property 2c: Toolbar undo/redo buttons still bind to do_undo / do_redo.

    **Validates: Requirements 3.4**

    Verifies that create_widgets source contains toolbar button definitions
    that use command=self.do_undo and command=self.do_redo.
    """
    source = inspect.getsource(GanttPilotGUI.create_widgets)

    # Check undo button binding
    assert "command=self.do_undo" in source, (
        "GanttPilotGUI.create_widgets: toolbar undo button does not bind to self.do_undo"
    )

    # Check redo button binding
    assert "command=self.do_redo" in source, (
        "GanttPilotGUI.create_widgets: toolbar redo button does not bind to self.do_redo"
    )

    # Verify the buttons are assigned to instance attributes
    assert "self.undo_btn" in source, (
        "GanttPilotGUI.create_widgets: undo_btn not found — toolbar undo button may be missing"
    )
    assert "self.redo_btn" in source, (
        "GanttPilotGUI.create_widgets: redo_btn not found — toolbar redo button may be missing"
    )


# --- Property 2d: Dialog tk.Text controls retain wrap=tk.WORD ---

@given(dialog_class=dialog_class_strategy)
@settings(max_examples=20)
def test_property_2d_text_widget_wrap_preserved(dialog_class):
    """Property 2d: Dialog tk.Text controls retain wrap=tk.WORD attribute.

    **Validates: Requirements 3.3**

    Verifies that all 6 dialog classes' tk.Text widgets still have wrap=tk.WORD,
    ensuring original text widget attributes are preserved after the fix.
    """
    source = inspect.getsource(dialog_class.__init__)

    # Verify tk.Text( call exists
    assert "tk.Text(" in source, (
        f"{dialog_class.__name__}.__init__ does not create a tk.Text widget"
    )

    # Verify wrap=tk.WORD is present
    assert "wrap=tk.WORD" in source, (
        f"{dialog_class.__name__}.__init__: tk.Text() missing wrap=tk.WORD — "
        f"original text widget attribute has been removed or changed"
    )
