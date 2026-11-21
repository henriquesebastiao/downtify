"""Artist Watch must not download a song the library already holds under
another name (downtify/library_songs.py, monitor.check_artist).

The names come from real data: Drake's songs as Spotify names them (a
playlist download) and as YouTube Music lists them (an artist watch).
All offline - the providers and the downloader are faked.
"""

from __future__ import annotations

import asyncio
import hashlib

from mutagen.id3 import ID3, TALB, TIT2, TPE1, TRCK

from downtify import monitor
from downtify.downloader import Downloader
from downtify.library_songs import LibrarySongs, same_recording

CHANNEL_ID = 'UCdrake0000000000000000'
#: One 32 kbps MPEG-1 Layer III frame header (frames are 104 bytes and
#: 1152 samples long at 44.1 kHz).
_FRAME_HEADER = b'\xff\xfb\x10\x64'


def _album(album_id: str, name: str) -> dict:
    return {'album_id': album_id, 'name': name, 'year': '2021'}


def _track(  # noqa: PLR0913  # mirrors a track's fields
    song_id, name, album, number, *, duration, artists=('Drake',)
):
    return {
        'song_id': song_id,
        'name': name,
        'album_name': album,
        'track_number': number,
        'artists': list(artists),
        'duration': duration,
        'source': 'youtube',
    }


def _write_track(path, song) -> None:
    """A tagged MP3 as long as *song*: the sweep checks the length of
    what it downloaded against the release."""

    path.parent.mkdir(parents=True, exist_ok=True)
    tags = ID3()
    tags.add(TIT2(encoding=3, text=[song['name']]))
    tags.add(TALB(encoding=3, text=[song['album_name']]))
    tags.add(TPE1(encoding=3, text=song['artists']))
    tags.add(TRCK(encoding=3, text=[str(song['track_number'])]))
    tags.save(path)
    seconds = float(song.get('duration') or 0)
    frames = max(4, round(seconds * 44100 / 1152))
    payload = (hashlib.sha256(path.name.encode()).digest() * 4)[:100]
    with path.open('ab') as stream:
        stream.write((_FRAME_HEADER + payload) * frames)


class _FakeDownloader:
    organize_by_artist = True
    organize_by_album = False

    def __init__(self, root, *, taken=None):
        self.download_dir = root
        # Library path of a file already holding the name a song gets.
        self.taken = taken
        self.calls: list[str] = []

    def existing_filename_for(self, song, subdir=None):
        return self.taken

    def download(self, song, progress_cb=None, subdir=None):
        if self.taken and not song.get('_output_suffix'):
            raise FileExistsError('Another release occupies the path')
        self.calls.append(song['song_id'])
        suffix = song.get('_output_suffix')
        stem = song['song_id'] + (f' ({suffix})' if suffix else '')
        filename = f'Drake/{stem}.mp3'
        _write_track(self.download_dir / filename, song)
        return filename


def _library_file(root, name: str) -> str:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'audio')
    return name


def _patch(monkeypatch, albums, tracks):
    monkeypatch.setattr(
        monitor.providers, 'artist_albums_from_channel_id', lambda _c: albums
    )
    monkeypatch.setattr(
        monitor.providers,
        'album_tracks_from_browse_id',
        lambda album_id: tracks.get(album_id, []),
    )


def _run(tmp_path, downloader, rows):
    db = monitor.PlaylistMonitorDB(tmp_path / 'monitor.db')
    watch = db.add_playlist(
        CHANNEL_ID, 'Drake', 'url', 60, monitor.KIND_ARTIST
    )
    library = (
        None if rows is None else monitor.LibraryStores(listing=lambda: rows)
    )

    async def scenario():
        async def broadcast(_message):
            return None

        return await monitor.check_artist(
            watch,
            db,
            downloader,
            broadcast,
            asyncio.get_running_loop(),
            settings={},
            library=library,
        )

    downloaded = asyncio.run(scenario())
    return downloaded, db, watch


def test_song_from_a_spotify_playlist_is_linked_not_downloaded(
    monkeypatch, tmp_path
):
    # Spotify: "(with …)" and "Future, Young Thug"; YouTube Music:
    # "(feat. …)" and "Future & Young Thug". Same song, other names.
    spotify_name = (
        'Drake/Drake, Future, Young Thug - '
        'Way 2 Sexy (with Future & Young Thug).mp3'
    )
    rows = [
        {
            'file': _library_file(tmp_path, spotify_name),
            'artist': 'Drake, Future, Young Thug',
            'title': 'Way 2 Sexy (with Future & Young Thug)',
            'duration': 257.6,
        }
    ]
    _patch(
        monkeypatch,
        [_album('CLB', 'Certified Lover Boy')],
        {
            'CLB': [
                _track(
                    'w2s',
                    'Way 2 Sexy (feat. Future & Young Thug)',
                    'Certified Lover Boy',
                    9,
                    artists=('Drake', 'Future & Young Thug'),
                    duration=257,
                ),
                _track('tsu', 'TSU', 'Certified Lover Boy', 8, duration=308),
            ]
        },
    )
    dl = _FakeDownloader(tmp_path)

    downloaded, db, watch = _run(tmp_path, dl, rows)

    assert dl.calls == ['tsu']
    assert downloaded == 1
    assert db.get_track_filenames(watch.id)['w2s'] == spotify_name
    assert db.get_seen_album_ids(watch.id) == {'CLB'}


