# Optional local music analysis

**Experimental beta: all modules and the separate unqualified-engine trial default off for new installations and
accounts.** Existing explicit preferences are retained. Set
`DOWNTIFY_MUSIC_AI_ENABLED=1` only after supplying the optional web dependencies,
matching companion images, verified model build contexts and shared derived
state. This flag exposes capabilities; it does not opt users into modules.

For the optional web recipe, build the frontend with `npm ci` and `npm run build`
inside `frontend/`. Create a source offer from the committed public revision using
`git archive --format=tar.gz --output=<source-offer-directory>/source.tar.gz HEAD`.
Build `Dockerfile.music-ai-web` with
`--build-context source_offer=<source-offer-directory>`. Keep that corresponding
source archive available to authenticated users of modified builds.

The analysis recipe also needs `audio_bundle` and `sqlite_source` named contexts;
the DJ recipe needs `dj_models` and `sqlite_source`. Models are public upstream
inputs, not music-library files. Do not generate a trusted manifest from arbitrary
downloads: compare upstream provenance and expected hashes before bundle creation.
Deploy the companions without network access, using the same derived-state mount
as the web process and only read-only audio roots. Operators must provision the
state directory for their chosen runtime UID; no recursive library permission
changes are needed. Runtime model downloading is disabled.

For developer tests, install the native development environment first, then
`uv pip install --python .venv/bin/python -r requirements-music-ai-tests.txt` and
run `uv run --no-sync pytest tests/music_ai`. The extra dependencies are CPU
signal fixtures, not the model runtimes or weights. FFmpeg/FFprobe integration
tests skip explicitly when these executables are absent. Use the DJ image for
the real encoder and UID acceptance checks.

The CPU companion runs independently from the native web process. Mount the
existing catalog roots read-only, and only
the separate derived database directory read-write. Run without a network,
without Docker access and with all Linux capabilities dropped. Match the web
process runtime identity for the shared private SQLite database. The standalone
image defaults to UID/GID 1000. Match this to your native runtime user.
Neither provider credentials nor the native application data directory are
mounted in the companion. No provider credentials are required.
The web process supplies jobs using the existing catalog and visibility rules.

DCLAP v1 weights and the LAION tokenizer revision are verified against the model
manifest before loading. The six fixed English descriptions are encoded once
with the pinned reference text tower during bundle preparation. The runtime
contains only the small audio tower and those verified fixed vectors; it does
not load the text tower or Transformers. Audio analysis uses chronological ten
second windows with five second overlap, bounded PCM buffering and CPU ONNX
sessions with one thread. The worker checks pause, native activity, leases and
file changes before publishing derived vectors. Original music is never changed.

Sources checked 2026-11-05:

- DCLAP: https://github.com/NeptuneHub/AudioMuse-AI-DCLAP
- DCLAP license: https://github.com/NeptuneHub/AudioMuse-AI-DCLAP/blob/main/LICENSE
- LAION CLAP: https://github.com/LAION-AI/CLAP
- ONNX Runtime: https://onnxruntime.ai/docs/

DCLAP's repository uses AGPL-3.0. The companion includes that license, its full
Python source and the dependency/build recipe. Preserve these with modifications
and provide corresponding source to the users of the modified service. Upstream
model and dataset notices remain applicable; no training audio is redistributed.

Prepare the bundle with `curation/prepare_audio_bundle.py` in the reference
environment. Build with `--build-context audio_bundle=/path/to/public/bundle`.
The four public model files are copied into the image with read-only file modes.
Compare audio and normalized mood vector hashes against the reference benchmark
before using a new bundle. The final image requires no model mount. Preserve the
original reference release for reproducibility.

Each module has an administrator switch and a user preference. Local similarity,
personalization, similarity, daily/weekly playlists, external beta and both DJ
modes default off on new installations and accounts. An administrator must
enable a module globally, then each user can opt in independently. Existing
stored preferences are preserved during upgrades. Turning off personalization rejects new listening events. Erasing
analyses pauses analysis rather than silently recreating it. Erasing the listening
profile does not delete liked songs or saved native playlists.

