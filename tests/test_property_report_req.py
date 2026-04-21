#!/usr/bin/env python3
# Feature: requirement-tracking, Property 7 & 8: Report requirement sections
"""Property-based tests for requirement sections in project reports.

Property 7: Report with requirements contains both sections in correct order.
Validates: Requirements 9.1, 9.2, 9.3, 9.4

Property 8: Report without requirements omits both sections.
Validates: Requirement 9.5
"""

import tempfile
import shutil

from hypothesis import given, settings
from hypothesis import strategies as st

from ganttpilot_core import DataStore
from ganttpilot_gantt import generate_gantt_markdown


# ── Strategies ──────────────────────────────────────────────

_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"),
    min_size=0,
    max_size=30,
)
_nonempty_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"),
    min_size=1,
    max_size=30,
)
_positive_float = st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False)
_progress = st.integers(min_value=0, max_value=100)
_lang = st.sampled_from(["zh", "en"])

task_strategy = st.fixed_dictionaries({
    "subject": _nonempty_text,
    "effort_days": _positive_float,
    "description": _text,
})

requirement_strategy = st.fixed_dictionaries({
    "category": _text,
    "subject": _nonempty_text,
    "description": _text,
    "tasks": st.lists(task_strategy, min_size=0, max_size=3),
})


@settings(max_examples=100, deadline=None)
@given(
    requirements=st.lists(requirement_strategy, min_size=1, max_size=3),
    lang=_lang,
)
def test_report_with_requirements_has_both_sections(requirements, lang):
    """Property 7: Report with requirements contains both sections in correct order.

    The report should contain a "需求分析"/"Requirement Analysis" section
    BEFORE the milestones section, and a "需求跟踪"/"Requirement Tracking"
    section AFTER the plan progress details section.

    Validates: Requirements 9.1, 9.2, 9.3, 9.4
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        ds = DataStore(tmp_dir)
        ds.add_project("ReportTest")
        ds.add_milestone("ReportTest", "MS1", deadline="20250630")

        for req_data in requirements:
            req = ds.add_requirement("ReportTest", req_data["category"],
                                     req_data["subject"], req_data["description"])
            for task_data in req_data["tasks"]:
                ds.add_task("ReportTest", req["id"],
                            task_data["subject"], task_data["effort_days"],
                            task_data["description"])

        proj = ds.get_project("ReportTest")
        md = generate_gantt_markdown(proj, lang=lang)

        # Section headers based on language
        if lang == "zh":
            req_analysis_header = "需求分析"
            req_tracking_header = "需求跟踪"
            milestones_header = "里程碑"
        else:
            req_analysis_header = "Requirement Analysis"
            req_tracking_header = "Requirement Tracking"
            milestones_header = "Milestones"

        # Both sections must exist
        assert req_analysis_header in md, f"Missing '{req_analysis_header}' section"
        assert req_tracking_header in md, f"Missing '{req_tracking_header}' section"

        # Requirement Analysis should appear BEFORE Milestones
        analysis_pos = md.index(req_analysis_header)
        milestones_pos = md.index(milestones_header)
        assert analysis_pos < milestones_pos, \
            "Requirement Analysis section should appear before Milestones"

        # Requirement Tracking should appear AFTER Plan Progress Details
        tracking_pos = md.index(req_tracking_header)
        # The tracking section should be after milestones
        assert tracking_pos > milestones_pos, \
            "Requirement Tracking section should appear after Milestones"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@settings(max_examples=100, deadline=None)
@given(lang=_lang)
def test_report_without_requirements_omits_sections(lang):
    """Property 8: Report without requirements omits both sections.

    When a project has no requirements (empty requirements list),
    the generated report should NOT contain "需求分析" or "需求跟踪" sections.

    Validates: Requirement 9.5
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        ds = DataStore(tmp_dir)
        ds.add_project("NoReqProject")
        ds.add_milestone("NoReqProject", "MS1", deadline="20250630")
        ds.add_plan("NoReqProject", "MS1", "Some Plan", "executor",
                     "20250101", "20250131")

        proj = ds.get_project("NoReqProject")
        # Ensure no requirements
        assert len(proj.get("requirements", [])) == 0

        md = generate_gantt_markdown(proj, lang=lang)

        if lang == "zh":
            assert "需求分析" not in md, "Should not contain '需求分析' section"
            assert "需求跟踪" not in md, "Should not contain '需求跟踪' section"
        else:
            assert "Requirement Analysis" not in md, "Should not contain 'Requirement Analysis' section"
            assert "Requirement Tracking" not in md, "Should not contain 'Requirement Tracking' section"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
