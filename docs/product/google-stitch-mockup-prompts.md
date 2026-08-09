# Google Stitch mockup brief for Uzbekistan OS

Status: MVP page-generation brief
Last updated: 2026-08-08
Visual specification: [`design.md`](../../design.md)
Product flows: [`launch-workflows.md`](./launch-workflows.md)

## How to use this document

1. Start a Google Stitch project with the shared project prompt below.
2. Generate one page at a time using the matching page prompt.
3. For a guided workflow, first use one of the six shared workflow-screen
   prompts, then append the relevant workflow addendum from section 4.
4. Ask Stitch for a 1440px desktop view and a 390px mobile view of every
   customer-facing page. Add a 768px tablet view for workflows, search,
   knowledge, conversation, and admin pages.
5. Keep English copy in the first mockup, but leave enough space for Uzbek and
   Russian strings to expand by at least 40%.

The prompts describe information architecture and visual intent. They must not
be interpreted as permission to invent government rules, official seals,
eligibility answers, deadlines, fees, or source claims.

## 1. Shared project prompt

Paste this once as the project-level direction before generating individual
pages:

> Design a responsive web application called Uzbekistan OS. It helps visitors,
> foreign residents, students, workers, founders, and families navigate official
> procedures in Uzbekistan through evidence-backed guidance, AI-assisted search,
> and personalized step-by-step workflows. The design combines Apple Human
> Interface Guidelines with an original editorial visual language inspired by
> Wolverine Worldwide: oversized tightly tracked headlines, confident black and
> white contrast, restrained civic blue accents, generous negative space,
> asymmetric 12-column desktop layouts, rounded cinematic media, and subtle
> directional animation. Do not copy Wolverine Worldwide's font, images, logo,
> page composition, or code.
>
> Use a platform-native multilingual sans-serif stack with Noto Sans fallback.
> Use near-black #0B0D0F, white #FFFFFF, paper gray #F5F6F8, primary civic blue
> #0668D7, and supporting turquoise #0C8F91. Use blue only for actions, links,
> focus, and active progress. Use 14px control radii, 20–24px panel radii, thin
> neutral borders, minimal shadows, and 44px minimum interactive targets.
> Support equally complete light and dark themes.
>
> Marketing and discovery pages may use large editorial type, documentary
> photography of contemporary life in Uzbekistan, asymmetric image placement,
> and restrained scroll reveals. Guided tasks, knowledge pages, account pages,
> and administration screens must be calmer, denser, and highly predictable.
> Every procedural answer must make its official source, applicability,
> freshness, and uncertainty visible. Never imply government endorsement.
>
> Use a 12-column desktop grid with 20px gutters and 32–48px margins, an
> 8-column tablet grid, and a single-column mobile layout with 12px margins.
> Keep procedural reading width between 640px and 736px. Use one dominant action
> per screen, sentence-case labels, plain language, visible focus, semantic
> hierarchy, WCAG 2.2 AA contrast, reduced-motion behavior, and layouts that
> reflow at 400% zoom. Design for English, Uzbek, and Russian. Do not add voice,
> OCR, payments, appointments, reminders, native-app patterns, user document
> storage, or direct government API features.

## 2. Shared application shell

Apply this shell to all public product screens:

> Create a responsive Uzbekistan OS application shell. On desktop, use a clear
> wordmark at the upper left, primary navigation for Ask, Explore, Workflows, and
> My activity, and separate language, appearance, and account controls at the
> upper right. On mobile, use a compact wordmark, a labelled Menu button, and a
> simple bottom navigation for Home, Search, Workflows, History, and Profile.
> Include a skip link, visible current-page state, a persistent main landmark,
> and a global error area below the page title. Discovery pages may use a
> floating condensed header over media; task pages must use an opaque, stable
> header. Keep the reading order identical across breakpoints.

The administration area uses its own shell described in section 7.

## 3. Public discovery and knowledge pages

### 3.1 Home — `/`

> Design the Uzbekistan OS home page as a confident editorial entry point to a
> trustworthy civic-navigation product. Begin with a cinematic inset hero using
> a privacy-safe contemporary Uzbekistan image or muted video, a short oversized
> headline such as “Know what comes next,” a one-sentence explanation, and a
> prominent natural-language question field with an Ask button. Follow with a
> small urgent-actions strip, an asymmetric presentation of the five product
> domains, a curated row of high-priority workflows, and a black or near-black
> trust chapter explaining official sources, citations, and freshness. End with
> a restrained multilingual footer containing help, privacy, accessibility, and
> source-policy links. Avoid a generic grid of equally weighted cards; create a
> clear narrative from question to workflow to evidence.

### 3.2 Immigration domain — `/domains/immigration`

> Design an Immigration landing page with a large editorial headline focused on
> entering, staying, working, studying, registering, and leaving legally and
> confidently. Use one documentary arrival or border-processing image, a short
> domain explanation, and prominent entry points for Visa Eligibility, Arrival
> & Entry, Foreigner Registration, Temporary Residence, Extend Your Stay, and
> Leaving Uzbekistan. Include “common moments” organized as Before travel, On
> arrival, During your stay, and Before departure. Finish with source coverage,
> latest review information, and a clear notice that the product provides
> sourced guidance rather than legal representation.

