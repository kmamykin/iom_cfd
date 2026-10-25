# Running on Google Cloud (Batch)

Each study becomes one [Cloud Batch](https://cloud.google.com/batch) job with
one task per case. Every task runs the solver image, works on the VM's local
disk, and copies the finished case (without processor directories and
intermediate time steps; mesh and logs gzipped) to a Cloud Storage bucket
mounted with Cloud Storage FUSE. VMs are Spot by default, and preempted tasks
retry automatically (exit code 50001). Long cases keep checkpoints in the
bucket and resume from them when retried (Checkpoints, below).

## One-time setup

1. Install the [gcloud CLI](https://cloud.google.com/sdk/docs/install) and log
   in: `gcloud auth login`.
2. `cp cloud/gcp/config.env.example cloud/gcp/config.env` and fill in the
   project id, region, bucket name and service account (it's git-ignored).
3. `cloud/gcp/setup.sh` enables the APIs (Batch, Compute, Logging, Artifact
   Registry, Storage), creates the Docker repository, the bucket and a service
   account with only the roles Batch VMs need (`batch.agentReporter`,
   `logging.logWriter`, `artifactregistry.reader` on the repo,
   `storage.objectUser` on the bucket). It asks before creating anything
   (`-y` skips the question, e.g. when run with `!` from Claude Code) and
   does not change your active gcloud configuration.
4. Your own account needs `roles/batch.jobsEditor` and
   `roles/iam.serviceAccountUser` on that service account.

## Image

Every push to a branch builds and pushes the solver image from GitHub
Actions ([.github/workflows/image.yml](../.github/workflows/image.yml)):
fast tests first, then `docker/Dockerfile` for linux/amd64, tagged
`<git describe>` (the short commit hash). Pushes to `main` also move
`latest`, the default `IMAGE_TAG`; a branch's image runs with
`iomcfd gcp submit <study> --tag <git describe>` (e.g. a pull request's
branch, before merging). Run the workflow by hand with
`gh workflow run image.yml --ref <branch>`. Local builds (`make image`) are
unaffected.

One-time setup, after `setup.sh`:

```bash
cloud/gcp/setup-github.sh     # asks first; -y to skip the question
```

It sets up Workload Identity Federation, so GitHub gets short-lived tokens
and no service account key exists anywhere. Only workflow runs on branches
of this repository (pushes and manual runs, not `pull_request` events, so
not forks) are accepted. They act as the `iom-cfd-ci`
service account, which can push to the image repository and nothing else.
The script also sets the repository variables the workflow reads
(`GCP_PROJECT`, `GCP_REGION`, `AR_REPO`, `IMAGE_NAME`, `GCP_WIF_PROVIDER`,
`GCP_CI_SA`) with the `gh` CLI, or prints them if `gh` is not logged in.
These are identifiers, not credentials; in a public repository they show
up in the Actions logs.

Manual pushes still work, e.g. to test an image before committing:

```bash
make push      # docker buildx: linux/amd64 + linux/arm64, tag <git describe>
make push-amd64  # x86 only (all Cloud Batch needs); much faster from an Apple Silicon Mac
```

They tag `<git describe>` only (`-dirty` for uncommitted changes); run them
with `--tag`. Only CI on `main` moves `latest`, so a branch's image never
becomes the default of every job by accident.

The image contains the code, templates and `geometry/`, so changes to
templates or `src/` reach the cloud once they are pushed (`latest`: to
`main`). Study YAMLs and `geometry/` are uploaded
at submit time, so new studies and new STL files don't need a rebuild. Set
`IMAGE_TAG` in `config.env` to a git tag to pin a reproducible version; the
tag is recorded in every `result.json` (`image`).

## Submitting

```bash
uv run iomcfd gcp submit foil2d/keel-sections --dry-run      # write the job JSON only
uv run iomcfd gcp submit foil2d/keel-sections                # 2D sweep, default machine
uv run iomcfd gcp submit appendage3d/leeway-sweep --machine h3-standard-88 --np 44
uv run iomcfd gcp status                                     # recent jobs
uv run iomcfd gcp status <job-name>                          # task counts + log query
uv run iomcfd gcp progress foil2d/keel-sections              # newest job: each task's latest progress lines
uv run iomcfd gcp progress foil2d/keel-sections --run-id 20261012-045433 --lines 10
uv run iomcfd gcp fetch foil2d/keel-sections                 # latest run's results -> runs/<study>/<run id>/
uv run iomcfd gcp fetch foil2d/keel-sections --run-id 20261012-045433   # a particular run
uv run iomcfd gcp fetch foil2d/keel-sections --logs          # + logs of failed / not-converged cases
uv run iomcfd gcp fetch foil2d/keel-sections --fields        # + whole cases of the study's highlights (for viz)
uv run iomcfd gcp fetch foil2d/keel-sections --only aoa4_foilnaca0008   # + these whole cases
```

## Fetching: what comes to your machine

The bucket keeps every run in full; `fetch` downloads only what you need
(`gcloud storage rsync`, so repeating it only adds what is missing):

| Fetched | What | Size (foil2d, medium mesh) | Needed by |
|---|---|---|---|
| always | `study.yaml`, `run.json`, each case's `params.json`, `result.json`, `surface.csv` | about 40 kB per case | collect, report, summary.md, findings |
| always | mesh and checkMesh log of one case per mesh level | 6 MB gzipped (20 MB before compression) | the report's mesh figure |
| `--logs` | solver logs of failed and not-converged cases | about 0.2 MB per case gzipped | diagnosing them |
| `--fields` | whole cases of the study's `highlights:` (all cases if it has none) | about 15 MB per case | `iomcfd viz` |
| `--only CASE...` | whole cases | about 15 MB per case | `iomcfd viz --only`, re-running a case |

A whole medium foil2d case in the bucket is about 15 MB with the mesh and
logs gzipped (31 MB before compression: mesh 20 MB, final fields 8 MB, log
2 MB, postProcessing 1 MB), so a 450-case run is about 7 GB there and about
20 MB on your machine after a default fetch. Cloud Storage costs about
$0.02 per GB-month; delete old runs in the bucket with
`gcloud storage rm -r gs://<bucket>/runs/<study>/<run id>` (soft delete
keeps them recoverable for 7 days). `iomcfd slim` frees space locally
(docs/workflow.md).

Every submit is a new run of the study. The run id (UTC submit time,
`YYYYMMDD-HHMMSS`) names the job (`iomcfd-<study>-<run id>`), is a job label
(`run`), and is the results directory. The study file and `run.json` are
uploaded to that directory first, and tasks read the study from there, so
editing or resubmitting a study never affects a job that is already running.
The job spec and `run.json` are also saved locally in
`cloud/gcp/jobs/<job name>/`.

`--parallelism` caps how many tasks run at once. Without it, `submit` sets
it from the quotas' headroom at submit time and prints how. Batch would
otherwise ask for every task's VM at once. If that is over a quota, the
instance group can't create the VMs, and after a few retries the job stays
queued for good. The quotas checked are:
* VM instances in the region (24 here);
* the machine family's vCPUs in the region. Older families have their own
  quota, e.g. C2D_CPUS (100). Newer ones (C3D, H3, C4…) count against
  CPUS_PER_VM_FAMILY, read with `gcloud beta quotas`; C3D is 150 here;
* vCPUs in all regions (512).

Usage counts every live VM in the project, other sessions' jobs too. With
no headroom the job gets one VM and waits in the queue. Example (bulb-section,
2026-10-19): 39 one-VM keel3d tasks with 116 of 150 C3D vCPUs in use leaves
room for 2 `c3d-standard-16` VMs. The same study on `c2d-standard-16` (8
physical cores too, its own 100-vCPU quota) ran 6 at a time.

The cap is fixed at submit time: a job submitted while the quotas are full
stays at its few VMs after they free up. Pass `--parallelism` to choose.

How tasks are packed: each case gets `np` MPI ranks, each rank a physical
core (2 vCPUs on SMT families such as C3D/C2D, 1 vCPU on H3, T2D, C4A).
Batch then packs as many tasks per VM as fit. Example: a `c3d-standard-16`
runs eight single-core foil2d cases at once.

## Checkpoints: surviving Spot preemption

A preempted task is retried on a new VM, and the case would start from
scratch: a foil2d time-accurate case at 1.5 m/s needs 16-24 h on one core,
and in October 2026 the Spot VMs in us-central1 were preempted every 11-14 h
(custom-section-transient lost 25 h that way). So every job runs with
`--checkpoint <bucket>/checkpoints`
([src/iomcfd/checkpoint.py](../src/iomcfd/checkpoint.py)):

* While a case runs, the runner copies its newest completely written time
  directory and `postProcessing/` (the force history) to
  `gs://<bucket>/checkpoints/<study>/<run id>/<case>/`, at most every 15 min.
  Two slots alternate and a manifest is written last, so a preemption
  during a copy can't spoil the previous checkpoint.
* A retried task renders the case as usual, copies the checkpoint in, and
  the solver continues from it (the templates start from `latestTime`). The
  job log says `resumed   <case> from its checkpoint at t = ...`, and
  `result.json` has `resumed_from`. The force history joins across the
  restart (foil2d reads every `postProcessing/forceCoeffs/<start>/`).
* A case that finishes deletes its checkpoint; a failed one keeps it.
* Tasks are retried up to 6 times.

**Every case is checkpointed**, in every project, steady or time-accurate,
on one rank or many. `Project.checkpoint_setup` picks how the solver writes:
* **"signal"** (the default). Every 15 minutes the runner sends the solver
  `SIGUSR1`. The case's `system/controlDict` gets `OptimisationSwitches {
  writeNowSignal 10; }`, so OpenFOAM writes its fields at the end of that
  time step and carries on. For a parallel case the signal goes to
  `mpirun`, which passes it on to every rank. The templates' `purgeWrite`
  removes the older writes.
  * The signal is sent only once the solver has installed its handler: its
    log says `sigWriteNow : Enabling writing upon signal 10` and has a first
    time step.
  * It is never sent to meshing or initialisation tools, which `SIGUSR1`
    would kill.
* **True**: the project makes the solver write periodically itself.
  foil2d's time-accurate cases write every flow-through, keeping the last
  two, so at most about one flow-through of work is lost per preemption.
  Those writes land the adjustable time step on the write times, so the time
  steps differ slightly from a run without checkpoints.

**What a checkpoint holds.**
* A decomposed case (np > 1): `processor*/<time>`. A serial case: `<time>`.
* Once per case:
  * the final mesh, `processor*/constant/polyMesh` or `constant/polyMesh`;
  * the logs of the steps before the solver (blockMesh, snappyHexMesh,
    checkMesh, decomposePar, a steady start).

**How a resumed task restarts.** It restores the mesh, the logs and the
fields, and sets `IOMCFD_RESUME`. Every template's Allrun then skips meshing,
decomposition and field initialisation and goes straight to the solver. A
3D case doesn't run snappyHexMesh again, whose mesh might not match the saved
fields cell for cell. A checkpoint is only restored into a case with the
same parameters (`params_hash`) and the same number of MPI ranks.

`tests/test_projects.py` checks that every project can be resumed, so a new
project or template can't leave this out. Locally, `iomcfd run --checkpoint
DIR [--checkpoint-every SECONDS]` does the same.

Checked with a real case (2026-10-19). foil2d NACA 0009, xcoarse mesh,
4 flow-throughs after a 200-iteration steady start; the solver was killed
(exit 137) just after the 2-flow-through checkpoint and run again in an
empty directory:
* it resumed at t = 0.16 s, with the old-time fields (`U_0`, `phi_0`,
  `k_0`, ...) and the time step it had (0.00123 s);
* it didn't repeat the steady start;
* its force history is continuous across the restart;
* it finished ok with 4.0 flow-throughs, the last fields written at the
  end time, and the checkpoint deleted.

Signal checkpoints were checked with real cases in Docker on 2026-10-22.
Each case was killed after its first checkpoint and run again in an empty
directory:
* **foil2d smoke, steady, 1 rank:** it saved iteration 1001 and resumed at
  1002.
* **foil2d smoke, 2 ranks:** it saved iteration 1849, with both processors'
  fields and meshes, and resumed at 1850 without running decomposePar
  again. It was then reconstructed and extracted.
* **appendage3d smoke, 2 ranks:** it saved the snappyHexMesh mesh (32 MB)
  and the meshing logs with iteration 78, and resumed at 79 without meshing.

Each case then finished: the foil2d ones at their iteration limit, and
appendage3d converged ok at iteration 254. The decomposed ones were
reconstructed, every case was extracted, and its checkpoint was deleted.

## Choosing machines

Prices are us-central1 list prices for October 2026 (Cloud Billing Catalog),
rounded. Spot prices change daily.

| Workload | Machine | Notes |
|---|---|---|
| foil2d sweeps (1 core per case) | `c3d-standard-16` Spot (~$0.18/h incl. memory) | Cheapest per core-hour; 8 cases per VM. |
| 3D / hull / sails (8-88 ranks) | `h3-standard-88` (~$4.9/h on demand) | 88 physical cores, high memory bandwidth, built for CFD. Only in us-central1-a; Spot availability for H3 is unconfirmed. |
| Budget 3D | `c3d-standard-60` Spot (30 physical cores) | Use `--np 30`. |
| Arm (C4A Axion) | Not by default | Batch's default container images are x86 only, and C4A needs a Hyperdisk boot disk. Possible later with a custom Arm boot image. |

Rough cost of a medium foil2d polar (10 angles, up to about an hour each on
one core) on Spot C3D: well under $1. Run times of the 3D projects at medium
resolution have not been measured yet; run one case first and scale from its
`wall_time_s`.

## Notes

* Batch runs containers as root. The image sets `OMPI_ALLOW_RUN_AS_ROOT`, and
  tasks get `--shm-size` scaled to their memory for MPI shared memory.
* Logs: `iomcfd gcp progress <study>` shows each task's newest lines. Every
  10 minutes a running case logs a progress line: time and % done, ETA,
  `deltaT`, Courant number, forces and their drift. A diverging case is
  stopped and logs `DIVERGED <case>: <reason>`. See "Progress and
  divergence" in [workflow.md](workflow.md). The full log: `gcloud logging
  read` with the query `iomcfd gcp status <job>` prints, or in the Cloud
  console under Batch.
* Results land in `gs://<bucket>/runs/<study>/<run id>/<case>/`, the same
  layout as local `runs/`.
