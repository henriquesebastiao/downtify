# Catalog folding and responsiveness

External folders remain part of the playable library. Artist matching and
duplicate filtering keep their existing order and duration rules. Each fold
prepares the owned artist names once and caches repeated external artists,
including misses, only for that catalog snapshot.

During the web application's lifespan, a single spawned process calculates
the pure folded listing. Only plain listing rows cross that boundary: the
worker does not receive SQLite stores, credentials, or filesystem writers.
One submission at a time bounds queued work. Standalone library calls remain
synchronous. The application releases the worker on shutdown.

Listing writers serialize their read/modify/publish cycle. UI requests keep
reading the last cached snapshot without taking that writer lock. A failed
calculation leaves the previous snapshot available. A cold library still has
to build its first listing; process isolation does not remove that initial
work or guarantee a particular download speed.

The offline benchmark uses generated artist names and track counters; it
does not inspect a music library or make network requests:

```sh
python benchmarks/catalog_fold.py --repo .
```

It loads the baseline's pure functions from the specified public Git commit
and asserts that the complete partition results are identical. Use
`--baseline-ref <commit>` to select another locally available baseline, or
`--external 200` for a smaller fixture. Timings depend on CPU and Python
version and measure catalog calculation rather than provider/network speed.
