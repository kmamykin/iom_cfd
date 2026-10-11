#!/bin/bash
# Load the OpenFOAM environment, then run the given command in the current
# working directory. The stock /openfoam/run entrypoint changes to $HOME,
# which breaks `docker run -w /work ...`, so we use this instead.

# OpenFOAM's bashrc is not `set -u` safe and may return non-zero; that's fine.
# shellcheck disable=SC1090
source "${FOAM_BASHRC:?FOAM_BASHRC not set}" >/dev/null 2>&1 || true

if [ "$#" -eq 0 ]; then
    exec bash -i
fi
exec "$@"
