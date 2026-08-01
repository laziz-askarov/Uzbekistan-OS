import type { Metadata } from "next";
import ReviewConsole from "./review-console";

export const metadata: Metadata = {
  title: "Review queue · Uzbekistan OS",
  description: "Internal evidence review operations for Uzbekistan OS.",
};

export default function ReviewQueuePage() {
  return <ReviewConsole />;
}