### 3.3 Tourism domain — `/domains/tourism`

> Design a Tourism landing page for short-term visitors who need practical
> arrival and departure guidance rather than destination marketing. Use a warm
> contemporary travel image, a concise oversized headline, and quick access to
> Arrival & Entry, Visa Eligibility, Foreigner Registration, Healthcare,
> Importing Personal Belongings, and Leaving Uzbekistan. Highlight airport,
> customs, money, connectivity, registration, and emergency topics in a
> time-based journey. Keep monuments secondary to real traveler actions and
> make urgent official links easy to identify.

### 3.4 Business Registration domain — `/domains/business-registration`

> Design a Business Registration landing page for foreign founders and people
> working in Uzbekistan. Use a contemporary small-business or office image and a
> bold headline about moving from an idea to compliant operations. Prioritize
> Start an LLC and Work in Uzbekistan, with supporting links to PINFL, Banking,
> Temporary Residence, and Moving to Uzbekistan. Show a dependency map for
> formation, tax registration, banking, employment, accounting, and continuing
> compliance. Include strong evidence and date treatments because business and
> tax information is high risk.

### 3.5 Healthcare domain — `/domains/healthcare`

> Design a Healthcare landing page that puts emergencies first without creating
> alarm. Lead with a calm headline, an immediately visible emergency guidance
> panel, and a documentary healthcare image that protects patient privacy.
> Organize guidance into Emergency care, Insurance and payment expectations,
> Finding care, Private and public providers, and Vaccinations. Include the
> Healthcare workflow as the primary action and clearly state that Uzbekistan OS
> does not diagnose, prescribe, or replace a clinician. Use restrained visuals,
> strong readability, and no decorative autoplay video.

### 3.6 Everyday Living domain — `/domains/everyday-living`

> Design an Everyday Living landing page for people settling into daily life in
> Uzbekistan. Use an authentic neighborhood or home-life image and a concise
> editorial headline. Feature Moving to Uzbekistan, Open a Bank Account, Get a
> PINFL, Renting, Healthcare, and Importing Personal Belongings. Organize the
> page around First week, First month, and Ongoing responsibilities, showing
> dependencies between registration, PINFL, banking, phone, housing, and care.
> Do not include property listings, financial product rankings, transactions, or
> payment features.

### 3.7 Workflow directory — `/workflows`

> Design a searchable directory of all 15 guided workflows. Use a strong but
> compact page title, a plain-language explanation, search, and removable filters
> for domain, life moment, audience, and estimated duration. Display workflow
> cards with title, one-sentence outcome, domain, estimated steps, risk-aware
> source status, and a Start or Resume action. Highlight the most common flows
> without making others look unavailable. On mobile, place filters in a labelled
> drawer and announce the result count. Include loading, empty, partial-data, and
> error states.

### 3.8 Search — `/search`

> Design a verified-guidance search page. Place a labelled search field and
> result count at the top, with desktop filters in a left rail and mobile filters
> in an accessible drawer. Each result must show title, concise summary, domain,
> audience or applicability, language, official publisher, freshness date, and
> verification state in text. Separate knowledge results from suggested guided
> workflows without mixing their interaction patterns. Include removable filter
> chips, cursor pagination, no-result suggestions, partial-data messaging,
> offline recovery, and a clear option to ask the assistant instead.

### 3.9 Knowledge article — `/knowledge/[documentId]`

> Design a procedural knowledge article with a calm utility layout. At the top,
> show the title, direct summary, domain, audience, applicability, last verified
> date, language, and current or superseded status. Structure the body into
> Requirements, Ordered steps, Documents, Deadlines, Fees, Exceptions, and What
> to do next, showing claim-level citations beside the content they support. On
> desktop, add a sticky “On this page” rail; on mobile, use a labelled disclosure.
> End with official sources, related workflows, and a section-specific Report an
> issue action. Prominently warn before affected content if evidence is expired,
> conflicting, or incomplete.

### 3.10 Source detail — `/sources/[sourceId]`

> Design a source-transparency page for one official source. Show the publisher,
> source title, official URL, jurisdiction, language, content type, retrieved
> date, effective or publication date when available, verification status, and
> the specific Uzbekistan OS articles and claims supported by it. Include a
> clear external-link affordance, freshness history, and warnings for moved,
> expired, conflicting, or inaccessible material. This page should feel factual
> and audit-friendly rather than promotional.

### 3.11 How it works — `/how-it-works`

> Design an editorial explainer page showing the sequence from a user question
> to a grounded answer: understand the need, identify applicability, retrieve
> eligible official knowledge, validate claims and citations, present the answer,
> and recommend a workflow. Use a simple visual timeline, short sections, and
> example UI fragments rather than technical architecture diagrams. Explain the
> difference between search, assistant conversations, and guided workflows.
> Include clear limitations, privacy boundaries, and a call to start a workflow.

### 3.12 Trust and sources — `/trust`

