import sqlite3

from scripts.backup import create_backup
from scripts.restore import restore_backup


def test_backup_and_restore_round_trip(tmp_path):
    data_dir = tmp_path / "data"
    database = data_dir / "tenancies" / "tenant.db"
    database.parent.mkdir(parents=True)
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE sample(value TEXT)")
        connection.execute("INSERT INTO sample(value) VALUES ('kept')")

    backup = create_backup(data_dir, tmp_path / "backups", retention=2)
    restored_dir = tmp_path / "restored"
    restored = restore_backup(backup, restored_dir, force=False)

    assert restored == [restored_dir / "tenancies" / "tenant.db"]
    with sqlite3.connect(restored[0]) as connection:
        assert connection.execute("SELECT value FROM sample").fetchone()[0] == "kept"
