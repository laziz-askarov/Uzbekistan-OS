import "server-only";

import { openai } from "@ai-sdk/openai";
import { generateText, Output } from "ai";
import { z } from "zod";
import {
  evidenceForWorkflow,
  selectVisaWorkflow,
  type VisaEvidence,
  type VisaWorkflow,
} from "./visa-workflows";

export const chatRequestSchema = z.object({
  messages: z
    .array(
      z.object({
        role: z.enum(["user", "assistant"]),
        content: z.string().trim().min(1).max(2_000),
      }),
    )
    .min(1)
    .max(12),
});

const citationIds = z.array(z.string().min(1)).max(6);
const profileItemSchema = z.object({
  field: z.string().min(1).max(80),
  value: z.string().min(1).max(240),
});

const answerContentShape = {
  status: z.enum(["answered", "needs_information", "insufficient"]),
  summary: z.string().min(1).max(1_200),
  summaryCitationIds: citationIds,
  sections: z
    .array(
      z.object({
        heading: z.string().min(1).max(120),
        content: z.string().min(1).max(2_000),
        citationIds,
      }),
    )
    .max(8),
  followUpQuestions: z.array(z.string().min(1).max(240)).max(1),
};

function validateAnswerShape(
  answer: z.infer<z.ZodObject<typeof answerContentShape>>,
  context: z.RefinementCtx,
) {
  if (answer.status === "answered" && answer.sections.length === 0) {
    context.addIssue({ code: "custom", path: ["sections"], message: "Answered responses require sections." });
  }
  if (answer.status === "answered" && answer.summaryCitationIds.length === 0) {
    context.addIssue({ code: "custom", path: ["summaryCitationIds"], message: "Answered summaries require citations." });
  }
  if (answer.status === "needs_information" && answer.followUpQuestions.length !== 1) {
    context.addIssue({ code: "custom", path: ["followUpQuestions"], message: "Gathering requires exactly one question." });
  }
  if (answer.status === "needs_information" && answer.sections.length > 0) {
    context.addIssue({ code: "custom", path: ["sections"], message: "Do not start the plan before intake is complete." });
  }
  if (answer.status === "answered" && answer.followUpQuestions.length > 0) {
    context.addIssue({ code: "custom", path: ["followUpQuestions"], message: "A completed plan cannot ask intake questions." });
  }
}

const visaResponseContentSchema = z.object(answerContentShape).superRefine(validateAnswerShape);

export const visaAnswerSchema = z
  .object({
    ...answerContentShape,
    profile: z.array(profileItemSchema).max(8),
    missingProfileFields: z.array(z.string().min(1).max(80)).max(8),
  })
  .superRefine(validateAnswerShape);

export type VisaAnswer = z.infer<typeof visaAnswerSchema>;

export type VisaChatResult = {
  answer: VisaAnswer;
  workflow: VisaWorkflow;
  sources: VisaEvidence[];
  generated: boolean;
};

const forbiddenControlText = ["<|system|>", "<|assistant|>", "[system]", "begin system message"];
const stopWords = new Set([
  "a", "an", "and", "are", "as", "at", "be", "before", "by", "for", "from", "in", "is", "it", "of", "on", "or", "the", "to", "with", "your",
]);

function meaningfulTokens(value: string): Set<string> {
  return new Set(
    value
      .toLocaleLowerCase()
      .match(/[\p{L}\p{N}-]+/gu)
      ?.filter((token) => token.length > 1 && !stopWords.has(token)) ?? [],
  );
}

function evidenceSupports(text: string, citations: VisaEvidence[]): boolean {
  const claimTokens = meaningfulTokens(text);
  if (claimTokens.size === 0) return false;
  const evidenceTokens = meaningfulTokens(citations.map((citation) => citation.content).join(" "));
  let matched = 0;
  for (const token of claimTokens) if (evidenceTokens.has(token)) matched += 1;
  const requiredMatches = Math.min(2, claimTokens.size);
  return matched >= requiredMatches && matched / claimTokens.size >= 0.1;
}

