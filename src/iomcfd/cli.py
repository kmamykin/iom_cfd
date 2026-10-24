"""iomcfd command line.

    iomcfd projects                         list projects
    iomcfd plan    STUDY                    show the cases a study expands to
    iomcfd render  STUDY                    write OpenFOAM case dirs, don't run
    iomcfd run     STUDY [-j N] [--np P]    render + mesh + solve + extract (a new run)
    iomcfd runs    STUDY                    list the runs of a study
    iomcfd collect STUDY                    gather results -> runs/<study>/<run>/results.csv
    iomcfd report  STUDY                    plots, tables, summary.md (host, needs [analysis])
    iomcfd viz     STUDY                    ParaView images, montages, gallery (viz image)
    iomcfd slim    STUDY                    delete a local run's meshes, logs and fields, keep results
    iomcfd shell                            OpenFOAM shell in the container (host)
    iomcfd site export|build                the website: data from runs, figures, Quarto build
    iomcfd gcp ...                          Google Cloud Batch (see `iomcfd gcp -h`)

STUDY is a path to a study YAML or the short form <project>/<study>
(= projects/<project>/studies/<study>.yaml).

Each `run` writes a new timestamped run, runs/<study>/<YYYYMMDD-HHMMSS>/, so
earlier results are never overwritten; `--resume` continues the latest run
instead. collect, report and viz work on the latest run, or `--run-id ID`,
using the study file as it was when that run started.

`run` executes OpenFOAM. Outside the container it re-launches itself inside
the iom-cfd Docker image with the repository mounted at /work.
"""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from . import config


def resolve_study_path(spec: str) -> Path:
    p = Path(spec)
    if p.is_file():
        return p.resolve()
    if "/" in spec and not spec.endswith((".yaml", ".yml")):
        proj, name = spec.split("/", 1)
        cand = config.projects_dir() / proj / "studies" / f"{name}.yaml"
        if cand.is_file():
            return cand
    raise SystemExit(f"study not found: {spec}")


def parse_sets(items: list[str] | None) -> dict[str, Any]:
    out = {}
    for it in items or []:
        if "=" not in it:
            raise SystemExit(f"--set expects key=value, got '{it}'")
        k, v = it.split("=", 1)
        out[k.strip()] = yaml.safe_load(v)
    return out


def _load(args):
    from .project import load_project
    from .study import Study

    study = Study.load(resolve_study_path(args.study), parse_sets(getattr(args, "set", None)))
    project = load_project(study.project)
    cases = study.expand(project.defaults)
    return study, project, cases


def _load_run(args):
    """Study, project, cases and directory of an existing run. The study comes
    from the run's own copy of the study file, so later edits to the study
    (new parameters, report options) don't change what an old run means.
    Exception: `highlights:` (what to look at) come from the current study
    file if it has any; see iomcfd.highlights."""
    from .highlights import resolve
    from .project import load_project
    from .runner import resolve_run
    from .study import Study

    current = Study.load(resolve_study_path(args.study))
    rdir = resolve_run(current, _runs(args), getattr(args, "run_id", None))
    snap = rdir / "study.yaml"
    study = Study.load(snap) if snap.is_file() else current
    study.highlights, study.highlights_from = resolve(current, study)
    project = load_project(study.project)
    return study, project, study.expand(project.defaults), rdir


def _highlights(study, cases, log=print):
    """[(Highlight, Layout)] of this run (see iomcfd.highlights)."""
    from .highlights import plan

    hl = getattr(study, "highlights", [])
    if not hl:
        return []
    log(f"highlights from {study.highlights_from}")
    return plan(hl, cases, log)


def _target_run(args, study) -> Path:
    """Run directory to write into: a new run, the latest (--resume) or --run-id."""
    from .runner import is_run_id, new_run_id, resolve_run, study_dir

    run_id = getattr(args, "run_id", None)
    if getattr(args, "resume", False) or run_id == "latest":
        return resolve_run(study, _runs(args))
    if run_id and not is_run_id(run_id):
        raise SystemExit(f"--run-id {run_id}: expected YYYYMMDD-HHMMSS (UTC) or 'latest'")
    return study_dir(study, _runs(args)) / (run_id or new_run_id())


def _select(cases, args):
    if getattr(args, "only", None):
        wanted = set(args.only)
        cases = [c for c in cases if c.name in wanted or str(c.index) in wanted]
        if not cases:
            raise SystemExit(f"no case matches {sorted(wanted)}")
    idx = getattr(args, "index", None)
    if idx is not None:
        if not idx.lstrip("-").isdigit():  # name of an env var, e.g. BATCH_TASK_INDEX
            idx = os.environ.get(idx, "")
            if not idx.isdigit():
                raise SystemExit(f"--index: environment variable not set to an integer")
        cases = [cases[int(idx)]]
    return cases


