import type { Metadata } from "next";
import LegalPage from "../legal/legal-page";

export const metadata: Metadata = {
  title: "Terms of Use | Uzbekistan OS",
  description: "The rules and limitations that apply when using Uzbekistan OS.",
};

const sections = [
  {
    id: "agreement",
    title: "Agreement to these terms",
    content: (
      <>
        <p>
          These Terms of Use form an agreement between you and Uzbekistan OS,
          operated from Tashkent, Uzbekistan. By accessing the website, creating
          an account, or using the assistant, you agree to these terms and
          acknowledge the Privacy Policy. If you do not agree, do not use the
          service.
        </p>
      </>
    ),
  },
  {
    id: "service",
    title: "What Uzbekistan OS provides",
    content: (
      <>
        <p>
          Uzbekistan OS organizes public information and uses AI to provide
          general, source-linked guidance about visas, immigration, registration
          after arrival, and related public services. Some features personalize
          guidance from information you provide and save the resulting
          conversation to your account.
        </p>
        <p>
          Uzbekistan OS is independent. It is not a government body, embassy,
          consulate, migration authority, law firm, or licensed immigration
          adviser. It cannot submit applications, issue visas, make official
          decisions, guarantee eligibility, contact authorities for you, or
          replace advice from a qualified professional.
        </p>
      </>
    ),
  },
  {
    id: "eligibility",
    title: "Who may use the service",
    content: (
      <>
        <p>
          You must be legally able to accept these terms. If you are under the
          age of legal majority where you live, you may use Uzbekistan OS only
          with the involvement and permission of a parent or legal guardian. You
          may not use the service if applicable law prohibits you from doing so.
        </p>
      </>
    ),
  },
  {
    id: "accounts",
    title: "Accounts and security",
    content: (
      <>
        <p>
          You must provide accurate account information, keep your credentials
          confidential, and promptly update your contact details. You are
          responsible for activity carried out through your account unless it
          results from our failure to use reasonable security measures. Tell us
          promptly at{" "}
          <a href="mailto:info@uzbekistanos.com">info@uzbekistanos.com</a> if
          you suspect unauthorized access.
        </p>
        <p>
          We may require email or phone verification, impose reasonable usage
          limits, or suspend access when needed to protect users, providers, or
          the service.
        </p>
      </>
    ),
  },
  {
    id: "your-content",
    title: "Your content and privacy",
    content: (
      <>
        <p>
          You retain your rights in questions and other content you submit. You
          give Uzbekistan OS a limited, worldwide, non-exclusive license to
          host, process, reproduce, transmit, and display that content only as
          needed to operate, secure, and improve the service and to work with
          the providers described in our Privacy Policy.
        </p>
        <p>
          You are responsible for having the right to submit your content. Do
          not submit another person’s confidential information without
          authority. The current service does not require passport numbers,
          PINFLs, payment details, medical records, government credentials, or
          identity-document uploads, so do not include them in chat.
        </p>
      </>
    ),
  },
  {
    id: "acceptable-use",
    title: "Acceptable use",
    content: (
      <>
        <p>You may not use Uzbekistan OS to:</p>
        <ul>
          <li>
            break the law, violate another person’s rights, or cause harm;
          </li>
          <li>
            impersonate another person, misrepresent your identity, or submit
            fraudulent information;
          </li>
          <li>
            interfere with the service, bypass rate limits or security controls,
            probe vulnerabilities, or introduce malicious code;
          </li>
          <li>
            scrape, copy, reverse engineer, or commercially exploit the service
            except where applicable law expressly permits it;
          </li>
          <li>
            use automated access without our written permission or place an
            unreasonable load on the service; or
          </li>
          <li>
            present AI output as an official government decision or use it to
            deceive another person.
          </li>
        </ul>
      </>
    ),
  },
  {
    id: "accuracy",
    title: "AI output, official sources, and your decisions",
    content: (
      <>
        <p>
          AI-generated guidance can be incomplete, outdated, or wrong, even when
          it cites a source. Government rules, fees, processing times, and
          eligibility can change without notice. Citations and links are
          provided so you can verify important information with the responsible
          authority.
        </p>
        <p>
          You are responsible for checking official requirements before booking
          travel, paying fees, submitting documents, changing immigration
          status, or relying on a deadline. Government portals and officials—not
          Uzbekistan OS—control applications and outcomes. Seek a qualified
          lawyer or authorized adviser where your circumstances require
          professional advice.
        </p>
      </>
    ),
  },
  {
    id: "third-parties",
    title: "Third-party services and links",
    content: (
      <>
        <p>
          The service depends on third-party infrastructure and may link to
          government portals or other websites. Their terms, privacy practices,
          availability, and content are controlled by those third parties. A
          link or integration does not mean Uzbekistan OS operates, endorses, or
          guarantees that service.
        </p>
      </>
    ),
  },
  {
    id: "intellectual-property",
    title: "Our intellectual property",
    content: (
      <>
        <p>
          Uzbekistan OS and its software, interface, branding, original text,
          organization, and design are owned by us or our licensors and are
          protected by applicable law. These terms give you a personal,
          revocable, non-exclusive, non-transferable right to use the service
          for lawful purposes; they do not transfer ownership of the service or
          third-party source material.
        </p>
      </>
    ),
  },
  {
    id: "availability",
    title: "Availability, changes, and suspension",
    content: (
      <>
        <p>
          We may update, limit, suspend, or discontinue features, providers, or
          the service. We do not promise uninterrupted availability. We may
          suspend or terminate access when we reasonably believe these terms
          have been violated, use creates risk, law requires it, or continued
          operation is no longer practical.
        </p>
        <p>
          You may stop using the service at any time. You can permanently delete
          your account through account settings, or contact{" "}
          <a href="mailto:info@uzbekistanos.com">info@uzbekistanos.com</a> from
          the email associated with your account if you need help with an
          account or personal-data request.
        </p>
      </>
    ),
  },
  {
    id: "disclaimers",
    title: "Disclaimers",
    content: (
      <>
        <p>
          To the fullest extent permitted by law, Uzbekistan OS is provided “as
          is” and “as available.” We disclaim implied warranties of
          merchantability, fitness for a particular purpose, accuracy,
          non-infringement, and uninterrupted availability. Nothing in these
          terms excludes a warranty or consumer right that cannot lawfully be
          excluded.
        </p>
      </>
    ),
  },
  {
    id: "liability",
    title: "Limitation of liability",
    content: (
      <>
        <p>
          To the fullest extent permitted by law, Uzbekistan OS will not be
          liable for indirect, incidental, special, consequential, or punitive
          loss, or for lost profits, opportunities, data, travel costs,
          application fees, or immigration outcomes arising from use of the
          service. Our total liability relating to the service will not exceed
          the greater of the amount you paid us for the service during the 12
          months before the event giving rise to the claim or US$100.
        </p>
        <p>
          These limits do not apply to fraud, willful misconduct, death or
          personal injury caused by negligence, or any liability that applicable
          law does not allow us to limit.
        </p>
      </>
    ),
  },
  {
    id: "law",
    title: "Governing law and disputes",
    content: (
      <>
        <p>
          These terms are governed by the laws of the Republic of Uzbekistan,
          without regard to conflict-of-law rules. Courts with jurisdiction in
          Tashkent, Uzbekistan will hear disputes unless mandatory consumer law
          gives you the right to bring a claim elsewhere. Before filing a claim,
          please contact us so we can try to resolve the issue informally.
        </p>
      </>
    ),
  },
  {
    id: "changes-contact",
    title: "Changes and contact",
    content: (
      <>
        <p>
          We may revise these terms as the service or law changes. Updated terms
          will show a new effective date. If a change materially affects
          existing users, we will provide reasonable notice. Continued use after
          the effective date means you accept the revised terms where permitted
          by law.
        </p>
        <p>
          Legal contact: Uzbekistan OS, Tashkent, Uzbekistan ·{" "}
          <a href="mailto:info@uzbekistanos.com">info@uzbekistanos.com</a>
        </p>
      </>
    ),
  },
] as const;

export default function TermsPage() {
  return (
    <LegalPage
      description="These terms explain what Uzbekistan OS provides, the rules for using it, and the limits of AI-generated public-service guidance."
      effectiveDate="11 August 2026"
      eyebrow="Using the service"
      sections={[...sections]}
      summary={
        <p>
          Uzbekistan OS provides independent informational guidance, not legal
          advice or government services. Verify important information with the
          cited authority, protect your account, do not submit sensitive
          identity documents, and use the service lawfully.
        </p>
      }
      title="Terms of Use"
    />
  );
}
