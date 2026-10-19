# Where imozuru's rules come from

Which source, and which passage in it, backs each rule in SKILL.md. The sources were saved with the skill itself in a 2026-10-09 trial
on research about how people search. Line numbers refer to the .txt / .md that `scripts/fetch.py` produces from the URLs below
(PDFs through `pdftotext -layout`, HTML through ax). Other converters shift the line numbers, so search by the short quotes.
Reread the original passage before changing a rule.

## Sources

| File name | URL |
|---|---|
| `bates-1989-berrypicking` | https://www.pages.gseis.ucla.edu/faculty/bates/articles/berrypicking.pdf |
| `ellis-1987-phd-behavioural-model` | https://etheses.whiterose.ac.uk/id/eprint/2975/1/DX093006.pdf |
| `kuhlthau-1991-inside-search-process` | https://tefkos.rutgers-sci.domains/Courses/612/Articles/Kuhlthau_Inside_91.pdf |
| `arxiv-2609.01294-explore-before-committing` | https://arxiv.org/pdf/2609.01294 |
| `arxiv-2608.02009-halt` | https://arxiv.org/pdf/2608.02009 |
| `arxiv-2602.03304-to-search-or-not` | https://arxiv.org/pdf/2602.03304 |
| `kastner-2007-horizon-estimate` | https://pmc.ncbi.nlm.nih.gov/articles/PMC2655834/ |
| `eumesy-unknown-terms` | https://speakerdeck.com/eumesy/examine-the-meaning-of-unknown-terms |
| `arxiv-2505.09316-scent-of-knowledge` | https://arxiv.org/pdf/2505.09316 |

## Rules and sources

| Rule | Source | Where |
|---|---|---|
| The question shifts during the search; you gather pieces along the way | Bates 1989 "The design of browsing and berrypicking techniques for the online search interface" | `bates-1989-berrypicking.txt` |
| Six moves for following leads (backward, forward, journal run, area scanning, subject indexes, author) | Bates 1989 | same, L295-355 |
| Following citations avoids having to name the subject | Bates 1989 | same, L297-302 |
| starting / chaining / browsing / differentiating / monitoring / extracting | Ellis 1987 PhD thesis (basis of the paywalled 1989 JoD paper) | `ellis-1987-phd-behavioural-model.txt` L64, contents L165-276 |
| Confusion early in a search is normal; detailed notes cause premature closure; list the facts that seem to fit | Kuhlthau 1991 "Inside the Search Process" | `kuhlthau-1991-inside-search-process.txt` L345-368 |
| Committing to one direction lets later searches reinforce it; branch into hypotheses and compare first | Zhou et al. 2026 "Explore Before Committing" (HypoSearch), arXiv 2609.01294 | `arxiv-2609.01294-explore-before-committing.txt`, abstract |
| Stop when evidence supports every needed claim, not when confident | Roh & Han 2026 "HALT", arXiv 2608.02009 | `arxiv-2608.02009-halt.txt`, abstract |
| Two failure modes: over-search (going on when there's enough) and under-search (quitting early and missing things) | Zhang et al. 2026 "To Search or Not to Search", arXiv 2602.03304 | `arxiv-2602.03304-to-search-or-not.txt`, abstract |
| Estimate how much is still unfound from the overlap of two independent searches (capture-mark-recapture) | Kastner et al. 2007 "Estimating the Horizon of Articles to Decide When to Stop Searching" | `kastner-2007-horizon-estimate.md` L51 |
| Look up unknown terms coarse to fine: encyclopedia → specialist encyclopedia → textbooks and lecture notes → surveys → original papers | Sho Yokoi 2017 "Examine the meaning of unknown terms" (Speaker Deck) | `eumesy-unknown-terms.md` L343-373 |
| Pick the next lead by information scent | Pirolli & Card 1999 "Information foraging" (paywalled, DOI 10.1037/0033-295x.106.4.643) | Not obtained; for an application to LLMs, see `arxiv-2505.09316-scent-of-knowledge.txt` |

## What the trials showed about the process

- Search-result URLs go stale: 5 of 11 were 404s, login walls, or HTML posing as PDF. So `fetch.py` judges by content.
- Across the references of three papers on LLM search agents, studies of human information seeking (Bates, Kuhlthau, Ellis, Marchionini) appear zero times, and information foraging theory once. The AI side barely uses this work.
- OpenAlex full-text search (`search=`) ranks explainer articles first; restricting to titles and sorting by citations puts the paper itself first. Registered titles sometimes lack the subtitle, so DOI comes first.
- Searchers fill in "not searched" reliably, and it serves directly as the next round's leads.

## Standard works not yet read (add them when reached)

- Pirolli & Card 1999 (paywalled); Marchionini 2006 "Exploratory search" (paywalled)
- Case & Given 2016 "Looking for Information", a textbook on information-seeking research, near the top of OpenAlex works citing Bates and Kuhlthau
- Wilson 1999 "Models in information behaviour research"; Booth 2010 "How much searching is enough?"; TARCiS 2024 (guidance on citation searching)

## Three trial topics (2026-10-09)

- The topics: research on how people search (done by the parent, by hand); making AI-generated images editable (a paper-heavy field, run twice); continent painting (no papers, only personal posts).
- Claims phrased only as "there is …" filled in one round, and the search stopped with the core of the request unchecked. Hence: one claim carries the request's condition verbatim, and at least half need a source to answer.
- In paper-heavy fields, chain.py works for older papers but not for ones about a year old.
- In the personal-posts field, chain.py and DOIs were useless; only fetch.py and WebSearch helped. Standard search came up nearly empty, then extended search surfaced everything at once. The important material sits behind the login walls of X, pixiv, and Xiaohongshu.
- Short Japanese articles can be genuine (one was 2,904 characters), and the 3,000-character floor set for English papers dropped them.
- Searcher reports rest on search snippets; one described Type-R differently from the source.
