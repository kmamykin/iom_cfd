"""keel3d's 2D table for the transition correction, from a foil2d run.

    uv run python tools/keel3d_transition_table.py runs/transition-delta/<run id> \\
        projects/keel3d/data/naca0007-transition.csv [time-accurate.csv ...]

Keeps the converged and not-converged cases (failed ones are dropped) and the
columns keel3d.transition_delta needs, plus the quality flags. Time-accurate
points (foil2d transient-check exports in site/data/, Tu 0.1 %, kOmegaSSTLM)
replace the steady ones at the same foil, chord, angle and speed, as in
foil2d/methodology.md; their `source` names the run. The first line names
the runs.
"""
import json
import sys
from pathlib import Path

import pandas as pd

run, out, extra = Path(sys.argv[1]), Path(sys.argv[2]), [Path(a) for a in sys.argv[3:]]
df = pd.read_csv(run / "results.csv")
df = df[df["status"].isin(["ok", "not_converged"])].copy()
info = json.loads((run / "run.json").read_text())
df["source"] = f"{info['study']} {info['run_id']} (steady)"
used = []
for f in extra:
    ta = pd.read_csv(f)
    foil = df["foil"].iloc[0]
    for _, t in ta[(ta["foil"] == foil) & (ta.get("max_co", 10) == 10) if "max_co" in ta else (ta["foil"] == foil)].iterrows():
        m = ((df["turbulence"] == "kOmegaSSTLM") & (df["Tu"] == 0.1) & (df["chord"].round(4) == round(t["chord"], 4))
             & (df["aoa"] == t["aoa"]) & (df["speed"] == t["speed"]))
        if m.sum() == 1:
            for c in ("Cl", "Cd", "Cl_std", "Cd_friction"):
                df.loc[m, c] = t[c]
            df.loc[m, ["status", "unsteady", "source"]] = ["ok", True, f"transient-check {t['run']} (time-accurate)"]
            used.append(f"{t['chord']:g} m {t['aoa']:g} deg")
cols = [c for c in ("foil", "turbulence", "Tu", "chord", "speed", "Re", "aoa", "Cl", "Cd", "Cd_friction", "Cl_std",
                    "Cd_std", "unsteady", "status", "source") if c in df]
out.parent.mkdir(parents=True, exist_ok=True)
with out.open("w") as fh:
    fh.write(f"# foil2d {info['study']} run {info['run_id']} (git {info.get('git')}), steady, {len(df)} cases;"
             f" time-accurate at Tu 0.1 %: {', '.join(used) or 'none'}\n")
    df.sort_values(["turbulence", "Tu", "chord", "aoa"])[cols].to_csv(fh, index=False)
print(f"{out}: {len(df)} rows, {len(used)} time-accurate: {used}")
