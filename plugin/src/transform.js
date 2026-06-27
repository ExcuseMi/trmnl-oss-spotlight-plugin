// OSS Spotlight — pick projects to feature from the daily Wikidata snapshot.
//
// The polling URL (projects.json) is rewritten daily by the GitHub Action.
// We shuffle the pool on every render and expose up to 4 projects so the
// plugin is mashup-ready (one project per mashup slot). A `timestamp` is
// included in the payload so the rendered output always differs between
// refreshes — this keeps the plugin "active" and lets it rotate projects
// on each refresh instead of being skipped by lazy refresh.
function transform(input) {
  input = input || {};
  // TRMNL exposes the polling body fields directly on `input`
  // (input.projects, input.updated). Fall back to input.data only if a
  // wrapper is ever present.
  var data = (input.projects || input.updated) ? input : (input.data || input);
  var list = Array.isArray(data.projects)
    ? data.projects
    : (Array.isArray(data) ? data : []);

  function domainOf(url) {
    return (url || "")
      .replace(/^https?:\/\//, "")
      .replace(/^www\./, "")
      .replace(/\/.*$/, "");
  }

  // Fisher–Yates shuffle on a copy so each render features different projects.
  var pool = list.slice();
  for (var i = pool.length - 1; i > 0; i--) {
    var j = Math.floor(Math.random() * (i + 1));
    var tmp = pool[i]; pool[i] = pool[j]; pool[j] = tmp;
  }

  var items = pool.slice(0, 4).map(function (p) {
    p = p || {};
    return {
      title: p.title || "",
      description: p.description || "",
      year: p.year || "",
      url: p.url || "",
      domain: domainOf(p.url),
      image: p.image || ""
    };
  });

  return {
    items: items,
    updated: data.updated || "",
    pool_size: list.length,
    timestamp: Date.now()
  };
}
