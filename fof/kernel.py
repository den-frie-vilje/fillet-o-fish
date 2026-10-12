"""Fillets through the fixed Open CASCADE kernel, run as a DRAW script.

The Python bindings (OCP 8.0.1) carry a kernel whose fillet fails on some runs and cannot round
fillets that touch. The fix (OCCT pull requests 1293 and 1449, merged 2026-08-09) is in OCCT's
IR branch, due in release 8.1. fof builds that branch from source (tools/build_occt.sh) and
drives it through its DRAW harness: the body goes out as a BREP file, the fillet runs there, the
result comes back as BREP. The format is shared between the two kernel versions, so the rest of
a build stays in OCP.

Set FOF_OCCT to the install prefix (default ~/.local/opt/occt-ir).
"""
import os, subprocess, tempfile, numpy as np
from OCP.BRepTools import BRepTools
from OCP.TopoDS import TopoDS_Shape
from OCP.BRep import BRep_Builder
from OCP.BRepCheck import BRepCheck_Analyzer

PREFIX = os.environ.get('FOF_OCCT', os.path.expanduser('~/.local/opt/occt-ir'))

def available():
    return os.path.exists(os.path.join(PREFIX, 'bin', 'DRAWEXE'))

def version():
    try: return open(os.path.join(PREFIX, 'SOURCE_COMMIT.txt')).read().strip()
    except OSError: return 'unknown'

_SCRIPT = r'''
pload MODELING
restore {brep} S
explode S E
set n [llength [explode S E]]
set fh [open {mids} r]; set mids [split [string trim [read $fh]] "\n"]; close $fh
set picked {{}}
foreach m $mids {{
  lassign $m mx my mz
  set best ""; set bestd 1e9
  for {{set i 1}} {{$i <= $n}} {{incr i}} {{
    lassign [bounding S_$i] x0 y0 z0 x1 y1 z1
    if {{$mx >= $x0 - 0.01 && $mx <= $x1 + 0.01 && $my >= $y0 - 0.01 && $my <= $y1 + 0.01 && $mz >= $z0 - 0.01 && $mz <= $z1 + 0.01}} {{
      set d [expr {{($x1 - $x0 + 1e-6) * ($y1 - $y0 + 1e-6) * ($z1 - $z0 + 1e-6)}}]
      if {{$d < $bestd}} {{ set bestd $d; set best S_$i }}
    }}
  }}
  if {{$best ne "" && [lsearch $picked $best] < 0}} {{ lappend picked $best }}
}}
puts "FOF edges [llength $mids] -> [llength $picked]"
set args {{}}
foreach e $picked {{ lappend args {rho} $e }}
set r [catch {{ eval blend F S $args }} msg]
if {{ [info exist F] == 0 }} {{ puts "FOF failed $msg" }} else {{
  puts "FOF check [checkshape F]"
  save F {out}
  puts "FOF done"
}}
exit
'''

def fillet(shape, edge_points, rho, keep_dir=None):
    """shape with every edge that contains one of edge_points (one point per edge, e.g. its
    midpoint) rounded by a ball of rho. Raises on failure or an invalid result."""
    assert available(), 'the fixed kernel is not installed at %s (tools/build_occt.sh)' % PREFIX
    d = keep_dir or tempfile.mkdtemp(prefix='fof-fillet-')
    brep, mids, out, tcl = [os.path.join(d, f) for f in ('in.brep', 'mids.txt', 'out.brep', 'fillet.tcl')]
    BRepTools.Write_s(shape, brep)
    np.savetxt(mids, np.asarray(edge_points, float).reshape(-1, 3), fmt='%.6f')
    open(tcl, 'w').write(_SCRIPT.format(brep=brep, mids=mids, out=out, rho='%.6f' % rho))
    env = dict(os.environ, CASROOT=PREFIX, DYLD_LIBRARY_PATH=os.path.join(PREFIX, 'lib'))
    r = subprocess.run([os.path.join(PREFIX, 'bin', 'DRAWEXE'), '-v', '-f', tcl], env=env, capture_output=True, text=True, timeout=600)
    log = [l for l in r.stdout.splitlines() if l.startswith('FOF ')]
    if not any(l == 'FOF done' for l in log):
        raise RuntimeError('kernel fillet failed: %s' % (' | '.join(log) or r.stderr[-400:]))
    n_in, n_edges = [int(x) for x in log[0].split()[2::2]]
    if n_edges < n_in:
        raise RuntimeError('kernel fillet: only %d of %d edges matched' % (n_edges, n_in))
    result = TopoDS_Shape(); BRepTools.Read_s(result, out, BRep_Builder())
    assert BRepCheck_Analyzer(result).IsValid(), 'kernel fillet: result is not a valid solid'
    if not keep_dir:
        for f in (brep, mids, out, tcl): os.remove(f)
        os.rmdir(d)
    return result
