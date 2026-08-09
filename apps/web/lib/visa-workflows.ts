import "server-only";
import visaKnowledge from "./visa-knowledge.json";

export type VisaWorkflowId =
  | "visa-route-discovery"
  | "visa-free-entry"
  | "electronic-visa"
  | "consular-visa"
  | "business-visa"
  | "work-visa"
  | "student-visa"
  | "family-visit"
  | "residence-permit"
  | "arrival-registration"
  | "overstay-and-exit";

export type VisaEvidence = {
  id: string;
  title: string;
  url: string;
  reviewedAt: string;
  content: string;
  sourceFile: string;
  sourceSha256: string;
};

export type VisaWorkflow = {
  id: VisaWorkflowId;
  title: string;
  description: string;
  requiredProfile: string[];
  evidenceTopics: string[];
};

export const visaWorkflows: readonly VisaWorkflow[] = [
  {
    id: "visa-route-discovery",
    title: "Find the right visa route",
    description: "Identify visa-free, electronic or consular entry.",
    requiredProfile: ["nationality", "passport type", "travel purpose", "intended stay", "sponsor or host"],
    evidenceTopics: ["visa-free-entry", "electronic-visa", "visa-categories", "mfa-visa-guidance", "passport-validity"],
  },
  {
    id: "visa-free-entry",
    title: "Visa-free entry",
    description: "Check whether an eligible passport can enter without an advance visa.",
    requiredProfile: ["nationality", "passport type", "travel purpose", "intended stay"],
    evidenceTopics: ["visa-free-entry", "mfa-visa-guidance", "passport-validity", "arrival-registration"],
  },
  {
    id: "electronic-visa",
    title: "Electronic visa",
    description: "Check eligibility, documents, application steps and fees.",
    requiredProfile: ["nationality", "passport type", "travel dates", "number of entries"],
    evidenceTopics: ["electronic-visa", "passport-validity", "arrival-registration"],
  },
  {
    id: "consular-visa",
    title: "Consular visa",
    description: "Match a purpose to a non-electronic visa category.",
    requiredProfile: ["nationality", "passport type", "travel purpose", "intended stay", "sponsor or host"],
    evidenceTopics: ["visa-categories", "mfa-visa-guidance", "passport-validity"],
  },
  {
    id: "business-visa",
    title: "Business visa",
    description: "Prepare a sponsored B-1 or B-2 business visit.",
    requiredProfile: ["nationality", "business purpose", "inviting Uzbek entity", "intended stay"],
    evidenceTopics: ["business-visa", "mfa-visa-guidance", "passport-validity", "arrival-registration"],
  },
  {
    id: "work-visa",
    title: "Work visa",
    description: "Separate employment authorization from the visa application.",
    requiredProfile: ["nationality", "employer", "job role", "authorization status", "intended stay"],
    evidenceTopics: ["visa-categories", "mfa-visa-guidance", "passport-validity", "arrival-registration"],
  },
  {
    id: "student-visa",
    title: "Student visa",
    description: "Prepare the institution-sponsored study route.",
    requiredProfile: ["nationality", "institution", "program type", "study dates", "admission status"],
    evidenceTopics: ["student-visa", "mfa-visa-guidance", "passport-validity", "arrival-registration"],
  },
  {
    id: "family-visit",
    title: "Private or family visit",
    description: "Identify PV-1, PV-2 or VTD and the correct host evidence.",
    requiredProfile: ["nationality", "relationship", "host status", "host address", "intended stay"],
    evidenceTopics: ["family-visit", "mfa-visa-guidance", "passport-validity", "arrival-registration"],
  },
  {
    id: "residence-permit",
    title: "Residence permit",
    description: "Distinguish residence status from a short-stay visa.",
    requiredProfile: ["nationality", "current status", "residence basis", "family or sponsor", "current location"],
    evidenceTopics: ["permanent-residence", "temporary-residence", "arrival-registration"],
  },
  {
    id: "arrival-registration",
    title: "Arrival registration",
    description: "Understand registration after entry and accommodation responsibilities.",
    requiredProfile: ["accommodation type", "arrival date", "current location"],
    evidenceTopics: ["arrival-registration", "temporary-residence"],
  },
  {
    id: "overstay-and-exit",
    title: "Overstay and exit",
    description: "Use a safe escalation path for an expired permitted stay.",
    requiredProfile: ["visa or entry type", "expiry date", "current location", "planned departure"],
    evidenceTopics: ["overstay-and-exit", "mfa-visa-guidance"],
  },
] as const;

