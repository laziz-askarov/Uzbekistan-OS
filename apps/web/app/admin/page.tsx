import type { Metadata } from "next";
import OperationsDashboard from "./operations-dashboard";

export const metadata: Metadata = {
  title: "Ingestion operations · Uzbekistan OS",
  description: "Internal source, upload, and crawler operations for Uzbekistan OS.",
};

export default function AdminOperationsPage() {
  return <OperationsDashboard />;
}
