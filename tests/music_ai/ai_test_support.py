"""Explicit opt-in for functional fixtures written before beta became off by default."""

from downtify.music_ai.store import ANALYSIS_FEATURES, Store


def opted_in_store(path):
    database = Store(path)
    flags = dict.fromkeys(ANALYSIS_FEATURES, True)
    for owner in (-1, 1, 2):
        database.set_preferences(owner, flags)
    return database
