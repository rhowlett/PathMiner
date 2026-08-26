# Claude: Start Here

This is a self-contained PathMiner v0.13 work package with the full project specification, punch list, 34 Claude session prompts, coordination controls, source, examples, schemas, and the original design conversation.

## Preflight

1. Verify the unopened package: `python3 validate_package.py` from the package root.
2. `cd workspace`.
3. Read `.ai/planning/SESSION_INDEX.md` and `.ai/coordination/SESSION_EXECUTION_RULES.md`.
4. This supplied source has no Git history. Before any session, initialize it once:

   ```bash
   git init
   git add .
   git commit -m "PathMiner v0.13 packaged baseline"
   git tag pathminer-v0.13-packaged-baseline
   ```

5. Assign exactly one Claude prompt for a ready session. Record the baseline commit and create the named branch/worktree.

Do not run two writers for the same session. The corresponding ChatGPT prompt exists in the separate paired-prompt package and is an alternative executor, not a second implementation. If a second model is used, make it a read-only reviewer of the completed diff and handoff.

## Source-of-truth order

1. Assigned session prompt
2. Refactor and development plan
3. Project specification
4. Implementation punch list
5. Existing design contracts and schemas
6. Current tests
7. Current implementation behavior

Stop and log unresolved contradictions. Never silently choose a lower-priority source.

## Locations inside `workspace`

- Claude prompts: `.ai/prompts/claude/`
- Plans/specifications: `.ai/planning/`
- Rules, ledger, schemas, and coordinator guide: `.ai/coordination/`
- Original conversation and repository map: `.ai/reference/`
- Handoffs: `.ai/handoffs/`
- Working application: normal repository paths such as `tools/`, `schema/`, `documents/`, and the future `pathminer/` package

## Package limitations

- Model labels are owner-supplied routing recommendations; confirm the selected Claude model is available before starting.
- External field solvers, measured thermal data, and proprietary component libraries are not bundled. Sessions that require them must stop or produce clearly labeled scaffolding until approved data/tools are supplied.
- The package contains a nested reference KiCad project archive but may still require deliberate extraction/configuration for board-backed acceptance runs.
