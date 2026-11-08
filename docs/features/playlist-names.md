# Playlist display names

Use **Rename** on an imported or synchronized playlist to choose its name
inside Downtify. This changes its display name only: the source URL, source
identifier, files, sharing permissions and synchronization remain unchanged.
Subsequent synchronization keeps the custom label. **Restore source name**
removes it. Downtify does not rename the playlist on Spotify, YouTube or Deezer.

Only the owner or an administrator may rename a playlist. Liked songs keep
their reserved name. Names must be nonempty, at most 120 characters and must
not collide with another playlist visible to the owner.

Locally created playlists retain their existing rename behavior.
The mobile playlist response adds `display_name`; `name` remains the stable
lookup key. Compatible clients should display the label and keep using `name`
for API requests. Older clients continue using the original name.
