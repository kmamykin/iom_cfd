#!/usr/bin/env bash
# Build XFOIL 6.99 (M. Drela, GPL) from the MIT source and install the binary.
#
#   tools/build-xfoil.sh [PREFIX]      # default PREFIX: ~/.local  -> ~/.local/bin/xfoil
#
# Needs gfortran and libX11 (macOS: `brew install gcc libx11`; Debian/Ubuntu:
# `apt install gfortran libx11-dev`). XFOIL is only run in batch mode with
# plotting switched off, but it still links the X11 plot library.
# iomcfd.xfoil finds the binary through $IOMCFD_XFOIL, then PATH, then
# ~/.local/bin/xfoil.
set -euo pipefail

PREFIX=${1:-$HOME/.local}
URL=https://web.mit.edu/drela/Public/web/xfoil/xfoil6.99.tgz
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

if [[ -d /opt/homebrew/include/X11 ]]; then X11=/opt/homebrew
elif [[ -d /usr/local/include/X11 ]]; then X11=/usr/local
elif [[ -d /opt/X11/include/X11 ]]; then X11=/opt/X11
else X11=/usr; fi

curl -sSfL -o "$WORK/xfoil.tgz" "$URL"
tar -xzf "$WORK/xfoil.tgz" -C "$WORK"
cd "$WORK/Xfoil"

# gfortran >= 10 rejects some of XFOIL's legacy argument passing without these.
LEGACY="-std=legacy -fallow-argument-mismatch -w"

cat > plotlib/config.make <<EOF
PLTLIB = libPlt_gDP.a
DEFINE = -DUNDERSCORE
FC = gfortran
CC = gcc
DP = -fdefault-real-8
FFLAGS = -O2 \$(DP) $LEGACY
CFLAGS = -O2 \$(DEFINE) -I$X11/include
AR = ar r
RANLIB = ranlib
LINKLIB = -L$X11/lib -lX11
EOF
make -C plotlib libPlt_gDP.a >/dev/null

# The Orr-Sommerfeld database (orrs/) is not built: the default envelope e^n
# transition model doesn't read it.
sed -e "s|^BINDIR = .*|BINDIR = $PREFIX/bin/|" \
    -e "s|^PLTLIB = .*|PLTLIB = -L$X11/lib -lX11|" \
    -e "s|^FFLAGS = .*|FFLAGS = -O2 \$(DBL) $LEGACY|" \
    -e "s|^FFLOPT = .*|FFLOPT = -O2 \$(DBL) $LEGACY|" \
    -e "s|^INSTALLCMD = .*|INSTALLCMD = install|" \
    bin/Makefile_gfortran > bin/Makefile
mkdir -p "$PREFIX/bin"
make -C bin xfoil >/dev/null
echo "installed $PREFIX/bin/xfoil"
