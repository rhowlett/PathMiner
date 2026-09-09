# v0.1
"""pathminer.kicad.prefs — KiCad application preferences discovery.

Extracted from tools/pcb_trace_resistance.py v0.13.

Locates KiCad's per-user configuration directories and reads recently opened
projects from ``kicad.json``.  Does not import Qt, wx, or pathminer.core.

Purpose
-------
- Pre-fill the Open dialog with the last project KiCad had open.
- Resolve a project path to its board file and vice versa.

These are read-only helpers; they never open a file without user action, and
they never write to the KiCad settings directory.

Public surface
--------------
KICAD_VERSIONS : tuple[str, ...]
    Supported KiCad major.minor version strings, newest first.
kicad_pref_dirs() -> list[str]
    Return existing KiCad preference directories, newest version first.
kicad_recent_projects() -> list[dict]
    Return recently opened projects from ``kicad.json``.
board_for_project(project_path) -> str | None
    Given a ``.kicad_pro`` path, return the sibling ``.kicad_pcb`` path.
project_for_board(board_path) -> str | None
    Given a ``.kicad_pcb`` path, return the sibling ``.kicad_pro`` path if
    it exists.

Behaviour notes
---------------
``kicad_recent_projects`` is tolerant of:
- Missing or unreadable ``kicad.json``.
- Malformed JSON (returns empty list).
- Both ``system.open_projects`` (nested dict) and the flat
  ``"system.open_projects"`` key written by some KiCad versions.
- A single string instead of a list under ``open_projects``.
"""

from __future__ import annotations

import json
import os
import sys

# KiCad version strings to probe, newest first.
KICAD_VERSIONS: tuple[str, ...] = ("9.0", "8.0", "7.0")


def kicad_pref_dirs() -> list[str]:
    """Return existing KiCad preference directories, newest version first.

    Checks the platform-appropriate configuration root(s) and returns all
    directories that actually exist on disk.  An empty list is returned when
    KiCad is not installed or its configuration has not been written yet.

    Platform roots:
    - macOS:   ``~/Library/Preferences/kicad``
    - Windows: ``%APPDATA%\\kicad``, ``%LOCALAPPDATA%\\kicad``
    - Linux:   ``$XDG_CONFIG_HOME/kicad`` (or ``~/.config/kicad``)
    """
    home = os.path.expanduser("~")
    if sys.platform == "darwin":
        roots = [os.path.join(home, "Library", "Preferences", "kicad")]
    elif os.name == "nt":
        roots = [
            os.path.join(os.environ.get("APPDATA", ""), "kicad"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "kicad"),
        ]
    else:
        roots = [
            os.path.join(
                os.environ.get("XDG_CONFIG_HOME", os.path.join(home, ".config")),
                "kicad",
            )
        ]

    out: list[str] = []
    for root in roots:
        if not root:
            continue
        for ver in KICAD_VERSIONS:
            d = os.path.join(root, ver)
            if os.path.isdir(d):
                out.append(d)
    return out


def kicad_recent_projects() -> list[dict]:
    """Return recently opened projects from KiCad's ``kicad.json``.

    Each entry is a dict with keys:

    - ``"project"`` — absolute path to the ``.kicad_pro`` file
    - ``"exists"``  — True when the path exists on disk
    - ``"source"``  — absolute path to the ``kicad.json`` that supplied it

    Projects are deduplicated across version directories (first occurrence
    wins).  Used only to pre-fill the Open dialog; never opened without being
    asked by the user.

    Returns an empty list when KiCad is not installed or the file is absent
    or unreadable.
    """
    seen: set[str] = set()
    out: list[dict] = []
    for d in kicad_pref_dirs():
        path = os.path.join(d, "kicad.json")
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, ValueError):
            continue

        system = doc.get("system") or {}
        # KiCad writes either {"system": {"open_projects": [...]}} or the
        # flat key "system.open_projects" at the top level.
        entries = system.get("open_projects") or doc.get("system.open_projects") or []
        if isinstance(entries, str):
            entries = [entries]

        for p in entries:
            if isinstance(p, str) and p and p not in seen:
                seen.add(p)
                out.append(
                    {"project": p, "exists": os.path.exists(p), "source": path}
                )
    return out


def board_for_project(project_path: str) -> str | None:
    """Return the ``.kicad_pcb`` path for the given project file.

    Resolution order:

    1. If *project_path* already ends with ``.kicad_pcb``, return it as-is.
    2. Construct the sibling ``.kicad_pcb`` path by replacing the extension.
       Return it if it exists.
    3. Scan the project's directory for ``.kicad_pcb`` files; return the only
       match when exactly one is found, otherwise return None.

    This defers opening the schematic or netlist to a later user action: the
    project file is the entry point, and the board is its sibling.
    """
    base, ext = os.path.splitext(project_path)
    if ext == ".kicad_pcb":
        return project_path

    cand = base + ".kicad_pcb"
    if os.path.exists(cand):
        return cand

    folder = os.path.dirname(project_path) or "."
    try:
        hits = [
            os.path.join(folder, f)
            for f in sorted(os.listdir(folder))
            if f.endswith(".kicad_pcb")
        ]
    except OSError:
        hits = []

    return hits[0] if len(hits) == 1 else None


def project_for_board(board_path: str) -> str | None:
    """Return the sibling ``.kicad_pro`` path if it exists, else None.

    Parameters
    ----------
    board_path:
        Path to a ``.kicad_pcb`` file.
    """
    base, _ext = os.path.splitext(board_path)
    cand = base + ".kicad_pro"
    return cand if os.path.exists(cand) else None
