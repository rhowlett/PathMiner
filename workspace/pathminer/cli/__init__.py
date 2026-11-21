# v0.2
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
#  Project   : PathMiner
#  File      : __init__.py
#  Copyright : (c) 2026 brickChip and Richard Howlett. All rights reserved.
#  Author    : Richard Howlett <rhowlett@eenerd.com>
#  License   : PolyForm Noncommercial 1.0.0. Free for noncommercial use;
#              commercial use requires written permission from the owner.
#              Full terms in LICENSE at the project root.
#  Warranty  : None. Provided as is; the owner is not liable for any
#              damages arising from its use (No Liability, LICENSE).
#  BRICKCHIP-ENTRY-POINT: pathminer command-line interface (console script)
#  SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
################################################################################

"""pathminer.cli — command-line entry points.

Layer contract: imports analysis, report, and storage.  No Qt.  No wx.
Provides the ``pathminer`` console script entry point and all subcommands.

Subcommands (planned for later sessions):
    gui         — launch the Qt application
    init        — initialise a .pathminer/ project directory
    validate    — validate net-selection or project JSON against schemas
    inspect     — print board facts without running an analysis
    run         — headless resistance analysis from saved inputs
    run-paths   — multi-net path analysis
    report      — render a saved analysis result
    emit-schema — write the current JSON schemas to disk
    selftest    — run the internal acceptance-vector suite
"""


def main() -> None:
    """Entry point registered in pyproject.toml [project.scripts].

    This stub exits with a clear message until the CLI is implemented
    in a later session.
    """
    import sys

    print(
        "pathminer CLI is not yet implemented (Session 02 skeleton).\n"
        "Run 'python3 tools/pcb_trace_resistance.py --help' for the v0.13 interface.",
        file=sys.stderr,
    )
    sys.exit(1)
