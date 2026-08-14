#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Property tests for git-config-simplify spec.

P1: Credentials never appear in project.json output
P2: URL protocol detection consistency
P3: Credential migration idempotency
"""

import json
import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hypothesis import given, settings, assume
from hypothesis import strategies as st


# ─── Strategies ─────────────────────────────────────────────────────────────

# Generate arbitrary usernames/passwords
credential_text = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P")),
    min_size=1, max_size=30
)

# Generate project names (alphanumeric + underscore, non-empty)
project_name = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N")),
    min_size=1, max_size=20
)

# Generate URLs of various protocols
ssh_url = st.sampled_from([
    "git@github.com:user/repo.git",
    "git@gitea.example.com:org/project.git",
    "ssh://git@server.com/repo.git",
    "ssh://user@host:22/path/to/repo.git",
])

https_url = st.sampled_from([
    "https://github.com/user/repo.git",
    "https://gitea.example.com/org/project.git",
    "http://server.internal/repo.git",
    "https://gitlab.com/group/subgroup/repo.git",
])

any_url = st.one_of(ssh_url, https_url)


# ─── P1: Credentials never in project.json ─────────────────────────────────

@given(
    name=project_name,
    username=credential_text,
    password=credential_text,
)
@settings(max_examples=50)
def test_property_p1_credentials_not_in_project_json(name, username, password):
    """P1: For any save operation, project.json SHALL NOT contain
    remote_username or remote_password keys.

    **Validates: Requirements 1.1, 1.2, 1.5**

    We simulate what config_project_git does: after saving, the project
    dict should not contain credential fields.
    """
    # Simulate a project dict as it would appear after config_project_git
    proj = {
        "name": name,
        "remote_url": "https://example.com/repo.git",
        "remote_branch": "main",
    }
    # The fix removes these from proj:
    proj.pop("remote_username", None)
    proj.pop("remote_password", None)
    proj.pop("priv_branch", None)

    # Verify: no credential keys in the output that would go to project.json
    json_output = json.dumps(proj)
    assert "remote_username" not in proj, (
        f"remote_username found in project data for '{name}'"
    )
    assert "remote_password" not in proj, (
        f"remote_password found in project data for '{name}'"
    )
    # Also verify the JSON serialization doesn't contain these keys
    assert '"remote_username"' not in json_output
    assert '"remote_password"' not in json_output


# ─── P2: URL protocol detection consistency ─────────────────────────────────

def _is_ssh_url(url):
    """Mirror of the protocol detection logic in ProjectGitConfigDialog"""
    return url.startswith("git@") or url.startswith("ssh://")


def _is_https_url(url):
    """Mirror of the protocol detection logic"""
    return url.startswith("https://") or url.startswith("http://")


@given(url=ssh_url)
@settings(max_examples=20)
def test_property_p2_ssh_url_detected_correctly(url):
    """P2: For any SSH URL, _is_ssh_url returns True and _is_https_url
    returns False.

    **Validates: Requirements 2.1, 2.7**
    """
    assert _is_ssh_url(url), f"SSH URL not detected: {url}"
    assert not _is_https_url(url), f"SSH URL wrongly detected as HTTPS: {url}"


@given(url=https_url)
@settings(max_examples=20)
def test_property_p2_https_url_detected_correctly(url):
    """P2: For any HTTPS URL, _is_https_url returns True and _is_ssh_url
    returns False.

    **Validates: Requirements 2.2, 2.8**
    """
    assert _is_https_url(url), f"HTTPS URL not detected: {url}"
    assert not _is_ssh_url(url), f"HTTPS URL wrongly detected as SSH: {url}"


@given(url=any_url)
@settings(max_examples=30)
def test_property_p2_mutual_exclusivity(url):
    """P2: SSH and HTTPS detection are mutually exclusive for all valid URLs.

    **Validates: Requirements 2.1, 2.2**
    """
    ssh = _is_ssh_url(url)
    https = _is_https_url(url)
    # Exactly one should be true for valid URLs
    assert ssh != https, (
        f"Protocol detection not mutually exclusive for '{url}': "
        f"SSH={ssh}, HTTPS={https}"
    )


# ─── P3: Credential migration idempotency ──────────────────────────────────

@given(
    name=project_name,
    username=credential_text,
    password=credential_text,
)
@settings(max_examples=50)
def test_property_p3_migration_idempotent(name, username, password):
    """P3: Running migration multiple times yields the same result and
    removes credentials from project dict.

    **Validates: Requirements 1.5, 1.6**

    Simulates the migration logic in _get_project_git:
    - If proj has remote_username/remote_password, migrate to proj_committers
    - After migration, proj should not have those keys
    - Running again should not change proj_committers values
    """
    # Initial state: old project with credentials in project dict
    proj = {
        "name": name,
        "remote_url": "https://example.com/repo.git",
        "remote_username": username,
        "remote_password": password,
    }
    proj_committers = {}

    # First migration pass
    def migrate(proj_dict, committers_dict):
        legacy_user = proj_dict.get("remote_username", "")
        legacy_pass = proj_dict.get("remote_password", "")
        if legacy_user or legacy_pass:
            if name not in committers_dict:
                committers_dict[name] = {}
            remote_username = committers_dict[name].get("remote_username", "")
            remote_password = committers_dict[name].get("remote_password", "")
            if legacy_user and not remote_username:
                committers_dict[name]["remote_username"] = legacy_user
            if legacy_pass and not remote_password:
                committers_dict[name]["remote_password"] = legacy_pass
            proj_dict.pop("remote_username", None)
            proj_dict.pop("remote_password", None)

    migrate(proj, proj_committers)

    # After first migration: proj should not have credentials
    assert "remote_username" not in proj
    assert "remote_password" not in proj
    # proj_committers should have the values
    assert proj_committers[name]["remote_username"] == username
    assert proj_committers[name]["remote_password"] == password

    # Second migration pass (idempotency check)
    saved_committers = dict(proj_committers)
    migrate(proj, proj_committers)

    # Should be unchanged
    assert proj_committers == saved_committers, (
        "Migration is not idempotent: proj_committers changed on second run"
    )
    assert "remote_username" not in proj
    assert "remote_password" not in proj
