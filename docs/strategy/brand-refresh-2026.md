# Uzbekistan OS brand refresh: strategy and direction

Status: direction approved by the owner on 2026-10-28 (decisions recorded in section 10)
Date: 2026-10-28
Author: prepared for Laziz (owner, uzbekistanos.com)
Scope: brand positioning, audience, site direction, content and AI-citation strategy, lead generation. Website implementation and the marketing calendar follow as separate workstreams.

---

## 1. Executive summary

Uzbekistan OS today is a government-procedure product wearing a travel domain name. The homepage sells an account-gated visa planner, the assistant is visa-only and hidden from crawlers, and the design reads as a fintech or e-government portal. Underneath that, the editorial system is unusually strong: 13 English travel guides with Uzbek and Russian editions, every claim dated and tied to an official source, Markdown editions for machines, JSON-LD, hreflang, llms.txt, RSS, and a review-and-publish workflow with an audit trail. That machinery is exactly what AI answer engines reward, and no competitor in the English-language Uzbekistan space has it.

The market opportunity is real but narrow. Uzbekistan recorded 11.7M foreign arrivals in 2025, yet roughly 80% came from neighbouring countries and only about 16% travelled for leisure. The Western leisure segment is small (tens of thousands per country per year) but growing 2.5x to 3x since 2022, the US became visa-free on 1 January 2026, and new European and Gulf flights plus the Khiva high-speed rail link are lowering friction. The English-language information market is served by one stale independent (Caravanistan), several operators with sales bias and stale rules (Advantour, Eurasia Travel), a weak official portal, and bloggers. Nobody is simultaneously fresh, independent, and authoritative on rules. That is the position to take.

**Approved direction in one line:** Uzbekistan OS, operated by Kebab Travel, becomes the independent, continuously verified reference for travelling in and living in Uzbekistan, written by a Tashkent-based team, with a clearly labelled Kebab Travel trip-planning service as the lead engine.

**Three strategic bets:**

1. **Verified freshness is the brand.** Every rules page carries a visible "Last verified" date, a quoted official source, and a change log. Monthly verification sweeps become a published ritual, not a back-office task. This is the single strongest lever for both human trust and AI citation.
2. **Editorial independence sells more trips than a sales pitch.** The media brand stays neutral and non-promotional; the trip service is a labelled, separate surface. Trust earned on the guide converts on the inquiry form.
3. **Authority is earned off-site too.** AI mention share correlates far more with YouTube and third-party brand mentions than with backlinks. The plan includes a deliberate off-site programme (Reddit, Wikivoyage, YouTube, press hooks), not just on-site SEO.

---

## 2. What is built today (audit summary)

### 2.1 Product and brand surface

| Area | Current state |
| --- | --- |
| Brand name and tagline | "Uzbekistan OS" with "Trusted guides for visiting, living and business". OG tagline "Uzbekistan, explained clearly." |
| Homepage | Visa product. H1 "Find the right visa for Uzbekistan", 15 sections almost all about visa routes, categories, checklists, and overstay. Only CTA is "Create free account". |
| Visual system | iOS-style black pills, white, blue accent, one Tashkent skyline photo. 1,861 lines of hardcoded hex in `globals.css`, light-only, Inter referenced but not bundled. A separate token system with dark mode exists in `packages/design-system/tokens.css` but public pages do not use it. No logo asset, no destination imagery. |
| Assistant (`/chat`) | Login-required, noindex, 11 visa workflows, knowledge from gov.uz, e-visa.gov.uz, my.gov.uz. No tourism flow. A legacy pipeline in `apps/web/lib/visa-ai.ts` is dead code. |
| Lead capture | None. No newsletter, contact form, inquiry CTA, WhatsApp/Telegram, or social links. Only `info@uzbekistanos.com` in legal footers. |
| Localization | English-first chrome; articles in en, uz, ru via translation groups with hreflang. |

### 2.2 Editorial and discovery surface (the asset)

