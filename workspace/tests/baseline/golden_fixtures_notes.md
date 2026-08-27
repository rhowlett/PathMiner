# Golden Fixtures — Test Infrastructure

**Status:** Framework established; fixture creation pending reference board availability  
**Date:** 2026-08-26  
**Session:** 01 (repair phase)

## Purpose

Golden fixtures are immutable reference outputs used to detect numerical regressions and report-contract changes. This document defines their structure, normalized fields, and integrity checks.

## Fixture Sources and SHA-256 Checksums

### Source Board Files

| Board | Location | SHA-256 | Status |
|-------|----------|---------|--------|
| Headless (v0.13 embedded) | tools/pcb_trace_resistance.py | N/A (embedded) | ✓ Available |
| Power-Bank (Real Board) | ai_reference/kicad_project_example/Ref_PowerBank_injoinic_IP5385_v0.8.kicad_pcb | (to be measured) | ✓ Available |
| Reference (Test Board) | ai_reference/kicad_project_example/?? | (unknown) | ⏳ BLOCKED |

### Fixture Output Formats

Fixtures will be created in JSON (canonical), with rendered Markdown and text for human review.

```
tests/baseline/fixtures/
├── headless_118_checks.json          (118/118 selftest output, canonicalized)
├── headless_118_checks.md            (human-readable render)
├── headless_118_checks.txt           (plaintext render)
├── powerbank_284_checks.json         (284/284 selftest output, canonicalized)
├── powerbank_284_checks.md           (human-readable render)
├── powerbank_284_checks.txt          (plaintext render)
├── reference_254_checks.json         (pending reference board)
├── reference_254_checks.md           (pending reference board)
├── reference_254_checks.txt          (pending reference board)
└── fixture_manifest.json             (integrity and source metadata)
```

## Field Normalization Rules

Golden fixtures must normalize volatile fields so regression tests detect only logical changes, not environmental noise.

### Timestamps (EXCLUDE)
- Fixture generation timestamp: EXCLUDE from comparison
- Report generation `generated` field: EXCLUDE (timestamp-dependent)
- Any ISO-8601 or Unix-epoch timestamp: EXCLUDE

### Paths (NORMALIZE)
- Absolute paths → relative to workspace root
- Example: `/Users/.../<workspace>/ai_reference/...` → `ai_reference/...`
- Machine-specific home directories → `.` (current directory marker)

### Runtime Metadata (EXCLUDE)
- Solver execution time: EXCLUDE
- Parse/trace time: EXCLUDE
- Benchmark elapsed seconds: EXCLUDE
- Memory usage: EXCLUDE

### Machine-Specific (NORMALIZE or EXCLUDE)
- SciPy availability: NORMALIZE to "available" or "not-available"
- Python version: NORMALIZE to major.minor only
- PySide6/Qt version: NORMALIZE to major.minor only
- Platform: NORMALIZE to "darwin", "linux", or "win32"

### Version Identifiers (NORMALIZE)
- Tool version v0.13: NORMALIZE to "baseline" (immutable)
- Schema version: NORMALIZE to version string only (not timestamp)
- Board timestamp/UUID: EXCLUDE (non-deterministic KiCad fields)

## Fixture Integrity

Each fixture JSON includes a metadata section:

```json
{
  "_fixture_meta": {
    "session": 1,
    "date": "2026-08-26",
    "source_board": "Ref_PowerBank_injoinic_IP5385_v0.8.kicad_pcb",
    "source_board_sha256": "...",
    "command": "python3 tools/pcb_trace_resistance.py --selftest <board>",
    "exit_code": 0,
    "vectors_passed": 284,
    "vectors_total": 284,
    "normalized_for_regression": true,
    "normalization_rules": [
      "timestamps excluded",
      "absolute paths normalized to relative",
      "platform-specific metadata omitted"
    ]
  },
  "selftest_vectors": [
    { "id": "V10 Q7.S->R51.1 path>0", "status": "PASS", "got": true, "want": true },
    ...
  ]
}
```

## Regression Test Execution

When fixtures are complete, the regression test will:

1. Run selftest with the appropriate board
2. Canonicalize the output (apply normalization rules)
3. Compare against the golden fixture using deep equality
4. Report pass/fail with delta details if mismatch

Example:
```bash
python3 tests/baseline/regression_test.py headless
# Output: ✓ 118/118 headless vectors match golden fixture
```

## Fixture Updates

Fixtures are immutable during Session 01. They may be updated only with explicit coordinator approval in future sessions, with careful review of any numerical changes.

Update approval requires:
- Evidence of intentional change (e.g., numeric precision fix)
- Proof that change improves accuracy without loss
- Update to the fixture SHA-256 and metadata
- Change log entry documenting the update

## Pending Work

- [ ] Extract headless selftest output → `tests/baseline/fixtures/headless_118_checks.json`
- [ ] Extract power-bank selftest output → `tests/baseline/fixtures/powerbank_284_checks.json`
- [ ] Calculate source board SHA-256 checksums
- [ ] Apply normalization rules to both fixtures
- [ ] Create human-readable renderings (.md, .txt)
- [ ] Create `fixture_manifest.json` with integrity metadata
- [ ] Create `regression_test.py` executable test script
- [ ] Obtain reference board and extract `tests/baseline/fixtures/reference_254_checks.json`

---

**Status:** Framework complete; fixture content creation deferred to integration phase after reference board is available.
