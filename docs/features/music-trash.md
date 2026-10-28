# Music trash (operator opt-in)

This feature requires explicit operator configuration. It is not enabled for
existing deployments. Administrators confirm the exact files selected, move
them into a private `.downtify-trash` folder in their collection and restore
them during the next 30 days. The retention clock starts after a successful
move, not when the request is queued. There is no early-empty action.

Audio and track-specific sidecars move together. Shared artwork and other
MP3/FLAC versions are not automatically included. Originals are revalidated
against fingerprints; restoration collisions never overwrite an existing file.
Library IDs, favourites and playlist associations are retained for restoration.
The tombstone continues to prevent automatic downloads after expiration until
the administrator explicitly permits them again.

## Operator configuration

Set `DOWNTIFY_TRASH_CONFIG` to a private JSON configuration file with this schema:

```json
{"version":1,"roots":{"downloads":{"path":"/downloads"}}}
```

Each root is explicitly allowlisted. Roots on removable/network storage should
also specify `marker` (a relative marker filename) and `marker_value` (its expected
contents). Include only collections that the operator deliberately authorizes.
Do not expose configuration through the API. Keep external application mounts
read-only and mount the same roots writable only into the separate worker.
The worker rechecks the administrator in a read-only authentication database:

```sh
python -m downtify.trash_worker --config /config/trash-roots.json --database /data/library.db --auth-database /data/auth.db --limit 1
```

Use the actual library and auth database locations for the installation. The
operator must schedule this bounded worker with a fixed allowlist, no network,
no Docker socket, resource limits, and defer it while affected files are being
played, scanned or written. Failed or interrupted work remains recoverable in
the journal; do not delete its database or switch to an older server with
unrestored files. Review pending operations before changing worker configuration.

The implementation requires Linux atomic no-replace moves and directory file
descriptors. Unsupported filesystems fail closed. Trash folders contain `.ignore`
for Jellyfin and are excluded from Downtify scans and audio resolution.

## API

All routes are under `/api/v1/library/trash`. `GET /capabilities` returns
`can_manage` and `retention_days`. Only authenticated administrator sessions or
paired administrator devices may preview, confirm, list, restore or retry.

`POST /preview` accepts `files` and/or `track_ids`, returns 202 with `request_id`;
poll `GET /preview/{request_id}` for the account-bound confirmation token.
`POST /confirm` accepts `{confirmation}`. `GET /` lists operations; `POST /restore`
and `/retry` accept `{ids}`. `/exclusions` and `/allow-download` manage explicit
post-expiration download permission. Operations are asynchronous; pending is
not a claim that the physical move has already succeeded.

## Review status

The generic worker scheduling contract, disabled-feature UI and full-suite
integration need review before upstream merge. This contribution is a draft,
not an invitation to enable deletion without configuring and testing the worker.
