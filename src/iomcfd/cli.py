"""iomcfd command line.

    iomcfd projects                         list projects
    iomcfd plan    STUDY                    show the cases a study expands to
    iomcfd render  STUDY                    write OpenFOAM case dirs, don't run
    iomcfd run     STUDY [-j N] [--np P]    render + mesh + solve + extract
    iomcfd collect STUDY                    gather results -> runs/<study>/results.csv
    iomcfd report  STUDY                    plots from results.csv (host, needs [analysis])
    iomcfd shell                            OpenFOAM shell in the container (host)
    iomcfd gcp ...                          Google Cloud Batch (see `iomcfd gcp -h`)

STUDY is a path to a study YAML or the short form <project>/<study>
(= projects/<project>/studies/<study>.yaml).

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
    run_study(project, study, _select(cases, args), RunOptions(render_only=True), runs=_runs(args))
    print(f"rendered into {_runs(args) / study.name}")


def cmd_run(args) -> None:
    if not config.in_container() and not args.no_docker:
        _exec_in_docker(["run", *sys.argv[sys.argv.index("run") + 1 :]], args)
        return
    from .results import collect
    from .runner import RunOptions, run_study, study_dir

    study, project, cases = _load(args)
    cases = _select(cases, args)
    np_ = args.np
    jobs = args.jobs or max(1, (os.cpu_count() or 1) // (np_ or int(cases[0].params.get("np", 1))))
    opts = RunOptions(jobs=jobs, np=np_, force=args.force, export=args.export, keep_fields=not args.no_fields)
    results = run_study(project, study, cases, opts, runs=_runs(args))
    rows, out = collect(study_dir(study, _runs(args)))
    n_bad = sum(r["status"] == "failed" for r in results)
    print(f"results: {out}  ({len(rows)} cases, {n_bad} failed this run)")
    if opts.export:
        import shutil

        dst = Path(opts.export) / study.name
        dst.mkdir(parents=True, exist_ok=True)
        if study.path:
            shutil.copy2(study.path, dst / "study.yaml")
    if n_bad:
        sys.exit(1)


def cmd_collect(args) -> None:
    from .results import collect
    from .runner import study_dir
    from .study import Study

    study = Study.load(resolve_study_path(args.study))
    rows, out = collect(study_dir(study, _runs(args)))
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(f"{out}: {len(rows)} cases " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))


def cmd_report(args) -> None:
    try:
        import pandas as pd
    except ImportError:
        raise SystemExit("report needs pandas + matplotlib: `uv sync` (dev group) or `pip install iomcfd[analysis]`")
    from .project import load_project
    from .results import collect
    from .runner import study_dir
    from .study import Study

    study = Study.load(resolve_study_path(args.study))
    sdir = study_dir(study, _runs(args))
    collect(sdir)
    df = pd.read_csv(sdir / "results.csv")
    out = sdir / "report"
    out.mkdir(exist_ok=True)
    project = load_project(study.project)
    files = project.report(df, out, reference=project.load_reference(study.reference))
    for f in files:
        print(f)


def cmd_shell(args) -> None:
    _exec_in_docker(args.command or [], args, interactive=True, raw=True)


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
    cmd += ["-e", f"IOMCFD_IMAGE_REF={config.image()}"]
    return cmd


def _exec_in_docker(argv: list[str], args, interactive: bool = False, raw: bool = False) -> None:
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
    cmd = docker_base(interactive, _runs(args)) + [config.image()]
    cmd += (fixed or ["bash"]) if raw else ["iomcfd", *fixed]
    print("+ " + " ".join(cmd), file=sys.stderr)
    try:
        sys.exit(subprocess.call(cmd))
    except FileNotFoundError:
        raise SystemExit("docker not found; install Docker or run inside the container with --no-docker")


# ---------------------------------------------------------------------------


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
    study_cmd("render", cmd_render, "write case directories without running")
    p = study_cmd("run", cmd_run, "run a study (in Docker unless already inside the container)")
    p.add_argument("-j", "--jobs", type=int, help="cases in parallel (default: cpus / np)")
    p.add_argument("--np", type=int, help="MPI ranks per case (overrides the study)")
    p.add_argument("--force", action="store_true", help="re-run finished cases")
    p.add_argument("--export", type=Path, help="copy finished cases to this directory")
    p.add_argument("--no-fields", action="store_true", help="with --export: skip the final field directory")
    p.add_argument("--no-docker", action="store_true", help="run with the local OpenFOAM installation")
    p = sub.add_parser("collect", help="gather results into results.csv")
    p.add_argument("study")
    p.set_defaults(func=cmd_collect)
    p = sub.add_parser("report", help="plots from results.csv")
    p.add_argument("study")
    p.set_defaults(func=cmd_report)
    p = sub.add_parser("shell", help="interactive shell (or a command) in the container")
    p.add_argument("command", nargs=argparse.REMAINDER)
    p.set_defaults(func=cmd_shell)

    from .cloud import gcp

    gcp.add_parser(sub)
    return ap


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