# ---------------------------------------------------------------------------
# commands


def cmd_projects(args) -> None:
    from .project import list_projects

    for p in list_projects():
        studies = sorted((config.projects_dir() / p / "studies").glob("*.yaml"))
        print(f"{p:<14} {len(studies)} studies: " + ", ".join(s.stem for s in studies))


def cmd_plan(args) -> None:
    study, project, cases = _load(args)
    cases = _select(cases, args)
    print(f"study   {study.name}  (project {project.name}, {len(cases)} cases)")
    if study.description:
        print("        " + study.description.strip().replace("\n", "\n        "))
    keys = list(cases[0].varied) if cases else []
    print(f"\n{'#':>4}  {'case':<44} " + " ".join(f"{k:>12}" for k in keys))
    for c in cases:
        print(f"{c.index:>4}  {c.name:<44} " + " ".join(f"{str(c.varied[k]):>12}" for k in keys))
    if args.verbose and cases:
        print("\nfull parameters of case 0:")
        derived = project.derive(dict(cases[0].params))
        for k, v in {**cases[0].params, **derived}.items():
            print(f"  {k:<22} {v}")


def cmd_render(args) -> None:
    from .runner import RunOptions, run_study

    study, project, cases = _load(args)
    rdir = _target_run(args, study)
    run_study(project, study, _select(cases, args), RunOptions(render_only=True), rdir)
    print(f"rendered into {rdir}")


def cmd_run(args) -> None:
    if not config.in_container() and not args.no_docker:
        _exec_in_docker(["run", *sys.argv[sys.argv.index("run") + 1 :]], args)
        return
    from .results import collect
    from .runner import RunOptions, run_study

    study, project, cases = _load(args)
    cases = _select(cases, args)
    rdir = _target_run(args, study)
    np_ = args.np
    jobs = args.jobs or max(1, (os.cpu_count() or 1) // (np_ or int(cases[0].params.get("np", 1))))
    opts = RunOptions(jobs=jobs, np=np_, force=args.force, export=args.export, keep_fields=not args.no_fields,
                      checkpoint=args.checkpoint)
    if args.checkpoint_every:
        opts.checkpoint_seconds = args.checkpoint_every
    results = run_study(project, study, cases, opts, rdir)
    rows, out = collect(rdir)
    n_bad = sum(r["status"] == "failed" for r in results)
    print(f"results: {out}  ({len(rows)} cases, {n_bad} failed this time)")
    if opts.export:
        import shutil

        dst = Path(opts.export) / study.name / rdir.name
        dst.mkdir(parents=True, exist_ok=True)
        if study.path and not (dst / "study.yaml").exists():
            shutil.copy2(study.path, dst / "study.yaml")
    if n_bad:
        sys.exit(1)


def cmd_runs(args) -> None:
    import json as _json

    from .runner import list_runs, study_dir
    from .study import Study

    sdir = study_dir(Study.load(resolve_study_path(args.study)), _runs(args))
    for rid in list_runs(sdir):
        info = {}
        if (sdir / rid / "run.json").is_file():
            info = _json.loads((sdir / rid / "run.json").read_text())
        n_cases = sum(1 for p in (sdir / rid).iterdir() if (p / "params.json").is_file())
        report = "report" if (sdir / rid / "report").is_dir() else ""
        size = sum(f.lstat().st_size for f in (sdir / rid).rglob("*") if f.is_file())
        print(f"{rid}  {n_cases:>4} cases  {size / 1e6:>7.0f} MB  {info.get('backend', 'local'):<5} "
              f"git {info.get('git') or '?':<16} {report}")


def cmd_collect(args) -> None:
    from .results import collect

    rows, out = collect(_load_run(args)[3])
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(f"{out}: {len(rows)} cases " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))


def cmd_report(args) -> None:
    try:
        import pandas as pd
    except ImportError:
        raise SystemExit("report needs pandas + matplotlib: `uv sync` (dev group) or `pip install iomcfd[analysis]`")
    from .meshplot import study_mesh_figures
    from .results import collect
    from .summary import write_summary

    study, project, cases, rdir = _load_run(args)
    collect(rdir)
    df = pd.read_csv(rdir / "results.csv")
    out = rdir / "report"
    out.mkdir(exist_ok=True)
    files = project.report(df, out, reference=project.load_reference(study.reference), options=study.report)
    planned = _highlights(study, cases)
    for old in out.glob("highlight*"):  # rebuilt from the current highlights
        old.unlink()
    files += project.highlight_report(rdir, df, planned, out) if planned else []
    files += study_mesh_figures(project, rdir, df, out)
    files.append(write_summary(rdir, study, cases, df, files))
    print(f"run {rdir.name}")
    for f in files:
        print(f)


