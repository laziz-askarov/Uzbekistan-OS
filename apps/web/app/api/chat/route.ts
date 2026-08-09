import { NextResponse } from "next/server";
import { chatRequestSchema, generateVisaChatResult } from "@/lib/visa-ai";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(request: Request) {
  const requestId = request.headers.get("x-request-id") ?? crypto.randomUUID();
  try {
    const payload = chatRequestSchema.safeParse(await request.json());
    if (!payload.success) {
      return NextResponse.json(
        { error: "invalid_request", message: "Send between 1 and 12 valid chat messages." },
        { status: 400, headers: { "x-request-id": requestId } },
      );
    }

    console.info("[visa-chat] request", { requestId, messageCount: payload.data.messages.length });
    const result = await generateVisaChatResult(payload.data.messages);
    console.info("[visa-chat] response", {
      requestId,
      workflowId: result.workflow.id,
      status: result.answer.status,
      generated: result.generated,
    });
    return NextResponse.json(result, { headers: { "x-request-id": requestId } });
  } catch (error) {
    console.error("[visa-chat] request failed", {
      requestId,
      error: error instanceof Error ? error.name : "UnknownError",
    });
    return NextResponse.json(
      { error: "chat_unavailable", message: "Visa guidance is temporarily unavailable." },
      { status: 503, headers: { "x-request-id": requestId } },
    );
  }
}
