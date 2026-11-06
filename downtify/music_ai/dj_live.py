"""Short-horizon server renderer. No original file is ever an output."""

from __future__ import annotations

import time

import numpy as np

from .dj_audio import RATE
from .dj_hls import HlsEncoder
from .dj_live_plan import LivePlan
from .dj_mix import StereoMixer
from .dj_plan import Profile
from .dj_validation import runtime_identity


class LiveRenderer:
    def __init__(
        self, worker, io, results, *, clock=time.monotonic, sleep=time.sleep
    ):
        self.worker, self.io, self.results = worker, io, results
        self.clock, self.sleep = clock, sleep
        self.plan = LivePlan(
            [Profile(**value['profile']) for value in results.values()],
            worker.job['theme'],
            order=worker.job['ids'] if worker.job.get('queue_order') else None,
        )
        self.sources = {}
        if worker.job.get('continuous') and not worker.job.get('queue_order'):
            self.plan.rows = self.plan.rows[:6]
            self.plan.rows[-1]['transition'] = None
            last = self.plan.rows[-1]
            last['source_end'] = self.plan.profiles[last['id']].duration
            last['end'] = (
                last['start']
                + (last['source_end'] - last['cue']) / last['speed']
            )
        self.files = {}
        self.decoded = 0
        self.mixer = StereoMixer(self.plan.rows, self.source_for)
        self.paused = False
        self.anchor = None
        self.anchor_position = 0.0
        self.compute_seconds = 0.0
        self.published = 0.0
        self.command_checked = -1.0
        self.runtime = runtime_identity()
        self.continuous = worker.job.get('continuous', False)
        self.media_origin = None
        self.listener_checked = 0.0
        self.live_started = None

    def idle(self):
        if (
            not self.continuous
            or self.live_started is None
            or self.clock() - self.listener_checked < 5
        ):
            return False
        self.listener_checked = self.clock()
        session = self.worker.dj.get(
            self.worker.job['owner'], self.worker.job['id']
        )
        age = time.time() - max(
            self.live_started, session.get('listener_seen', 0)
        )
        if age > 900:
            self.worker.dj.publish(
                self.worker.job['id'],
                self.worker.job['lease_token'],
                'stopped',
                {'phase': 'idle'},
            )
            return True
        if age > 90 and not self.paused:
            self.anchor_position, self.anchor = self.position(), self.clock()
            self.paused = True
            self.publish(force=True)
        return False

    def extend(self):
        """Reuse the bounded analyzed pool without restarting the HLS encoder."""
        if not self.continuous:
            return
        rendered = self.mixer.position / RATE
        # Keep at least two complete future decks. An extension changes only
        # the last, unrendered transition, never the current or next deck.
        future = [
            row for row in self.plan.rows if row['start'] > rendered + 30
        ]
        if len(future) >= 3:
            return
        from .dj_plan import order_tracks

        recent = [
            row['id']
            for row in self.plan.rows[
                -min(10, max(1, len(self.results) - 2)) :
            ]
        ]
        candidates = [
            Profile(**value['profile'])
            for identity, value in self.results.items()
            if identity not in recent
        ]
        if len(candidates) < 2:
            candidates = [
                Profile(**value['profile'])
                for identity, value in self.results.items()
                if identity != self.plan.rows[-1]['id']
            ]
        if len(candidates) == 1:
            selected = candidates
        else:
            selected = order_tracks(
                candidates, self.plan.theme, limit=min(4, len(candidates))
            )
        self.plan.append(selected, rendered)
        self.plan.trim(rendered)
        self.mixer.replan(self.plan.rows)

    def position(self):
        if self.paused or self.anchor is None:
            return self.anchor_position
        return min(
            self.mixer.position / RATE,
            self.anchor_position + self.clock() - self.anchor,
        )

    @staticmethod
    def key(row):
        return row['id'], row['cue'], row['speed']

    def source_for(self, index, row):
        key = self.key(row)
        if key not in self.sources:
            result = self.results[row['id']]
            original = self.worker.job['sources'][row['id']]
            source = original.get('snapshot', original)
            duration = result['profile']['duration']
            complete = {
                **row,
                'source_end': duration,
                'end': row['start'] + (duration - row['cue']) / row['speed'],
            }
            self.decoded += 1
            filename = self.io.decode(
                source['path'],
                complete,
                result['loudness'],
                self.io.workspace / f'decoded-{self.decoded}.pcm',
                self.worker.checkpoint,
                expected=source['source_version'],
            )
            length = filename.stat().st_size // 8
            self.sources[key] = np.memmap(
                filename, mode='r', dtype='<f4', shape=(length, 2)
            )
            self.files[key] = filename
        return self.sources[key]

    def release_unused(self, *, all_sources=False):
        position = self.mixer.position / RATE
        active = {
            self.key(row)
            for row in self.plan.rows
            if row['start'] <= position + 1e-8 < row['end']
        }
        for key in list(self.sources):
            if all_sources or key not in active:
                self.sources.pop(key)._mmap.close()
                self.files.pop(key).unlink(missing_ok=True)

    def commands(self):
        if self.clock() - self.command_checked < 0.5:
            return
        self.command_checked = self.clock()
        worker = self.worker
        for command in worker.dj.pending_commands(
            worker.job['id'], worker.job['lease_token']
        ):
            action = command['action']
            original = self.plan.rows, self.plan.theme, self.plan.revision
            try:
                if action in ('pause', 'resume'):
                    position = self.position()
                    self.paused = action == 'pause'
                    self.anchor_position, self.anchor = position, self.clock()
                    result = {'accepted': True, 'effective_after_seconds': 0.0}
                else:
                    result = {
                        'accepted': True,
                        **self.plan.change(
                            action,
                            command['payload'],
                            self.mixer.position / RATE,
                            self.position(),
                        ),
                    }
                    self.mixer.replan(self.plan.rows)
                    self.release_unused()
            except ValueError:
                self.plan.rows, self.plan.theme, self.plan.revision = original
                result = {
                    'accepted': False,
                    'reason': 'La transition est engagée ou le titre n’est plus disponible.',
                }
            if not worker.dj.complete_command(
                worker.job['id'],
                worker.job['lease_token'],
                command['nonce'],
                result,
            ):
                raise PermissionError('dj_session_stopped')

    def publish(self, *, force=False):
        if not force and self.clock() - self.published < 1:
            return
        self.published = self.clock()
        self.worker.stage = (
            'paused'
            if self.paused
            else 'playing'
            if self.anchor is not None
            else 'rendering'
        )
        self.worker.publish(
            phase='paused' if self.paused else 'live',
            position=self.position(),
            rendered=self.mixer.position / RATE,
            next_mutable_at=self.plan.next_mutable_at(
                self.mixer.position / RATE
            ),
            duration=self.plan.rows[-1]['end'],
            timeline=self.plan.rows,
            theme=self.plan.theme,
            revision=self.plan.revision,
            renewals=self.plan.renewals,
            continuous=self.continuous,
            media_origin=self.media_origin,
            engine=self.worker.engine,
            runtime=self.runtime,
            render_speed=self.mixer.position
            / RATE
            / max(0.001, self.compute_seconds),
        )

    def render(self):
        encoder = HlsEncoder(self.io, self.worker.checkpoint)
        try:
            while (
                self.continuous
                or self.mixer.position < self.mixer.total_frames
            ):
                self.worker.checkpoint()
                self.commands()
                if self.idle():
                    return encoder.manifest
                self.extend()
                self.publish()
                if (
                    self.paused
                    or self.mixer.position / RATE >= self.position() + 24
                ):
                    self.sleep(0.1)
                    continue
                started = self.clock()
                encoder.write(self.mixer.read(RATE))
                self.compute_seconds += self.clock() - started
                self.release_unused()
                if self.anchor is None and encoder.ready():
                    self.media_origin = encoder.origin
                    self.live_started = time.time()
                    self.anchor = self.clock()
                    self.publish(force=True)
            encoder.finish()
            self.worker.checkpoint()
            if not self.worker.dj.publish(
                self.worker.job['id'],
                self.worker.job['lease_token'],
                'ready',
                {
                    'phase': 'ended',
                    'rendered': self.mixer.position / RATE,
                    'duration': self.plan.rows[-1]['end'],
                    'timeline': self.plan.rows,
                    'render_speed': self.mixer.position
                    / RATE
                    / max(0.001, self.compute_seconds),
                },
            ):
                raise PermissionError('dj_session_stopped')
            return encoder.manifest
        finally:
            encoder.close()
            self.release_unused(all_sources=True)