const workflowTerms: readonly [VisaWorkflowId, readonly string[]][] = [
  ["overstay-and-exit", ["overstay", "expired", "exit visa", "просроч", "muddati tug"]],
  ["arrival-registration", ["register", "registration", "hotel registration", "регистрац", "ro'yxat"]],
  ["residence-permit", ["residence permit", "permanent residence", "temporary residence", "вид на жительство"]],
  ["work-visa", ["work visa", "work permit", "employment", "job", "работ", "ish"]],
  ["student-visa", ["student", "study", "university", "school", "учеб", "o'qish"]],
  ["family-visit", ["family", "private visit", "pv-1", "pv-2", "vtd", "relative", "семь"]],
  ["business-visa", ["business visa", "business trip", "b-1", "b-2", "conference", "commercial"]],
  ["electronic-visa", ["e-visa", "evisa", "electronic visa", "online visa"]],
  ["visa-free-entry", ["visa free", "visa-free", "without a visa", "без виз"]],
  ["consular-visa", ["consular", "embassy visa", "tourist visa", "transit visa", "medical visa"]],
];

export function selectVisaWorkflow(question: string): VisaWorkflow {
  const normalized = question.toLocaleLowerCase();
  const selectedId = workflowTerms.find(([, terms]) => terms.some((term) => normalized.includes(term)))?.[0] ?? "visa-route-discovery";
  return visaWorkflows.find((workflow) => workflow.id === selectedId) ?? visaWorkflows[0];
}

const retrievalStopWords = new Set([
  "a", "an", "and", "are", "for", "from", "i", "in", "is", "it", "my", "of", "on", "or", "the", "to", "with",
]);

function retrievalTokens(value: string): Set<string> {
  const normalized = value
    .toLocaleLowerCase()
    .replace(/\b(?:u\.?s\.?a?|american)\b/g, "united states")
    .replace(/\be-visa\b/g, "electronic visa");
  return new Set(
    normalized
      .match(/[\p{L}\p{N}-]+/gu)
      ?.filter((token) => token.length > 1 && !retrievalStopWords.has(token)) ?? [],
  );
}

export function evidenceForWorkflow(workflow: VisaWorkflow, query: string): VisaEvidence[] {
  const allowed = new Set(workflow.evidenceTopics);
  const queryTokens = retrievalTokens(query);
  const candidates = visaKnowledge.chunks
    .filter((chunk) => allowed.has(chunk.topic))
    .map((chunk) => {
      const contentTokens = retrievalTokens(`${chunk.title} ${chunk.content}`);
      const lexicalScore = [...queryTokens].reduce(
        (score, token) => score + (contentTokens.has(token) ? 3 : 0),
        0,
      );
      const topicPriority = workflow.evidenceTopics.length - workflow.evidenceTopics.indexOf(chunk.topic);
      return { chunk, score: lexicalScore + topicPriority };
    })
    .sort((left, right) => right.score - left.score || left.chunk.id.localeCompare(right.chunk.id));

  const selected = new Map<string, (typeof candidates)[number]["chunk"]>();
  for (const topic of workflow.evidenceTopics) {
    const bestForTopic = candidates.find(({ chunk }) => chunk.topic === topic);
    if (bestForTopic) selected.set(bestForTopic.chunk.id, bestForTopic.chunk);
  }
  const perSource = new Map<string, number>();
  for (const chunk of selected.values()) {
    perSource.set(chunk.sourceFile, (perSource.get(chunk.sourceFile) ?? 0) + 1);
  }
  for (const { chunk } of candidates) {
    if (selected.size >= 8) break;
    if (selected.has(chunk.id) || (perSource.get(chunk.sourceFile) ?? 0) >= 2) continue;
    selected.set(chunk.id, chunk);
    perSource.set(chunk.sourceFile, (perSource.get(chunk.sourceFile) ?? 0) + 1);
  }

  return [...selected.values()].map((chunk) => ({
    id: chunk.id,
    title: chunk.title,
    url: chunk.url,
    reviewedAt: chunk.reviewedAt,
    content: chunk.content,
    sourceFile: chunk.sourceFile,
    sourceSha256: chunk.sourceSha256,
  }));
}
