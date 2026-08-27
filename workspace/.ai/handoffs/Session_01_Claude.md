# Session 01 — Baseline Freeze and Compatibility Inventory [READY_FOR_REVIEW]

**Status:** READY_FOR_REVIEW
**AI:** Claude
**Model:** claude-sonnet-4-6 (authorized substitution; prompt specified Haiku-4.5 / claude-haiku-4-5-20251001)
**Effort Level:** Medium
**Date:** 2026-08-26 (coordinator repair completed 2026-08-27)
**Final Commit:** 92baa47

---

## Executive Summary

Session 01 establishes PathMiner v0.13 baseline with documented compatibility requirements,
actual golden regression fixtures with executable comparator, measured performance baseline,
and architecture decision record. All three canonical acceptance suites pass:

- **118/118 headless selftest** ✓ (0.220 s wall clock)
- **284/284 IP5385 real-board selftest** ✓ (27.882 s wall clock)
- **1 net, 11 pairs IP5385 batch report** ✓ (9.512 s wall clock)

All obsolete 254/254 and 656/656 references have been removed from all planning, manifest,
baseline, ADR, test, and handoff artifacts. KiCad project files are committed to the repo
so tests are fully self-contained.

**Closure Status:**
- BASE-001 (Freeze baseline): `closed` — 118/118 ✓  284/284 ✓  1 net/11 pairs ✓
- BASE-002 (Compatibility inventory): `closed` — corrected against v0.13 source; all errors resolved
- QA-004 (Regression fixtures): `open` — all three suites have fixtures + executable comparator; CI automation deferred
- QA-006 (Performance budgets): `open` — measured baselines recorded; CI enforcement deferred

---

## Authorized Model Substitution

The assigned prompt (`Session_01_Claude_Haiku-4.5_medium.md`) specified model
`claude-haiku-4-5-20251001`. The actual running model is `claude-sonnet-4-6`.
This substitution is authorized by the user and recorded here per the coordinator's
requirement. All output was produced by claude-sonnet-4-6.

---

## Session Context

### Baseline Commit
```
fe507fd01017cd0930739cbd8c4cc3f916b47e98
fix: preserve virtual environment in AI launchers
```

### No Prerequisites
This session (W0) has no dependencies on prior work.

### Scope Compliance
All work remains within owned write scope:
- ✓ `baseline/` — freeze identifier and documentation
- ✓ `tests/baseline/` — test framework, golden fixtures, comparator, performance baseline
- ✓ `documents/compatibility_inventory.md` — created and corrected against v0.13 source
- ✓ `documents/adr/ADR-001.md` — architecture decision record
- ✓ `ai_reference/kicad_project_example/` — KiCad project files committed (coordinator directed)
- ✓ No modifications to v0.13 tool itself (frozen)
- ✓ No changes to shared APIs, schemas, or registries
- ✓ `__MACOSX/` metadata not committed
- ✓ `SESSION_01_SUMMARY.md` not committed (not in owned scope)

---

## Detailed Test Results

### Test 1: Headless Selftest (118/118 vectors)

**Command:**
```bash
python3 tools/pcb_trace_resistance.py --selftest
```

**Exit Code:** 0

**Result:**
```
118/118 checks passed
```

**Measured Runtime:**
```
0.12s user  0.03s system  67% cpu  0.220 total
```

**Status:** ✓ PASS

**Golden Fixture:** `tests/baseline/fixtures/headless_118_selftest.json`
- 118 normalized vectors
- 4 vectors with `<normalized_path>` (V23 temp dir paths)
- 0 platform_dependent entries

---

### Test 2: Real-Board Selftest (284/284 power-bank board)

**Board File:**
```
ai_reference/kicad_project_example/Ref_PowerBank_injoinic_IP5385_v0.8.kicad_pcb
SHA-256: 0a1ca4dcfbf8c6609319091f00a515854c3f78e60058272fbd93203d1276a6e9
```

**Command:**
```bash
python3 tools/pcb_trace_resistance.py --selftest \
  ai_reference/kicad_project_example/Ref_PowerBank_injoinic_IP5385_v0.8.kicad_pcb
```

**Exit Code:** 0

