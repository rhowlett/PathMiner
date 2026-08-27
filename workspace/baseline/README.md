# PathMiner v0.13 Baseline

**Baseline Commit:** fe507fd01017cd0930739cbd8c4cc3f916b47e98  
**Baseline Date:** 2026-08-26  
**Status:** Immutable reference implementation

## Overview

This directory contains documentation, fixtures, and test results for PathMiner v0.13, the validated baseline implementation from which all refactoring work proceeds.

## Contents

- `BASELINE_IDENTIFIER.txt` - Immutable baseline tag and commit hash
- Test results and performance baselines (to be filled in during test runs)
- Golden fixtures with normalized volatile fields (to be created)

## Scope

The v0.13 baseline is the complete, working implementation in `tools/pcb_trace_resistance.py`:
- Single-file PySide6 application
- Three UI tabs: Trace, Via/Path, Stackup
- Headless batch mode driven by JSON net-selection files
- Board-net tracing with Dijkstra search
- Nodal analysis solver with optional SciPy backend
- DC resistance and IPC-2221 temperature-rise calculations

## Acceptance Criteria

The baseline is frozen when all acceptance vectors pass:
- 254/254 reference-board selftest checks ✓
- 284/284 real-board (power-bank) selftest checks ✓
- 118/118 headless (no-board) selftest checks ✓

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

1. Create immutable baseline identifier (v0.13.0 tag)
2. Run and record all selftest results with exact version
3. Create golden fixtures for representative use cases
4. Document performance baselines (project load, solve times)
5. Proceed to architecture extraction (Session 02)