> Design a high-trust methodology page explaining which official sources are
> eligible, how documents are retrieved and reviewed, how freshness and expiry
> work, how translations are approved, and how unsupported answers fail safely.
> Use a restrained black-and-white editorial layout with small evidence-themed
> illustrations or interface details. Include sections for Source eligibility,
> Human review, Citation validation, AI limitations, Corrections, and Publication
> history. Avoid security claims or performance statistics that have not been
> approved.

## 4. Assistant and guided workflow pages

### 4.1 Assistant start — `/assistant`

> Design a focused assistant-start page with the question “What do you need help
> with?” and a large but conventional message composer. Offer 4–6 example prompts
> tied to approved workflows, a language indicator, and a short trust notice that
> answers use reviewed official sources. Show a clear distinction between asking
> a question and starting a structured workflow. Keep the page calm and avoid a
> decorative chatbot character, voice controls, document upload, or unsupported
> promises.

### 4.2 Conversation — `/assistant/[conversationId]`

> Design a responsive grounded-assistant conversation. On desktop, use a narrow
> history rail, a central message column, and an optional evidence rail; on
> mobile, keep one reading column with evidence in a bottom sheet. Distinguish
> user messages, clarification questions, sourced answers, warnings, workflow
> recommendations, and system errors. Answers should use structured sections and
> claim-level citation markers that reveal source title, publisher, date, and
> applicability. Include Stop, Retry, Copy, positive/negative feedback, and a
> persistent composer; retain drafts on connection failure. Do not make the
> interface resemble casual social messaging.

### 4.3 Conversation history — `/history`

> Design a conversation-history page grouped by Today, Previous 7 days, and
> Earlier. Provide search and filters by domain and language. Each row should show
> a user-readable title, last activity, related workflow when present, and actions
> to open, rename, or delete. Include a privacy explanation, a confirmation for
> deletion, and useful empty, loading, and error states. Keep content compact and
> accessible on mobile.

### 4.4 Workflow introduction template — `/workflows/[slug]`

> Design a workflow introduction page that makes the outcome and evidence status
> clear before collecting information. Show an editorial but concise title,
> one-sentence outcome, intended audience, estimated number of steps, information
> the user will need, what will be saved, source freshness, and important scope or
> safety limitations. Use one primary Start workflow action and quieter links to
> related knowledge. If the user has progress, replace Start with Resume and show
> the saved step. Do not ask questions on this introductory screen.

### 4.5 Workflow question template — `/workflows/[slug]/steps/[stepId]`

> Design one guided decision step in a stable 640px utility column. Show workflow
> name, “Step X of Y,” an accessible progress indicator, one direct question, a
> brief explanation of why the answer is needed, and large native answer controls.
> Include Back and Continue actions in consistent positions and a safe Exit link.
> Provide inline validation, an error summary, an “I’m not sure” route when the
> rules support it, and a contextual evidence disclosure for high-risk questions.
> Never use oversized display type inside the form.

### 4.6 Workflow review template — `/workflows/[slug]/review`

> Design an answer-review page before generating a personalized result. Group
> responses into logical sections, show each label and answer in plain text, and
> provide an explicit Edit action that returns to the correct step without losing
> later progress. Identify unanswered or conflicting information before the
> primary Generate my guidance action. Include a concise privacy statement and
> do not suggest that submitting the form sends an application to the government.

### 4.7 Workflow result template — `/workflows/[slug]/result`

> Design a personalized workflow result beginning with the direct outcome or a
> safe insufficient-evidence message. Separate Requirements, Your ordered plan,
> Deadlines, Documents, Fees, Exceptions, and Official application or escalation
> links. Attach citations to the exact claims they support and show freshness and
> applicability. Add a prominent View checklist action, a quieter Change answers
> action, and one next recommended workflow. Use warnings proportional to risk
> and never imply guaranteed eligibility or approval.

### 4.8 Checklist template — `/workflows/[slug]/checklist`

> Design a personalized checklist grouped by meaningful moments such as Before
> travel, On arrival, First week, Before renewal, or Before departure. Each item
> should show status, responsible person, prerequisite, timing, required evidence,
> and a source link when factual. Use text and icons for Completed, Current,
> Blocked, and Optional states. Include print, accessible export, and Change
> answers actions, but no reminders or calendar automation. On mobile, keep the
> current item and primary next action easy to reach without covering content.

### 4.9 My workflows — `/my/workflows`

> Design a personal workflow dashboard with In progress, Needs revalidation,
> Completed, and Archived sections. Each workflow card should show title, current
> step, progress in text, last updated date, and Resume or Review result action.
> Explain when a source change requires revalidation. Include restart and abandon
> actions behind proportional confirmation, plus a clear guest-versus-account
> continuity message. Avoid gamification and celebratory visuals for legal or
> medical tasks.

### 4.10 Workflow-specific addenda

Append one of these paragraphs to the appropriate workflow template prompt.

#### Arrival & Entry Assistant

> Tailor this workflow to a traveler arriving soon. Collect nationality, visa
> context, passport status, goods, arrival airport, connectivity, money, and
> accommodation only when needed. The result should prioritize urgency and group
> the checklist into Before departure, At the airport, Border control, and First
> days in Uzbekistan. Link to Visa Eligibility and Foreigner Registration.

