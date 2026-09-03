<!-- v0.2 -->
# Golden Fixtures — Test Infrastructure

**Status:** All three canonical fixtures created and comparator verified PASS
**Date:** 2026-08-26 (updated 2026-08-27 coordinator repair v3)
**Session:** 01 (claude-sonnet-4-6; authorized substitution for Haiku-4.5)

## Purpose

Golden fixtures are immutable reference outputs used to detect numerical regressions
and report-contract changes between refactoring sessions. Each fixture was captured
from a real run on the v0.13 baseline (commit fe507fd) with volatile fields normalized.

## Canonical Acceptance Gate

All three suites must exit 0 before a session is eligible for integration:

```bash
python3 tests/baseline/regression_compare.py all
```

## Fixture Files

### 1. `fixtures/headless_118_selftest.json`

**Source:** `python3 tools/pcb_trace_resistance.py --selftest` (no board file)
**Vectors:** 118 (all PASS)
**Board SHA-256:** N/A (embedded selftest data; no external board file)

Normalized fields:
- 4 vectors use `<normalized_path>` — V23 path-resolution tests that produce
  temp-directory paths from `mkdtemp`
- 0 platform-dependent vectors

Fixture structure:
```json
{
  "_fixture_meta": {
    "session": 1,
    "date": "2026-08-26",
    "source_board": "embedded (no board file)",
    "source_board_sha256": "N/A (embedded selftest data)",
    "command": "python3 tools/pcb_trace_resistance.py --selftest",
    "exit_code": 0,
    "vectors_passed": 118,
    "vectors_total": 118,
    "normalized_for_regression": true,
    "normalization_rules": [...]
  },
  "selftest_vectors": [
    {"status": "PASS", "description": "...", "got": "...", "want": "..."},
    ...
  ]
}
```

### 2. `fixtures/powerbank_284_selftest.json`

**Source:** `python3 tools/pcb_trace_resistance.py --selftest <IP5385.kicad_pcb>`
**Vectors:** 284 (all PASS)
**Board SHA-256:** `0a1ca4dcfbf8c6609319091f00a515854c3f78e60058272fbd93203d1276a6e9`

Normalized fields:
- 5 vectors use `<normalized_path>` — V19 "json default dir is the board dir"
  (workspace-relative board path) and V23 temp-directory paths
- 1 vector uses `<platform_dependent>` — V18 "reopen restores height" (pixel
  count varies by screen DPI and font metrics; the selftest itself verifies
  got==want at runtime; PASS status is what the fixture checks)

### 3. `fixtures/ip5385_pack_report.json`

**Source:** `python3 tools/pcb_trace_resistance.py --report <IP5385.kicad_pcb> --nets net_selection_PACK.json --format json`
**Net:** `/Reference Design/PACK_P`
**Pairs:** 11 (JP1.B source)
**Board SHA-256:** `0a1ca4dcfbf8c6609319091f00a515854c3f78e60058272fbd93203d1276a6e9`
**Net selection SHA-256:** `ff8e5ec8f10975670cb65495d2fe5f698ce803e1d7b4f295cfc6686c5aa7d111`

Normalized fields:
- `generated` timestamp: excluded from comparison
- `solve_seconds` per pair: excluded from comparison
- `notes` branch-location: first-branch location string stripped (hash-map
  iteration order is non-deterministic); count `(and N more)` and message
  text are preserved and compared

## Normalization Rules

### selftest vectors

The comparator (`regression_compare.py`) applies these rules in order:

1. **Workspace-root paths → `<normalized_path>`**
   The repo checkout root (wherever the repo lives on any machine) is replaced
   deterministically. This covers developer machines, Docker containers, and
   GitHub Actions runners regardless of checkout path.

2. **macOS home paths → `<normalized_path>`**
   Pattern: `/Users/<username>/...`

3. **macOS temp paths → `<normalized_path>`**
   Pattern: `/var/folders/...` (produced by `tempfile.mkdtemp()`)

4. **Linux temp paths → `<normalized_path>`**
   Pattern: `/tmp/...`

5. **Linux home paths → `<normalized_path>`**
   Pattern: `/home/<username>/...`

6. **CI workspace roots → `<normalized_path>`**
   Patterns: `/workspace/...`, `/github/workspace/...`, `/runner/work/...`

7. **Platform-dependent values → `<platform_dependent>`**
   Descriptions in `_PLATFORM_DEPENDENT_DESCRIPTIONS` (currently only
   "V18 reopen restores height"). Both `got` and `want` are replaced with
   the sentinel; the comparator skips the got/want check and verifies only
   that `status == "PASS"`.

### report pairs

1. Board and net-selection SHA-256 values: verified against fixture metadata
   before comparing results
2. `generated` field: excluded (timestamp-dependent)
3. `solve_seconds` per pair: excluded (timing-dependent)
4. Numeric result and nested-segment floats: compared with 1e-6 relative
   tolerance; segment keys, order, labels, layers, integer counts, and other
   non-floating values remain exact
5. `notes` branch-location: first-branch location stripped; remaining
   structure `"branch (and N more): <message>"` compared exactly

## Running the Comparator

```bash
# All three canonical suites
python3 tests/baseline/regression_compare.py all

# Individual suites
python3 tests/baseline/regression_compare.py headless
python3 tests/baseline/regression_compare.py powerbank
python3 tests/baseline/regression_compare.py report
```

Exit codes: 0 = all match, 1 = mismatch found, 2 = usage/I/O error

## Fixture Integrity

Fixtures are immutable during Session 01 and may be updated only with explicit
coordinator approval in future sessions. Any update requires:
- Evidence of an intentional, authorized change
- New run capturing the updated output
- Re-verification that all three suites pass
- Commit message citing the authorizing decision

## What Is NOT in Fixtures

- Reference-board selftest (254 vectors) — removed from canonical baseline;
  the IP5385 real-board selftest (284 vectors) is the canonical board-level gate
- PDF output — PDF rendering is GUI-only (QPdfWriter); not testable headlessly
- GUI screenshot / pixel tests — deferred to a future session
