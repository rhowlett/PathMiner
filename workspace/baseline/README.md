# PathMiner v0.13 Baseline

**Baseline Commit:** fe507fd01017cd0930739cbd8c4cc3f916b47e98
**Baseline Date:** 2026-08-26
**Status:** Immutable reference implementation

## Overview

This directory contains documentation, fixtures, and test results for PathMiner v0.13,
the validated baseline implementation from which all refactoring work proceeds.

## Contents

- `BASELINE_IDENTIFIER.txt` — Immutable baseline tag, commit hash, and canonical test commands

## Scope

The v0.13 baseline is the complete, working implementation in `tools/pcb_trace_resistance.py`:
- Single-file PySide6 application (5545 lines)
- Four UI tabs: Trace, Via/Path, Report, Setup
- Headless batch mode driven by JSON net-selection files
- Board-net tracing with Dijkstra search
- Nodal analysis solver with optional SciPy backend
- DC resistance and IPC-2221 temperature-rise calculations

## Acceptance Criteria

The canonical acceptance baseline is defined by three verifiable checks, all currently PASS:

1. **118/118 headless selftest** ✓
   `python3 tools/pcb_trace_resistance.py --selftest`

2. **284/284 real-board selftest** ✓ (IP5385 power-bank)
   `python3 tools/pcb_trace_resistance.py --selftest ai_reference/kicad_project_example/Ref_PowerBank_injoinic_IP5385_v0.8.kicad_pcb`
   Board SHA-256: `0a1ca4dcfbf8c6609319091f00a515854c3f78e60058272fbd93203d1276a6e9`

3. **IP5385 batch report — 1 net, 11 pairs** ✓ (PACK_P net, net_selection_PACK.json)
   `python3 tools/pcb_trace_resistance.py --report ... --nets ... --format json`
   Resistance values frozen in `tests/baseline/fixtures/ip5385_pack_report.json`

Executable regression comparison:
```bash
python3 tests/baseline/regression_compare.py all   # exit 0 = all baselines match
```

## Models Validated

1. **Trace Resistance** — R = ρL/(W·t) with temperature correction
2. **Via Barrel Resistance** — π/4·(OD²-ID²) with plating and layer span options
3. **Zone Models** — None, 1-D ladder, and rasterized mesh
4. **Nodal Analysis** — Parallel copper, network-equivalent resistance
5. **Temperature Rise** — IPC-2221 curve-fit for isolated traces
6. **Arc Length** — True arc through three points

## Numerical Guarantees

- All v0.13 results remain within published tolerances
- Copper material data: IACS annealed copper, 1.724e-8 Ω·m at 20°C, α = 0.00393/K
- Via conventions: Hole (bit/finished), barrel length (facing/centre/outer)
- Outer plating growth: Adds 2×plating thickness to board stack

## Known Limitations

As documented in `tools/pcb_trace_resistance.py`:
- Through vias only (no blind/buried/microvias)
- DC steady-state only (no AC or skin effect)
- No pad spreading or thermal-relief-spoke models
- No full-wave electromagnetic simulation
- IPC-2221 is an isolated-trace estimate
- Electrodeposited barrel plating resistivity not separately modeled

## Preserved Behavior

All compatibility items listed in `documents/compatibility_inventory.md` must survive the refactor.

## Next Steps

1. Run all regression suites before each session (`regression_compare.py all`)
2. Proceed to package extraction (Session 02)
