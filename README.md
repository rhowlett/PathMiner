<!-- v0.1 -->
# PathMiner

DC resistance analysis for KiCad PCBs: it traces real routed copper, vias and pours into a
resistor network and reports point-to-point resistance, voltage drop and temperature rise.
The application and package live in [`workspace/`](workspace/README.md); the AI session
system that drives development starts at [`CLAUDE_START_HERE.md`](CLAUDE_START_HERE.md).

## Install

```bash
cd workspace
python -m pip install -e ".[gui,dev]"
```

## Usage

```bash
python workspace/tools/pcb_trace_resistance.py            # GUI
python workspace/tools/pcb_trace_resistance.py --selftest # aggregate self-test
cd workspace && python -m pytest -q                       # test suite
```

The full description, status and options are in [`workspace/README.md`](workspace/README.md).

<!-- BRICKCHIP-LICENSE:BEGIN -->
## Copyright & License

```text
################################################################################
#                                                                              #
# ███████  ███████    ██ ███████  ██   ██     ███████  ██   ██    ██ ███████   #
# ██   ██  ██   ██    ██ ██   ██  ██   ██     ██   ██  ██   ██    ██ ██   ██   #
# ██   ██  ██   ██    ██ ██       ██ ██       ██       ██   ██    ██ ██   ██   #
# ████████ ████████  ███ ███      ████████    ███      ████████  ███ ███████   #
# ███  ███ ███  ███  ███ ███      ███  ███    ███      ███  ███  ███ ███       #
# ███  ███ ███  ███  ███ ███      ███  ███    ███      ███  ███  ███ ███       #
# ███  ███ ███  ███  ███ ███  ███ ███  ███    ███  ███ ███  ███  ███ ███       #
# ████████ ███  ███  ███ ████████ ███  ███    ████████ ███  ███  ███ ███       #
#                                                                              #
################################################################################
```

**Project:** PathMiner  
**Copyright:** © 2026 brickChip and Richard Howlett. All rights reserved.  
**Owner / Author:** Richard Howlett · rhowlett@eenerd.com

All source code, documentation and other files in this project are licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE) (SPDX: `PolyForm-Noncommercial-1.0.0`).

- **Free** to use, copy, modify and share for any noncommercial purpose: personal, hobby, research, education.
- **Commercial use** requires a separate written license. This includes selling it, building it into a product or paid service, or using it in for-profit work. Contact rhowlett@eenerd.com.
- **No warranty, no liability.** It is provided as is. As far as the law allows, the owner is not responsible for any damage or loss arising from its use (see *No Liability* in LICENSE).

### Entry points

Every file that starts something in this project carries a `BRICKCHIP-ENTRY-POINT` line, so `grep -rn BRICKCHIP-ENTRY-POINT .` lists them all:

| File | Runs |
|---|---|
| `validate_package.py` | Verify package files against PACKAGE_MANIFEST.json |
| `.session_tools/activate` | Source to activate the shared venv and the session tools |
| `.session_tools/advance_session` | Validate an integrated session, assign the next, launch its worktree |
| `.session_tools/package_session_review` | Create the Git report and bundle for session review |
| `.session_tools/sanity_check` | Preflight a PathMiner Claude implementation session |
| `.session_tools/start_claude` | Validate and launch the assigned Claude model for a session |
| `workspace/pathminer/cli/__init__.py` | pathminer command-line interface (console script) |
| `workspace/tests/baseline/regression_compare.py` | Compare selftest and report output with the v0.13 golden fixtures |
| `workspace/tools/build_single_file.py` | Generate the single-file PathMiner distribution |
| `workspace/tools/pcb_trace_resistance.py` | PCB trace/via resistance calculator (GUI, batch report, --selftest) |

<!-- BRICKCHIP-LICENSE:END -->
