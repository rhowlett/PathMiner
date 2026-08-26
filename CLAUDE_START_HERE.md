# Claude: Start Here

This is a self-contained PathMiner v0.13 work package with the full project specification, punch list, 34 Claude session prompts, coordination controls, source, examples, schemas, and the original design conversation.

## Directory model

The directory containing this file is the **Git worktree root**. The application and AI coordination files are intentionally contained in its `workspace/` subdirectory, which is the **Claude execution root**.

For the main checkout and a Session 01 worktree, the expected layout is:

```text
PathMiner/                              # main Git worktree root
├── CLAUDE_START_HERE.md
├── validate_package.py
├── workspace/                         # main Claude execution root
│   ├── CLAUDE.md
│   ├── .ai/
│   ├── tools/
│   ├── schema/
│   └── documents/
└── pathminer-session-01-claude/       # optional nested secondary worktree
    ├── CLAUDE_START_HERE.md
    └── workspace/                     # Session 01 Claude execution root
        ├── CLAUDE.md
        ├── .ai/
        ├── tools/
        ├── schema/
        └── documents/
```

The repository may be named `PathMiner`; `workspace` is only the stable execution subdirectory. All prompt paths such as `.ai/...`, `tools/...`, and `documents/...` are relative to the active worktree's `workspace/` directory.

Git commands work from either level, but always launch Claude and run PathMiner commands from the active worktree's `workspace/` directory. For Session 01 in the layout above:

```bash
cd pathminer-session-01-claude/workspace
```

A sibling worktree beside `PathMiner/` is safer than a worktree nested inside it. If a worktree is intentionally nested as shown above, exclude it locally in the main checkout before any broad `git add` command:

```bash
echo "pathminer-session-*/" >> "$(git rev-parse --git-common-dir)/info/exclude"
```

Confirm that `git status --short` in the main checkout does not list the nested worktree. Never commit one worktree as content of another.

## Preflight

1. Verify the unopened package: `python3 validate_package.py` from the package root.
2. If this supplied package has no Git history, initialize it once from the package/Git root—the directory containing this file:

   ```bash
   git init
   git add .
   git commit -m "PathMiner v0.13 packaged baseline"
   git tag pathminer-v0.13-packaged-baseline
   ```

3. Create or enter the assigned session worktree, then `cd workspace` inside that worktree.
4. Read `.ai/planning/SESSION_INDEX.md` and `.ai/coordination/SESSION_EXECUTION_RULES.md` from the active `workspace/` directory.
5. Assign exactly one Claude prompt for a ready session. Record the baseline commit and branch/worktree.
6. Launch Claude from the active `workspace/` directory so it loads `CLAUDE.md` and all prompt-relative paths resolve correctly.

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

## Locations relative to the active execution root (`workspace/`)

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
