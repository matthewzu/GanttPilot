#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Property test: Bug Condition - Dialog focus_set missing and focus restoration missing.

Feature: dialog-focus-bug-fix, Property 1: Bug Condition
**Validates: Requirements 1.1, 1.2**

This test verifies the bug condition exists BEFORE the fix is applied:
- All dialog classes should call focus_set() after grab_set() in __init__
- GanttPilotGUI should bind <FocusIn> for focus restoration
- GanttPilotGUI should have _active_dialog attribute for tracking

On unfixed code, these tests are EXPECTED TO FAIL (proving the bug exists).
After the fix, these tests should PASS (confirming the fix is correct).
"""

import inspect
import re
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
    GanttPilotGUI,
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
def test_property_1a_focus_set_after_grab_set(dialog_class):
    """Property 1a: For all dialog classes, __init__ source should contain
    focus_set() call after grab_set().

    **Validates: Requirements 1.1, 1.2**

    On unfixed code this FAILS — proving the bug exists.
    """
    source = inspect.getsource(dialog_class.__init__)

    # Find positions of grab_set() and focus_set() in the source
    grab_set_match = re.search(r'\.grab_set\(\)', source)
    focus_set_match = re.search(r'\.focus_set\(\)', source)

    assert grab_set_match is not None, (
        f"{dialog_class.__name__}.__init__ does not call grab_set()"
    )
    assert focus_set_match is not None, (
        f"{dialog_class.__name__}.__init__ does not call focus_set() — "
        f"grab_set() found at position {grab_set_match.start()} but no focus_set() call follows"
    )

    # focus_set() should appear AFTER grab_set()
    assert focus_set_match.start() > grab_set_match.start(), (
        f"{dialog_class.__name__}.__init__: focus_set() (pos {focus_set_match.start()}) "
        f"should appear after grab_set() (pos {grab_set_match.start()})"
    )


def test_property_1b_focusin_binding_on_main_gui():
    """Property 1b: GanttPilotGUI should bind <FocusIn> event handler
    for focus restoration.

    **Validates: Requirements 1.1, 1.2**

    On unfixed code this FAILS — proving the bug exists.
    """
    source = inspect.getsource(GanttPilotGUI.__init__)

    assert "<FocusIn>" in source, (
        "GanttPilotGUI.__init__ does not bind <FocusIn> event — "
        "no focus restoration mechanism for modal dialogs after window switching"
    )


def test_property_1c_active_dialog_attribute():
    """Property 1c: GanttPilotGUI should have _active_dialog attribute
    for tracking active modal dialogs.

    **Validates: Requirements 1.1, 1.2**

    On unfixed code this FAILS — proving the bug exists.
    """
    source = inspect.getsource(GanttPilotGUI.__init__)

    assert "_active_dialog" in source, (
        "GanttPilotGUI.__init__ does not initialize _active_dialog attribute — "
        "no mechanism to track active modal dialogs for focus restoration"
    )