Daily playlists rotate at 04:00 Europe/Paris; weekly selections rotate Monday at
04:15, including catch-up after restart. Native saved copies remain stable.
The daily mix keeps the six mood prompts; the weekly set covers nine themes
(six moods plus the three genre themes rap, rock and electro). A genre theme
never falls back to another style: it is offered only once the native library
holds enough tracks tagged in that genre, otherwise the set stays pending so a
later metadata completion fills it. Weekly sets hold twenty-five distinct
titles. Each playlist card exposes a deterministic cover at
`GET /api/v1/music-ai/playlists/{cadence}/{mood}/cover.svg?period=…` (same key,
same picture, cached for a day); the client may show it alongside the four
cover track ids.

## Optional prepared DJ renderer

The separate CPU renderer uses Beat This! 1.1.0 (MIT), verified small0/final0
checkpoints, conservative onset/grid confidence, and FFmpeg's Rubber Band filter.
Rubber Band changes tempo by at most four percent without changing pitch.
The key estimate is advisory. Rhythm never proves absence of vocals: uncertain
vocals or grids always use short transitions. There is no stem separation.
The mixer exchanges bass progressively, normalizes track level conservatively
and limits oversampled output peaks. Originals are strictly inputs.

Prepared sets stream directly from the two-deck mixer into one AAC encoder.
Decoded PCM is loaded when needed and removed after its last block; a complete
uncompressed copy of the set is never written. The dedicated DJ cache defaults
to 5 GiB, configurable with --cache-bytes. A 2 GiB disk reserve is required.
The budget includes working files and completed sets and refuses allocation
before crossing it. Delete individual sets with the owner-scoped cache action;
the single renderer performs deletion after cancelled child processes exit.
Other caches, library permissions and original audio are not modified.

DJ API uses native authentication, current catalog ids and visibility rules.
Session creation has an owner-scoped request id for retry safety. Status and
media access recheck visibility of every source. Set media supports HTTP Range;
filesystem paths, source versions and owner columns are never returned. The
prepared page pauses classical playback without modifying its queue.

Build Dockerfile.music-dj with --build-context dj_models=/path/to/verified/models.
The image pins its Python base, direct dependencies, FFmpeg package and model
hashes. Runtime has no network, read-only roots, dropped capabilities and a
separate state mount. The deployment matches the native runtime identity.
Exact installed Python/Debian versions and license notices are in
/usr/share/doc/music-dj. Corresponding application source is served by the
authenticated source endpoint, including the Dockerfile and dependency recipe.

Upstream sources and notices checked 2026-11-05/06:
- https://github.com/CPJKU/beat_this/tree/ad7974846029835307ba19a3d5cefbf40b243041
- https://github.com/CPJKU/beat_this/blob/ad7974846029835307ba19a3d5cefbf40b243041/LICENSE
- https://sources.debian.org/src/ffmpeg/ (5.1.9-0+deb12u1 source package)
- https://breakfastquay.com/rubberband/ (GPL/commercial dual licensing; GPL build used)
- https://ffmpeg.org/ffmpeg-filters.html#rubberband

## Interactive HLS and validation gate

Readiness is measured where the listener feels it. An interactive set records
`ready_seconds` on the first successful manifest read; a prepared set records
`preparation_seconds` when the renderer publishes its file. Both stay in the
private session document. A bounded rolling history (200 entries) is exposed
to administrators at `GET /api/v1/music-ai/dj/readiness` with `p50`, `p95`,
worst delay and the count above the ten-second target. The measurement adds no
client identity, audio or track metadata and never delays the response.

The interactive renderer uses one continuous AAC encoder, six-second HLS
segments and a 24-second render horizon. A twelve-segment manifest and four
extra segments support short network interruptions. Only completed files are
published atomically. Segments and manifests recheck native authentication,
ownership, enabled modules and current source visibility; no arbitrary URI or
key resource can be embedded in a manifest. The same account can share one
render between web and Android. One global renderer runs at a time.

Pause/resume, next, replace and theme commands carry idempotent request ids.
The renderer acknowledges the actual effective transition; already rendered
audio is never rewritten. Replacement uses unused analyzed tracks from the
session selection, and theme changes reorder its remaining tracks. The UI
shows the effective delay. Prepared sets retain full seeking; live playback
follows the active HLS window. There is no promise of instantaneous changes.

