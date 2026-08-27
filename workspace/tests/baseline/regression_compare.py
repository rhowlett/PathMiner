#!/usr/bin/env python3
"""
PathMiner v0.13 Baseline Regression Comparator
Session 01 — QA-004 contribution

Runs selftest suites and the IP5385 report, normalizes the output, and
compares it against the golden fixture file captured at baseline freeze.

Usage:
    python3 tests/baseline/regression_compare.py headless
    python3 tests/baseline/regression_compare.py powerbank
    python3 tests/baseline/regression_compare.py report
    python3 tests/baseline/regression_compare.py all

Exit codes:
    0  — all vectors / pairs match golden fixture
    1  — one or more values differ from golden fixture
    2  — usage or I/O error

Normalization applied (must match golden_fixtures_notes.md rules):
    selftest:  absolute paths replaced with <normalized_path>; runtime fields excluded
    report:    generated timestamp and solve_seconds excluded; resistance values kept
"""

import json
import math
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
NETSEL_PACK = (
    WORKSPACE
    / "ai_reference/kicad_project_example/net_selection_PACK.json"
)

SUITES = {
    "headless": {
        "kind": "selftest",
        "command": [sys.executable, str(TOOL), "--selftest"],
        "fixture": FIXTURES_DIR / "headless_118_selftest.json",
        "expected_total": 118,
        "board_required": False,
    },
    "powerbank": {
        "kind": "selftest",
        "command": [sys.executable, str(TOOL), "--selftest", str(BOARD_PB)],
        "fixture": FIXTURES_DIR / "powerbank_284_selftest.json",
        "expected_total": 284,
        "board_required": True,
    },
    "report": {
        "kind": "report",
        "command": [
            sys.executable, str(TOOL),
            "--report", str(BOARD_PB),
            "--nets",   str(NETSEL_PACK),
            "--format", "json",
        ],
        "fixture": FIXTURES_DIR / "ip5385_pack_report.json",
        "expected_nets": 1,
        "expected_pairs": 11,
        "board_required": True,
    },
}

_PASS_FAIL = re.compile(
    r"\s+\[(PASS|FAIL)\]\s+(.+?)\s{2,}got\s+(.*?)\s{2,}want\s+(.*?)\s*$"
)

# V18 "reopen restores height" reports a pixel count that varies by platform
# DPI and font metrics.  The selftest already verifies got == want at runtime
# (PASS means they matched); we store a sentinel in the fixture so the
# comparator does not reject valid runs on different-DPI systems.
PLATFORM_DEPENDENT_SENTINEL = "<platform_dependent>"
_PLATFORM_DEPENDENT_DESCRIPTIONS = {
    "V18 reopen restores height",
}

# Tolerance for floating-point resistance comparison (relative).
# 1e-9 matches the tool's own network-vs-path tolerance; we use 1e-6
# to allow for minor platform floating-point ordering differences.
FLOAT_TOL = 1e-6


def normalize_path(s: str) -> str:
    """Replace volatile filesystem paths with a stable sentinel.

    Handles:
      /Users/<user>/...        macOS home-directory paths
      /var/folders/<x>/...     macOS temp (mkdtemp) paths
      /tmp/...                 Linux temp paths
      /home/<user>/...         Linux home-directory paths
    """
    s = re.sub(r"/Users/[^/\s]+/\S+", "<normalized_path>", s)
    s = re.sub(r"/var/folders/\S+", "<normalized_path>", s)
    s = re.sub(r"/tmp/\S+", "<normalized_path>", s)
    s = re.sub(r"/home/[^/\s]+/\S+", "<normalized_path>", s)
    return s


def normalize_vector(status: str, desc: str, got: str, want: str) -> dict:
    """Build a selftest vector record with appropriate normalization applied."""
    desc = desc.strip()
    got = normalize_path(got.strip())
    want = normalize_path(want.strip())
    # Platform-dependent values: store sentinel; comparator checks status only
    if desc in _PLATFORM_DEPENDENT_DESCRIPTIONS:
        got = PLATFORM_DEPENDENT_SENTINEL
        want = PLATFORM_DEPENDENT_SENTINEL
    return {"status": status, "description": desc, "got": got, "want": want}


def parse_selftest_output(text: str) -> list[dict]:
    vectors = []
    for line in text.splitlines():
        m = _PASS_FAIL.match(line)
        if m:
            status, desc, got, want = m.groups()
            vectors.append(normalize_vector(status, desc, got, want))
    return vectors


