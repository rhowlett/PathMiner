#!/usr/bin/env python3
# v0.1
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
#  File      : validate_package.py
#  Copyright : (c) 2026 brickChip and Richard Howlett. All rights reserved.
#  Author    : Richard Howlett <rhowlett@eenerd.com>
#  License   : PolyForm Noncommercial 1.0.0. Free for noncommercial use;
#              commercial use requires written permission from the owner.
#              Full terms in LICENSE at the project root.
#  Warranty  : None. Provided as is; the owner is not liable for any
#              damages arising from its use (No Liability, LICENSE).
#  BRICKCHIP-ENTRY-POINT: Verify package files against PACKAGE_MANIFEST.json
#  SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
################################################################################

import hashlib
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
manifest_path = root / "PACKAGE_MANIFEST.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
failures = []
for item in manifest["files"]:
    path = root / item["path"]
    if not path.is_file():
        failures.append(f"missing: {item['path']}")
        continue
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != item["sha256"]:
        failures.append(f"checksum: {item['path']}")

prompt_dir = root / "workspace" / ".ai" / "prompts" / "claude"
prompts = sorted(prompt_dir.glob("Session_*_Claude_*.md"))
if len(prompts) != 34:
    failures.append(f"expected 34 Claude prompts, found {len(prompts)}")

if failures:
    print("Package validation FAILED")
    for failure in failures:
        print(f"- {failure}")
    sys.exit(1)
print(f"Package validation passed: {len(manifest['files'])} files, {len(prompts)} Claude prompts")
