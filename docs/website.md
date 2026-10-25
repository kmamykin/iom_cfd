# The website

A front page with a card for each published study, and a page per study
written like a paper (abstract, prior work, methodology, results,
conclusion). Built with [Quarto](https://quarto.org) from `site/` and
published on GitHub Pages: <https://kmamykin.github.io/iom_cfd/>.

The findings logs (`projects/<project>/findings/`) stay the dated record of
every run. A study's page says where things stand now, and links to them.

## Layout

```
site/
├── index.qmd        the front page: a card per published study, in order
├── fin-selection/
│   └── index.qmd    a study's page, written by hand (which fin section; foil2d)
├── privacy/
│   └── index.qmd    what Google Analytics collects (the cookie banner links to it)
├── _quarto.yml      Quarto settings (navbar, footer; for study pages: contents, numbering, references)
├── _quarto-publish.yml  the published site only: Google Analytics, cookie consent
├── styles.scss      the look: fonts, colours, cards (figures.py uses the same palette)
├── references.bib   cited sources
├── data.yaml        which run each data file comes from
├── data/            small CSVs taken from runs (committed); sources.json records where from
├── assets/          pictures and videos that can't be rebuilt online (ParaView renders)
├── figures.py       one function per chart, drawn from data/ and assets/ into _generated/
├── _generated/      figures, tables and card images (build output, not committed)
└── _site/           the built site (build output, not committed)
```

Study pages share `data/`, `assets/`, `_generated/` and `references.bib`,
and refer to them one level up (`../assets/...`).

Charts are drawn during the build from `site/data/`, so the site builds
without `runs/`, and changing a chart doesn't leave a new copy of a picture
in the git history each time. Only renders that need the run's fields
(ParaView) are committed as files, and they are replaced rarely.

## Building

```bash
uv run iomcfd site build             # figures, then quarto render -> site/_site/
uv run iomcfd site build --preview   # serve it locally, rebuild on save
make site / make site-preview        # the same
```

Local builds leave out Google Analytics and the cookie banner; add
`QUARTO_PROFILE=publish` to build exactly what is published.

Quarto is used from `PATH` if installed (`brew install --cask quarto`);
otherwise `uvx` runs the PyPI build of the same version
(`iomcfd.site.QUARTO_VERSION`; the first run downloads it).

## Publishing

`.github/workflows/site.yml` builds and deploys the site on every push to
main that changes `site/`, or the code its figures use (the mesh generator,
`projects/foil2d/project.py`). It can also be run by hand from the Actions
tab. Website-only pushes don't rebuild the solver image (`image.yml`).

One-time setup: repository Settings → Pages → Source: **GitHub Actions**.

## Analytics

The published site counts visits with Google Analytics (GA4), set in
`site/_quarto-publish.yml`, which the workflow turns on with
`QUARTO_PROFILE=publish`. Visitors opt in: Quarto's cookie-consent banner
holds back every script marked `cookie-consent="tracking"` until they
accept, and "Cookie preferences" in the footer changes the choice. The GA
tags are written by hand rather than with Quarto's `google-analytics:` key,
which loads gtag.js from Google before consent;
`tests/test_site.py` checks they stay gated. `site/privacy/` says what is
collected; keep it in step if the analytics change. The banner's wording is
the consent library's own (it mentions ads; Quarto can't change it).

## Publishing a study

A study's page is `site/<study>/index.qmd`, at
`kmamykin.github.io/iom_cfd/<study>/`. Its card on the front page comes from
its front matter:

* `title`: the card's title (a question works well);
* `description`: a sentence or two, the question and the answer so far. It
  is also the text of link previews; the page itself doesn't show it;
* `image`: a picture at 3:1, for example a crop of a render made by a
  function in `figures.py` (`card_image` for fin-selection).

Every `site/*/index.qmd` is built, but only pages listed under `contents:`
in `site/index.qmd` get a card, in that order (`privacy/` is the one page
that isn't a study). A page that isn't listed can
still be reached by its address, so keep unfinished pages out of `site/`.

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
4. Edit the affected sections of the study's page. Set `date-modified:` and
   add a line to "Revision history". If the answer changes, change the
   page's `description` too: it is the card on the front page.
5. Build, look at it, run `uv run pytest tests/test_site.py`.
6. Commit and push: that publishes it.

## Rules

* Every number on a page comes from a findings log or `site/data/`, or
  is labelled an estimate. Keep the limitations on the page: a polished
  page reads as more certain than the logs do.
* Don't copy other people's images or text; cite and link them in
  `references.bib`. Mark sources not yet checked.
* No cloud details (project ids, bucket names) on the page.