def test_a_single_also_on_the_album_is_downloaded_once(monkeypatch, tmp_path):
    _patch(
        monkeypatch,
        [_album('S1', 'Pop Style'), _album('VIEWS', 'Views')],
        {
            'S1': [_track('s1', 'Pop Style', 'Pop Style', 1, duration=212)],
            'VIEWS': [
                _track(
                    'v13',
                    'Pop Style (feat. The Throne)',
                    'Views',
                    13,
                    duration=213,
                )
            ],
        },
    )
    dl = _FakeDownloader(tmp_path)

    _downloaded, db, watch = _run(tmp_path, dl, [])

    assert dl.calls == ['s1']
    assert db.get_seen_album_ids(watch.id) == {'S1', 'VIEWS'}


def test_a_different_recording_is_still_downloaded(monkeypatch, tmp_path):
    rows = [
        {
            'file': _library_file(tmp_path, 'Drake/Drake - Over.mp3'),
            'artist': 'Drake',
            'title': 'Over',
            'duration': 233,
        }
    ]
    _patch(
        monkeypatch,
        [_album('LIVE', 'Live')],
        {'LIVE': [_track('live', 'Over', 'Live', 1, duration=301)]},
    )
    dl = _FakeDownloader(tmp_path)

    _run(tmp_path, dl, rows)

    assert dl.calls == ['live']


def test_unknown_length_never_matches(monkeypatch, tmp_path):
    rows = [
        {
            'file': _library_file(tmp_path, 'Drake/Drake - Over.mp3'),
            'artist': 'Drake',
            'title': 'Over',
            'duration': 233,
        }
    ]
    _patch(
        monkeypatch,
        [_album('A', 'Thank Me Later')],
        {'A': [_track('o', 'Over', 'Thank Me Later', 3, duration=0)]},
    )
    dl = _FakeDownloader(tmp_path)

    _run(tmp_path, dl, rows)

    assert dl.calls == ['o']


def test_a_listed_file_that_is_gone_is_not_linked(monkeypatch, tmp_path):
    rows = [
        {
            'file': 'Drake/Drake - Over.mp3',
            'artist': 'Drake',
            'title': 'Over',
            'duration': 233,
        }
    ]
    _patch(
        monkeypatch,
        [_album('A', 'Thank Me Later')],
        {'A': [_track('o', 'Over', 'Thank Me Later', 3, duration=233)]},
    )
    dl = _FakeDownloader(tmp_path)

    _run(tmp_path, dl, rows)

    assert dl.calls == ['o']


def test_without_the_library_listing_nothing_changes(monkeypatch, tmp_path):
    _patch(
        monkeypatch,
        [_album('A', 'Views')],
        {'A': [_track('t', 'Hotline Bling', 'Views', 20, duration=267)]},
    )
    dl = _FakeDownloader(tmp_path)

    _run(tmp_path, dl, None)

    assert dl.calls == ['t']


def test_a_name_taken_by_another_recording_gets_the_album_added(
    monkeypatch, tmp_path
):
    other = _track('x', 'Intro', 'Views', 1, duration=150)
    _write_track(tmp_path / 'Drake/Drake - Intro.mp3', other)
    _patch(
        monkeypatch,
        [_album('A', 'Her Loss')],
        {'A': [_track('intro', 'Intro', 'Her Loss', 1, duration=90)]},
    )
    dl = _FakeDownloader(tmp_path, taken='Drake/Drake - Intro.mp3')

    _downloaded, db, watch = _run(tmp_path, dl, None)

    assert dl.calls == ['intro']
    assert db.get_track_filenames(watch.id)['intro'] == (
        'Drake/intro (Her Loss).mp3'
    )
    assert db.get_seen_album_ids(watch.id) == {'A'}


