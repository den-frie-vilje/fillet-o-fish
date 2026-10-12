# Tools

## `build_occt.sh`

Builds Open CASCADE's IR branch, which carries the fillet fixes merged on 2026-08-09 for
release 8.1, with its DRAW harness, and installs it into `$FOF_OCCT` (default
`~/.local/opt/occt-ir`, about 180 MB). It builds the modelling modules and Draw only, with no
visualisation, Tk, FreeType or TBB. Needs `cmake`, `make` and `clang`; about 30 minutes on an
M-series laptop. It ends by running the fix's own case, two 5 mm fillets that touch in a 10 mm
box, which version 8.0.1 refuses, and prints `FOF touching fillets: OK`. The commit built is
recorded in `SOURCE_COMMIT.txt` beside the install.

`fof.kernel` finds the install through `FOF_OCCT` or the default path, and `fof.brep.fillet_edges`
uses it whenever it is there.

## `capped.sh`

```
tools/capped.sh CAP_GB command...
```

Runs the command and polls its memory, with every process it started, once a second; past the
cap it kills them all and exits 137. A grid blend or an envelope check that goes wrong can take a
laptop's whole memory in a minute, so every heavy run goes through it.
