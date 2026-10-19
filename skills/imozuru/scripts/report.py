#!/usr/bin/env python3
"""Turn the extracts (extracts.json) into a page for reading (report.html), after checking them against the sources.

Save 40 sources and, left as English PDFs and hour-long captions, they go unread.
Yet if the agent summarises them, it is back to "premature closure". The middle ground is
Ellis's extracting: for each claim, cut passages from the sources verbatim and lay them out.
The agent writes only the headings, "not found", and translations.

To keep paraphrases from slipping in, it checks by machine that each extract appears verbatim at the given lines of its source.
If even one isn't found, it builds no HTML, prints which ones don't match, and stops.

Usage:
    report.py <topic_dir>         … <topic_dir>/extracts.json → <topic_dir>/report.html
    report.py <topic_dir> --check … check only, no HTML

Format of extracts.json (example in the repository at examples/demo/extracts.json):
    {"title", "question", "stopped",
     "claims": [{"claim", "status": "sourced|partial|unsourced", "note"?,
                 "quotes": [{"file", "line", "end"?, "text", "en"?, "mark"?, "context_note"?}]}],
     "disagreements"?: [{"topic", "quotes": [{..., "who"}]}],
     "unreached"?: ["..."]}
"""

import html
import json
import re
import sys
from pathlib import Path, PureWindowsPath

# Lines to show before and after, so the reader can open the flow an extract sat in from within the page.
CONTEXT_LINES = 6


