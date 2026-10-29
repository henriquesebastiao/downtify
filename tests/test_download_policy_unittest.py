import sqlite3
import unittest

import pytest

from downtify.download_policy import DownloadPolicy, DownloadPolicyBlocked


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.now = 0.0
        self.song = {
            'song_id': 'TrackABC',
            'name': 'Home (Jedi Knights Remix)',
            'artist': 'Depeche Mode',
            'album': 'Ultra',
            'duration': 424,
        }
        self.policy = DownloadPolicy(self.connect, clock=lambda: self.now)

    def tearDown(self):
        self.db.close()

    def connect(self):
        return self.db

    def test_cumulative_budget_excludes_time_between_attempts(self):
        attempt = self.policy.begin(self.song, 3600)
        self.now = 1200
        attempt.finish(successful=False)
        self.now = 100000
        attempt = self.policy.begin(self.song, 3600)
        self.now += 2399
        attempt.check(force=True)
        self.now += 1
        with pytest.raises(DownloadPolicyBlocked):
            attempt.check(force=True)
        attempt.finish(successful=False)
        assert self.policy.blocked(self.song)
        assert self.policy.exclusions()[0]['reason'] == 'timeout'

    def test_manual_exclusion_respects_recording_version(self):
        ident = self.policy.suppress(self.song, user_id=1)['id']
        variant = dict(
            self.song,
            song_id='another',
            album='Other',
            name='Home (Jedi Knights Remix) (feat. Jedi Knights)',
        )
        assert self.policy.blocked(variant)
        assert not self.policy.blocked(dict(variant, name='Home (Live)'))
        self.policy.resume(ident)
        assert not self.policy.blocked(variant)

    def test_success_resets_budget_and_concurrent_attempts_rejected(self):
        attempt = self.policy.begin(self.song, 3600)
        with pytest.raises(DownloadPolicyBlocked):
            self.policy.begin(self.song, 3600)
        self.now = 500
        attempt.finish(successful=True)
        next_attempt = self.policy.begin(self.song, 3600)
        assert next_attempt.base == 0
        next_attempt.finish(successful=False)

    def test_resume_waits_until_previous_attempt_has_stopped(self):
        attempt = self.policy.begin(self.song, 3600)
        ident = self.policy.suppress(self.song, user_id=1)['id']
        with pytest.raises(ValueError, match='attempt_still_stopping'):
            self.policy.resume(ident)
        attempt.finish(successful=False)
        self.policy.resume(ident)
        assert not self.policy.blocked(self.song)

    def test_track_ids_are_case_sensitive_and_url_not_stored(self):
        self.policy.suppress(self.song, user_id=1)
        other = dict(self.song, song_id='trackabc', name='Different recording')
        assert not self.policy.blocked(other)
        song = dict(
            self.song,
            song_id='https://example.test/?token=secret',
            name='Other song',
        )
        self.policy.suppress(song, user_id=1)
        with self.connect() as conn:
            assert 'secret' not in str([
                tuple(row)
                for row in conn.execute('SELECT * FROM download_policy')
            ])


if __name__ == '__main__':
    unittest.main()