def normalize_pair(p: dict) -> dict:
    """Strip volatile fields from a report pair."""
    return {k: v for k, v in p.items() if k != "solve_seconds"}


def floats_close(a, b, tol=FLOAT_TOL) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    try:
        fa, fb = float(a), float(b)
    except (TypeError, ValueError):
        return a == b
    if fa == fb:
        return True
    denom = max(abs(fa), abs(fb), 1e-30)
    return abs(fa - fb) / denom <= tol


FLOAT_PAIR_KEYS = {
    "path_ohms", "network_ohms", "hot_ohms",
    "drop_v", "power_w", "parallel_gain_pct",
    "voltage_in_v", "voltage_out_v",
}

# Notes contain the first-discovered branch location, which varies with
# hash-map iteration order.  Normalize to the structural pattern only:
#   "branch at <location> (and N more): <message>"
#   → "branch (and N more): <message>"
_NOTE_BRANCH = re.compile(
    r"^(branch at .+?) (\(and \d+ more\)): (.+)$"
)
_NOTE_BRANCH_SOLO = re.compile(
    r"^(branch at .+?): (.+)$"
)


def normalize_note(n: str) -> str:
    m = _NOTE_BRANCH.match(n)
    if m:
        return f"branch {m.group(2)}: {m.group(3)}"
    m = _NOTE_BRANCH_SOLO.match(n)
    if m:
        return f"branch: {m.group(2)}"
    return n


def normalize_notes(notes) -> list:
    if notes is None:
        return []
    return [normalize_note(str(n)) for n in notes]


def diff_pair(live: dict, gold: dict) -> list[str]:
    diffs = []
    all_keys = set(live) | set(gold)
    for k in sorted(all_keys):
        lv, gv = live.get(k), gold.get(k)
        if k in FLOAT_PAIR_KEYS:
            if not floats_close(lv, gv):
                diffs.append(f"    {k}: live={lv} golden={gv} (rel diff > {FLOAT_TOL})")
        elif k == "notes":
            ln_norm = normalize_notes(lv)
            gn_norm = normalize_notes(gv)
            if ln_norm != gn_norm:
                diffs.append(f"    notes (normalized): live={ln_norm!r} golden={gn_norm!r}")
        else:
            if lv != gv:
                diffs.append(f"    {k}: live={lv!r} golden={gv!r}")
    return diffs


# ---- selftest runner --------------------------------------------------------

def run_selftest_suite(name: str, suite: dict) -> int:
    fixture_path = suite["fixture"]

    if suite["board_required"] and not BOARD_PB.exists():
        print(f"BLOCKED: board file not found: {BOARD_PB}")
        return 2

    if not fixture_path.exists():
        print(f"ERROR: golden fixture not found: {fixture_path}")
        return 2

    with open(fixture_path, encoding="utf-8") as fh:
        golden = json.load(fh)

    golden_vectors = golden["selftest_vectors"]
    expected_total = suite["expected_total"]

    print(f"Command: {' '.join(suite['command'])}")
    print(f"Golden:  {fixture_path.name} ({len(golden_vectors)} vectors)")
    print()

    result = subprocess.run(suite["command"], capture_output=True, text=True)
    stdout = result.stdout + result.stderr

    if result.returncode != 0:
        print(f"FAIL  selftest exited non-zero (exit code {result.returncode})")
        print(stdout[-2000:])
        return 1

    summary_m = re.search(r"(\d+)/(\d+) checks passed", stdout)
    if not summary_m:
        print("FAIL  could not find summary line in selftest output")
        return 1

    passed_count = int(summary_m.group(1))
    total_count = int(summary_m.group(2))

    if total_count != expected_total:
        print(f"FAIL  vector count: got {total_count}, expected {expected_total}")
        return 1

    if passed_count != total_count:
        print(f"FAIL  {total_count - passed_count} vectors did not PASS in live run")
        return 1

    live_vectors = parse_selftest_output(stdout)
    if len(live_vectors) != len(golden_vectors):
        print(f"FAIL  parsed count mismatch: live={len(live_vectors)}, golden={len(golden_vectors)}")
        return 1

    failures = []
    for i, (live, gold) in enumerate(zip(live_vectors, golden_vectors)):
        diffs = []
        for k in ("status", "description", "got", "want"):
            lv, gv = live.get(k), gold.get(k)
            # Platform-dependent: fixture stores sentinel; only check status
            if gv == PLATFORM_DEPENDENT_SENTINEL:
                continue
            if lv != gv:
                diffs.append(f"    {k}: live={lv!r} golden={gv!r}")
        if diffs:
            failures.append((i + 1, live.get("description", "?"), diffs))

    if failures:
        print(f"FAIL  {len(failures)} vector(s) differ from golden fixture:")
        for idx, desc, diffs in failures:
            print(f"  [{idx}] {desc}")
            for d in diffs:
                print(d)
        return 1

    meta = golden.get("_fixture_meta", {})
    print(f"PASS  {passed_count}/{total_count} vectors match golden fixture exactly")
    print(f"      Board SHA-256: {meta.get('source_board_sha256', 'N/A')} (baseline)")
    return 0


