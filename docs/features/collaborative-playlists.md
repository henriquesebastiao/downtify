# Collaborative playlists

The owner can share a Library playlist with named users and allow selected
recipients to add and remove tracks. Other recipients retain playback access.
Only the owner and administrators can rename, reshare or delete the playlist.
Removing a recipient, disabling sharing, or making the playlist private revokes
editing. Public visibility alone never grants editing.

Synchronized playlists offer an independent collaborative copy. The original
playlist keeps its synchronization; collaborators change only the copy.
Edits are serialized to preserve simultaneous additions. Added tracks must be
visible to the person making the edit. The common library setting is unchanged.

Web and mobile playlist responses include `can_edit_tracks`. The visibility
endpoint accepts `editors`, a subset of the named `shared_with` recipients.
