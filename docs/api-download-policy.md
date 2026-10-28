# Administrative download policy API

Browser sessions and paired devices require a currently valid administrator.
All endpoints live under `/api/v1/download-policy`.

- `GET /exclusions`: `{items: [...]}` with persisted blocked recordings.
- `POST /exclusions`: recording with `name`, optional `song_id`, `artist`,
  `artists`, `album_name`, and `duration` in seconds. Returns its exclusion ID.
  Insufficient identity returns 422; no file is removed.
- `DELETE /exclusions/{id}`: explicitly allow future attempts and reset elapsed
  time. Returns `{ok: true}`; 404 for unknown IDs, 409 while an attempt is stopping.

`download_retry_budget_minutes` in native settings accepts 0–1440, default 0.
