#!/usr/bin/env python3
"""Fetch one source and keep it in sources/ only if its content looks real.

Stale search URLs often serve 404s, login walls, or HTML posing as PDF with a 200,
so judge by content and length, not by status or extension.

Usage:
    fetch.py <sources_dir> <name> <url>
Output (one line on stdout, tab-separated):
    OK   <name> <saved file> <characters> <first line>
    FAIL <name> <reason>
"""

import codecs
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

# Error pages and walls fit in a few thousand characters. HTML gets a lower floor so short
# Japanese articles pass (a real one was 2,904 characters).
MIN_TEXT_CHARS = 3000
MIN_HTML_CHARS = 1000
MAX_BYTES = 40_000_000
WALL_PATTERNS = (
    "404 not found",
    "page not found",
    "access denied",
    "you do not currently have access",
    "sign in to continue",
    "log in to continue",
    "enable javascript",
    "are you a robot",
    "captcha",
)


class _Redirect308(urllib.request.HTTPRedirectHandler):
    """Follow 308 redirects on Python 3.10, which only learned them in 3.11 (#3)."""

    http_error_308 = urllib.request.HTTPRedirectHandler.http_error_302

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, 307 if code == 308 else code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_Redirect308)


def download(url: str) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 imozuru"})
    with _OPENER.open(req, timeout=90) as res:
        return res.read(MAX_BYTES), res.headers.get("Content-Type", "")


# Pages declaring Shift_JIS often use Windows extensions (①, 髙), so read them as cp932
_CHARSET_ALIASES = {"shift_jis": "cp932", "shift-jis": "cp932", "sjis": "cp932", "x-sjis": "cp932",
                    "windows-31j": "cp932", "ms_kanji": "cp932"}


def _declared_charsets(body: bytes, ctype: str) -> list[str]:
    found = re.findall(r"charset\s*=\s*[\"']?([\w.:-]+)", ctype or "", re.I)
    found += re.findall(rb"<meta[^>]*charset\s*=\s*[\"']?([\w.:-]+)", body[:4096], re.I)
    names = [(n.decode("ascii", "ignore") if isinstance(n, bytes) else n).lower() for n in found]
    return [_CHARSET_ALIASES.get(n, n) for n in names]


def decode_text(body: bytes, ctype: str = "") -> str:
    """Decode with the first charset that works: declared, UTF-8, then the Japanese ones.

    Declarations can lie. If nothing decodes cleanly, take the result with the fewest U+FFFD.
    """
    candidates = []
    for name in [*_declared_charsets(body, ctype), "utf-8", "cp932", "euc_jp"]:
        try:
            codec = codecs.lookup(name).name
        except LookupError:
            continue
        if codec not in candidates:
            candidates.append(codec)
    for codec in candidates:
        try:
            return body.decode(codec)
        except UnicodeDecodeError:
            continue
    return min((body.decode(c, errors="replace") for c in candidates), key=lambda t: t.count("�"))


def missing(*commands: str) -> list[str]:
    return [c for c in commands if shutil.which(c) is None]


def pdf_to_text(pdf: Path) -> str:
    """-enc UTF-8 because Xpdf's pdftotext (in Git for Windows) defaults to Latin-1 (#3)."""
    if missing("pdftotext"):
        return ""
    out = pdf.with_suffix(".txt")
    subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", str(pdf), str(out)], check=False,
                   stderr=subprocess.DEVNULL)
    return out.read_text(encoding="utf-8", errors="replace") if out.exists() else ""


def ocr_pdf(pdf: Path) -> str:
    """OCR a scanned PDF that has no text layer. English only."""
    if missing("pdftoppm", "tesseract"):
        return ""
    tmp = pdf.parent / f".{pdf.stem}-ocr"
    tmp.mkdir(exist_ok=True)
    subprocess.run(["pdftoppm", "-r", "200", "-png", str(pdf), str(tmp / "p")],
                   check=False, stderr=subprocess.DEVNULL)
    pages = []
    for img in sorted(tmp.glob("p-*.png")):
        res = subprocess.run(["tesseract", str(img), "-", "-l", "eng"],
                             capture_output=True, encoding="utf-8", errors="replace")
        pages.append(f"=== page {img.stem.split('-')[-1]} ===\n{res.stdout}")
        img.unlink()
    tmp.rmdir()
    text = "\n".join(pages)
    out = pdf.with_suffix(".txt")
    out.write_text("(Text produced by OCR. Errors remain, so check quotes against the original PDF.)\n\n" + text,
                   encoding="utf-8")
    return text