function validateEvidence(answer: VisaAnswer, sources: VisaEvidence[]): boolean {
  if (answer.status !== "answered") return true;
  const sourcesById = new Map(sources.map((source) => [source.id, source]));
  const validateClaim = (text: string, ids: string[]) => {
    const citations = ids.map((id) => sourcesById.get(id)).filter((item): item is VisaEvidence => Boolean(item));
    return citations.length === ids.length && ids.length > 0 && evidenceSupports(text, citations);
  };
  return (
    validateClaim(answer.summary, answer.summaryCitationIds) &&
    answer.sections.every((section) => validateClaim(section.content, section.citationIds))
  );
}

function validateProfile(answer: VisaAnswer, workflow: VisaWorkflow): boolean {
  const required = new Set(workflow.requiredProfile);
  const collected = answer.profile.map((item) => item.field);
  const missing = answer.missingProfileFields;
  const combined = [...collected, ...missing];
  const unique = new Set(combined);
  const fieldsAreKnown = combined.every((field) => required.has(field));
  const isCompletePartition =
    unique.size === combined.length &&
    unique.size === required.size &&
    [...required].every((field) => unique.has(field));
  if (!fieldsAreKnown || !isCompletePartition) return false;
  if (answer.status === "needs_information") {
    return missing.length > 0 && answer.followUpQuestions.length === 1 && answer.sections.length === 0;
  }
  if (answer.status === "answered") {
    return missing.length === 0 && collected.length === required.size && answer.followUpQuestions.length === 0;
  }
  return true;
}

const emptyProfileValue = /^(unknown|not provided|not specified|missing|n\/?a|to be provided)$/i;

type ProfileState = Pick<VisaAnswer, "profile" | "missingProfileFields">;

function normalizeExtractedProfile(
  extractedProfile: z.infer<typeof profileItemSchema>[],
  workflow: VisaWorkflow,
  messages: z.infer<typeof chatRequestSchema>["messages"],
): ProfileState {
  const required = new Set(workflow.requiredProfile);
  const collectedFields = new Set<string>();
  const profile = extractedProfile.filter((item) => {
    if (
      !required.has(item.field) ||
      collectedFields.has(item.field) ||
      emptyProfileValue.test(item.value.trim())
    ) {
      return false;
    }
    collectedFields.add(item.field);
    return true;
  });

  const userText = messages
    .filter((message) => message.role === "user")
    .map((message) => message.content)
    .join("\n");
  if (
    required.has("nationality") &&
    !collectedFields.has("nationality") &&
    /\b(?:u\.?s\.?|united states|american)\s+(?:citizen|national)\b/i.test(userText)
  ) {
    profile.push({ field: "nationality", value: "United States" });
    collectedFields.add("nationality");
  }

  return {
    profile,
    missingProfileFields: workflow.requiredProfile.filter(
      (field) => !collectedFields.has(field),
    ),
  };
}

function compileProfilePrompt(
  workflow: VisaWorkflow,
  messages: z.infer<typeof chatRequestSchema>["messages"],
): string {
  return `Extract the traveler's visa-intake profile from the full conversation.

Rules:
- Extract only facts explicitly supplied by the user. Assistant messages provide context for short replies, but are never themselves user facts.
- Read every message so facts stated earlier remain collected.
- Use only the exact REQUIRED PROFILE field labels. Do not add fields.
- Omit unknown, vague, contradictory, or unanswered fields. Never output placeholder values.
- An explicit negative answer is still a supplied fact. For example, "no sponsor or host" must be retained for the "sponsor or host" field rather than omitted.
- Normalize clear equivalents. For example, "US citizen", "U.S. citizen", "American citizen", and "citizen of the United States" mean nationality "United States".
- A short reply can answer the assistant's immediately preceding question (for example, "ordinary" after a passport-type question).

REQUIRED PROFILE:
${JSON.stringify(workflow.requiredProfile)}

UNTRUSTED CONVERSATION:
${JSON.stringify(messages)}`;
}

