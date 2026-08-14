import type { Metadata } from "next";
import OperationsDashboard from "./operations-dashboard";

export const metadata: Metadata = {
  title: "System analytics and operations · Uzbekistan OS",
  description:
    "Internal service health, error, source, upload, and crawler operations for Uzbekistan OS.",
  robots: { index: false, follow: false },
};

export default function AdminOperationsPage() {
  return <OperationsDashboard />;
}