HAS_AX = shutil.which("ax") is not None


class _TextExtractor(HTMLParser):
    """Fallback HTML-to-text when ax is missing.

    Prefers <main>/<article> when it has enough text. Keeps links as `[text](URL)` for backward chaining.
    """

    FOCUS = {"main", "article"}

    SKIP = {"script", "style", "noscript", "svg", "template", "iframe"}
    BLOCK = {"p", "div", "section", "article", "main", "header", "footer", "nav", "aside",
             "li", "tr", "br", "hr", "pre", "blockquote", "table", "ul", "ol", "dl", "dt", "dd",
             "figure", "figcaption"}
    HEADING = {"h1": "# ", "h2": "## ", "h3": "### ", "h4": "#### ", "h5": "##### ", "h6": "###### "}

    def __init__(self, base: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base = base
        self.parts: list[str] = []
        self.skip = 0
        self.href: str | None = None
        self.link_text: list[str] = []
        self.focus = 0
        self.focus_parts: list[str] = []

    def _emit(self, piece: str) -> None:
        self.parts.append(piece)
        if self.focus:
            self.focus_parts.append(piece)

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif self.skip:
            return
        elif tag in self.FOCUS:
            self.focus += 1
        elif tag in self.HEADING:
            self._emit("\n\n" + self.HEADING[tag])
        elif tag in self.BLOCK:
            self._emit("\n")
        elif tag == "a":
            href = dict(attrs).get("href")
            if href and not href.startswith(("#", "javascript:")):
                self.href = urllib.parse.urljoin(self.base, href)
                self.link_text = []

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
        elif self.skip:
            return
        elif tag in self.FOCUS:
            self.focus = max(0, self.focus - 1)
        elif tag in self.HEADING or tag in self.BLOCK:
            self._emit("\n")
        elif tag == "a" and self.href is not None:
            text = " ".join("".join(self.link_text).split())
            self._emit(f"[{text}]({self.href})" if text else "")
            self.href = None

    def handle_data(self, data):
        if self.skip:
            return
        if self.href is not None:
            self.link_text.append(data)
        else:
            self._emit(data)

    def text(self) -> str:
        focused = "".join(self.focus_parts)
        raw = focused if len(focused.strip()) >= MIN_HTML_CHARS else "".join(self.parts)
        lines = (" ".join(line.split()) for line in raw.splitlines())
        return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip() + "\n"


def html_to_md(url: str, out: Path, body: bytes | None = None, ctype: str = "") -> str:
    """Convert a page to markdown with ax, or with _TextExtractor reusing body if given."""
    if HAS_AX:
        res = subprocess.run(["ax", url, "--md", "--all"], capture_output=True,
                             encoding="utf-8", errors="replace")
        text = res.stdout
    else:
        if body is None:
            body, ctype = download(url)
        if body[:5] == b"%PDF-":
            # Redirected to a PDF; the caller refetches it as one
            text = "%PDF"
        else:
            parser = _TextExtractor(url)
            parser.feed(decode_text(body, ctype))
            text = parser.text()
    out.write_text(text, encoding="utf-8")
    return text


def ax_save(url: str, out: Path) -> bool:
    """Save the raw body. Needed where ax gets a PDF but urllib got HTML (HAL)."""
    if HAS_AX:
        subprocess.run(["ax", url, "-o", str(out)], capture_output=True)
    else:
        try:
            out.write_bytes(download(url)[0])
        except Exception:
            return False
    return out.exists() and out.stat().st_size > 0


YOUTUBE = re.compile(r"(youtube\.com/(watch|shorts|live)|youtu\.be/)")
X_POST = re.compile(r"^https?://(www\.)?(x|twitter)\.com/")
MIN_TRANSCRIPT_CHARS = 300


def youtube_to_md(url: str, out: Path) -> str:
    """Save captions (not the video) as `[min:sec] text` lines.

    Manual captions first, auto only if there are none: both use the same file name, and the
    header records which kind, since auto-captions need checking against the video.
    Auto-captions repeat lines across segments, so consecutive duplicates are dropped.
    """
    tmp = out.parent / f".{out.stem}-subs"
    tmp.mkdir(exist_ok=True)
    kind = "manual"
    for flag in ("--write-subs", "--write-auto-subs"):
        meta = subprocess.run(
            ["yt-dlp", "--no-update", "--skip-download", flag, "--encoding", "utf-8",
             "--sub-langs", "ja,en", "--sub-format", "vtt", "--no-simulate",
             "--print", "%(title)s\t%(uploader)s\t%(upload_date)s",
             "-o", str(tmp / "v.%(ext)s"), url],
            capture_output=True, encoding="utf-8", errors="replace")
        if any(tmp.glob("*.vtt")):
            break
        kind = "auto (has mistranscriptions; check quotes against the video)"
    vtts = sorted(tmp.glob("*.vtt"), key=lambda p: (".ja" not in p.name, p.name))
    lines, last = [], ""
    if vtts:
        stamp = "00:00"
        for raw in vtts[0].read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"(\d\d):(\d\d):(\d\d)\.\d+ -->", raw)
            if m:
                h, mi, s = (int(x) for x in m.groups())
                stamp = f"{h * 60 + mi:02d}:{s:02d}"
                continue
            text = re.sub(r"<[^>]+>", "", raw).strip()
            if not text or text in ("WEBVTT",) or text.startswith(("Kind:", "Language:")):
                continue
            if text != last:
                lines.append(f"[{stamp}] {text}")
                last = text
    for p in tmp.iterdir():
        p.unlink()
    tmp.rmdir()
    head = meta.stdout.strip().split("\t")
    title = head[0] if head and head[0] else url
    info = " / ".join(head[1:]) if len(head) > 1 else ""
    body = "\n".join(lines)
    out.write_text(f"# {title}\n\n{url}\n{info}\nCaptions: {kind + ' ' + vtts[0].name if vtts else 'none'}\n\n{body}\n",
                   encoding="utf-8")
    return body