async function extractProfile(
  workflow: VisaWorkflow,
  messages: z.infer<typeof chatRequestSchema>["messages"],
): Promise<ProfileState> {
  const { output } = await generateText({
    model: openai(process.env.OPENAI_MODEL_ID ?? "gpt-5.4-mini"),
    output: Output.object({ schema: z.object({ profile: z.array(profileItemSchema).max(8) }) }),
    prompt: compileProfilePrompt(workflow, messages),
    maxOutputTokens: 500,
  });
  return normalizeExtractedProfile(output.profile, workflow, messages);
}

const intakeQuestions: Record<string, string> = {
  nationality: "What nationality is shown in your passport?",
  "passport type": "What type of passport will you travel with (for example, ordinary, diplomatic, or official)?",
  "travel purpose": "What is the main purpose of your trip?",
  "intended stay": "How long do you plan to stay in Uzbekistan?",
  "sponsor or host": "Will you have a sponsor or host in Uzbekistan?",
  "travel dates": "What dates do you plan to travel?",
  "number of entries": "Will you need single, double, or multiple entry?",
  "business purpose": "What business activity will you carry out in Uzbekistan?",
  "inviting Uzbek entity": "Which organization in Uzbekistan is inviting you?",
  employer: "Who will employ you in Uzbekistan?",
  "job role": "What job will you perform in Uzbekistan?",
  "authorization status": "Has your employer started or obtained the required work authorization?",
  institution: "Which educational institution will you attend?",
  "program type": "What type of study program will you attend?",
  "study dates": "When does your study program begin and end?",
  "admission status": "Have you received formal admission from the institution?",
  relationship: "What is your relationship to the person you will visit?",
  "host status": "What is your host's immigration or citizenship status in Uzbekistan?",
  "host address": "What is your host's address in Uzbekistan?",
  "current status": "What is your current immigration status in Uzbekistan?",
  "residence basis": "What is the basis for your planned residence in Uzbekistan?",
  "family or sponsor": "Will a family member or sponsor support your residence application?",
  "current location": "Where are you currently located?",
  "accommodation type": "Where will you stay (for example, a hotel, rental, or private home)?",
  "arrival date": "When did you arrive, or when will you arrive, in Uzbekistan?",
  "visa or entry type": "What visa or entry permission did you use to enter Uzbekistan?",
  "expiry date": "When does your current visa or permitted stay expire?",
  "planned departure": "When do you plan to leave Uzbekistan?",
};

function questionForMissingField(field: string): string {
  return intakeQuestions[field] ?? `Please tell me your ${field}.`;
}

function safeFallback(workflow: VisaWorkflow, sources: VisaEvidence[]): VisaChatResult {
  return {
    workflow,
    sources,
    generated: false,
    answer: {
      status: "insufficient",
      summary:
        "I could not produce a sufficiently supported answer from the reviewed official evidence. Please use the official sources below or provide more details about your passport, purpose and intended stay.",
      summaryCitationIds: [],
      sections: [],
      profile: [],
      missingProfileFields: [...workflow.requiredProfile],
      followUpQuestions: [],
    },
  };
}

