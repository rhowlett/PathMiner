#!/usr/bin/env python3
"""
PathMiner v0.13 Baseline Regression Comparator
Session 01 — QA-004 contribution

Runs a selftest suite, normalizes the output, and compares it against
the golden fixture file captured at baseline freeze.

Usage:
    python3 tests/baseline/regression_compare.py headless
    python3 tests/baseline/regression_compare.py powerbank
    python3 tests/baseline/regression_compare.py all

Exit codes:
    0  — all vectors match golden fixture
    1  — one or more vectors differ from golden fixture
    2  — usage or I/O error

Normalization applied (must match golden_fixtures_notes.md rules):
    - Absolute paths replaced with <normalized_path>
    - Runtime fields excluded from comparison
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
TOOL = WORKSPACE / "tools" / "pcb_trace_resistance.py"
BOARD_PB = (
    WORKSPACE
    / "ai_reference/kicad_project_example/Ref_PowerBank_injoinic_IP5385_v0.8.kicad_pcb"
)

SUITES = {
    "headless": {
        "command": [sys.executable, str(TOOL), "--selftest"],
        "fixture": FIXTURES_DIR / "headless_118_selftest.json",
        "expected_total": 118,
        "board_required": False,
    },
    "powerbank": {
        "command": [sys.executable, str(TOOL), "--selftest", str(BOARD_PB)],
        "fixture": FIXTURES_DIR / "powerbank_284_selftest.json",
        "expected_total": 284,
        "board_required": True,
    },
}

_PASS_FAIL = re.compile(
    r"\s+\[(PASS|FAIL)\]\s+(.+?)\s{2,}got\s+(.*?)\s{2,}want\s+(.*?)\s*$"
)


def normalize_path(s: str) -> str:
    return re.sub(r"/Users/[^/]+/[^\s]+", "<normalized_path>", s)


def parse_output(text: str) -> list[dict]:
    vectors = []
    for line in text.splitlines():
        m = _PASS_FAIL.match(line)
        if m:
            status, desc, got, want = m.groups()
            vectors.append(
                {
                    "status": status,
                    "description": desc.strip(),
                    "got": normalize_path(got.strip()),
                    "want": normalize_path(want.strip()),
                }
            )
    return vectors


def run_suite(name: str) -> int:
    suite = SUITES[name]
    fixture_path = suite["fixture"]

    if suite["board_required"] and not BOARD_PB.exists():
        print(f"BLOCKED: board file not found: {BOARD_PB}")
        print("         Cannot run power-bank suite without the board file.")
        return 2

    if not fixture_path.exists():
        print(f"ERROR: golden fixture not found: {fixture_path}")
        return 2

    with open(fixture_path, encoding="utf-8") as fh:
        golden = json.load(fh)

    golden_vectors = golden["selftest_vectors"]
    expected_total = suite["expected_total"]

    print(f"=== Regression compare: {name} ===")
    print(f"Command: {' '.join(suite['command'])}")
    print(f"Golden fixture: {fixture_path.name} ({len(golden_vectors)} vectors)")
    print()

    result = subprocess.run(
        suite["command"],
        capture_output=True,
        text=True,
    )
    stdout = result.stdout + result.stderr  # selftest writes to stdout only
    live_vectors = parse_output(stdout)

    # Check counts
    if result.returncode != 0:
        print(f"FAIL  selftest exited non-zero (exit code {result.returncode})")
        print(stdout[-2000:])
        return 1

    # Extract summary
    summary_m = re.search(r"(\d+)/(\d+) checks passed", stdout)
    if not summary_m:
        print("FAIL  could not find summary line in selftest output")
        return 1

    passed_count = int(summary_m.group(1))
    total_count = int(summary_m.group(2))

    if total_count != expected_total:
        print(
            f"FAIL  vector count mismatch: got {total_count}, expected {expected_total}"
        )
        return 1

    if passed_count != total_count:
        print(f"FAIL  {total_count - passed_count} vectors did not pass in live run")
        return 1

    # Compare vectors
    if len(live_vectors) != len(golden_vectors):
        print(
            f"FAIL  parsed vector count mismatch: "
            f"live={len(live_vectors)}, golden={len(golden_vectors)}"
        )
        return 1

    failures = []
    for i, (live, gold) in enumerate(zip(live_vectors, golden_vectors)):
        diffs = []
        for key in ("status", "description", "got", "want"):
            if live.get(key) != gold.get(key):
                diffs.append(
                    f"    {key}: live={live.get(key)!r} golden={gold.get(key)!r}"
                )
        if diffs:
            failures.append((i + 1, live.get("description", "?"), diffs))

    if failures:
        print(f"FAIL  {len(failures)} vector(s) differ from golden fixture:")
        for idx, desc, diffs in failures:
            print(f"  [{idx}] {desc}")
            for d in diffs:
                print(d)
        return 1

    print(
        f"PASS  {passed_count}/{total_count} vectors match golden fixture exactly"
    )
    meta = golden.get("_fixture_meta", {})
    print(
        f"      Board SHA-256: {meta.get('source_board_sha256', 'N/A')} (baseline)"
    )
    return 0


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in list(SUITES) + ["all"]:
        print(f"Usage: {sys.argv[0]} headless|powerbank|all")
        return 2

    target = sys.argv[1]
    names = list(SUITES) if target == "all" else [target]

    overall = 0
    for name in names:
        rc = run_suite(name)
        if rc != 0:
            overall = rc
        print()

    if len(names) > 1:
        if overall == 0:
            print("=== All suites PASS ===")
        else:
            print("=== One or more suites FAILED ===")
    return overall


if __name__ == "__main__":
    sys.exit(main())
