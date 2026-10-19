---
name: imozuru
description: |
  Catch up on an unfamiliar field. Starting from everyday words, find the field's terms, central people, and venues
  (conferences, journals, personal blogs, videos, repositories, curated lists), then follow citations, links, and authors
  lead by lead, and save the sources that hit (papers, personal posts, video captions) to ~/research/<topic>/sources/ unsummarised.
  A map (map.md) grows each round; the dig stops when every needed claim has a source or results saturate.
  Watch mode pulls new posts from the map's venues (Qiita and Zenn tags, note, YouTube, blogs, arXiv) over RSS and lists each with its opening line.
  Use for: "dig into this field", "help me catch up on X", "find the papers and prior work on X",
  "where did this technique come from?", "how do skilled people do X?", "is there research on X? I want the original",
  "what is this called and who works on it?", "find the canonical papers on X", "literature dive",
  "what's new in X this week", "/imozuru", "/imozuru watch".
  Not for: checking a single fact (a year, whether something exists, one spec; just search),
  finding files on the local machine, or summarising material already read.
---

# imozuru

Dig into an unfamiliar field, from not knowing its vocabulary to holding its original sources.
Two rules sit at the core: **save sources without summarising them**, and **stop on evidence, not confidence**.

## Why (read first)

- **No summaries.** Detailed summaries in the confused early stage of a search cause premature closure (Kuhlthau 1991). An agent that summarises early closes the question on its own view and drops the details the user needs to judge. This skill grew out of "what the AI found doesn't match my sense of it". The user reads the sources and judges; the agent points to where they are.
- **No committing early.** When several directions are open, AI search tends to pick one and let later searches reinforce it until it fails (Zhou et al. 2026, HypoSearch). When unsure, branch, compare, then move on.
- **No words? Follow citations.** Chaining through citations avoids having to name the subject at all (Bates 1989). When search terms won't come, follow citations and authors.
- Theory and source locations: `references/theory.md`.

## Layout

Default: `~/research/<topic>/`, with the topic in lowercase English and hyphens (`search-methods`). Use another place if the user names one.

```
map.md        question, needed claims, terms, people, venues, source table, next leads (format below)
log.md        per round: who searched for what, what turned up, decisions and why; every searcher launched,
              including ones that never returned (what it was asked, whether it returned or was stopped)
sources/      the sources: PDF plus .txt, HTML as .md; no summary files
extracts.json extracts, written after stopping (see "The extract page")
report.html   the extract page, built by report.py
watch.tsv     places to watch (watch mode only)
watch/        watch results, one <date>.md per run
```

## Searchers

Hand round 0 and each round's searching to **searcher subagents** ("searchers"). Broad sweeps need no judgement, so a light model such as Haiku is enough. Use an agent definition limited to reading and web search if one exists. Without subagents, run the same briefs yourself, one after another.

## Flow

### 0. Write the question and the needed claims

Create map.md (format below) with the **question** and the 3–6 **claims** needed to answer it, e.g. "what this field calls X", "what the standard methods are", "where they fail". The claims decide when to stop (HALT, Roh & Han 2026).

Claims are easy to make too soft. In one trial all five read "there is …"; they filled in a single round, and the core of the request ("AI-generated images") was never checked. So:

- **At least one claim carries the request's own condition.** For "turn AI-generated images into editable data", write "there are results or cases on AI-generated images".
- **Not only "there is …".** At least half should need a source to answer: how well it works, where it fails, what is missing.
- **The first claim is always "where does this field's knowledge collect?"** Venues are found by searching, not taken from a fixed list (see step 1).
- **For tips and standard practice, add "is there an original source or study behind this?"** If none turns up, write "none found in the range searched". Tutorials alone lead to "there are no rules": in a 2026-10-12 comparison, the plain request concluded that three times out of three, and imozuru without this claim never reached Rood 1879.

The question may shift along the way (berrypicking). When it does, rewrite the question and claims in map.md and log why.

### 1. Map the field (round 0)

Run **two searchers with different approaches**, by default English and Japanese. If one language covers the field, split into "search by terms" and "find the standard reviews and textbooks". The more the two overlap, the fuller the map (capture–recapture, Kastner 2007).

