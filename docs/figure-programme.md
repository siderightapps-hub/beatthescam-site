# The guide-figure programme

Written 2026-08-01, after the first six figures shipped (`#84`) and the gate gap they
exposed was closed (`#85`).

## State

| | |
|---|---|
| Public guides | 184 |
| With a figure | 6 |
| Without | 178 |
| Renderer | done — `build.render_guide_figure()`, no further code needed |

The remaining work is **entirely editorial**. Nothing is blocked on code.

## The gate gap, and why it is the reason this doc exists

`figure` shipped on 2026-08-01 and for one day **nothing in the gate read it**. Figure title,
alt text, caption and per-step sentences are published, reader-visible prose — and the alt
text is the *only* version of the diagram a screen-reader user gets. A figure could have
named an invented number, a retired brand, or routed a Cifas matter via Report Fraud, and
every suite would have stayed green.

`_post_text`'s own docstring already carried the rule this broke: *"Any new reader-visible
field MUST be added here at the same time it is rendered."*

Closing it caught a real defect in the six on the first run — `hsbc-bank-scam-call-uk` said a
different phone *"removes the risk of a held-open line entirely"*, an absolute
risk-elimination claim of exactly the class the site blocks elsewhere. Six hand-written,
hand-reviewed figures produced one BLOCK. **That rate is the argument for not scaling this
without the gate.**

Figure text now reaches `_post_text`, `_route_fields`, `check_text_wellformed` and
`_body_words` via one generator, `content_gate._figure_fields()`. A future renderer has one
place to hook into rather than four field lists to remember.

## Triage: the heuristic was tried and does not work

A keyword pass (ordering cues like *first/then/next*, decision cues like *if/check/never*)
split the 178 into 82 "prose already carries an ordered procedure" and 96 "weaker". **Do not
use that split.** Two spot-checks from the "weak" pile show it measures signposting, not
structure:

- **`vinted-scam-warning-uk`** scored zero ordering cues and is one of the most figure-ready
  guides in the corpus. It has a single root-cause test — *is anyone pushing you off the
  app?* — that resolves both the buyer and the seller case. It simply never writes the word
  "first".
- **`fake-wifi-hotspot-scam-uk`** scored lowest overall, and here the low score is *right*,
  but for a reason the heuristic cannot see: the guide's substance is a nuance — HTTPS
  materially limits what an attacker reads **but does not validate the hotspot**. Three boxes
  would flatten that into "HTTPS = safe", which is worse than no figure.

So the triage question is not *does this guide contain an ordered procedure?* It is:

> **Does flattening this guide into three or four boxes preserve its point, or damage it?**

That is a judgement made by reading the guide, at authoring time, inside the tranche. It is
not precomputable, and a precomputed list would give false confidence.

## What makes it tractable

Every one of the 178 already has a **verdict-first 35–60-word `quick_answer`**. The figure is
that quick answer expressed as an ordered ladder — the editorial judgement of "what matters
most, stated first" has already been made and reviewed per guide. The author starts from
that, not from a blank page.

Guide length is not a constraint: median body is 671 words and only 6 guides are under 400.

## Suggested tranche order

Fifteen per tranche (the established batch size), highest-value first:

| Order | Categories | Guides | Why |
|---|---|---|---|
| 1–3 | sms 21, marketplace 15 | 36 | The two proven verticals |
| 4–5 | payment 12, phone 12 | 24 | Highest per-incident harm |
| 6–8 | email 15, travel 14 | 29 | Large, and seasonally live |
| 9–12 | website 12, finance 11, government 10, tech 10 | 43 | Mixed; tech needs the most care (see fake-wifi above) |
| 13–15 | fraud 9, crypto 8, employment 7, social 7, shopping 7, dating 6, utility 2 | 46 | Long tail |

## Rules for authoring a figure

Learned from the first six and the BLOCK the gate caught:

1. **No absolutes.** "Removes the risk entirely", "completely safe", "always works" — the
   gate blocks these and it is right to. State the mechanism instead: *a scammer can only
   hold open the line they called you on.*
2. **Never template.** Same three checks with the brand swapped across 178 pages is the
   cookie-cutter duplication this site spent a programme removing, placed in the most
   prominent element on the page. Figure words now count toward `_body_words`, so a templated
   figure raises the similarity it actually causes.
3. **Safety ordering beats scam ordering.** `smart-meter-scam-call-uk` puts *"if you smell
   gas, call 0800 111 999"* ahead of any scam concern. Get this wrong and the diagram is
   actively dangerous.
4. **The figure must agree with the guide's prose and quick answer**, or the page contradicts
   itself in its most visible element.
5. **Alt text is the content, not a label.** Write the whole ladder into `alt` — it is what a
   screen-reader user gets instead of the diagram.
6. **Skip the guide if flattening damages it.** A missing figure costs nothing. A figure that
   oversimplifies a security nuance costs a reader.
7. **A figure missing `title`, `alt` or `steps` renders nothing** — deliberate, so a
   half-finished record cannot ship an image no one can describe.

## Scale

Roughly twelve tranches. This is weeks of work, not a sitting, and it is the largest
remaining item on the site's backlog.
