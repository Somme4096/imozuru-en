# What imozuru rests on

Which source, and which part of it, each rule in SKILL.md comes from. The sources were saved with this skill itself in a 2026-10-09 trial
(topic: research on how people search). Line numbers refer to the .txt / .md produced by saving the URLs below with `scripts/fetch.py`
(PDFs via `pdftotext -layout`, HTML via ax. A different conversion shifts the line numbers, so search by the short quotes).
Before changing a rule, reread the original passage here first.

## Where to get the sources

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

## Rules and their sources

| Rule | Source | Location in the source |
|---|---|---|
| The question changes as you search. You gather the pieces you pick up along the way | Bates 1989 "The design of browsing and berrypicking techniques for the online search interface" | `bates-1989-berrypicking.txt` |
| Six moves for following leads (backward, forward, journal run, area scanning, subject indexes, author) | Bates 1989 | same, L295-355 |
| Following citations sidesteps the problem of putting a subject into words | Bates 1989 | same, L297-302 |
| starting / chaining / browsing / differentiating / monitoring / extracting | Ellis 1987 PhD thesis (the basis of the 1989 JoD paper; the paper itself is paywalled) | `ellis-1987-phd-behavioural-model.txt` L64, contents L165-276 |
| Confusion at the start of a search is normal. Detailed notes invite premature closure. List the facts that seem to fit | Kuhlthau 1991 "Inside the Search Process" | `kuhlthau-1991-inside-search-process.txt` L345-368 |
| Committing to one direction makes later searches reinforce the same path. Branch into hypotheses and compare before moving on | Zhou et al. 2026 "Explore Before Committing" (HypoSearch) arXiv 2609.01294 | `arxiv-2609.01294-explore-before-committing.txt`, abstract at the top |
| When to stop is not confidence but whether evidence supports every needed claim | Roh & Han 2026 "HALT" arXiv 2608.02009 | `arxiv-2608.02009-halt.txt`, abstract |
| Two kinds of error: over-search, continuing when there is enough, and under-search, quitting early and missing | Zhang et al. 2026 "To Search or Not to Search" arXiv 2602.03304 | `arxiv-2602.03304-to-search-or-not.txt`, abstract |
| Estimate the total not yet found from the overlap between two independent searches (capture-mark-recapture) | Kastner et al. 2007 "Estimating the Horizon of Articles to Decide When to Stop Searching" | `kastner-2007-horizon-estimate.md` L51 |
| Look up unknown terms from coarse to fine: encyclopedia → specialist encyclopedia → textbooks and lecture notes → surveys → original papers | Sho Yokoi 2017 "Examine the meaning of unknown terms" (Speaker Deck) | `eumesy-unknown-terms.md` L343-373 |
| Choose where to go next by information scent | Pirolli & Card 1999 "Information foraging" (paywalled, DOI 10.1037/0033-295x.106.4.643) | Not obtained. An example applied to LLMs is `arxiv-2505.09316-scent-of-knowledge.txt` |

## Facts about the process learned in trials

- URLs from search results go stale. 5 of 11 were 404s, login walls, or HTML posing as PDF → `fetch.py` looks at the content to decide
- The references of three papers on LLM search agents cite zero studies of human information seeking (Bates, Kuhlthau, Ellis, Marchionini) and only one on information foraging theory. The AI side makes almost no use of this body of work
- In OpenAlex title search, full-text search (`search=`) puts explainer articles on top. Restricting to titles and sorting by citation count puts the paper itself first. But the registered title sometimes lacks the subtitle → DOI takes top priority
- Searcher subagents write the "not searched" section properly. It becomes the list of leads for the next round as-is

## Standard works not yet read (add when reached)

- Pirolli & Card 1999 (paywalled) / Marchionini 2006 "Exploratory search" (paywalled)
- Case & Given 2016 "Looking for Information" (a textbook on information-seeking research; near the top of OpenAlex papers citing Bates and Kuhlthau)
- Wilson 1999 "Models in information behaviour research" / Booth 2010 "How much searching is enough?" / TARCiS 2024 (guidance on citation-following search)

## What three trial topics showed (2026-10-09)

- Topics: research on how people search (by the parent, by hand) / making AI-generated images editable (a paper-heavy field, twice) / continent painting (a field with no papers, only personal posts)
- Listing claims as "there is ..." alone fills them in one round and stops with the core of the request missing → one claim carries the request's condition verbatim, and more than half take a form that can't be answered without reading a source
- In paper-heavy fields, chain.py works on older papers but not on new ones (about a year old)
- In the personal-posts field, neither chain.py nor DOIs were usable, and the only tools were fetch.py and WebSearch. Standard search came up almost empty, and extended search turned everything up at once. The important content gathers behind the login walls of X, pixiv, and Xiaohongshu
- Japanese articles are real even when short (2,904 characters). The 3,000-character floor meant for English papers drops them
- Searcher reports are based on search-result snippets. Their description of Type-R differed from the source