- 13 English tourism guides live (first trip, visa, best time, cost, transport, safety, Tashkent arrival, money, where to stay, SIM/eSIM, food, packing, registration), plus 6 Uzbek/Russian editions. All published 2026-10-28, around 1,700 words each, dated official quotes, CC-licensed photography with attribution.
- Per-article `BlogPosting` + `BreadcrumbList` + `FAQPage` JSON-LD, canonical, hreflang, OG image, Markdown edition at `/blog/[slug]/markdown`, `/llms.txt`, `/llms-full.txt`, RSS, dynamic sitemap.
- Content model supports content types (article, guide, platform_update, interview), five domains, structured "key takeaways" and FAQ fields, reviewed-source links, authors (bio exists; avatar and profile URL never rendered), review-due dates, opt-in RAG.
- Governed pipeline: draft → in_review → approved → published → stale/archived with audit events, role grants, and a content studio.
- Gaps: no `Organization`/`WebSite`/`Person` schema on home or index pages, no author page route, no topic or destination hubs with their own metadata, robots does not explicitly name GPTBot/ClaudeBot/PerplexityBot/Google-Extended, llms.txt still describes the site as "visa guidance", footer "Last content review" is a hardcoded string.
- Indexing: a `site:` check on Bing and DuckDuckGo returned nothing today. Expected, since everything published today, but it means Search Console, Bing Webmaster Tools, and IndexNow are not yet proven.

### 2.3 Knowledge pipeline constraints that shape the plan

- Only two approved sources exist, both Uzbek-language and manual-only (MFA visa page, e-visa localization feed). No English source is production-eligible, so the grounded assistant fails closed for most English questions.
- Guides and RAG posts must link at least one official, active source. Blogs, hotels, and airlines cannot ground retrieval unless registered as official organizations.
- Review windows: 30 days for immigration-tagged content, 180 days for tourism-only. Multi-domain content inherits the shortest window.
- Scope rules (AGENTS.md) forbid payments, bookings, appointments, native apps, reminders, autonomous agents, and government API integration. An inquiry/contact form is allowed; a booking engine is not.
- The 15 approved workflows are mostly immigration and relocation; 5 are tourism-adjacent (arrival, visa eligibility, registration, extension, departure). Repositioning requires a new scope decision per ADR 0014.

---

## 3. Market and audience

### 3.1 Demand (sources in appendix)

| Metric | Value | Note |
| --- | --- | --- |
| Foreign arrivals 2023 / 2024 / 2025 | 6.6M / 8.2M / 11.7M | Statistics Committee via kun.uz; "tourism purposes" counts all foreign visits |
| Share from neighbouring countries, 2025 | ~81% | secondary (bne IntelliNews) |
| Leisure share, 2025 | ~16.5% (~1.9M) | secondary |
| Germany / Italy / USA tourists, 2025 | ~43k / ~43k / ~37k | secondary; Jan–Sep official: 29.6k / 32.6k / 23.6k |
| France / UK tourists, 2024 | 23.4k / 21.1k | Statistics Committee via kun.uz |
| Growth vs 2022 | USA 3x, France 2.9x, UK 2.6x, Germany 2.5x | gov.uz |
| 2030 target | 15M foreign tourists, $5B tourism exports | Uzbekistan-2030 strategy |

Interpretation: the addressable Western leisure audience is on the order of 200k to 300k trips per year, growing fast from a low base, high spend, mostly first-time visitors. This is a niche where one site can realistically own the English information layer.

### 3.2 Catalysts worth building content and PR around

- US citizens visa-free 30 days since 1 January 2026; UK, EU, Canada, Australia already 30 days visa-free (verify the official MFA list before publishing).
- Etihad Abu Dhabi–Tashkent daily since August 2026; Uzbekistan Airways JFK–Tashkent 2–3x weekly; Centrum Air Frankfurt and Copenhagen announced for 2026 (launch unconfirmed).
- High-speed rail Bukhara–Urgench–Khiva from 2026 (Tashkent–Khiva from 14h to about 7h40; service start date unconfirmed); "Samarkand Express" luxury train targeted late 2026.
- Draft 2026 law tightening hotel liability for E-mehmon registration.

