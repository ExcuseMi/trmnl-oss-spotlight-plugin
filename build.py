#!/usr/bin/env python3
"""Query Wikidata for popular open-source projects, enrich with Wikipedia intros,
snapshot 100 to projects.json."""
import datetime
import json
import random
import urllib.parse
import urllib.request

ENDPOINT = "https://query.wikidata.org/sparql"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
UA = "trmnl-oss-spotlight/1.0 (https://github.com/ExcuseMi/trmnl-oss-spotlight-plugin; wardje@gmail.com)"

# Pull a popular pool of real software, then sample from it for daily variety.
# Constraints, all required:
#   P31/P279* Q341  -> free/open-source software
#   P31/P279* Q7397 -> is actually software (excludes services, books, protocols)
#   P856            -> has an official website
#   P571            -> has a founding/inception date
#   P18             -> has a screenshot/image (every spotlight gets a visual)
# We also grab the English Wikipedia article title (?wp) to fetch a richer intro.
# Ranked by sitelinks (number of Wikipedia language editions) as a popularity proxy.
# GROUP BY ?item collapses the SPARQL path-multiplication into one row per project.
QUERY = """
SELECT ?item
       (SAMPLE(?name) AS ?nm)
       (SAMPLE(?desc) AS ?ds)
       (SAMPLE(?inception) AS ?inc)
       (SAMPLE(?website) AS ?web)
       (SAMPLE(?im) AS ?img)
       (SAMPLE(?wpname) AS ?wp)
       (SAMPLE(?sl) AS ?sites)
WHERE {
  ?item wdt:P31/wdt:P279* wd:Q341 .
  ?item wdt:P31/wdt:P279* wd:Q7397 .
  ?item wikibase:sitelinks ?sl .
  ?item wdt:P856 ?website .
  ?item wdt:P571 ?inception .
  ?item wdt:P18 ?im .
  ?item rdfs:label ?name . FILTER(LANG(?name)="en")
  ?item schema:description ?desc . FILTER(LANG(?desc)="en")
  OPTIONAL {
    ?article schema:about ?item ;
             schema:isPartOf <https://en.wikipedia.org/> ;
             schema:name ?wpname .
  }
}
GROUP BY ?item
ORDER BY DESC(?sites) LIMIT 250
"""

# Protocols / services / coins that are tagged as software but aren't "tools to learn".
SKIP = {"Bitcoin", "Ethereum", "Monero", "Telegram", "OpenStreetMap", "Litecoin",
        "Dogecoin", "Zcash", "arXiv", "Wikipedia", "Wikimedia Commons", "Bitcoin Cash",
        "Bluesky", "Ripple", "Cardano", "Solana"}

POOL_SIZE = 100
SUMMARY_LIMIT = 460  # chars of Wikipedia intro to keep (trimmed to a sentence)


def _get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def fetch_pool():
    url = ENDPOINT + "?" + urllib.parse.urlencode({"format": "json", "query": QUERY})
    return _get_json(url)["results"]["bindings"]


def fetch_extracts(titles):
    """Return {requested_title: plaintext intro} for English Wikipedia articles."""
    out = {}
    for i in range(0, len(titles), 20):
        batch = titles[i:i + 20]
        params = {
            "action": "query", "format": "json", "prop": "extracts",
            "exintro": "1", "explaintext": "1", "exlimit": "max", "redirects": "1",
            "titles": "|".join(batch),
        }
        try:
            q = _get_json(WIKIPEDIA_API + "?" + urllib.parse.urlencode(params)).get("query", {})
        except Exception:
            continue
        # Map each requested title to its final article via normalization + redirects.
        norm = {x["from"]: x["to"] for x in q.get("normalized", [])}
        redir = {x["from"]: x["to"] for x in q.get("redirects", [])}
        pages = {pg["title"]: (pg.get("extract") or "") for pg in q.get("pages", {}).values()}
        for t in batch:
            final = redir.get(norm.get(t, t), norm.get(t, t))
            ex = pages.get(final, "")
            if ex:
                out[t] = ex
    return out


def summarize(text, limit=SUMMARY_LIMIT):
    """Collapse whitespace and trim to a clean sentence boundary near `limit`."""
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    best = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    if best > limit * 0.5:
        return cut[:best + 1]
    return cut.rsplit(" ", 1)[0].rstrip(",.;:") + "…"


def main():
    seen, pool = set(), []
    for b in fetch_pool():
        name = b["nm"]["value"]
        if name in seen or name in SKIP:
            continue
        seen.add(name)
        image = b.get("img", {}).get("value", "").replace("http://", "https://", 1)
        pool.append({
            "title": name,
            "description": b["ds"]["value"],
            "year": b["inc"]["value"][:4],
            "url": b["web"]["value"],
            "image": image,
            "_wp": b.get("wp", {}).get("value", "") or name,
        })

    # Stable daily rotation: pick deterministically from today's date so the
    # snapshot changes every day (forcing a re-render) but not within a day.
    rng = random.Random(datetime.date.today().toordinal())
    rng.shuffle(pool)
    picks = pool[:POOL_SIZE]

    # Enrich only the picked projects with a Wikipedia intro ("why use it").
    extracts = fetch_extracts([p["_wp"] for p in picks])
    for p in picks:
        summary = summarize(extracts.get(p["_wp"], ""))
        p["summary"] = summary or p["description"]
        del p["_wp"]

    out = {
        "updated": datetime.date.today().isoformat(),
        "count": len(picks),
        "projects": picks,
    }
    with open("projects.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    enriched = sum(1 for p in picks if p["summary"] != p["description"])
    print(f"wrote {len(picks)} projects (pool {len(pool)}, {enriched} with Wikipedia intros)")


if __name__ == "__main__":
    main()
