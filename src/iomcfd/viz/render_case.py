"""Render the views of one case (run inside the viz image, one process per case).

    python -m iomcfd.viz.render_case --case runs/<study>/<case> --project foil2d \
        [--views velocity,pressure] [--options '{"q_level": 3}'] [--no-time]

Writes <case>/viz/<view>.png, and for cases with several time directories
(transient runs with snapshots) <case>/viz/<view>_time.mp4 for the project's
TIME_VIEWS. A manifest <case>/viz/viz.json records what was rendered.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

from .. import config
from . import Skip


def load_viz_module(project: str):
    path = config.projects_dir() / project / "viz.py"
    spec = importlib.util.spec_from_file_location(f"iomcfd_viz.{project}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def encode(frames_dir: Path, pattern: str, out: Path, fps: float) -> Path | None:
    if not shutil.which("ffmpeg"):
        return None
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(frames_dir / pattern),
           "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2,format=yuv420p", "-c:v", "libx264", "-r", "25", str(out)]
    subprocess.run(cmd, check=True)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True, type=Path)
    ap.add_argument("--project", required=True)
    ap.add_argument("--out", type=Path, help="default: <case>/viz")
    ap.add_argument("--views", help="comma-separated (default: the project's DEFAULT_VIEWS)")
    ap.add_argument("--options", default="{}", help="JSON options passed to the views")
    ap.add_argument("--no-time", action="store_true", help="skip time-series animations")
    args = ap.parse_args(argv)

    from .pvlib import Ctx

    mod = load_viz_module(args.project)
    out = args.out or (args.case / "viz")
    out.mkdir(parents=True, exist_ok=True)
    views = args.views.split(",") if args.views else list(mod.DEFAULT_VIEWS)
    ctx = Ctx(args.case, out, json.loads(args.options))
    old = out / "viz.json"
    previous = json.loads(old.read_text()).get("views", {}) if old.is_file() else {}
    manifest = {"case": args.case.name, "project": args.project, "times": ctx.times, "views": dict(previous)}
    for name in views:
        fn = mod.VIEWS.get(name)
        if fn is None:
            manifest["views"][name] = {"status": "unknown view"}
            continue
        t0 = time.time()
        try:
            fn(ctx)
            png = ctx.save(out / f"{name}.png", ctx.times[-1] if ctx.times else None)
            entry = {"status": "ok", "image": png.name}
            if (not args.no_time and len(ctx.times) > 1 and name in getattr(mod, "TIME_VIEWS", [])):
                frames = out / "frames" / name
                shutil.rmtree(frames, ignore_errors=True)
                for i, t in enumerate(ctx.times):
                    if ctx._title is not None:
                        ctx._title.Text = ctx._title.Text.split("   t =")[0] + f"   t = {t:.4g} s"
                    ctx.save(frames / f"f_{i:04d}.png", t)
                fps = max(4.0, min(25.0, len(ctx.times) / 8.0))
                mp4 = encode(frames, "f_%04d.png", out / f"{name}_time.mp4", fps)
                if mp4:
                    entry["time_animation"] = mp4.name
                    shutil.rmtree(frames, ignore_errors=True)
            manifest["views"][name] = entry
        except Skip as exc:
            manifest["views"][name] = {"status": "skipped", "reason": str(exc)}
        except Exception as exc:  # noqa: BLE001 - one broken view must not stop the others
            manifest["views"][name] = {"status": "error", "error": f"{type(exc).__name__}: {exc}",
                                       "traceback": traceback.format_exc()}
        finally:
            manifest["views"][name]["seconds"] = round(time.time() - t0, 1)
            ctx.end_view()
    if (out / "frames").is_dir() and not any((out / "frames").iterdir()):
        (out / "frames").rmdir()
    (out / "viz.json").write_text(json.dumps(manifest, indent=2) + "\n")
    bad = [n for n in views if manifest["views"].get(n, {}).get("status") == "error"]
    for n in bad:
        print(f"[{args.case.name}] view {n} failed:\n{manifest['views'][n]['traceback']}", file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
