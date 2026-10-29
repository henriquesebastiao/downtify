"""Durable receipts and atomic reference relinking for audio replacements."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .sqlite_utils import connect_sqlite

_LINKED = ('linked', 'retained', 'removed', 'complete')


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def replacement_for_id(
    conn: sqlite3.Connection, track_id: str
) -> Optional[dict[str, Any]]:
    """Compatibility for a previously issued mobile id, without a feed duplicate."""
    try:
        row = conn.execute(
            """SELECT r.new_metadata FROM library_audio_sync_aliases a
               JOIN library_audio_replacements r ON r.old_file = a.old_file
               WHERE a.track_id = ? AND r.state IN ('linked','retained','removed','complete')""",
            (track_id,),
        ).fetchone()
    except sqlite3.OperationalError as exc:
        if 'no such table' in str(exc):
            return None
        raise
    return json.loads(row[0]) if row else None


class AudioReplacementStore:
    """Operation state only; never an audio backup or an age-based cleanup list."""

    def __init__(self, db_path: Path) -> None:
        self.path = str(db_path)
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS library_audio_replacements (
                old_file TEXT PRIMARY KEY,
                run_id INTEGER NOT NULL,
                new_file TEXT NOT NULL,
                old_key TEXT NOT NULL,
                new_key TEXT NOT NULL,
                old_sha TEXT NOT NULL,
                new_sha TEXT NOT NULL,
                new_metadata TEXT NOT NULL,
                catalog TEXT NOT NULL,
                delete_original INTEGER NOT NULL DEFAULT 0,
                state TEXT NOT NULL DEFAULT 'prepared',
                detail TEXT NOT NULL DEFAULT '',
                source_deleted INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )""")
            db.execute(
                'CREATE INDEX IF NOT EXISTS idx_audio_replacement_run ON library_audio_replacements(run_id)'
            )
            db.execute("""CREATE TABLE IF NOT EXISTS library_audio_sync_aliases (
                track_id TEXT PRIMARY KEY,
                old_file TEXT NOT NULL
            )""")

    def connect(self) -> sqlite3.Connection:
        return connect_sqlite(self.path, row_factory=True)

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        out = dict(row)
        out['new_metadata'] = json.loads(out['new_metadata'])
        out['catalog'] = json.loads(out['catalog'])
        return out

    def get(self, old_file: str) -> Optional[dict[str, Any]]:
        with self.connect() as db:
            row = db.execute(
                'SELECT * FROM library_audio_replacements WHERE old_file = ?',
                (old_file,),
            ).fetchone()
        return self._row(row) if row else None

    def save_prepared(self, receipt: dict[str, Any]) -> None:
        """Insert once; a changed original must never silently replace its receipt."""
        values = {**receipt, 'updated_at': _now()}
        values['new_metadata'] = json.dumps(values['new_metadata'])
        values['catalog'] = json.dumps(values['catalog'])
        with self.connect() as db:
            db.execute(
                """INSERT INTO library_audio_replacements
                (old_file, run_id, new_file, old_key, new_key, old_sha, new_sha,
                 new_metadata, catalog, delete_original, updated_at)
                VALUES (:old_file,:run_id,:new_file,:old_key,:new_key,:old_sha,:new_sha,
                        :new_metadata,:catalog,:delete_original,:updated_at)""",
                values,
            )

    def reuse(self, old_file: str, run_id: int, delete_original: bool) -> None:
        with self.connect() as db:
            db.execute(
                """UPDATE library_audio_replacements
                SET run_id = ?, delete_original = ?, updated_at = ? WHERE old_file = ?""",
                (run_id, int(delete_original), _now(), old_file),
            )

    def for_run(self, run_id: int) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                'SELECT * FROM library_audio_replacements WHERE run_id = ? ORDER BY old_file',
                (run_id,),
            ).fetchall()
        return [self._row(row) for row in rows]

    def mark(
        self,
        old_file: str,
        state: str,
        detail: str = '',
        *,
        deleted: bool = False,
    ) -> None:
        with self.connect() as db:
            db.execute(
                """UPDATE library_audio_replacements
                SET state = ?, detail = ?, source_deleted = MAX(source_deleted, ?),
                    updated_at = ? WHERE old_file = ?""",
                (state, detail[:200], int(deleted), _now(), old_file),
            )

    def path_alias(self, stored: str) -> Optional[str]:
        with self.connect() as db:
            row = db.execute(
                """SELECT new_file FROM library_audio_replacements
                WHERE old_file = ? AND state IN ('linked','retained','removed','complete')""",
                (stored,),
            ).fetchone()
        return str(row[0]) if row else None

    def summary(self, run_id: int) -> dict[str, int]:
        with self.connect() as db:
            rows = db.execute(
                """SELECT state, source_deleted, count(*) FROM library_audio_replacements
                WHERE run_id = ? GROUP BY state, source_deleted""",
                (run_id,),
            ).fetchall()
        totals = {
            'prepared': 0,
            'linked': 0,
            'removed': 0,
            'retained': 0,
            'blocked': 0,
        }
        for state, deleted, count in rows:
            if deleted:
                totals['removed'] += count
            elif state == 'complete':
                totals['retained'] += count
            elif state in totals:
                totals[state] += count
        return totals

    def assert_relinked(self, receipts: list[dict[str, Any]]) -> None:
        """Fail closed if authoritative tables still reference an old path."""
        with self.connect() as db:
            tables = {
                row[0]
                for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            for table, column in (
                ('library_tracks', 'filename'),
                ('playlist_tracks', 'filename'),
                ('liked_tracks', 'stored_path'),
                ('track_owners', 'stored_path'),
                ('hidden_library_items', 'item_path'),
            ):
                if table not in tables:
                    continue
                paths = [r['old_file'] for r in receipts]
                for start in range(0, len(paths), 400):
                    chunk = paths[start : start + 400]
                    marks = ','.join('?' * len(chunk))
                    if db.execute(
                        f'SELECT 1 FROM {table} WHERE {column} IN ({marks}) LIMIT 1',
                        chunk,
                    ).fetchone():
                        raise ValueError(
                            'Old library references remain; cleanup blocked'
                        )

    def relink(self, receipts: list[dict[str, Any]]) -> None:
        """Update authoritative references together, after M3U publication.

        A temporary indexed mapping avoids one full table scan per track.
        All source files still exist. A rollback leaves those references
        intact and a durable prepared receipt for retry.
        """
        if not receipts:
            return
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute("""CREATE TEMP TABLE audio_relink (
                old_file TEXT PRIMARY KEY,new_file TEXT NOT NULL,
                old_key TEXT NOT NULL,new_key TEXT NOT NULL,
                title TEXT,artist TEXT,duration REAL
            )""")
            db.executemany(
                'INSERT INTO audio_relink VALUES (?,?,?,?,?,?,?)',
                [
                    (
                        r['old_file'],
                        r['new_file'],
                        r['old_key'],
                        r['new_key'],
                        r['new_metadata'].get('title', ''),
                        r['new_metadata'].get('artist', ''),
                        r['new_metadata'].get('duration', 0),
                    )
                    for r in receipts
                ],
            )
            db.execute(
                'CREATE INDEX audio_relink_old_key ON audio_relink(old_key)'
            )
            tables = {
                row[0]
                for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            for table in ('library_tracks', 'playlist_tracks'):
                if table in tables:
                    db.execute(f"""UPDATE {table} SET
                        filename = (SELECT new_file FROM audio_relink WHERE old_file = {table}.filename),
                        content_key = (SELECT new_key FROM audio_relink WHERE old_file = {table}.filename)
                        WHERE filename IN (SELECT old_file FROM audio_relink)""")
            if 'navidrome_tracks' in tables:
                # These are cached server IDs, not authoritative playlist
                # memberships. The new recording needs a fresh lookup.
                db.execute(
                    'DELETE FROM navidrome_tracks WHERE filename IN (SELECT old_file FROM audio_relink)'
                )
            if 'liked_tracks' in tables:
                db.execute("""INSERT INTO liked_tracks
                    (stored_path,user_id,content_key,title,artist,duration,liked_at)
                    SELECT m.new_file,l.user_id,m.new_key,m.title,m.artist,m.duration,l.liked_at
                    FROM liked_tracks l JOIN audio_relink m ON l.stored_path=m.old_file
                    WHERE 1
                    ON CONFLICT(user_id,stored_path) DO UPDATE SET
                      content_key=excluded.content_key,title=excluded.title,
                      artist=excluded.artist,duration=excluded.duration,
                      liked_at=MIN(liked_tracks.liked_at,excluded.liked_at)""")
                db.execute(
                    'DELETE FROM liked_tracks WHERE stored_path IN (SELECT old_file FROM audio_relink)'
                )
            if 'track_owners' in tables:
                db.execute("""CREATE TEMP TABLE audio_owners AS
                    SELECT m.new_key,o.user_id,o.added_at,m.new_file
                    FROM track_owners o JOIN audio_relink m
                    ON o.stored_path=m.old_file OR (o.stored_path='' AND o.content_key=m.old_key)""")
                db.execute(
                    'DELETE FROM track_owners WHERE stored_path IN (SELECT old_file FROM audio_relink)'
                )
                db.execute("""DELETE FROM track_owners WHERE stored_path='' AND content_key IN
                    (SELECT old_key FROM audio_relink)""")
                db.execute(
                    'INSERT OR IGNORE INTO track_owners(content_key,user_id,added_at,stored_path) SELECT * FROM audio_owners'
                )
                db.execute("""UPDATE track_owners SET stored_path=(SELECT new_file FROM audio_owners a
                    WHERE a.new_key=track_owners.content_key AND a.user_id=track_owners.user_id LIMIT 1)
                    WHERE EXISTS(SELECT 1 FROM audio_owners a WHERE a.new_key=track_owners.content_key AND a.user_id=track_owners.user_id)""")
            if 'hidden_library_items' in tables:
                db.execute("""CREATE TEMP TABLE audio_hidden AS
                    SELECT h.kind,m.new_key,m.new_file,h.label,h.detail,h.hidden_at
                    FROM hidden_library_items h JOIN audio_relink m
                    ON h.item_path=m.old_file OR (h.item_path='' AND h.item_key=m.old_key)
                    WHERE h.kind='track'""")
                db.execute("""DELETE FROM hidden_library_items WHERE kind='track'
                    AND item_path IN (SELECT old_file FROM audio_relink)""")
                db.execute("""DELETE FROM hidden_library_items WHERE kind='track' AND item_path=''
                    AND item_key IN (SELECT old_key FROM audio_relink)""")
                db.execute(
                    'INSERT OR IGNORE INTO hidden_library_items(kind,item_key,item_path,label,detail,hidden_at) SELECT * FROM audio_hidden'
                )
                db.execute("""UPDATE hidden_library_items SET item_path=(SELECT new_file FROM audio_hidden a WHERE a.new_key=hidden_library_items.item_key LIMIT 1)
                    WHERE kind='track' AND item_key IN (SELECT new_key FROM audio_hidden)""")
            if 'sync_tracks' in tables:
                db.execute("""INSERT OR REPLACE INTO library_audio_sync_aliases(track_id,old_file)
                    SELECT s.track_id,m.old_file FROM sync_tracks s JOIN audio_relink m
                    ON s.path=m.old_file OR (s.path IS NULL AND s.content_key=m.old_key
                    AND (SELECT count(*) FROM audio_relink a WHERE a.old_key=m.old_key)=1)""")
            db.execute(
                """UPDATE library_audio_replacements SET state='linked',detail='',updated_at=?
                WHERE old_file IN (SELECT old_file FROM audio_relink)""",
                (_now(),),
            )
