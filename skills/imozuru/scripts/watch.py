#!/usr/bin/env python3
"""List new posts from the map's venues via RSS / Atom, each with its own opening line.

Usage:
    watch.py add   <topic_dir> <url> [name]  … add a place to watch (finds the RSS automatically)
    watch.py list  <topic_dir>               … list the places watched
    watch.py check <topic_dir> [--days N] [--fresh]
                                             … list new posts and keep them in watch/<date-time>.md
                                               a first-time feed only shows the last N days (default 14)
                                               --fresh ignores the seen record and selects by the window alone
                                               places with nothing new still show their latest item, regardless of the window

Files (<topic_dir> = ~/research/<topic>/):
    watch.tsv          kind, name, feed URL, original URL (tab-separated)
    watch-state.json   URLs of posts already seen, per feed
    watch/<date>.md    results of check
"""

import datetime as dt
import email.utils
import html
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0 imozuru-watch"}
ATOM = "{http://www.w3.org/2005/Atom}"
HEAD_CHARS = 120
# Feeds return a few dozen items, so this is plenty
SEEN_LIMIT = 500


class _Redirect308(urllib.request.HTTPRedirectHandler):
    """Copy of fetch.py's: scripts run with -I can't import each other."""

    http_error_308 = urllib.request.HTTPRedirectHandler.http_error_302

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, 307 if code == 308 else code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_Redirect308)


def fetch(url: str) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers=UA)
    with _OPENER.open(req, timeout=60) as res:
        return res.read(5_000_000), res.headers.get("Content-Type", "")


def known_feed(url: str) -> tuple[str, str] | None:
    rules = [
        (r"^https?://qiita\.com/tags/([^/?#]+)", "qiita-tag", "https://qiita.com/tags/{0}/feed"),
        (r"^https?://zenn\.dev/topics/([^/?#]+)", "zenn-topic", "https://zenn.dev/topics/{0}/feed"),
        (r"^https?://zenn\.dev/([^/?#]+)/?$", "zenn-user", "https://zenn.dev/{0}/feed"),
        (r"^https?://note\.com/([^/?#]+)/?$", "note-user", "https://note.com/{0}/rss"),
        (r"^https?://qiita\.com/([^/?#]+)/?$", "qiita-user", "https://qiita.com/{0}/feed"),
        (r"^https?://(?:www\.|old\.)?reddit\.com/r/([^/?#]+)", "reddit", "https://www.reddit.com/r/{0}/.rss"),
    ]
    for pat, kind, tmpl in rules:
        m = re.match(pat, url)
        if m:
            return kind, tmpl.format(*m.groups())
    if "export.arxiv.org/api/query" in url:
        return "arxiv", url
    return None


def discover(url: str) -> tuple[str, str]:
    """Return (kind, feed URL) from a known URL pattern, the URL itself, or the page's <link rel=alternate>."""
    hit = known_feed(url)
    if hit:
        return hit
    body, ctype = fetch(url)
    if "xml" in ctype or body.lstrip()[:5] in (b"<?xml", b"<rss ", b"<feed"):
        return "feed", url
    text = body.decode("utf-8", errors="replace")
    for m in re.finditer(r"<link\b[^>]*>", text, re.I):
        tag = m.group(0)
        if re.search(r'type=["\']application/(rss|atom)\+xml', tag, re.I):
            href = re.search(r'href=["\']([^"\']+)', tag)
            if href:
                feed = html.unescape(href.group(1))
                if feed.startswith("/"):
                    root = re.match(r"^https?://[^/]+", url).group(0)
                    feed = root + feed
                kind = "youtube" if "youtube.com/feeds" in feed else "site"
                return kind, feed
    raise SystemExit(f"No RSS found: {url} (the page doesn't advertise one; X and pixiv don't publish RSS at all)")


def plain(s: str | None) -> str:
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"\s+", " ", s).strip()


def parse_date(s: str | None) -> dt.datetime | None:
    if not s:
        return None
    s = s.strip()
    try:
        d = email.utils.parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def items(feed_bytes: bytes) -> list[dict]:
    """Parse RSS 2.0 and Atom items.

    Rejects DOCTYPE/ENTITY (XXE, billion laughs) without needing defusedxml. Only the prolog is
    checked, since CDATA bodies may legitimately contain "<!DOCTYPE html>".
    """
    root_at = re.search(rb"<(rss|feed|rdf:RDF)\b", feed_bytes)
    prolog = feed_bytes[: root_at.start()] if root_at else feed_bytes
    if re.search(rb"<!(DOCTYPE|ENTITY)", prolog, re.I):
        raise ValueError("feeds containing DOCTYPE or ENTITY are not read")
    root = ET.fromstring(feed_bytes)
    out = []
    for it in root.iter("item"):
        out.append({
            "title": plain(it.findtext("title")),
            "link": (it.findtext("link") or "").strip(),
            "date": parse_date(it.findtext("pubDate") or it.findtext("{http://purl.org/dc/elements/1.1/}date")),
            "head": plain(it.findtext("description")),
        })
    for en in root.iter(f"{ATOM}entry"):
        link = ""
        for ln in en.findall(f"{ATOM}link"):
            if ln.get("rel", "alternate") == "alternate":
                link = ln.get("href", "")
                break
        head = en.findtext(f"{ATOM}summary") or en.findtext(f"{ATOM}content") \
            or en.findtext("{http://search.yahoo.com/mrss/}group/{http://search.yahoo.com/mrss/}description")
        out.append({
            "title": plain(en.findtext(f"{ATOM}title")),
            "link": link,
            "date": parse_date(en.findtext(f"{ATOM}published") or en.findtext(f"{ATOM}updated")),
            "head": plain(head),
        })
    return out


