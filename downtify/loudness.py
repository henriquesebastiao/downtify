"""Read-only loudness measurement and a durable, CPU-bounded analysis queue."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import sqlite3
import subprocess
import threading
from pathlib import Path
from typing import Any, Callable

from .library_catalog import LibraryContext, resolve_library_file
from .sqlite_utils import connect_sqlite

ALGORITHM_VERSION = 1
TARGET_LUFS = -18.0
MAX_GAIN_DB = 12.0
PEAK_CEILING_DBTP = -1.0
_DEMUXERS = {
    '.mp3': 'mp3',
    '.flac': 'flac',
    '.wav': 'wav',
    '.ogg': 'ogg',
    '.opus': 'ogg',
    '.m4a': 'mov',
    '.m4b': 'mov',
    '.mp4': 'mov',
    '.aac': 'aac',
    '.aif': 'aiff',
    '.aiff': 'aiff',
    '.wma': 'asf',
    '.mka': 'matroska',
    '.alac': 'mov',
}


def normalization_gain(integrated: float, true_peak: float) -> float:
    """A constant track gain, capped by both amplification and true peak."""
    if not math.isfinite(integrated) or not math.isfinite(true_peak):
        return 0.0
    if not -120 <= integrated <= 20 or not -160 <= true_peak <= 20:
        raise ValueError('Invalid loudness measurement')
    return min(
        MAX_GAIN_DB, TARGET_LUFS - integrated, PEAK_CEILING_DBTP - true_peak
    )


def file_signature(path: Path) -> str:
    stat = path.stat()
    identity = (
        stat.st_size,
        stat.st_mtime_ns,
        stat.st_dev,
        stat.st_ino,
        ALGORITHM_VERSION,
    )
    return hashlib.sha256(repr(identity).encode()).hexdigest()


def file_etag(stat: os.stat_result) -> str:
    """The ETag Starlette's ``FileResponse`` sends for a file with ``stat``.

    The apps download the original through ``FileResponse`` and compare
    this to the header they got, to know the measurement is of their copy.
    """
    etag = hashlib.md5(
        f'{stat.st_mtime}-{stat.st_size}'.encode(), usedforsecurity=False
    ).hexdigest()
    return f'"{etag}"'


def analysis_workers() -> int:
    """Respect the container quota and leave a fixed upper bound for library IO."""
    capacity = float(os.cpu_count() or 1)
    try:
        capacity = min(capacity, len(os.sched_getaffinity(0)))
    except (AttributeError, OSError):
        pass
    try:
        quota, period = (
            Path('/sys/fs/cgroup/cpu.max').read_text(encoding='utf-8').split()
        )
        if quota != 'max':
            capacity = min(capacity, float(quota) / float(period))
    except (OSError, ValueError, ZeroDivisionError):
        try:
            quota = float(
                Path('/sys/fs/cgroup/cpu/cpu.cfs_quota_us').read_text(
                    encoding='utf-8'
                )
            )
            period = float(
                Path('/sys/fs/cgroup/cpu/cpu.cfs_period_us').read_text(
                    encoding='utf-8'
                )
            )
            if quota > 0:
                capacity = min(capacity, quota / period)
        except (OSError, ValueError, ZeroDivisionError):
            pass
    return max(1, min(2, int(capacity)))


class LoudnessAnalyzer:
    """No analysis starts on construction or after a restart."""

    def __init__(
        self,
        db_path: Path,
        context: Callable[[], LibraryContext],
        *,
        workers: int | None = None,
    ) -> None:
        self.path = str(db_path)
        self.context = context
        self._lock = threading.RLock()
        self._pause = threading.Event()
        self._closed = threading.Event()
        self._thread: threading.Thread | None = None
        self._processes: set[subprocess.Popen] = set()
        self._workers = max(
            1, min(2, workers if workers is not None else analysis_workers())
        )
        with connect_sqlite(self.path) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS loudness_measurements (
                file TEXT PRIMARY KEY, signature TEXT NOT NULL, profile TEXT NOT NULL)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS loudness_jobs (
                file TEXT PRIMARY KEY, position INTEGER NOT NULL, status TEXT NOT NULL)""")
            conn.execute(
                'CREATE INDEX IF NOT EXISTS loudness_jobs_pending ON loudness_jobs(status, position)'
            )
            conn.execute(
                "UPDATE loudness_jobs SET status='pending' WHERE status='running'"
            )

    def info(self, file: str, full_path: Path) -> dict[str, Any] | None:
        try:
            signature = file_signature(full_path)
        except OSError:
            return None
        with connect_sqlite(self.path) as conn:
            row = conn.execute(
                'SELECT profile FROM loudness_measurements WHERE file=? AND signature=?',
                (file, signature),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def status(self) -> dict[str, Any]:
        with connect_sqlite(self.path) as conn:
            counts = dict(
                conn.execute(
                    'SELECT status, COUNT(*) FROM loudness_jobs GROUP BY status'
                )
            )
        with self._lock:
            active = self._thread is not None and self._thread.is_alive()
        return {
            'active': active,
            'pause_requested': self._pause.is_set(),
            'paused': not active and bool(counts.get('pending', 0)),
            'total': sum(counts.values()),
            'done': counts.get('done', 0),
            'failed': counts.get('failed', 0),
            'pending': counts.get('pending', 0),
            'running': counts.get('running', 0),
            'workers': self._workers,
        }

    def start(self, files: list[str]) -> None:
        with self._lock:
            self._check_idle()
            with connect_sqlite(self.path) as conn:
                conn.execute('DELETE FROM loudness_jobs')
                conn.executemany(
                    "INSERT OR IGNORE INTO loudness_jobs VALUES (?, ?, 'pending')",
                    [(file, index) for index, file in enumerate(files)],
                )
            self.resume()

    def _check_idle(self) -> None:
        if self._closed.is_set():
            raise ValueError('Analyzer is closed')
        if self._thread is not None and self._thread.is_alive():
            raise ValueError('An analysis is already running')

    def resume(self) -> None:
        with self._lock:
            self._check_idle()
            self._pause.clear()
            self._thread = threading.Thread(
                target=self._run, name='loudness-analysis', daemon=True
            )
            self._thread.start()

    def pause(self) -> None:
        # Finish the current file, preserving the rest of the queue.
        with self._lock:
            self._pause.set()

    def close(self) -> None:
        self._closed.set()
        self._pause.set()
        with self._lock:
            thread = self._thread
            for process in self._processes:
                if process.poll() is None:
                    process.terminate()
        if thread is not None:
            thread.join(timeout=5)

    def _measure(self, path: Path) -> dict[str, Any]:
        executable = shutil.which('ffmpeg')
        demuxer = _DEMUXERS.get(path.suffix.lower())
        if not executable or not demuxer:
            raise ValueError('FFmpeg or the audio format is unavailable')
        command = [
            executable,
            '-hide_banner',
            '-nostdin',
            '-nostats',
            '-protocol_whitelist',
            'file,pipe',
            '-threads',
            '1',
            '-f',
            demuxer,
            '-i',
            str(path),
            '-map',
            '0:a:0',
            '-vn',
            '-filter_threads',
            '1',
            '-af',
            # Keep the existing true-peak sampling rate, without normalizing
            # an unused output. Padding only this discarded analysis stream
            # flushes the final partial block, including its last sample peak.
            'aresample=192000,apad=pad_dur=0.1,'
            'ebur128=peak=sample:metadata=1,'
            'ametadata=print:key=lavfi.r128.I,'
            'ametadata=print:key=lavfi.r128.sample_peak',
            '-f',
            'null',
            '-',
        ]
        with self._lock:
            if self._closed.is_set():
                raise ValueError('Analyzer is closed')
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
            )
            self._processes.add(process)
            if hasattr(os, 'setpriority'):
                try:
                    os.setpriority(os.PRIO_PROCESS, process.pid, 10)
                except OSError:
                    pass
        try:
            _, stderr = process.communicate(timeout=1800)
            if process.returncode:
                raise ValueError('Audio could not be analyzed')
            levels = re.findall(r'lavfi\.r128\.I=([^\r\n]+)', stderr)
            peaks = re.findall(r'lavfi\.r128\.sample_peak=([^\r\n]+)', stderr)
            summary = stderr.rsplit('Summary:', 1)[-1]
            final_peaks = re.findall(r'Peak:\s+([-+\w.]+)\s+dBFS', summary)
            if not levels or not peaks or not final_peaks:
                raise ValueError('Audio measurement unavailable')
            integrated = float(levels[-1])
            amplitude = max(float(value) for value in peaks)
            peak = max(
                20 * math.log10(amplitude) if amplitude > 0 else float('-inf'),
                # The summary rounds to 0.1 dB: take its conservative bound.
                max(float(value) for value in final_peaks) + 0.05,
            )
            if integrated <= -70:
                integrated = float('-inf')
            if not math.isfinite(integrated) or not math.isfinite(peak):
                return {
                    'state': 'silent',
                    'gain_db': 0.0,
                    'algorithm_version': ALGORITHM_VERSION,
                }
            return {
                'state': 'ready',
                'gain_db': normalization_gain(integrated, peak),
                'integrated_lufs': integrated,
                'true_peak_dbtp': peak,
                'algorithm_version': ALGORITHM_VERSION,
            }
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise ValueError('Analysis timed out') from None
        finally:
            with self._lock:
                self._processes.discard(process)

    def _run(self) -> None:
        if self._workers == 1:
            self._drain()
            return
        threads = [
            threading.Thread(
                target=self._drain,
                name=f'loudness-worker-{index}',
                daemon=True,
            )
            for index in range(self._workers)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    def _drain(self) -> None:
        while not self._pause.is_set() and not self._closed.is_set():
            with self._lock:
                if self._pause.is_set() or self._closed.is_set():
                    return
                with connect_sqlite(self.path) as conn:
                    row = conn.execute(
                        "SELECT file FROM loudness_jobs WHERE status='pending' ORDER BY position LIMIT 1"
                    ).fetchone()
                    if row is None:
                        return
                    file = row[0]
                    conn.execute(
                        "UPDATE loudness_jobs SET status='running' WHERE file=?",
                        (file,),
                    )
            result = 'failed'
            try:
                full = resolve_library_file(file, self.context())
                if full is None:
                    raise ValueError('File unavailable')
                before = file_signature(full)
                profile = self.info(file, full)
                if profile is None:
                    profile = self._measure(full)
                    if self._closed.is_set():
                        raise ValueError('Analyzer is closed')
                    if file_signature(full) != before:
                        raise ValueError('File changed during analysis')
                    stat = full.stat()
                    profile['fingerprint'] = before
                    profile['source_size'] = stat.st_size
                    profile['source_etag'] = file_etag(stat)
                    with connect_sqlite(self.path) as conn:
                        conn.execute(
                            'INSERT INTO loudness_measurements VALUES (?, ?, ?) '
                            'ON CONFLICT(file) DO UPDATE SET signature=excluded.signature, profile=excluded.profile',
                            (
                                file,
                                before,
                                json.dumps(profile, allow_nan=False),
                            ),
                        )
                result = 'done'
            except (OSError, ValueError, KeyError, IndexError, sqlite3.Error):
                # Do not export FFmpeg stderr: tags and filenames can be private.
                if self._closed.is_set():
                    result = 'pending'
            finally:
                with connect_sqlite(self.path) as conn:
                    conn.execute(
                        'UPDATE loudness_jobs SET status=? WHERE file=?',
                        (result, file),
                    )