### 3.3 Target audience

Primary: American and Western European travellers aged roughly 35 to 70, culturally curious, Silk Road on the list, planning a first trip of 7 to 14 days, researching 2 to 9 months ahead, comfortable spending $150 to $400 per person per day. Two behaviours:

- **Independent planners.** Want rules, prices, train booking mechanics, safety nuance. They build the site's authority and traffic; a minority convert to "help me with the hard parts".
- **Assisted travellers.** Want someone trusted to design and run the trip. They are the lead-gen target. They arrive through the same questions, then look for a human.

Secondary niches with disproportionate value: photographers, textile and ceramics enthusiasts, architecture and history buffs, rail enthusiasts, Aral Sea and Karakalpakstan travellers, food travellers, solo women, travellers over 60.

### 3.4 Competitive position

| Competitor | Their strength | Their weakness, our opening |
| --- | --- | --- |
| Caravanistan | Trusted independent since 2010, forum | Uzbekistan guide last updated May 2025, routes to partner operators |
| Advantour, Eurasia Travel | Rank for visa queries, huge page counts | Sales bias, stale rules (Eurasia still says US visa-free only 55+) |
| uzbekistan.travel (official) | Authority | Promotional, thin on rules, weak English, poor freshness |
| Lonely Planet | Brand, frequently cited | Generic, inconsistent details, affiliate-heavy |
| Wikivoyage | Granular, partly updated Sep 2026 | No authorship, uneven reliability |
| Journal of Nomads, Wander-Lush | Fresh, first-hand | Episodic, affiliate, pushes own tours |

Top web results for "is Uzbekistan safe", "visa for US citizens", "best time to visit", and "10 day itinerary" are dominated by operators and bloggers. No one holds the "fresh, independent, official-sourced" position.

---

## 4. Brand strategy

### 4.1 Name decision: keep "Uzbekistan OS", change what it means

Decision (2026-10-28): keep the name and domain, presented as "Uzbekistan OS by Kebab Travel". Reasons: the domain, email, structured-data publisher identity, and 19 published URLs already carry it; the metaphor can be re-read as "the operating system for your trip", everything that has to work underneath a great holiday (entry, registration, money, trains, SIM, safety); it is short, distinctive, and memorable in a category full of "-tour" and "-travel" names. The risk is that "OS" reads as software to some travellers. Mitigation: never let the name stand alone; always pair it with the descriptor "The verified guide to travelling in Uzbekistan".

If you prefer a rename, do it now before indexing takes hold. The cost after the refresh is far higher.

### 4.2 Positioning statement

For American and European travellers planning a first trip to Uzbekistan, Uzbekistan OS is the independent travel reference that verifies every rule, price, and timetable against official sources on a published date, written by people living in Tashkent. Unlike operator sites and aging blogs, it is non-promotional, continuously updated, and machine-readable, so both travellers and AI assistants can rely on it.

### 4.3 Brand pillars

1. **Verified, dated, sourced.** Every factual page shows "Last verified", the official source, and what changed. The verification log is public.
2. **Independent.** Editorial does not sell. The trip service is clearly labelled and separate. Operator and hotel recommendations follow a published methodology.
3. **From Tashkent.** A named team of authors with extensive tourism experience in Uzbekistan, each with a profile, photo, credentials, and on-the-ground observations ("we checked this at Tashkent airport on 20 October").
4. **Built for the first-timer.** Assumes nothing, explains why a rule exists, and gives the one next action.
5. **Open to machines.** Markdown editions, llms.txt, structured data, crawler access. The site wants to be quoted.

### 4.4 Voice and tone

