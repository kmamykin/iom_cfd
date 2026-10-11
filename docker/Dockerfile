# IOM CFD solver image: ESI OpenFOAM v2512 + the iomcfd Python tooling.
#
# Multi-arch (linux/amd64 + linux/arm64) because the base image is. Runs
# natively on Apple Silicon and on x86 or Arm (Axion/Ampere) cloud VMs.
#
# Build:   make image            (local, native arch)
#          make push             (multi-arch, pushes to Artifact Registry)
ARG OPENFOAM_VERSION=2512
FROM opencfd/openfoam-default:${OPENFOAM_VERSION}

ARG OPENFOAM_VERSION
ENV OPENFOAM_VERSION=${OPENFOAM_VERSION} \
    FOAM_BASHRC=/usr/lib/openfoam/openfoam${OPENFOAM_VERSION}/etc/bashrc \
    DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Open MPI refuses to run as root unless told otherwise (containers run as root).
    OMPI_ALLOW_RUN_AS_ROOT=1 \
    OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1 \
    # Avoid the vader/CMA "process_vm_readv" failures inside containers.
    OMPI_MCA_btl_vader_single_copy_mechanism=none

# Python runtime for case generation and post-processing. Ubuntu 24.04 ships
# numpy 1.26 / scipy 1.11 / pyyaml 6, which is all the solver side needs.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        python3 python3-numpy python3-scipy python3-yaml \
        ca-certificates rsync zstd \
 && rm -rf /var/lib/apt/lists/*

# The tooling and project templates. At runtime IOMCFD_HOME can be pointed at a
# bind-mounted checkout instead (that is what `iomcfd run` does locally), so
# template edits do not need an image rebuild.
COPY src /opt/iom-cfd/src
COPY projects /opt/iom-cfd/projects
COPY geometry /opt/iom-cfd/geometry
COPY docker/entrypoint.sh /opt/iom-cfd/docker/entrypoint.sh
RUN chmod +x /opt/iom-cfd/docker/entrypoint.sh \
 && printf '#!/bin/sh\nexec python3 -m iomcfd "$@"\n' > /usr/local/bin/iomcfd \
 && chmod +x /usr/local/bin/iomcfd

ENV IOMCFD_HOME=/opt/iom-cfd \
    PYTHONPATH=/opt/iom-cfd/src \
    IOMCFD_IN_CONTAINER=1

WORKDIR /work
# Replaces /openfoam/run, which cd's to $HOME and would ignore `-w /work`.
ENTRYPOINT ["/opt/iom-cfd/docker/entrypoint.sh"]
CMD ["bash"]
