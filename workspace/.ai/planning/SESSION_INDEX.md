# PathMiner AI Session Index

Paired ChatGPT and Claude prompts are alternative executors for the same unit of work. Assign one writer per session. A second model may perform a read-only review after handoff.

| # | Session | Wave | Depends on | Closure ownership | ChatGPT model / speed / effort | Claude model / effort |
|---:|---|---|---|---|---|---|
| 01 | Baseline freeze and compatibility inventory | W0 | None | BASE-001, BASE-002 | 5.6-luna / fast / medium | Haiku-4.5 / medium |
| 02 | Package and CI skeleton | W1 | Session 01 | ARCH-001, ARCH-002 | 5.6-terra / fast / high | Sonnet-4.6 / high |
| 03 | Units, materials, trace and via extraction | W2-A | Session 02 | PWR-001 | 5.6-sol / standard / high | Sonnet-5 / high |
| 04 | Geometry and numerical backend extraction | W2-B | Session 02 | BASE-005 | 5.6-sol / standard / extra high | Opus-4.8 / extra |
| 05 | KiCad syntax, stackup and preferences extraction | W2-C | Session 02 | slice only | 5.6-terra / fast / high | Sonnet-4.6 / high |
| 06 | BoardSource and file-backed board model | W3 | Session 05 | ARCH-003 | 5.6-sol / standard / high | Sonnet-5 / high |
| 07 | Common network, builders and model-selection policy | W4 | Session 03, Session 04, Session 06 | ARCH-004 | 5.6-sol / standard / max | Opus-4.8 / extra |
| 08 | Compatibility integration and single-file build | W5 | Session 03, Session 04, Session 07 | BASE-004, ARCH-006, ARCH-010 | 5.6-sol / standard / high | Sonnet-5 / high |
| 09 | Shared domain contracts | W6 | Session 08 | ARCH-005 | 5.6-sol / standard / extra high | Opus-4.8 / high |
| 10 | Schemas, defaults and migration | W7 | Session 09 | ARCH-009, DATA-002, DATA-003, QA-002 | 5.6-sol / standard / high | Sonnet-5 / high |
| 11 | Project storage, identifiers, provenance and atomic writes | W8-A | Session 10 | DATA-001, DATA-004, DATA-007, DATA-008, DATA-009 | 5.6-terra / standard / high | Sonnet-5 / high |
| 12 | Immutable runs and portable analysis bundles | W9-A | Session 11 | DATA-010, DATA-011 | 5.6-terra / fast / high | Sonnet-4.6 / high |
| 13 | Headless runner, jobs and factorization reuse | W10 | Session 07, Session 09, Session 12 | ARCH-007 | 5.6-sol / standard / max | Opus-4.8 / extra |
| 14 | Report registry and canonical result renderers | W8-B | Session 09, Session 10 | ARCH-008, AUTO-003, AUTO-005 | 5.6-terra / standard / high | Sonnet-5 / high |
| 15 | CLI, exit codes and CI examples | W11-A | Session 13, Session 14 | AUTO-001, AUTO-002, AUTO-007 | 5.6-terra / fast / high | Sonnet-4.6 / high |
| 16 | Application shell, Project destination and shared status | W8-C | Session 09, Session 10 | UI-001, UI-002, UI-003, UI-004, UI-015 | 5.6-sol / standard / high | Sonnet-5 / high |
| 17 | Investigation, shared scope and explicit pairs | W9-B | Session 16 | UI-005, UI-006, UI-007, UI-016 | 5.6-sol / standard / high | Sonnet-5 / high |
| 18 | Analysis configuration and path unification | W11-B | Session 13, Session 16, Session 17 | UI-008, UI-009, UI-010, UI-011 | 5.6-sol / standard / max | Opus-4.8 / extra |
| 19 | Reusable results and compare/what-if UI | W12 | Session 18 | UI-012 | 5.6-sol / standard / high | Fable-5 / high |
| 20 | Reports, Diagnostics and diagnostic bundles | W13 | Session 14, Session 16, Session 17, Session 19 | UI-013, UI-014, AUTO-006 | 5.6-terra / standard / high | Sonnet-5 / high |
| 21 | Resistance v1 integration and release gate | W14 | Session 15, Session 18, Session 20 | BASE-003, PWR-002, QA-003, QA-004, QA-005, QA-006, QA-007 | 5.5 / standard / max | Opus-4.8 / max |
| 22 | Component sidecar, snapshots and captured paths | W15 | Session 21 | DATA-005, DATA-006, PWR-003, PWR-004 | 5.6-sol / standard / extra high | Opus-4.8 / high |
| 23 | Thin KiCad capture plugin | W16-A | Session 22 | AUTO-004 | 5.6-terra / fast / high | Sonnet-4.6 / high |
| 24 | Source, load and current-limit physics | W16-B | Session 22 | PWR-005, PWR-006, PWR-007 | 5.5 / standard / max | Opus-4.8 / max |
| 25 | Verdicts, margins and parallel branches | W17 | Session 24 | PWR-008, PWR-009, PWR-010 | 5.5 / standard / max | Opus-4.8 / max |
| 26 | Power-tree structure and investigation integration | W18 | Session 22, Session 25 | PWR-011 | 5.6-sol / standard / extra high | Opus-4.8 / high |
| 27 | Simultaneous multi-load solve and what-if | W19 | Session 25, Session 26 | PWR-012, PWR-013 | 5.5 / standard / max | Opus-4.8 / max |
| 28 | System-power release gate | W20 | Session 23, Session 27 | slice only | 5.5 / standard / max | Opus-4.8 / max |
| 29 | DC return geometry, mesh, injections and solve | W21-A | Session 28 | RET-001, RET-002, RET-003, RET-004 | 5.5 / standard / max | Opus-4.8 / max |
| 30 | DC return metrics, maps and release evidence | W22-A | Session 29 | RET-005, RET-006 | 5.5 / standard / max | Opus-4.8 / max |
| 31 | Thermal, electrothermal and correlation gate | W23-A | Session 30 | RET-007, RET-008, RET-009, RET-010 | 5.5 / standard / max | Opus-4.8 / max |
| 32 | Signal-channel geometry screening | W21-B | Session 28 | SIG-001, SIG-002, SIG-003, SIG-007 | 5.6-sol / standard / extra high | Opus-4.8 / high |
| 33 | Complex signal-return network and coupling | W22-B | Session 32 | SIG-004, SIG-005, SIG-006 | 5.5 / standard / max | Opus-4.8 / max |
| 34 | Signal overlays, field-solver correlation and final gates | W24 | Session 31, Session 33 | SIG-008, SIG-009, QA-001, QA-008, QA-009 | 5.5 / standard / max | Opus-4.8 / max |
