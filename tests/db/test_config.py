from __future__ import annotations

from pathlib import Path

import pytest

from downtify.db.config import GROUP_FILES, DbConfig, Dialect


def test_defaults_from_empty_env():
    cfg = DbConfig.from_env({})
    assert cfg == DbConfig()
    assert cfg.url is None
    assert cfg.data_dir == Path('/data')
    assert cfg.pool_min == 2
    assert cfg.pool_max == 20
    assert cfg.pool_timeout == 10.0


def test_dataclass_defaults():
    cfg = DbConfig()
    assert cfg.url is None
    assert cfg.data_dir == Path('/data')
    assert cfg.pool_min == 2
    assert cfg.pool_max == 20
    assert cfg.pool_timeout == 10.0


def test_dialect_sqlite_without_url():
    assert DbConfig().dialect is Dialect.SQLITE
    assert DbConfig.from_env({}).dialect is Dialect.SQLITE


def test_dialect_postgres_with_url():
    cfg = DbConfig.from_env({'DATABASE_URL': 'postgresql://u:p@h/db'})
    assert cfg.dialect is Dialect.POSTGRES
    cfg = DbConfig.from_env({'DATABASE_URL': 'postgres://u:p@h/db'})
    assert cfg.dialect is Dialect.POSTGRES


def test_dialect_values():
    assert Dialect.SQLITE.value == 'sqlite'
    assert Dialect.POSTGRES.value == 'postgres'


def test_empty_or_blank_url_is_none():
    assert DbConfig.from_env({'DATABASE_URL': ''}).url is None
    assert DbConfig.from_env({'DATABASE_URL': '   '}).url is None


def test_url_is_stripped():
    cfg = DbConfig.from_env({'DATABASE_URL': '  postgres://h/db  '})
    assert cfg.url == 'postgres://h/db'


def test_sqlite_path_for_every_group(tmp_path):
    cfg = DbConfig(data_dir=tmp_path)
    assert set(GROUP_FILES) == {
        'library',
        'monitor',
        'auth',
        'activity',
        'doctor_hashes',
        'doctor_dupes',
    }
    for group, filename in GROUP_FILES.items():
        assert cfg.sqlite_path(group) == tmp_path / filename


def test_sqlite_path_specific_files():
    cfg = DbConfig(data_dir=Path('/d'))
    assert cfg.sqlite_path('library') == Path('/d/downtify_library.db')
    assert cfg.sqlite_path('doctor_hashes') == Path(
        '/d/doctor/audio_hashes.db'
    )
    assert cfg.sqlite_path('doctor_dupes') == Path('/d/doctor/duplicates.db')


def test_sqlite_path_unknown_group_raises():
    with pytest.raises(ValueError, match='unknown DB group'):
        DbConfig().sqlite_path('nope')


def test_data_dir_from_env():
    cfg = DbConfig.from_env({'DATABASE_DIR': '/srv/dl'})
    assert cfg.data_dir == Path('/srv/dl')


def test_pool_values_parsed_from_env():
    cfg = DbConfig.from_env({
        'DB_POOL_MIN': '3',
        'DB_POOL_MAX': ' 8 ',
        'DB_POOL_TIMEOUT': '2.5',
    })
    assert cfg.pool_min == 3
    assert cfg.pool_max == 8
    assert cfg.pool_timeout == 2.5


def test_blank_pool_values_use_defaults():
    cfg = DbConfig.from_env({'DB_POOL_MIN': '', 'DB_POOL_TIMEOUT': ' '})
    assert cfg.pool_min == 2
    assert cfg.pool_timeout == 10.0


def test_pool_timeout_integer_string_parsed_as_float():
    cfg = DbConfig.from_env({'DB_POOL_TIMEOUT': '5'})
    assert cfg.pool_timeout == 5.0


def test_url_without_postgres_scheme_rejected():
    with pytest.raises(ValueError, match='DATABASE_URL'):
        DbConfig.from_env({'DATABASE_URL': 'mysql://h/db'})


def test_url_error_does_not_leak_password():
    secret = 'hunter2'
    with pytest.raises(ValueError, match='must start with') as excinfo:
        DbConfig.from_env({'DATABASE_URL': f'mysql://u:{secret}@h/db'})
    assert secret not in str(excinfo.value)


def test_non_numeric_pool_min_rejected():
    with pytest.raises(ValueError, match='DB_POOL_MIN'):
        DbConfig.from_env({'DB_POOL_MIN': 'abc'})


def test_non_numeric_pool_max_rejected():
    with pytest.raises(ValueError, match='DB_POOL_MAX'):
        DbConfig.from_env({'DB_POOL_MAX': 'ten'})


def test_non_numeric_pool_timeout_rejected():
    with pytest.raises(ValueError, match='DB_POOL_TIMEOUT'):
        DbConfig.from_env({'DB_POOL_TIMEOUT': 'soon'})


def test_float_pool_min_rejected_as_not_integer():
    with pytest.raises(ValueError, match='DB_POOL_MIN'):
        DbConfig.from_env({'DB_POOL_MIN': '2.5'})


def test_negative_pool_min_rejected():
    with pytest.raises(ValueError, match='DB_POOL_MIN must be >= 0'):
        DbConfig.from_env({'DB_POOL_MIN': '-1'})


def test_zero_pool_min_allowed():
    cfg = DbConfig.from_env({'DB_POOL_MIN': '0', 'DB_POOL_MAX': '1'})
    assert cfg.pool_min == 0


def test_pool_max_below_one_rejected():
    with pytest.raises(ValueError, match='DB_POOL_MAX must be >= 1'):
        DbConfig.from_env({'DB_POOL_MIN': '0', 'DB_POOL_MAX': '0'})


def test_pool_max_below_pool_min_rejected():
    with pytest.raises(ValueError, match='DB_POOL_MAX must be >= DB_POOL_MIN'):
        DbConfig.from_env({'DB_POOL_MIN': '5', 'DB_POOL_MAX': '4'})


def test_pool_max_equal_pool_min_allowed():
    cfg = DbConfig.from_env({'DB_POOL_MIN': '5', 'DB_POOL_MAX': '5'})
    assert cfg.pool_min == cfg.pool_max == 5


def test_from_env_defaults_to_os_environ(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgres://h/db')
    monkeypatch.setenv('DATABASE_DIR', '/x')
    cfg = DbConfig.from_env()
    assert cfg.url == 'postgres://h/db'
    assert cfg.data_dir == Path('/x')


def test_search_path_defaults_to_none():
    assert DbConfig.from_env({}).search_path is None


def test_search_path_read_from_env():
    cfg = DbConfig.from_env({'DB_SEARCH_PATH': ' tenant_a '})
    assert cfg.search_path == 'tenant_a'


def test_blank_search_path_is_none():
    assert DbConfig.from_env({'DB_SEARCH_PATH': '  '}).search_path is None


@pytest.mark.parametrize(
    'value', ['a b', 'x;drop table', '1abc', 'a-b', 'a.b', 'x' * 64]
)
def test_search_path_must_be_plain_identifier(value):
    with pytest.raises(ValueError, match='DB_SEARCH_PATH'):
        DbConfig.from_env({'DB_SEARCH_PATH': value})
