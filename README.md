# TRMNL OSS Spotlight

A TRMNL plugin that spotlights a different **open-source project** every day — from
the Linux kernel to terminal tools to brand-new AI projects. The goal is discovery:
learn about a tool you've never tried, or finally read up on one you've only heard of.

Each project shows its **name, description, founding year, website, and a screenshot**.

## Where the data comes from

The datasource is **[Wikidata](https://www.wikidata.org)** — community-curated, structured,
and not tied to GitHub, so it covers projects that live anywhere (GNU, BSDs, LaTeX, GIMP, …).
Fields map almost 1:1:

| Plugin field | Wikidata property |
|---|---|
| Title | `rdfs:label` |
| Description | `schema:description` |
| Founding year | `P571` (inception) — *true* historical dates |
| Website | `P856` (official website) |
| Screenshot | `P18` (image) |

Popularity ranking uses `wikibase:sitelinks` (number of Wikipedia language editions).
The list **evolves on its own** as Wikidata editors add projects — nothing to maintain.

## How it works

```
Wikidata SPARQL ──(daily GitHub Action)──> projects.json ──(TRMNL polling)──> device
```

- **`build.py`** queries Wikidata, filters noise, snapshots 100 projects to `projects.json`.
- **`.github/workflows/snapshot.yml`** runs `build.py` daily and commits the result.
- **TRMNL** polls the raw `projects.json` URL; **`transform.js`** shuffles and exposes up
  to 4 projects (mashup-ready — one per slot). A `timestamp` in the payload keeps the
  plugin active so it rotates on each refresh.

This static-snapshot design means Wikidata is queried **once per day total**, not once per
device — friendly to the public query service.

## Develop

```bash
cd plugin
trmnlp serve          # local dev server at http://127.0.0.1:4567
trmnlp build          # render static HTML to plugin/_build/
```

## Test

```bash
cd test/transform
npm test              # runs transform.js against test/transform/data/sample.json
```

## Publish

```bash
cd plugin
trmnlp login
trmnlp push
```
