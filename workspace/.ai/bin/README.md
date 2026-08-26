# PathMiner AI Session Automation

These commands discover the active PathMiner `workspace/` from the current directory, so they work from the execution root or its Git worktree root.

## Install command links

From the active worktree's `workspace/` directory:

```bash
python3 .ai/bin/install_commands
```

If prompted, add this once to `~/.zshrc` and open a new shell:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Use

```bash
sanity_check 01
start_claude 01
```

`sanity_check` verifies the branch, base commit, clean worktree, tracked prompt, prerequisite status, Python 3.10+, PySide6, pip dependencies, the v0.13 headless self-test, Claude CLI, authentication, and nested-worktree exclusion.

`start_claude` runs the same preflight, resolves the paired Claude prompt, maps its model and effort to current Claude CLI flags, activates the worktree `.venv` for the launched process, names the Claude session, and supplies the initial instruction to read and execute the session prompt.

Options:

```bash
sanity_check 01 --skip-selftest
start_claude 01 --dry-run
start_claude 01 --skip-selftest
```

Haiku 4.5 does not support the Claude CLI effort control, so its assigned effort is treated as a prompt-level planning posture. Other Claude `extra` assignments map to CLI `xhigh`.