def cmd_slim(args) -> None:
    """Free disk: keep each case's results (and viz images), drop its mesh,
    logs and fields. The mesh of one case per mesh level stays for the
    report's mesh figure."""
    from .meshplot import mesh_candidates
    from .results import collect
    from .runner import slim_run

    study, _, _, rdir = _load_run(args)
    rows, _ = collect(rdir)
    keep = {names[0] for names in mesh_candidates(rows) if names}
    n, size = slim_run(rdir, keep, dry_run=not args.yes)
    print(f"{study.name} run {rdir.name}: {n} files, {size / 1e9:.2f} GB "
          + ("deleted" if args.yes else "would be deleted (run again with --yes)"))
    if not args.yes and n:
        print("Results (params.json, result.json, surface.csv), viz images, results.csv, report/ and the mesh of "
              f"{', '.join(sorted(keep))} are kept. Anything not also in the bucket is gone for good.")


def cmd_viz(args) -> None:
    """Render ParaView views of finished cases (in the iom-cfd-viz image)."""
    if not config.in_viz_container() and not args.no_docker:
        _exec_in_docker(["viz", *sys.argv[sys.argv.index("viz") + 1 :]], args, image=config.viz_image())
        return
    import json as _json

    from .highlights import case_names as highlight_case_names
    from .viz.study import VizOptions, visualize_study

    study, project, all_cases, rdir = _load_run(args)
    planned = _highlights(study, all_cases)
    if args.only or args.index is not None or args.all or not planned:
        cases = _select(all_cases, args)
    else:  # only the highlighted cases
        names = set(highlight_case_names(planned))
        cases = [c for c in all_cases if c.name in names]
    opts = VizOptions(
        views=args.views.split(",") if args.views else None,
        animate=args.animate,
        jobs=args.jobs or max(1, (os.cpu_count() or 2) // 2),
        no_time=args.no_time,
        options=_json.loads(args.options) if args.options else {},
    )
    visualize_study(project.name, study, cases, rdir, opts, all_cases=all_cases, highlights=planned)


def cmd_shell(args) -> None:
    _exec_in_docker(args.command or [], args, interactive=True, raw=True,
                    image=config.viz_image() if args.viz else None)


def _runs(args) -> Path:
    return Path(args.runs).resolve() if getattr(args, "runs", None) else config.runs_dir()


# ---------------------------------------------------------------------------
# docker delegation


def docker_base(interactive: bool = False, runs: Path | None = None) -> list[str]:
    repo = config.home()
    cmd = ["docker", "run", "--rm", "--init", "--shm-size=2g"]
    cmd += ["-it"] if interactive and sys.stdin.isatty() else []
    cmd += ["-v", f"{repo}:/work", "-w", "/work"]
    cmd += ["-e", "IOMCFD_HOME=/work", "-e", "PYTHONPATH=/work/src", "-e", "IOMCFD_IN_CONTAINER=1"]
    runs = runs or config.runs_dir()
    try:
        rel = runs.resolve().relative_to(repo)
        cmd += ["-e", f"IOMCFD_RUNS=/work/{rel}"]
    except ValueError:
        cmd += ["-v", f"{runs}:/runs", "-e", "IOMCFD_RUNS=/runs"]
    if platform.system() == "Linux":
        cmd += ["--user", f"{os.getuid()}:{os.getgid()}", "-e", "HOME=/tmp"]
    cmd += ["-e", f"IOMCFD_IMAGE_REF={config.image()}", "-e", f"IOMCFD_GIT={config.git_describe()}"]
    return cmd


def _exec_in_docker(argv: list[str], args, interactive: bool = False, raw: bool = False, image: str | None = None) -> None:
    repo = config.home()
    fixed = []
    for a in argv:  # rewrite host paths of study files to /work/...
        p = Path(a)
        if a.endswith((".yaml", ".yml")) and p.exists():
            try:
                a = "/work/" + str(p.resolve().relative_to(repo))
            except ValueError:
                raise SystemExit(f"{a} must be inside the repository ({repo}) to run in Docker")
        fixed.append(a)
    if "--runs" in fixed:  # runs dir is passed via env instead
        i = fixed.index("--runs")
        del fixed[i : i + 2]
    cmd = docker_base(interactive, _runs(args)) + [image or config.image()]
    cmd += (fixed or ["bash"]) if raw else ["iomcfd", *fixed]
    print("+ " + " ".join(cmd), file=sys.stderr)
    try:
        sys.exit(subprocess.call(cmd))
    except FileNotFoundError:
        raise SystemExit("docker not found; install Docker or run inside the container with --no-docker")


# ---------------------------------------------------------------------------


def cmd_site(args) -> None:
    from . import site

    if args.action == "export":
        for f in site.export(args.names or None):
            print(f.relative_to(site.site_dir()))
    else:
        site.build(preview=args.preview)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="iomcfd", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", help="runs directory (default: <repo>/runs or $IOMCFD_RUNS)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def study_cmd(name, func, help_):
        p = sub.add_parser(name, help=help_)
        p.add_argument("study")
        p.add_argument("--set", action="append", metavar="KEY=VALUE", help="override a parameter for all cases")
        p.add_argument("--only", nargs="+", metavar="CASE", help="case names or indices")
        p.add_argument("--index", help="run only case #INDEX (int or env var name, e.g. BATCH_TASK_INDEX)")
        p.set_defaults(func=func)
        return p

    sub.add_parser("projects", help="list projects").set_defaults(func=cmd_projects)
    p = study_cmd("plan", cmd_plan, "list the cases of a study")
    p.add_argument("-v", "--verbose", action="store_true")
    def target_run(p):
        p.add_argument("--run-id", metavar="ID", help="write into this run (YYYYMMDD-HHMMSS, UTC; created if "
                       "missing) instead of a new one")
        p.add_argument("--resume", action="store_true", help="continue the latest run: skip its finished cases")

    def existing_run(p):
        p.add_argument("--run-id", metavar="ID", help="which run (default: the latest; see `iomcfd runs`)")

    target_run(study_cmd("render", cmd_render, "write case directories without running"))
    p = study_cmd("run", cmd_run, "run a study (in Docker unless already inside the container)")
    target_run(p)
    p.add_argument("-j", "--jobs", type=int, help="cases in parallel (default: cpus / np)")
    p.add_argument("--np", type=int, help="MPI ranks per case (overrides the study)")
    p.add_argument("--force", action="store_true", help="with --resume / --run-id: re-run finished cases too")
    p.add_argument("--export", type=Path, help="copy finished cases to this directory")
    p.add_argument("--no-fields", action="store_true", help="with --export: skip the final field directory")
    p.add_argument("--checkpoint", type=Path, help="keep checkpoints of long cases here and resume from them "
                   "(<dir>/<study>/<run id>/<case>; cloud jobs: the bucket)")
    p.add_argument("--checkpoint-every", type=float, metavar="SECONDS",
                   help="with --checkpoint: seconds between checkpoints (default 900)")
    p.add_argument("--no-docker", action="store_true", help="run with the local OpenFOAM installation")
    p = study_cmd("viz", cmd_viz, "render ParaView views, study animations and a gallery (viz image)")
    existing_run(p)
    p.add_argument("--all", action="store_true", help="every case, not only the study's highlights")
    p.add_argument("--views", help="comma-separated view names (default: those of the highlights, else "
                   "project/study defaults)")
    p.add_argument("--animate", help="swept parameter for study animations (default: auto)")
    p.add_argument("-j", "--jobs", type=int, help="cases rendered in parallel (default: cpus / 2)")
    p.add_argument("--options", help='JSON options for the views, e.g. \'{"q_level": 3}\'')
    p.add_argument("--no-time", action="store_true", help="skip time-series animations of transient cases")
    p.add_argument("--no-docker", action="store_true", help="run with the local ParaView installation")
    p = sub.add_parser("runs", help="list the runs of a study")
    p.add_argument("study")
    p.set_defaults(func=cmd_runs)
    p = sub.add_parser("collect", help="gather results into results.csv")
    p.add_argument("study")
    existing_run(p)
    p.set_defaults(func=cmd_collect)
    p = sub.add_parser("report", help="plots, comparison tables and summary.md from results.csv")
    p.add_argument("study")
    existing_run(p)
    p.set_defaults(func=cmd_report)
    p = sub.add_parser("slim", help="delete a local run's meshes, logs and fields; keep its results")
    p.add_argument("study")
    existing_run(p)
    p.add_argument("--yes", action="store_true", help="delete (default: only show what would go)")
    p.set_defaults(func=cmd_slim)
    p = sub.add_parser("shell", help="interactive shell (or a command) in the container")
    p.add_argument("--viz", action="store_true", help="use the visualisation (ParaView) image")
    p.add_argument("command", nargs=argparse.REMAINDER)
    p.set_defaults(func=cmd_shell)
    p = sub.add_parser("site", help="the website (site/): export data from runs, build with Quarto")
    p.add_argument("action", choices=["export", "build"])
    p.add_argument("names", nargs="*", help="export: entries of site/data.yaml (default: all)")
    p.add_argument("--preview", action="store_true", help="build: serve and rebuild on change")
    p.set_defaults(func=cmd_site)

    from .cloud import gcp
    from .vpp import cli as vpp_cli

    gcp.add_parser(sub)
    vpp_cli.add_parser(sub)
    return ap


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
