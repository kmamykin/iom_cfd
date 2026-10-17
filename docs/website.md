# The website

A one-page summary of the project, written like a paper (abstract, prior
work, methodology, studies, findings, conclusion), built with
[Quarto](https://quarto.org) from `site/` and published on GitHub Pages:
<https://kmamykin.github.io/iom_cfd/> once Pages is switched on.

The findings logs (`projects/<project>/findings/`) stay the dated record of
every run. The page says where things stand now, and links to them.

## Layout

```
site/
├── index.qmd        the page, written by hand
├── _quarto.yml      Quarto settings (layout, table of contents, numbering, references)
├── styles.scss      the look: fonts, colours (figures.py uses the same palette)
├── references.bib   cited sources
├── data.yaml        which run each data file comes from
├── data/            small CSVs taken from runs (committed); sources.json records where from
├── assets/          pictures and videos that can't be rebuilt online (ParaView renders)
├── figures.py       one function per chart, drawn from data/ into _generated/
├── _generated/      figures and tables (build output, not committed)
└── _site/           the built page (build output, not committed)
```

Charts are drawn during the build from `site/data/`, so the site builds
without `runs/`, and changing a chart doesn't leave a new copy of a picture
in the git history each time. Only renders that need the run's fields
(ParaView) are committed as files, and they are replaced rarely.

## Building

```bash
uv run iomcfd site build             # figures, then quarto render -> site/_site/index.html
uv run iomcfd site build --preview   # serve it locally, rebuild on save
make site / make site-preview        # the same
```

Quarto is used from `PATH` if installed (`brew install --cask quarto`);
otherwise `uvx` runs the PyPI build of the same version
(`iomcfd.site.QUARTO_VERSION`; the first run downloads it).

## Publishing

`.github/workflows/site.yml` builds and deploys the page on every push to
main that changes `site/`, or the code its figures use (the mesh generator,
`projects/foil2d/project.py`). It can also be run by hand from the Actions
tab. Website-only pushes don't rebuild the solver image (`image.yml`).

One-time setup: repository Settings → Pages → Source: **GitHub Actions**.

## Updating it after new findings

The `site-update` skill (`.claude/skills/site-update/`) does this.

1. A run finishes: `iomcfd report`, then the `study-findings` skill writes
   the findings entry. That is unchanged.
2. Decide whether the page changes. It does when the recommendation, a
   number the page quotes, the method, or the data behind a figure changes.
   Most runs don't need a page update.
3. Refresh the data. Point the entry in `site/data.yaml` at the new run,
   then run `uv run iomcfd site export <name>`. A light `gcp fetch` of the
   run is enough for tables. `kind: manual` tables are copied by hand from
   a findings log; keep their `source:` up to date.
4. Edit the affected sections of `site/index.qmd`. Set `date-modified:` and
   add a line to "Revision history".
5. Build, look at it, run `uv run pytest tests/test_site.py`.
6. Commit and push: that publishes it.

## Rules

* Every number on the page comes from a findings log or `site/data/`, or
  is labelled an estimate. Keep the limitations on the page: a polished
  page reads as more certain than the logs do.
* Don't copy other people's images or text; cite and link them in
  `references.bib`. Mark sources not yet checked.
* No cloud details (project ids, bucket names) on the page.