**Result:**
```
284/284 checks passed
```

**Measured Runtime:**
```
27.10s user  0.61s system  99% cpu  27.882 total
```

**Status:** ✓ PASS

**Golden Fixture:** `tests/baseline/fixtures/powerbank_284_selftest.json`
- 284 normalized vectors
- 5 vectors with `<normalized_path>` (V19 + V23 paths)
- 1 platform_dependent: "V18 reopen restores height" → `<platform_dependent>` sentinel
  (pixel count varies by DPI; comparator verifies only status=PASS)

---

### Test 3: IP5385 Batch Report (1 net, 11 pairs)

**Board File:**
```
ai_reference/kicad_project_example/Ref_PowerBank_injoinic_IP5385_v0.8.kicad_pcb
Board SHA-256:  0a1ca4dcfbf8c6609319091f00a515854c3f78e60058272fbd93203d1276a6e9
Net Selection:  ai_reference/kicad_project_example/net_selection_PACK.json
Netsel SHA-256: ff8e5ec8f10975670cb65495d2fe5f698ce803e1d7b4f295cfc6686c5aa7d111
```

**Command:**
```bash
python3 tools/pcb_trace_resistance.py \
  --report ai_reference/kicad_project_example/Ref_PowerBank_injoinic_IP5385_v0.8.kicad_pcb \
  --nets   ai_reference/kicad_project_example/net_selection_PACK.json \
  --format json
```

**Exit Code:** 0

**Result:** 1 net (`/Reference Design/PACK_P`), 11 pad pairs from JP1.B

**Measured Runtime:** ~9.512 s wall clock

**Status:** ✓ PASS

**Golden Fixture:** `tests/baseline/fixtures/ip5385_pack_report.json`
- Timestamp and solve_seconds excluded from comparison
- Resistance values kept (compared with 1e-6 relative tolerance)
- Notes: branch-location stripped, count+message pattern preserved

---

### Test 4: Regression Comparator (all three suites)

**Command:**
```bash
python3 tests/baseline/regression_compare.py all
```

**Exit Code:** 0

**Result:**
```
PASS  118/118 vectors match golden fixture exactly
PASS  284/284 vectors match golden fixture exactly
PASS  1 net(s), 11 pair(s) match golden fixture (tol=1e-06)
=== All suites PASS ===
```

**Status:** ✓ PASS

---

### Test 5: JSON Handoff Syntax

**Command:**
```bash
python3 -m json.tool < .ai/handoffs/Session_01_Claude.json > /dev/null
```

**Exit Code:** 0

**Status:** ✓ PASS (valid JSON syntax)

---

## Environment (Captured)

| Component | Version |
|-----------|---------|
| Python    | 3.12.13 [Clang 21.0.0] |
| PySide6   | 6.10.3 |
| Qt        | 6.10.3 |
| SciPy     | NOT INSTALLED |
| Platform  | macOS-26.6.2-arm64-arm-64bit |

---

## Closure Ownership Analysis

### BASE-001 — Freeze and tag v0.13 baseline

**Done When:** Three canonical suites pass: 118/118 headless, 284/284 real-board, 1 net/11 pairs report

| Suite | Count | Status |
|-------|-------|--------|
| Headless | 118/118 | ✓ PASS |
| Real-board (IP5385 power-bank) | 284/284 | ✓ PASS |
| IP5385 batch report | 1 net, 11 pairs | ✓ PASS |

**Status:** `closed`

---

### BASE-002 — Record behavioral compatibility requirements

**Done When:** "The list is reviewed against the README, schema, and v0.13 code."

`documents/compatibility_inventory.md` corrected against v0.13 source during coordinator repair:

