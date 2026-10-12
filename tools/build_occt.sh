#!/usr/bin/env bash
# Build Open CASCADE's IR branch (the fillet fixes of 2026-08-09, due in release 8.1) with its DRAW
# harness, and install it where fof/kernel.py looks: $FOF_OCCT, default ~/.local/opt/occt-ir.
# Needs cmake, make and clang (Xcode command line tools). About 30 minutes on an M-series laptop.
set -euo pipefail
PREFIX="${FOF_OCCT:-$HOME/.local/opt/occt-ir}"
WORK="${WORK:-${TMPDIR:-/tmp}/fof-occt}"
mkdir -p "$WORK"; cd "$WORK"
[ -d src ] || git clone -q --depth 1 --branch IR https://github.com/Open-Cascade-SAS/OCCT.git src
mkdir -p build && cd build
cmake -G "Unix Makefiles" -S ../src -B . -DCMAKE_C_COMPILER=/usr/bin/clang -DCMAKE_CXX_COMPILER=/usr/bin/clang++ \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PREFIX" -DINSTALL_DIR_LAYOUT=Unix \
  -DBUILD_MODULE_Visualization=OFF -DBUILD_MODULE_ApplicationFramework=OFF -DBUILD_MODULE_Draw=ON \
  -DBUILD_MODULE_DataExchange=ON -DUSE_TK=OFF -DUSE_FREETYPE=OFF -DUSE_TBB=OFF -DBUILD_DOC_Overview=OFF
make -j"$(sysctl -n hw.ncpu)"
make install
(cd ../src && git log -1 --format='%H %cd %s' --date=short) > "$PREFIX/SOURCE_COMMIT.txt"
# the fix's own case: two 5 mm fillets that touch in a 10 mm box, which 8.0.1 refuses
cat > "$WORK/touch.tcl" <<'EOF'
pload MODELING
box Box 10 10 10
explode Box E
catch { blend Fillet Box 5 Box_1 5 Box_3 } msg
if { [info exist Fillet] == 0 } { puts "FOF touching fillets: FAILED" } else { puts "FOF touching fillets: OK" }
exit
EOF
CASROOT="$PREFIX" DYLD_LIBRARY_PATH="$PREFIX/lib" "$PREFIX/bin/DRAWEXE" -v -f "$WORK/touch.tcl" | grep FOF
