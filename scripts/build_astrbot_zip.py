from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_DIR_NAME = "astrbot_plugin_apexrankwatch"
EXCLUDE_DIRS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    "docs",
    "scripts",
    "tests",
    "_generated",
    "AstrBot",
}
EXCLUDE_FILES = {".gitignore"}


def read_metadata_value(key: str) -> str:
    prefix = f"{key}:"
    for line in (ROOT / "metadata.yaml").read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip().strip("\"'")
    raise RuntimeError(f"metadata.yaml 缺少 {key} 字段")


ARCHIVE_NAME = f"{ROOT_DIR_NAME}_{read_metadata_value('version')}.zip"
OUT_PATH = Path.home() / "Desktop" / ARCHIVE_NAME
EXCLUDE_FILES.add(ARCHIVE_NAME)


def should_include(path: Path) -> bool:
    if path.is_dir():
        return False
    rel = path.relative_to(ROOT)
    if not rel.parts:
        return False
    if rel.parts[0] in EXCLUDE_DIRS:
        return False
    if rel.name in EXCLUDE_FILES:
        return False
    if any(part in EXCLUDE_DIRS for part in rel.parts):
        return False
    return True


def build_zip() -> Path:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{ROOT_DIR_NAME}/", "")
        for path in sorted(ROOT.rglob("*")):
            if not should_include(path):
                continue
            rel = path.relative_to(ROOT).as_posix()
            zf.write(path, f"{ROOT_DIR_NAME}/{rel}")
    return OUT_PATH


if __name__ == "__main__":
    print(build_zip())
