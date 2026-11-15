"""Fetch public SQLite source; verify the official release's SHA3 before use."""

import argparse
import hashlib
import io
import json
import urllib.request
import zipfile
from pathlib import Path

URL = 'https://www.sqlite.org/2026/sqlite-amalgamation-3530400.zip'
SOURCE_ID = '2026-07-24 19:02:57 bf7c7f30031888f4e796e429ab3978879485813aaca6f641c7b33e4e09459bcc'
SOURCE_SHA3 = (
    '67f423e9ebbbdc473cbc4772c872ee6b89f31fde4ed0279a5c25d5f65c043a16'
)
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
options = parser.parse_args()
with urllib.request.urlopen(URL, timeout=60) as response:
    payload = response.read(8 * 1024**2 + 1)
if len(payload) > 8 * 1024**2:
    raise RuntimeError('Unexpected source archive size')
with zipfile.ZipFile(io.BytesIO(payload)) as archive:
    files = {
        name: archive.read('sqlite-amalgamation-3530400/' + name)
        for name in ('sqlite3.c', 'sqlite3.h')
    }
if hashlib.sha3_256(files['sqlite3.c']).hexdigest() != SOURCE_SHA3:
    raise RuntimeError(
        'SQLite source differs from the official release digest'
    )
if (
    SOURCE_ID.encode() not in files['sqlite3.h']
    or b'#define SQLITE_VERSION        "3.53.4"' not in files['sqlite3.h']
):
    raise RuntimeError('Unexpected SQLite source identity')
options.output.mkdir(parents=True, exist_ok=True)
for name, content in files.items():
    (options.output / name).write_bytes(content)
manifest = {
    'version': '3.53.4',
    'url': URL,
    'source_id': SOURCE_ID,
    'source_sha3': SOURCE_SHA3,
    'files': {
        name: hashlib.sha256(content).hexdigest()
        for name, content in files.items()
    },
}
(options.output / 'manifest.json').write_text(
    json.dumps(manifest, indent=2), encoding='utf-8'
)
print(json.dumps(manifest))
