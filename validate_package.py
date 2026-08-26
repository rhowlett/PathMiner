#!/usr/bin/env python3
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