A meticulous local friend. Calm, precise, generous with specifics, never breathless. Short sentences. Numbers and dates over adjectives. No "hidden gem", "bucket list", "magical". Admit uncertainty plainly ("we could not confirm the fine amount; here is what the decree says"). Address the reader as "you". Mention the author's own experience where it adds evidence.

Messaging hierarchy for the homepage:

- Eyebrow: "The verified guide to Uzbekistan"
- H1 options: "Plan Uzbekistan with facts that are checked, dated and sourced." / "Everything that has to work on your Uzbekistan trip, verified." / "Uzbekistan, explained clearly." (already used on OG, keeps continuity)
- Support line: "Visa rules, registration, trains, money, SIM, safety and itineraries for travellers from the US and Europe. Every page shows when we last verified it and which official source says so."
- Primary CTA: "Plan my trip with Uzbekistan OS" (inquiry). Secondary: "Start with the first-trip guide".

### 4.5 Visual direction

Keep the design thesis from `design.md` ("editorial confidence") but move the subject from civic certainty to travel certainty.

- **Palette:** anchor in Uzbek ceramics and architecture rather than Tailwind defaults. A Samarkand turquoise/cobalt primary, warm earthen neutrals (Bukhara brick, Khiva clay), ivory paper background, one accent (saffron or pomegranate) for CTAs. Dark mode derived from the same tokens. Consolidate onto `packages/design-system/tokens.css` and remove the hardcoded hex layer.
- **Type:** a display serif with character for headlines (editorial, travel-magazine feel) paired with Inter or a similar humanist sans for body, both bundled via `next/font`. Oversized headlines stay; the gov-portal pill buttons go softer.
- **Imagery:** real destination photography (Registan, Kalon minaret, Itchan Kala, Fergana ceramics, Afrosiyob train, bazaars, people). Decision: CC-licensed, attributed sets (as the guides already do) combined with Kebab Travel's own existing photo library; the owner will supply those photos. Every hub and guide gets a hero. OG images gain photography.
- **Marks:** decision: a simple typographic wordmark for "Uzbekistan OS" with a "by Kebab Travel" lockup, plus a monogram (the "U" the blog header already uses) so there is a logo file for `Organization` schema, favicons, social profiles, and YouTube.
- **Trust furniture:** a visible "Last verified" badge pattern, source cards, author card with photo, and a "How we verify" link in every footer.

### 4.6 Relationship between the media brand and the tourism business

Decision (2026-10-28): **"Uzbekistan OS by Kebab Travel"**. Kebab Travel is the operating company that runs the site and plans the tours. The site stops being a visa-assistance product and becomes a tourism-first, life-in-Uzbekistan reference.

How it works in practice:

- Publisher identity: "Uzbekistan OS by Kebab Travel" in the header lockup, footer, About page, and `Organization` schema (Kebab Travel as the organisation, Uzbekistan OS as the `WebSite` brand it publishes).
- Editorial surface: guides, fact pages, destinations, itineraries, and the Living section stay neutral and non-promotional.
- Service surface: `/trips/` presents Kebab Travel's trip design, private guides, train and hotel arrangements, transfers, and custom itineraries, with inclusions and "prices from" published and a stated response time.
- Independence policy, published on the About page: editorial does not change based on what Kebab Travel sells; the service appears on guides only in a labelled "Need help with this? Kebab Travel can arrange it" box; no affiliate links on fact pages.

This keeps the authority that drives citations while giving the lead funnel a trustworthy, disclosed home.

---

## 5. Site direction (for the website workstream)

### 5.1 Information architecture

