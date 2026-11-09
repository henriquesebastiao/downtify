from downtify.music_ai import dj_worker


def test_exact_import_formatting_preserves_cached_analysis_identity(
    monkeypatch,
):
    old = (
        'def analyze_child(options):\n'
        '    from beat_this.inference import Audio2Beats\n'
        '    from .dj_evidence import profile_from_signal\n'
        '    analyze(options)\n'
    )
    formatted = old.replace('Audio2Beats\n', 'Audio2Beats\n\n')
    monkeypatch.setattr(dj_worker.inspect, 'getsource', lambda _: formatted)
    assert dj_worker.analysis_source(dj_worker.analyze_child) == old.encode()


def test_analysis_logic_and_other_functions_remain_in_the_identity(
    monkeypatch,
):
    before = (
        'def analyze_child(options):\n'
        '    from beat_this.inference import Audio2Beats\n\n'
        '    from .dj_evidence import profile_from_signal\n'
        '    analyze(options)\n'
    )
    changed = before.replace('analyze(options)', 'analyze_new(options)')
    monkeypatch.setattr(dj_worker.inspect, 'getsource', lambda _: before)
    first = dj_worker.analysis_source(dj_worker.analyze_child)
    monkeypatch.setattr(dj_worker.inspect, 'getsource', lambda _: changed)
    assert dj_worker.analysis_source(dj_worker.analyze_child) != first
    assert (
        dj_worker.analysis_source(dj_worker.validate_models)
        == changed.encode()
    )
