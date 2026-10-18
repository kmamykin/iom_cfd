---
name: site-update
description: Update the project website (a study's page, site/<study>/index.qmd, published to GitHub Pages) after new findings - refresh its data from the runs, redraw the figures, edit the affected sections, add a revision-history line, then build and check it. Use after a study-findings entry changes a conclusion, a number quoted on the page or the method, or when the user asks to update the website.
argument-hint: [what changed, e.g. foil2d/transient-check run <id>]
---

# Site update

The website (`site/`, docs/website.md) is a curated, current summary of the
project. The findings logs (`projects/<project>/findings/*.md`) stay the
dated record; the page states where things stand now and links to them.
Pushing to main publishes it, so nothing here is committed or pushed unless
the user asks.

## 1. Decide whether the page changes

Read the new findings entry (and, for foil2d, "Where the selection stands"
in findings/fin-profile-selection.md), then the study's page,
`site/<study>/index.qmd` (foil2d fin sections: `site/fin-selection/index.qmd`).
The page changes when one of these does:
* the recommendation or its confidence;
* a number the page quotes (search the page for it);
* the method (projects/foil2d/methodology.md);
* the data behind a figure (a newer run of the same cases).

If none does, stop and say so.

## 2. Refresh the data

* Point the entry in `site/data.yaml` at the new run (`runs:`), or add an
  entry. Then `uv run iomcfd site export <name> ...`. It reads the local
  runs: a light `uv run iomcfd gcp fetch <project>/<study> --run-id ID` is
  enough for tables. Never fetch whole runs.
* `kind: manual` tables are copied by hand from a findings log. Update the
  CSV and its `source:` together.
* New pictures or videos (ParaView renders) go in as `kind: file`. Keep each
  under about 1 MB. Don't copy third-party images; cite and link them.

## 3. Figures

Charts are functions in `site/figures.py`, drawn from `site/data/` only (or
from the project's code, as the mesh is), listed in `make_all()`. Use the
palette at the top of the file. Check every changed figure by eye: build,
then open the SVG or PNG from `site/_generated/`, or view the page.

## 4. Text

Edit only the affected sections of the study's page:
* every number traceable to a findings log or `site/data/`; estimates
  labelled as such; unverified sources marked in `references.bib`;
* keep in step: the status callout, the key-results row, the abstract, the
  studies table, the conclusion and its "why not higher confidence", and the
  front-matter `description` (the study's card on the front page);
* when a conclusion is superseded, say so on the page, not only in the log;
* set `date-modified:` in the front matter to today (UTC), and add a line
  to "Revision history": date, what changed, which runs.

Plain words. Readers are sailors and engineers, not the people who ran it.

## 5. Build and check

```bash
uv run iomcfd site build            # figures, then quarto render; no warnings expected
uv run pytest tests/test_site.py -q  # every data file in the manifest, with a source
uv run iomcfd site build --preview   # optional: serve it and look
```

Look at the changed sections at desktop and phone width (no horizontal
scroll).

## 6. Report

Tell the user what changed on the page and why, and which data files were
refreshed. Commit or push only when asked: a push to main that touches
`site/` deploys the page.
