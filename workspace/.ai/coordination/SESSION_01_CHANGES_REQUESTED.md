# Session 01 — Coordinator Changes Requested

Resume the existing Claude session and repair Session 01 on the existing branch `ai/session-01-claude-baseline`. Do not start Session 02, merge, rebase, push, tag, or modify coordinator-owned status files.

Read the original Session 01 prompt, `SESSION_01_COORDINATOR_REVIEW.md`, the punch-list Done-when clauses, and the current handoffs before editing.

## Mandatory corrections

1. Treat `BASE-001` as open until all three required suites reproduce exactly 118/118, 254/254, and 284/284. If the approved reference board or power-bank board is unavailable, stop with `BLOCKED`; do not substitute a different board or repeat a historical claim.
2. Add executable golden fixtures under `tests/baseline/` that detect numerical and report-contract changes. Include source-board SHA-256 values and normalization rules. Normalize or exclude timestamps, absolute paths, runtimes, and machine-specific metadata.
3. Add an actual measured baseline performance report. Record the machine/OS, Python, PySide6/Qt, optional SciPy status, exact commands, sample count, runtime statistic, and any unavailable scenario. A template alone is insufficient. Keep `QA-006` open unless its full Done-when clause is met.
4. Correct the file inventory. The Markdown and JSON handoffs must match `git diff --name-status <base_commit>..HEAD`, including both handoff files where appropriate.
5. Validate `.ai/handoffs/Session_01_Claude.json` against `.ai/coordination/HANDOFF_SCHEMA.json` and record the exact validator command and exit code.
6. Update the execution summary so it does not say complete or satisfied while a mandatory gate is pending.
7. Re-run focused tests, the full available pytest suite, all three acceptance runs, `git diff --check`, and the scope check. Record exact commands, exit codes, counts, and runtimes. Never report an unrun test as passing.

## Status rules

- End `READY_FOR_REVIEW` only if every mandatory Session 01 gate passes.
- End `BLOCKED` if either approved board or another required dependency is unavailable.
- End `PARTIAL` if useful work is committed but a non-dependency acceptance condition remains incomplete.
- Do not mark the session integrated; only the coordinator may do that.

Commit the repair locally and update both required handoff files. Report the base commit, final implementation commit, branch HEAD, and recommended coordinator command sequence.
