from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def backup_database(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as source_connection, sqlite3.connect(destination) as target:
        source_connection.backup(target)


def create_backup(data_dir: Path, output_dir: Path, retention: int) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = output_dir / f"observa-{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=False)

    files: list[dict[str, str | int]] = []
    for source in sorted(data_dir.rglob("*.db")):
        if output_dir == source or output_dir in source.parents:
            continue
        relative = source.relative_to(data_dir)
        destination = backup_dir / relative
        backup_database(source, destination)
        files.append(
            {
                "path": relative.as_posix(),
                "sha256": sha256(destination),
                "bytes": destination.stat().st_size,
            }
        )

    if not files:
        shutil.rmtree(backup_dir)
        raise RuntimeError(f"No SQLite databases found under {data_dir}")

    manifest = {
        "format": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(data_dir.resolve()),
        "includes_secrets": False,
        "files": files,
    }
    (backup_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    backups = sorted(
        (item for item in output_dir.glob("observa-*") if item.is_dir()),
        key=lambda item: item.name,
        reverse=True,
    )
    for expired in backups[max(1, retention) :]:
        shutil.rmtree(expired)
    return backup_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a consistent Observa SQLite backup")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--retention", type=int, default=14)
    args = parser.parse_args()
    destination = create_backup(args.data_dir.resolve(), args.output_dir.resolve(), args.retention)
    print(destination)


if __name__ == "__main__":
    main()