#### Visa Eligibility Checker

> Tailor this workflow around citizenship, residence country, travel purpose, and
> length of stay. The result must state whether current evidence supports visa-free
> entry or a visa route, then show type, documents, dated processing information,
> fees, and an official application link. Make uncertainty and exceptions highly
> visible and link to Arrival, Study, Work, or Moving.

#### Foreigner Registration

> Tailor this workflow around hotel, short-term rental, and private-residence
> situations. Emphasize who is responsible, the deadline, required documents,
> proof of registration, and what to do if a host does not act. The result should
> use a responsibility timeline rather than a generic checklist.

#### Moving to Uzbekistan

> Tailor this workflow as a dependency-ordered relocation plan using nationality,
> reason for moving, household context, and target timeline. Connect visa,
> registration, residence, PINFL, banking, phone, apartment, healthcare, and tax
> orientation. Visually distinguish prerequisites from parallel tasks and clarify
> that tax content is general orientation.

#### Start an LLC

> Tailor this workflow to a foreign founder's activity, nationality or residency,
> ownership, and hiring plans. Organize the result into Before registration,
> Formation, Tax and banking, Employment, and Ongoing compliance. Highlight
> restricted or licensed activities without inventing requirements, and use a
> compliance timeline with dated official evidence.

#### Temporary Residence Permit

> Tailor this workflow around the applicant's eligibility basis. The result should
> show eligibility confidence, required documents, responsible application route,
> processing, dated fees, validity, and renewal window. Use a clear timeline and
> an official escalation path for unsupported cases.

#### Work in Uzbekistan

> Tailor this workflow around whether an employment offer exists and the employer
> context. Separate worker responsibilities from employer responsibilities and
> show dependencies among work authorization, residence, taxes, social insurance,
> and PINFL. Use prominent warnings against beginning regulated work without the
> required authorization.

#### Study in Uzbekistan

> Tailor this workflow around institution and acceptance status. Organize guidance
> into Before arrival, Institution responsibilities, Registration and residence,
> Extensions, and Work permissions. Link to Arrival, Renting, Banking, and
> Healthcare and make institution-specific evidence requirements clear.

#### Open a Bank Account

> Tailor this workflow to identity, residency, and PINFL context. Present a neutral
> comparison framework for banks and products using eligibility, documents, dated
> fees, accessibility, card, and mobile-banking criteria. Do not rank providers,
> advertise products, or include account-opening transactions.

#### Get a PINFL

> Tailor this workflow around who needs a PINFL and for what supported purpose.
> Explain the identifier in plain language, then present eligibility, documents,
> responsible office or channel, application sequence, processing expectation,
> and verification. Link to Banking, Work, and Start an LLC.

#### Healthcare

> Tailor this workflow around emergency status, insurance context, and type of
> care needed without asking for a diagnosis. Put emergency escalation before all
> other content, then show coverage documents, neutral clinic-selection criteria,
> public and private care context, and vaccination sources. Never diagnose or
> recommend treatment.

#### Renting

> Tailor this workflow around budget, household or accessibility needs, and
> neighborhood criteria. Organize the output into Viewing, Lease review, Deposit
> and handover, Registration responsibility, and Utilities. Include warning signs
> and a link to Foreigner Registration, but do not show property listings or
> facilitate transactions.

#### Importing Personal Belongings

> Tailor this workflow around relocation status and categories of property. Create
> item groups for household goods, valuables, restricted items, and vehicles, with
> customs status, declaration evidence, dated duties or thresholds, and official
> escalation. Use strong warning hierarchy for prohibited or unsupported items.

#### Extend Your Stay

> Tailor this workflow around current immigration status, expiry date, and the
> supported extension or residence route. Make the deadline the dominant piece of
> information, followed by documents, application channel, dated fees, and
> overstay warnings. Link to Temporary Residence or Leaving Uzbekistan.

#### Leaving Uzbekistan

> Tailor this workflow as a departure checklist covering exit registration,
> outstanding fines, tax obligations, customs declaration, pets, and airport
> preparation. Group tasks into One month before, One week before, Day before,
> and At the airport. Clearly mark unresolved obligations and official escalation
> routes.

## 5. Authentication and account pages

### 5.1 Sign in — `/auth/sign-in`

> Design a compact sign-in page with a visible email field, password field when
> approved, show-password control, inline validation, and one clear Sign in
> action. Include Continue as guest and Create account as secondary choices.
> Explain that signing in preserves conversations and workflow progress. Use a
> calm opaque panel rather than a decorative hero and retain the user's intended
> destination after success or session expiry.

### 5.2 Create account — `/auth/register`

> Design a minimal account-registration page that requests only approved identity
> information. Use visible labels, autocomplete, password requirements when
> applicable, inline errors, and a concise consent explanation. Explain what an
> account saves and what it does not store, especially that Uzbekistan OS does not
> store user passports or official documents. Include Sign in and Continue as
> guest alternatives.

### 5.3 Guest upgrade — `/auth/upgrade`

