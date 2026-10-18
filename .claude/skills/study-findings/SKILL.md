---
name: study-findings
description: Analyse a finished iom_cfd study run and add an entry to its findings log (conclusions, evidence tables, assumptions, compromises, learnings, next steps), comparing with earlier runs of the study and related studies. Use after a run has finished and `iomcfd report` has been run, when the user asks what a run showed, or to record decisions about a study.
argument-hint: <project>/<study> [run id]
---

# Study findings

Turn one finished run into a dated entry in the study's findings log,
`projects/<project>/findings/<study>.md`. That file is committed; `runs/` is
not. So the log must carry the numbers its conclusions rest on.

Arguments: `<project>/<study>` and optionally a run id (YYYYMMDD-HHMMSS); the
default is the latest run.

## 1. Make the report current (no cases are re-run)

```bash
uv run iomcfd runs <project>/<study>                 # pick the run
uv run iomcfd report <project>/<study> [--run-id ID]  # plots, tables, report/summary.md
```

Results live in `runs/<study>/<run id>/`. If the run is on GCP and not yet
local: `uv run iomcfd gcp fetch <project>/<study> --run-id ID`. That
downloads only the results (a few MB), which is all the report and this
analysis need. Never fetch whole runs (the laptop's disk is limited); for
flow pictures of the highlighted cases add `--fields` and run
`uv run iomcfd viz <project>/<study> --run-id ID`, and for the logs of
failed cases add `--logs`.

## 2. Read, in this order

1. `report/summary.md`: the facts. Setup, status counts, failures and why,
   where cases did not converge or were unsteady (by parameter), compute
   used, and project tables such as `selection_compare.md`.
2. `study.yaml` in the run directory: its `description` states the intent,
   the hypotheses and the known caveats. Read this copy, not the one in
   `projects/`, which may have changed since. Also read `run.json`: git
   version, image, `--set` overrides.
3. The figures in `report/*.png` (open them with Read and look at them).
   The highlights (the cases the study names for a close look) are in
   `report/highlights.md` (separation and reattachment points, Cl, Cd) and
   `report/highlight_<name>.png` (foil2d: Cp and Cf along the chord). If
   `viz/highlights.md` exists, look at its montages too.
4. Earlier context:
   * `projects/<project>/findings/<study>.md`, for earlier runs and
     decisions;
   * the other `projects/<project>/findings/*.md`, for related studies such
     as validations;
   * the project `README.md`, for its validation section and known limits.

## 3. Analyse

* Recompute anything you state from `results.csv` and `report/*.csv` with
  short `uv run python` snippets. Never estimate a number from a figure if
  the CSV has it.
* For every conclusion, check whether it holds across the nuisance
  parameters the run swept (turbulence intensity, mesh, model) and across
  operating conditions. Quantify it: how many of N comparisons agree, and
  the size of the differences. Compare at the physically relevant
  condition; in foil2d that is equal side force, not equal Cl.
* Say which conclusions rest on failed, not-converged or unsteady cases.
* Against the previous run of the same study:
  * what changed (`diff` the two `study.yaml` copies);
  * whether earlier conclusions still hold, and how much numbers moved on
    the cases both runs share;
  * name any earlier conclusion that is now superseded.
* Look for surprises (non-monotonic trends, outliers, a lift reversal, a
  mesh effect) and explain or flag them.

## 4. Write the entry

Insert it below the file's intro, above earlier entries (newest first).
Create the file with a short intro if it does not exist. Do not rewrite
earlier entries.

```markdown
## Run <run id> (<date>, git <x>, <local|GCP>, <n> cases)

**Setup.** What was swept and fixed, mesh, solver; what changed since the previous run and why.
**Outcome.** ok / not converged / failed / unsteady counts.

### Conclusions
Numbered, each one sentence in bold, then the support (numbers) and a confidence word (high / medium / low) with the reason.

### Evidence
The table(s) the conclusions rest on, copied from report/*.md and trimmed to what matters; how they were computed.

### Decisions
What this run changes for the next one (parameters fixed or dropped, cases added), and the cost of each choice.

### Assumptions
Every input not computed in this run, with its source. Mark **not verified** where so.

### Compromises
What was cut or accepted (mesh, steady solver, failed cases left, sweep resolution) and its likely effect on the conclusions.

### Learnings
About the physics, the solver, the workflow, and compute and cost.

### Open questions and next steps
Including the highlights for the next run: which cases to look at closely,
and why, given what this run showed.
```

## Rules

* Never edit anything under `runs/`. To change a result, change the project
  or study and run again.
* Every number has to be traceable to a file of the run, or be labelled an
  assumption. Don't present a guess as a finding, and give unverified
  sources as unverified.
* State uncertainty plainly: "10 of 17 comparisons agree" is better than
  "robust".
* Use the symbols in docs/nomenclature.md for forces, moments and angles:
  S_h, D_h = D_v + D_i, leeway β_Y, heel φ, β_TW and β_AW (from the course),
  V_b. Output and parameter names (`Cl`, `aoa`, `drag_N`) stay as they are.
* If the analysis contradicts something said earlier (in the log, the
  README or the study description), say so explicitly in the new entry.
* Keep the study YAML and README as they are unless the user asks. Propose
  the edits in your reply instead, including a `highlights:` block (YAML,
  docs/workflow.md): a few cases each, a `why` that names the finding or
  question, `compare` along the parameter in question. Explain a surprise,
  check a close call, show what drives a ranking; not every case.
* Finish by telling the user, in a few lines, the main conclusions and any
  changes you suggest to the next run.

Headless (e.g. at the end of a batch script):
`claude -p "/study-findings foil2d/fin-profile-selection"`.
