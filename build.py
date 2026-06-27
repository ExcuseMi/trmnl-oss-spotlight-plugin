#!/usr/bin/env python3
"""Query Wikidata for popular open-source projects, snapshot 100 to projects.json."""
import datetime
import json
import urllib.parse
import urllib.request

ENDPOINT = "https://query.wikidata.org/sparql"
UA = "trmnl-oss-spotlight/1.0 (https://github.com/ExcuseMi/trmnl-oss-spotlight-plugin; wardje@gmail.com)"

# Pull a popular pool of real software, then sample from it for daily variety.
# Constraints, all required:
#   P31/P279* Q341  -> free/open-source software
#   P31/P279* Q7397 -> is actually software (excludes services, books, protocols)
#   P856            -> has an official website
#   P571            -> has a founding/inception date
#   P18             -> has a screenshot/image (every spotlight gets a visual)
# Ranked by sitelinks (number of Wikipedia language editions) as a popularity proxy.
# GROUP BY ?item collapses the SPARQL path-multiplication into one row per project.
QUERY = """
SELECT ?item
       (SAMPLE(?name) AS ?nm)
       (SAMPLE(?desc) AS ?ds)
       (SAMPLE(?inception) AS ?inc)
       (SAMPLE(?website) AS ?web)
       (SAMPLE(?im) AS ?img)
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
}
GROUP BY ?item
ORDER BY DESC(?sites) LIMIT 250
"""

# Protocols / services / coins that are tagged as software but aren't "tools to learn".
SKIP = {"Bitcoin", "Ethereum", "Monero", "Telegram", "OpenStreetMap", "Litecoin",
        "Dogecoin", "Zcash", "arXiv", "Wikipedia", "Wikimedia Commons", "Bitcoin Cash",
        "Bluesky", "Ripple", "Cardano", "Solana"}

POOL_SIZE = 100


def fetch():
    url = ENDPOINT + "?" + urllib.parse.urlencode({"format": "json", "query": QUERY})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["results"]["bindings"]


def main():
    rows = fetch()
    seen, pool = set(), []
    for b in rows:
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
        })

    # Stable daily rotation: pick deterministically from today's date so the
    # snapshot changes every day (forcing a re-render) but not within a day.
    rng = __import__("random").Random(datetime.date.today().toordinal())
    rng.shuffle(pool)
    picks = pool[:POOL_SIZE]

    out = {
        "updated": datetime.date.today().isoformat(),
        "count": len(picks),
        "projects": picks,
    }
    with open("projects.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"wrote {len(picks)} projects (pool {len(pool)})")


if __name__ == "__main__":
    main()