```
/                      Home: positioning, verified-fact strip, featured guides, destinations, Plan-with-us
/plan/                 Hub: Before you go (visa, registration, money, SIM, safety, best time, cost, packing, insurance, health)
/destinations/         Hub: Tashkent, Samarkand, Bukhara, Khiva, Fergana Valley, Nukus & Aral Sea, Termez, Chimgan mountains
/getting-around/       Hub: trains (Afrosiyob, Sharq, night trains, Khiva high-speed), flights, taxis & Yandex Go, car with driver, borders
/itineraries/          Hub: 7 / 10 / 14 days; by interest (architecture, textiles, food, rail, photography); by month
/culture/              Hub: food, dress, etiquette, alcohol, bazaars, crafts, festivals (Navruz)
/facts/                "Always-current" rule pages (see 6.2)
/living/               Second pillar: moving, registration and residence, business, healthcare, banking, renting (existing civic guides)
/trips/                Plan your trip with Kebab Travel: service, inclusions, sample trips, prices from, inquiry form, how it works, testimonials
/about/                Who we are (Kebab Travel), author team profiles, methodology ("How we verify"), editorial independence, contact
/authors/[slug]        One profile per contributing author
/updates/              Public verification and change log (RSS)
/blog/                 Remains as the chronological index; existing URLs preserved
```

Decision: `/chat` and account signup keep working for existing users but are removed from the homepage and main navigation until tourism knowledge is loaded. Decision: "Living in Uzbekistan" is the second pillar in the main navigation, with its own hub, carrying the immigration, business, healthcare, and everyday-living guides; it brings expat and relocation traffic and shares the pipeline.

### 5.2 Lead-generation design

Within scope (contact and inquiry, no payments or bookings). Decision: email inquiry form is the sole lead channel at launch; messaging buttons and a newsletter are deferred.

- **Primary:** "Plan my trip" inquiry form on `/trips/` and as a contextual box in every guide. Fields: travel month, nights, party size, interests, comfort level, budget band, name, email, free text. Confirmation email with a stated response time. Submissions stored and notified to Kebab Travel (email plus a lightweight CRM or spreadsheet to start).
- **Deferred:** "Get the first-trip checklist" email capture and nurture sequence; WhatsApp/Telegram click-to-chat. Revisit once inquiry volume and response capacity are known.
- **Proof:** testimonials with names and countries, a "who you will be talking to" card from the Kebab Travel team, licence or registration number if the business has one, response-time promise.
- **Measurement:** GA4 or Plausible alongside Vercel Analytics, UTM discipline, form and click-to-chat events, lead source attribution, a simple lead-quality score.

### 5.3 Technical GEO/SEO baseline

1. Add `Organization` (logo, sameAs, contactPoint, address in Tashkent), `WebSite`, and `Person` (author) JSON-LD on all pages; `TouristDestination` on destination pages; `TouristTrip` on itineraries; `FAQPage` only where the FAQ is visible.
2. Ship `/authors/[slug]` for each contributing author with photo, credentials, and links; render avatar and profile URL everywhere; `Person` schema per author with `worksFor` Kebab Travel.
3. Hubs are real pages with metadata, in the sitemap, with curated internal links (not query filters).
4. `robots.ts`: explicitly allow GPTBot, OAI-SearchBot, ClaudeBot, Claude-SearchBot, PerplexityBot, Google-Extended, Applebot, CCBot, Bingbot. Keep `/chat`, `/account`, `/admin` disallowed.
5. Register Google Search Console and Bing Webmaster Tools; enable IndexNow on publish; submit the sitemap. Verify indexing weekly for the first two months.
6. `dateModified` must reflect real verification updates; sitemap `lastmod` must match. Add a visible "Last verified" and a "What changed" block to rules pages.
7. Update llms.txt to describe the site as a travel reference, add hubs, about, methodology, and the trips page.
8. Consolidate styling onto tokens, bundle fonts, add dark mode on public pages, keep Core Web Vitals green.
9. Remove `apps/web/lib/visa-ai.ts` and its tests; update `tests/landing-page.test.mjs`, which currently asserts the visa framing.

---

## 6. Content strategy for authority and AI citation

### 6.1 Principles (from the evidence)

