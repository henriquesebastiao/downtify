from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from downtify.library_catalog import LibraryContext
from downtify.manual_playlists import (
    ManualPlaylistError,
    create_manual_playlist,
)
from downtify.playlist_catalog import ManualPlaylistOwners
from downtify.playlist_shares import PUBLIC, PlaylistShares


def test_same_name_creators_serialize_file_and_owner_claim(
    tmp_path: Path,
) -> None:
    ctx = LibraryContext(download_dir=tmp_path / 'Playlists')
    owners = ManualPlaylistOwners(tmp_path / 'library.db')
    shares = PlaylistShares(tmp_path / 'library.db')
    gate = Barrier(2)

    def create(user_id: int):
        gate.wait()
        try:
            return create_manual_playlist(
                ctx, 'Shared Name', owners, user_id, shares
            )
        except ManualPlaylistError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create, (11, 22)))

    succeeded = [result for result in results if isinstance(result, dict)]
    rejected = [
        result for result in results if isinstance(result, ManualPlaylistError)
    ]
    assert len(succeeded) == 1
    assert len(rejected) == 1
    assert rejected[0].status_code == 409
    playlist_dir = ctx.download_dir / 'Playlists'
    assert list(playlist_dir.glob('*.m3u')) == [
        playlist_dir / 'Shared Name.m3u'
    ]
    assert owners.owner('Shared Name') in {11, 22}


def test_ownership_failure_rolls_back_only_new_playlist(
    tmp_path: Path,
) -> None:
    ctx = LibraryContext(download_dir=tmp_path / 'Playlists')
    owners = ManualPlaylistOwners(tmp_path / 'library.db')
    shares = PlaylistShares(tmp_path / 'library.db')
    shares.set_visibility('Unclaimed', PUBLIC)
    cover = ctx.download_dir / 'Playlists' / 'Unclaimed.jpg'
    cover.parent.mkdir(parents=True)
    cover.write_bytes(b'preexisting orphan cover')

    def fail_claim(name: str, user_id: int) -> bool:
        raise OSError('database unavailable')

    owners.claim_owner = fail_claim  # type: ignore[method-assign]
    with pytest.raises(OSError, match='database unavailable'):
        create_manual_playlist(ctx, 'Unclaimed', owners, 11, shares)

    assert not (ctx.download_dir / 'Playlists' / 'Unclaimed.m3u').exists()
    assert owners.owner('Unclaimed') is None
    assert shares.visibility('Unclaimed') == PUBLIC
    assert cover.read_bytes() == b'preexisting orphan cover'


@pytest.mark.parametrize('dependency', ['owners', 'shares'])
def test_authenticated_creation_requires_ownership_store(
    tmp_path: Path, dependency: str
) -> None:
    ctx = LibraryContext(download_dir=tmp_path / 'Playlists')
    with pytest.raises(ManualPlaylistError) as error:
        create_manual_playlist(
            ctx,
            'Unclaimed',
            owners=None if dependency == 'owners' else object(),
            user_id=11,
            shares=None if dependency == 'shares' else object(),
        )
    assert error.value.status_code == 503
    assert not (ctx.download_dir / 'Playlists' / 'Unclaimed.m3u').exists()


def test_claim_owner_never_replaces_existing_owner(tmp_path: Path) -> None:
    owners = ManualPlaylistOwners(tmp_path / 'library.db')
    assert owners.claim_owner('Mix', 11)
    assert not owners.claim_owner('mix', 22)
    assert owners.owner('MIX') == 11
