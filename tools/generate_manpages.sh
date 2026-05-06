#!/usr/bin/env bash
#
# Regenerate man/*.1 files from the argparse definitions in cpau.cli.
# Run this whenever a CLI's arguments, DESCRIPTION, or EPILOG change.
# The output is checked into git so consumers installing from a wheel
# get the man pages without needing argparse-manpage themselves.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"
mkdir -p man

TOOLS=(
    "cpau.cli:build_parser_electric:cpau-electric"
    "cpau.cli:build_parser_water:cpau-water"
    "cpau.cli:build_parser_availability:cpau-availability"
)

for entry in "${TOOLS[@]}"; do
    module="$(echo "$entry" | cut -d: -f1)"
    fn="$(echo "$entry" | cut -d: -f2)"
    prog="$(echo "$entry" | cut -d: -f3)"
    echo "Generating man/${prog}.1 ..."
    argparse-manpage \
        --module "$module" \
        --function "$fn" \
        --prog "$prog" \
        --project-name "cpau" \
        --author "Joe Sinnott <joe@jsinnott.net>" \
        --author "Claude <noreply@anthropic.com>" \
        --output "man/${prog}.1"
done

echo "Done."