- Google's guidance says AI Overviews and AI Mode need nothing beyond indexing and snippet eligibility; llms.txt is not a ranking lever. Keep it (harmless, used by some agents) but spend effort on indexing, structure, and freshness.
- The Princeton GEO study found adding quotations, statistics, and cited sources raised generative-engine visibility by roughly 28% to 43%; keyword stuffing hurt. Rules-and-numbers content with quoted decrees is the sweet spot.
- Freshness matters most for ChatGPT; roughly three quarters of AI-cited pages were updated within 12 months. "Last updated" matters more than "published".
- Ahrefs found AI brand mentions correlate strongly with YouTube mentions and branded web mentions and only weakly with backlinks.
- OpenAI's search answers require allowing OAI-SearchBot; Perplexity requires PerplexityBot.

### 6.2 Content system: four page types

1. **Fact pages (`/facts/`)**: one entity, one question, always current. "Uzbekistan visa rules for US citizens", "...for UK citizens", "...for EU citizens", "E-mehmon registration for tourists", "Uzbekistan e-visa cost and processing time", "Afrosiyob timetable and booking", "Tashkent airport SIM cards", "Uzbekistan currency and card acceptance", "Uzbekistan travel advisories by country". Structure: 40 to 60 word direct answer at the top, dated quote from the official source, key numbers in a table, "What changed" log, FAQ, related guides. Verified monthly; rule changes same week.
2. **Guides** (existing format): how-to depth, 1,500 to 2,500 words, author experience, photos. Target the question list in 6.3.
3. **Destination and itinerary pages**: practical, opinionated, with day-by-day structure, train times, and "when this is worth it". These are the pages that convert to the trip service.
4. **Original data pages**: the stats that others will cite. Monthly arrivals by country (from the Statistics Committee), exchange-rate tracker with dated bank rates, train fare and timetable tables, a "cost of a day in Uzbekistan" index updated quarterly, flight-route tracker from US/EU. Original, dated data is the most citable content a site can produce.

### 6.3 Priority question clusters (from demand research)

- Safety: safe for tourists 2026; solo women; border areas and Termez; police and passport checks; LGBTQ+ legal risk (handled with care, already done well).
- Entry: US/UK/EU visa-free 2026; 30-day extension or visa run; passport validity; registration in hotels, Airbnbs, yurts; fines.
- Money: cards vs cash; ATMs and USD; exchange rates; daily budget; tipping.
- Connectivity: airport SIM (Ucell, Beeline, Mobiuz), eSIM, VPN, IMEI registration.
- Trains: booking Afrosiyob with a foreign card, sell-out timing, Khiva high-speed, train vs flight.
- Itineraries: 7/10/14 days; days per city; is Tashkent worth it; Khiva to Bukhara options.
- Food and culture: alcohol, tap water, vegetarian, dress code, mosques, Fergana conservatism.
- Timing: best month, summer heat, winter, Navruz.
- Regions: Aral Sea from Nukus, Karakalpakstan safety, Fergana two days.
- Tours vs independent: is a guide necessary; private driver costs; reputable operators (with a methodology).

Target: 25 to 30 new English pages in the first 90 days (10 fact pages, 8 destination pages, 5 itineraries, 5 to 7 guides), then 4 to 6 per month plus the monthly verification sweep.

### 6.4 Language policy for the tourism vertical

English first. Russian and Uzbek editions stay for civic content and for pages with clear demand, but the tourism cluster should not wait on translations. Consider German as the next tourism language given Germany is the largest Western source market, but only after the English cluster is complete.

### 6.5 Freshness operations

- Monthly "verification sweep" of all fact pages against official sources, logged on `/updates/`.
- Immediate update on rule changes with a dated "Changed on" note.
- The 180-day tourism review window in the pipeline becomes 90 days for fact pages (tag them tourism-only to avoid the 30-day immigration window unless truly immigration content).
- Register the missing official sources (Tourism Committee, Customs Committee, Uzbekistan Railways, Tashkent airport, E-mehmon/my.gov.uz, Central Bank) so fact pages can link eligible sources and feed the assistant.

