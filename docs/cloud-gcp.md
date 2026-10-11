# Running on Google Cloud (Batch)

Each study becomes one [Cloud Batch](https://cloud.google.com/batch) job with
one task per case. Every task runs the solver image, works on the VM's local
disk, and copies the finished case (without processor directories and
intermediate time steps) to a Cloud Storage bucket mounted with Cloud Storage
FUSE. VMs are Spot by default, and preempted tasks retry automatically
(exit code 50001).

## One-time setup

1. Install the [gcloud CLI](https://cloud.google.com/sdk/docs/install) and log
   in: `gcloud auth login`.
2. `cp cloud/gcp/config.env.example cloud/gcp/config.env` and fill in the
   project id, region, bucket name and service account (it's git-ignored).
3. `cloud/gcp/setup.sh` enables the APIs (Batch, Compute, Logging, Artifact
   Registry, Storage), creates the Docker repository, the bucket and a service
   account with only the roles Batch VMs need (`batch.agentReporter`,
   `logging.logWriter`, `artifactregistry.reader` on the repo,
   `storage.objectUser` on the bucket). It asks before creating anything.
4. Your own account needs `roles/batch.jobsEditor` and
   `roles/iam.serviceAccountUser` on that service account.

## Image

```bash
make push      # docker buildx: linux/amd64 + linux/arm64, tags <git describe> and latest
```

The image contains the code, templates and `geometry/`. Rebuild and push
after changing templates or `src/`. Study YAMLs and `geometry/` are uploaded
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
uv run iomcfd gcp fetch foil2d/keel-sections                 # bucket -> runs/, then results.csv
uv run iomcfd gcp fetch foil2d/keel-sections --fields        # also final flow fields
```

Job specs are saved in `cloud/gcp/jobs/` for reference.

How tasks are packed: each case gets `np` MPI ranks, each rank a physical
core (2 vCPUs on SMT families such as C3D/C2D, 1 vCPU on H3, T2D, C4A).
Batch then packs as many tasks per VM as fit. Example: a `c3d-standard-16`
runs eight single-core foil2d cases at once.

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
* Logs: `gcloud logging read` with the query `iomcfd gcp status <job>`
  prints, or in the Cloud console under Batch.
* Results land in `gs://<bucket>/runs/<study>/<case>/`, mirroring the local
  `runs/` layout, so fetched results merge with local ones.
