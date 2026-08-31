# PathMiner v0.13 Baseline Tests

**Baseline Commit:** fe507fd01017cd0930739cbd8c4cc3f916b47e98
**Test Date:** 2026-08-26
**Python Version:** 3.12.13 [Clang 21.0.0]
**Platform:** macOS-26.6.2-arm64-arm-64bit

---

## Canonical Acceptance Suites

All three suites must pass before a session is eligible for integration.

### 1. Headless Acceptance Tests (118 vectors)

**Location:** Embedded in `tools/pcb_trace_resistance.py --selftest`
**Purpose:** Validate core calculations without GUI or board file
**Status:** 118/118 PASS ✓

**Coverage:**
- V1 (18 tests): Stackup layer parsing and copper weight conversion
- V2 (8 tests): Via barrel resistance across layer pairs
- V3 (3 tests): Via barrel resistance by convention (facing, centre, outer)
- V4 (4 tests): Via hole and finished diameter calculations
- V5 (4 tests): Plating effect on via resistance and board thickness (D8 rule)
- V6 (5 tests): Parallel via arrays with sharing derate
- V7 (2 tests): Via ID limit validation (≥2 µm required)
- V8 (2 tests): Material identity check (resistivity)
- v0.2 regressions (5 tests): Trace resistance, IPC temperature, unit conversion
- V9 (3 tests): Arc length (semicircle, quarter, degenerate chord)
- V11 (7 tests): Network analysis (series, parallel, bridges, stubs)
- V12 (10 tests): JSON schema validation (version, keys, enums, types)
- V21 (4 tests): Point-in-polygon and distance-to-edge
- V23 (6 tests): File path resolution (board/project/preference directories)
- V13 (6 tests): Pour geometry (bounding box, containment, aspect ratio)
- V14 (2 tests): Zone ladder model clustering

**Output Format:**
```
[PASS] <vector_id> <description>                   got <value>  want <expected>
```

**Summary:**
```
118/118 checks passed
```

**Run Command:**
```bash
python3 tools/pcb_trace_resistance.py --selftest
```

**Exit Code:** 0 (success)

**Golden Fixture:** `tests/baseline/fixtures/headless_118_selftest.json`

---

### 2. Real-Board Acceptance Tests (284 vectors)

**Board:** `ai_reference/kicad_project_example/Ref_PowerBank_injoinic_IP5385_v0.8.kicad_pcb`
**Board SHA-256:** `0a1ca4dcfbf8c6609319091f00a515854c3f78e60058272fbd93203d1276a6e9`
**Purpose:** Validate board parsing and routed-copper tracing on a real 4-layer power system PCB
**Status:** 284/284 PASS ✓

**Coverage (sample):**
- V10: Network resistance on 5 pad-pair combinations, segment sums, unreachable pair handling
- V15–V17: Skipped (not the reference test board) — expected
- V18: Collapsible section UI (height stored as `<platform_dependent>` sentinel)
- V19: Board label, JSON default dir
- V20: Skipped (not the reference test board) — expected
- V22: Zone-only pads, ladder vs. mesh comparison on real pour (within 5%), repeated pin collapsing

**Run Command:**
```bash
python3 tools/pcb_trace_resistance.py --selftest \
  ai_reference/kicad_project_example/Ref_PowerBank_injoinic_IP5385_v0.8.kicad_pcb
```

**Exit Code:** 0 (success)
**Measured Runtime:** 27.882 s wall clock (27.10 s user, 0.61 s system, 99% CPU)

**Golden Fixture:** `tests/baseline/fixtures/powerbank_284_selftest.json`

---

### 3. IP5385 Batch Report (1 net, 11 pairs)

**Board:** `ai_reference/kicad_project_example/Ref_PowerBank_injoinic_IP5385_v0.8.kicad_pcb`
**Net Selection:** `ai_reference/kicad_project_example/net_selection_PACK.json`
**Net Selection SHA-256:** `ff8e5ec8f10975670cb65495d2fe5f698ce803e1d7b4f295cfc6686c5aa7d111`
**Purpose:** Validate end-to-end batch report CLI for a real PACK_P power path
**Status:** 1 net, 11 pairs PASS ✓

**Run Command:**
```bash
python3 tools/pcb_trace_resistance.py \
  --report ai_reference/kicad_project_example/Ref_PowerBank_injoinic_IP5385_v0.8.kicad_pcb \
  --nets   ai_reference/kicad_project_example/net_selection_PACK.json \
  --format json
```