Brief the searchers to:
- Return four things: **terms** (with the URL where each appeared), **people** (affiliation, best-known work), **venues** (conferences, journals, lists, repositories), and **standard materials** (title, author, year, free URL).
- Sort the report into "found / searched, none / not searched". "Not searched" becomes the next leads.
- **Not summarise.** Exact names and URLs come first.
- **Not write files.** Downloading is the parent's job (in one trial a searcher wrote a temp file with curl).
- **Find the venues instead of picking from a list.** Ask "where do this field's experts write?" and "where are the standard materials published?", add the answers to "Venues" in map.md, and log how many results came from each venue, so the per-field skew builds up on record. Whether the know-how lives in papers or personal posts depends on the field; don't decide in round 0. Only when you have no idea at all, use these as examples: conferences, journals, arXiv; personal blogs; Qiita, Zenn, note; YouTube; GitHub; X; pixiv and FANBOX tutorials; forums. A fixed list skews toward its maker's habits, which here means Japanese tech articles.
- When the entry words are unknown, go coarse to fine: encyclopedia (English Wikipedia's References) → specialist encyclopedia → textbooks and lecture notes → surveys → original papers (Yokoi 2017). Without papers: glossaries and intro articles → the people whose names keep coming up → their own records of practice.
- With no Japanese entry words, go in through English ("berrypicking ベイツ" returned only fruit-picking articles).
- **Use normal search first, and deep search only when a wanted kind comes back empty.** Judge thinness by kind, not count: articles but no videos, nothing in Japanese. In the continent-painting trial, eight normal searches came back nearly empty and the first deep search surfaced note, YouTube, and blogs at once; in the MIX trial, normal search found articles but no YouTube. Deep search costs several times more, so don't start there.

When they return, add the terms, people, and venues to map.md, and move "not searched" into **next leads**.

Searcher reports come from search-result snippets; searchers rarely open pages (in one trial, neither opened a single one). Affiliations, "published", and numbers can be wrong. Mark such entries **(unverified)** in map.md and drop the mark once checked against a source.

### 2. Follow (each round)

From the next leads, follow those with a strong scent: names that keep coming up, reviews and textbooks, works cited as the standard, people others point to ("see this person's post"). There are six moves (Bates 1989, Ellis 1987). They work the same for papers and personal posts; only the targets change.

| Move | Papers | Personal posts | Tool |
|---|---|---|---|
| Backward | References | Links in the article, "based on so-and-so's post" | `chain.py refs`, grep the saved text |
| Forward | Citing works, most cited first | Posts that introduce or quote it, Hatena Bookmark | `chain.py cites`, searchers |
| By author | The author's other papers | Their blog archive; post lists on Zenn, Qiita, note; their YouTube channel | `chain.py author`, searchers |
| Scan a venue | The central conferences and journals | Qiita and Zenn tags, pixiv tutorial tags, Discord, Reddit, awesome lists | Searchers |
| Browse nearby | Same issue, same list | Related posts, same tag, the same person's playlists | Searchers |
| Search again | The terms newly on the map | Same, plus community slang and abbreviations | Searchers |

**The fewer papers a field has, the more its know-how lives in personal posts** (painting techniques, MIX, getting the most out of a tool). Don't restrict yourself to authoritative sources.

- **Look papers up by DOI.** A title lookup can land on another record or an explainer, so check `chain.py find` candidates by year and title first.
- **`chain.py` returns 0 for papers about a year old.** OpenAlex hasn't registered their citations yet; 0 doesn't mean none. Go backward by grepping the references section of the saved text (in a trial, this found the target paper). Go forward by asking a searcher for "papers citing <title>".
- **With two or more plausible directions, don't commit.** Run two searchers on different hypotheses and compare when both return.
- **Save hits with `fetch.py`.** Only `OK` results go in map.md's source table. Log each `FAIL` with its reason and URL (paywall, 404, login wall).
- **Before calling a standard work unreachable, look for another copy:** the author's or lab's page, the field's roundup sites, the technical report it came from, university repositories. On 2026-10-14, the Mann & Thompson and Hovy originals that got a 403 on DTIC were on SFU's RST site. No pirate sites.
- After saving, grep the .txt / .md for the parts that bear on the claims and **confirm the line numbers**. On the claim's line in map.md, write file and line, with a short quote. No summary, no conclusion.
- **Pair every line number with a short quote** (a few words, in English). pdftotext merges the columns of two-column PDFs onto one line, so a line number alone won't find the spot, but a quote can be grepped.

### 3. Decide at the end of the round (parent)

**Wait until every searcher you launched has returned.** If you moved on without one, stop it now.

**Round 0** ends once the searchers have built the map; no sources need saving yet. **A round** means saving sources from the leads and following from them at least once: backward, forward, or by author. Relaunching searchers is optional. Without papers, following a saved article's links backward counts. A round where the searchers came up empty and the parent searched alone still counts, but don't measure saturation on it. **Came up empty** means none of the pages the searchers listed turned out to be a hit once saved. It isn't about result counts; searchers report without opening pages, so only the parent's save shows a hit.

Stop when any of these holds, and log the reason:

- **Every needed claim has a source location** (file:line and a short quote each).
- **Saturated**: at least 70% of the people and materials the searchers listed this round are already in map.md, and new terms have nearly dried up. Log the fraction ("11 of 14 already known"). The 70% came from trials and is still a rough guess.
  - **Count only searchers that asked the same question in different ways** (English and Japanese, terms and reviews). Searchers on different hypotheses overlap little by nature, so they say nothing about saturation (one trial branch scored 2/14). Judge each hypothesis branch by whether its own claims are filled.
  - **"Already known" includes the parent's own finds.** Give searchers that same list (once the parent's finds were left out and the fraction came out too low).
