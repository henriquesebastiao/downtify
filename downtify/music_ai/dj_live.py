"""Short-horizon server renderer. No original file is ever an output."""

from __future__ import annotations

import time
from copy import deepcopy

import numpy as np

from .dj_audio import RATE
from .dj_hls import HlsEncoder
from .dj_live_plan import LivePlan
from .dj_mix import StereoMixer
from .dj_plan import Profile
from .dj_preparation import SinglePreparation
from .dj_prepared_deck import (
    decode_deck,
    discard_analysis,
    discard_decoded,
    prepare_analysis,
)
from .dj_validation import runtime_identity


class LiveRenderer:
    def __init__(
        self, worker, io, results, *, clock=time.monotonic, sleep=time.sleep
    ):
        self.worker, self.io, self.results = worker, io, results
        self.clock, self.sleep = clock, sleep
        initial_count = len(results)
        self.plan = LivePlan(
            [Profile(**value['profile']) for value in results.values()],
            worker.job['theme'],
            order=worker.job['ids'][:initial_count]
            if worker.job.get('queue_order') or worker.job.get('seed_id')
            else None,
        )
        self.sources = {}
        self.pending_ids = list(worker.job['ids'][initial_count:])
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
        self.pool_checked = -10.0
        self.refill_revision = 0
        self.live_started = None
        self.preparation = SinglePreparation()
        self.preparing = None
        self.pending_change = None
        self.candidate = None

    def window(self, plan=None):
        """Oldest audible deck and at most three following occurrences."""
        return [
            row
            for row in (plan or self.plan).rows
            if round(row['end'] * RATE) > self.mixer.position
        ][:4]

    def wanted_rows(self):
        rows = self.window()
        if self.candidate is not None:
            rows += self.window(self.candidate)
        return rows

    def has_source(self, row):
        source = self.sources.get(self.key(row))
        return source is not None and len(source) >= (
            round(row['end'] * RATE) - round(row['start'] * RATE)
        )

    def block_ready(self):
        """Preflight the entire block before StereoMixer mutates EQ state."""
        end = min(self.mixer.position + RATE, self.mixer.total_frames)
        return all(
            self.has_source(row) and self.range_ready(row, start, finish, end)
            for row, (start, finish) in zip(self.mixer.rows, self.mixer.bounds)
            if start < end and finish > self.mixer.position
        )

    def range_ready(self, row, start, finish, end):
        source = self.sources[self.key(row)]
        if hasattr(source, 'ready'):
            return source.ready(
                max(start, self.mixer.position) - start,
                min(end, finish) - start,
            )
        return True

    def compute_ready(self):
        if hasattr(self.worker, 'try_require_compute'):
            return self.worker.try_require_compute()
        return True

    def complete(self, command, result):
        worker = self.worker
        if not worker.dj.complete_command(
            worker.job['id'],
            worker.job['lease_token'],
            command['nonce'],
            result,
        ):
            raise PermissionError('dj_session_stopped')

    def update_candidate(self):
        if self.pending_change is None:
            return
        command = self.pending_change
        try:
            candidate = deepcopy(self.plan)
            result = candidate.change(
                command['action'],
                command['payload'],
                self.mixer.position / RATE,
                self.position(),
            )
            self.candidate = candidate
            if all(self.has_source(row) for row in self.window(candidate)):
                # Rebase on the current rendered cursor, never a captured one.
                self.mixer.replan(candidate.rows)
                self.plan = candidate
                self.pending_change = self.candidate = None
                self.complete(command, {'accepted': True, **result})
        except ValueError:
            self.pending_change = self.candidate = None
            self.complete(
                command,
                {
                    'accepted': False,
                    'reason': 'La transition est engagée ou le titre n’est plus disponible.',
                },
            )

    def reap(self):
        finished = self.preparation.poll()
        if finished is None:
            return
        task, self.preparing = self.preparing, None
        self.compute_seconds += max(0.0, time.monotonic() - task['started'])
        current = self.worker.job['sources'].get(task['id'], {})
        valid = all(
            current.get(key) == task['source'].get(key)
            for key in ('path', 'source_version', 'fingerprint')
        )
        if finished.cancelled or not valid:
            if finished.value is not None:
                if task['kind'] == 'analysis':
                    discard_analysis(finished.value, self.io)
                else:
                    discard_decoded(finished.value, self.io)
            return
        if finished.error is not None:
            raise finished.error
        value = finished.value
        if task['kind'] == 'analysis':
            wanted = {row['id'] for row in self.wanted_rows()}
            if task.get('append') and len(self.window()) < 4:
                try:
                    self.plan.append(
                        [Profile(**value.result['profile'])],
                        self.mixer.position / RATE,
                    )
                    self.plan.trim(self.mixer.position / RATE)
                    self.mixer.replan(self.plan.rows)
                except BaseException:
                    discard_analysis(value, self.io)
                    raise
                wanted.add(value.track)
                if self.pending_ids and self.pending_ids[0] == value.track:
                    self.pending_ids.pop(0)
            if value.track not in wanted:
                discard_analysis(value, self.io)
                return
            snapshot = value.source['snapshot']
            self.io.allow_snapshot(
                snapshot['path'], snapshot['source_version']
            )
            self.worker.job['sources'][value.track] = value.source
            self.results[value.track] = value.result
        elif value.key in {self.key(row) for row in self.wanted_rows()}:
            self.sources[value.key] = (
                value.buffer
                if value.buffer is not None
                else np.memmap(
                    value.path, mode='r', dtype='<f4', shape=(value.frames, 2)
                )
            )
            self.files[value.key] = value.path
        else:
            discard_decoded(value, self.io)

    def schedule(self, row, *, append=False):
        if self.preparation.busy or not self.compute_ready():
            return
        identity = row['id']
        source = deepcopy(self.worker.job['sources'][identity])
        task = {
            'id': identity,
            'source': source,
            'started': time.monotonic(),
            'append': append,
        }
        if append or 'snapshot' not in source:
            occupied = {
                path.name for path in self.io.workspace.glob('source-*.audio')
            }
            slot = next(
                index
                for index in range(40)
                if f'source-{index}.audio' not in occupied
            )
            task['kind'] = 'analysis'

            def work(checkpoint):
                return prepare_analysis(
                    self.worker, self.io, identity, source, slot, checkpoint
                )

        else:
            task['kind'] = 'decode'
            key, result, row = (
                self.key(row),
                deepcopy(self.results[identity]),
                deepcopy(row),
            )
            self.decoded += 1
            target = self.io.workspace / f'decoded-{self.decoded}.pcm'
            task['key'] = key

            def work(checkpoint):
                return decode_deck(
                    self.io,
                    row,
                    result,
                    source,
                    key,
                    target,
                    checkpoint,
                    progressive=True,
                )

        self.preparing = task
        self.preparation.submit(task, work)

    def prepare(self):
        """Owner-only publication; slow I/O never runs on the HLS thread."""
        self.reap()
        self.update_candidate()
        self.release_unused()
        if self.preparation.busy:
            wanted = self.wanted_rows()
            if self.preparing['kind'] == 'decode' and self.preparing[
                'key'
            ] not in {self.key(row) for row in wanted}:
                self.preparation.cancel()
            return
        for row in self.wanted_rows():
            if not self.has_source(row):
                self.schedule(row)
                return
        self.extend()

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
        """Prepare at most three following decks without restarting HLS."""
        if not self.continuous and not self.pending_ids:
            return
        if (
            self.continuous
            and self.clock() - self.pool_checked >= 5
            and hasattr(self.worker.dj, 'sources')
        ):
            self.pool_checked = self.clock()
            latest = self.worker.dj.get(
                self.worker.job['owner'], self.worker.job['id']
            )
            if latest.get('refill_revision', 0) != self.refill_revision:
                self.refill_revision = latest.get('refill_revision', 0)
                sources = self.worker.dj.sources(
                    self.worker.job['owner'], self.worker.job['id']
                )
                fresh = [
                    identity
                    for identity in latest['ids']
                    if identity not in self.worker.job['sources']
                ]
                self.worker.job['sources'].update(sources)
                self.pending_ids.extend(fresh)
        # Keep at least two complete future decks. An extension changes only
        # the last, unrendered transition, never the current or next deck.
        if len(self.window()) >= 4 or self.pending_change is not None:
            return
        if self.pending_ids:
            self.schedule({'id': self.pending_ids[0]}, append=True)
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
            selected = order_tracks(candidates, self.plan.theme, limit=2)[:1]
        if selected:
            self.schedule({'id': selected[0].id}, append=True)

    def position(self):
        if self.paused or self.anchor is None:
            return self.anchor_position
        return min(
            self.mixer.position / RATE,
            self.anchor_position + self.clock() - self.anchor,
        )

    @staticmethod
    def key(row):
        return row['id'], row['cue'], row['speed'], row['start']

    def source_for(self, index, row):
        key = self.key(row)
        if key not in self.sources:
            raise RuntimeError('dj_deck_not_prepared')
        return self.sources[key]

    def release_unused(self, *, all_sources=False):
        active = {self.key(row) for row in self.wanted_rows()}
        for key in list(self.sources):
            if all_sources or key not in active:
                source = self.sources.pop(key)
                if hasattr(source, 'close'):
                    source.close()
                else:
                    source._mmap.close()
                self.files.pop(key).unlink(missing_ok=True)
        if hasattr(self.worker, 'release_decks'):
            keep = (
                set()
                if all_sources
                else {row['id'] for row in self.wanted_rows()}
            )
            if not all_sources and self.preparing is not None:
                keep.add(self.preparing['id'])
            self.worker.release_decks(self.io, keep)

    def commands(self):
        if self.clock() - self.command_checked < 0.5:
            return
        self.command_checked = self.clock()
        worker = self.worker
        for command in worker.dj.pending_commands(
            worker.job['id'], worker.job['lease_token']
        ):
            action = command['action']
            navigation = command.get('navigation')
            if (
                navigation
                and navigation.get('accepted')
                and 'seek_to_seconds' in navigation
            ):
                # A seek changes the transport cursor, never the latest pause intent.
                self.anchor_position = navigation['seek_to_seconds']
                self.anchor = self.clock()
                self.complete(command, navigation)
            elif action in {'pause', 'resume'}:
                position = self.position()
                self.paused = action == 'pause'
                self.anchor_position, self.anchor = position, self.clock()
                self.complete(
                    command, {'accepted': True, 'effective_after_seconds': 0.0}
                )
            elif self.pending_change is None:
                self.pending_change = command
            elif self.pending_change['nonce'] != command['nonce']:
                # Serialize plan edits; never prepare an unbounded command queue.
                self.complete(
                    command,
                    {
                        'accepted': False,
                        'reason': 'Une modification du mix est déjà en préparation.',
                    },
                )

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
            remaining_decks=len(self.pending_ids),
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
                self.prepare()
                if self.idle():
                    return encoder.manifest
                self.publish()
                if (
                    self.paused
                    or self.mixer.position / RATE >= self.position() + 24
                ):
                    if (
                        not self.preparation.busy
                        and all(
                            getattr(source, 'idle', True)
                            for source in self.sources.values()
                        )
                        and hasattr(self.worker, 'yield_compute')
                    ):
                        self.worker.yield_compute()
                    self.sleep(0.1)
                    continue
                if not self.block_ready() or not self.compute_ready():
                    self.sleep(0.05)
                    continue
                started = time.monotonic()
                encoder.write(self.mixer.read(RATE))
                self.compute_seconds += time.monotonic() - started
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
            self.preparation.close()
            # A cancelled task may have completed just before cancellation.
            # Dispose its result before Worker.step can remove the workspace.
            finished = self.preparation.poll()
            if finished is not None and finished.value is not None:
                if self.preparing['kind'] == 'analysis':
                    discard_analysis(finished.value, self.io)
                else:
                    discard_decoded(finished.value, self.io)
            self.preparing = None
            encoder.close()
            self.release_unused(all_sources=True)
