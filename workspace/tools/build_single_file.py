#!/usr/bin/env python3
# v0.2
"""tools/build_single_file.py — generate the single-file PathMiner distribution.

Session 08 (BASE-004: "preserve a generated single-file distribution. Add
tools/build_single_file.py after the package split. Done when: the generated
file passes the same aggregate self-test as the package.").

``tools/pcb_trace_resistance.py`` is now the legacy *compatibility facade*:
it delegates its numerical solver dispatcher and pure planar-geometry
helpers to the extracted ``pathminer.core`` package (Sessions 03/04/07)
instead of keeping duplicate copies (see that file's own module docstring
and v0.14 change-log entry, and ARCH-006/ARCH-010). That is the right shape
for development — one source of truth for the physics — but it means the
facade alone can no longer be copied as a single file and run without the
rest of the ``pathminer`` package importable on ``sys.path``.

This script restores v0.13's single-file distribution model (project
specification S17, "Preserve single-file generated build") without
reintroducing the duplicated source it replaced: it takes the facade's own
source unchanged, finds the ``pathminer.core`` bootstrap block by its
sentinel comments, and replaces *only* that block with the inlined source of
``pathminer/core/geometry.py`` and ``pathminer/core/solver.py`` — each
executed into its own throwaway module object bound to the same
``_pm_geometry`` / ``_pm_solver`` names the facade already calls — so the
generated file has no import-time dependency on the ``pathminer`` package at
all. Every other line of the facade is carried through byte-for-byte.

Generated files are never hand-edited (project convention); regenerate them
from this script instead.

Usage:
    python3 tools/build_single_file.py               # write dist/pcb_trace_resistance_single_file.py
    python3 tools/build_single_file.py -o PATH        # write to a chosen path
    python3 tools/build_single_file.py --check        # generated-file parity (BASE-004)
    python3 tools/build_single_file.py --check --board BOARD.kicad_pcb

--check generates the file to a temporary path and runs ``--selftest`` on it
and on the split facade, each in its own subprocess. Each side must, on its
own, exit 0, print a parseable "N/N checks passed" summary, and have every
vector PASS — "the generated file passes the same aggregate self-test" means
both actually pass, not merely that they fail identically to each other — and
only then are the two runs' named vectors (``[PASS]/[FAIL] <name>``) and
totals compared for an exact match. Raw ``got``/``want`` text is not compared
byte-for-byte because a few vectors (V19, V23) legitimately print a fresh
temp-directory path on every run; the pass/fail identity per named vector is
what "the same aggregate self-test" means, and it is what
``tests/baseline/regression_compare.py`` also checks against the frozen
golden fixtures.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FACADE_PATH = REPO_ROOT / "tools" / "pcb_trace_resistance.py"
GEOMETRY_PATH = REPO_ROOT / "pathminer" / "core" / "geometry.py"
SOLVER_PATH = REPO_ROOT / "pathminer" / "core" / "solver.py"
DEFAULT_OUTPUT = REPO_ROOT / "dist" / "pcb_trace_resistance_single_file.py"

BOOTSTRAP_BEGIN = "# === PATHMINER_CORE_BOOTSTRAP_BEGIN ==="
BOOTSTRAP_END = "# === PATHMINER_CORE_BOOTSTRAP_END ==="

# Matches a selftest report line: "  [PASS] <name>  got <g>  want <w>".
# The name is left-padded with spaces to a run-dependent column width, so we
# only anchor on the two-or-more spaces before the literal "got".
_REPORT_LINE = re.compile(r"^\s*\[(PASS|FAIL)\]\s+(.*?)\s{2,}got\b")
_SUMMARY_LINE = re.compile(r"^(\d+)/(\d+) checks passed\s*$")


def _inline_module(module_name: str, source_path: Path, module_var: str) -> str:
    """Render source that builds a throwaway module object named *module_var*
    from *source_path*, so the facade's existing ``_pm_geometry.foo`` /
    ``_pm_solver.foo`` call sites keep working unchanged against it."""
    source = source_path.read_text(encoding="utf-8")
    # A repo-relative tag, not an absolute machine path (nothing machine- or
    # checkout-specific belongs in a distributable generated file).
    tag = f"<inlined {source_path.relative_to(REPO_ROOT).as_posix()}>"
    return (
        f"{module_var} = _types.ModuleType({module_name!r})\n"
        f"{module_var}.__file__ = {tag!r}\n"
        f"exec(compile({source!r}, {tag!r}, 'exec'), {module_var}.__dict__)\n"
    )


def generate_source() -> str:
    """Return the generated single-file distribution as source text."""
    facade = FACADE_PATH.read_text(encoding="utf-8")
    try:
        pre, rest = facade.split(BOOTSTRAP_BEGIN, 1)
        _, post = rest.split(BOOTSTRAP_END, 1)
    except ValueError as exc:
        raise RuntimeError(
            f"{FACADE_PATH} is missing the pathminer.core bootstrap sentinels "
            f"({BOOTSTRAP_BEGIN!r} / {BOOTSTRAP_END!r}); this generator has "
            "nothing to locate and replace. Do not hand-edit the generated "
            "file; fix the facade's bootstrap block instead."
        ) from exc

    inlined = "\n".join([
        "# --- inlined pathminer.core (generated; do not edit by hand) ---",
        "# BASE-004: this block replaces the pathminer.core bootstrap in",
        "# tools/pcb_trace_resistance.py so the file below has no import-time",
        "# dependency on the pathminer package. Generated by",
        "# tools/build_single_file.py from pathminer/core/geometry.py and",
        "# pathminer/core/solver.py — regenerate with that script rather than",
        "# editing this block.",
        "import types as _types",
        "",
        _inline_module("pathminer.core.geometry", GEOMETRY_PATH, "_pm_geometry"),
        _inline_module("pathminer.core.solver", SOLVER_PATH, "_pm_solver"),
        "# --- end inlined pathminer.core ---",
    ])
    return pre + inlined + post


def write_file(path: Path) -> Path:
    source = generate_source()
    compile(source, str(path), "exec")           # fail fast on a bad generation
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    path.chmod(0o755)
    return path


def _run_selftest(script: Path, board: str | None) -> subprocess.CompletedProcess:
    args = [sys.executable, str(script), "--selftest"]
    if board:
        args.append(board)
    env = dict(os.environ)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    return subprocess.run(args, capture_output=True, text=True, env=env)


def _parse_selftest(stdout: str):
    """Return (ordered [(name, status), ...], (passed, total)) from selftest
    CLI output; deliberately ignores the got/want columns (see module
    docstring: a few vectors print a fresh temp path on every run)."""
    vectors = []
    summary = None
    for line in stdout.splitlines():
        m = _REPORT_LINE.match(line)
        if m:
            vectors.append((m.group(2).strip(), m.group(1)))
            continue
        m = _SUMMARY_LINE.match(line.strip())
        if m:
            summary = (int(m.group(1)), int(m.group(2)))
    return vectors, summary


def _validate_own_selftest(label: str, result: "subprocess.CompletedProcess",
                            vectors, summary) -> list[str]:
    """Return problems (empty if none) with *one side's* own --selftest run.

    "The generated file passes the same aggregate self-test as the package"
    (BASE-004) requires each side to actually pass on its own — exit 0, a
    parseable "N/N checks passed" summary, at least one vector, and every
    vector PASS — before the two sides are even compared against each other.
    Without this, two runs that fail *identically* (e.g. both "0/1 checks
    passed", exit 1) would otherwise agree with each other and be reported
    as a false PASS."""
    problems = []
    if result.returncode != 0:
        problems.append(f"{label}'s own --selftest did not pass (exit code {result.returncode})")
    if summary is None:
        problems.append(f"{label}'s --selftest did not print a parseable "
                         f"'N/N checks passed' summary line")
    elif summary[0] != summary[1]:
        problems.append(f"{label}'s --selftest reported {summary[0]}/{summary[1]} "
                         f"checks passed, not all of them")
    if not vectors:
        problems.append(f"{label}'s --selftest reported no parseable [PASS]/[FAIL] vectors")
    elif any(status != "PASS" for _name, status in vectors):
        failed = [n for n, s in vectors if s != "PASS"]
        problems.append(f"{label}'s --selftest reported {len(failed)} FAIL vector(s), "
                         f"e.g. {failed[:5]!r}")
    return problems


def check(board: str | None) -> int:
    """Generated-file parity (BASE-004): the generated single file's
    ``--selftest`` must itself pass, and report the same named vectors in
    the same pass/fail state, as the split facade's own (also-passing)
    ``--selftest``."""
    with tempfile.TemporaryDirectory(prefix="pathminer_single_file_") as tmp:
        generated_path = write_file(Path(tmp) / "pcb_trace_resistance_single_file.py")
        split = _run_selftest(FACADE_PATH, board)
        single = _run_selftest(generated_path, board)

    split_vectors, split_summary = _parse_selftest(split.stdout)
    single_vectors, single_summary = _parse_selftest(single.stdout)

    problems = _validate_own_selftest("the split facade", split, split_vectors, split_summary)
    problems += _validate_own_selftest("the generated single file", single,
                                       single_vectors, single_summary)

    # Only compare the two runs against each other once each has been
    # confirmed to actually pass on its own; otherwise a missing summary or a
    # shared failure could make the comparisons below misleadingly agree.
    if not problems:
        if split_summary != single_summary:
            problems.append(f"totals differ: split={split_summary} single-file={single_summary}")
        if split_vectors != single_vectors:
            split_map = dict(split_vectors)
            single_map = dict(single_vectors)
            only_split = [n for n in split_map if n not in single_map]
            only_single = [n for n in single_map if n not in split_map]
            differ = [n for n in split_map if n in single_map and split_map[n] != single_map[n]]
            if only_split:
                problems.append(f"{len(only_split)} vector(s) missing from the single file, "
                                 f"e.g. {only_split[:5]!r}")
            if only_single:
                problems.append(f"{len(only_single)} vector(s) only in the single file, "
                                 f"e.g. {only_single[:5]!r}")
            if differ:
                problems.append(f"{len(differ)} vector(s) differ in PASS/FAIL, "
                                 f"e.g. {differ[:5]!r}")
            if not (only_split or only_single or differ):
                problems.append("vector order differs between the two runs")

    if problems:
        print("FAIL: generated single file does not pass the same aggregate "
              "self-test as the package:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    passed, total = split_summary
    print(f"PASS  generated single file agrees with the split package: "
          f"{len(split_vectors)} vectors, {passed}/{total} passed on both "
          f"(exit code {split.returncode})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-o", "--out", type=Path, default=DEFAULT_OUTPUT,
                        help=f"output path (default: {DEFAULT_OUTPUT.relative_to(REPO_ROOT)})")
    parser.add_argument("--check", action="store_true",
                        help="generated-file parity check (BASE-004) instead of writing --out")
    parser.add_argument("--board", default=None,
                        help="optional .kicad_pcb to also exercise board-dependent vectors")
    args = parser.parse_args()

    if args.check:
        return check(args.board)

    path = write_file(args.out)
    print(f"wrote {path.relative_to(REPO_ROOT) if REPO_ROOT in path.parents else path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