- **Four rounds done**: list the claims not reached and why (paywall, not found), then stop.
- **Blocked by walls**: the sources for every remaining claim sit behind login walls (X, pixiv, Xiaohongshu, members-only sites) or paywalls, and nothing more is reachable from outside. List the URLs and ask the user to open them in their browser (see "Hand over").
  - **A partially sourced claim counts as blocked if every missing piece is behind a wall.** If anything is still searchable outside the walls, keep going.
  - **If the source is free and only bot protection blocks it (a Cloudflare challenge, a 403), ask the user to open it in their browser before stopping.** A real browser passes the challenge. A tool that drives the user's browser (such as a DevTools MCP) is fine once the user agrees. Don't trick your way past the challenge. "Request a copy" forms and paid content remain walls.
- **Hit an agreed limit**: the request set a time or round limit and you reached it first. Report how far each criterion got (claims with sources, the saturation fraction) and stop. Don't pretend a criterion was met.

**Don't stop before round 1 is done.** Even if round 0 seems to fill every claim, follow forward or by author from a hit paper at least once. Under-search, quitting early and missing things, is the other classic failure of AI search (Zhang et al. 2026). When continuing, log 2–4 leads for the next round before moving on.

### 4. Hand over

**Before replying, check for searchers or background processes you started that are still running, stop them, and log them.** In a 2026-10-12 trial, processes an agent had started kept running after it returned its report, and since log.md didn't record them, nobody could tell what they were.

Then give the user:

1. **Why you stopped**: one of the five conditions above.
2. **Where each claim's source is**: a line in `sources/<file>`, 1–2 lines per claim.
3. **What wasn't reached**, such as paywalled standard works.
4. **The path to the extract page (`report.html`) first**, then 2–4 other sources most worth reading, each with its path and one line on where to read.
5. **Important-looking material behind walls**: the URL plus one line on why. The user opens it in a logged-in browser. The agent never creates accounts or logs in.
6. Problems with the process itself: tool bugs, searchers overstepping.
7. **One question, "Did this match your sense of it?", with the answer recorded verbatim at the end of `<topic>/log.md`.** Don't paraphrase it. Changes to the 70% threshold or the round limit are decided by reviewing several of these answers together, not from memory.

No summaries or explanations in the reply, unless the user asks for one.

### The extract page

