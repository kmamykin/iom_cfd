"""One video of several sections side by side in time: each frame stacks
one rendered view (`iomcfd viz`) of each case group at the same value of the
swept parameter, top to bottom in the order given. For comparing sections
along an angle sweep, e.g. the Thistle page's NACA 0006, parallel-sided and
plank boards (site/data.yaml thistle-flow-*):

    uv run python tools/stack_viz_video.py runs/thistle-screen/20261023-125405 boundary_layer \
        --groups Tu1_aoa{}_foilnaca0006mt0556_speed1.5199 Tu1_aoa{}_foilparallelml30mt50mr05ma20_speed1.5199 \
                 Tu1_aoa{}_foilplankmtypical_speed1.5199 \
        --values 0 1 2 4 6 8 --out runs/thistle-screen/20261023-125405/viz/compare_boundary_layer_by_aoa.mp4

Reads <run>/<case>/viz/<view>.png only (render them first); writes the mp4
(and a gif next to it) with iomcfd.viz.study's encoder. Needs ffmpeg.
"""
import argparse
import shutil
from pathlib import Path

from PIL import Image

from iomcfd.viz.study import _encode_sequence


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", type=Path)
    ap.add_argument("view")
    ap.add_argument("--groups", nargs="+", required=True, help="case name patterns, {} = the swept value")
    ap.add_argument("--values", nargs="+", required=True)
    ap.add_argument("--crop", type=float, nargs=2, metavar=("TOP", "BOTTOM"), default=(0.0, 1.0),
                    help="keep this band of each image, as fractions of its height")
    ap.add_argument("--width", type=int, default=1400, help="width of the video [px]")
    ap.add_argument("--fps", type=float, default=0.8)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    tmp = a.out.with_suffix(".stack")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    frames = []
    for i, v in enumerate(a.values):
        ims = []
        for g in a.groups:
            im = Image.open(a.run / g.format(v) / "viz" / f"{a.view}.png").convert("RGB")
            w, h = im.size
            ims.append(im.crop((0, int(a.crop[0] * h), w, int(a.crop[1] * h))))
        w = max(im.size[0] for im in ims)
        sheet = Image.new("RGB", (w, sum(im.size[1] for im in ims)), "white")
        y = 0
        for im in ims:
            sheet.paste(im, (0, y))
            y += im.size[1]
        sheet = sheet.resize((a.width, round(sheet.size[1] * a.width / w)), Image.LANCZOS)
        frames.append(tmp / f"s_{i:04d}.png")
        sheet.save(frames[-1])
    a.out.parent.mkdir(parents=True, exist_ok=True)
    print("\n".join(str(f) for f in _encode_sequence(frames, a.out, a.fps)))
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