**Expected Output Structure:**
- 1 net: `/Reference Design/PACK_P`
- 11 pad pairs sourced from JP1.B
- JSON output indented 2-space; resistance values frozen in golden fixture
- Exit code 0

**Measured Runtime:** 9.512 s wall clock

**Golden Fixture:** `tests/baseline/fixtures/ip5385_pack_report.json`

---

## Executable Regression Comparator

The comparator runs all three suites and diffs live output against golden fixtures:

```bash
# Run all three suites
python3 tests/baseline/regression_compare.py all

# Run individual suite
python3 tests/baseline/regression_compare.py headless
python3 tests/baseline/regression_compare.py powerbank
python3 tests/baseline/regression_compare.py report
```

**Exit Codes:**
- 0 — all vectors / pairs match golden fixture
- 1 — one or more values differ from golden fixture
- 2 — usage or I/O error

**Normalization applied:**
- Selftest: absolute paths replaced with `<normalized_path>` (macOS home, macOS temp, Linux temp, Linux home)
- V18 "reopen restores height": stored as `<platform_dependent>` sentinel; comparator verifies only status=PASS
- Report: generated timestamp and solve_seconds excluded; resistance values kept; notes branch-location stripped (hash-map order volatile)

---

## Test Execution (Complete Suite)

```bash
# Quick headless sanity check
python3 tools/pcb_trace_resistance.py --selftest

# Full canonical suite
python3 tests/baseline/regression_compare.py all
```

---

## Performance Baseline

| Suite | Wall Clock | User | System | CPU |
|-------|------------|------|--------|-----|
| Headless selftest (118 vectors) | 0.220 s | 0.12 s | 0.03 s | 67% |
| Real-board selftest (284 vectors) | 27.882 s | 27.10 s | 0.61 s | 99% |
| IP5385 batch report (1 net, 11 pairs) | 9.512 s | — | — | — |

**Regression threshold:** +20% wall-clock increase flags a potential regression.

Full details in `tests/baseline/PERFORMANCE_BASELINE_v0.13.txt`.

---

## Regression Test Integration

### GitHub Actions / CI

When automated CI is configured, the test suite should:
1. Run `--selftest` in headless mode (118/118 target)
2. Run `regression_compare.py all` against golden fixtures
3. Reject PRs that break any acceptance vector or exceed performance threshold

### Local Pre-commit Hook

Developers should run before committing:
```bash
python3 tests/baseline/regression_compare.py all && echo "✓ Baseline tests pass"
```

---

## Known Limitations

- **GUI tests:** None automated in v0.13 (manual QA via application use)
- **Platform variation:** V18 pixel height is DPI-dependent; stored as sentinel in fixtures
- **Performance variance:** Timing tests vary by system load and scipy availability
- **SciPy not installed on baseline system:** Power-bank suite uses pure-Python solver (27.9 s)

---

## Adding New Tests

When refactoring:
1. **Do not delete v0.13 vectors.** Add new vectors with distinct IDs (e.g., V25, V26).
2. **Preserve vector IDs.** If a vector is replaced, document the old ID in the v0.13 section.
3. **Maintain expected values.** Update expected values only with explicit authorization.
4. **Expand coverage incrementally.** Each session may add new tests for new functionality.

---

## Test Data Files

- `schema/pcb_net_selection.schema.json` — Net selection JSON schema (immutable)
- `ai_reference/kicad_project_example/Ref_PowerBank_injoinic_IP5385_v0.8.kicad_pcb` — Real board (in repo)
- `ai_reference/kicad_project_example/net_selection_PACK.json` — Real board net selection (in repo)
- `tests/baseline/fixtures/headless_118_selftest.json` — Golden fixture, 118 normalized vectors
- `tests/baseline/fixtures/powerbank_284_selftest.json` — Golden fixture, 284 normalized vectors
- `tests/baseline/fixtures/ip5385_pack_report.json` — Golden fixture, 1 net / 11 pairs

---

## Revision History

| Date | Event | Details |
|------|-------|---------|
| 2026-08-26 | Session 01 | Baseline test suite established; 118/118 headless verified; 284/284 powerbank verified; IP5385 report suite established |
| 2026-08-26 | Coordinator repair | Removed obsolete reference-board section (254/254); added IP5385 report suite; updated comparator for path normalization and platform-dependent sentinel |

---

**Test framework created by:** Session 01 (claude-sonnet-4-6, authorized substitution for Haiku-4.5)
**Status:** All three canonical suites PASS
