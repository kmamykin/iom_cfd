"""Montages: case images side by side in a labelled grid (matplotlib, no
ParaView), one per highlight and view."""

from __future__ import annotations

from pathlib import Path


def montage(grid: list[list[Path | None]], col_labels: list[str], row_labels: list[str], title: str,
            out: Path, panel_width: float = 8.0) -> Path | None:
    """Images in rows x columns; missing images leave the panel empty.
    Returns `out`, or None if the grid holds no image."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    imgs = [[plt.imread(p) if p is not None and Path(p).is_file() else None for p in row] for row in grid]
    shapes = [im.shape for row in imgs for im in row if im is not None]
    if not shapes:
        return None
    aspect = max(h / w for h, w, *_ in shapes)
    nr, nc = len(imgs), max(len(r) for r in imgs)
    # exact geometry in inches (tight_layout leaves slack around fixed-aspect images)
    w, h = panel_width, panel_width * aspect
    left = 0.5 if any(row_labels) else 0.1
    head, ts, gap, foot = 0.2 + 0.25 * (title.count("\n") + 1), 0.4, 0.15, 0.1
    W, H = left + nc * w + (nc - 1) * gap + 0.1, head + nr * (ts + h) + foot
    fig, axs = plt.subplots(nr, nc, squeeze=False, figsize=(W, H))
    fig.subplots_adjust(left=left / W, right=1 - 0.1 / W, top=1 - (head + ts) / H, bottom=foot / H,
                        wspace=gap / w, hspace=ts / h)
    for i, row in enumerate(imgs):
        for j in range(nc):
            ax = axs[i, j]
            ax.set_xticks([])
            ax.set_yticks([])
            for s in ax.spines.values():
                s.set_visible(False)
            im = row[j] if j < len(row) else None
            if im is not None:
                ax.imshow(im)
            else:  # a blank panel of the same shape keeps the grid regular
                ax.imshow(np.ones((round(aspect * 1000), 1000, 3)))
                ax.text(0.5, 0.5, "not rendered", ha="center", va="center", color="0.5", transform=ax.transAxes)
            if i == 0 and col_labels[j]:
                ax.set_title(col_labels[j], fontsize=12, fontweight="bold")
            if j == 0 and row_labels[i]:
                ax.set_ylabel(row_labels[i], fontsize=11, fontweight="bold")
    fig.suptitle(title, fontsize=13, x=0.1 / W, y=1 - 0.1 / H, ha="left", va="top")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=100)
    plt.close(fig)
    return out
