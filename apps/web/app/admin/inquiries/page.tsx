import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getStaffIdentity } from "@/lib/admin-auth";
import { listTripInquiries } from "@/lib/admin-inquiries";
import styles from "./inquiries.module.css";

export const metadata: Metadata = {
  title: "Trip inquiries | Uzbekistan OS",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Tashkent",
  }).format(new Date(value));
}

export default async function AdminInquiriesPage() {
  const identity = await getStaffIdentity();
  if (!identity) redirect("/account");

  const inquiries = await listTripInquiries();

  return (
    <main className={styles.page}>
      <h1>Trip inquiries</h1>
      <p>
        Inquiries from the public trip-planning form, newest first. Reply from
        your mail client; this page is read-only. <Link href="/admin">Back to operations</Link>.
      </p>
      {inquiries.length === 0 ? (
        <p className={styles.empty}>No inquiries yet.</p>
      ) : (
        <ul className={styles.list}>
          {inquiries.map((inquiry) => (
            <li className={styles.card} key={inquiry.id}>
              <div className={styles.head}>
                <strong>{inquiry.name}</strong>
                <span className={styles.status}>{inquiry.status}</span>
                <span>{formatDate(inquiry.created_at)}</span>
              </div>
              <dl className={styles.facts}>
                <div>
                  <dt>Email</dt>
                  <dd>
                    <a href={`mailto:${inquiry.email}`}>{inquiry.email}</a>
                  </dd>
                </div>
                <div>
                  <dt>Travel month</dt>
                  <dd>{inquiry.travel_month}</dd>
                </div>
                <div>
                  <dt>Nights</dt>
                  <dd>{inquiry.nights}</dd>
                </div>
                <div>
                  <dt>Travellers</dt>
                  <dd>{inquiry.travellers}</dd>
                </div>
                <div>
                  <dt>Comfort</dt>
                  <dd>{inquiry.comfort}</dd>
                </div>
                <div>
                  <dt>Budget</dt>
                  <dd>{inquiry.budget}</dd>
                </div>
                <div>
                  <dt>Interests</dt>
                  <dd>{inquiry.interests.join(", ") || "Not given"}</dd>
                </div>
                <div>
                  <dt>Came from</dt>
                  <dd>{inquiry.source_path ?? "/trips"}</dd>
                </div>
              </dl>
              {inquiry.message ? (
                <p className={styles.message}>{inquiry.message}</p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
