#!/usr/bin/env python3
"""Watch the "venues" on the map and list what has appeared since last time (Ellis's monitoring).

Pulls RSS / Atom instead of searching. Search results fluctuate and cost money, but a feed
returns "what is new at that place" as-is. Instead of searching the same Qiita, Zenn, and X every time,
this is a tool for watching the places a dig turned up.

New posts get no summary. Instead, the opening line of the original from the feed is shown as-is
(only a cue for choosing, with no agent wording in between).

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
# Length of the opening line. Enough to choose by, short enough not to stand in for a summary.
HEAD_CHARS = 120
# How many seen URLs to keep per feed. Feeds return only a few dozen items, newest first,
# so this many is enough to never mistake "seen before" for new.
SEEN_LIMIT = 500


class _Redirect308(urllib.request.HTTPRedirectHandler):
    """Follow 308 redirects on Python 3.10 too (3.10 doesn't handle 308).

    Same as in fetch.py. Run with -I, the script's folder isn't on the import path, so this keeps its own copy.
    """

    http_error_308 = urllib.request.HTTPRedirectHandler.http_error_302

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, 307 if code == 308 else code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_Redirect308)


def fetch(url: str) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers=UA)
    with _OPENER.open(req, timeout=60) as res:
        return res.read(5_000_000), res.headers.get("Content-Type", "")


def known_feed(url: str) -> tuple[str, str] | None:
    """Places whose feed can be told from the shape of the URL alone. Returns the kind and the feed URL."""
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
    """Find the feed from the page's <link rel="alternate" type="application/rss+xml">.

    Personal blogs, Hatena, WordPress, and YouTube channel pages have one.
    If the URL itself is a feed, use it as-is.
    """
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
        d = email.utils.parsedate_to_datetime(s)  # RSS 2.0 format
    except (TypeError, ValueError):
        try:
            d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))  # Atom format
        except ValueError:
            return None
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def items(feed_bytes: bytes) -> list[dict]:
    """Normalise RSS 2.0 and Atom items into title, URL, date, and opening line.

    Feeds come from other people's servers. XML containing DOCTYPE or ENTITY can be used to load
    external entities or expand nested ones (billion laughs), so it is rejected unread.
    defusedxml is the usual answer, but it isn't installed (adding a dependency needs sign-off).
    Ordinary RSS / Atom doesn't use DOCTYPE, so rejecting it rarely costs anything.
    """
    # Declarations can only come before the root element. Look only before the root, so a body
    # (an HTML article wrapped in CDATA) containing "<!DOCTYPE html>" isn't rejected.
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
    # Report a failure in one line instead of raising, so the next ones can still be added
    # (Reddit returned 429 and it stopped with a traceback, 2026-10-10 trial).
    try:
        kind, feed = discover(url)
        found = items(fetch(feed)[0])  # don't add a feed that can't be read
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
        # The last segment alone gives nothing but "blog" and "releases", so name it by domain and path
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
    """List new posts. With fresh, ignore the seen record and select by the window (days) alone.

    Posts outside the first window are also recorded as "seen", so the record gets in the way
    when widening the window to list again (after 14 days, 30 days couldn't be reviewed, 2026-10-10 trial).
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
        except Exception as e:  # if one feed fails, still check the others
            lines += [f"## {label} ({kind})", f"- Couldn't fetch: {type(e).__name__}: {e}", ""]
            continue
        seen = set() if fresh else set(state.get(feed, []))
        first = fresh or feed not in state
        new = [i for i in got if i["link"] and i["link"] not in seen
               and (not first or (i["date"] and i["date"] >= cutoff))]
        new.sort(key=lambda i: i["date"] or now, reverse=True)
        state[feed] = ([i["link"] for i in got] + list(set(state.get(feed, [])) - {i["link"] for i in got}))[:SEEN_LIMIT]
        if not new:
            # Even with nothing new, show the feed's latest item in one line, regardless of the window. This keeps
            # the latest official news from dropping out of sight past the window (React 19.3 was missed at 31 days old).
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
    # Include seconds. With the date alone, the second run of the day overwrote the first (2026-10-10 trial).
    out = topic / "watch" / f"{now.astimezone():%Y-%m-%d-%H%M%S}.md"
    n = 2
    while out.exists():  # don't erase an earlier result even when run again within the same second
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
    # It prints post titles and opening lines, so don't crash on characters the terminal encoding lacks (à in cp932, etc.)
    sys.stdout.reconfigure(errors="replace")
    sys.exit(main())