| Error | Correction |
|-------|-----------|
| Tab named "Stackup" | Tab is "Setup" (class `SetupTab`, line ~5400) |
| `--plating <um\|mil\|oz>` | Only accepts numeric µm (float(args[...])); no unit string |
| `--dump-stackup` output: human-readable + JSON | Human-readable text table ONLY |
| CLI `--format md\|txt\|json\|pdf` | PDF is GUI-only (QPdfWriter); CLI: md, txt, json only |
| JSON output compact | JSON output is indented 2-space (json.dumps indent=2) |
| Report table: Margin and Pass/Fail columns | These columns do not exist in v0.13 |
| `--plating` "required, no default" | Default 18.0 µm (DEFAULT_OPTIONS line 2070) |
| `--current` default 0 A | Default 1.0 A (DEFAULT_OPTIONS line 2077) |
| signal_voltage_v not listed | Default 3.3 V (DEFAULT_OPTIONS line 2080) |
| outer_plating_adds default off | Default True (DEFAULT_OPTIONS line 2073) |
| max_pairs_warn not listed | Default 28 (DEFAULT_OPTIONS line 2079) |

**Status:** `closed`

---

### QA-004 — Add real-board regression suites

**Done When:** "Prior real-board defects cannot recur silently."

Created:
- `tests/baseline/fixtures/headless_118_selftest.json` — 118 normalized vectors
- `tests/baseline/fixtures/powerbank_284_selftest.json` — 284 normalized vectors, board SHA-256 recorded
- `tests/baseline/fixtures/ip5385_pack_report.json` — 1 net, 11 pairs, resistance values frozen
- `tests/baseline/regression_compare.py` — executable comparator for all three suites; exit code 0 = all match
- Normalization covers: macOS home, macOS temp (/var/folders), Linux temp (/tmp), Linux home; V18 platform-dependent sentinel

**Status:** `open` — fixtures and comparator complete for all three suites; CI automation deferred

---

### QA-006 — Add performance budgets

**Done When:** "Regressions fail automated benchmarks or require an explicit waiver."

Created:
- `tests/baseline/PERFORMANCE_BASELINE_v0.13.txt` — **measured** (not estimated) runtimes
  - Headless: 0.220 s wall clock
  - Power-bank: 27.882 s wall clock
  - Report: 9.512 s wall clock
  - Regression threshold: +20% flags a regression

Automated pytest-benchmark integration deferred to future session.

**Status:** `open` — baselines recorded; CI enforcement deferred

---

## Files Changed

### Added
```
baseline/
  README.md                                    (acceptance criteria, 3-suite canonical baseline)
  BASELINE_IDENTIFIER.txt                      (immutable tag, canonical test commands)

tests/baseline/
  README.md                                    (3 canonical suites, comparator, normalization rules)
  golden_fixtures_notes.md                     (~138 lines)
  PERFORMANCE_BASELINE_v0.13.txt               (measured runtimes)
  regression_compare.py                        (executable comparator, all 3 suites)
  fixtures/
    headless_118_selftest.json                 (118 normalized vectors)
    powerbank_284_selftest.json                (284 normalized vectors, 1 platform_dependent)
    ip5385_pack_report.json                    (1 net, 11 pairs, resistance values frozen)

documents/
  compatibility_inventory.md                   (corrected against v0.13 source)

documents/adr/
  ADR-001.md                                   (incremental refactor and parity policy)

ai_reference/kicad_project_example/
  Ref_PowerBank_injoinic_IP5385_v0.8.kicad_pcb  (2.1 MB; SHA-256: 0a1ca4dc...)
  Ref_PowerBank_injoinic_IP5385_v0.8.kicad_pro
  Ref_PowerBank_injoinic_IP5385_v0.8.kicad_sch
  change_log.kicad_sch
  main.kicad_sch
  net_selection_PACK.json                        (SHA-256: ff8e5ec8...)
  test_points.kicad_sch

.ai/handoffs/
  Session_01_Claude.md                         (this file)
  Session_01_Claude.json                       (JSON handoff)
```

**Total:** 20 files added, 0 modified, 0 removed

### Not Committed (excluded by design)
- `ai_reference/kicad_project_example/__MACOSX/` (macOS metadata)
- `SESSION_01_SUMMARY.md` (not in owned scope)

---

## APIs Changed
None. No APIs modified.

## Schemas Changed
None. `schema/pcb_net_selection.schema.json` preserved as-is.

## Compatibility Consequences
None. Session is documentation and baseline infrastructure only.

---

## Tests Executed