Live inputs are frozen and analyzed progressively in a window of four decks,
within the same 5 GiB DJ budget and disk reserve. This prevents a concurrent
library replacement from breaking an ongoing live set. File versions
are checked during the copy, originals stay read-only, and temporary copies
are removed when the session ends or fails. There is no application backup.
Derived rhythm profiles remain fenced by their original fingerprints, model
hashes and physical source versions. DJ reuses valid sound embeddings when
available. Otherwise a bounded local selection feeds its own rhythm/energy
analysis. Whole-library recommendation indexing follows its four independent
recommendation/playlist switches. Creation retries retain the same selection
even when the catalog or its analyses advance during a request.

Qualified interactive mode requires the administrator's local validation.
An independently disabled-by-default `dj_trial` preference (administrator and user)
permits a voluntary trial of an available unqualified engine. This does not
create a qualification receipt or relax authentication/visibility/module gates. Both global and user interactive switches
must be enabled; this does not bypass disabled modules. The administrator
validation endpoint is separate from ordinary session creation. It chooses
up to forty local tracks and requires at least 3700 seconds of planned audio.
Play the resulting direct stream without pausing, seeking or stopping it.
Only continuous progress timed by the server can accumulate the required
3600 seconds; client elapsed-time claims or accelerated seeks cannot do so.
The clock compares total server and playback progress within each uninterrupted
window. A bounded two-second phase allowance absorbs HTTP response/queue jitter;
it never contributes to the required duration. Both observed durations must
reach 3600 seconds. Reader interruption events reset the window, as do missing
reports, reversed progress and cumulative clock drift beyond that allowance.
An administrator can revalidate an earlier interactive selection to reuse still
valid analyses; current file versions and visibility are checked again.
The gate also requires render throughput above 1.5 times real time and zero
interruptions. It is bound to exact engine, model and runtime hashes; an
incompatible update invalidates it. Synthetic tests never satisfy this gate.

Web uses pinned hls.js 1.7.4 only when a direct stream is opened. Its BSD
license is in docs/hlsjs-LICENSE.txt and the source offer. Android reuses the
existing Media3 1.11.1 foreground media service, native authentication and
logical media ids. DJ manifests/segments bypass the persistent audio cache,
and capability changes stop disabled playback. DJ mixes never become fake
library listening/favorite events.

Sources checked 2026-11-06:
- https://raw.githubusercontent.com/FFmpeg/FFmpeg/n5.1.9/doc/muxers.texi
- https://github.com/video-dev/hls.js/releases/tag/v1.7.4
- https://developer.android.com/media/media3/exoplayer/hls

Status: experimental. Synthetic tests do not prove musical relevance.
Physical Android/background QA and twenty-seed listening comparisons require
separate evidence. A real prepared set has been rendered and checked, but
this does not establish subjective transition quality or the live one-hour
gate. External beta and both DJ modes remain off by default.

## Queue DJ and continuous themes (candidate, 6 November 2026)

The queue's Mode DJ preserves the order of 2–40 upcoming local tracks,
including repeated occurrences. During playback it prepares the following
tracks and hands over at the actual end of the current song, provided the
render is ready. If preparation misses that boundary, ordinary playback
continues. Non-local entries require an explicit different selection.

The web uses the main audio transport for DJ playback, volume, equalizer,
media-session controls and the sleep timer. Current and next decks come from
the audible media clock. Only their actual overlap animates the artwork and
transition progress. The classic queue is retained when leaving DJ mode.
Android uses its existing foreground Media3 service and updates compatible
media-item metadata without changing the stream address.

Continuous themes start from a bounded local selection and replenish it with
currently authorized catalog candidates in a single background selector. The
interactive request never performs this renewal calculation. Recently selected
ids are excluded (up to 80), genre filters remain active, and unavailable
continuations retain the existing local pool without falling back to radio. One HLS
encoder remains alive; decoded decks, rolling segments and timeline history
are bounded. The pool rotates without performing downloads or starting a
classic radio. Rap, rock and electronic shortcuts filter native genre tags;
insufficient matching metadata yields a clear error, never a different genre.

