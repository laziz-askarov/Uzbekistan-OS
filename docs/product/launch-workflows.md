# Approved MVP launch workflows

Decision: D-001

Approved: 2026-08-01

These 15 workflows are the initial Uzbekistan OS product scope. They inherit the
responsive, accessibility, failure-state, privacy, and evidence criteria in
`responsive-flow-wireframes.md`. Approval selects the product flows; it does not
authorize a source, relax publication eligibility, or permit unsupported guidance.

## Shared workflow contract

Every flow must:

- collect only the context needed to determine applicability;
- explain why sensitive or personal context is requested before collection;
- express unknown, unsupported, expired, and inapplicable states explicitly;
- cite authoritative sources at the claim or step they support;
- show publisher, effective date, verification date, and freshness state;
- preserve progress without storing user documents;
- allow people to revisit decisions, correct input, and recover from interruption;
- provide a personalized checklist, next action, and relevant next workflow;
- pass mobile, tablet, desktop, keyboard, screen-reader, zoom/reflow, contrast,
  localization, and reduced-motion review before launch.

## Portfolio

| # | Workflow | Primary domains | Risk | Primary outcome |
| --- | --- | --- | --- | --- |
| 1 | Arrival & Entry Assistant | Immigration, Tourism, Everyday Living | High | Personalized entry and first-arrival checklist |
| 2 | Visa Eligibility Checker | Immigration | High | Visa requirement, type, documents, fees, and official route |
| 3 | Foreigner Registration | Immigration | High | Registration duty, responsible party, deadline, and verification |
| 4 | Moving to Uzbekistan | Cross-domain | High | Sequenced relocation plan from visa through taxes and healthcare |
| 5 | Start an LLC | Business Registration | High | Formation, tax, banking, employment, and compliance checklist |
| 6 | Temporary Residence Permit | Immigration | High | Eligibility, application, processing, fees, and renewal plan |
| 7 | Work in Uzbekistan | Immigration, Business Registration | High | Work authorization and employment compliance plan |
| 8 | Study in Uzbekistan | Immigration, Everyday Living | High | Student entry, registration, residence, extension, and work rules |
| 9 | Open a Bank Account | Everyday Living | Medium | Eligibility, documents, provider comparison, card, and mobile access |
| 10 | Get a PINFL | Everyday Living | High | PINFL eligibility, application, processing, and uses |
| 11 | Healthcare | Healthcare | High | Insurance, provider, emergency, and vaccination guidance |
| 12 | Renting | Everyday Living | Medium | Budget, location, lease, registration, utilities, and deposit plan |
| 13 | Importing Personal Belongings | Immigration, Everyday Living | High | Customs, goods, vehicle, tax, and restriction checklist |
| 14 | Extend Your Stay | Immigration | High | Extension route, documents, deadlines, and fees |
| 15 | Leaving Uzbekistan | Immigration, Tourism | High | Exit, fines, taxes, customs, pets, and airport checklist |

## 1. Arrival & Entry Assistant

Trigger: “I’m flying to Uzbekistan tomorrow.”

Decision path:

1. Nationality and passport jurisdiction.
2. Visa requirement and permitted stay.
3. Passport validity and document requirements.
4. Customs allowances and restricted items.
5. Arrival airport and border-control process.
6. SIM-card options and identity requirements.
7. Currency exchange and declaration thresholds.
8. Foreigner-registration requirement and deadline.

Outputs: personalized checklist, airport guide, customs rules, currency declaration
guidance, immigration process, and the next recommended workflow. Urgent or
unsupported cases route to an official authority rather than generating an answer.

## 2. Visa Eligibility Checker

Inputs: citizenship, residence country, travel purpose, and length of stay.

Decision path: visa required → eligible visa type → required documents → official
processing time → fees → official application channel → recommended next steps.

Outputs: eligibility result with applicability explanation, document checklist,
fee/processing range with effective date, official application link, and a route to
Arrival & Entry, Study, Work, or Moving as appropriate.

## 3. Foreigner Registration

Decision path: registration applicability → hotel, short-term rental, or private
residence → responsible registering party → statutory deadline → required documents
→ proof and verification method.

