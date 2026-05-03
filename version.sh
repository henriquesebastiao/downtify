#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

usage() {
  echo "Usage: $0 <new-version>"
  echo "       $0 --current"
  echo
  echo "Examples:"
  echo "  $0 2.6.0"
  echo "  $0 --current"
  exit 1
}

# ── helpers ────────────────────────────────────────────────────────────────────

current_version() {
  grep -m1 "__version__" "$REPO_ROOT/downtify/__init__.py" \
    | sed "s/__version__ = '//;s/'//"
}

validate_semver() {
  if ! echo "$1" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo "Error: '$1' is not a valid semver version (expected X.Y.Z)." >&2
    exit 1
  fi
}

# ── argument parsing ────────────────────────────────────────────────────────────

[[ $# -eq 1 ]] || usage

if [[ "$1" == "--current" ]]; then
  echo "$(current_version)"
  exit 0
fi

NEW_VERSION="$1"
validate_semver "$NEW_VERSION"

OLD_VERSION="$(current_version)"

if [[ "$OLD_VERSION" == "$NEW_VERSION" ]]; then
  echo "Already at version $NEW_VERSION — nothing to do."
  exit 0
fi

echo "Bumping $OLD_VERSION → $NEW_VERSION"

# ── downtify/__init__.py ───────────────────────────────────────────────────────

sed -i "s/__version__ = '${OLD_VERSION}'/__version__ = '${NEW_VERSION}'/" \
  "$REPO_ROOT/downtify/__init__.py"
echo "  updated downtify/__init__.py"

# ── pyproject.toml ─────────────────────────────────────────────────────────────

sed -i "s/^version = \"${OLD_VERSION}\"/version = \"${NEW_VERSION}\"/" \
  "$REPO_ROOT/pyproject.toml"
echo "  updated pyproject.toml"

# ── frontend/package.json ──────────────────────────────────────────────────────

sed -i "s/\"version\": \"${OLD_VERSION}\"/\"version\": \"${NEW_VERSION}\"/" \
  "$REPO_ROOT/frontend/package.json"
echo "  updated frontend/package.json"

# ── verify ─────────────────────────────────────────────────────────────────────

echo
echo "Verification:"
grep "__version__"   "$REPO_ROOT/downtify/__init__.py"
grep "^version"      "$REPO_ROOT/pyproject.toml"
grep '"version"'     "$REPO_ROOT/frontend/package.json" | head -1
