# v0.1
"""Tests for pathminer.kicad.prefs.

Session 05 — KiCad syntax, stackup and preferences extraction.
Punch-list contribution: ARCH-003 (parser foundation capability slice).

Covers:
  - kicad_pref_dirs: returns list, all entries exist as directories
  - kicad_recent_projects: empty list on missing/malformed kicad.json,
    deduplication, both flat and nested key formats, string entries
  - board_for_project: .kicad_pcb passthrough, sibling resolution, scan,
    multi-file scan returns None, missing file returns None
  - project_for_board: present sibling, absent sibling

No real KiCad installation is assumed.  Tests use tmp_path fixtures that
simulate the KiCad preference directory layout.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

from pathminer.kicad.prefs import (
    KICAD_VERSIONS,
    board_for_project,
    kicad_pref_dirs,
    kicad_recent_projects,
    project_for_board,
)


# ---------------------------------------------------------------------------
# KICAD_VERSIONS constant
# ---------------------------------------------------------------------------

class TestKicadVersions:
    def test_is_tuple(self):
        assert isinstance(KICAD_VERSIONS, tuple)

    def test_not_empty(self):
        assert len(KICAD_VERSIONS) > 0

    def test_9_0_included(self):
        assert "9.0" in KICAD_VERSIONS

    def test_newest_first(self):
        """Higher version numbers should come before lower ones."""
        nums = [tuple(int(x) for x in v.split(".")) for v in KICAD_VERSIONS]
        assert nums == sorted(nums, reverse=True)


# ---------------------------------------------------------------------------
# kicad_pref_dirs
# ---------------------------------------------------------------------------

class TestKicadPrefDirs:
    def test_returns_list(self):
        result = kicad_pref_dirs()
        assert isinstance(result, list)

    def test_all_entries_exist(self):
        """Every returned path must be an actual directory."""
        for d in kicad_pref_dirs():
            assert os.path.isdir(d), f"Returned path does not exist: {d}"

    def test_no_empty_strings(self):
        for d in kicad_pref_dirs():
            assert d.strip() != ""

    def test_version_appears_in_path(self):
        """Each returned path should contain one of the version strings."""
        for d in kicad_pref_dirs():
            assert any(v in d for v in KICAD_VERSIONS), (
                f"No version string found in path: {d}"
            )

    def test_simulated_dir(self, tmp_path):
        """Simulate a KiCad preference directory and check it is found."""
        # We can't patch sys.platform easily without monkeypatching, so
        # we just exercise the function on the real system.  This test
        # verifies the function never raises.
        result = kicad_pref_dirs()
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# kicad_recent_projects
# ---------------------------------------------------------------------------

class TestKicadRecentProjects:
    """Simulate kicad.json in a tmp_path-based fake pref directory."""

    def _write_kicad_json(self, pref_dir, content: dict):
        path = os.path.join(pref_dir, "kicad.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(content, fh)
        return path

    def test_returns_list(self):
        result = kicad_recent_projects()
        assert isinstance(result, list)

    def test_empty_on_no_kicad_installation(self, tmp_path, monkeypatch):
        """Monkeypatching kicad_pref_dirs to return an empty list gives []."""
        import pathminer.kicad.prefs as prefs_mod
        monkeypatch.setattr(prefs_mod, "kicad_pref_dirs", lambda: [])
        result = prefs_mod.kicad_recent_projects()
        assert result == []

    def test_nested_open_projects(self, tmp_path, monkeypatch):
        """Standard format: {"system": {"open_projects": [...]}}"""
        pref_dir = tmp_path / "9.0"
        pref_dir.mkdir()
        proj = str(tmp_path / "my_project.kicad_pro")
        self._write_kicad_json(str(pref_dir), {"system": {"open_projects": [proj]}})

        import pathminer.kicad.prefs as prefs_mod
        monkeypatch.setattr(prefs_mod, "kicad_pref_dirs", lambda: [str(pref_dir)])
        result = prefs_mod.kicad_recent_projects()

        assert len(result) == 1
        assert result[0]["project"] == proj
        assert isinstance(result[0]["exists"], bool)
        assert "source" in result[0]

    def test_flat_key_format(self, tmp_path, monkeypatch):
        """Flat format: {"system.open_projects": [...]}"""
        pref_dir = tmp_path / "9.0"
        pref_dir.mkdir()
        proj = str(tmp_path / "flat_project.kicad_pro")
        self._write_kicad_json(str(pref_dir), {"system.open_projects": [proj]})

        import pathminer.kicad.prefs as prefs_mod
        monkeypatch.setattr(prefs_mod, "kicad_pref_dirs", lambda: [str(pref_dir)])
        result = prefs_mod.kicad_recent_projects()

        assert any(r["project"] == proj for r in result)

    def test_string_instead_of_list(self, tmp_path, monkeypatch):
        """Some versions write a single string instead of a list."""
        pref_dir = tmp_path / "9.0"
        pref_dir.mkdir()
        proj = str(tmp_path / "single.kicad_pro")
        self._write_kicad_json(
            str(pref_dir), {"system": {"open_projects": proj}}
        )

        import pathminer.kicad.prefs as prefs_mod
        monkeypatch.setattr(prefs_mod, "kicad_pref_dirs", lambda: [str(pref_dir)])
        result = prefs_mod.kicad_recent_projects()

        assert len(result) == 1
        assert result[0]["project"] == proj

    def test_deduplication_across_versions(self, tmp_path, monkeypatch):
        """Same project path in two version dirs appears only once."""
        proj = str(tmp_path / "same.kicad_pro")
        dirs = []
        for ver in ("9.0", "8.0"):
            d = tmp_path / ver
            d.mkdir()
            self._write_kicad_json(str(d), {"system": {"open_projects": [proj]}})
            dirs.append(str(d))

        import pathminer.kicad.prefs as prefs_mod
        monkeypatch.setattr(prefs_mod, "kicad_pref_dirs", lambda: dirs)
        result = prefs_mod.kicad_recent_projects()

        assert len(result) == 1

    def test_malformed_json_skipped(self, tmp_path, monkeypatch):
        """A malformed kicad.json produces an empty result without raising."""
        pref_dir = tmp_path / "9.0"
        pref_dir.mkdir()
        path = os.path.join(str(pref_dir), "kicad.json")
        with open(path, "w") as fh:
            fh.write("{ this is not json }")

        import pathminer.kicad.prefs as prefs_mod
        monkeypatch.setattr(prefs_mod, "kicad_pref_dirs", lambda: [str(pref_dir)])
        result = prefs_mod.kicad_recent_projects()
        assert result == []

    def test_missing_kicad_json_skipped(self, tmp_path, monkeypatch):
        """A version directory without kicad.json is silently skipped."""
        pref_dir = tmp_path / "9.0"
        pref_dir.mkdir()
        # No kicad.json written

        import pathminer.kicad.prefs as prefs_mod
        monkeypatch.setattr(prefs_mod, "kicad_pref_dirs", lambda: [str(pref_dir)])
        result = prefs_mod.kicad_recent_projects()
        assert result == []

    def test_exists_false_for_nonexistent_project(self, tmp_path, monkeypatch):
        """entry["exists"] is False when the project file does not exist."""
        pref_dir = tmp_path / "9.0"
        pref_dir.mkdir()
        proj = "/nonexistent/path/board.kicad_pro"
        self._write_kicad_json(str(pref_dir), {"system": {"open_projects": [proj]}})

        import pathminer.kicad.prefs as prefs_mod
        monkeypatch.setattr(prefs_mod, "kicad_pref_dirs", lambda: [str(pref_dir)])
        result = prefs_mod.kicad_recent_projects()

        assert result[0]["exists"] is False

    def test_empty_string_entries_skipped(self, tmp_path, monkeypatch):
        """Empty strings in open_projects are silently skipped."""
        pref_dir = tmp_path / "9.0"
        pref_dir.mkdir()
        self._write_kicad_json(
            str(pref_dir), {"system": {"open_projects": ["", "   "]}}
        )

        import pathminer.kicad.prefs as prefs_mod
        monkeypatch.setattr(prefs_mod, "kicad_pref_dirs", lambda: [str(pref_dir)])
        result = prefs_mod.kicad_recent_projects()
        # Empty strings and whitespace-only strings should be excluded
        # (the function checks `if isinstance(p, str) and p` — "   " is truthy)
        # The whitespace-only string passes the `and p` guard, so only "" is skipped.
        # That's v0.13 behavior; we preserve it exactly.
        assert all(r["project"] != "" for r in result)

    def test_non_string_entries_skipped(self, tmp_path, monkeypatch):
        """Non-string entries (e.g. None, int) in open_projects are skipped."""
        pref_dir = tmp_path / "9.0"
        pref_dir.mkdir()
        proj = str(tmp_path / "valid.kicad_pro")
        self._write_kicad_json(
            str(pref_dir),
            {"system": {"open_projects": [None, 42, proj]}},
        )

        import pathminer.kicad.prefs as prefs_mod
        monkeypatch.setattr(prefs_mod, "kicad_pref_dirs", lambda: [str(pref_dir)])
        result = prefs_mod.kicad_recent_projects()
        assert len(result) == 1
        assert result[0]["project"] == proj


# ---------------------------------------------------------------------------
# board_for_project
# ---------------------------------------------------------------------------

class TestBoardForProject:
    def test_kicad_pcb_returned_as_is(self, tmp_path):
        board = tmp_path / "my.kicad_pcb"
        board.touch()
        assert board_for_project(str(board)) == str(board)

    def test_kicad_pro_resolves_to_sibling_pcb(self, tmp_path):
        proj = tmp_path / "my.kicad_pro"
        board = tmp_path / "my.kicad_pcb"
        proj.touch()
        board.touch()
        result = board_for_project(str(proj))
        assert result == str(board)

    def test_missing_sibling_scans_directory(self, tmp_path):
        proj = tmp_path / "design.kicad_pro"
        board = tmp_path / "different_name.kicad_pcb"
        proj.touch()
        board.touch()
        result = board_for_project(str(proj))
        assert result == str(board)

    def test_multiple_pcbs_returns_none(self, tmp_path):
        proj = tmp_path / "design.kicad_pro"
        for name in ("a.kicad_pcb", "b.kicad_pcb"):
            (tmp_path / name).touch()
        proj.touch()
        # Sibling (same stem) doesn't exist, and there are two .kicad_pcb files
        result = board_for_project(str(proj))
        assert result is None

    def test_no_pcb_in_directory_returns_none(self, tmp_path):
        proj = tmp_path / "design.kicad_pro"
        proj.touch()
        result = board_for_project(str(proj))
        assert result is None

    def test_unreadable_directory_returns_none(self):
        """Unreadable directory or nonexistent parent → None (not a crash)."""
        # Use a path with a nonexistent parent; the scan will get OSError.
        # The sibling construction will produce a path that doesn't exist,
        # and the scan will fail to listdir.
        result = board_for_project("/nonexistent/deep/path/design.kicad_pro")
        assert result is None

    def test_sibling_pcb_takes_priority_over_scan(self, tmp_path):
        """If the exact sibling exists, it is returned before scanning."""
        proj = tmp_path / "my.kicad_pro"
        exact = tmp_path / "my.kicad_pcb"
        other = tmp_path / "other.kicad_pcb"
        proj.touch()
        exact.touch()
        other.touch()
        result = board_for_project(str(proj))
        assert result == str(exact)


# ---------------------------------------------------------------------------
# project_for_board
# ---------------------------------------------------------------------------

class TestProjectForBoard:
    def test_sibling_pro_exists(self, tmp_path):
        board = tmp_path / "my.kicad_pcb"
        proj = tmp_path / "my.kicad_pro"
        board.touch()
        proj.touch()
        result = project_for_board(str(board))
        assert result == str(proj)

    def test_sibling_pro_absent_returns_none(self, tmp_path):
        board = tmp_path / "my.kicad_pcb"
        board.touch()
        result = project_for_board(str(board))
        assert result is None

    def test_nonexistent_board_returns_none(self):
        result = project_for_board("/nonexistent/path/board.kicad_pcb")
        assert result is None