> Design a consent-focused page for converting a guest session into an account.
> List the exact conversations, workflow progress, and preferences that will
> transfer, along with anything that will not. Let the user deselect optional
> transfer categories where policy allows. Use Create account and Keep using as
> guest actions with equal clarity and no coercive language.

### 5.4 Profile — `/profile`

> Design a profile page showing minimal account identity, preferred name when
> supported, language, region, and account state. Keep personal data separate from
> preferences and activity. Include edit, sign out, and account-data controls
> without requesting unrelated nationality, passport, health, or immigration
> details. Show a guest-state version that explains the benefit and limits of an
> optional account.

### 5.5 Settings — `/settings`

> Design a settings page with grouped controls for Language, Region and formats,
> Appearance, Accessibility, and Conversation preferences. Include English,
> Uzbek, and Russian; light, dark, and system appearance; reduced-motion behavior;
> and readable descriptions of each choice. Settings should save predictably and
> show success or failure in text. Do not add notification or reminder settings.

### 5.6 Data and privacy controls — `/settings/privacy`

> Design a privacy-control page explaining conversation retention, workflow
> progress, feedback, and analytics consent in plain language. Provide approved
> actions to export account data, delete selected conversations, clear workflow
> progress, or request account deletion. Show the consequences and retention
> boundaries before confirmation. Separate reversible cleanup from irreversible
> account deletion and never imply that user documents are stored.

### 5.7 Saved guidance — `/saved`

> Design a saved-guidance library for bookmarked knowledge articles, source links,
> and generated checklists. Provide search and filters by type, domain, language,
> and freshness. Each item should show title, saved date, current verification or
> revalidation state, and Open or Remove action. Warn when saved guidance has been
> superseded, and provide a link to the current version.

## 6. Help, legal, and policy pages

### 6.1 Help centre — `/help`

> Design a help centre organized around common tasks: Ask a question, Use a
> workflow, Understand citations, Manage progress, Change language or appearance,
> and Report a problem. Include a prominent help search, concise topic cards, and
> escalation information for product support. Keep official emergency and agency
> contacts visually distinct from Uzbekistan OS product support.

### 6.2 Report inaccurate guidance — `/help/report`

> Design a report form that can be opened with the relevant article, section,
> source, or conversation already identified. Ask for issue category, concise
> description, preferred language, and optional contact details. Explain what will
> be sent, prohibit sensitive personal documents, and show a clear confirmation
> with a reference number after submission. Include accessible validation and a
> safe recovery path if submission fails.

### 6.3 Privacy policy — `/legal/privacy`

> Design a readable privacy-policy page with a short plain-language summary,
> effective date, table of contents, and sections for data collected, purpose,
> retention, processors, user choices, security, international handling, children,
> and contact. Use conventional article typography and avoid oversized editorial
> treatment inside the legal text. Highlight account, guest, conversation,
> feedback, and analytics distinctions.

### 6.4 Terms of use — `/legal/terms`

> Design a readable terms page with effective date, table of contents, and clear
> sections for service scope, acceptable use, official-source limitations, no
> guarantee of eligibility or approval, account responsibilities, intellectual
> property, availability, and contact. Use restrained utility styling and make
> changes to the terms easy to identify.

### 6.5 Accessibility statement — `/accessibility`

> Design an accessibility statement describing supported standards, keyboard and
> screen-reader behavior, zoom and reflow, appearance and motion settings,
> multilingual support, known limitations, and how to request help. Include a
> prominent accessible-feedback action and expected response process without
> inventing an SLA. Demonstrate excellent typography, focus, and contrast on the
> page itself.

### 6.6 Content and translation policy — `/trust/content-policy`

> Design a transparent policy page explaining eligible official sources,
> publisher precedence, review roles, translation workflow, language status,
> freshness schedules, expiry, corrections, and safe insufficiency. Use a simple
> lifecycle diagram from source to published guidance and clearly distinguish
> source language, reviewed translation, and unavailable translation. Do not
> suggest that machine-generated procedural translations publish without review.

## 7. Administration pages

Apply this shell to all administration screens:

> Create an authenticated Uzbekistan OS administration shell using calm utility
> styling. Use a persistent desktop navigation rail for Overview, Sources, Jobs,
> Reviews, Publications, and Audit, with principal identity and role visible.
> Use a labelled mobile navigation drawer. Keep request status, authorization,
> source environment, and freshness explicit in text. Use tables only for truly
> tabular data, preserve keyboard navigation, and fail closed for unauthorized or
> stale actions. Do not use cinematic imagery, oversized marketing type, glass
> effects, or decorative animation.

### 7.1 Operations dashboard — `/admin`

> Design an ingestion-operations overview showing eligible sources, recent crawl
> and upload jobs, failures, review backlog, publications awaiting action, and
> high-level system health. Use compact metric tiles with definitions, followed by
> actionable queues rather than decorative charts. Include source search, dark
> mode, environment labels, and clear disabled states when production identity or
> source approval is not configured. Primary actions should lead to Sources,
> Jobs, or Reviews rather than performing risky operations directly.

### 7.2 Source registry — `/admin/sources`

