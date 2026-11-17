"""Row type compatible with ``sqlite3.Row`` for PostgreSQL results."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from functools import lru_cache
from typing import Any


@lru_cache(maxsize=256)
def _name_index(keys: tuple[str, ...]) -> dict[str, int]:
    """Map lower-cased column names to their first index."""
    index: dict[str, int] = {}
    for position, name in enumerate(keys):
        index.setdefault(name.lower(), position)
    return index


class Row(tuple):
    """Tuple of values that also supports lookup by column name.

    Behaves like ``sqlite3.Row``: integer and slice indexing, plus
    case-insensitive column name lookup. Iteration, equality and hashing
    follow the plain tuple of values.
    """

    def __new__(cls, keys: Sequence[str], values: Sequence[Any]) -> Row:
        self = super().__new__(cls, values)
        self._keys = tuple(keys)
        self._index = _name_index(self._keys)
        return self

    def __getnewargs__(self) -> tuple[tuple[str, ...], tuple[Any, ...]]:
        return (self._keys, tuple(self))

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, str):
            position = self._index.get(key.lower())
            if position is None:
                raise IndexError('No item with that key')
            return tuple.__getitem__(self, position)
        return tuple.__getitem__(self, key)

    def keys(self) -> list[str]:
        """Return the column names in their original case."""
        return list(self._keys)

    def get(self, key: Any, default: Any = None) -> Any:
        """Return the value for ``key`` or ``default`` if it is missing."""
        try:
            return self[key]
        except (IndexError, TypeError):
            return default


def pg_row_factory(cursor: Any) -> Callable[[Sequence[Any]], Row]:
    """psycopg row factory producing ``Row`` objects.

    Column names are read from ``cursor.description`` once per result set.
    """
    description = cursor.description or []
    keys = tuple(column.name for column in description)

    def make_row(values: Sequence[Any]) -> Row:
        return Row(keys, values)

    return make_row
