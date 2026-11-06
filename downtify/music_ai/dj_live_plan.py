"""Change only an uncommitted DJ transition; all positions are absolute seconds."""

from __future__ import annotations

import math
from dataclasses import asdict, replace

from .dj_plan import Profile, order_tracks, timeline, transition
from .store import MOODS


def tail(profiles, first, *, skip_after=None):
    start, cue, speed = first['start'], first['cue'], first['speed']
    result = []
    for index, profile in enumerate(profiles):
        mix = (
            transition(profile, profiles[index + 1], speed)
            if index + 1 < len(profiles)
            else None
        )
        if index == 0 and skip_after is not None and mix:
            minimum = cue + (skip_after - start + mix.overlap) * speed
            ends = [
                beat
                for beat in profile.downbeats
                if minimum <= beat <= profile.duration
            ]
            end = ends[0] if ends else min(profile.duration, minimum)
            mix = replace(
                mix,
                source_end=end,
                aligned=mix.aligned and bool(ends),
                reason='Prochain titre · transition adaptée au tampon déjà rendu',
            )
        source_end = mix.source_end if mix else profile.duration
        if source_end <= cue:
            raise ValueError('Insufficient uncommitted audio')
        end = start + (source_end - cue) / speed
        row = {
            'id': profile.id,
            'start': start,
            'end': end,
            'cue': cue,
            'source_end': source_end,
            'speed': speed,
            'transition': asdict(mix) if mix else None,
        }
        result.append(row)
        if mix:
            if mix.overlap >= end - start:
                raise ValueError('Insufficient uncommitted audio')
            start, cue, speed = (
                end - mix.overlap,
                mix.incoming_cue,
                mix.incoming_speed,
            )
    return result


class LivePlan:
    def __init__(
        self, profiles: list[Profile], theme: str, *, order=None, cue=0.0
    ):
        self.profiles = {item.id: item for item in profiles}
        self.theme = theme
        selected = (
            [self.profiles[identity] for identity in order]
            if order is not None
            else order_tracks(profiles, theme, limit=len(profiles))
        )
        if len(selected) < 2 or not math.isfinite(cue) or cue < 0:
            raise ValueError('A queue needs two playable occurrences')
        self.rows = (
            tail(selected, {'start': 0.0, 'cue': cue, 'speed': 1.0})
            if cue
            else timeline(selected)
        )
        self.revision = 0
        self.renewals = 0

    def append(self, profiles, rendered, *, guard=6.0):
        """Join new decks beyond the committed horizon, retaining the encoder."""
        if not profiles or not math.isfinite(rendered) or rendered < 0:
            raise ValueError('Invalid continuation')
        last = self.rows[-1]
        updated = tail([self.profiles[last['id']], *profiles], last)
        if updated[1]['start'] < rendered + guard - 1e-8:
            raise ValueError('The last transition is already committed')
        self.profiles.update({profile.id: profile for profile in profiles})
        self.rows = self.rows[:-1] + updated
        self.revision += 1
        self.renewals += 1

    def trim(self, rendered, *, keep=2):
        """Bound the live timeline while keeping a little title history."""
        if not math.isfinite(rendered) or rendered < 0 or not 0 <= keep <= 8:
            raise ValueError('Invalid live history')
        ended = 0
        for row in self.rows:
            if row['end'] > rendered:
                break
            ended += 1
        drop = max(0, ended - keep)
        if drop:
            self.rows = self.rows[drop:]
        return drop

    def mutable_index(self, rendered, *, guard=6.0):
        if not math.isfinite(rendered) or rendered < 0:
            raise ValueError('Invalid rendered position')
        boundary = rendered + guard
        return max(
            index
            for index, row in enumerate(self.rows)
            if row['start'] <= boundary
        )

    def change(self, action, payload, rendered, playhead, *, guard=6.0):
        if action not in {'next', 'replace', 'theme'} or not isinstance(
            payload, dict
        ):
            raise ValueError('Invalid live plan command')
        if not math.isfinite(playhead) or not 0 <= playhead <= rendered:
            raise ValueError('Invalid playback position')
        index = self.mutable_index(rendered, guard=guard)
        if index + 1 >= len(self.rows):
            raise ValueError('No uncommitted transition remains')
        first = self.rows[index]
        used = {row['id'] for row in self.rows[: index + 1]}
        remaining = [
            self.profiles[row['id']] for row in self.rows[index + 1 :]
        ]
        theme = (
            payload.get('theme', self.theme)
            if action == 'theme'
            else self.theme
        )
        if theme not in MOODS:
            raise ValueError('Unknown musical theme')
        if action == 'replace':
            identity = payload.get('id')
            if identity not in self.profiles or identity in used:
                raise ValueError(
                    'Replacement must be an unused analyzed track from this set'
                )
            chosen = self.profiles[identity]
            remaining = [chosen] + [
                item for item in remaining if item.id != identity
            ]
        elif action == 'theme' and len(remaining) >= 2:
            remaining = order_tracks(remaining, theme, limit=len(remaining))
        updated = tail(
            [self.profiles[first['id']], *remaining],
            first,
            skip_after=rendered + guard if action == 'next' else None,
        )
        if updated[1]['start'] < rendered + guard - 1e-8:
            raise ValueError('The next transition is already committed')
        self.rows = self.rows[:index] + updated
        self.theme = theme
        self.revision += 1
        return {
            'revision': self.revision,
            'effective_at': updated[1]['start'],
            'effective_after_seconds': max(
                0.0, updated[1]['start'] - playhead
            ),
        }

    def next_mutable_at(self, rendered):
        index = self.mutable_index(rendered)
        return (
            self.rows[index + 1]['start']
            if index + 1 < len(self.rows)
            else self.rows[-1]['end']
        )