> Design a source-registry page with search and filters for organization,
> environment, language, crawl policy, production eligibility, and health. Each
> row should show source name, official domain, adapter, policy, latest snapshot,
> latest job, and eligibility in text. Provide View source as the row action and
> only show Upload or Crawl controls where deterministic policy allows them.
> Make it explicit that source approval and registry configuration are managed as
> reviewed code changes, not editable in this UI.

### 7.3 Source detail and upload — `/admin/sources/[sourceId]`

> Design a source-detail workspace with registry metadata, official URL, adapter,
> language coverage, crawl policy, schedule, eligibility reasoning, recent
> snapshots, recent jobs, and related review items. Include separate cards for
> Queue approved crawl and Upload official document. The upload control must state
> accepted PDF, HTML, XHTML, and text types, the 10 MB limit, checksum behavior,
> and that uploaded evidence enters the same human-review pipeline. Keep ineligible
> actions disabled with a textual reason.

### 7.4 Ingestion jobs — `/admin/jobs`

> Design a filterable ingestion-job list showing job ID, source, trigger type,
> environment, status, attempts, queued and completed time, duration, documents or
> artifacts created, and error summary. Provide filters for status, source, date,
> trigger, and dead-letter state. Make retry eligibility explicit but do not offer
> a retry action unless the backend contract supports it. Include loading, empty,
> stale, and partial-failure states.

### 7.5 Job detail — `/admin/jobs/[jobId]`

> Design a technical but readable job-detail page with a lifecycle timeline,
> request and correlation IDs, source snapshot, attempts, extraction stages,
> checksums, artifact links, review items, index status, duration, cost or latency
> telemetry when available, and structured errors. Keep secrets and raw credentials
> out of the interface. Show the next permitted operation based on deterministic
> state and role.

### 7.6 Review queue — `/admin/reviews`

> Design a prioritized review queue with filters for status, risk, domain,
> language, source, freshness, and assignee. Each item should show candidate title,
> source, priority, detected change, current owner, age, and blockers. Support
> keyboard-friendly selection and a responsive list-to-detail pattern. Clearly
> distinguish pending, claimed, approved, rejected, published, and stale items.

### 7.7 Review workbench — `/admin/reviews/[reviewId]`

> Design a reviewer workbench with candidate metadata and lineage, source evidence,
> extracted structured content, side-by-side section comparison on wide screens,
> and a stacked comparison on mobile. Include Claim, Approve, and Reject actions
> with role, ownership, reason, and stale-state requirements. Publisher roles may
> also see evidence-bound Publish controls. Preserve stable identifiers, checksums,
> citations, language, and applicability throughout the interface.

### 7.8 Published record — `/admin/publications/[documentId]`

> Design a published-knowledge record showing the current version, previous
> immutable versions, source evidence package, language variants, applicability,
> effective and expiry dates, index status, and audit events. Provide role-gated
> Expire and Re-index controls with required reasons and clear consequences.
> Emphasize which version is publicly retrievable and why. Never present an
> optimistic success state before the server confirms the transition.

### 7.9 Audit history — `/admin/audit`

> Design an immutable audit-event browser with filters for date, principal, role,
> action, entity type, entity ID, environment, and result. Each event should show
> timestamp, request ID, actor, deterministic action, previous and resulting state,
> and linked entity. Provide an expandable structured-detail view and accessible
> export only if approved. This is a forensic utility page, so favor density,
> precision, and legibility over visual storytelling.

## 8. Required system and recovery states

Generate these as full-page or in-context variants using the shared shell.

### 8.1 Page not found — `404`

> Design a helpful 404 page with a direct “We couldn't find that page” message,
> Home, Search, and Browse workflows actions, and no blame-oriented copy. Keep the
> global shell and search available. Use one restrained editorial illustration or
> typographic treatment without suggesting that user data was lost.

### 8.2 Service error — `500`

> Design a service-error page stating that Uzbekistan OS could not complete the
> request. Show a request reference when safe, Retry and Return home actions, and
> product-support guidance. Do not expose technical stack details or imply that a
> procedural action succeeded.

### 8.3 Offline or interrupted connection

> Design an offline state that preserves the current draft, answers, and workflow
> inputs already available locally. Explain which content may be stale and which
> actions require reconnection. Provide Retry connection and Continue reading
> actions without automatically discarding work.

### 8.4 Session expired

> Design a session-expired state that keeps safe unsent input and returns the user
> to the same task after authentication. Explain what was preserved and provide
> Sign in and Continue as guest when supported. Never place credentials in the URL
> or imply that a failed request was saved.

### 8.5 Unauthorized or forbidden

> Design distinct unauthorized and forbidden states. Unauthorized should request
> authentication and preserve the destination; forbidden should state that the
> signed-in role cannot access the resource and offer a safe return route. Admin
> variants must show principal and environment context without revealing protected
> data.

### 8.6 Insufficient official evidence

> Design a safe-insufficiency result that clearly states Uzbekistan OS could not
> verify an answer from current eligible official sources. Show what information
> is missing, the sources checked when appropriate, an official escalation route,
> and related lower-risk guidance. Do not fill the gap with generic advice or make
> the state look like a technical failure.

