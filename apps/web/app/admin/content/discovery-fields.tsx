"use client";

import { useState } from "react";

type Faq = { question: string; answer: string };
export default function DiscoveryFields({
  value,
  disabled,
  onChange,
}: {
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
}) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  let data: Record<string, unknown>;
  try {
    const parsed = JSON.parse(value);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed))
      throw new Error();
    data = parsed;
  } catch {
    return (
      <p role="status">
        Fix the advanced structured JSON before editing discovery fields.
      </p>
    );
  }
  const takeaways = Array.isArray(data.key_takeaways)
    ? data.key_takeaways.filter(
        (item): item is string => typeof item === "string",
      )
    : [];
  const faqs = (
    Array.isArray(data.faq)
      ? data.faq
      : Array.isArray(data.faqs)
        ? data.faqs
        : []
  ).filter((item): item is Faq =>
    Boolean(
      item &&
      typeof item === "object" &&
      typeof item.question === "string" &&
      typeof item.answer === "string",
    ),
  );
  function update(patch: Record<string, unknown>) {
    onChange(JSON.stringify({ ...data, ...patch }, null, 2));
  }
  return (
    <fieldset disabled={disabled}>
      <legend>Answers readers can find and cite</legend>
      <p>
        These appear on the published page and in its machine-readable content.
        Use specific answers supported by your article and sources.
      </p>
      <label>
        Key takeaways (one per line)
        <textarea
          rows={4}
          value={takeaways.join("\n")}
          onChange={(event) =>
            update({ key_takeaways: event.target.value.split("\n") })
          }
        />
      </label>
      {faqs.map((item, index) => (
        <div key={`${index}-${item.question}`}>
          <strong>{item.question}</strong>
          <p>{item.answer}</p>
          <button
            type="button"
            onClick={() =>
              update({ faq: faqs.filter((_, position) => position !== index) })
            }
          >
            Remove question {index + 1}
          </button>
        </div>
      ))}
      <label>
        Frequently asked question
        <input
          maxLength={500}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
        />
      </label>
      <label>
        Answer
        <textarea
          rows={3}
          maxLength={4000}
          value={answer}
          onChange={(event) => setAnswer(event.target.value)}
        />
      </label>
      <button
        type="button"
        disabled={disabled || !question.trim() || !answer.trim()}
        onClick={() => {
          update({
            faq: [
              ...faqs,
              { question: question.trim(), answer: answer.trim() },
            ],
          });
          setQuestion("");
          setAnswer("");
        }}
      >
        Add FAQ
      </button>
    </fieldset>
  );
}
