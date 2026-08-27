# Session 01 — Baseline Freeze and Compatibility Inventory [PARTIAL]

**Status:** PARTIAL  
**AI:** Claude  
**Model:** claude-sonnet-4-6 (authorized substitution; prompt specified Haiku-4.5 / claude-haiku-4-5-20251001)  
**Effort Level:** Medium  
**Date:** 2026-08-26 (strict repair completed 2026-08-26)

---

## Executive Summary

Session 01 establishes PathMiner v0.13 baseline with documented compatibility requirements,
actual golden regression fixtures with executable comparator, measured performance baseline,
and architecture decision record. Two of three required acceptance suites pass (118/118 headless,
284/284 real-board). Reference-board test (254/254) is blocked because that board file is not in
the package. BASE-001 remains open; BASE-002 is open until coordinator reviews the corrected
compatibility inventory.

**Closure Status:**
- BASE-001 (Freeze baseline): `open` — 118/118 ✓  284/284 ✓  254/254 ⏳ blocked (reference board unavailable)
- BASE-002 (Compatibility inventory): `open` — corrected; pending coordinator review
- QA-004 (Regression fixtures): `open` — fixtures + comparator created for headless and power-bank suites; reference-board fixture blocked
- QA-006 (Performance budgets): `open` — measured baselines recorded; CI automation deferred to future session

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
- ✓ No modifications to v0.13 tool itself (frozen)
- ✓ No changes to shared APIs, schemas, or registries
- ✓ Extracted KiCad board files not committed (excluded from git add)
- ✓ SESSION_01_SUMMARY.md not committed (not in owned scope)

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

**Coverage:** Stackup math (V1–V6), via conventions (V4–V5), arc geometry (V9),
network solver (V11), schema validation (V12), GUI collapsibles (V13–V14, V18, V21, V23),
v0.2 regression vectors, zone geometry (V13–V14).

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

**Coverage (sample):**
- V10: Network resistance on 5 pad-pair combinations, segment sums, unreachable pair handling
- V15–V17: Skipped (not the reference test board) — expected
- V18: Collapsible section UI
- V19: Board label, JSON default dir
- V20: Skipped (not the reference test board) — expected
- V22: Zone-only pads, ladder vs. mesh comparison on real pour (within 5%), repeated pin collapsing

---

### Test 3: Reference-Board Selftest (254/254 expected)

**Status:** BLOCKED

**Required:** .kicad_pcb file with net `/SDA` (net 4) and pads `Z1.SDA`, `Z2.SDA`

**Impact:** BASE-001's exact Done-when clause requires all three suites. Only 402 of 656
total vectors verified.

---

### Test 4: Regression Comparator (executable)

**Command:**
```bash
python3 tests/baseline/regression_compare.py all
```

**Exit Code:** 0

**Result:**
```
PASS  118/118 vectors match golden fixture exactly
PASS  284/284 vectors match golden fixture exactly
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

**Status:** ✓ PASS (valid JSON syntax; jsonschema module not available for full schema validation)

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

**Done When:** "The archived version reproduces 254/254 reference-board checks, 284/284 real-board checks, and 118/118 headless checks."

| Suite | Count | Status |
|-------|-------|--------|
| Headless | 118/118 | ✓ PASS |
| Real-board (power-bank) | 284/284 | ✓ PASS |
| Reference-board | 254/254 | ⏳ BLOCKED — board unavailable |

**Status:** `open`

---

### BASE-002 — Record behavioral compatibility requirements

**Done When:** "The list is reviewed against the README, schema, and v0.13 code."

`documents/compatibility_inventory.md` was created then corrected during strict repair.
Errors corrected against v0.13 source (lines cited in revision history):

| Error | Correction |
|-------|-----------|
| Tab named "Stackup tab" | Tab is "Setup" (class `SetupTab`, label line 5400) |
| `--plating` "required, no default" | Default 18.0 µm (DEFAULT_OPTIONS line 2070) |
| `--current` default 0 A | Default 1.0 A (DEFAULT_OPTIONS line 2077) |
| signal_voltage_v not listed | Default 3.3 V (DEFAULT_OPTIONS line 2080) |
| outer_plating_adds default off | Default True (DEFAULT_OPTIONS line 2073) |
| max_pairs_warn not listed | Default 28 (DEFAULT_OPTIONS line 2079) |
| Zone model on Via/Path tab | Moved to Setup tab "Via and zone modelling" section (SetupTab.sec_model line 2913) |
| Plating on Via/Path tab input | Moved to Setup tab "Global settings" (GlobalConditions line 2700) |
| Drill/barrel conventions on Via/Path | Moved to Setup tab (SetupTab.drill_conv line 2881, len_conv line 2885) |

**Status:** `open` — corrected; pending coordinator review to verify all fields are now accurate

---

### QA-004 — Add real-board regression suites

**Done When:** "Prior real-board defects cannot recur silently."

Created:
- `tests/baseline/fixtures/headless_118_selftest.json` — 118 normalized vectors, SHA-256 of embedded data
- `tests/baseline/fixtures/powerbank_284_selftest.json` — 284 normalized vectors, board SHA-256 recorded
- `tests/baseline/regression_compare.py` — executable comparator; runs selftests and diffs output against fixtures; exit code 0 = all match
- Regression compare verified: 118/118 and 284/284 match exactly (exit code 0)

Reference-board fixture blocked pending board availability.

**Status:** `open` — fixtures and comparator functional for 2 of 3 suites; reference-board fixture deferred

---

### QA-006 — Add performance budgets

**Done When:** "Regressions fail automated benchmarks or require an explicit waiver."

Created:
- `tests/baseline/PERFORMANCE_BASELINE_v0.13.txt` — **measured** (not estimated) runtimes
  - Headless: 0.220 s wall clock
  - Power-bank: 27.882 s wall clock
  - Regression threshold: +20% flags a regression

Automated pytest-benchmark integration deferred to future session.

**Status:** `open` — baselines recorded; CI enforcement deferred

---

## Files Changed

### Added
```
baseline/
  README.md                                    (~200 lines)
  BASELINE_IDENTIFIER.txt                      (~50 lines)

