import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from downtify.db.core import Database
from downtify.library_trash import LibraryTrash, TrashRoot
from tests.db.helpers import execute


class WorkerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.music = self.base / 'music'
        self.music.mkdir()
        (self.music / '.marker').write_text('expected')
        self.audio = self.music / 'test.flac'
        self.audio.write_bytes(b'synthetic audio')
        self.lyrics = self.music / 'test.lrc'
        self.lyrics.write_text('[00:01.00] synthetic')
        self.db = self.base / 'library.db'
        self.auth = self.base / 'auth.db'
        auth = Database.sqlite(self.auth)
        execute(auth, 'CREATE TABLE users (id INTEGER PRIMARY KEY, role TEXT)')
        execute(auth, "INSERT INTO users VALUES (1, 'admin')")
        self.config = self.base / 'roots.json'
        self.config.write_text(
            json.dumps({
                'version': 1,
                'roots': {
                    'music': {
                        'path': str(self.music),
                        'marker': '.marker',
                        'marker_value': 'expected',
                    }
                },
            })
        )
        self.store = LibraryTrash(
            self.db, {'music': TrashRoot(self.music, '.marker', 'expected')}
        )
        track = {
            'stored': 'test.flac',
            'root_key': 'music',
            'relative': 'test.flac',
            'track_id': 'id',
            'metadata': {
                'title': 'Test',
                'artist': 'Artist',
                'album': 'Album',
            },
        }
        preview = self.store.preview(1, [track])
        self.ident = preview['items'][0]['id']
        self.store.confirm(1, preview['confirmation'])

    def worker(self):
        result = subprocess.run(
            [
                sys.executable,
                '-m',
                'downtify.trash_worker',
                '--config',
                str(self.config),
                '--database',
                str(self.db),
                '--auth-database',
                str(self.auth),
                '--limit',
                '1',
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        return result

    def test_separate_process_moves_and_restores_selected_file_and_lyrics(
        self,
    ):
        assert json.loads(self.worker().stdout)['succeeded'] == 1
        assert not self.audio.exists()
        assert not self.lyrics.exists()
        self.store.request_restore([self.ident])
        assert json.loads(self.worker().stdout)['succeeded'] == 1
        assert self.audio.read_bytes() == b'synthetic audio'
        assert self.lyrics.read_text() == '[00:01.00] synthetic'

    def test_revoked_admin_does_not_move_file(self):
        execute(
            Database.sqlite(self.auth),
            "UPDATE users SET role='user' WHERE id=1",
        )
        assert json.loads(self.worker().stdout)['failed'] == 1
        assert self.audio.exists()


if __name__ == '__main__':
    unittest.main()
