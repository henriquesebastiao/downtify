"""Offline synthetic benchmark; never reads a user's music or configuration."""

import __future__

import argparse
import ast
import hashlib
import importlib
import json
import subprocess
import sys
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--repo', type=Path, required=True)
parser.add_argument('--external', type=int, default=4000)
parser.add_argument(
    '--baseline-ref', default='6d7bebf00d7e41c011645b9ebe1de004c9e31e74'
)
args = parser.parse_args()
repo = args.repo.resolve()
sys.path.insert(0, str(repo))
ext = importlib.import_module('downtify.external_library')

baseline_text = subprocess.check_output(
    ['git', 'show', args.baseline_ref + ':downtify/external_library.py'],
    cwd=repo,
    text=True,
    encoding='utf-8',
)
tree = ast.parse(baseline_text)
nodes = [
    n
    for n in tree.body
    if isinstance(n, (ast.FunctionDef, ast.ClassDef))
    or isinstance(n, ast.Assign)
    or isinstance(n, ast.AnnAssign)
]
namespace = dict(vars(ext))
exec(
    compile(
        ast.Module(body=nodes, type_ignores=[]),
        '<baseline pure functions>',
        'exec',
        flags=__future__.annotations.compiler_flag,
    ),
    namespace,
)


def name(index: int) -> str:
    return 'Ensemble ' + hashlib.sha256(str(index).encode()).hexdigest()[:12]


owned = [
    {
        'file': f'owned/{i}.mp3',
        'title': f'Owned {i}',
        'artist': name(i % 800),
        'duration': 180,
    }
    for i in range(2000)
]
external = [
    {
        'file': ext.EXTERNAL_LIBRARY_PREFIX + f'synthetic/{i}.mp3',
        'title': f'External {i}',
        'artist': name(10000 + i % 200),
        'duration': 180,
    }
    for i in range(args.external)
]
entries = owned + external
times = {}
results = {}
for label, fn in [
    ('baseline', namespace['partition_extra_entries']),
    ('optimized', ext.partition_extra_entries),
]:
    start = time.perf_counter()
    results[label] = fn(entries)
    times[label] = time.perf_counter() - start
assert results['baseline'] == results['optimized'], 'Behavior changed'
print(
    json.dumps(
        {
            'entries': len(entries),
            'external': len(external),
            'external_artists': 200,
            'seconds': times,
            'speedup': times['baseline'] / times['optimized'],
            'identical': True,
        },
        indent=2,
    )
)
