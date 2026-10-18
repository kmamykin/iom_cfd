"""The website's data (site/data.yaml, site/data/, site/assets/), export and
figures (pure Python, no OpenFOAM, no Quarto)."""

import json
import re

import pytest
import yaml

from iomcfd import site
from iomcfd.config import home

pd = pytest.importorskip("pandas")
pytest.importorskip("matplotlib")

SITE = home() / "site"


def test_every_data_file_is_in_the_manifest_with_a_source():
    entries = site.manifest()
    sources = json.loads((SITE / "data" / "sources.json").read_text())
    expected = {site.output_path(SITE, n, e).relative_to(SITE).as_posix() for n, e in entries.items()}
    present = {p.relative_to(SITE).as_posix() for d in ("data", "assets") for p in (SITE / d).iterdir()
               if p.name != "sources.json"}
    assert present == expected  # nothing missing, nothing left over
    assert set(sources) == set(entries)
    for name, s in sources.items():
        assert s["file"] == site.output_path(SITE, name, entries[name]).relative_to(SITE).as_posix()
        assert s["source"], name


@pytest.fixture
def fake(tmp_path, monkeypatch):
    """A site with a manifest, and a runs directory with one finished run."""
    runs = tmp_path / "runs"
    monkeypatch.setenv("IOMCFD_RUNS", str(runs))
    run = runs / "st" / "20260101-000000"
    (run / "report").mkdir(parents=True)
    pd.DataFrame({"foil": ["a", "a", "b"], "speed": [1.0, 2.0, 1.0], "Cl": [0.1, 0.2, 0.3], "x": 1}).to_csv(
        run / "results.csv", index=False)
    (run / "report" / "pic.png").write_bytes(b"png")
    s = tmp_path / "site"
    (s / "data").mkdir(parents=True)
    (s / "data" / "by-hand.csv").write_text("a\n1\n")
    (s / "data.yaml").write_text(
        "tab: {study: st, runs: [20260101-000000], file: results.csv, where: {speed: 1.0}, columns: [foil, Cl]}\n"
        "pic: {kind: file, study: st, runs: [20260101-000000], file: report/pic.png}\n"
        "by-hand: {kind: manual, source: a findings log}\n")
    return s


def test_export_copies_and_records_sources(fake):
    written = site.export(site=fake)
    assert {p.name for p in written} == {"tab.csv", "pic.png"}
    tab = pd.read_csv(fake / "data" / "tab.csv")
    assert list(tab.columns) == ["run", "foil", "Cl"] and list(tab.foil) == ["a", "b"]
    assert (fake / "assets" / "pic.png").read_bytes() == b"png"
    src = json.loads((fake / "data" / "sources.json").read_text())
    assert src["tab"]["runs"] == ["20260101-000000"] and src["tab"]["study"] == "st"
    assert src["by-hand"] == {"kind": "manual", "file": "data/by-hand.csv", "source": "a findings log"}


def test_export_of_a_run_that_is_not_here_says_how_to_fetch_it(fake):
    (fake / "data.yaml").write_text("tab: {study: st, runs: [20260202-000000], file: results.csv}\n")
    with pytest.raises(FileNotFoundError, match="gcp fetch"):
        site.export(site=fake)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """site/figures.py, and everything its make_all() draws from the committed data."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("site_figures", SITE / "figures.py")
    figs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(figs)
    return figs, figs.make_all(SITE / "data", tmp_path_factory.mktemp("generated"))


def test_figures_build_from_the_committed_data(built):
    figs, out = built
    assert all(p.is_file() and p.stat().st_size > 0 for p in out)
    # the loads are the steady side forces of 0009/80 at 1 m/s (methodology.md: 1.15, 6.69, 8.33 N)
    steady = figs._whole_fin(pd.read_csv(SITE / "data" / "steady-1ms.csv"))
    assert [round(v, 2) for v in figs.loads(steady).values()] == [1.15, 6.69, 8.33]
    assert figs.wagner(15) == pytest.approx(0.958, abs=0.002)  # ~95 % after 15 flow-throughs


def _front_matter(page):
    return yaml.safe_load(re.match(r"---\n(.*?)\n---\n", page.read_text(), re.DOTALL).group(1))


def test_every_study_on_the_front_page_has_a_card(built):
    """The front page lists study pages; each card needs the page's title, description and image."""
    made = {p.name for p in built[1]}
    pages = _front_matter(SITE / "index.qmd")["listing"]["contents"]
    assert pages
    for page in pages:
        meta = _front_matter(SITE / page)
        assert meta.get("title") and meta.get("description"), page
        image = ((SITE / page).parent / meta["image"]).resolve()
        if image.parent == (SITE / "_generated").resolve():
            assert image.name in made, f"{page}: figures.make_all() doesn't make {image.name}"
        else:
            assert image.is_file(), f"{page}: no {meta['image']}"
