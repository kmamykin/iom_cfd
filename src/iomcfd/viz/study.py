"""Study-level visualisation: render every finished case, build study
animations (one frame per case along a swept parameter) and an HTML gallery.

Reads only finished results (params.json, result.json, the final field
directory); never modifies them. Re-run as often as you like.

Outputs
    runs/<study>/<case>/viz/<view>.png        per-case views
    runs/<study>/<case>/viz/<view>_time.mp4   time series (transient runs with snapshots)
    runs/<study>/viz/<view>_by_<param>[_<group>].mp4/.gif   study animations
    runs/<study>/viz/index.html               gallery of everything above + the report
"""

from __future__ import annotations

import html
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .. import config


@dataclass
class VizOptions:
    views: list[str] | None = None  # None: project DEFAULT_VIEWS (or study viz.views)
    animate: str | None = None  # swept parameter for study animations (None: auto)
    jobs: int = 2
    no_time: bool = False
    options: dict[str, Any] = field(default_factory=dict)


def load_viz_meta(project: str):
    """Import projects/<project>/viz.py (it must not import ParaView at module level)."""
    path = config.projects_dir() / project / "viz.py"
    if not path.is_file():
        raise SystemExit(f"project '{project}' has no viz.py")
    spec = importlib.util.spec_from_file_location(f"iomcfd_viz_meta.{project}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def has_fields(case_dir: Path) -> bool:
    for d in case_dir.iterdir():
        try:
            if float(d.name) > 0 and (d / "U").exists():
                return True
        except ValueError:
            continue
    return False


def animation_axis(cases, preferred: list[str], forced: str | None) -> tuple[str | None, list[str]]:
    """Pick the swept parameter to animate along, and the others to group by."""
    varied = list(cases[0].varied) if cases else []
    if forced:
        if forced not in varied:
            raise SystemExit(f"--animate {forced}: not a varied parameter of this study ({varied})")
        axis = forced
    elif varied:
        # the parameter with the most distinct values; ties: project preference order
        n = {v: len({str(c.varied[v]) for c in cases}) for v in varied}
        rank = {v: (preferred.index(v) if v in preferred else len(preferred)) for v in varied}
        axis = min(varied, key=lambda v: (-n[v], rank[v]))
    else:
        axis = None
    return axis, [v for v in varied if v != axis]


def animation_groups(cases, axis: str, others: list[str]) -> dict[str, list]:
    groups: dict[str, list] = {}
    for c in cases:
        key = "_".join(f"{k}{c.varied[k]}" for k in others)
        groups.setdefault(key, []).append(c)
    for g in groups.values():
        # numbers in numeric order; words (mesh levels, foil names) in study order
        g.sort(key=lambda c: (0, float(c.varied[axis]), 0) if _is_number(c.varied[axis]) else (1, 0.0, c.index))
    return {k: v for k, v in groups.items() if len(v) > 1}


def _is_number(v) -> bool:
    try:
        float(v)
        return not isinstance(v, bool)
    except (TypeError, ValueError):
        return False


def _encode_sequence(images: list[Path], out_mp4: Path, fps: float = 1.0) -> list[Path]:
    if not shutil.which("ffmpeg") or not images:
        return []
    tmp = out_mp4.with_suffix(".frames")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    for i, img in enumerate(images):
        shutil.copy(img, tmp / f"f_{i:04d}.png")
    pad = "pad=ceil(iw/2)*2:ceil(ih/2)*2"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(tmp / "f_%04d.png"),
                    "-vf", f"{pad},format=yuv420p", "-c:v", "libx264", "-r", "25", str(out_mp4)], check=True)
    gif = out_mp4.with_suffix(".gif")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(tmp / "f_%04d.png"),
                    "-vf", "scale=960:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse", str(gif)],
                   check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    return [out_mp4, gif]