### 8.7 Expired or superseded guidance

> Design an article and saved-item warning state that appears before affected
> content. State whether guidance is expired or superseded, show the relevant date,
> prevent outdated instructions from looking current, and link to the replacement
> when one exists. Keep the historical content available only when policy permits
> and label it unmistakably.

### 8.8 No search results

> Design a no-results state that repeats the query and active filters, offers
> individual filter removal, suggests broader approved terms, and provides Ask the
> assistant or Browse workflows actions. Do not fabricate popular results or hide
> the zero-result count.

### 8.9 Empty workflow history

> Design an empty My workflows state explaining what guided workflows do and what
> progress they retain. Recommend 3–4 high-value flows based on general popularity,
> not inferred personal data, and include Browse all workflows. Keep the state
> useful for both guests and account holders.

### 8.10 Interrupted assistant response

> Design an in-conversation failure state that keeps the user's message, any fully
> validated answer sections, and the draft composer. Clearly mark incomplete text,
> avoid presenting uncited partial claims as final, and provide Retry and Edit
> question actions. Focus must remain predictable for keyboard and screen-reader
> users.

### 8.11 Maintenance or degraded service

> Design a service-status message for planned maintenance or degraded search,
> assistant, workflow, or account capability. State which features remain usable,
> what may be delayed, and where to find current official information. Avoid an
> unapproved restoration estimate and provide a manual Retry action.

## 9. Internal design-system catalogue — `/design-system`

> Design an internal Uzbekistan OS design-system catalogue documenting foundations
> and production components. Include light and dark color tokens, multilingual
> typography, spacing, grid, radii, icons, motion, focus, buttons, fields, alerts,
> badges, cards, citations, evidence panels, progress, workflow questions,
> checklists, tables, drawers, and empty or error states. Show interactive states,
> mobile and desktop examples, English/Uzbek/Russian stress tests, reduced-motion
> behavior, and accessibility annotations. Make the catalogue practical for
> engineers and reviewers rather than a public marketing page.

## 10. Mockup review checklist

Before accepting a generated screen, confirm:

- The page has one dominant purpose and one primary next action.
- The layout matches editorial mode or utility mode appropriately.
- Procedural claims have visible source, freshness, and applicability treatment.
- No unapproved product capability or government interaction was invented.
- Desktop and mobile use the same logical reading order.
- Controls are at least 44px and have visible hover, focus, active, disabled,
  loading, success, and error states where applicable.
- Light and dark themes are both complete.
- The page supports English, Uzbek, and Russian expansion.
- Images are contemporary, licensed in production, privacy-safe, and not copied
  from the inspiration site.
- Reduced-motion mode remains complete and understandable.
- Empty, partial, stale, offline, unauthorized, and failure states have a useful
  next action.

## 11. Stitch generation protocol

Use this protocol to keep the generated screens coherent enough to become a
single product rather than a collection of unrelated concepts.

### 11.1 Establish context before generating screens

1. Import the repository `design.md` into the Stitch project as the design-system
   source of truth.
2. Add this mockup brief to the project context.
3. Provide the Wolverine Worldwide URL only as inspiration context. Explicitly
   instruct Stitch not to copy its assets, font, logo, wording, or page structure.
4. Do not combine unrelated visual references. Uzbekistan OS must have one clear
   visual direction.
5. Keep factual government content labelled as illustrative until it is supplied
   from reviewed Uzbekistan OS knowledge.

Use this context instruction:

> Treat the imported Uzbekistan OS `design.md` as authoritative. The reference
> website communicates editorial confidence, not a component library to copy.
> Reuse Uzbekistan OS tokens, component patterns, navigation, and content rules
> across every screen. If a page prompt conflicts with `design.md`, follow
> `design.md` and identify the conflict rather than silently inventing a new rule.

### 11.2 Generate five anchor screens first

Generate and approve these screens before producing the complete inventory:

1. Home page — establishes editorial mode.
2. Workflow question — establishes form and task behavior.
3. Knowledge article — establishes evidence and citation presentation.
4. Assistant conversation — establishes AI answer and source behavior.
5. Admin review workbench — establishes dense operational mode.

For each anchor, request three meaningfully different layout directions while
keeping the same tokens and content hierarchy. Select one direction, then ask
Stitch to reconcile the best ideas into a single approved screen. Do not generate
the remaining pages until these five agree on typography, navigation, controls,
radii, citation treatment, and responsive behavior.

### 11.3 Lock reusable components

After approving the anchors, ask Stitch to identify and reuse these named
components across the project:

- Public header and mobile navigation
- Admin navigation rail
- Primary, secondary, text, and destructive buttons
- Search field and filter drawer
- Workflow entry card
- Workflow progress header
- Question and answer controls
- Grounded answer section
- Citation marker and evidence drawer
- Source and freshness badge
- Warning, insufficiency, expired, and error alerts
- Checklist item
- Knowledge result card
- Conversation message group
- Data table, filter bar, and details panel
- Empty, loading, offline, and unauthorized state

Use this instruction:

