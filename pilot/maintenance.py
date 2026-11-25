"""Manual local backup/restore to a NEW path only; no unattended work or overwrite."""
import argparse
from contextlib import closing
import os
from pathlib import Path
import sqlite3

from .store import Store


def copy_database(source, destination, restore=False):
    source, destination = Path(source), Path(destination)
    if not source.is_file() or destination.exists():
        raise ValueError('source-must-exist-and-destination-must-be-new')
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Reserve exclusively; never overwrite owner files, including concurrent creation.
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    with closing(sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True)) as src:
        if src.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('source-integrity-failed')
        if src.execute('PRAGMA user_version').fetchone()[0] != 1:
            raise ValueError('unsupported-schema-version')
        with closing(sqlite3.connect(destination)) as target:
            src.backup(target)
    if restore:
        recovered = Store(destination)
        with recovered.tx() as db:
            db.execute('DELETE FROM sessions')
            db.execute("UPDATE runs SET outcome='failed',error='restored-snapshot',ended=? WHERE outcome='in-flight'", (recovered.clock(),))
            db.execute('UPDATE source_state SET lease=NULL,lease_until=0,next_eligible=MAX(next_eligible,?)', (recovered.clock() + 1800,))
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('backup', 'restore'))
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    copy_database(args.source, args.destination, restore=args.command == 'restore')
    print('New private database copy verified. No original file overwritten.')


if __name__ == '__main__':
    main()