| # | Command | Exit | Result | Runtime |
|---|---------|------|--------|---------|
| 1 | `python3 tools/pcb_trace_resistance.py --selftest` | 0 | 118/118 PASS | 0.220 s |
| 2 | `python3 tools/pcb_trace_resistance.py --selftest <IP5385.kicad_pcb>` | 0 | 284/284 PASS | 27.882 s |
| 3 | `python3 tools/pcb_trace_resistance.py --report ... --nets ... --format json` | 0 | 1 net, 11 pairs PASS | 9.512 s |
| 4 | `python3 tests/baseline/regression_compare.py all` | 0 | 118+284+report match fixtures | ~38 s |
| 5 | `python3 -m json.tool < .ai/handoffs/Session_01_Claude.json` | 0 | Valid JSON | <1 s |

---

## Decisions

1. **Canonical baseline changed:** 254/254 reference-board suite removed at coordinator direction. IP5385 report suite added as third canonical check. All obsolete 254/254 and 656/656 references removed from all artifacts.

2. **KiCad project files committed:** Previously excluded; committed in alignment pass (coordinator directed) to make tests fully self-contained without external extraction.

3. **V18 platform-dependent height:** Stored as `<platform_dependent>` sentinel in powerbank fixture. Comparator verifies only status=PASS, not the pixel value. Preserves semantic got-equals-want check during live selftest execution.

4. **Notes normalization:** First-branch location stripped from report notes (hash-map iteration order is volatile); count and message pattern preserved. Regression is against the stable pattern.

5. **Create actual golden fixtures (not deferred):** All three suites have real fixture files from actual test runs with correct normalization applied.

6. **Measured runtimes only:** Wall-clock times from actual runs (headless 0.220 s, powerbank 27.882 s, report 9.512 s).

7. **BASE-002 closed:** All factual errors in compatibility_inventory.md corrected against v0.13 source in coordinator repair pass.

8. **Model substitution recorded:** Prompt specified Haiku-4.5; actual model is claude-sonnet-4-6. Authorized by user. Recorded in this handoff and in the inventory.

---

## Assumptions

1. v0.13 acceptance vectors are authoritative for all 118+284 selftest checks.
2. The power-bank board SHA-256 (`0a1ca4dcfbf8c6609319091f00a515854c3f78e60058272fbd93203d1276a6e9`) is stable; any change to the board file invalidates the fixture.
3. The net selection SHA-256 (`ff8e5ec8f10975670cb65495d2fe5f698ce803e1d7b4f295cfc6686c5aa7d111`) is stable; any change invalidates the report fixture.

---

## Deviations

1. **Model substitution:** claude-sonnet-4-6 used instead of claude-haiku-4-5-20251001 (prompt specification). Authorized by user.
2. **Canonical baseline changed:** 254/254 reference-board suite removed at coordinator direction; IP5385 report suite added.
3. **KiCad project files committed:** Previously excluded; committed in alignment pass (coordinator directed).
4. **Notes normalization added:** Not in original plan; required to handle hash-map order variance in branch location strings.

---

## Known Issues

1. **SciPy not installed** — Power-bank suite runs pure-Python solver (27.9 s). With SciPy the sparse solver would be faster. Severity: Low (correctness unaffected).
2. **Automated benchmark CI** — Performance thresholds recorded but not enforced in CI. Severity: Low (deferred to future session).

---

## Dependent Session Impact

- **Session 02 (Package and CI skeleton):** May proceed. BASE-001 and BASE-002 both closed. `regression_compare.py all` provides the canonical executable gate.
- **All subsequent sessions (03–34):** ADR-001 parity gates and corrected compatibility inventory are available. Three-suite regression compare is the canonical gate.

---

## Recommended Next Action

**For Coordinator:**

1. Run `python3 tests/baseline/regression_compare.py all` to confirm exit 0.
2. Review `documents/compatibility_inventory.md` against v0.13 source if desired.
3. If satisfied → mark INTEGRATED and assign Session 02.

---

**Handoff prepared by:** claude-sonnet-4-6 (authorized substitution for Haiku-4.5)
**Date:** 2026-08-27
**Status:** READY_FOR_REVIEW — all three canonical suites pass; BASE-001 and BASE-002 closed
