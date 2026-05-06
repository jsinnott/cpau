#!/usr/bin/env bash
#
# Refresh src/cpau/baseapp.py from the local checkout of jsinnott_utils.
#
# This package is public, so it cannot depend on the (private) jsinnott_utils
# package as a normal dependency. Instead we vendor BaseApp into the source
# tree and refresh it via this script. The vendored copy gets a header
# noting the source version so consumers know where it came from.
#
# Run this whenever a new version of jsinnott_utils is published with
# changes that should be picked up here.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE_REPO="${HOME}/code/python-utils"
SOURCE_FILE="${SOURCE_REPO}/src/jsinnott_utils/baseapp.py"
DEST_FILE="${PROJECT_ROOT}/src/cpau/baseapp.py"

if [[ ! -f "$SOURCE_FILE" ]]; then
    echo "ERROR: source file not found: $SOURCE_FILE" >&2
    echo "       (expected a local checkout of jsinnott_utils at $SOURCE_REPO)" >&2
    exit 1
fi

# Extract the version from the source repo's pyproject.toml.
VERSION=$(awk -F'"' '/^version/ {print $2; exit}' "${SOURCE_REPO}/pyproject.toml")
if [[ -z "$VERSION" ]]; then
    echo "ERROR: could not determine version from ${SOURCE_REPO}/pyproject.toml" >&2
    exit 1
fi

# Write the destination file: header banner + verbatim source.
{
    echo "# This file is vendored from jsinnott_utils v${VERSION}."
    echo "# Do NOT edit it here — run tools/sync_baseapp.sh to refresh."
    echo "#"
    echo "# Source: ${SOURCE_FILE}"
    echo
    cat "$SOURCE_FILE"
} > "$DEST_FILE"

echo "Synced ${DEST_FILE} from jsinnott_utils v${VERSION}"
