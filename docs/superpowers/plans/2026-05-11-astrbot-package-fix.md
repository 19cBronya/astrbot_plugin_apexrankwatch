# AstrBot Plugin Package Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce an AstrBot-uploadable plugin zip with a stable top-level directory entry, bump the plugin version, and verify the archive installs cleanly.

**Architecture:** Keep the plugin source tree unchanged except for the version bump. Add a small packaging helper that emits a zip with an explicit `astrbot_plugin_apexrankwatch/` root directory entry before any files so AstrBot's archive resolver sees the correct package root. Validate the archive by inspecting `namelist()` order and checking the root directory is first.

**Tech Stack:** Python `zipfile`, PowerShell for local verification, AstrBot plugin metadata.

---

### Task 1: Bump the plugin version

**Files:**
- Modify: `E:\OneDrive\appdata\codex\astrbot_plugin_apexrankwatch\metadata.yaml`

- [ ] **Step 1: Update the version**

```yaml
version: 2.1.9
```

- [ ] **Step 2: Verify the metadata is still valid YAML**

Run: `Get-Content 'E:\OneDrive\appdata\codex\astrbot_plugin_apexrankwatch\metadata.yaml'`
Expected: `version` is `2.1.9` and other fields are unchanged.

### Task 2: Add a deterministic AstrBot zip builder

**Files:**
- Create: `E:\OneDrive\appdata\codex\astrbot_plugin_apexrankwatch\scripts\build_astrbot_zip.py`

- [ ] **Step 1: Write the zip builder**

```python
from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_NAME = "astrbot_plugin_apexrankwatch_2.1.9.zip"
ROOT_DIR_NAME = "astrbot_plugin_apexrankwatch"
OUT_PATH = Path.home() / "Desktop" / ARCHIVE_NAME
EXCLUDE_DIRS = {".git", ".pytest_cache", "__pycache__", ".mypy_cache", ".ruff_cache"}
EXCLUDE_FILES = {ARCHIVE_NAME}


def iter_payload_files():
    for path in sorted(ROOT.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(ROOT)
        if rel.parts[0] in EXCLUDE_DIRS:
            continue
        if rel.name in EXCLUDE_FILES:
            continue
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        yield rel


def build_zip() -> Path:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(ROOT_DIR_NAME + "/", "")
        for rel in iter_payload_files():
            zf.write(ROOT / rel, ROOT_DIR_NAME + "/" + rel.as_posix())
    return OUT_PATH


if __name__ == "__main__":
    print(build_zip())
```

- [ ] **Step 2: Verify the builder emits the root directory entry first**

Run: `python scripts/build_astrbot_zip.py`
Expected: The printed path points to `C:\Users\z\Desktop\astrbot_plugin_apexrankwatch_2.1.9.zip`.

### Task 3: Validate the archive shape

**Files:**
- Test: `C:\Users\z\Desktop\astrbot_plugin_apexrankwatch_2.1.9.zip`

- [ ] **Step 1: Check the first archive entry**

Run:
```python
import zipfile
with zipfile.ZipFile(r"C:\Users\z\Desktop\astrbot_plugin_apexrankwatch_2.1.9.zip") as zf:
    print(zf.namelist()[:5])
```
Expected: The first entry is `astrbot_plugin_apexrankwatch/`.

- [ ] **Step 2: Confirm AstrBot can install the zip**

Install the zip in AstrBot's plugin manager.
Expected: No `NotADirectoryError`, and the plugin loads normally.
