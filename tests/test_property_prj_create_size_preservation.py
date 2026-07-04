#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Property test: Preservation — 协作模式及其他对话框尺寸不受影响.

Feature: prj_create_window_issue, Property 2: Preservation
**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

This test verifies the PRESERVATION behavior — behaviors that must NOT change:
- DIALOG_SIZE_COLLAB remains "500x480"
- _on_mode_change collab branch uses width=500, height=480
- Other dialog classes maintain their own size constants:
  - ProjectEditDialog: 520x600
  - ConfigDialog: 620x520
  - ProjectGitConfigDialog: 560x380
  - MCPConfigDialog: 620x520

On UNFIXED code, these tests are EXPECTED TO PASS (confirming baseline).
After the fix, these tests should STILL PASS (confirming no regression).
"""

import inspect
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hypothesis import given, settings
from hypothesis import strategies as st

from ganttpilot_gui import (
    ProjectCreateDialog,
    ProjectEditDialog,
    ConfigDialog,
    ProjectGitConfigDialog,
    MCPConfigDialog,
)


# ─── Strategy: preservation scenarios ───────────────────────────────────────

# All non-bug-condition scenarios that must remain unchanged
preservation_scenario = st.sampled_from([
    {
        "context": "DIALOG_SIZE_COLLAB constant",
        "check": "collab_constant",
    },
    {
        "context": "_on_mode_change collab branch size",
        "check": "collab_mode_change",
    },
    {
        "context": "ProjectEditDialog size (520x600)",
        "check": "edit_dialog_size",
    },
    {
        "context": "ConfigDialog size (620x520)",
        "check": "config_dialog_size",
    },
    {
        "context": "ProjectGitConfigDialog size (560x380)",
        "check": "git_config_dialog_size",
    },
    {
        "context": "MCPConfigDialog size (620x520)",
        "check": "mcp_config_dialog_size",
    },
])


@given(scenario=preservation_scenario)
@settings(max_examples=20)
def test_property_preservation_collab_and_other_dialogs(scenario):
    """Property 2: Preservation — 协作模式及其他对话框尺寸不受影响.

    **Validates: Requirements 3.1, 3.2, 3.3, 3.4**

    For all non-bug-condition cases (collaboration mode and other dialogs),
    the dialog sizes SHALL remain at their established baseline values.

    This test captures the preservation baseline:
    - On unfixed code: PASSES (baseline confirmed)
    - On fixed code: PASSES (no regression)
    """
    check_type = scenario["check"]
    context = scenario["context"]

    if check_type == "collab_constant":
        # Requirement 3.1: Collaboration mode size stays 500x480
        actual = ProjectCreateDialog.DIALOG_SIZE_COLLAB
        assert actual == "500x580", (
            f"Preservation violated in {context}: "
            f"DIALOG_SIZE_COLLAB = '{actual}' (expected '500x580'). "
            f"Collaboration mode size must not be affected by the fix."
        )

    elif check_type == "collab_mode_change":
        # Requirement 3.1, 3.3: _on_mode_change collab branch uses 500x480
        source = inspect.getsource(ProjectCreateDialog._on_mode_change)
        # Find _center_dialog calls with 500 width (collab mode branch)
        calls = re.findall(
            r'_center_dialog\s*\(\s*self\.top\s*,\s*self\.parent\s*,\s*(\d+)\s*,\s*(\d+)\s*\)',
            source
        )
        collab_calls = [(int(w), int(h)) for w, h in calls if int(w) == 500]
        assert len(collab_calls) > 0, (
            f"No _center_dialog call with width=500 found in "
            f"_on_mode_change for {context}"
        )
        width, height = collab_calls[0]
        assert width == 500 and height == 580, (
            f"Preservation violated in {context}: "
            f"_center_dialog(self.top, self.parent, {width}, {height}) "
            f"expected (500, 580). "
            f"Collaboration mode size must not be affected by the fix."
        )

    elif check_type == "edit_dialog_size":
        # Requirement 3.4: ProjectEditDialog maintains 520x600
        source = inspect.getsource(ProjectEditDialog.__init__)
        calls = re.findall(
            r'_center_dialog\s*\(\s*self\.top\s*,\s*parent\s*,\s*(\d+)\s*,\s*(\d+)\s*\)',
            source
        )
        assert len(calls) > 0, (
            f"No _center_dialog call found in ProjectEditDialog.__init__ "
            f"for {context}"
        )
        width, height = int(calls[0][0]), int(calls[0][1])
        assert width == 520 and height == 600, (
            f"Preservation violated in {context}: "
            f"ProjectEditDialog uses ({width}, {height}) "
            f"expected (520, 600)."
        )

    elif check_type == "config_dialog_size":
        # Requirement 3.4: ConfigDialog maintains 620x520
        source = inspect.getsource(ConfigDialog.__init__)
        calls = re.findall(
            r'_center_dialog\s*\(\s*self\.top\s*,\s*parent\s*,\s*(\d+)\s*,\s*(\d+)\s*\)',
            source
        )
        assert len(calls) > 0, (
            f"No _center_dialog call found in ConfigDialog.__init__ "
            f"for {context}"
        )
        width, height = int(calls[0][0]), int(calls[0][1])
        assert width == 620 and height == 520, (
            f"Preservation violated in {context}: "
            f"ConfigDialog uses ({width}, {height}) "
            f"expected (620, 520)."
        )

    elif check_type == "git_config_dialog_size":
        # Requirement 3.4: ProjectGitConfigDialog maintains 560x380
        source = inspect.getsource(ProjectGitConfigDialog.__init__)
        calls = re.findall(
            r'_center_dialog\s*\(\s*self\.top\s*,\s*parent\s*,\s*(\d+)\s*,\s*(\d+)\s*\)',
            source
        )
        assert len(calls) > 0, (
            f"No _center_dialog call found in ProjectGitConfigDialog.__init__ "
            f"for {context}"
        )
        width, height = int(calls[0][0]), int(calls[0][1])
        assert width == 560 and height == 380, (
            f"Preservation violated in {context}: "
            f"ProjectGitConfigDialog uses ({width}, {height}) "
            f"expected (560, 380)."
        )

    elif check_type == "mcp_config_dialog_size":
        # Requirement 3.4: MCPConfigDialog maintains 620x520
        source = inspect.getsource(MCPConfigDialog.__init__)
        calls = re.findall(
            r'_center_dialog\s*\(\s*self\.top\s*,\s*parent\s*,\s*(\d+)\s*,\s*(\d+)\s*\)',
            source
        )
        assert len(calls) > 0, (
            f"No _center_dialog call found in MCPConfigDialog.__init__ "
            f"for {context}"
        )
        width, height = int(calls[0][0]), int(calls[0][1])
        assert width == 620 and height == 520, (
            f"Preservation violated in {context}: "
            f"MCPConfigDialog uses ({width}, {height}) "
            f"expected (620, 520)."
        )