Program-date-time timestamps map late-joining clients onto the same absolute
timeline. A continuous session without HLS readers pauses after 90 seconds
and stops after 15 minutes. Restarting playback resumes a paused session.
Engine qualification remains version-specific; a voluntary unqualified trial
is identified separately and requires explicit opt-in. Proofs for
previous engines are retained for rollback. Synthetic accelerated tests do
not qualify a new engine for interactive use.

Design references checked 6 November 2026:
- https://support.apple.com/fr-fr/105067
- https://developer.android.com/reference/androidx/media3/common/Player
- https://datatracker.ietf.org/doc/html/rfc8216

This section describes candidate behavior, not a deployment or listening
qualification receipt. Physical Android background playback and subjective
listening comparisons still require their own evidence.

## Corrective architecture and current validation — 6 November 2026

Home reads stored selections and native point lookups only (four daily cards,
at most 160 ids), with account-private ETag validation. It does not generate
playlists, rehash the library or reconcile the native catalog. The background
indexer consumes native revision changes and a bounded pending-analysis queue;
unchanged native cursors do not reload the feed. Erasure and file replacement
invalidate derived analyses. Explicit full similarity/ranking requests still
read the derived snapshot; background jobs/caching for those requests remain
follow-up work and must not be described as already completed.

Web and Android use a single playback authority. User play/pause intent is
independent from renderer state. Every mode/account/manual-selection change
invalidates old asynchronous work. An owner-scoped cancellation tombstone also
rejects a creation that completes after cancellation or a timeout. Returning
from DJ selects the dominant deck during overlap and maps cue plus adjusted
playback speed back to the source time. Queue occurrences distinguish repeated
copies of the same title. Theme and seed mixes remain local; seed mixes require
a current sound embedding and start with the chosen track. If that title is already playing, clients
let it finish and request a seed-excluded selection for the next boundary.

Use `GET /dj/sessions?summary=true` for page summaries and
`GET /dj/sessions/{id}?view=playback&position=...` for a bounded playback plan.
Private ETags return 304 when that plan is unchanged. Legacy full responses
remain available. The renderer prepares at most three future decks, reuses
snapshot slots after passed decks, and retains the 24-second committed horizon.
Analysis and DJ share one expiring compute lease. DJ requests priority; an
analysis checkpoint yields. A paused/full renderer releases the lease. Analysis
also defers under native activity or guest memory/I/O pressure.

Starting deployment budgets: analysis 0.5 CPU/1.5 GiB, DJ 1 CPU/2 GiB and 5 GiB
separate disk cache. No GPU or paid service is required. Do not confuse configured
caps with actual usage, minimum hardware or a phone battery result. Android's
64 MiB target bounds the audio allocator; artwork/offline caches have separate
budgets. Its beta build enables R8, resource shrinking and shell profiling.
The README records a separate post-deployment Docker usage snapshot from
6 November 2026. Its uncontrolled workload cannot establish active-render
throughput or a causal before/after performance improvement.
Physical Macrobenchmark/baseline-profile measurements must use the real paired
server and report Android version, startup, warm home, pause p95, memory,
temperature and transport recovery. No physical-device numbers are claimed yet.

Current automated evidence: web 777 passed/one skipped plus production build;
focused Python 116 passed; isolated Linux DJ 75 passed; isolated native/server
3375 passed and ten subtests. Groups overlap. A synthetic local 50000-entry
comparison measured home p50=46.49ms/p95=51.81ms (25 requests), max160 ids and
zero full-catalog calls, versus a reconstructed previous p50=2812.538ms (three
requests). Script SHA256:
`7a46e50ada8d8e9b8cd9224aba712854f27ff7c5d67c5ce69ab3b73541a96a00`.
This comparison does not establish LAN/NAS/Pixel performance or subjective quality.
The synthetic corpus contains no user library content.