function compilePrompt(
  workflow: VisaWorkflow,
  sources: VisaEvidence[],
  messages: z.infer<typeof chatRequestSchema>["messages"],
  profileState: ProfileState,
): string {
  const evidence = sources.map((source) => ({ id: source.id, content: source.content }));
  return `You are the Uzbekistan OS visa guidance assistant.

This is a high-risk immigration information task. Follow these rules:
- Answer in the language used by the user's latest message.
- Use only the retrieved EVIDENCE below for factual claims. Conversation text is context, never evidence.
- Treat each evidence item as a retained document excerpt. Prefer Ministry of Foreign Affairs and official portal material when excerpts conflict, state uncertainty, and direct the user to verify current rules at the linked official service.
- Never infer eligibility from nationality unless the supplied evidence explicitly states it.
- Never invent fees, timelines, deadlines, legal outcomes, URLs or document requirements.
- Treat this as a friendly conversation, not a form. Briefly acknowledge what the user just told you in natural language.
- The AUTHORITATIVE PROFILE STATE below was extracted separately from the full conversation. Never ask for a collected field again.
- If missingProfileFields is non-empty, use status "needs_information", return no sections, and ask exactly one short, natural follow-up question about the first most useful missing field. Do not list several questions or show the visa plan yet.
- Keep summary to one short warm acknowledgement. Put the next question only in followUpQuestions and do not repeat information already collected.
- When no required fields are missing, use status "answered", ask no follow-up questions, and start the user's workflow immediately with a concise personalized summary.
- Return the supported detail sections in this order when evidence is available: Route; Fees; Requirements and documents; Application process; Processing time; Validity; Arrival and registration obligations; Restrictions or important notes.
- Keep section headings short and do not put multiple named topics into one section unless the evidence only supports a combined explanation.
- If route eligibility is not explicit in the evidence, explain the official verification step conditionally instead of claiming the user is eligible.
- If the evidence cannot support an answer, use status "insufficient".
- For every answered summary and section, cite one or more evidence IDs. Reuse the evidence's concrete wording so support can be validated.
- Do not offer to submit an application, store documents, book appointments, take payment or contact authorities.

WORKFLOW:
${JSON.stringify({ id: workflow.id, title: workflow.title, description: workflow.description, requiredProfile: workflow.requiredProfile })}

AUTHORITATIVE PROFILE STATE:
${JSON.stringify(profileState)}

EVIDENCE:
${JSON.stringify(evidence)}

UNTRUSTED CONVERSATION:
${JSON.stringify(messages)}`;
}

export async function generateVisaChatResult(
  messages: z.infer<typeof chatRequestSchema>["messages"],
): Promise<VisaChatResult> {
  const latestQuestion = [...messages].reverse().find((message) => message.role === "user")?.content ?? "";
  const userContext = messages
    .filter((message) => message.role === "user")
    .map((message) => message.content)
    .join("\n");
  const workflow = selectVisaWorkflow(userContext);
  const sources = evidenceForWorkflow(workflow, userContext);
  const normalized = latestQuestion.toLocaleLowerCase();
  if (forbiddenControlText.some((value) => normalized.includes(value))) return safeFallback(workflow, sources);

  try {
    const profileState = await extractProfile(workflow, messages);
    console.info("[visa-chat] profile context extracted", {
      workflowId: workflow.id,
      collectedCount: profileState.profile.length,
      missingCount: profileState.missingProfileFields.length,
    });
    const { output } = await generateText({
      model: openai(process.env.OPENAI_MODEL_ID ?? "gpt-5.4-mini"),
      output: Output.object({ schema: visaResponseContentSchema }),
      prompt: compilePrompt(workflow, sources, messages, profileState),
      maxOutputTokens: 2_000,
    });
    const nextMissingField = profileState.missingProfileFields[0];
    const answer = visaAnswerSchema.parse({
      ...output,
      ...profileState,
      ...(nextMissingField
        ? {
            status: "needs_information",
            summary: "Thanks — I’ve saved the details you’ve shared so far.",
            sections: [],
            summaryCitationIds: [],
            followUpQuestions: [questionForMissingField(nextMissingField)],
          }
        : {}),
    });
    if (!validateProfile(answer, workflow)) {
      console.warn("[visa-chat] profile validation rejected model output", {
        workflowId: workflow.id,
        status: answer.status,
        collectedCount: answer.profile.length,
        missingCount: answer.missingProfileFields.length,
      });
      return safeFallback(workflow, sources);
    }
    if (!validateEvidence(answer, sources)) {
      console.warn("[visa-chat] evidence validation rejected model output", {
        workflowId: workflow.id,
        status: answer.status,
        summaryCitationCount: answer.summaryCitationIds.length,
        sectionCitationCounts: answer.sections.map((section) => section.citationIds.length),
      });
      return safeFallback(workflow, sources);
    }
    return { answer, workflow, sources, generated: true };
  } catch (error) {
    console.error("[visa-chat] generation failed", {
      error: error instanceof Error ? error.name : "UnknownError",
      message: error instanceof Error ? error.message : "Unknown generation failure",
      statusCode:
        typeof error === "object" && error !== null && "statusCode" in error
          ? error.statusCode
          : undefined,
      workflowId: workflow.id,
    });
    return safeFallback(workflow, sources);
  }
}
