# PathMiner Session Tools

These commands are stored with the PathMiner repository instead of being
installed under `~/.local/bin`. One shared activation file discovers the main
checkout through Git, activates `PathMiner/.venv`, and places this directory on
`PATH` for the current shell.

From the main checkout or any linked session worktree:

```bash
source "$(git rev-parse --path-format=absolute --git-common-dir)/../.session_tools/activate"
```

Available commands:

```bash
list
sanity_check 05
start_claude 05 --dry-run
start_claude 05
package_session_review 05 --dry-run
package_session_review 05
advance_session 05 06 --push
```

`list` is a shell function defined by `activate`. It lists executable scripts
in `.session_tools`. `deactivate` restores the original `PATH` and prompt and
removes the `list` function.

`package_session_review` refuses to bundle a dirty worktree and creates
`git_NN.log` plus `pathminer-sessionNN.bundle` beside the main checkout.

The older `workspace/.ai/bin` and `~/.local/bin` copies are not used by this
layout. After this directory is committed and verified, remove the former from
the repository and remove only the PathMiner-owned symlinks from the latter.
