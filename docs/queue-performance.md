# Download queue performance

Queue synchronization keeps the existing reactive items and indexes them with the same identity used by the server: song ID, falling back to URL. Applying a snapshot therefore performs linear lookup work rather than searching the whole reactive list for each row. Changed batches and WebSocket messages publish one queue version; unchanged snapshots leave it alone.

This is an internal optimization. Queue endpoints, response shapes, polling cadence, provider order and download settings are unchanged. It does not make a provider transfer or an audio conversion faster.

## Reproduce the benchmark

Install the frontend's existing dependencies, then run from `frontend/`:

```sh
DOWNTIFY_QUEUE_BENCHMARK=1 npm test -- benchmarks/queue-sync.test.js
```

PowerShell:

```powershell
$env:DOWNTIFY_QUEUE_BENCHMARK = '1'
npm test -- benchmarks/queue-sync.test.js
Remove-Item Env:DOWNTIFY_QUEUE_BENCHMARK
```

The opt-in test retrieves public baseline commit `6d7bebf00d7e41c011645b9ebe1de004c9e31e74` with `git show` (no network fetch), loads both actual queue modules with real Vue reactivity and mocked API responses, and compares their final states for 250, 2,000 and 10,000 generated jobs. The commit must be available locally; `DOWNTIFY_QUEUE_BASELINE_REF` can select another available revision.

Output reports initial population, median of three unchanged snapshots, median of three snapshots changing ten percent of rows, and notifications for unchanged snapshots. Initialization and final-state comparison are outside the repeated timing samples. It creates one temporary baseline module beside the benchmark and removes that file in a `finally` block.

Set `DOWNTIFY_QUEUE_BENCHMARK_OUTPUT` to a file path to retain the JSON report independently of the test reporter.

These timings exclude provider/network latency and browser DOM rendering. They are diagnostic measurements, not timing thresholds in CI. The normal offline tests cover identity, notification behavior, index lifecycle and linear key-access work.
