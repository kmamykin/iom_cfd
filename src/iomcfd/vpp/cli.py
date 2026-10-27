"""`iomcfd vpp ...`: race time and exchange rates, single points, comparisons
and the hydrostatics of a boat file (boats/<name>.yaml)."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import time
from pathlib import Path

import yaml

from .. import config


def _boat_path(ref: str) -> Path:
    p = Path(ref)
    if p.exists():
        return p
    q = config.home() / "boats" / (ref if ref.endswith(".yaml") else f"{ref}.yaml")
    if q.exists():
        return q
    raise SystemExit(f"no boat file {ref} (nor {q})")


def _sets(items) -> dict:
    from ..cli import parse_sets

    return parse_sets(items)


def _built(args, extra: dict | None = None):
    from . import cache
    from .boat import BoatSpec, build

    cache.ENABLED[0] = not getattr(args, "no_cache", False)

    spec = BoatSpec.load(_boat_path(args.boat), {**_sets(args.set), **(extra or {})})
    t = time.time()
    b = build(spec)
    print(f"built {spec.name} in {time.time() - t:.1f} s: {b.info}")
    for w in b.warnings:
        print(f"warning: {w}")
    return b


def _out_dir(args, name: str) -> Path:
    if getattr(args, "out", None):
        return Path(args.out)
    runs = Path(args.runs) if getattr(args, "runs", None) else config.runs_dir()
    return runs / "vpp" / name / dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def _run_info(args, b, timings: dict) -> dict:
    """run.json: what was run, with the values the build resolved (course,
    wind, settings, each part's classes and controls) and, for each --set
    path, the boat file's own value."""
    from dataclasses import asdict

    from .boat import BoatSpec
    from .tables import _plain

    def cls(o) -> str | None:
        return None if o is None else f"{type(o).__module__}.{type(o).__qualname__}"

    sets = _sets(args.set)
    original = BoatSpec.load(b.spec.path) if b.spec.path else None
    controls = b.boat.controls()
    parts = [{"name": c.name, "kind": c.kind, "attitude": c.attitude, "shape": cls(getattr(c, "shape", None)),
              "forces": cls(getattr(c, "forces", c)), "owner": getattr(c, "owner", True),
              "controls": [asdict(k) for k in controls if k.key.startswith(f"{c.name}.")]} for c in b.boat.components]
    return _plain({
        "boat": b.spec.name, "file": str(b.spec.path), "overrides": sets,
        "file_values": {k: original.get(k) if original else None for k in sets},
        "created": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git": config.git_describe(), "info": b.info, "warnings": b.warnings,
        "course": asdict(b.course),
        "wind": {"tws": b.wind.tws, "weights": b.wind.weights, "z_ref": b.wind.z_ref, "alpha": b.wind.alpha},
        "settings": asdict(b.boat.settings), "parts": parts, "timings": timings})


def cmd_run(args) -> None:
    from . import report
    from .race import boat_lengths, race, weighted
    from .rates import rates, standard
    from .response import responses
    from .solver import polar

    timings: dict[str, float] = {}
    t = time.time()
    b = _built(args)
    timings["build_s"] = round(time.time() - t, 2)
    out = _out_dir(args, b.spec.name)
    out.mkdir(parents=True, exist_ok=True)

    def info() -> None:
        (out / "run.json").write_text(json.dumps(_run_info(args, b, timings), indent=2, default=str) + "\n")

    (out / "boat.yaml").write_text(yaml.safe_dump(b.spec.data, sort_keys=False))
    info()
    report.write_csv(out / "mass.csv", b.mass.to_rows())
    report.write_csv(out / "hydro.csv", b.table.rows())
    t = time.time()
    rows = race(b.boat, b.wind, b.course)
    timings["race_s"] = round(time.time() - t, 2)
    print(f"race: {timings['race_s']:.1f} s, weighted race time {weighted(rows):.1f} s")
    report.write_csv(out / "race.csv", [r.row() for r in rows])
    report.write_csv(out / "vmg.csv", [r.up.row() | {"leg": "up"} for r in rows] +
                     [r.down.row() | {"leg": "down"} for r in rows])
    warnings = list(b.warnings)
    for r in rows:
        for leg, p in (("up", r.up), ("down", r.down)):
            if not p.converged or p.flags:
                warnings.append(f"TWS {r.tws:g} {leg}: {' '.join(p.flags) or 'not converged'}")
    t = time.time()
    report.write_csv(out / "response.csv", responses(b.boat, rows, b.wind))
    timings["response_s"] = round(time.time() - t, 2)
    print(f"response: {timings['response_s']:.1f} s")
    rr, rs = None, None
    if not args.no_rates:
        from .boat import build as rebuild_fn

        def rebuild(over):
            return rebuild_fn(b.spec.with_overrides(over)).boat

        t = time.time()
        rr, rs = rates(b.boat, b.course, b.wind, rows, standard(b.boat, rebuild), check=args.check)
        timings["rates_s"] = round(time.time() - t, 2)
        print(f"rates: {timings['rates_s']:.1f} s")
        report.write_csv(out / "rates.csv", [x.row() for x in rr])
        t0 = weighted(rows)
        report.write_csv(out / "rates_summary.csv", [
            {"name": n, "dt_pct": pct, "boat_lengths": boat_lengths(pct / 100 * t0, t0, b.course)}
            for n, pct in rs.items()])
    pts = []
    if not args.no_polar:
        t = time.time()
        twa = [float(a) for a in (b.spec.get("polar.twa") or [35, 45, 60, 90, 120, 150, 180])]
        pts = polar(b.boat, b.wind.tws, twa, b.wind.z_ref, b.wind.alpha)
        timings["polar_s"] = round(time.time() - t, 2)
        print(f"polar: {timings['polar_s']:.1f} s")
        report.write_csv(out / "polar.csv", [p.row() for p in pts])
        try:
            report.polar_figure(pts, rows, out / "polar.png", b.spec.name)
        except ImportError:
            pass
    report.summary_md(out / "summary.md", b.spec.name, b.info, rows, b.course, rr, rs, warnings)
    info()
    print(f"wrote {out}")
    print((out / "summary.md").read_text())
    print(f"report: {report.html_report(out)}")


def cmd_report(args) -> None:
    """report.html of a run folder again (e.g. after a template change)."""
    from . import report
    from ..runner import list_runs

    p = Path(args.run)
    if not (p / "run.json").is_file():
        runs = Path(args.runs) if getattr(args, "runs", None) else config.runs_dir()
        sdir = runs / "vpp" / args.run
        ids = list_runs(sdir)
        run_id = ids[-1] if ids and args.run_id in (None, "latest") else args.run_id
        if run_id not in ids:
            raise SystemExit(f"no run {args.run_id or ''} of {args.run} in {sdir} (runs: {', '.join(ids) or 'none'})")
        p = sdir / run_id
    print(f"wrote {report.html_report(p)}")


def cmd_point(args) -> None:
    from .components.base import Wind
    from .solver import solve_point

    b = _built(args)
    t = time.time()
    p = solve_point(b.boat, Wind(args.tws, args.twa, b.wind.z_ref, b.wind.alpha), hold=_sets(args.hold))
    print(f"solved in {time.time() - t:.2f} s")
    for k, v in p.row().items():
        if not k.startswith(("X_", "Y_", "Z_", "K_", "M_", "N_")):
            print(f"  {k}: {v:.4g}" if isinstance(v, float) else f"  {k}: {v}")
    print("  component       X [N]     Y [N]     Z [N]    K [N·m]   M [N·m]   N [N·m]")
    for name, ld in p.parts.items():
        print(f"  {name:12s} {ld.X:9.4f} {ld.Y:9.4f} {ld.Z:9.4f} {ld.K:9.4f} {ld.M:9.4f} {ld.N:9.4f}")


def cmd_compare(args) -> None:
    from .boat import BoatSpec, build
    from .race import boat_lengths, race, weighted

    base = _built(args)
    other_path = _boat_path(args.other) if args.other else _boat_path(args.boat)
    spec_b = BoatSpec.load(other_path, {**_sets(args.set), **_sets(args.set_b)})
    b = build(spec_b)
    ra, rb = race(base.boat, base.wind, base.course), race(b.boat, b.wind, b.course)
    ta, tb = weighted(ra), weighted(rb)
    print(f"A {base.spec.name} {_sets(args.set)}\nB {spec_b.name} {_sets(args.set_b)}")
    print("TWS m/s  VMG up A    B      VMG down A   B     race A s   B s    ΔB−A %")
    for x, y in zip(ra, rb):
        print(f"{x.tws:6.2f} {x.up.vmg:9.4f} {y.up.vmg:7.4f} {-x.down.vmg:10.4f} {-y.down.vmg:7.4f} "
              f"{x.t:9.1f} {y.t:7.1f} {100 * (y.t - x.t) / x.t:8.3f}")
    d = 100 * (tb - ta) / ta
    print(f"weighted: A {ta:.1f} s, B {tb:.1f} s, B−A {d:+.3f} % ({boat_lengths(tb - ta, ta, base.course):+.2f} "
          "boat lengths)")


def cmd_sweep(args) -> None:
    """Each combination of --vary values against the boat file as it is:
    race time per wind (re-timed at the baseline's best-VMG angles and flat
    unless --full) and the weighted change."""
    import itertools

    from . import report
    from .boat import build
    from .race import boat_lengths, race, weighted
    from .rates import _retime

    base = _built(args)
    rows0 = race(base.boat, base.wind, base.course)
    t0 = weighted(rows0)
    if args.variant:
        variants = [_sets(v.split(";")) for v in args.variant]
    else:
        keys, values = [], []
        for v in args.vary or []:
            k, vals = v.split("=", 1)
            keys.append(k)
            values.append([_sets([f"x={x}"])["x"] for x in vals.split(",")])
        variants = [dict(zip(keys, combo)) for combo in itertools.product(*values)]
    out_rows = []
    for over in variants:
        try:
            b = build(base.spec.with_overrides(over))
        except (ValueError, FileNotFoundError) as e:
            print(f"{over}: {e}")
            continue
        rows = _retime(b.boat, base.course, base.wind, rows0, check=args.full)
        t = weighted(rows)
        r = {**over, "dt_pct": 100 * (t - t0) / t0, "boat_lengths": boat_lengths(t - t0, t0, base.course),
             **{k: v for k, v in b.info.items() if isinstance(v, (int, float))}}
        for x0, x1 in zip(rows0, rows):
            r[f"dt_pct_{x0.tws:g}"] = 100 * (x1.t - x0.t) / x0.t
        r["flags"] = " ".join(sorted({f for x in rows for p in (x.up, x.down) for f in p.flags}))
        out_rows.append(r)
        print(f"{over}: {r['dt_pct']:+.3f} % ({r['boat_lengths']:+.2f} boat lengths) {r['flags']}")
    out = _out_dir(args, f"{base.spec.name}-sweep")
    report.write_csv(out / "sweep.csv", out_rows)
    print(f"wrote {out / 'sweep.csv'}")


def cmd_export_table(args) -> None:
    from . import keel3d

    out = keel3d.export(args.run, _sets(args.select), args.out)
    print(f"wrote {out}")


def cmd_table(args) -> None:
    from . import keel3d

    t = time.time()
    out = keel3d.build_table(args.recipe)
    print(f"wrote {out} in {time.time() - t:.1f} s")


def cmd_hydro(args) -> None:
    from .mass import check_rules

    b = _built(args)
    print(f"mass {b.mass.mass:.4f} kg, CG {[round(float(c), 4) for c in b.mass.cg]}")
    for r in b.mass.to_rows():
        print(f"  {r}")
    print(" heel    RM N·m   GZ mm   sink mm   trim deg   wetted m²")
    tab = b.table
    for h in range(0, 61, 5):
        d = tab.at(float(h), 0.0)
        gz = d["rm"] / (b.mass.mass * 9.80665) * 1000
        print(f"{h:5d} {d['rm']:9.4f} {gz:8.1f} {d['sink'] * 1000:8.2f} {d['trim']:9.3f} {d['wetted_area']:10.4f}")


def add_parser(sub) -> None:
    p = sub.add_parser("vpp", help="velocity prediction: race time, exchange rates, polars (boats/<name>.yaml)")
    vs = p.add_subparsers(dest="vpp_cmd", required=True)

    def boat_cmd(name, func, help_):
        q = vs.add_parser(name, help=help_)
        q.add_argument("boat", help="boats/<name>.yaml or a path")
        q.add_argument("--set", action="append", metavar="KEY=VALUE", help="override an entry by its dotted path")
        q.add_argument("--no-cache", action="store_true", help="compute the boat's tables afresh (config.cache_dir)")
        q.set_defaults(func=func)
        return q

    q = boat_cmd("run", cmd_run, "race time per wind, exchange rates, a polar and report.html; writes runs/vpp/<boat>/<id>/")
    q.add_argument("--no-rates", action="store_true")
    q.add_argument("--no-polar", action="store_true")
    q.add_argument("--check", action="store_true", help="rates by a full re-search, not the envelope shortcut")
    q.add_argument("--out", help="output directory (default runs/vpp/<boat>/<UTC time>)")
    q = vs.add_parser("report", help="write a run's report.html again (nothing is solved)")
    q.add_argument("run", help="a run directory, or a boat name (its runs in runs/vpp/<boat>/)")
    q.add_argument("--run-id", help="YYYYMMDD-HHMMSS (default: the latest)")
    q.set_defaults(func=cmd_report)
    q = boat_cmd("point", cmd_point, "one equilibrium with each component's forces")
    q.add_argument("--tws", type=float, required=True, help="m/s at the reference height")
    q.add_argument("--twa", type=float, required=True, help="deg from the course")
    q.add_argument("--hold", action="append", metavar="KEY=VALUE",
                   help="hold a control, e.g. sails.flat=0.8 or sails.set=1 (default: search)")
    q = boat_cmd("compare", cmd_compare, "race time of two boats (or one with --set-b changes)")
    q.add_argument("other", nargs="?", help="second boat file (default: the same with --set-b)")
    q.add_argument("--set-b", action="append", metavar="KEY=VALUE", help="override for boat B only")
    boat_cmd("hydro", cmd_hydro, "mass budget and righting moment against heel")
    q = boat_cmd("sweep", cmd_sweep, "race time of variants (e.g. CFD designs) against the boat file")
    q.add_argument("--vary", action="append", metavar="KEY=V1,V2,..",
                   help="dotted path and values, e.g. components.keel.forces.args.table=a.csv,b.csv "
                        "(repeat for a grid)")
    q.add_argument("--variant", action="append", metavar="K1=V1;K2=V2",
                   help="one variant: overrides separated by ';' (repeat; instead of --vary)")
    q.add_argument("--full", action="store_true", help="re-search angle and flat (default: the baseline's)")
    q.add_argument("--out", help="output directory")
    q = vs.add_parser("export-table", help="a CFD run's results for one design as a VPP table (for a boat file)")
    q.add_argument("tool", choices=["keel3d"])
    q.add_argument("run", help="<study>@<run id> (in $IOMCFD_SOURCE_RUNS, then runs/) or a results.csv")
    q.add_argument("--select", action="append", metavar="KEY=VALUE", help="the design's parameters (repeat)")
    q.add_argument("--out", required=True, help="the table, e.g. boats/tables/<name>.csv")
    q.set_defaults(func=cmd_export_table)
    q = vs.add_parser("table", help="build a table from a recipe file (boats/tables/<name>.yaml)")
    q.add_argument("action", choices=["build"])
    q.add_argument("recipe", help="the recipe, e.g. boats/tables/keel-ht35.yaml")
    q.set_defaults(func=cmd_table)
