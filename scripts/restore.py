from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def restore_backup(backup_dir: Path, data_dir: Path, *, force: bool) -> list[Path]:
    manifest_path = backup_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != 1:
        raise RuntimeError("Unsupported backup format")

    restored: list[Path] = []
    for item in manifest.get("files", []):
        relative = Path(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError(f"Unsafe path in manifest: {relative}")
        source = (backup_dir / relative).resolve()
        if backup_dir.resolve() not in source.parents:
            raise RuntimeError(f"Backup file escapes backup directory: {relative}")
        if sha256(source) != item["sha256"]:
            raise RuntimeError(f"Checksum mismatch: {relative}")
        destination = data_dir / relative
        if destination.exists() and not force:
            raise RuntimeError(f"Refusing to overwrite {destination}; pass --force")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        restored.append(destination)
    return restored


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify and restore an Observa backup")
    parser.add_argument("backup_dir", type=Path)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    restored = restore_backup(
        args.backup_dir.resolve(), args.data_dir.resolve(), force=args.force
    )
    print(f"Restored {len(restored)} database(s)")


if __name__ == "__main__":
    main()
