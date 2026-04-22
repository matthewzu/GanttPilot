#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Property test: Preservation - Dialog modal behavior and normal flow unchanged.

Feature: dialog-focus-bug-fix, Property 2: Preservation
**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

Observation-first methodology:
- On unfixed code, all dialog classes call transient(parent) in __init__ (modal basis)
- On unfixed code, all dialog classes call grab_set() in __init__ (modal core)
- On unfixed code, all dialog classes use tk.Toplevel to create dialog windows

These tests establish the baseline behavior that MUST be preserved after the fix.
On unfixed code, these tests should PASS (confirming baseline behavior exists).
"""

import inspect
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hypothesis import given, settings
from hypothesis import strategies as st

from ganttpilot_gui import (
    PlanDialog,
    PlanEditDialog,
    ActivityDialog,
    ConfigDialog,
    ProjectEditDialog,
    MilestoneEditDialog,
    ActivityEditDialog,
    ProjectGitConfigDialog,
    ProjectCreateDialog,
    MilestoneCreateDialog,
    RequirementDialog,
    RequirementEditDialog,
    TaskDialog,
    TaskEditDialog,
    ProgressDialog,
)

# All 15 dialog classes
ALL_DIALOG_CLASSES = [
    PlanDialog,
    PlanEditDialog,
    ActivityDialog,
    ConfigDialog,
    ProjectEditDialog,
    MilestoneEditDialog,
    ActivityEditDialog,
    ProjectGitConfigDialog,
    ProjectCreateDialog,
    MilestoneCreateDialog,
    RequirementDialog,
    RequirementEditDialog,
    TaskDialog,
    TaskEditDialog,
    ProgressDialog,
]

dialog_class_strategy = st.sampled_from(ALL_DIALOG_CLASSES)


@given(dialog_class=dialog_class_strategy)
@settings(max_examples=50)
def test_property_2a_transient_call_preserved(dialog_class):
    """Property 2a: For all dialog classes, __init__ source contains transient( call.

    **Validates: Requirements 3.3**

    This ensures the modal basis (transient parent relationship) is preserved.
    On unfixed code this should PASS — confirming baseline behavior.
    """
    source = inspect.getsource(dialog_class.__init__)

    assert "transient(" in source, (
        f"{dialog_class.__name__}.__init__ does not call transient() — "
        f"modal basis (parent-child window relationship) is missing"
    )


@given(dialog_class=dialog_class_strategy)
@settings(max_examples=50)
def test_property_2b_grab_set_call_preserved(dialog_class):
    """Property 2b: For all dialog classes, __init__ source contains grab_set() call.

    **Validates: Requirements 3.3, 3.4**

    This ensures the modal core (input grab) is preserved, preventing
    interaction with the main window while a dialog is open.
    On unfixed code this should PASS — confirming baseline behavior.
    """
    source = inspect.getsource(dialog_class.__init__)

    assert "grab_set()" in source, (
        f"{dialog_class.__name__}.__init__ does not call grab_set() — "
        f"modal behavior (input event routing to dialog) is missing"
    )


@given(dialog_class=dialog_class_strategy)
@settings(max_examples=50)
def test_property_2c_toplevel_creation_preserved(dialog_class):
    """Property 2c: For all dialog classes, __init__ uses tk.Toplevel to create dialog window.

    **Validates: Requirements 3.1, 3.2**

    This ensures dialogs are created as proper Toplevel windows.
    On unfixed code this should PASS — confirming baseline behavior.
    """
    source = inspect.getsource(dialog_class.__init__)

    assert "tk.Toplevel(" in source, (
        f"{dialog_class.__name__}.__init__ does not use tk.Toplevel() — "
        f"dialog window creation mechanism is missing or changed"
    )
