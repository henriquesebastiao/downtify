"""Pinned Beat This inference, with model instances retained between inputs."""

from __future__ import annotations

import contextlib
import json
import math
import re
import signal
import sys

from .dj_audio import AudioError, AudioIO
from .dj_evidence import profile_from_signal


class AnalysisEngine:
    def __init__(self, options):
        import torch
        from beat_this.inference import Audio2Beats

        from .dj_worker import validate_models

        validate_models(options.models)
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        self.options = options
        self.torch = torch
        self.factory = Audio2Beats
        self.models = {}

    def model(self, name):
        if name not in self.models:
            self.models[name] = self.factory(
                str(self.options.models / (name + '.ckpt')),
                device='cpu',
                dbn=False,
            )
        return self.models[name]

    @staticmethod
    def positions(values, duration):
        if any(
            not math.isfinite(value)
            or value < -0.05
            or value > duration + 0.05
            for value in values
        ):
            raise AudioError('invalid_beat_positions')
        return [float(value) for value in values if 0 <= value < duration]

    def analyze(self, payload):
        options = self.options
        io = AudioIO(
            options.cache,
            options.root,
            budget=options.cache_bytes,
            min_free=options.min_free,
            workspace=payload.get('workspace', options.workspace),
        )
        if payload.get('snapshot'):
            io.allow_snapshot(payload['path'], payload['source_version'])
        chosen = ['small0']

        def tracker(audio, rate):
            with self.torch.inference_mode():
                beats, bars = self.model('small0')(audio, rate)
                beats = self.positions(beats, len(audio) / rate)
                bars = self.positions(bars, len(audio) / rate)
                evidence = profile_from_signal(
                    payload['id'], audio, rate, beats, bars
                )
                if 0.2 <= evidence.confidence < 0.75:
                    other_beats, other_bars = self.model('final0')(audio, rate)
                    other_beats = self.positions(
                        other_beats, len(audio) / rate
                    )
                    other_bars = self.positions(other_bars, len(audio) / rate)
                    other = profile_from_signal(
                        payload['id'], audio, rate, other_beats, other_bars
                    )
                    if other.confidence > evidence.confidence + 0.05:
                        beats, bars, chosen[0] = (
                            other_beats,
                            other_bars,
                            'final0',
                        )
                return beats, bars

        result = io.analyze(
            payload['id'],
            payload['path'],
            tracker,
            lambda: None,
            artist=payload.get('artist', ''),
            expected=payload['source_version'],
        )
        result['beat_model'] = chosen[0]
        return result


def serve(options):
    from .analysis_process import MAX_INPUT
    from .dj_worker import analysis_identity

    def stop(*_):
        # Unwind AudioIO/run_audio so decoder children are reaped before exit.
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    expected = analysis_identity()
    # Model diagnostics must never corrupt the bounded stdout protocol.
    with contextlib.redirect_stdout(sys.stderr):
        engine = AnalysisEngine(options)
    while True:
        line = sys.stdin.buffer.readline(MAX_INPUT + 1)
        if not line:
            return
        if len(line) > MAX_INPUT or not line.endswith(b'\n'):
            raise AudioError('unexpected_audio_input')
        request = json.loads(line)
        nonce = request.get('request_id', '')
        if not isinstance(nonce, str) or not re.fullmatch(
            '[a-f0-9]{32}', nonce
        ):
            raise AudioError('analysis_request_invalid')
        payload = request.get('payload')
        try:
            if (
                not isinstance(payload, dict)
                or payload.get('analysis_model') != expected
            ):
                raise AudioError('analysis_identity_changed')
            with contextlib.redirect_stdout(sys.stderr):
                result = engine.analyze(payload)
            response = {'request_id': nonce, 'result': result}
        except Exception:
            response = {
                'request_id': nonce,
                'error': 'dj_analysis_unavailable',
            }
        print(json.dumps(response), flush=True)