# ---- report runner ----------------------------------------------------------

def run_report_suite(name: str, suite: dict) -> int:
    fixture_path = suite["fixture"]

    if not BOARD_PB.exists():
        print(f"BLOCKED: board file not found: {BOARD_PB}")
        return 2
    if not NETSEL_PACK.exists():
        print(f"BLOCKED: net selection file not found: {NETSEL_PACK}")
        return 2

    if not fixture_path.exists():
        print(f"ERROR: golden fixture not found: {fixture_path}")
        return 2

    with open(fixture_path, encoding="utf-8") as fh:
        golden = json.load(fh)

    g_report = golden["report"]
    g_nets = g_report["nets"]
    expected_pairs = suite["expected_pairs"]

    print(f"Command: {' '.join(str(x) for x in suite['command'])}")
    print(f"Golden:  {fixture_path.name} "
          f"({suite['expected_nets']} net, {expected_pairs} pairs)")
    print()

    result = subprocess.run(suite["command"], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"FAIL  report exited non-zero (exit code {result.returncode})")
        print(result.stderr[-2000:])
        return 1

    try:
        live_report = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print(f"FAIL  could not parse report JSON: {exc}")
        return 1

    live_nets = live_report.get("nets", [])

    if len(live_nets) != len(g_nets):
        print(f"FAIL  net count: live={len(live_nets)}, golden={len(g_nets)}")
        return 1

    failures = []
    for net_idx, (ln, gn) in enumerate(zip(live_nets, g_nets)):
        if ln["name"] != gn["name"]:
            failures.append((f"net[{net_idx}]", f"name: live={ln['name']!r} golden={gn['name']!r}", []))
            continue
        if len(ln["pairs"]) != len(gn["pairs"]):
            failures.append((ln["name"], f"pair count: live={len(ln['pairs'])} golden={len(gn['pairs'])}", []))
            continue
        for pi, (lp, gp) in enumerate(zip(ln["pairs"], gn["pairs"])):
            live_norm = normalize_pair(lp)
            gold_norm = normalize_pair(gp)
            diffs = diff_pair(live_norm, gold_norm)
            if diffs:
                label = f"{lp.get('from','?')} > {lp.get('to','?')}"
                failures.append((label, f"pair[{pi}]", diffs))

    if failures:
        print(f"FAIL  {len(failures)} pair(s) differ from golden fixture:")
        for label, ctx, diffs in failures:
            print(f"  {label}  ({ctx})")
            for d in diffs:
                print(d)
        return 1

    total_pairs = sum(len(n["pairs"]) for n in live_nets)
    meta = golden.get("_fixture_meta", {})
    print(f"PASS  {len(live_nets)} net(s), {total_pairs} pair(s) match golden fixture "
          f"(tol={FLOAT_TOL:.0e})")
    print(f"      Board SHA-256:  {meta.get('source_board_sha256', 'N/A')} (baseline)")
    print(f"      Netsel SHA-256: {meta.get('net_selection_sha256', 'N/A')} (baseline)")
    return 0


# ---- dispatch ---------------------------------------------------------------

def run_suite(name: str) -> int:
    suite = SUITES[name]
    print(f"=== Regression compare: {name} ===")
    if suite["kind"] == "selftest":
        return run_selftest_suite(name, suite)
    elif suite["kind"] == "report":
        return run_report_suite(name, suite)
    else:
        print(f"ERROR: unknown suite kind '{suite['kind']}'")
        return 2


def main() -> int:
    valid = list(SUITES) + ["all"]
    if len(sys.argv) < 2 or sys.argv[1] not in valid:
        print(f"Usage: {sys.argv[0]} {'|'.join(valid)}")
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