> Reuse approved components and tokens. Do not redraw a control differently on
> each page. If a new component is necessary, explain why an existing component
> cannot serve the need, then add the smallest reusable variant.

### 11.4 Generate page families, not isolated pages

Generate in this order:

1. Shared shell and global states.
2. Five domain landings from the approved domain template.
3. Workflow introduction, question, review, result, checklist, and My workflows.
4. Apply the 15 workflow addenda without changing the workflow layout system.
5. Search, knowledge, source, trust, and help pages.
6. Assistant and conversation history.
7. Authentication, profile, settings, privacy, and saved guidance.
8. Admin sources, jobs, reviews, publications, and audit.
9. Legal pages and remaining recovery states.

When generating related screens, keep them together on the same canvas and name
frames with their route and viewport, for example:

```text
Home / Desktop / Light
Home / Mobile / Light
Home / Desktop / Dark
Workflow Step / Mobile / Error
Knowledge Article / Desktop / Expired
```

### 11.5 Control every generation request

Append this block to every page prompt:

> Generate a high-fidelity product mockup, not a mood board. Use the approved
> Uzbekistan OS design system and existing components. Show realistic but clearly
> illustrative UI copy; do not use lorem ipsum and do not invent official rules,
> deadlines, fees, endorsements, seals, or eligibility results. Include the
> default, loading, empty or insufficient, error, and disabled states relevant to
> this page. Preserve the same content hierarchy at desktop and mobile sizes.
> Annotate important interaction behavior, responsive changes, accessibility
> requirements, and any assumption that needs product approval.

### 11.6 Request responsive variants explicitly

For every customer-facing page, request:

- Desktop at 1440px width
- Mobile at 390px width
- Light and dark appearance

Also request tablet at 768px for:

- Search and filters
- Knowledge articles
- Assistant conversations
- Workflow question, review, result, and checklist
- Admin dashboard, queue, comparison, and data tables

Use this instruction:

> Do not scale the desktop canvas down to create mobile. Recompose it into the
> approved mobile reading order. Collapse contextual rails into labelled drawers
> or sheets, preserve 44px targets, avoid horizontal scrolling, and keep the
> primary action reachable without covering errors or final content.

### 11.7 Generate content and language stress tests

After approving the English default, generate at least these stress variants:

- A long Russian page title and long control labels
- Uzbek text containing apostrophe forms
- A result with several citations and a high-risk warning
- An article with an expired-source notice
- A workflow with a blocked prerequisite
- A search with zero results and multiple active filters
- A conversation with an interrupted response
- An admin table with long identifiers and a failed job

Ask Stitch not to solve text overflow by shrinking body text below the design
minimum or truncating legally important content.

### 11.8 Direct imagery carefully

Use reference images only to establish framing, tone, lighting, and composition.
Production images must be independently licensed or created for Uzbekistan OS.

Use this instruction:

> Use contemporary documentary imagery showing real actions in Uzbekistan:
> arriving, registering, studying, working, receiving care, opening a business,
> or settling into a home. Avoid generic travel advertising, monuments as the
> primary subject, official seals, staged political imagery, exposed personal
> documents, and copied reference-site photography. Keep faces and important
> actions clear of text overlays and specify an intentional crop and focal point.

### 11.9 Refine with atomic requests

Make one class of change at a time. Good refinement prompts include:

- “Keep the structure and components; reduce the hero headline by one scale.”
- “Preserve the desktop design; improve the 390px reading order.”
- “Use the approved evidence card instead of inventing a new citation pattern.”
- “Show loading, expired, and insufficient-evidence variants of this screen.”
- “Replace decorative gradients with documentary imagery and neutral surfaces.”
- “Increase Russian label capacity without shrinking control text.”
- “Remove the unapproved upload, payment, and reminder controls.”

Avoid broad instructions such as “make it better,” “make it more Apple,” or
“make it like Wolverine.” They encourage uncontrolled visual drift.

### 11.10 Build and test prototypes

Connect approved frames into these minimum interactive prototypes:

1. Home → Workflow directory → Workflow introduction → Question → Review →
   Result → Checklist.
2. Home → Ask → Conversation → Open citation → Knowledge article → Source.
3. Search → Filters → Knowledge article → Report inaccurate guidance.
4. Guest workflow → Save progress → Guest upgrade → My workflows.
5. Admin dashboard → Source → Job → Review workbench → Publication record.

Test back navigation, editing an earlier answer, interrupted responses, expired
sessions, mobile drawers, keyboard focus order, and a source that becomes stale.
Do not let prototype links imply that a government application, payment, upload,
or appointment is completed by Uzbekistan OS.

### 11.11 Export and handoff

- Export approved screens to Figma for design review and component cleanup.
- Preserve route and viewport names during export.
- Treat generated frontend code as a visual reference, not production-ready
  application code.
- Reconcile exported values with `packages/design-system/tokens.css`; do not add
  page-specific literals when a semantic token exists.
- Record unresolved assumptions and product decisions beside the relevant frame.
- Do not begin implementation until the anchor screens, responsive variants,
  dark mode, language stress tests, and critical states pass review.