### 6.6 Off-site authority programme

- **Reddit:** answer r/uzbekistan, r/travel, r/solotravel questions with dated facts and a link only when it genuinely answers; the goal is accurate, mention-rich threads, not link drops.
- **Wikivoyage and Wikipedia:** correct stale entries (US visa-free, registration), citing official sources and, where appropriate, the site's dated fact pages.
- **YouTube:** short, practical videos (arrival at Tashkent airport, booking Afrosiyob, SIM at the airport, registration) with the author on camera; transcripts republished as guides.
- **Press hooks:** US visa-free, new flights, Khiva high-speed, Samarkand Express. Offer dated data and a local expert quote to travel press.
- **Forums:** Caravanistan and TripAdvisor forum answers; Google Business Profile for the trip service.
- **Partnerships:** guesthouses, guides, and train-ticket agents for data and distribution; universities and craft centres for expert quotes.

### 6.7 Measuring AI citation

Build a fixed panel of 30 prompts (from 6.3) and run them monthly in ChatGPT, Perplexity, Claude, Gemini, and Google AI Mode. Record whether uzbekistanos.com is cited, mentioned, or absent, and who is cited instead. Track alongside Search Console impressions, indexed pages, and leads. Commercial trackers (Profound, Peec, Semrush AI Toolkit) are optional once the manual panel shows movement.

---

## 7. Product scope decisions required

1. **New scope decision (ADR):** tourism becomes the primary domain and lead-generation inquiry forms are in scope. Keep the five domains; re-prioritise the 15 workflows so arrival, visa eligibility, registration, extension, and departure lead.
2. **Assistant:** decision: keep account-required and crawler-hidden, remove from public navigation and homepage; add tourism knowledge over time via opt-in RAG from published guides. Not a launch dependency for the refresh.
3. **Dead code and stale docs:** remove `apps/web/lib/visa-ai.ts`; update EXECUTION_PLAN, phase-4 acceptance, and the AI runbook, which still say there is no public chat endpoint.
4. **Open decisions D-007 (hosting) and D-008 (privacy/retention)** must be closed before collecting leads at scale: lead data is personal data and needs a retention rule and a privacy-policy update.

---

## 8. Roadmap

| Phase | Weeks | Outcome |
| --- | --- | --- |
| 0. Decide and prepare | 1 to 2 | Name and business-relationship decisions; author identity (photo, bio, credentials); brand kit (palette, type, wordmark, photo direction); Search Console, Bing, IndexNow, analytics; ADR for scope. |
| 1. Website refresh | 2 to 6 | New homepage and hubs; `/trips/` with inquiry form; `/about/` and author page; schema, robots, llms.txt, sitemap; token consolidation and dark mode; existing 13 guides re-skinned, not rewritten. |
| 2. Content sprint | 4 to 12 | 10 fact pages, 8 destination pages, 5 itineraries, first data page; monthly verification sweep starts; `/updates/` live. |
| 3. Authority and growth | 8 to 26 | YouTube series, Reddit/Wikivoyage programme, press outreach on catalysts, email nurture, second data page, German edition evaluation, monthly AI-citation panel. |

### KPIs

| Horizon | Target |
| --- | --- |
| 30 days | All public pages indexed on Google and Bing; inquiry form live; 5 fact pages verified |
| 90 days | 40+ English pages; 1,000+ monthly organic sessions; first 10 qualified inquiries; cited in at least 3 of 30 panel prompts on any engine |
| 180 days | 5,000+ monthly organic sessions; 25+ qualified inquiries per month; cited in 10 of 30 panel prompts; at least one press mention and one Wikivoyage reference |

---

## 9. Risks and how the plan handles them