def load_watch(topic: Path) -> list[list[str]]:
    p = topic / "watch.tsv"
    if not p.exists():
        return []
    return [ln.split("\t") for ln in p.read_text(encoding="utf-8").splitlines()
            if ln and not ln.startswith("#")]


def cmd_add(topic: Path, url: str, name: str | None) -> int:
    # One-line errors, not tracebacks, so a batch of adds keeps going
    try:
        kind, feed = discover(url)
        found = items(fetch(feed)[0])
    except SystemExit as e:
        print(f"Couldn't add: {e}")
        return 1
    except Exception as e:
        print(f"Couldn't add: {url} ({type(e).__name__}: {e})")
        return 1
    for row in load_watch(topic):
        if row[2] == feed:
            print(f"Already watching: {row[1]} {feed}")
            return 0
    if name:
        label = name
    elif kind == "arxiv":
        q = re.search(r"search_query=([^&]+)", url)
        label = "arxiv " + (urllib.parse.unquote(q.group(1)) if q else "query")
    elif kind == "feed" and found:
        label = found[0]["title"][:30]
    else:
        label = re.sub(r"^https?://(www\.)?", "", url).rstrip("/")[:40]
    topic.mkdir(parents=True, exist_ok=True)
    p = topic / "watch.tsv"
    if not p.exists():
        p.write_text("# kind\tname\tfeed\toriginal URL\n", encoding="utf-8")
    with p.open("a", encoding="utf-8") as f:
        f.write(f"{kind}\t{label}\t{feed}\t{url}\n")
    print(f"Added: {kind}\t{label}\t{feed} ({len(found)} items now)")
    return 0


def cmd_check(topic: Path, days: int, fresh: bool) -> None:
    """List posts not seen before; a first-time feed (or fresh) only shows the last `days`.

    Posts outside the first window are marked seen too, hence `fresh` for re-listing with a wider window.
    """
    rows = load_watch(topic)
    if not rows:
        raise SystemExit(f"Nothing to watch: {topic}/watch.tsv (add with watch.py add)")
    state_p = topic / "watch-state.json"
    state = json.loads(state_p.read_text(encoding="utf-8")) if state_p.exists() else {}
    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(days=days)
    lines = [f"# New posts {now.astimezone():%Y-%m-%d %H:%M}", ""]
    quiet: list[str] = []
    total = 0
    for kind, label, feed, *_ in rows:
        try:
            got = items(fetch(feed)[0])
        except Exception as e:
            lines += [f"## {label} ({kind})", f"- Couldn't fetch: {type(e).__name__}: {e}", ""]
            continue
        seen = set() if fresh else set(state.get(feed, []))
        first = fresh or feed not in state
        new = [i for i in got if i["link"] and i["link"] not in seen
               and (not first or (i["date"] and i["date"] >= cutoff))]
        new.sort(key=lambda i: i["date"] or now, reverse=True)
        state[feed] = ([i["link"] for i in got] + list(set(state.get(feed, [])) - {i["link"] for i in got}))[:SEEN_LIMIT]
        if not new:
            # Still show the latest item, so a release just outside the window isn't missed
            dated = [i for i in got if i["date"]]
            if dated:
                last = max(dated, key=lambda i: i["date"])
                quiet.append(f"- {label} ({kind}) latest {last['date'].astimezone():%Y-%m-%d} [{last['title']}]({last['link']})")
            else:
                quiet.append(f"- {label} ({kind}) no posts")
            continue
        total += len(new)
        lines.append(f"## {label} ({kind}){', last ' + str(days) + ' days' if first else ''}")
        for i in new:
            day = i["date"].astimezone().strftime("%Y-%m-%d") if i["date"] else "no date"
            lines.append(f"- {day} [{i['title']}]({i['link']})")
            if i["head"]:
                lines.append(f"  > {i['head'][:HEAD_CHARS]}{'…' if len(i['head']) > HEAD_CHARS else ''}")
        lines.append("")
    if total == 0:
        lines += ["Nothing new", ""]
    if quiet:
        lines += ["## Places with nothing new (latest item, regardless of the window)", *quiet, ""]
    state_p.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    out = topic / "watch" / f"{now.astimezone():%Y-%m-%d-%H%M%S}.md"
    n = 2
    while out.exists():
        out = out.with_name(f"{now.astimezone():%Y-%m-%d-%H%M%S}-{n}.md")
        n += 1
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\n→ {out} ({total} new, {len(rows)} watched)")


def main() -> int:
    args = sys.argv[1:]
    days = 14
    fresh = "--fresh" in args
    if fresh:
        args.remove("--fresh")
    if "--days" in args:
        i = args.index("--days")
        days = int(args[i + 1])
        del args[i:i + 2]
    if len(args) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    cmd, topic = args[0], Path(args[1]).expanduser()
    if cmd == "add" and len(args) >= 3:
        return cmd_add(topic, args[2], args[3] if len(args) > 3 else None)
    elif cmd == "list":
        for row in load_watch(topic):
            print("\t".join(row))
    elif cmd == "check":
        cmd_check(topic, days, fresh)
    else:
        print(__doc__, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    # Don't crash printing characters the console encoding lacks (e.g. cp932)
    sys.stdout.reconfigure(errors="replace")
    sys.exit(main())