def visualize_study(project_name: str, study, cases, sdir: Path, opts: VizOptions, log=print,
                    all_cases=None) -> Path:
    """Render `cases`; animations and the gallery cover every rendered case of
    the study (`all_cases`, default: `cases`), so partial re-renders
    (--only, --views) update things in place."""
    meta = load_viz_meta(project_name)
    sviz = dict(study.raw.get("viz") or {})
    views = opts.views or sviz.get("views") or list(meta.DEFAULT_VIEWS)
    unknown = set(views) - set(meta.VIEWS)
    if unknown:
        raise SystemExit(f"unknown view(s) {sorted(unknown)}; {project_name} has: {sorted(meta.VIEWS)}")
    options = {**(sviz.get("options") or {}), **opts.options}

    ready, missing = [], []
    for c in cases:
        d = sdir / c.name
        if (d / "params.json").is_file() and has_fields(d):
            ready.append(c)
        elif (d / "params.json").is_file():
            missing.append(c.name)
    if missing:
        log(f"  no field data (not run yet, or fetched without --fields): {', '.join(missing)}")
    log(f"viz {study.name}: {len(ready)} cases, views: {', '.join(views)}")

    def render(c):
        cmd = [sys.executable, "-m", "iomcfd.viz.render_case", "--case", str(sdir / c.name), "--project",
               project_name, "--views", ",".join(views), "--options", json.dumps(options)]
        if opts.no_time:
            cmd.append("--no-time")
        r = subprocess.run(cmd, capture_output=True, text=True, env=dict(os.environ))
        return c, r

    with ThreadPoolExecutor(max_workers=max(1, opts.jobs)) as pool:
        for c, r in pool.map(render, ready):
            manifest = sdir / c.name / "viz" / "viz.json"
            stat = json.loads(manifest.read_text())["views"] if manifest.is_file() else {}
            summary = " ".join(f"{k}:{v['status']}" for k, v in stat.items())
            log(f"  {c.name}: {summary or 'failed'}")
            if r.returncode != 0:
                log("    " + (r.stderr or r.stdout).strip().replace("\n", "\n    ")[-3000:])

    out = sdir / "viz"
    out.mkdir(exist_ok=True)
    rendered = [c for c in (all_cases or cases) if (sdir / c.name / "viz" / "viz.json").is_file()]
    # every view that exists on disk for some case, in the project's order
    on_disk = set()
    for c in rendered:
        vs = json.loads((sdir / c.name / "viz" / "viz.json").read_text()).get("views", {})
        on_disk |= {k for k, v in vs.items() if v.get("status") == "ok"}
    all_views = [v for v in meta.VIEWS if v in on_disk] + sorted(on_disk - set(meta.VIEWS))
    # study animations are rebuilt from the images every time (cheap, always consistent)
    for f in list(out.glob("*_by_*.mp4")) + list(out.glob("*_by_*.gif")):
        f.unlink()
    animations = []
    axis, others = animation_axis(rendered, sviz.get("animate_params") or list(getattr(meta, "ANIMATE_PARAMS", [])),
                                  opts.animate or sviz.get("animate"))
    if axis:
        anim_views = [v for v in all_views if v in getattr(meta, "ANIMATE_VIEWS", all_views)]
        for key, group in animation_groups(rendered, axis, others).items():
            for v in anim_views:
                imgs = [sdir / c.name / "viz" / f"{v}.png" for c in group]
                imgs = [i for i in imgs if i.is_file()]
                if len(imgs) < 2:
                    continue
                name = f"{v}_by_{axis}" + (f"_{re.sub(r'[^A-Za-z0-9.+-]', '', key)}" if key else "")
                fps = 1.0 if len(imgs) <= 10 else 2.0
                files = _encode_sequence(imgs, out / f"{name}.mp4", fps)
                if files:
                    animations.append({"view": v, "axis": axis, "group": key,
                                       "values": [c.varied[axis] for c in group], "files": [f.name for f in files]})
        if animations:
            log(f"  study animations along '{axis}': {len(animations)}")
    (out / "viz.json").write_text(json.dumps({"views": all_views, "axis": axis, "animations": animations,
                                              "cases": [c.name for c in rendered]}, indent=2) + "\n")
    index = write_gallery(study, sdir, rendered, all_views, animations)
    log(f"gallery: {index}")
    return index


def write_gallery(study, sdir: Path, cases, views: list[str], animations: list[dict]) -> Path:
    """Static HTML page linking every image and animation (open it locally)."""
    e = html.escape
    parts = [
        "<!doctype html><html><head><meta charset='utf-8'><title>" + e(study.name) + "</title>",
        "<style>body{font:14px system-ui,sans-serif;margin:16px;max-width:1700px}"
        "img,video{max-width:100%;border:1px solid #ddd}.grid{display:grid;"
        "grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:12px}"
        "h2{margin-top:32px;border-bottom:1px solid #ccc}figure{margin:0}figcaption{color:#555}"
        "table{border-collapse:collapse}td{padding:2px 8px;border-bottom:1px solid #eee}</style></head><body>",
        f"<h1>{e(study.name)}</h1><p>{e((study.description or '').strip())}</p>",
    ]
    report = sdir / "report"
    if report.is_dir():
        imgs = sorted(report.glob("*.png"))
        if imgs:
            parts.append("<h2>Report</h2><div class='grid'>")
            parts += [f"<figure><a href='../report/{i.name}'><img src='../report/{i.name}'></a>"
                      f"<figcaption>{e(i.name)}</figcaption></figure>" for i in imgs]
            parts.append("</div>")
    if animations:
        parts.append("<h2>Study animations</h2><div class='grid'>")
        for a in animations:
            mp4 = next(f for f in a["files"] if f.endswith(".mp4"))
            cap = f"{a['view']} along {a['axis']} = {', '.join(map(str, a['values']))}" + (f" ({a['group']})" if a["group"] else "")
            parts.append(f"<figure><video src='{e(mp4)}' controls loop muted playsinline></video>"
                         f"<figcaption>{e(cap)}</figcaption></figure>")
        parts.append("</div>")
    parts.append("<h2>Cases</h2>")
    for c in cases:
        cdir = sdir / c.name
        res = json.loads((cdir / "result.json").read_text()) if (cdir / "result.json").is_file() else {}
        metrics = {k: v for k, v in (res.get("metrics") or {}).items() if isinstance(v, (int, float))}
        keys = list(metrics)[:8]
        parts.append(f"<h3>{e(c.name)} <small>({e(res.get('status', '?'))})</small></h3>")
        if keys:
            parts.append("<table><tr>" + "".join(f"<td>{e(k)}</td>" for k in keys) + "</tr><tr>"
                         + "".join(f"<td>{metrics[k]:.4g}</td>" for k in keys) + "</tr></table>")
        parts.append("<div class='grid'>")
        for v in views:
            png = cdir / "viz" / f"{v}.png"
            if png.is_file():
                rel = f"../{c.name}/viz/{v}.png"
                parts.append(f"<figure><a href='{rel}'><img src='{rel}' loading='lazy'></a><figcaption>{e(v)}</figcaption></figure>")
            mp4 = cdir / "viz" / f"{v}_time.mp4"
            if mp4.is_file():
                parts.append(f"<figure><video src='../{c.name}/viz/{v}_time.mp4' controls loop muted></video>"
                             f"<figcaption>{e(v)} over time</figcaption></figure>")
        parts.append("</div>")
    parts.append("</body></html>")
    index = sdir / "viz" / "index.html"
    index.write_text("\n".join(parts))
    return index
