#!/usr/bin/env python3
"""Follow a paper's citations backward and forward, or an author's works, via OpenAlex.

Free for 1,000 calls a day; over the limit it just stops. No API key needed.

Usage:
    chain.py find  <DOI or title>          … identify a paper and print its ID (5 candidates for a title)
    chain.py refs  <ID or DOI> [-n 20]     … backward: works the paper cites
    chain.py cites <ID or DOI> [-n 20]     … forward: works citing the paper (most cited first)
    chain.py author <author name> [-n 20]  … by author: that person's papers (most cited first)
Output: one work per line, tab-separated (year, citation count, ID, title, DOI, free PDF)
"""

import json
import sys
import urllib.parse
import urllib.request

API = "https://api.openalex.org"
FIELDS = "id,display_name,publication_year,cited_by_count,doi,best_oa_location"


def get(path: str, **params) -> dict:
    url = f"{API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "imozuru (mailto omitted)"})
    with urllib.request.urlopen(req, timeout=60) as res:
        return json.load(res)


def search_title(key: str) -> list[dict]:
    """Top 5 title matches, most cited first.

    Full-text search ranks explainers above the paper itself, so search titles only.
    Registered titles may lack the subtitle, so on no hits retry with the first 3 words.
    """
    words = key.replace(",", " ").replace(":", " ").split()
    for terms in (words, words[:3]):
        hits = get("/works", filter="title.search:" + " ".join(terms),
                   sort="cited_by_count:desc", **{"per-page": 5}, select=FIELDS)["results"]
        if hits:
            return hits
    return []


def resolve(key: str) -> dict:
    """Resolve a DOI, OpenAlex ID, or title (most cited match) to one work."""
    if key.startswith("W") or "openalex.org/" in key:
        return get(f"/works/{key.rsplit('/', 1)[-1]}", select=FIELDS)
    if key.startswith("10.") or "doi.org/" in key:
        doi = key.split("doi.org/")[-1]
        return get(f"/works/doi:{doi}", select=FIELDS)
    hits = search_title(key)
    if not hits:
        raise SystemExit(f"Not found: {key}")
    return hits[0]


def row(w: dict) -> str:
    oa = (w.get("best_oa_location") or {}).get("pdf_url") or ""
    wid = (w.get("id") or "").rsplit("/", 1)[-1]
    return "\t".join(str(x) for x in (
        w.get("publication_year"), w.get("cited_by_count"), wid,
        (w.get("display_name") or "")[:120], w.get("doi") or "", oa))


def main() -> int:
    args = sys.argv[1:]
    n = 20
    if "-n" in args:
        i = args.index("-n")
        n = int(args[i + 1])
        del args[i:i + 2]
    if len(args) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    cmd, key = args[0], " ".join(args[1:])

    if cmd == "find":
        hits = [resolve(key)] if key.startswith(("W", "10.")) or "/" in key else search_title(key)
        if not hits:
            print(f"No candidates: {key} (try the DOI, or fewer title words)")
        for w in hits:
            print(row(w))
    elif cmd in ("refs", "cites"):
        wid = resolve(key)["id"].rsplit("/", 1)[-1]
        flt = f"cited_by:{wid}" if cmd == "refs" else f"cites:{wid}"
        res = get("/works", filter=flt, sort="cited_by_count:desc",
                  **{"per-page": n}, select=FIELDS)
        print(f"# {cmd} {wid} top {len(res['results'])} of {res['meta']['count']}")
        for w in res["results"]:
            print(row(w))
    elif cmd == "author":
        hits = get("/authors", search=key, **{"per-page": 1})["results"]
        if not hits:
            raise SystemExit(f"Author not found: {key}")
        a = hits[0]
        aid = a["id"].rsplit("/", 1)[-1]
        inst = ", ".join(i["display_name"] for i in a.get("last_known_institutions") or [])
        print(f"# author {a['display_name']} {aid} {inst} {a.get('works_count')} works")
        res = get("/works", filter=f"author.id:{aid}", sort="cited_by_count:desc",
                  **{"per-page": n}, select=FIELDS)
        for w in res["results"]:
            print(row(w))
    else:
        print(__doc__, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
