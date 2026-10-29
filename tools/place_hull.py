"""Put a hull STL in the boat frame (x aft, y port, z up, design waterline
z = 0; docs/geometry.md) and print its particulars at z = 0.

Rotations (`--rotate AXIS DEG`, in order) and then a translation
(`--translate DX DY DZ`) in the file's own units (`--scale` to metres for
the printout, default mm). The surface must be closed; it is written as a
binary STL, outward. The alternative hull (docs/hulls.md: its transom on
the waterline at the origin, the bow at +x) to x = 1000 mm at the transom:

    uv run python tools/place_hull.py boats/private/hulls/source/IOM_Alternative_Hull.stl \\
        boats/private/hulls/iom-alternative.stl --rotate z 180 --translate 1000 0 0
"""

import argparse
import hashlib
from pathlib import Path

from iomcfd.geometry import stl
from iomcfd.vpp.hydrostatics import particulars

ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
ap.add_argument("source")
ap.add_argument("out")
ap.add_argument("--rotate", nargs=2, action="append", default=[], metavar=("AXIS", "DEG"))
ap.add_argument("--translate", nargs=3, type=float, default=[0.0, 0.0, 0.0], metavar=("DX", "DY", "DZ"))
ap.add_argument("--scale", type=float, default=0.001, help="file units to metres (default mm)")
args = ap.parse_args()

s = stl.read(args.source, Path(args.out).stem)
for axis, deg in args.rotate:
    s = s.rotated(axis, float(deg))
s = s.translated(args.translate)
if not s.is_closed():
    raise SystemExit(f"{args.source} is not a closed surface")
s = s.oriented_outward()
s.write(args.out, binary=True)

lo, hi = s.bounds
print(f"wrote {args.out} ({len(s.triangles)} triangles), sha256 {hashlib.sha256(Path(args.out).read_bytes()).hexdigest()}")
print(f"source sha256 {hashlib.sha256(Path(args.source).read_bytes()).hexdigest()}")
print("bounds (file units): " + ", ".join(f"{a} {lo[i]:.2f} .. {hi[i]:.2f}" for i, a in enumerate("xyz")))
p = particulars(s.scaled(args.scale))
print(f"at z = 0: volume {p.volume * 1e3:.4f} L, waterline x {p.x_fwd * 1e3:.2f} .. {p.x_aft * 1e3:.2f} mm "
      f"(LWL {p.lwl * 1e3:.1f}), BWL {p.bwl * 1e3:.1f} mm, T_c {p.draft * 1e3:.1f} mm")
print(f"  LCB {p.lcb * 1e3:.1f} mm, LCF {p.lcf * 1e3:.1f} mm, VCB {p.vcb * 1e3:.1f} mm, A_WP {p.waterplane_area:.4f} m², "
      f"S {p.wetted_area:.4f} m², A_X {p.section_area * 1e4:.2f} cm² at {p.x_section * 1e3:.0f} mm")
print(f"  C_B {p.cb:.3f}, C_P {p.cp:.3f}, C_X {p.cx:.3f}, C_WP {p.cwp:.3f}, BM_T {p.bm_t * 1e3:.1f} mm, "
      f"BM_L {p.bm_l * 1e3:.0f} mm, immersion {p.immersion:.1f} g/mm")
