# Playback volume normalization

Normalization is optional and off by default. It uses an integrated loudness
measurement and a constant track gain during playback, targeting -18 LUFS,
limiting amplification to 12 dB and predicted true peaks to -1 dBTP. Audio files
are never rewritten. Web Audio combines the gain with the existing equalizer.
Unmeasured, changed, silent or unavailable files keep their original level.

Administrators explicitly start library analysis from general settings. One
FFmpeg worker reads one file at a time, with no network protocols enabled.
Pause finishes the current file, preserving pending work. Restart preserves the
queue and measurements but never resumes analysis automatically. File metadata
and the algorithm version invalidate obsolete measurements after replacement.

Mobile clients can read `GET /api/v1/tracks/{id}/loudness`; permissions match
track visibility. Analysis controls remain restricted to administrators.
The profile includes its source fingerprint, ETag and size for clients that bind
an offline measurement to the exact downloaded audio. No measurement means no
gain change. Very dynamic or very quiet tracks may remain below the target due
to the amplification and peak limits.
