---
icon: lucide/database
---

# Database

Downtify keeps its library, playlist monitor, accounts, activity log and audio-check caches in a database. There are two backends: SQLite files on disk (the default) and PostgreSQL. Only one is active at a time, chosen by the `DATABASE_URL` environment variable.

## Choosing a backend

| | SQLite (default) | PostgreSQL (`DATABASE_URL` set) |
|---|---|---|
| Setup | Nothing to configure | A PostgreSQL server and a connection URL |
| Storage | Six `.db` files under `DATABASE_DIR` | One database for everything |
| Best for | A single user or a small library | Several parallel downloads, the playlist monitor and many clients writing at the same time |
| Schema | Created by each store on startup | Created on startup by versioned migrations |

## SQLite (default)

With `DATABASE_URL` unset, each store uses its own file under `DATABASE_DIR` (default `/data`, the `./docker/data` folder in Docker Compose):

| File | Holds |
|------|-------|
| `downtify_library.db` | Library tracks, playlists, downloads and the download queue |
| `downtify_monitor.db` | Playlist monitor state |
| `downtify_auth.db` | Users, paired devices and sign-in sessions |
| `downtify_activity.db` | Activity log and traffic counters |
| `doctor/audio_hashes.db` | Audio hashes cached by Doctor |
| `doctor/duplicates.db` | Duplicate pairs you kept apart in Doctor |

The files run in WAL mode, so each one can also have `-wal` and `-shm` companion files while the server runs.

## PostgreSQL

Set `DATABASE_URL` to a `postgres://` or `postgresql://` URL. Downtify then stores everything in that one database. On startup it applies any pending migrations (recorded in a `schema_migrations` table), so you do not create tables yourself. The migrations run under a lock, so several processes starting at once wait for each other.

```bash
DATABASE_URL=postgresql://downtify:secret@localhost:5432/downtify
```

Use a database that is empty, or one previously used by Downtify. Downtify does not create the database itself: create it first.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | unset (SQLite) | PostgreSQL URL. Must start with `postgres://` or `postgresql://`, otherwise startup fails. |
| `DATABASE_DIR` | `/data` | Data directory. Used for the SQLite files and for settings, cookies, caches and the server identity, with or without PostgreSQL. |
| `DB_POOL_MIN` | `2` | Connections kept open in the pool. Must be `0` or more. |
| `DB_POOL_MAX` | `20` | Maximum connections in the pool. Must be at least `1` and at least `DB_POOL_MIN`. |
| `DB_POOL_TIMEOUT` | `10` | Seconds to wait for a free connection before giving up. |
| `DB_SEARCH_PATH` | unset (`public`) | PostgreSQL schema to use. A plain identifier: letters, digits and underscores, not starting with a digit. |
| `POSTGRES_PASSWORD` | `downtify` | Password for the bundled `postgres` service in Docker Compose. Used to build `DATABASE_URL` in `docker-compose.yml`. |

## Docker Compose with PostgreSQL

The shipped `docker-compose.yml` includes a PostgreSQL 17 service, but it is off by default: Downtify keeps using SQLite until you turn it on.

- The `postgres` service uses the `postgres:17-alpine` image, stores its data in the named volume `pgdata` and only starts under the `postgres` Compose profile.
- To enable it, uncomment the `depends_on` block and the `DATABASE_URL` line of the `downtify` service, then start everything with `docker compose --profile postgres up -d`.
- The password comes from `POSTGRES_PASSWORD` (set it in `.env`; the default is `downtify`).
- An existing install should run `make db-migrate` first (see [Migrating an existing SQLite install](#migrating-an-existing-sqlite-install)), or it starts on an empty database.

::: warning The password is set only once
PostgreSQL reads `POSTGRES_PASSWORD` when it first creates the `pgdata` volume. Changing it later in `.env` does not change the password of an existing database. Either change it inside PostgreSQL too, or recreate the volume (this deletes the data).
:::

To go back to SQLite, comment out the `DATABASE_URL` line (and `depends_on`) again and restart it:

```bash
docker compose up -d
```

Your SQLite files under `./docker/data` are used again. Data written to PostgreSQL while it was active is not copied back; see [Rolling back](#rolling-back). Keep the `pgdata` volume until you are sure you no longer need it: `docker compose down -v` deletes it.

## Migrating an existing SQLite install

Migrating copies the data of an existing SQLite install into PostgreSQL. Do it once:

1. Stop Downtify so nothing writes to the SQLite files during the copy.
2. Run the migration against an empty PostgreSQL database:

   ```bash
   python main.py db-migrate --from-sqlite /path/to/data --to postgresql://downtify:secret@localhost:5432/downtify
   ```

   `--from-sqlite` defaults to `DATABASE_DIR` and `--to` defaults to `DATABASE_URL`, so both can be left out when they are set. In Docker, the image's entrypoint always starts the server, so run the command with `docker compose run --rm --entrypoint python downtify main.py db-migrate` instead.

3. Read the report. Every table is listed with its source rows, skipped rows, target rows and checksum result. The command exits with `0` when all tables pass and `1` otherwise.
4. Set `DATABASE_URL` and start Downtify.

What the migration does:

- **Read-only source.** The SQLite files are opened read-only and are never modified.
- **One transaction.** All tables are copied in one transaction. If anything fails, it is rolled back and PostgreSQL is left as it was.
- **Verification.** For each table it compares row counts and a checksum over the primary key (or over every column when a table has no primary key).
- **Orphans are skipped.** Old SQLite files did not enforce foreign keys. A `playlist_tracks` row whose playlist is missing is skipped and counted in the *skipped* column. Rows without a playlist name are kept.
- **Marker file.** On success it writes `MIGRATED_TO_POSTGRES` into the SQLite data directory, with the time of the migration.

::: warning Running it twice
The command refuses to run when `MIGRATED_TO_POSTGRES` already exists, or when the target already has rows. Adding `--force` repeats the copy: it **empties the PostgreSQL tables first**, so only use it when you want the SQLite data to replace what is in PostgreSQL.
:::

If you start the server in SQLite mode after migrating, while the marker exists and `DATABASE_URL` is unset, it logs a warning. The SQLite files are then stale, so set `DATABASE_URL` again to use the migrated data.

## Backups

**PostgreSQL.** Dump the database with `pg_dump`. In Docker Compose:

```bash
docker compose exec -T postgres pg_dump -U downtify downtify > downtify-backup.sql
```

To restore, load the dump into an empty database with `psql`.

**SQLite.** Stop the server first, then copy the `.db` files together with their `-wal` and `-shm` files, if present, from `DATABASE_DIR`. Copying while the server runs can produce an inconsistent backup.

## Rolling back

To return to SQLite, unset `DATABASE_URL` (comment out the line in Docker Compose) and restart. Downtify then reads the SQLite files again. Those files hold the data as it was before the migration: changes made while PostgreSQL was active are not in them. If you need those changes, the PostgreSQL dump is the source for them.

## Trash worker

The trash worker (`python -m downtify.trash_worker`) reads the same stores as the server:

- **SQLite:** `--database` and `--auth-database` are required and point at the SQLite files.
- **PostgreSQL:** with `DATABASE_URL` set, `--database` and `--auth-database` are optional and ignored. The stores come from the database, and `--data-dir` (default `DATABASE_DIR`, then `/data`) only sets where the database groups are located.

## Health check

`GET /api/health` also checks PostgreSQL. When the server cannot be reached, it returns:

```json
{"status": "database_unavailable"}
```

with HTTP status `503`. Otherwise it returns `200` with `"status": "ok"`. On SQLite the check never fails because of the database.
