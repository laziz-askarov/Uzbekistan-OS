import { NextResponse } from "next/server";

export function GET() {
  return NextResponse.json({
    data: {
      service: "web",
      status: "ok",
      version: "0.1.0",
    },
    meta: {},
  });
}
