"""Locations. Everything is relative to IOMCFD_HOME (the repository root)."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_IMAGE = "iom-cfd:latest"
DEFAULT_VIZ_IMAGE = "iom-cfd-viz:latest"


def home() -> Path:
    env = os.environ.get("IOMCFD_HOME")
    if env:
        return Path(env).resolve()
    # src/iomcfd/config.py -> repository root
    return Path(__file__).resolve().parents[2]


def projects_dir() -> Path:
    return home() / "projects"


def geometry_dir() -> Path:
    env = os.environ.get("IOMCFD_GEOMETRY")
    return Path(env) if env else home() / "geometry"


def runs_dir() -> Path:
    env = os.environ.get("IOMCFD_RUNS")
    return Path(env).resolve() if env else home() / "runs"


def in_container() -> bool:
    return bool(os.environ.get("IOMCFD_IN_CONTAINER") or os.environ.get("WM_PROJECT_DIR"))


def image() -> str:
    return os.environ.get("IOMCFD_IMAGE", DEFAULT_IMAGE)


def viz_image() -> str:
    return os.environ.get("IOMCFD_VIZ_IMAGE", DEFAULT_VIZ_IMAGE)


def in_viz_container() -> bool:
    return bool(os.environ.get("IOMCFD_VIZ_CONTAINER"))
