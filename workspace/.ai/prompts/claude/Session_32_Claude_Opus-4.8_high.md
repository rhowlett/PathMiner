# Session 32 — Signal-channel geometry screening

## Assignment

- **Recommended model:** Opus-4.8
- **Effort:** high
- **Role:** implementing writer for this session
- **Parallel wave:** W21-B
- **Prerequisite sessions:** Session 28

This file is one of two equivalent executor prompts. Use either this Claude prompt or the paired prompt for the same session—never both as concurrent writers. A second AI may review the completed handoff without changing files.

## Objective

Define rerunnable signal channels and identify local references, discontinuities, transitions, and visualization-only heuristics.

## Punch-list responsibility

Closure owner in this session:

- SIG-001
- SIG-002
- SIG-003
- SIG-007

Contributes to or extends these living/cross-session items:

- None

Do not mark a whole punch-list item complete unless its exact **Done when** clause in `.ai/planning/PathMiner_Implementation_Punch_List.md` has been demonstrated. Capability slices remain open until their named closure session.

## Preconditions

1. Work in a dedicated branch/worktree named `ai/session-32-claude-signal-geometry`.
2. Start from the exact coordinator-approved commit containing all prerequisites: Session 28.
3. Record `git rev-parse HEAD` as the base commit before editing.
4. Confirm no other writer owns this session or its allowed paths.
5. Run the relevant pre-change tests and record the results.
6. If Git metadata is absent, stop and ask the coordinator to create the baseline repository/commit; do not invent ancestry.

## Read first

Use this source-of-truth order and stop on an unresolved conflict:

1. This session prompt.
2. `.ai/planning/PathMiner_Refactor_and_Development_Plan.md` — Sections 2, 3, 7, 9, 11, and 15 plus this session row.
3. `.ai/planning/PathMiner_Project_Specification.md` — architecture, equations, data contracts, and capability sections relevant to this session.
4. `.ai/planning/PathMiner_Implementation_Punch_List.md` — assigned IDs and their exact completion clauses.
5. Existing files in `documents/`, `schema/`, and `.ai/reference/pathminer.md` relevant to the work.
6. Current tests.
7. Current implementation behavior in `tools/pcb_trace_resistance.py`.

Higher-priority sources win. Do not silently resolve a contradiction; record it in the handoff and pause the affected decision.

## Owned write scope

You may create or modify only these areas unless the coordinator grants a written scope amendment:

- pathminer/models/signal.py
- pathminer/analysis/signal_geometry.py
- schema/signal_channel.schema.json
- tests/test_signal_channel.py
- tests/test_signal_geometry.py

Reading elsewhere is allowed. Generated files must be produced by their generator, never hand-edited.

## Prohibited and out of scope

- Do not edit another active session's files.
- Do not broaden public APIs, schemas, defaults, units, tolerances, or numerical behavior beyond this session.
- Do not edit `tools/pcb_trace_resistance.py`, package export hubs, shared registries, or central schemas unless they are explicitly listed in Owned write scope.
- Do not merge, rebase, push, delete worktrees, or rewrite shared history.
- Do not add credentials, absolute machine paths, caches, generated reports, or proprietary external data.
- Do not replace validated physics with a heuristic. Preserve units, provenance, confidence, and failure modes.

## Required work

1. Inspect the assigned punch items, existing tests, and target symbols; write a brief implementation note in the handoff before coding.
2. Make the smallest coherent implementation that satisfies this session's objective and respects dependency direction.
3. Add positive, boundary, failure, and regression tests. Preserve stable acceptance-vector IDs where they exist.
4. Keep GUI, CLI, reports, and storage dependent on shared domain contracts rather than duplicated state or formulas.
5. Make output deterministic where practical; separate volatile metadata such as timestamps from golden content.
6. Update affected user/developer documentation and `documents/change_log.md` only when allowed by this session.
7. Re-run focused tests and all reasonably affected regression tests.

## Required deliverables

- stable channel schema
- route reference segmentation
- location-linked discontinuities
- explicit visualization-only label

## Verification

Run these commands when the named files exist, plus any narrower tests needed for changed code:

- python3 -m pytest -q tests/test_signal_channel.py tests/test_signal_geometry.py

Also run `python3 -m pytest -q` before handoff when it is available and proportionate. Record exact commands, exit codes, pass/fail/skip counts, runtime, and any unavailable fixture or dependency. Never report an unrun test as passing.

## Acceptance gate

- Every closure-owned punch item meets its exact completion clause, or is explicitly left open with evidence.
- Pre-existing baseline behavior remains within documented tolerances.
- No forbidden import or duplicated formula/state source is introduced.
- Persisted data validates before use/save and is portable when storage is involved.
- Results expose units, effective assumptions, provenance, confidence, and named errors as applicable.
- The diff contains no unrelated cleanup.

## Handoff

Create both:

- `.ai/handoffs/Session_32_Claude.md`
- `.ai/handoffs/Session_32_Claude.json`

Validate the JSON against `.ai/coordination/HANDOFF_SCHEMA.json`. Include session/AI/model/settings, base and final commits, branch, punch-item status (`implemented`, `verified`, `closed`, or `open`), files changed, APIs/schemas changed, exact tests/results, decisions, assumptions, deviations, known failures, dependent-session impact, and recommended next action.

End with one of: `READY_FOR_REVIEW`, `BLOCKED`, or `PARTIAL`. Do not mark the session integrated; only the coordinator may do that.
