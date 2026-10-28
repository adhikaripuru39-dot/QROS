import importlib.util
from pathlib import Path
import sqlite3

import pytest

spec = importlib.util.spec_from_file_location('backup_sqlite', Path(__file__).resolve().parents[2] / 'deployment' / 'backup_sqlite.py')
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


def test_online_backup_includes_committed_wal_and_maps_auxiliary(tmp_path):
    var = tmp_path / 'var'
    var.mkdir()
    source = var / 'main.db'
    live = sqlite3.connect(source)
    live.execute('PRAGMA journal_mode=WAL')
    live.execute('CREATE TABLE example (value INTEGER)')
    live.execute('INSERT INTO example VALUES (42)')
    live.commit()
    paper = var / 'accounts' / 'paper.sqlite'
    paper.parent.mkdir()
    with sqlite3.connect(paper) as db:
        db.execute('CREATE TABLE positions (ticket INTEGER)')
    old = var / 'backups' / 'old'
    old.mkdir(parents=True)
    (old / 'not-a-db.sqlite').write_text('ignored')
    out = var / 'backups' / 'new'
    out.mkdir()
    mapping = backup.backup_databases(source, var, out)
    assert len(mapping) == 2
    with sqlite3.connect(out / 'qros.db') as db:
        assert db.execute('SELECT value FROM example').fetchone()[0] == 42
    assert (out / 'auxiliary' / 'accounts' / 'paper.sqlite').exists()
    assert (out / 'backup_manifest.json').exists()
    live.close()


def test_backup_refuses_missing_source_or_overwrite(tmp_path):
    missing = tmp_path / 'missing.db'
    with pytest.raises(ValueError):
        backup.online_copy(missing, tmp_path / 'copy.db')
    assert not missing.exists()
    with sqlite3.connect(missing) as db:
        db.execute('CREATE TABLE x(a INTEGER)')
    destination = tmp_path / 'existing.db'
    destination.write_text('preserve')
    with pytest.raises(ValueError):
        backup.online_copy(missing, destination)
    assert destination.read_text() == 'preserve'
