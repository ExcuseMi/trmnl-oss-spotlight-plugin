#!/usr/bin/env python3
"""Query Wikidata for popular open-source projects, snapshot 100 to projects.json."""
import datetime
import json
import urllib.parse
import urllib.request

ENDPOINT = "https://query.wikidata.org/sparql"
UA = "trmnl-oss-spotlight/1.0 (https://github.com/ExcuseMi/trmnl-oss-spotlight-plugin; wardje@gmail.com)"

# Pull a large popular pool; we sample from it for daily variety.
# Ranked by sitelinks (number of Wikipedia language editions) as a popularity proxy.
QUERY = """
SELECT ?name ?desc ?inception ?website ?img ?sl WHERE {
  ?item wdt:P31/wdt:P279* wd:Q341 .
  ?item wikibase:sitelinks ?sl .
  ?item wdt:P856 ?website .
  ?item wdt:P571 ?inception .
  ?item rdfs:label ?name . FILTER(LANG(?name)="en")
  ?item schema:description ?desc . FILTER(LANG(?desc)="en")
  OPTIONAL { ?item wdt:P18 ?img . }
}
ORDER BY DESC(?sl) LIMIT 400
"""

# Crypto/protocols/services that aren't "tools to learn".
SKIP = {"Bitcoin", "Ethereum", "Monero", "Telegram", "OpenStreetMap", "Litecoin",
        "Dogecoin", "Zcash", "arXiv", "Wikipedia", "Wikimedia Commons", "Bitcoin Cash"}

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
        name = b["name"]["value"]
        if name in seen or name in SKIP:
            continue
        seen.add(name)
        image = b.get("img", {}).get("value", "").replace("http://", "https://", 1)
        pool.append({
            "title": name,
            "description": b["desc"]["value"],
            "year": b["inception"]["value"][:4],
            "url": b["website"]["value"],
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