Outputs: responsible-party statement, deadline, document checklist, verification
steps, and escalation guidance when a host or accommodation provider does not act.

## 4. Moving to Uzbekistan

Inputs: nationality, reason for moving, household context, and target timeline.

Decision path: visa → foreigner registration → residence permit → PINFL → bank
account → phone → apartment → healthcare → taxes.

Outputs: dependency-ordered relocation plan, personalized milestones, prerequisites,
and links into the specialist workflows below. The flow must distinguish general
orientation from individualized legal or tax advice.

## 5. Start an LLC

Inputs: business idea, proposed activity, founder nationality/residency, ownership,
and intended hiring.

Decision path: company type → founder documents → company registration → tax
registration → bank account → employees → accounting → continuing compliance.

Outputs: formation checklist, decision explanations, official registration path,
tax/accounting obligations, renewal/reporting calendar, and evidence-backed warnings
for licensed or restricted activities.

## 6. Temporary Residence Permit

Decision path: eligibility basis → required documents → official application route
→ processing → fees → validity and renewal.

Outputs: applicability result, document checklist, dated fee/processing information,
application sequence, renewal window, and official escalation path.

## 7. Work in Uzbekistan

Input: whether an employment offer has been received and the employer context.

Decision path: work-permit applicability → employer obligations → residence permit
dependency → taxes → social insurance.

Outputs: worker and employer checklists, dependency order, authorization warnings,
tax/social-insurance orientation, and links to Residence Permit and PINFL.

## 8. Study in Uzbekistan

Input: institution and acceptance status.

Decision path: student visa → foreigner registration → residence arrangements →
visa/residence extensions → work permissions.

Outputs: pre-arrival and post-arrival student checklists, institution/host
responsibilities, deadline schedule, and links to Arrival, Renting, Banking, and
Healthcare.

## 9. Open a Bank Account

Decision path: eligibility → required identity, residency, and PINFL documents →
eligible banks/products → fees → card → mobile banking.

Outputs: eligibility and document checklist, neutral provider comparison criteria,
dated fees when authoritative, accessibility considerations, and links to PINFL.
The product must not rank providers without an approved, transparent methodology.

## 10. Get a PINFL

Decision path: what PINFL is → who needs it → required documents → responsible
office or channel → application → processing → supported uses.

Outputs: applicability explanation, document and office checklist, processing
expectation, verification method, and links to Banking, Work, and Business flows.

## 11. Healthcare

Decision path: insurance context → clinic options → emergency pathway → private
hospitals → government hospitals → vaccination guidance.

Outputs: emergency-first guidance, coverage and document checklist, neutral provider
selection criteria, vaccination source links, and clear medical-safety escalation.
The flow must not diagnose, prescribe, or replace professional medical care.

## 12. Renting

Inputs: budget, household/accessibility needs, and location preferences.

Decision path: neighborhood criteria → lease terms → foreigner registration impact
→ utilities → deposit and handover.

Outputs: viewing checklist, lease/deposit checklist, registration responsibilities,
utility setup, warning signs, and links to Foreigner Registration. Listings and
transactions remain out of MVP scope.

## 13. Importing Personal Belongings

Input: relocation status and categories of property.

Decision path: customs status → household goods → vehicle rules → duties/taxes →
prohibitions and restrictions.

Outputs: itemized customs checklist, declaration route, evidence requirements,
dated thresholds, restricted-item warnings, and an official customs escalation path.

## 14. Extend Your Stay

Decision path: eligibility → visa extension or residence route → documents → filing
deadlines → fees.

Outputs: deadline-led extension plan, applicable route, document checklist, dated
fees, overstay warning, and links to Residence Permit or Leaving Uzbekistan.

## 15. Leaving Uzbekistan

Decision path: exit-registration applicability → outstanding fines → tax obligations
→ customs declaration → pet requirements → airport recommendations.

Outputs: personalized departure checklist, unresolved-obligation warnings, customs
and pet documentation, airport timing guidance, and authoritative escalation links.

## Approval boundary

D-001 is resolved by this portfolio selection. Each workflow still requires reviewed
source mappings, domain rules, localized content, and acceptance evidence before its
implementation can be marked launch-ready.
