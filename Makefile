# IOM CFD - common tasks.  `make help`
SHELL := /bin/bash
IMAGE ?= iom-cfd:latest
OPENFOAM_VERSION ?= 2512

# Cloud image coordinates come from cloud/gcp/config.env (see config.env.example)
-include cloud/gcp/config.env
GIT_TAG := $(shell git describe --always --dirty 2>/dev/null || echo dev)
REMOTE_IMAGE = $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT)/$(AR_REPO)/$(or $(IMAGE_NAME),iom-cfd)

.PHONY: help setup image viz-image shell test test-docker smoke push push-viz clean-runs

help:  ## list targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

setup:  ## create the local Python env (uv) for planning, analysis and tests
	uv sync

image:  ## build the solver image for this machine's architecture
	docker build --build-arg OPENFOAM_VERSION=$(OPENFOAM_VERSION) -t $(IMAGE) -f docker/Dockerfile .

viz-image:  ## build the visualisation image (ParaView 6.2, headless) for this machine
	docker build -t iom-cfd-viz:latest -f docker/Dockerfile.viz .

shell: image  ## interactive OpenFOAM shell with the repo at /work
	uv run iomcfd shell

test:  ## unit tests (no OpenFOAM needed)
	uv run pytest -m "not docker"

test-docker: image  ## integration tests that run OpenFOAM in the image
	uv run pytest -m docker

smoke: image  ## 2-case end-to-end foil2d run (~1-2 min)
	uv run iomcfd run foil2d/smoke --force

push:  ## build multi-arch image and push to Artifact Registry (tags: git describe + latest)
	@test -n "$(GCP_PROJECT)" || (echo "fill in cloud/gcp/config.env first" && exit 1)
	docker buildx build --platform linux/amd64,linux/arm64 \
	    --build-arg OPENFOAM_VERSION=$(OPENFOAM_VERSION) \
	    -t $(REMOTE_IMAGE):$(GIT_TAG) -t $(REMOTE_IMAGE):latest \
	    -f docker/Dockerfile --push .
	@echo "pushed $(REMOTE_IMAGE):$(GIT_TAG)"

push-viz:  ## build multi-arch visualisation image and push to Artifact Registry
	@test -n "$(GCP_PROJECT)" || (echo "fill in cloud/gcp/config.env first" && exit 1)
	docker buildx build --platform linux/amd64,linux/arm64 \
	    -t $(REMOTE_IMAGE)-viz:$(GIT_TAG) -t $(REMOTE_IMAGE)-viz:latest \
	    -f docker/Dockerfile.viz --push .

clean-runs:  ## delete all local simulation output (runs/)
	rm -rf runs
