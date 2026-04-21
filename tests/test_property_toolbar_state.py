#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Property test: toolbar button state mapping.

Feature: requirement-tracking, Property 10: toolbar button state mapping
**Validates: Requirements 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9**

Each node type maps to correct enabled/disabled states per the spec.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hypothesis import given, settings
from hypothesis import strategies as st

from ganttpilot_gui import TOOLBAR_STATE


# Expected state mapping from the design document
EXPECTED_STATES = {
    None:             {"add": False, "edit": False, "delete": False, "up": False, "down": False, "dup": False, "copy": False, "paste": False},
    "project":        {"add": False, "edit": True,  "delete": False, "up": False, "down": False, "dup": True,  "copy": True,  "paste": False},
    "req_analysis":   {"add": True,  "edit": False, "delete": False, "up": False, "down": False, "dup": False, "copy": False, "paste": True},
    "requirement":    {"add": True,  "edit": True,  "delete": True,  "up": True,  "down": True,  "dup": True,  "copy": True,  "paste": True},
    "task":           {"add": False, "edit": True,  "delete": True,  "up": True,  "down": True,  "dup": True,  "copy": True,  "paste": False},
    "plan_execution": {"add": True,  "edit": False, "delete": False, "up": False, "down": False, "dup": False, "copy": False, "paste": True},
    "milestone":      {"add": True,  "edit": True,  "delete": True,  "up": True,  "down": True,  "dup": True,  "copy": True,  "paste": True},
    "plan":           {"add": True,  "edit": True,  "delete": True,  "up": True,  "down": True,  "dup": True,  "copy": True,  "paste": True},
    "activity":       {"add": False, "edit": True,  "delete": True,  "up": False, "down": False, "dup": True,  "copy": True,  "paste": False},
}

# Strategy: sample from all valid node types (including None)
node_type_strategy = st.sampled_from(list(EXPECTED_STATES.keys()))

# Strategy: sample from button names
button_strategy = st.sampled_from(["add", "edit", "delete", "up", "down", "dup", "copy", "paste"])


@given(node_type=node_type_strategy, button=button_strategy)
@settings(max_examples=100)
def test_toolbar_state_matches_spec(node_type, button):
    """Each node type's button state in TOOLBAR_STATE matches the expected spec."""
    assert node_type in TOOLBAR_STATE, f"Node type '{node_type}' not in TOOLBAR_STATE"
    actual = TOOLBAR_STATE[node_type][button]
    expected = EXPECTED_STATES[node_type][button]
    assert actual == expected, (
        f"For node_type={node_type!r}, button={button!r}: "
        f"expected {expected}, got {actual}"
    )


def test_all_node_types_covered():
    """TOOLBAR_STATE covers all expected node types."""
    for node_type in EXPECTED_STATES:
        assert node_type in TOOLBAR_STATE, f"Missing node type: {node_type!r}"


def test_all_buttons_present():
    """Each entry in TOOLBAR_STATE has all 8 button keys."""
    buttons = {"add", "edit", "delete", "up", "down", "dup", "copy", "paste"}
    for node_type, state in TOOLBAR_STATE.items():
        assert set(state.keys()) == buttons, (
            f"Node type {node_type!r} has keys {set(state.keys())}, expected {buttons}"
        )