def norm(s: str) -> str:
    """Normalise whitespace, line breaks, and bullet markers for matching. The characters themselves are left alone."""
    s = re.sub(r"(?m)^\s*[-*]\s+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def verify(src_dir: Path, q: dict) -> tuple[bool, list[str], int, int]:
    """Whether the extract appears verbatim at the given lines of the source (with 2 lines of slack either side). Also returns the surrounding context."""
    relative = Path(q["file"])
    if relative.is_absolute() or PureWindowsPath(q["file"]).is_absolute() or ".." in relative.parts:
        return False, [], 0, 0
    try:
        root = src_dir.resolve()
        topic = src_dir.parent.resolve()
        path = (src_dir / relative).resolve()
    except (OSError, RuntimeError, ValueError):
        return False, [], 0, 0
    if root == topic or not root.is_relative_to(topic):
        return False, [], 0, 0
    if not path.is_relative_to(root) or not path.is_file():
        return False, [], 0, 0
    # splitlines() also counts page breaks (\f) as line breaks, so line numbers drift from grep and sed. Split on newlines only
    lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
    start = max(1, q["line"] - 2)
    end = min(len(lines), q.get("end", q["line"]) + 2)
    region = norm(" ".join(lines[start - 1:end]))
    # In two-column PDFs the left and right columns mix onto one line, so a sentence spanning several lines can't be matched as-is
    # (this happened with Yoshida 2008). If the extract is split with "…", each piece is matched in order.
    # The splits stay on the page as "…", so the reader can see something was left out.
    pieces = [norm(p) for p in q["text"].split("…") if norm(p)]
    ok, pos = bool(pieces), 0
    for piece in pieces:
        at = region.find(piece, pos)
        if at < 0:
            ok = False
            break
        pos = at + len(piece)
    c0 = max(1, q["line"] - CONTEXT_LINES)
    c1 = min(len(lines), q.get("end", q["line"]) + CONTEXT_LINES)
    return ok, lines[c0 - 1:c1], c0, c1


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def quote_html(src_dir: Path, q: dict, ctx: list[str], c0: int) -> str:
    loc = f"{q['file']}:{q['line']}" + (f"-{q['end']}" if q.get("end") else "")
    hit = range(q["line"], q.get("end", q["line"]) + 1)
    # Blank lines in markdown spread things out, so skip empty lines (line numbers stay, so positions can still be traced)
    # span is display:block, so no newline between them (with one, the line spacing doubled)
    ctx_html = "".join(
        f'<span class="{"hit" if c0 + i in hit else ""}"><b>{c0 + i}</b> {esc(t)}</span>'
        for i, t in enumerate(ctx) if t.strip())
    parts = ['<figure class="quote">']
    if q.get("who"):
        parts.append(f'<div class="who">{esc(q["who"])}</div>')
    parts.append(f'<blockquote>{esc(q["text"])}</blockquote>')
    if q.get("en"):
        parts.append(f'<p class="en"><span class="tag">Translation</span>{esc(q["en"])}</p>')
    meta = [f'<code>{esc(loc)}</code>']
    if q.get("mark"):
        meta.append(f'<span class="mark">{esc(q["mark"])}</span>')
    if q.get("context_note"):
        meta.append(f'<span class="cn">{esc(q["context_note"])}</span>')
    parts.append(f'<figcaption>{" ".join(meta)}</figcaption>')
    parts.append(f'<details><summary>Read around it (lines {c0}–{c0 + len(ctx) - 1})</summary><pre>{ctx_html}</pre></details>')
    parts.append("</figure>")
    return "\n".join(parts)


CSS = """
:root{--bg:#f6efd3;--ink:#2e1703;--sub:#6b4a26;--accent:#814e0d;--card:#fbf7e8;--line:#e2cf9f;--hit:#efdcab}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#1f1710;--ink:#f1e6cc;--sub:#c9b28a;--accent:#e0a85a;--card:#2a2016;--line:#4a3a26;--hit:#4a3820}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,-apple-system,"Segoe UI","Noto Sans JP","Hiragino Sans",sans-serif;line-height:1.7;font-size:16px}
main{max-width:46rem;margin:0 auto;padding:2.5rem 1rem 5rem}
h1{font-size:1.6rem;margin:0 0 .5rem;letter-spacing:.02em}
h2{font-size:1.2rem;margin:3rem 0 .4rem;padding-top:1rem;border-top:1px solid var(--line)}
.lead{color:var(--sub);margin:.2rem 0}
.status{display:inline-block;font-size:.8rem;padding:.05rem .55rem;border-radius:99px;border:1px solid var(--accent);color:var(--accent);margin-left:.5rem;vertical-align:middle}
.status.none{border-style:dashed;color:var(--sub);border-color:var(--sub)}
.note{color:var(--sub);font-size:.95rem}
.quote{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:1rem 1.1rem;margin:1rem 0}
blockquote{margin:0;padding-left:.9rem;border-left:3px solid var(--accent);white-space:pre-wrap}
.who{font-weight:600;margin-bottom:.4rem}
.en{margin:.6rem 0 0;color:var(--sub)}
.tag{font-size:.75rem;border:1px solid var(--sub);border-radius:4px;padding:0 .3rem;margin-right:.4rem}
figcaption{margin-top:.6rem;font-size:.8rem;color:var(--sub);display:flex;flex-wrap:wrap;gap:.5rem}
code{font-family:ui-monospace,"Cascadia Code",monospace;font-size:.78rem}
.mark{color:var(--accent)}
details{margin-top:.5rem;font-size:.8rem}
summary{cursor:pointer;color:var(--sub)}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:.78rem;line-height:1.6;max-height:22rem;overflow:auto;margin:.4rem 0 0}
pre span{display:block}
pre span.hit{background:var(--hit)}
pre b{display:inline-block;min-width:3em;color:var(--sub);font-weight:400}
ul.unreached li{margin:.2rem 0}
footer{margin-top:4rem;font-size:.8rem;color:var(--sub)}
"""


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    topic = Path(sys.argv[1]).expanduser()
    check_only = "--check" in sys.argv
    data = json.loads((topic / "extracts.json").read_text(encoding="utf-8"))
    src = topic / "sources"

    bad, rendered = [], {}
    groups = [("claims", c) for c in data["claims"]] + [("dis", d) for d in data.get("disagreements", [])]
    for _, g in groups:
        for q in g.get("quotes", []):
            ok, ctx, c0, _ = verify(src, q)
            if not ok:
                bad.append(f"{q['file']}:{q['line']}  \"{q['text'][:40]}…\"")
            rendered[id(q)] = (ctx, c0)
    if bad:
        print("Some extracts were not found in the source (a paraphrase, or line numbers that drifted):")
        print("\n".join("  " + b for b in bad))
        return 1
    total = sum(len(g.get("quotes", [])) for _, g in groups)
    print(f"Check OK: all {total} extracts match the sources")
    if check_only:
        return 0

    body = [f"<h1>{esc(data['title'])}</h1>",
            f'<p class="lead">Question: {esc(data["question"])}</p>',
            f'<p class="lead">Why it stopped: {esc(data["stopped"])}</p>',
            '<p class="note">Every quote here is cut verbatim from a source (checked by machine). The agent wrote only the headings, statuses, notes, and "Translation" lines. Nothing is summarised.</p>']
    for c in data["claims"]:
        cls = "status none" if c["status"] == "unsourced" else "status"
        body.append(f'<h2>{esc(c["claim"])}<span class="{cls}">{esc(c["status"])}</span></h2>')
        if c.get("note"):
            body.append(f'<p class="note">{esc(c["note"])}</p>')
        for q in c.get("quotes", []):
            ctx, c0 = rendered[id(q)]
            body.append(quote_html(src, q, ctx, c0))
    for d in data.get("disagreements", []):
        body.append(f'<h2>Disagreement: {esc(d["topic"])}</h2><p class="note">Which is right is not stated. They are only laid side by side.</p>')
        for q in d.get("quotes", []):
            ctx, c0 = rendered[id(q)]
            body.append(quote_html(src, q, ctx, c0))
    if data.get("unreached"):
        body.append("<h2>Not reached</h2><ul class=\"unreached\">"
                    + "".join(f"<li>{esc(u)}</li>" for u in data["unreached"]) + "</ul>")
    # An absolute path would leak the local user name when the page is shared, so write it relative to the page
    body.append(f'<footer>imozuru extracts. The sources are in {esc(src.name)}/ next to this page</footer>')

    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(data['title'])} extracts</title><style>{CSS}</style></head>
<body><main>
{chr(10).join(body)}
</main></body></html>
"""
    out = topic / "report.html"
    out.write_text(page, encoding="utf-8")
    print(f"→ {out}")
    return 0


if __name__ == "__main__":
    # It prints the start of extracts, so don't crash on characters the terminal encoding lacks (à in cp932, etc.)
    sys.stdout.reconfigure(errors="replace")
    sys.exit(main())
