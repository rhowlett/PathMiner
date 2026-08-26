# Integration Playbook

## Before assignment

- Verify prerequisite sessions are `INTEGRATED`.
- Record the base commit and expected write scope.
- Assign one writer and mark the paired prompt unused or reviewer-only.
- Check that no active branch owns overlapping files.

## Review

- Validate both Markdown and JSON handoffs.
- Compare each claimed closure against the punch-list Done-when clause.
- Re-run focused tests and the appropriate integration gate.
- Reject unrelated changes, silent schema/default changes, missing provenance, or unsupported confidence claims.

## Integration

- Integrate in dependency order, never by session number alone when prerequisites differ.
- After merging a parallel wave, run the combined regression suite before opening downstream sessions.
- Central façade/registry conflicts belong to the next designated integration session; feature sessions must not resolve them opportunistically.
- Record the integrated commit and status in `SESSION_STATUS.csv` and relevant decisions in `DECISION_LOG.md`.

## Recovery

- If a session starts from the wrong base, stop it and transplant only reviewed commits onto a fresh branch.
- If scopes overlap, freeze both branches, choose the owner, and convert the other output to a read-only patch/review.
- If numerical parity fails, preserve both outputs, isolate the first failing vector, and open an explicit repair session; do not loosen tolerances without an ADR.
