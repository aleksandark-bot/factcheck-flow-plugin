# Originality & Search Intent — content guidelines

> Source thinking: Grow and Convert's [Originality Nuggets](https://www.growandconvert.com/content-marketing/originality-nuggets/),
> [Specificity Strategy](https://www.growandconvert.com/content-marketing/specificity-strategy/),
> and [Mirage Content](https://www.growandconvert.com/content-marketing/mirage-content/).
> Applies to ALL Pabau content work — writing a new article, editing/restructuring an existing
> one, or reviewing one in an editorial pass. It is self-contained: every check below is
> something you run yourself, so it works the same whether you're writing ad-hoc, editing, or
> inside a command that has already gathered SERP data. Read alongside `Pabau-style-guide.md`
> and `About-Pabau.md` — this guide governs *what makes the piece worth reading and able to
> rank*; those govern *voice, product facts, and formatting*.

---

## The one rule

**Every article must clear two bars at once: it must FIT SEARCHER INTENT (the floor) AND carry
at least one ORIGINALITY NUGGET (the ceiling).**

- **Intent match is what lets us rank.** Google ranks the pages that best answer the query in
  the shape searchers expect. If we answer a different question, or in the wrong format, we lose
  — however good the writing.
- **The originality nugget is what makes us worth ranking, sharing, and linking to.** Ten pages
  already answer the query; being the eleventh identical answer earns nothing. The nugget is the
  reason a reader remembers us and a site links to us.

An article that matches intent but has no unique angle is a **me-too page**. An article with a
clever angle that ignores intent **won't rank**. We need both, every time. Grow and Convert's
blunt version: if a piece can't clear both bars, it "is likely not worth writing."

Why this matters more than length: marketers keep chasing "10X content" (Rand Fishkin) and the
"Skyscraper technique" (Brian Dean) — make it longer, more thorough, taller than the competitor.
But length is not the lever. You do **not** always need 10X content to rank, especially for
lower-competition terms. What you need is (a) to actually answer the query and (b) at least one
genuine bit of originality. A tight 1,200-word piece that nails both beats a bloated 4,000-word
piece that's a longer version of everyone else's.

**How to use this guide in order:** Section 1 (intent) is the go/no-go you resolve FIRST, from
the SERP, before outlining. Section 2 (originality) is what you design the piece around. Section
3 (specificity) and Section 4 (anti-mirage) are how you execute every section so it holds up.
Section 5 walks a full example end to end. Section 6 is the pre-save checklist.

---

## 1. Fit searcher intent — judge from the SERP (the floor, non-negotiable)

**Intent is not just "informational vs commercial."** That bucket is the coarsest layer. The
real question is: *are we answering the exact query the searcher typed, in the shape Google
rewards for it?* The keyword is a literal question. Our article has to be the answer to THAT
question — not to an adjacent one we find more interesting or easier to write.

### The four layers of intent, most important first

1. **The actual question being asked.** Read the focus keyphrase literally and say, in one
   sentence, what the searcher wants to walk away with. "How to become an aesthetic practitioner
   in the UK" → *the steps and requirements to enter the field.* "Best clinic booking software"
   → *a shortlist of tools they can choose from.* "What is SOAP note" → *a definition and an
   example.* If you can't state the wanted outcome in one sentence, re-read the query.
2. **The format that delivers that answer.** The top 10 have already been selected by Google as
   the shapes that satisfy this query. Count them. If 7 of 10 are step-by-step guides, the
   format is how-to — not a listicle, not an explainer.
3. **The broad intent bucket** (informational / commercial-investigation / transactional) — use
   it as a sanity check, not the primary driver.
4. **Depth and scope** — short focused answer vs comprehensive guide. Match the altitude the
   SERP rewards. If the winners are 800-word direct answers, a 3,000-word tome may actually hurt.

### Query pattern → expected answer shape (read the keyphrase this way)

| Query pattern | What the searcher wants | Default format |
|---|---|---|
| "how to X" / "how do I X" | A procedure they can follow now | Step-by-step how-to, in order |
| "best X" / "top X" / "X tools" | A shortlist they can choose from | Listicle, usually with criteria |
| "what is X" / "X meaning" | A clear definition + example | Definition/explainer, answer up top |
| "X vs Y" / "X or Y" | A decision between named options | Comparison, with a verdict |
| "X cost" / "X pricing" / "how much" | Real numbers and ranges | Pricing breakdown, figures early |
| "X template" / "X example" | Something to copy or download | Template/example, usable artifact |
| "X checklist" / "X requirements" | A complete list they can tick off | Structured, exhaustive list |
| "why X" | An explanation / cause | Reasoned explainer |

Treat this as guidance, not gospel — the **SERP overrides the table**. If "best X" pulls up
mostly how-to guides, Google is telling you the real intent is procedural; follow the SERP.

### How to pull the SERP (do this yourself)

You need the actual top results before you can judge intent — don't guess them.

**Already have the SERP? Reuse it — do not re-fetch.** If the flow you're running in has already
pulled the SERP for this exact keyphrase (it's in your context / an earlier step gathered it),
use that read. Only pull it yourself when you don't already have it. Otherwise get it with
whichever tool you have:

- **DataForSEO (preferred when available)** — call `serp_organic_live_advanced` with the focus
  keyphrase, `location_name` "United States", `language_code` "en", `depth` 10. This is the
  cleanest read of the real organic top 10. Available in the main Claude session.
- **WebSearch (fallback)** — if you don't have DataForSEO (e.g. inside the /fact editorial
  agent, which only has WebSearch), run a WebSearch for the exact focus keyphrase and read the
  top ~10 organic results it returns. Good enough to judge format, angle, and depth.
- **Then open a few** — click into 2–4 of the top results (WebFetch) to confirm their format and
  depth first-hand, not just from the title.

If you genuinely can't reach either tool, say so and fall back to reasoning from the query
pattern table above — but flag that the intent read is unverified.

### Step-by-step: how to read intent from the SERP

1. Pull the top 10 organic results for the focus keyphrase (see "How to pull the SERP" above).
   Drop our own domain, pure aggregators/directories, and SERP features.
2. For each result, note in one line: its **format** (how-to / listicle / comparison / etc.),
   its **angle** (what makes it distinct), and roughly its **depth**.
3. Count the formats. The majority format is the intent signal. Note the second-most-common —
   sometimes the SERP is split (e.g. half how-to, half listicle), which means either shape can
   rank and you can choose the one that suits our nugget.
4. Read the **title tags** of the top 5. Titles reveal the promise Google is rewarding — the
   angle, the number ("7 steps"), the qualifier ("for beginners", "UK"), the year. Grow and
   Convert's point: a reader can tell a boring article from the title alone. Ours shouldn't be.
5. Note SERP features: a **featured snippet** means format the direct answer as a short paragraph
   *and* a list to compete for it. **People Also Ask** boxes are free sub-questions to answer as
   H2s/FAQs. A **video pack** or **image pack** signals the query wants visual/procedural content.
6. Write one sentence: *"To rank here we must be a [format] that answers [the actual question] at
   [depth], and our unique angle will be [nugget]."* If you can't complete it, you're not ready.

### Worked example — a unique article can still be the WRONG answer

Focus keyphrase: **"how to become an aesthetic practitioner in the UK."** The searcher wants a
**how-to route** — the qualifications to get, the order to get them in, the regulations, the
timeline, the cost. Now suppose our existing article is titled *"The qualifications and skills
every aesthetic business owner should have."* It's genuinely unique and well written — but it
answers a **different question** (a list of desirable attributes) for a **different reader** (an
existing business owner, not someone trying to enter the field). This is an **intent mismatch**.
It will underperform no matter how original it is.

The fix is *not* to sprinkle in the keyword. It's a structural change: rebuild the article as
the step-by-step route the query demands ("1. Meet the entry requirements → 2. Complete a Level
4/5/7 course → 3. Get insured → 4. Register with a body → 5. Set up to practice"), and then put
our originality *inside* that route — e.g. a realistic cost-and-timeline breakdown per training
path, or the operational steps of actually opening for bookings that competitors omit.

### Second example — right topic, wrong shape

Focus keyphrase: **"clinic appointment reminder templates."** Searcher wants **copy-paste
templates** (SMS/email) they can use today. An article that's a 1,500-word essay on *why*
reminders reduce no-shows misses the intent — it explains the value of a thing the searcher has
already decided to do. The winning shape is a set of actual templates (confirmation, 24-hour
reminder, rebooking, no-show follow-up), organized by channel, with a short note on when to send
each. The nugget can be templates tuned to aesthetic/medical contexts (pre-treatment prep,
consent reminders) that generic templates lists don't have.

### On a mismatch — the decision

If our article answers a different question, or is the wrong format, the fix is **structural,
not cosmetic** — reorder, merge, split, or replace sections, or change the article type outright.
**Do not tweak keywords on the wrong skeleton; fix the shape first.** This can be a larger
rewrite than a normal edit, and that's expected. Flag it clearly: name the current shape, the
shape the SERP rewards, and what has to change. (Whatever command you're running will have its
own mechanism for authorizing a bigger restructure — use it; if you're editing directly, just
make the change.)

---

## 2. Originality Nuggets — the unique angle (THE priority)

> An originality nugget is "little bits of originality that make a piece of content unique from
> others, and thus worthy of being shared or linked to."

**Rule:** every article we write or substantially update must contain at least one originality
nugget — something no other result in the top 10 has. **Name it explicitly, in one sentence,
before you outline.** If you can't name one, the article isn't ready; go find one. This is the
single highest-leverage thing in this guide.

The nugget must sit *inside* the correct answer (Section 1). An original answer to the wrong
question still loses. You are looking for: "we answer the same query as everyone else, but we
uniquely also [nugget]."

### The three tiers, by effort

Originality is not all-or-nothing. It scales. Most Pabau updates should land at **Light →
Medium**, producible in days, not the months a heavy piece takes. Start light.

**Light originality** — a dash of creativity, little extra work:
- **A better organizing principle.** Grow and Convert's canonical example: a "lead generation
  tools" list for their client Leadfeeder ranked **#2** simply by grouping the tools **by use
  case/category** when every competitor listed them flat. Pabau parallel: a "best tools for
  aesthetic clinics" list organized by the job (booking, records, marketing, payments) instead
  of an undifferentiated 20-item list.
- **A defensible contrarian stance.** Everyone says "send more reminders to cut no-shows"; a
  piece arguing "most reminder advice backfires — here's the sequence that actually works" is
  instantly distinct (only take a contrarian line you can back up).
- **Reframing around the reader's real job.** Competitors write "features of booking software";
  we write "what actually changes in your front desk's day when booking goes online."
- **A useful sort or filter competitors skip** — by price, by practice size, by country/
  regulation, by solo-vs-multi-location.

**Medium originality** — one or more solid, original ideas (the sweet spot for us):
- **A first-person / practitioner take.** Grow and Convert's "How to Get a Marketing Job" worked
  because it was an honest first-person account with a real book list and personal stories.
  Pabau parallel: walk through a real clinic's actual switch from paper to digital records — the
  friction, the timeline, what they'd do differently.
- **A proprietary framework, checklist, or decision tree** we name and reuse — e.g. a "no-show
  cost calculator" logic, or a "paper-to-digital migration checklist" for clinics.
- **An original cut of data.** Even a small one: pull a real figure (an industry no-show rate, a
  cost range for training, a benchmark) and interpret it for the reader. Use REAL numbers with a
  source — never fabricate a statistic (it will be fact-checked downstream).
- **An expert quote or interview.** Find someone with hands-on experience (a practitioner, a
  clinic manager) and quote a specific, non-obvious insight.
- **Concrete worked examples end to end** — not "you can automate rebooking" but the actual
  rebooking flow, trigger by trigger, with the message copy.

**Heavy originality** — serious effort, hard to reproduce (rare for us; plan deliberately):
- An **original study or survey** (e.g. survey 100 clinics on their no-show rates and publish
  the distribution). Grow and Convert's example: a mobile-checkout study analyzing 40 ecommerce
  sites — months of work.
- A **benchmark or dataset** across many clinics/tools.
- An **interactive tool or calculator** (their example: a coded burn-rate calculator for client
  Pilot). Pabau parallel: an interactive no-show-cost or pricing calculator.
- These double as "10X" / "Skyscraper" pieces — reserve them for high-value head terms.

### A brainstorm palette — run through these to find an angle

When you can't immediately name a nugget, ask each of these about the topic:
1. Can we **reorganize** the standard answer by a smarter principle (use case, practice type,
   country, budget)?
2. Do we have a **real example or customer story** competitors can't access?
3. Is there a **number or benchmark** we can cite and interpret?
4. Can we take a **defensible contrarian** position against the common advice?
5. Can we add a **usable artifact** — a template, checklist, calculator, script, decision tree?
6. Can we bring a **practitioner's first-hand perspective** the SEO-blog competitors lack?
7. Can we go **one level more specific/operational** than everyone else (the actual clicks, the
   actual message copy, the actual costs)?
8. Can we cover the **step everyone omits** (e.g. what happens *after* the obvious advice)?

One strong nugget is enough. Two or three, layered, is better — but never at the cost of intent.

### Where Pabau's nuggets come from (our unfair advantages)

Generic SaaS/marketing blogs writing about clinics have never run one. We have angles they
can't touch:
- **Real practice-management and clinic/aesthetic workflows**, in the specifics competitors
  gloss over — the front-desk reality, the patient journey, the paperwork.
- **Pabau product mechanics as concrete worked examples** — show the actual flow (introduce and
  qualify Pabau per the style guide on first mention; never keyword-stuff or over-pitch; lead
  with the outcome, not the feature).
- **Real customer stories, outcomes, and objections** from the field.
- **Industry-specific detail**: compliance and consent, regulated treatments, no-show
  economics, membership/retention models, insurance, before/after photo handling.

### The intro litmus test (your fastest originality check)

The introduction reveals whether a piece has originality. **If the intro is hard to write, or
it opens generically, the piece has no nugget yet.** Fix the angle before writing the body.

Generic openers that fail the test (do not write these):
- "When it comes to [topic], there are many things to consider…"
- "In today's fast-paced world…" / "In the digital age…"
- "[Topic] is more important than ever."
- A dictionary restatement of the keyword.

A passing intro states the specific, non-obvious promise immediately. Compare:

> **Fails:** "Running an aesthetic clinic comes with many challenges. In this article, we'll
> look at how to reduce no-shows and keep your schedule full."

> **Passes:** "Most no-show advice stops at 'send a reminder.' But clinics that cut no-shows
> below 5% do three specific things the generic advice skips — here's the exact sequence, with
> the message copy and timing."

### What is NOT a nugget (don't fake it)

- Rewording a competitor's point in your own words.
- "More comprehensive" alone — length is not originality.
- A generic stat everyone already cites, with no new interpretation.
- A fabricated example, quote, or number (fails fact-check and destroys trust).
- An angle that answers a different question than the query (fails Section 1).

---

## 3. Specificity — kill the generic (applies to the topic AND inside every piece)

> The biggest reason content fails: "their topics aren't specific enough." And: "Readers have
> just become smarter" — they're tired of clickbait and regurgitated, high-level content.

Grow and Convert's sharpest line: overly broad ideas "are entire blogs," not blog posts. "How
To Get More Customers For Your Startup," "How To Create Valuable Content" — each already has
whole websites and books devoted to it, so a single post can only be "average at best." Readers
can tell from the title: generic intro → stated problem → shallow list of high-level ideas, a
few paragraphs each. That's the pattern we must never produce.

### Topic altitude — split or deepen

If a section could plausibly be its own article, that's a signal. Two responses:
- **Deepen** it in place (if the SERP for our keyword rewards a comprehensive guide).
- **Split** it into its own targeted piece (if it maps to its own keyword in our plan).

Grow and Convert's method for breaking a broad topic down:
1. **Know the high-level pain point.** Don't guess — use user research, sales-call notes, or
   support tickets if unsure.
2. **Brainstorm why people search for it.** Use the "suggested search hack" (Google autocomplete
   and "searches related to"), People Also Ask, and Q&A forums like Quora/Reddit to surface the
   real sub-questions.
3. **List every reason/sub-question and consider a detailed post on each.** Their worked case:
   "Finding and Hiring Blog Writers" broke into (a) in-house vs agency vs freelance, (b) where to
   find and how to evaluate writers, (c) how much to pay and how to manage them — three deep
   posts, later combined into a 5,000+ word mega guide. Another: a single "how a company built
   great software" interview idea broke into 10–15 specific posts; a "why am I [X]" topic broke
   into 9.

Pabau parallel: "clinic marketing" is an entire blog, not a post. Break it into the real
sub-questions — "how to get more aesthetic clients from Instagram," "reactivating lapsed patients
by SMS," "setting up a membership plan that retains clients" — and write each specifically.

**Caveat — the SERP decides breadth.** Some head keywords legitimately want a broad, organized
overview (Section 1's depth signal). When the SERP rewards breadth, provide breadth — but make
*every sub-section* specific. Breadth is not a license for shallowness.

### Within-piece specificity — the concrete-detail rule

Every section answers a specific pain point with concrete detail, not high-level platitudes.
Depth-per-section is how a specific piece out-ranks a broad one. Concrete means:
- **Real numbers** — costs, ranges, rates, timelines (sourced, never invented).
- **Named steps in order** — "click X → set Y → the system does Z," not "you can configure it."
- **Actual examples and artifacts** — the message copy, the template, the screenshot/workflow.
- **Named tools, bodies, regulations, treatments** where relevant.
- **The specific reader and situation** — "a solo injector taking bookings by DM" beats "a
  business."

Before → after (generic → specific):

> **Generic:** "Automating your reminders can help reduce no-shows and save your team time."

> **Specific:** "Set a two-message sequence: a confirmation at booking and a reminder 24 hours
> before, each with a one-tap 'confirm or reschedule' link. Clinics that add the 24-hour
> reschedule option recover slots that would otherwise have been empty no-shows — the front desk
> stops phoning round to backfill."

---

## 4. Mirage content — the anti-pattern to eliminate

> "Mirage content is content that looks good on the surface, but after giving it a deeper look,
> you realize it's nothing but high-level fluff."

Root causes (both fixable at the writing stage): (1) a writer without real experience or
concrete examples on the subject, and (2) a lack of specificity — knowing a topic deeply
naturally produces specific writing. Telltale signs: elementary/obvious advice ("Optimize your
website for search engines," "Update your content"), high-level platitudes, "high-school-essay
intros," and no real examples.

Run every draft and every section through this four-test battery. **Any failure = rewrite that
part.**

### Test 1 — Reader's-shoes / "No shit" test

Imagine our **actual buyer** reading it: a practice owner, clinic manager, or practitioner who
already runs a clinic. Do they think *"Wow, no one has ever given me this advice"* — or *"No
shit, thanks"* and bounce? Expert content **skips the basics** because the author knows the
reader already knows them.

> **Mirage:** "To reduce no-shows, make sure clients know their appointment time and send them a
> reminder." (Every clinic owner already does this. No shit.)

> **Passes:** "Reminders alone plateau around a 10–15% no-show rate. The clinics that get below
> 5% add a deposit on high-value treatments and a one-tap reschedule link — here's exactly how
> that changes the front-desk workflow." (Non-obvious, specific, respects the reader.)

### Test 2 — Real-examples test

Are claims backed by concrete, specific examples, or generic assertions? Grow and Convert's
contrast: a generic SEO-services page ("optimize your site, publish regularly") makes readers
bounce; Backlinko showing **exactly** how someone ranked #1 with real steps makes readers want
the author's product. **No examples = mirage.** If you assert a claim, show it happening.

### Test 3 — Customer-fit test

Even specific, well-written content is a mirage if it targets the **wrong reader**. Grow and
Convert's example: a referral-marketing SaaS wrote about the *benefits* of referral marketing —
but their enterprise buyers already believed in referral marketing; they needed help *executing*
it. The content was useful to *someone*, just not to the *customer*. **Judge value from our
customer's perspective, not "useful to anyone."** Don't sell the category to people who've
already bought into the category.

Pabau parallel: a piece explaining "why clinics should go digital" is a mirage for a clinic
owner who's already shopping for software — they're past the why; they need the how, the
migration path, the comparison. Meet the reader where they actually are in the journey.

### Test 4 — Specificity test

Platitudes, obvious tips, and generic intros are mirage tells. If a sentence would survive being
copied into any competitor's article on the topic, it's too generic — cut or sharpen it.

### De-mirage in practice (before → after)

> **Mirage section:** "Good record-keeping is essential for any clinic. Keeping accurate
> patient records helps you stay organized and compliant. Make sure your records are up to date
> and stored securely."

> **Rewritten:** "For regulated treatments, your records need the consent form, the batch number
> of what was injected, before-and-after photos, and the practitioner's notes — tied to one
> patient timeline. On paper that means four places to check before a follow-up; digitally it's
> one screen the practitioner opens mid-appointment. The compliance win is real, but the daily
> win is not hunting through a filing cabinet between clients."

---

## 5. Putting it together — a worked end-to-end pass

Take the keyword **"how to reduce no-shows in a clinic."**

1. **Intent read (Section 1).** SERP is mostly step-by-step how-tos plus a couple of listicles;
   a featured snippet lists tactics. The actual question: *what concrete actions reduce no-shows?*
   → Format: how-to / actionable list, direct answer near the top, snippet-friendly. Depth:
   medium, comprehensive but skimmable.
2. **Name the nugget (Section 2).** Competitors stop at "send reminders." Our medium nugget: a
   **sequenced system** (deposits on high-value treatments → confirmation at booking → 24-hour
   one-tap reschedule → same-day waitlist backfill → no-show follow-up), with the **actual
   message copy** and the front-desk workflow — plus a real no-show cost figure interpreted for
   the reader. Nothing in the top 10 shows the whole operational sequence.
3. **Outline to the intent, nugget inside.** H1 answers the query as a how-to. Key Takeaways up
   top (snippet play). H2s = the sequence steps, in order. An FAQ for the PAA questions. Our
   nugget lives across the step sections (the copy, the workflow, the number).
4. **Write each section (Sections 3–4 of this guide).** Concrete detail per step; real message
   copy; run each through the mirage battery — cut "make sure clients know their time"; keep the
   deposit mechanics and the reschedule-link workflow. Introduce Pabau once, outcome-led, where
   the automated sequence is shown. No fabricated stats.
5. **Checklist (Section 6).** Confirm intent, name the nugget in one sentence, intro passes the
   litmus test, every section specific, nothing generic survives, Pabau handled per style guide.

---

## 6. Operational checklist (before writing / restructuring, and before save)

- [ ] **Intent — right question:** I can state in one sentence what the searcher wants, and our
      article delivers exactly that (not an adjacent question).
- [ ] **Intent — right format & depth:** matches the SERP-dominant format and altitude. If we
      answer a different question or use the wrong format → structural change, not a keyword tweak.
- [ ] **Nugget named:** I can state the specific originality nugget(s) in one sentence — what we
      have that the top 10 don't — and it lives *inside* the correct answer. (If not, stop and
      find one.)
- [ ] **Intro:** passes the litmus test — specific, non-generic, easy to write.
- [ ] **Specificity — topic:** nothing that "could be its own blog" is left at surface level;
      deepen or split.
- [ ] **Specificity — sections:** every section is a concrete pain point with real
      detail/examples/numbers/steps; no platitudes survive.
- [ ] **No mirage:** passes reader's-shoes, real-examples, customer-fit, and specificity tests.
- [ ] **Honest:** every example, quote, and number is real and sourced (nothing fabricated —
      it will be fact-checked downstream).
- [ ] **Pabau:** angle uses our real advantage; product introduced/qualified per the style guide;
      no over-pitching, no feature gating; outcomes-led.

### Priority order when they tension

**Answer the right question in the right format first** (or we don't rank) → **then the
originality nugget, delivered inside that answer** (or we don't deserve to) → **then specificity
and mirage-cleanup throughout.** Never trade away the nugget to hit a word count. Never trade
away intent to force an angle — an original answer to the wrong question still loses.