def test_a_name_taken_by_the_same_song_is_linked_even_without_listing(
    monkeypatch, tmp_path
):
    single = _track('s', 'Hotline Bling', 'Hotline Bling', 1, duration=267)
    _write_track(tmp_path / 'Drake/Drake - Hotline Bling.mp3', single)
    _patch(
        monkeypatch,
        [_album('V', 'Views')],
        {'V': [_track('v', 'Hotline Bling', 'Views', 20, duration=267)]},
    )
    dl = _FakeDownloader(tmp_path, taken='Drake/Drake - Hotline Bling.mp3')

    downloaded, db, watch = _run(tmp_path, dl, None)

    assert dl.calls == []
    assert downloaded == 0
    assert db.get_track_filenames(watch.id)['v'] == (
        'Drake/Drake - Hotline Bling.mp3'
    )
    assert db.get_seen_album_ids(watch.id) == {'V'}


def test_output_suffix_is_added_to_the_file_name(tmp_path):
    dl = Downloader(
        download_dir=tmp_path,
        output_template='{artists} - {title}.{output-ext}',
        organize_by_artist=True,
        organize_by_album=False,
    )
    song = {'name': 'Intro', 'artists': ['Drake'], 'album_name': 'Her Loss'}

    assert dl.expected_stem_for(song) == 'Drake/Drake - Intro'
    assert dl.expected_stem_for({**song, '_output_suffix': 'Her Loss'}) == (
        'Drake/Drake - Intro (Her Loss)'
    )


# --- LibrarySongs ----------------------------------------------------------


def _row(file: str, title: str, duration: float, artist: str = 'Drake'):
    return {
        'file': file,
        'artist': artist,
        'title': title,
        'duration': duration,
    }


def test_library_songs_prefers_a_file_outside_slskd_and_the_closest():
    songs = LibrarySongs([
        _row('slskd/x/Over.mp3', 'Over', 233),
        _row('Drake/Drake - Over.mp3', 'Over', 235),
        _row('Drake/Drake - Over (2).mp3', 'Over', 233.5),
    ])

    found = songs.find({'artists': ['Drake'], 'name': 'Over', 'duration': 233})

    assert found == 'Drake/Drake - Over (2).mp3'


def test_library_songs_needs_artist_title_and_length():
    songs = LibrarySongs([
        _row('a.mp3', 'Over', 233, artist=''),
        _row('b.mp3', '', 233),
        _row('c.mp3', 'Over', 0),
    ])
    over = {'artists': ['Drake'], 'name': 'Over', 'duration': 233}

    assert songs.find(over) is None
    assert songs.find({**over, 'artists': []}) is None


def test_library_songs_add_makes_a_new_download_findable():
    songs = LibrarySongs()
    songs.add(
        'Drake/s1.mp3',
        {'artists': ['Drake'], 'name': 'Pop Style', 'duration': 212},
    )

    found = songs.find({
        'artists': ['Drake', 'The Throne'],
        'name': 'Pop Style (feat. The Throne)',
        'duration': 213,
    })

    assert found == 'Drake/s1.mp3'


def test_same_recording_reads_the_files_own_tags(tmp_path):
    path = tmp_path / 'song.mp3'
    _write_track(path, _track('a', 'Over', 'Thank Me Later', 3, duration=233))
    over = {'artists': ['Drake'], 'name': 'Over (Live)', 'duration': 233}

    assert same_recording(path, {**over, 'name': 'Over'})
    assert not same_recording(path, {**over, 'duration': 300})
    assert not same_recording(path, {**over, 'artists': ['Someone Else']})


def test_library_songs_folds_the_album_version_tags_deezer_adds():
    songs = LibrarySongs([_row('Drake/Drake - Over.mp3', 'Over', 233)])
    over = {'artists': ['Drake'], 'duration': 233}

    for title in (
        'Over (Album Version)',
        'Over (Explicit Version)',
        'Over [Explicit]',
        'Over - Album Version',
        'Over (Original Mix)',
    ):
        assert songs.find({**over, 'name': title}) == 'Drake/Drake - Over.mp3'
    for title in ('Over (Clean)', 'Over (Radio Edit)', 'Over (Live)'):
        assert songs.find({**over, 'name': title}) is None


def test_library_songs_folds_the_film_a_song_is_from():
    # Indian labels name the film on one catalogue and not another.
    path = 'Arijit Singh/Arijit Singh - Tum Hi Ho.mp3'
    songs = LibrarySongs([_row(path, 'Tum Hi Ho', 262, 'Arijit Singh')])
    song = {'artists': ['Arijit Singh'], 'duration': 262}

    for title in (
        'Tum Hi Ho (From "Aashiqui 2")',
        'Tum Hi Ho [From "Aashiqui 2"]',
        'Tum Hi Ho (From the Motion Picture "Aashiqui 2")',
    ):
        assert songs.find({**song, 'name': title}) == path
    # Another recording of it is still another song.
    assert songs.find({**song, 'name': 'Tum Hi Ho (Unplugged)'}) is None
    assert songs.find({**song, 'name': 'Tum Hi Ho', 'duration': 320}) is None
