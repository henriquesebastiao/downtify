from downtify.library_sync import public_row


def test_genre_change_updates_revision_without_changing_track_identity():
    entry = {'file': 'a.mp3', 'title': 'T', 'artist': 'A', 'genre': 'Rock'}
    original = dict(entry)
    rock = public_row(entry)
    jazz = public_row({**entry, 'genre': 'Jazz'})

    assert rock['file'] == jazz['file']
    assert rock['genre'] == 'Rock'
    assert jazz['genre'] == 'Jazz'
    assert rock['revision'] != jazz['revision']
    assert entry == original


def test_genre_revision_uses_the_bounded_value_sent_to_clients():
    entry = {'file': 'a.mp3', 'title': 'T', 'artist': 'A'}
    bounded = public_row({**entry, 'genre': 'x' * 512})
    longer = public_row({**entry, 'genre': 'x' * 513})

    assert len(longer['genre']) == 512
    assert longer == bounded