def first_line(text: str) -> str:
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if len(line) > 8:
            return line[:100]
    return ""


def save_verified(saved: Path, kept: Path, destination: Path) -> Path:
    if saved != kept:
        saved.replace(destination / saved.name)
    target = destination / kept.name
    kept.replace(target)
    return target


def valid_source_name(name: str) -> bool:
    """A plain file name: no path parts, control characters, or Windows device names."""
    device = name.split(".", 1)[0].rstrip(" ").upper()
    return (bool(name.strip(" .")) and name == name.rstrip(" .")
            and not any(c in name for c in "/\\:")
            and not any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in name)
            and device not in {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
            and not re.fullmatch(r"(?:COM|LPT)[1-9¹²³]", device))


def fetch_source(sources: Path, name: str, url: str, destination: Path) -> int:
    """Work in the scratch folder `sources`; move to `destination` only after the checks pass."""
    if not valid_source_name(name):
        print(f"FAIL\t{name!r}\tthe source name must be a single file name")
        return 1

    if X_POST.match(url):
        print(f"FAIL\t{name}\tX keeps its text behind a login wall (keep the URL in map.md)")
        return 1
    if YOUTUBE.search(url):
        if missing("yt-dlp"):
            print(f"FAIL\t{name}\tyt-dlp is missing, so captions can't be downloaded")
            return 1
        kept = sources / f"{name}.md"
        body = youtube_to_md(url, kept)
        if len(body) < MIN_TRANSCRIPT_CHARS:
            kept.unlink(missing_ok=True)
            print(f"FAIL\t{name}\tno captions, or too short ({len(body)} characters)")
            return 1
        kept = save_verified(kept, kept, destination)
        print(f"OK\t{name}\t{kept}\t{len(body)}\t{first_line(body)}")
        return 0

    try:
        body, ctype = download(url)
    except Exception as e:
        print(f"FAIL\t{name}\t{type(e).__name__}: {e}")
        return 1

    if not body.strip():
        # Usually bot protection that only serves real browsers
        print(f"FAIL\t{name}\tempty response (possibly bot protection; it may open in a browser)")
        return 1
    if body[:5] == b"%PDF-":
        saved = sources / f"{name}.pdf"
        saved.write_bytes(body)
        text = pdf_to_text(saved)
        kept = saved.with_suffix(".txt")
        if len(text.strip()) < 200 and not re.search(r"arxiv\.org", url):
            text = ocr_pdf(saved)  # arXiv falls back to HTML below instead
    elif ctype.startswith(("text/plain", "text/markdown", "application/json", "text/csv")):
        # Before the HTML check: markdown starting with an HTML comment would otherwise go to ax and lose its line breaks
        ext = ".json" if "json" in ctype else ".csv" if "csv" in ctype else ".md"
        kept = saved = sources / f"{name}{ext}"
        text = decode_text(body, ctype)
        kept.write_text(text, encoding="utf-8")
    elif "html" in ctype or body.lstrip()[:1] == b"<":
        kept = sources / f"{name}.md"
        text = html_to_md(url, kept, body, ctype)
        saved = kept
        # ax followed a redirect to the PDF itself (HAL)
        if text.lstrip().startswith("%PDF"):
            kept.unlink(missing_ok=True)
            saved = sources / f"{name}.pdf"
            if ax_save(url, saved) and saved.read_bytes()[:5] == b"%PDF-":
                text = pdf_to_text(saved)
                kept = saved.with_suffix(".txt")
                if len(text.strip()) < 200:
                    text = ocr_pdf(saved)
            else:
                saved.unlink(missing_ok=True)
                print(f"FAIL\t{name}\tcouldn't save the redirected PDF")
                return 1
    else:
        print(f"FAIL\t{name}\tunsupported type: {ctype or 'unknown'}")
        return 1

    # pdftotext sometimes gets nothing from arXiv PDFs; the HTML version works
    arxiv_id = re.search(r"arxiv\.org/(?:pdf|abs)/(\d{4}\.\d{4,5}(?:v\d+)?)", url)
    if arxiv_id and len(text) < MIN_TEXT_CHARS:
        for p in (saved, kept):
            p.unlink(missing_ok=True)
        kept = saved = sources / f"{name}.md"
        text = html_to_md(f"https://arxiv.org/html/{arxiv_id.group(1)}", kept)

    floor = MIN_TEXT_CHARS if saved.suffix == ".pdf" else MIN_HTML_CHARS
    head = text[:4000].lower()
    wall = next((p for p in WALL_PATTERNS if p in head), None)
    if len(text) < floor or (wall and len(text) < MIN_TEXT_CHARS * 4):
        for p in (saved, kept):
            p.unlink(missing_ok=True)
        reason = f"hit a wall ({wall})" if wall else f"text too short ({len(text)} characters)"
        lacking = missing("pdftotext", "pdftoppm", "tesseract") if saved.suffix == ".pdf" else []
        if lacking:
            reason += f"; missing {', '.join(lacking)}"
        print(f"FAIL\t{name}\t{reason}")
        return 1

    kept = save_verified(saved, kept, destination)
    print(f"OK\t{name}\t{kept}\t{len(text)}\t{first_line(text)}")
    return 0


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__, file=sys.stderr)
        return 2
    sources, name, url = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    if not valid_source_name(name):
        print(f"FAIL\t{name!r}\tthe source name must be a single file name")
        return 1
    sources.mkdir(parents=True, exist_ok=True)
    # Inside the destination, so the final move stays on one filesystem
    with tempfile.TemporaryDirectory(prefix=".imozuru-fetch-", dir=sources) as tmp:
        return fetch_source(Path(tmp), name, url, sources)


if __name__ == "__main__":
    # Don't crash printing characters the console encoding lacks (e.g. cp932)
    sys.stdout.reconfigure(errors="replace")
    sys.exit(main())
