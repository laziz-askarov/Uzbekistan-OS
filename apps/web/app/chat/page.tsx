import type { Metadata } from "next";
import ChatWorkspace from "./chat-workspace";

export const metadata: Metadata = {
  title: "Visa Assistant | Uzbekistan OS",
  description:
    "A signed-in workspace preview for structured, official-source-backed Uzbekistan visa guidance.",
};

export default function ChatPage() {
  return <ChatWorkspace />;
}
