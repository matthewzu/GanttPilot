#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Property test: Bug Condition - ProjectCreateDialog 本地模式窗口高度不足.

Feature: prj_create_window_issue, Property 1: Bug Condition
**Validates: Requirements 1.1, 1.2, 1.3, 2.1, 2.2, 2.3**

This test verifies the EXPECTED behavior for ProjectCreateDialog local mode:
- DIALOG_SIZE_LOCAL should be "450x340"
- __init__ should call _center_dialog with height=340
- _on_mode_change local branch should call _center_dialog with height=340

On UNFIXED code, these tests are EXPECTED TO FAIL (proving the bug exists):
- Current code uses height=200 which is insufficient for all controls.

After the fix, these tests should PASS (confirming the fix is correct).

CRITICAL: This test must FAIL on unfixed code — failure confirms bug exists.
DO NOT attempt to fix the test or the code when it fails.
"""

import inspect
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hypothesis import given, settings
from hypothesis import strategies as st

from ganttpilot_gui import ProjectCreateDialog


# Strategy: generate scenarios representing local mode dialog open events
local_mode_scenario = st.sampled_from([
    {"context": "DIALOG_SIZE_LOCAL constant", "check": "constant"},
    {"context": "__init__ _center_dialog call", "check": "init"},
    {"context": "_on_mode_change local branch", "check": "mode_change"},
])


@given(scenario=local_mode_scenario)
@settings(max_examples=10)
def test_property_bug_condition_local_mode_height(scenario):
    """Property 1: Bug Condition — 本地模式窗口高度应为 340.

    **Validates: Requirements 1.1, 1.2, 1.3, 2.1, 2.2, 2.3**

    Bug Condition: isBugCondition(X) = X.dialog_type = "ProjectCreateDialog"
                   AND X.mode = "local"

    For all ProjectCreateDialog local mode scenarios, the window height
    SHALL be 340 (not 200). This encodes the EXPECTED behavior.

    On unfixed code: FAILS (height is 200, proving the bug exists).
    On fixed code: PASSES (height is 340, confirming the fix).
    """
    check_type = scenario["check"]
    context = scenario["context"]

    if check_type == "constant":
        # Check DIALOG_SIZE_LOCAL class constant
        actual = ProjectCreateDialog.DIALOG_SIZE_LOCAL
        assert actual == "450x340", (
            f"Bug confirmed in {context}: "
            f"DIALOG_SIZE_LOCAL = '{actual}' (expected '450x340'). "
            f"Height 200 is insufficient to display mode selector, "
            f"4 input fields, and OK button."
        )

    elif check_type == "init":
        # Check __init__ source for _center_dialog call with correct height
        source = inspect.getsource(ProjectCreateDialog.__init__)
        # Find _center_dialog calls with 450 width
        calls = re.findall(
            r'_center_dialog\s*\(\s*self\.top\s*,\s*parent\s*,\s*(\d+)\s*,\s*(\d+)\s*\)',
            source
        )
        assert len(calls) > 0, (
            f"No _center_dialog call found in __init__ for {context}"
        )
        width, height = int(calls[0][0]), int(calls[0][1])
        assert height == 340, (
            f"Bug confirmed in {context}: "
            f"_center_dialog(self.top, parent, {width}, {height}) "
            f"uses height={height} (expected 340). "
            f"Bottom controls (committer name/email, OK button) are clipped."
        )

    elif check_type == "mode_change":
        # Check _on_mode_change source for local branch _center_dialog call
        source = inspect.getsource(ProjectCreateDialog._on_mode_change)
        # Find the _center_dialog call with 450 width (local mode branch)
        calls = re.findall(
            r'_center_dialog\s*\(\s*self\.top\s*,\s*self\.parent\s*,\s*(\d+)\s*,\s*(\d+)\s*\)',
            source
        )
        # Filter for the local mode call (width=450)
        local_calls = [(int(w), int(h)) for w, h in calls if int(w) == 450]
        assert len(local_calls) > 0, (
            f"No _center_dialog call with width=450 found in "
            f"_on_mode_change for {context}"
        )
        width, height = local_calls[0]
        assert height == 340, (
            f"Bug confirmed in {context}: "
            f"_center_dialog(self.top, self.parent, {width}, {height}) "
            f"uses height={height} (expected 340). "
            f"Switching back to local mode restores insufficient height."
        )
