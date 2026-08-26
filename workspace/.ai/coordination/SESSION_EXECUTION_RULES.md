# Session Execution Rules

1. The coordinator assigns exactly one implementing AI to a session.
2. The ChatGPT and Claude prompts with the same number are alternatives, never concurrent writers.
3. Every session starts from an approved integrated prerequisite commit in its own branch/worktree.
4. Parallel sessions are allowed only when their owned write scopes are disjoint. If scopes overlap, serialize them or obtain a written scope amendment.
5. Integration sessions alone may reconcile the legacy façade, shared exports, registries, release documents, or other explicitly reserved files.
6. A model may commit locally. It may not push, merge, rebase shared branches, delete worktrees, or rewrite history unless separately authorized.
7. Only the coordinator changes a status to `INTEGRATED` and opens dependent sessions.
8. No punch item is closed without evidence for its exact Done-when clause. Living QA controls are extended at capability gates and finally closed in Session 34.
9. Higher-priority sources override lower-priority sources. Contradictions must be logged, not guessed away.
10. If an exact recommended model is unavailable, pause assignment. The coordinator may choose an equal-or-stronger model class and record the substitution.

## States

`NOT_STARTED`, `ASSIGNED`, `IN_PROGRESS`, `READY_FOR_REVIEW`, `BLOCKED`, `PARTIAL`, `CHANGES_REQUESTED`, `APPROVED`, `INTEGRATED`.

## Branch convention

`ai/session-<NN>-<ai>-<slug>`

## Review option

The unused paired model can be given the implementation handoff and diff as a read-only reviewer. Its review must not modify the implementation branch; requested changes return to the assigned writer or a separately authorized repair session.
