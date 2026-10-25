"""One video of several sections side by side in time: each frame stacks
one rendered view (`iomcfd viz`) of each case group at the same value of the
swept parameter, top to bottom in the order given, under a header that names
the quantity and the flow direction, with the renderer's own colour bar, and
above each render a label with the section, its C_l and C_d and whether the
case converged. For the Thistle page's NACA 0006, parallel-sided and plank
boards (site/data.yaml thistle-flow-*):

    uv run python tools/stack_viz_video.py runs/thistle-screen/20261023-125405 boundary_layer \
        --groups Tu1_aoa{}_foilnaca0006mt0556_speed1.5199 Tu1_aoa{}_foilparallelml30mt50mr05ma20_speed1.5199 \
                 Tu1_aoa{}_foilplankmtypical_speed1.5199 \
        --names "NACA 0006" "parallel-sided l30-t50" "plank" --values 0 1 2 4 6 8 \
        --crop 0.09 0.819 --legend-box 1060 420 1720 505 --legend-at header \
        --title "Streamwise velocity U_s/U (signed)" --note "..." --poster 8 \
        --out runs/thistle-screen/20261023-125405/viz/compare_boundary_layer_by_aoa.mp4

Reads <run>/<case>/viz/<view>.png and <run>/<case>/result.json only (render
first); writes the mp4, a gif next to it and, with --poster, <out>.poster.png
(that value's frame; --no-video writes only that still). The crop removes each render's own title and colour
bar from the stacked rows; the colour bar is shown once, cut unchanged (pixel
box --legend-box) from the first render and placed in the header or in a
column on the right. Needs ffmpeg.
"""
import argparse
import json
import shutil
from pathlib import Path

from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont

from iomcfd.viz.study import _encode_sequence

PAPER, INK, MUTED, WARN = (251, 250, 246), (29, 35, 42), (107, 116, 128), (181, 69, 43)


def _font(size: int, bold: bool = False):
    path = font_manager.findfont(font_manager.FontProperties(family="DejaVu Sans", weight="bold" if bold else "normal"))
    return ImageFont.truetype(path, size)


def _header(width: int, value: str, subtitle: str, title: str, note: str, legend: Image.Image | None) -> Image.Image:
    lh = legend.size[1] + 12 if legend is not None else 0
    img = Image.new("RGB", (width, 196 + lh), PAPER)
    d = ImageDraw.Draw(img)
    d.text((24, 12), value, font=_font(46, True), fill=INK)
    d.text((24, 70), subtitle, font=_font(26), fill=MUTED)
    d.text((24, 110), title, font=_font(28, True), fill=INK)
    for k, line in enumerate(note.replace("\\n", "\n").split("\n")):
        d.text((24, 148 + 26 * k), line, font=_font(22), fill=MUTED)
    ax = width - 220  # flow direction
    d.line([(ax, 40), (ax + 150, 40)], fill=INK, width=5)
    d.polygon([(ax + 170, 40), (ax + 145, 26), (ax + 145, 54)], fill=INK)
    d.text((ax + 85, 58), "flow", font=_font(24, True), fill=INK, anchor="ma")
    if legend is not None:
        img.paste(legend, (24, 196))
    return img


def _label(width: int, name: str, res: dict) -> Image.Image:
    img = Image.new("RGB", (width, 100), PAPER)
    d = ImageDraw.Draw(img)
    m = res.get("metrics", {})
    d.text((24, 10), name, font=_font(34, True), fill=INK)
    x = 24 + d.textlength(name, font=_font(34, True)) + 28
    d.text((x, 16), f"C_l {m.get('Cl', float('nan')):.3f}   C_d {m.get('Cd', float('nan')):.4f}", font=_font(28), fill=INK)
    if res.get("status") != "ok":
        d.text((24, 56), "NOT CONVERGED: solver oscillates; illustrative only", font=_font(26, True), fill=WARN)
    else:
        d.text((24, 56), "converged steady solution", font=_font(24), fill=MUTED)
    return img


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", type=Path)
    ap.add_argument("view")
    ap.add_argument("--groups", nargs="+", required=True, help="case name patterns, {} = the swept value")
    ap.add_argument("--names", nargs="+", required=True, help="a display name per group")
    ap.add_argument("--values", nargs="+", required=True)
    ap.add_argument("--title", required=True, help="the quantity shown")
    ap.add_argument("--note", default="", help="how to read the colours (\\n for a new line)")
    ap.add_argument("--subtitle", default="3 knots, Tu 1 %, steady solutions: one per angle, not a time history")
    ap.add_argument("--crop", type=float, nargs=2, metavar=("TOP", "BOTTOM"), default=(0.0, 1.0),
                    help="keep this band of each render, as fractions of its height")
    ap.add_argument("--crop-x", type=float, nargs=2, metavar=("LEFT", "RIGHT"), default=(0.0, 1.0))
    ap.add_argument("--legend-box", type=int, nargs=4, metavar=("X0", "Y0", "X1", "Y1"),
                    help="pixel box of the renderer's colour bar, cut from the first render")
    ap.add_argument("--legend-at", choices=["header", "right"], default="header")
    ap.add_argument("--legend-scale", type=float, default=1.5)
    ap.add_argument("--width", type=int, default=1200, help="width of the video [px]")
    ap.add_argument("--fps", type=float, default=0.7)
    ap.add_argument("--poster", help="also write this value's frame as <out>.poster.png")
    ap.add_argument("--no-video", action="store_true", help="only the --poster frame (a still)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    assert len(a.names) == len(a.groups)
    W = a.width
    legend = None
    if a.legend_box:
        first = a.run / a.groups[0].format(a.values[0]) / "viz" / f"{a.view}.png"
        legend = Image.open(first).convert("RGB").crop(tuple(a.legend_box))
        legend = legend.resize((round(legend.size[0] * a.legend_scale), round(legend.size[1] * a.legend_scale)),
                               Image.LANCZOS)
    side = legend.size[0] + 24 if legend is not None and a.legend_at == "right" else 0
    tmp = a.out.with_suffix(".stack")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    frames = []
    for i, v in enumerate(a.values):
        rows = []
        for g, name in zip(a.groups, a.names):
            case = a.run / g.format(v)
            res = json.loads((case / "result.json").read_text())
            im = Image.open(case / "viz" / f"{a.view}.png").convert("RGB")
            w, h = im.size
            im = im.crop((int(a.crop_x[0] * w), int(a.crop[0] * h), int(a.crop_x[1] * w), int(a.crop[1] * h)))
            im = im.resize((W - side, round(im.size[1] * (W - side) / im.size[0])), Image.LANCZOS)
            rows += [_label(W - side, name, res), im]
        head = _header(W, f"Section angle α_n = {v}°", a.subtitle, a.title, a.note,
                       legend if a.legend_at == "header" else None)
        body_h = sum(r.size[1] for r in rows) + 6 * len(a.groups)
        sheet = Image.new("RGB", (W, head.size[1] + body_h), PAPER)
        sheet.paste(head, (0, 0))
        y = head.size[1]
        for j, r in enumerate(rows):
            sheet.paste(r, (0, y))
            y += r.size[1] + (6 if j % 2 == 1 else 0)
        if side:
            sheet.paste(legend, (W - side + 12, head.size[1] + (body_h - legend.size[1]) // 2))
        frames.append(tmp / f"s_{i:04d}.png")
        sheet.save(frames[-1])
        if a.poster is not None and str(v) == str(a.poster):
            sheet.save(a.out.with_suffix(".poster.png"))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    if not a.no_video:
        print("\n".join(str(f) for f in _encode_sequence(frames, a.out, a.fps)))
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