- **Accuracy liability.** Verified-date pattern, official quotes, explicit "could not verify" statements, and the existing review workflow. Never state fine amounts or passport-validity rules without the source.
- **Commercial bias eroding trust.** Published independence policy; labelled service boxes; no affiliate links on fact pages.
- **Thin Western segment.** Acceptable; the goal is a dominant share of a small, high-value niche, and the segment is growing 2.5x to 3x in three years.
- **Name confusion.** Always pair the name with the descriptor; revisit after 6 months of data.
- **Sensitive topics (LGBTQ+ law, police, borders).** Keep the current factual, source-led handling; it is a differentiator.
- **Translation and review burden.** English-first for tourism; translations on demand.
- **Lead data privacy.** Close D-008, update the privacy policy, minimise fields, define retention.

---

## 10. Decisions recorded (owner, 2026-10-28)

| # | Decision | Outcome |
| --- | --- | --- |
| 1 | Brand name | Keep "Uzbekistan OS". |
| 2 | Site purpose | Fully tourism-first plus "Life in Uzbekistan"; no longer a visa-assistance product. |
| 3 | Business relationship | "Uzbekistan OS by Kebab Travel": Kebab Travel runs the site and plans the tours. |
| 4 | Authors | A team of contributing authors with extensive Uzbekistan tourism experience, each with a profile. |
| 5 | Lead channels | Email inquiry form only at launch; messaging and newsletter deferred. |
| 6 | Assistant and accounts | Keep working, hidden from public navigation and homepage. |
| 7 | Brand assets | CC-licensed attributed photos plus Kebab Travel's own photos; simple wordmark with "by Kebab Travel" lockup. |
| 8 | Living section | Second pillar in the main navigation with its own hub. |

Still to collect before the website build: author names, bios, photos, and credentials; Kebab Travel's legal details, licence number, and contact email for inquiries; the own-photo library; the trip offer list with inclusions and "prices from"; expected inquiry response time.

---

## Appendix: key sources

- Arrivals 2025 (+46.8%): https://kun.uz/en/news/2026/01/20/foreign-tourist-arrivals-to-uzbekistan-jump-by-nearly-47-percent-in-2025
- 2024 Western source markets: https://www.kun.uz/en/news/2025/02/21/uzbekistan-sees-significant-growth-in-tourist-arrivals-from-europe-and-asia
- Jan–Sep 2025 by country: https://www.kun.uz/en/news/2025/11/18/uzbekistan-sees-strong-growth-in-inbound-tourism-in-first-nine-months-of-2025
- Purpose and origin split 2025 (secondary): https://www.intellinews.com/uzbekistan-s-foreign-arrivals-jump-sixfold-from-1-9mn-in-2021-to-11-7mn-in-2025-430648/
- US visa-free from 2026: https://www.kun.uz/en/news/2025/11/03/uzbekistan-to-introduce-visa-free-regime-for-us-citizens-from-2026
- Khiva high-speed rail: https://kun.uz/en/news/2025/05/02/uzbekistan-to-launch-high-speed-trains-between-tashkent-and-khiva-in-2026
- Google AI features guidance: https://developers.google.com/search/docs/appearance/ai-features
- Princeton GEO study: https://arxiv.org/html/2311.09735v3
- Ahrefs AI brand visibility correlations: https://ahrefs.com/blog/ai-brand-visibility-correlations
- Ahrefs freshness study: https://ahrefs.com/blog/do-ai-assistants-prefer-to-cite-fresh-content
- Seer recency study 2026: https://www.seerinteractive.com/insights/study-content-recencys-impact-on-ai-visibility-in-2026
- OpenAI crawler docs: https://developers.openai.com/docs/bots
- Semrush most-cited domains: https://www.semrush.com/blog/most-cited-domains-ai/

Unverified in this research pass: full-year 2025 UK and France counts, the official MFA visa-free list text, e-visa fees on the official portal, registration fine amounts, Centrum Air launch status, Khiva high-speed start date, and actual LLM citation patterns for Uzbekistan queries (not tested in the engines).
