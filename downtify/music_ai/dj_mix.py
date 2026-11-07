"""Bounded sequential stereo mixing, shared by file and HLS renderers."""

from __future__ import annotations

import math

import numpy as np


class StereoMixer:
    def __init__(self, timeline, source_for, *, rate=48000, position=0):
        from scipy.signal import butter

        if not timeline or not 8000 <= rate <= 192000:
            raise ValueError('A valid stereo timeline is required')
        self.rate = rate
        self.rows = timeline
        self.source_for = source_for
        if type(position) is not int or position < 0:
            raise ValueError('Invalid rendered position')
        self.position = position
        self.sos = butter(2, 180, fs=rate, output='sos').astype(np.float32)
        self.states = {}
        self.bounds = []
        for index, row in enumerate(timeline):
            start, end = row['start'], row['end']
            if (
                not all(math.isfinite(value) for value in (start, end))
                or not 0 <= start < end
            ):
                raise ValueError('Invalid timeline bounds')
            if index and (
                start < timeline[index - 1]['start']
                or start > timeline[index - 1]['end'] + 1 / rate
            ):
                raise ValueError('Timeline contains a gap or is out of order')
            self.bounds.append((round(start * rate), round(end * rate)))
        if self.bounds[0][0] > position or self.bounds[-1][1] < position:
            raise ValueError('A timeline must cover the rendered position')
        self.total_frames = self.bounds[-1][1]

    def replan(self, rows):
        replacement = StereoMixer(
            rows, self.source_for, rate=self.rate, position=self.position
        )
        # Only an already rendered prefix can disappear. Retained occurrences
        # keep their absolute sample positions and their running EQ state.
        keys = ('id', 'start', 'cue', 'speed')
        first = tuple(rows[0].get(key) for key in keys)
        drop = next(
            (
                i
                for i, row in enumerate(self.rows)
                if tuple(row.get(key) for key in keys) == first
            ),
            None,
        )
        if drop is None:
            if self.position:
                raise ValueError('Rendered audio cannot be changed')
            drop = 0
        if any(finish > self.position for _, finish in self.bounds[:drop]):
            raise ValueError('Rendered audio cannot be removed')
        for old_index in range(drop, len(self.rows)):
            index, old = old_index - drop, self.rows[old_index]
            if self.bounds[old_index][0] >= self.position:
                if (
                    index < len(rows)
                    and replacement.bounds[index][0] < self.position
                ):
                    raise ValueError('Rendered audio cannot be changed')
                break
            if index >= len(rows):
                raise ValueError('Rendered audio cannot be removed')
            new = rows[index]
            if any(old.get(key) != new.get(key) for key in keys):
                raise ValueError('Rendered audio cannot be changed')
            if self.bounds[old_index][1] <= self.position and old != new:
                raise ValueError('Rendered transitions cannot be changed')
            if (
                self.bounds[old_index][1] > self.position
                and replacement.bounds[index][1] < self.position
            ):
                raise ValueError('Rendered audio cannot be shortened')
        self.rows, self.bounds = rows, replacement.bounds
        self.total_frames = replacement.total_frames
        self.states = {
            index - drop: value
            for index, value in self.states.items()
            if drop <= index < len(rows) + drop
            and self.bounds[index - drop][0] < self.position
        }

    def read(self, count):
        from scipy.signal import sosfilt

        if not 1 <= count <= self.rate * 10:
            raise ValueError('Render chunks must be bounded to ten seconds')
        end = min(self.position + count, self.total_frames)
        mixed = np.zeros((end - self.position, 2), dtype=np.float32)
        occupied = np.zeros(len(mixed), dtype=np.uint8)
        for index, (row, (start, finish)) in enumerate(
            zip(self.rows, self.bounds)
        ):
            left, right = max(start, self.position), min(end, finish)
            if right <= left:
                continue
            source = self.source_for(index, row)
            if (
                source.ndim != 2
                or source.shape[1] != 2
                or len(source) < finish - start
            ):
                raise ValueError(
                    'Decoded stereo audio is shorter than the plan'
                )
            audio = np.asarray(
                source[left - start : right - start], dtype=np.float32
            )
            if not np.all(np.isfinite(audio)):
                raise ValueError('Decoded audio contains invalid samples')
            state = self.states.get(index)
            if state is None:
                state = np.zeros((len(self.sos), 2, 2), dtype=np.float32)
            low, self.states[index] = sosfilt(
                self.sos, audio, axis=0, zi=state
            )
            high = audio - low
            times = np.arange(left, right, dtype=np.float64)
            incoming = self.bounds[index - 1][1] - start if index else 0
            outgoing = (
                finish - self.bounds[index + 1][0]
                if index + 1 < len(self.rows)
                else 0
            )
            fade_in = (
                np.clip((times - start) / incoming, 0, 1)
                if incoming > 0
                else np.ones(len(times))
            )
            fade_out = (
                np.clip((times - (finish - outgoing)) / outgoing, 0, 1)
                if outgoing > 0
                else np.zeros(len(times))
            )
            gain = np.sin(np.pi / 2 * fade_in) * np.cos(np.pi / 2 * fade_out)
            # Keep bass overlap lower than the rest of the spectrum. The
            # complementary high/low split reconstructs the original elsewhere.
            bass = np.sin(
                np.pi / 2 * np.clip((fade_in - 0.3) / 0.7, 0, 1)
            ) * np.cos(np.pi / 2 * np.clip(fade_out / 0.7, 0, 1))
            destination = slice(left - self.position, right - self.position)
            mixed[destination] += high * gain[:, None] + low * bass[:, None]
            occupied[destination] += 1
            if right == finish:
                self.states.pop(index, None)
        if np.any(occupied > 2) or (len(occupied) and np.any(occupied == 0)):
            raise ValueError(
                'A mix requires continuous audio and at most two decks'
            )
        self.position = end
        return mixed
