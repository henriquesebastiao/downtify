# Playback volume normalization

Normalization is optional and off by default. It uses an integrated loudness
measurement and a constant track gain during playback, targeting -18 LUFS,
limiting amplification to 12 dB and predicted true peaks to -1 dBTP. Audio files
are never rewritten. Web Audio combines the gain with the existing equalizer.
Unmeasured, changed, silent or unavailable files keep their original level.

Administrators explicitly start library analysis from general settings. Up to two
FFmpeg workers read files concurrently, bounded by the container's CPU quota
and CPU affinity, with no network protocols enabled. Each worker has one decode
and filter thread and runs at a lower scheduling priority where supported.
Pause finishes the current files, preserving pending work. Restart preserves the
queue and measurements but never resumes analysis automatically. File metadata
and the algorithm version invalidate obsolete measurements after replacement.

Starting another analysis checks the listed files but reuses valid stored
measurements. Only new, moved, replaced or modified files, and previously failed
measurements, need to be measured again. The optimized measurement retains the
192 kHz peak sampling and algorithm version, so existing results remain valid.
It measures the full track without normalizing an unused output, and flushes
the final partial analysis block to retain peaks at the end of the file.

Mobile clients can read `GET /api/v1/tracks/{id}/loudness`; permissions match
track visibility. Analysis controls remain restricted to administrators.
The profile includes its source fingerprint, ETag and size for clients that bind
an offline measurement to the exact downloaded audio. No measurement means no
gain change. Very dynamic or very quiet tracks may remain below the target due
to the amplification and peak limits.
