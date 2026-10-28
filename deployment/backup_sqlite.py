"""Online SQLite backup with WAL support and a restore mapping (no secrets)."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3


def online_copy(source: Path, destination: Path):
    if not source.is_file():
        raise ValueError('backup source missing')
    if destination.exists():
        raise ValueError('backup destination already exists')
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Read-only URI fails rather than creating an empty source if it disappears.
    with sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True) as original:
        with sqlite3.connect(destination) as copy:
            original.backup(copy)
            result = copy.execute('PRAGMA integrity_check').fetchone()[0]
            if result != 'ok':
                raise ValueError('backed-up database integrity check failed')


def backup_databases(main_database: Path, var_dir: Path, output: Path):
    output = output.resolve(strict=True)
    var_dir = var_dir.resolve(strict=True)
    main_database = main_database.resolve(strict=True)
    online_copy(main_database, output / 'qros.db')
    mapping = [{'source': str(main_database), 'backup': 'qros.db', 'kind': 'main'}]
    candidates = sorted({p for suffix in ('*.db', '*.sqlite', '*.sqlite3') for p in var_dir.rglob(suffix)})
    for candidate in candidates:
        relative = candidate.relative_to(var_dir)
        if 'backups' in relative.parts or candidate.is_symlink() or candidate.resolve() == main_database:
            continue
        resolved = candidate.resolve(strict=True)
        # Do not follow a symlink/junction in any ancestor to an unrelated tree.
        if not resolved.is_relative_to(var_dir):
            continue
        destination = output / 'auxiliary' / relative
        online_copy(resolved, destination)
        mapping.append({'source': str(resolved), 'backup': destination.relative_to(output).as_posix(),
                        'kind': 'auxiliary'})
    (output / 'backup_manifest.json').write_text(json.dumps({'databases': mapping,
        'integrity_checked': True, 'cross_database_atomic_snapshot': False}, indent=2), encoding='utf-8')
    return mapping


if __name__ == '__main__':
    import os
    import sys
    from sqlalchemy.engine import make_url
    project = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project / 'backend'))
    from qros.config.settings import Settings
    database = make_url(Settings().database_url)
    if not database.drivername.startswith('sqlite') or not database.database or database.database == ':memory:':
        raise ValueError('Use native database backup tooling for non-file SQLite deployments')
    backups = backup_databases(Path(database.database), project / 'var',
                               Path(os.environ['QROS_BACKUP_DESTINATION']))
    print(f'Integrity-checked online backups completed for {len(backups)} databases')