tests/baseline/
  README.md                                    (~300 lines)
  golden_fixtures_notes.md                     (~138 lines)
  PERFORMANCE_BASELINE_v0.13.txt               (measured runtimes, ~70 lines)
  regression_compare.py                        (executable comparator, ~160 lines)
  fixtures/
    headless_118_selftest.json                 (118 normalized vectors)
    powerbank_284_selftest.json                (284 normalized vectors)

documents/
  compatibility_inventory.md                   (corrected, ~480 lines)

documents/adr/
  ADR-001.md                                   (~700 lines)

.ai/handoffs/
  Session_01_Claude.md                         (this file)
  Session_01_Claude.json                       (JSON handoff)
```

**Total:** 12 files added, 0 modified, 0 removed

### Not Committed (excluded by design)
- `ai_reference/kicad_project_example/Ref_PowerBank_injoinic_IP5385_v0.8.kicad_pcb` (extracted board)
- `ai_reference/kicad_project_example/__MACOSX/` (macOS metadata)
- Other extracted KiCad project files
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
| 2 | `python3 tools/pcb_trace_resistance.py --selftest <power-bank.kicad_pcb>` | 0 | 284/284 PASS | 27.882 s |
| 3 | `python3 tools/pcb_trace_resistance.py --selftest <ref_board.kicad_pcb>` | N/A | BLOCKED | N/A |
| 4 | `python3 tests/baseline/regression_compare.py all` | 0 | 118+284 match fixtures | ~28 s |
| 5 | `python3 -m json.tool < .ai/handoffs/Session_01_Claude.json` | 0 | Valid JSON | <1 s |

---

## Decisions

1. **Treat reference board as hard blocker for BASE-001:** Per coordinator directive, did not substitute a different board or repeat historical claims. BASE-001 remains open.

2. **Create actual golden fixtures (not deferred):** Previous attempt deferred fixture content. This repair creates actual JSON files from real test output with normalization applied and comparator verified.

3. **Measured runtimes only:** Previous attempt used estimated ranges (~4-5 s, ~8-12 s). This repair captures actual wall-clock times (0.220 s headless, 27.882 s power-bank) using `time`.

4. **BASE-002 left open:** Inventory had critical errors (wrong tab name, wrong defaults). After correction, left open per coordinator status rules pending review.

5. **Model substitution recorded:** Prompt specified Haiku-4.5; actual model is claude-sonnet-4-6. Recorded in this handoff and in the inventory.

---

## Assumptions

1. v0.13 acceptance vectors are authoritative for all 656 checks.
2. Reference board is a specific artifact with `/SDA` net and `Z1.SDA`/`Z2.SDA` pads; no substitute is acceptable.
3. The power-bank board SHA-256 (`0a1ca4dcfbf8c6609319091f00a515854c3f78e60058272fbd93203d1276a6e9`) is stable; any change to the board file invalidates the fixture.

---

## Deviations

1. **Model substitution:** claude-sonnet-4-6 used instead of claude-haiku-4-5-20251001 (prompt specification). Authorized by user.
2. **BASE-002 reopened:** Previous handoff claimed BASE-002 closed. Strict repair found critical errors requiring correction; status reset to open pending coordinator review.
3. **Golden fixtures created (not deferred):** Previous repair deferred fixture content; strict repair instruction forbids deferral.

---

## Known Issues

1. **Reference board unavailable** — Blocks BASE-001 closure (need 254/254). Severity: High.
2. **SciPy not installed** — Power-bank suite runs pure-Python solver (27.9 s). With SciPy the sparse solver would be faster. Severity: Low (correctness unaffected).
3. **Reference-board fixture missing** — `tests/baseline/fixtures/reference_254_selftest.json` cannot be created without the board. Severity: Medium.
4. **Automated benchmark CI** — Performance thresholds recorded but not enforced in CI. Severity: Low (deferred to future session).

---

## Dependent Session Impact

- **Session 02 (Package and CI skeleton):** Can proceed with BASE-002 pending review. BASE-001 blocks full integration until reference board available.
- **All subsequent sessions (03–34):** ADR-001 parity gates and corrected compatibility inventory are available. Regression comparator (`regression_compare.py`) provides immediate executable baseline check.

---

## Recommended Next Action

**For Coordinator:**

1. Review `documents/compatibility_inventory.md` for correctness against your knowledge of v0.13.
2. If inventory is correct → close BASE-002.
3. Locate reference board (.kicad_pcb with `/SDA` net, `Z1.SDA`/`Z2.SDA` pads) and run:
   ```bash
   python3 tools/pcb_trace_resistance.py --selftest <ref_board.kicad_pcb>
   # Expected: 254/254
   ```
4. If 254/254 pass → close BASE-001 and mark session INTEGRATED.
5. If reference board unavailable → coordinate with project owner; escalate or defer.
6. Assign Session 02 to next writer.

---

**Handoff prepared by:** claude-sonnet-4-6 (authorized substitution for Haiku-4.5)  
**Date:** 2026-08-26  
**Status:** PARTIAL — 2/3 suites pass; BASE-001 and BASE-002 open; coordinator review required
