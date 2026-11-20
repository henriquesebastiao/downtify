"""Time-synced lyrics: Kugou, LRCLIB's search fallback, the synced-only
setting, telling which tracks already have synced lyrics, and the library
upgrade's lyrics summary and "scan, then upgrade"."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import httpx
import pytest
from mutagen.id3 import ID3, SYLT, USLT

from downtify import library_upgrade, lyrics
from downtify.library_upgrade import (
    CATEGORY_LYRICS,
    STATE_DONE,
    LibraryUpgradeRunner,
    UpgradeOptions,
    options_from,
    track_findings,
)
from downtify.library_upgrade_db import LibraryUpgradeDB
from downtify.lyrics import Lyrics
from tests.test_library_upgrade import _context, _deps, _entry, _write_track
from tests.test_lyrics_providers import SONG, calls  # noqa: F401  # fixture

SYNCED = '[00:01.00]Never gonna give you up'


# ── synced only ──────────────────────────────────────────────────────


def test_synced_only_asks_on_past_plain_lyrics(calls):  # noqa: F811
    asked, answers = calls
    answers['lrclib'] = Lyrics(plain='words only')
    answers['netease'] = None
    answers['kugou'] = Lyrics(synced=SYNCED)

    found = lyrics.fetch(
        SONG, ['lrclib', 'netease', 'kugou'], synced_only=True
    )

    assert found.synced == SYNCED
    assert asked == ['lrclib', 'netease', 'kugou']
    # Without it, plain lyrics are enough.
    asked.clear()
    assert lyrics.fetch(SONG, ['lrclib', 'kugou']).plain == 'words only'
    assert asked == ['lrclib']


def test_synced_only_finds_nothing_when_no_provider_has_timestamps(calls):  # noqa: F811
    _asked, answers = calls
    answers['lrclib'] = Lyrics(plain='words only')
    assert lyrics.fetch(SONG, ['lrclib'], synced_only=True) is None


# ── Kugou ────────────────────────────────────────────────────────────


class _Response:
    def __init__(self, data: Any, status: int = 200) -> None:
        self._data = data
        self.status_code = status

    def json(self) -> Any:
        return self._data


def _kugou(monkeypatch, candidates, lrc):
    asked: list[str] = []

    def get(url, params=None, **_kwargs):
        asked.append(url)
        if url.endswith('/search'):
            return _Response({'candidates': candidates})
        content = base64.b64encode(lrc.encode()).decode()
        return _Response({'status': 200, 'content': content})

    monkeypatch.setattr(lyrics.httpx, 'get', get)
    return asked


def test_kugou_returns_synced_lyrics_without_tags_or_credits(monkeypatch):
    _kugou(
        monkeypatch,
        [
            {
                'id': '1',
                'accesskey': 'k',
                'song': 'Never Gonna Give You Up',
                'singer': 'Rick Astley',
                'duration': 213000,
            }
        ],
        '[ar:Rick Astley]\n[offset:0]\n'
        '[00:00.00]Never Gonna Give You Up - Rick Astley\n'
        '[00:00.10]作词：Stock\n[00:00.20]Written by：Stock Aitken\n'
        '[00:01.00]Never gonna give you up\n',
    )

    found = lyrics._fetch_kugou(SONG)

    assert found.synced == SYNCED
    assert found.plain == 'Never gonna give you up'


def test_kugou_rejects_another_song_or_length(monkeypatch):
    asked = _kugou(
        monkeypatch,
        [
            {
                'id': '1',
                'song': 'Something Else',
                'singer': 'Rick Astley',
                'duration': 213000,
            },
            {
                'id': '2',
                'song': 'Never Gonna Give You Up',
                'singer': 'Someone',
                'duration': 300000,
            },
        ],
        SYNCED,
    )

    assert lyrics._fetch_kugou(SONG) is None
    assert len(asked) == 1  # nothing downloaded


# ── LRCLIB search ────────────────────────────────────────────────────


def test_lrclib_searches_when_the_exact_match_has_no_timestamps(monkeypatch):
    def get(url, params=None, **_kwargs):
        if url.endswith('/get'):
            return _Response({'plainLyrics': 'words only'})
        return _Response([
            {
                'trackName': 'Never Gonna Give You Up',
                'artistName': 'Rick Astley',
                'duration': 300,
                'syncedLyrics': '[00:09.00]too long',
            },
            {
                'trackName': 'Never Gonna Give You Up (Remastered)',
                'artistName': 'Rick Astley',
                'duration': 213.4,
                'syncedLyrics': SYNCED,
            },
        ])

    monkeypatch.setattr(lyrics.httpx, 'get', get)

    assert lyrics._fetch_lrclib(SONG).synced == SYNCED


def test_lrclib_keeps_plain_lyrics_when_search_finds_nothing(monkeypatch):
    def get(url, params=None, **_kwargs):
        if url.endswith('/get'):
            return _Response({'plainLyrics': 'words only'})
        raise httpx.ConnectError('down')

    monkeypatch.setattr(lyrics.httpx, 'get', get)

    assert lyrics._fetch_lrclib(SONG).plain == 'words only'


# ── Which tracks have synced lyrics ──────────────────────────────────


def _tagged(path: Path, frame) -> Path:
    tags = ID3()
    tags.add(frame)
    tags.save(str(path), v2_version=4)
    return path


@pytest.mark.parametrize(
    ('frame', 'synced'),
    [
        (USLT(encoding=3, lang='eng', desc='', text='words only'), False),
        (USLT(encoding=3, lang='eng', desc='', text=SYNCED), True),
        (
            SYLT(
                encoding=3,
                lang='eng',
                format=2,
                type=1,
                text=[('Never gonna', 1000)],
            ),
            True,
        ),
    ],
)
def test_synced_lyrics_in_the_tags_count(tmp_path, frame, synced):
    track = _tagged(tmp_path / 'a.mp3', frame)
    assert lyrics.has_synced_lyrics(track) is synced


def test_an_lrc_sidecar_counts_as_synced(tmp_path):
    track = _tagged(
        tmp_path / 'a.mp3', USLT(encoding=3, lang='eng', desc='', text='x')
    )
    track.with_suffix('.lrc').write_text(SYNCED, encoding='utf-8')
    assert lyrics.has_synced_lyrics(track)


def test_with_synced_only_plain_lyrics_are_a_finding(tmp_path):
    ctx = _context(tmp_path)
    track = _write_track(ctx.download_dir / 'a.mp3', cover_px=1200)
    tags = ID3(str(track))
    tags.add(USLT(encoding=3, lang='eng', desc='', text='words only'))
    tags.save(str(track), v2_version=4)
    entry = _entry(ctx, 'a.mp3')

    assert CATEGORY_LYRICS not in track_findings(
        entry, track, artwork_min_px=600
    )
    assert CATEGORY_LYRICS in track_findings(
        entry, track, artwork_min_px=600, synced_only=True
    )


# ── Scan, then upgrade; the lyrics summary ───────────────────────────


def test_scan_then_upgrade_runs_and_reports_lyrics(tmp_path, monkeypatch):
    ctx = _context(tmp_path)
    for name in ('found', 'missing'):
        _write_track(ctx.download_dir / f'{name}.mp3', cover_px=1200)

    def fetch(song, *_args, synced_only=False, **_kwargs):
        assert synced_only is True
        if song['name'] == 'Track' and fetch.first:
            fetch.first = False
            return Lyrics(synced=SYNCED)
        return None

    fetch.first = True
    monkeypatch.setattr(library_upgrade.lyrics_mod, 'fetch', fetch)
    runner = LibraryUpgradeRunner(
        LibraryUpgradeDB(tmp_path / 'lib.db'),
        _deps(
            ctx,
            settings={
                'lyrics_providers': ['lrclib'],
                'lyrics_synced_only': True,
            },
        ),
    )

    runner.start_scan(
        UpgradeOptions(categories=(CATEGORY_LYRICS,), start_after_scan=True)
    )
    for _ in range(2):  # the scan's thread, then the upgrade's
        worker = runner._worker
        if worker is not None:
            worker.join(timeout=30)

    status = runner.status()
    assert status['state'] == STATE_DONE
    assert status['lyrics'] == {
        'added': 1,
        'not_found': 1,
        'failed': 0,
        'pending': 0,
    }


def test_start_after_scan_is_read_from_the_request():
    assert options_from({'start_after_scan': True}).start_after_scan
    assert not options_from({'start_after_scan': 'yes'}).start_after_scan
    assert options_from({}).as_dict().get('start_after_scan') is None


# ── Synced lyrics inside the file; swapping plain ones out ───────────


def _plain_track(ctx, name='a.mp3', text='words only'):
    track = _write_track(ctx.download_dir / name, cover_px=1200)
    tags = ID3(str(track))
    tags.add(USLT(encoding=3, lang='eng', desc='', text=text))
    tags.save(str(track), v2_version=4)
    return track


def test_synced_lyrics_in_the_tags_are_read_as_synced(tmp_path):
    track = _tagged(
        tmp_path / 'a.mp3', USLT(encoding=3, lang='eng', desc='', text=SYNCED)
    )
    assert lyrics.read_track_lyrics(track) == {
        'synced': SYNCED,
        'plain': 'Never gonna give you up',
    }
    # raw: the sidecar only, and the tag exactly as stored.
    assert lyrics.read_track_lyrics(track, raw=True) == {
        'synced': '',
        'plain': SYNCED,
    }


def test_a_sylt_frame_is_read_as_lrc(tmp_path):
    track = _tagged(
        tmp_path / 'a.mp3',
        SYLT(
            encoding=3,
            lang='eng',
            format=2,
            type=1,
            text=[('Never gonna', 1000), ('give you up', 62_340)],
        ),
    )
    assert lyrics.read_track_lyrics(track)['synced'] == (
        '[00:01.00]Never gonna\n[01:02.34]give you up'
    )


def test_a_sylt_frame_timed_in_mpeg_frames_is_ignored(tmp_path):
    track = _tagged(
        tmp_path / 'a.mp3',
        SYLT(encoding=3, lang='eng', format=1, type=1, text=[('x', 10)]),
    )
    assert not lyrics.has_synced_lyrics(track)


def test_plain_lyrics_are_shown_without_timestamps_beside_a_sidecar(tmp_path):
    track = _tagged(
        tmp_path / 'a.mp3', USLT(encoding=3, lang='eng', desc='', text=SYNCED)
    )
    track.with_suffix('.lrc').write_text('[00:02.00]Other', encoding='utf-8')
    found = lyrics.read_track_lyrics(track)
    assert found['synced'] == '[00:02.00]Other'
    assert found['plain'] == 'Never gonna give you up'


@pytest.mark.parametrize(
    ('embed_synced', 'tag'), [(False, 'plain'), (True, SYNCED)]
)
def test_embed_synced_puts_the_lrc_text_in_the_tag(
    tmp_path, embed_synced, tag
):
    track = _tagged(
        tmp_path / 'a.mp3', USLT(encoding=3, lang='eng', desc='', text='old')
    )
    lyrics.write_to_file(
        track, Lyrics(plain='plain', synced=SYNCED), embed_synced=embed_synced
    )
    frames = ID3(str(track)).getall('USLT')
    assert [str(f.text) for f in frames] == [tag]
    assert track.with_suffix('.lrc').read_text(encoding='utf-8') == SYNCED


def _run(runner, options):
    runner.start_scan(options)
    for _ in range(2):  # the scan's thread, then the upgrade's
        worker = runner._worker
        if worker is not None:
            worker.join(timeout=30)
    return runner.status()


def test_plain_lyrics_are_swapped_for_synced_ones(tmp_path, monkeypatch):
    ctx = _context(tmp_path)
    track = _plain_track(ctx)
    monkeypatch.setattr(
        library_upgrade.lyrics_mod,
        'fetch',
        lambda *_a, **_k: Lyrics(plain='words only', synced=SYNCED),
    )
    runner = LibraryUpgradeRunner(
        LibraryUpgradeDB(tmp_path / 'lib.db'),
        _deps(
            ctx,
            settings={
                'lyrics_providers': ['lrclib'],
                'lyrics_synced_only': True,
            },
        ),
    )

    status = _run(
        runner,
        UpgradeOptions(categories=(CATEGORY_LYRICS,), start_after_scan=True),
    )

    assert status['summary']['plain_lyrics_only'] == 1
    assert status['lyrics']['added'] == 1
    assert [str(f.text) for f in ID3(str(track)).getall('USLT')] == [SYNCED]
    assert lyrics.has_synced_lyrics(track)


def test_a_check_made_without_synced_only_does_not_skip_the_track(
    tmp_path, monkeypatch
):
    ctx = _context(tmp_path)
    _plain_track(ctx)
    monkeypatch.setattr(
        library_upgrade.lyrics_mod, 'fetch', lambda *_a, **_k: None
    )
    settings = {'lyrics_providers': ['lrclib']}
    runner = LibraryUpgradeRunner(
        LibraryUpgradeDB(tmp_path / 'lib.db'), _deps(ctx, settings=settings)
    )
    options = UpgradeOptions(categories=(CATEGORY_LYRICS,), recheck_days=30)

    # Plain lyrics count as lyrics: nothing to do, and remembered so.
    assert _run(runner, options)['summary']['tracks'] == 0
    assert _run(runner, options)['summary']['recently_checked'] == 1

    settings['lyrics_synced_only'] = True
    summary = _run(runner, options)['summary']
    assert summary['tracks'] == 1
    assert summary['plain_lyrics_only'] == 1


def test_plain_text_drops_lrc_header_tags(tmp_path):
    lrc = "[ti:Snooze]\n[ar:SZA]\n[offset:0]\n[00:13.00]I'll touch"
    track = _tagged(
        tmp_path / 'a.mp3', USLT(encoding=3, lang='eng', desc='', text=lrc)
    )
    assert lyrics.read_track_lyrics(track)['plain'] == "I'll touch"
