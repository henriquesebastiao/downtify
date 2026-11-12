"""Request logging remains quiet after Uvicorn config initialization."""

from __future__ import annotations

import logging

import pytest
from uvicorn import Config

import main


@pytest.mark.parametrize('level', ['INFO', 'DEBUG'])
def test_request_logging_levels(monkeypatch, level):
    names = (
        'httpx',
        'httpcore',
        'uvicorn',
        'uvicorn.error',
        'uvicorn.access',
        'fastapi',
    )
    for name in names:
        log = logging.getLogger(name)
        monkeypatch.setattr(log, 'level', log.level)
        monkeypatch.setattr(log, 'handlers', log.handlers[:])
        monkeypatch.setattr(log, 'propagate', log.propagate)
    monkeypatch.setattr(main.logger, 'remove', lambda: None)
    monkeypatch.setattr(main.logger, 'add', lambda *a, **k: None)
    monkeypatch.setattr(logging, 'basicConfig', lambda **k: None)
    main._setup_logging(level)
    Config(app=object(), log_level=None, log_config=None)
    assert not logging.getLogger('httpx').isEnabledFor(logging.INFO)
    assert not logging.getLogger('httpcore').isEnabledFor(logging.INFO)
    assert logging.getLogger('httpx').isEnabledFor(logging.WARNING)
    assert logging.getLogger('uvicorn.access').isEnabledFor(logging.INFO) == (
        level == 'DEBUG'
    )
    assert logging.getLogger('uvicorn.error').isEnabledFor(logging.ERROR)