Dozens of saved sources go unread: English PDFs, hour-long captions. Summaries would bring premature closure back. So after stopping, build a page of **extracts** (Ellis's extracting) and hand it over first.

1. Write `<topic_dir>/extracts.json`, with a section per needed claim listing passages **cut verbatim** from the sources (file, line, and `end` if needed). Put an English translation of non-English text in `en`; the page marks it as a translation. Labels such as [First-hand] or auto-captions go in `mark`. Where two-column PDFs merge columns onto one line, split the extract with "…" and each piece is matched in turn; the "…" also shows the reader that something was cut. List disagreements in `disagreements` without saying which side is right. Put what wasn't reached in `unreached`. `examples/demo/extracts.json` in the repository is a model.
   Format (as at the top of report.py; `?` marks optional fields):
   ```
   {"title", "question", "stopped",
    "claims": [{"claim", "status": "sourced|partial|unsourced", "note"?,
                "quotes": [{"file", "line", "end"?, "text", "en"?, "mark"?}]}],
    "disagreements"?: [{"topic", "quotes": [{"file", "line", "text", "who", ...}]}],
    "unreached"?: ["..."]}
   ```
2. Run `scripts/report.py <topic_dir>`. **It checks that each extract appears verbatim at the given lines of its source**, and if any fails, it builds nothing, so paraphrases can't slip in. Otherwise it writes `report.html`, where each extract can expand to show the surrounding lines.
3. The agent writes only headings, statuses (sourced / partial / unsourced), one-line notes, and translations. Notes carry no conclusions or verdicts: "the order differs between articles" is fine, "this order is correct" is not. Write them as plain statements of who did what.
4. Leave auto-caption mistranscriptions as they are; fixing them is paraphrasing. An "auto-captions" label tells the reader to check against the video.

## Watch mode

Turn the venues from a dig into places to follow for new posts (Ellis's monitoring). Triggers: "what's new in X", "round up this week's X", "/imozuru watch <topic>". **Run it only when asked.** Scheduling it can wait until it has worked as intended a few times.

1. **Check for a map.** Without `~/research/<topic>/map.md` (say, a cold "what's new in React"), there are two ways in:
   - **Quick (default)**: add the obvious places and start watching: the official blog and GitHub releases, the Qiita tag, the Zenn topic, well-known personal blogs. Keep the map minimal (question, venues, people) and grow it later. In the React trial, two round-0 searchers took about 2 minutes and found almost exactly the obvious places.
   - **No idea where to look**: run step 1 (round 0) to find the venues, then watch.
2. **Add places to watch.** From "Venues" and "People" in map.md, pick places that publish new posts and add each with `scripts/watch.py add <topic_dir> <url>`. Supported: Qiita tags and users, Zenn topics and users, note users, Reddit, YouTube channels, blogs with RSS, and arXiv searches (`http://export.arxiv.org/api/query?search_query=...&sortBy=submittedDate&sortOrder=descending`). X and pixiv publish no RSS; tell the user they can't be watched.
   - **Let `watch.py add` decide whether a feed exists, not a searcher.** Searchers guess feed URLs, and one claimed react.dev had no feed when it did. Likewise, check "it stopped updating" against the latest item that check reports.
3. **Pull new posts.** `scripts/watch.py check <topic_dir>` lists what's new since the last run (for a first-time feed, the last 14 days; change with `--days`). Each run is saved to `watch/<date-time>.md`, so repeat runs on the same day don't overwrite each other.
   - **Places with nothing new still show their latest item**, whatever the window, so a big official release just outside the window stays visible.
   - **To widen the window and re-list, use `--fresh`.** Posts outside the first window are recorded as seen too; `--fresh` ignores that record and selects by window alone.
4. **Hand over.** Show the list: title, date, and place for each, plus the **original's opening line** from the feed as a `>` quote. **No agent summaries or scores**; the writer's own opening line is what the user chooses by. Save with `fetch.py` only what the user picks or what bears on a needed claim, and add it to the source table with its label.
   - **For long lists** (more than about 20), you may filter by kind to suit the request ("personal blogs and overseas too" means fewer Qiita and Zenn posts). Say you filtered and where the full file is. Filtering changes the selection, not the content: still no summaries.
   - Put the latest items from places with nothing new briefly at the end.
5. If people, venues, or terms missing from the map keep appearing, add them to "Next leads" in map.md and ask whether to watch them too. This is the way back from watching to digging.

## map.md format

```markdown
# map: <topic>

Question: <1–2 lines>
Entry words: <the words you started with>

## Needed claims
- [ ] <claim 1> — <source location; [x] once sourced>

## Terms
- <term> (<Japanese name>) — <URL where it appeared, or a file in sources/>

## People
- <name> (<affiliation>) — <best-known work>

## Venues
- <conference, journal, list, repository> — <URL>

## Sources (sources/)
| Paper or material | File | Original URL | Found via (round, move) |
|---|---|---|---|

## Next leads
- <not yet followed> — <why it looks promising>
```

Keep the sections in this order and append to the end of each, so tables don't scatter across rounds. One row per work in the source table; put all its files (PDF and .txt, an abstract .md) on that row. Mark rows from searchers whose sources nobody has opened (unverified).

Start each entry in the "Paper or material" column with one **kind label**. No scores; the user decides what to trust by reading.

- [Paper] peer-reviewed or conference papers, arXiv preprints
- [First-hand] a record by the person who did it: an article, video, or README showing the process of trying, making, or measuring it themselves
- [Observation] notes on features of someone else's work or methods ("these illustrators paint like this")
- [Roundup] articles that collect or restate others' findings: "I looked into it" posts, aggregators, explainers of explainers, encyclopedias, glossaries
- [Official] documents and announcements from the maker of the tool or product

[First-hand] counts as primary even when it's a personal post. For [Observation], if the observed person is named, add them to "Next leads"; their own record is the real primary source. [Roundup] is a good entry point and a place to pick up backward leads, but back claims with [First-hand] or [Paper] where possible.

After the label, add whichever of these apply:

- **has examples**: shows the writer's own work. When the user wants to know how skilled people do it, have them read these first; whether someone is skilled is for the user to judge from the examples
- **has measurements**: includes the writer's own numbers or comparisons (benchmarks, colours measured from photos, settings compared)
- **AI-assisted**: the writer says AI wrote it
- **promotional**: leads to something the writer sells. The content may still be first-hand; the label lets readers discount it
- **(unread)**: saved, but no agent or subagent has read it yet
- **auto-captions**: from YouTube auto-captions, which are full of mistranscriptions (「線画」 "line art" → 「洗画」). Quote only what's legible, and have the user check the video before it backs a claim

## Tools

The scripts need only the Python 3.10+ standard library. External commands are used when present; each line says what happens without them.

- `scripts/fetch.py <sources_dir> <name> <url>` saves a source and checks it's real. PDFs become .pdf plus .txt (`pdftotext -layout`, from poppler or Xpdf); HTML becomes .md; YouTube becomes a captions .md as `[min:sec] text` (`yt-dlp`; no video download). PDFs without a text layer are OCR'd with `pdftoppm` and `tesseract`. If a needed command is missing, the `FAIL` names it. HTML goes through [ax](https://github.com/yusukebe/ax) when available, otherwise the standard library (ax keeps headings and tables better). Downloads are checked in a scratch folder, and only passing files move to sources_dir. 404s, walls, and too-short text are `FAIL`, and an existing source with the same name is left untouched. X serves no text, so it's never fetched and always `FAIL`: keep the URL and the searcher's snippet in map.md, marked (unverified)
- Point into videos by time instead of line (`sources/x.md [12:34]`)
- `scripts/report.py <topic_dir> [--check]` checks extracts.json against the sources and, if all match, writes report.html. `--check` only checks
- `scripts/watch.py add|list|check` reads RSS / Atom and lists what's new since the last run. No search, so it's free and the results are stable. Feeds containing DOCTYPE or ENTITY are refused for safety
- `scripts/chain.py find|refs|cites|author` follows citations and authors through OpenAlex. Free for 1,000 calls a day; with a prepaid balance of 0, it just stops at the limit. **Never register an API key or payment details.** Good on older papers, weak on new papers and common author names (author can pick up a namesake)
- File names: `<author>-<year>-<short-title>`, or `arxiv-<number>-<short-title>` for arXiv

## Boundaries

- At most two searchers at once. Saturation is measured across two different approaches, and more searchers cost more and make overlap harder to read
- Keep confidential or personal research out of it. Searchers query the web, so the question leaves the machine as search terms
- No workarounds for paywalls (pirate sites and the like). Report those sources as not reached
- Saved sources are local reading copies. Don't redistribute them
