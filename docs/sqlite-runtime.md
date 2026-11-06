# Derived-state SQLite runtime

The two companions use SQLite 3.53.4, matching the native web image verified on
2026-11-06. It is compiled from the public upstream amalgamation in a separate
build stage; the compiler and source archive are not installed at runtime.
The Python standard library API is retained. LD_LIBRARY_PATH selects the pinned
libsqlite3.so.0 only inside these dedicated images.

Source: https://www.sqlite.org/2026/sqlite-amalgamation-3530400.zip
Release: https://www.sqlite.org/releaselog/3_53_4.html
Source id: 2026-07-24 19:02:57 bf7c7f30031888f4e796e429ab3978879485813aaca6f641c7b33e4e09459bcc
Official SHA3-256 of sqlite3.c: 67f423e9ebbbdc473cbc4772c872ee6b89f31fde4ed0279a5c25d5f65c043a16
SQLite is in the public domain: https://www.sqlite.org/copyright.html

Prepare with curation/fetch_sqlite_runtime.py --output /path/to/public/source,
then pass --build-context sqlite_source=/path/to/public/source to either
companion Dockerfile. Both recipes check the official source hash before
compiling and assert the loaded sqlite_version before accepting the image.

WAL may return SQLITE_BUSY during concurrent writes or last-connection cleanup.
The application avoids write transactions for unchanged catalog observations,
uses bounded write batches, throttles lease renewal, and defers transient
contention. Corruption and other non-transient errors are not treated as busy.
No native library database migration or private backup is performed.

Reference: https://www.sqlite.org/wal.html and https://www.sqlite.org/rescode.html
