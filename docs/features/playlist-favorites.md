# Favorite playlists

Use **Add playlist to favorites** in a playlist's menu to pin it to the top
of playlist lists and the home screen. Remove it using the same menu.

Favorites belong to your account and are shared across web and compatible
mobile clients. They are separate from liked songs and following a public
playlist. You can favorite any playlist you can open. Favoriting does not
grant access: a private or removed playlist is no longer displayed.

Renaming a local playlist preserves its favorites. Deleting the playlist
or account removes its saved preference. Existing playlists start unpinned.

The mobile contract adds `favorite` to `GET /api/v1/playlists`, and
`PUT /api/v1/playlists/favorite` accepts `{name, favorite}`. Older clients
may ignore the extra field. The equivalent web route is
`PUT /api/library/playlists/favorite`.