Pending gates: latest full Android build/tests and static checks; physical Pixel
background/Bluetooth/latency/thermal tests; 20 comparative transitions and seed
listening; one uninterrupted hour and longer battery testing. On-device Beat
This! small0 ONNX export/inference and a dual-deck transport are unqualified;
the Android companion offers an unqualified short-fade prototype without model
inference, while server mode remains the initial choice. A larger model is not a fix
for lifecycle races or full-catalog work on interactive requests.

Web HLS position uses a program date to locate a late join, then advances on the
audio element's clock. Refreshing fragment timestamps cannot move the listener
cursor; real seeks, stalls and interruption events remain visible to continuity
validation. Reconnection or a changed mix origin establishes a new anchor.
Synthetic clock tests cover stale dates, genuine seeks and reconnection. This
does not establish a successful one-hour stream: the latest live trial reset on
clock drift and client interruption events, and the engine stays unqualified.

Administrator validation sessions emit bounded browser-console diagnostics for
HLS error codes, buffer depth, playback rate, interruption type and continuity
request latency. They are disabled outside an active administrator validation,
stop on account/generation changes and omit URLs, session/track identifiers,
titles and raw errors. They explain a failed trial; they cannot qualify one.

## Live preparation correction — 7 November 2026

A real validation of the earlier engine exhausted the audio buffer after about
12 minutes while a deck was being prepared. Fast segment requests did not
prevent this renderer-side starvation. That trial failed and remains failed.

The corrected renderer owns one cancellable preparation slot. An isolated
AudioIO instance freezes/analyzes or decodes a deck without changing the owner's
plan, snapshot map, mixer or playback state. The owner reaps results after checking
source identity and current plan needs. It renews the compute lease, handles
transport commands and feeds HLS throughout preparation, including while paused
or at the 24-second render horizon. The shared heavy-compute lease is retained
until work is reaped. Shutdown cancels and joins preparation before removing
its files; old or cancelled results cannot attach to a new plan.

PCM lookup never decodes. The entire next one-second block is checked before
the mixer's cursor or EQ state can advance. The current occurrence and up to
three following occurrences retain their derived audio. A single pending plan
edit is rebased against the actual rendered cursor and commits only when its
audio is ready; pause/resume do not wait for that edit. Additional simultaneous
plan edits report busy rather than building a queue of background tasks.

A staged change temporarily retains the union of two four-occurrence PCM
windows, plus the single in-flight task until it completes or cancels. These
files remain inside the same 5 GiB cache and reserve checks; they are memory
mapped, not loaded as complete audio arrays. Superseded variants are removed
after commit. Cache accounting tolerates only files that disappear during
atomic rotation, retaining other filesystem and budget failures.

Reported live render speed now conservatively includes preparation wall time
as well as encoding/mixing time; overlapping work can be counted twice.
The engine identity includes the preparation helpers, so old qualification
cannot silently apply. The audio-analysis identity is unchanged, allowing
unchanged cached profiles to be reused without a library-wide reanalysis.

Evidence for this correction: 98 synthetic Linux checks passed with the real
encoder and model runtime, including live controls and continuous renewal;
25 targeted Windows checks passed with one symlink-privilege skip. The broader
Windows AI suite collected before the last additions passed 213 checks with
20 explicit skips. These groups overlap. No Pixel latency, battery, temperature,
subjective transition quality or successful one-hour qualification is inferred.

The final candidate passed 100 Linux checks after the precise import-formatting
identity regression was added. Its real playback trial subsequently reset on
clock drift and reader interruptions. Segment loads reached several seconds;
the test browser also stopped responding to control. These observations do not
establish a single cause and the candidate remains unqualified. The failed
trial is stopped, and its temporary user trial preference is restored without
changing global modules or unrelated preferences.

Validation-only browser diagnostics now capture monotonic and wall timestamps
with each audio-position sample. This permits comparison of media progress,
monotonic elapsed time and wall-clock changes without treating console capture
timestamps as an independent playback clock. No transport or threshold changes
are made. The administrator validation action remains visible when trial mode
makes an unqualified engine usable, avoiding a preference change just to test it.

Official references rechecked 6 November 2026:
- https://developer.android.com/media/media3/session/player
- https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview
- https://github.com/CPJKU/beat_this#available-models
