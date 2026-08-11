import type { Metadata } from "next";
import LegalPage from "../legal/legal-page";

export const metadata: Metadata = {
  title: "Privacy Policy | Uzbekistan OS",
  description:
    "How Uzbekistan OS collects, uses, stores, and shares personal information.",
};

const sections = [
  {
    id: "who-we-are",
    title: "Who we are",
    content: (
      <>
        <p>
          Uzbekistan OS is an independent information service operated from
          Tashkent, Uzbekistan. We are not a government agency, immigration
          authority, law firm, or official application portal.
        </p>
        <p>
          For questions or requests about this policy or your personal
          information, email us at{" "}
          <a href="mailto:info@uzbekistanos.com">info@uzbekistanos.com</a>.
        </p>
      </>
    ),
  },
  {
    id: "information-we-collect",
    title: "Information we collect",
    content: (
      <>
        <p>We collect only the information needed to operate the service:</p>
        <ul>
          <li>
            <strong>Account and contact information:</strong> email address or
            international phone number, account identifiers, verification
            status, and authentication records. Passwords are handled by our
            authentication provider and are not available to us in plain text.
          </li>
          <li>
            <strong>Profile information:</strong> first and last name,
            nationality, preferred language or residency information you choose
            to provide, and an optional profile image.
          </li>
          <li>
            <strong>Conversations and guidance:</strong> questions, travel or
            immigration details you type, assistant responses, citations, and
            saved conversation titles. This may include nationality, travel
            dates, host or sponsor details, and other information relevant to
            your request.
          </li>
          <li>
            <strong>Security and operational data:</strong> request IDs, dates
            and times, route and response status, rate-limit usage, device and
            network information, and diagnostic events. Our application logs do
            not intentionally record chat text, passwords, one-time codes, phone
            numbers, or email addresses.
          </li>
          <li>
            <strong>Analytics and performance data:</strong> page views,
            referrer, approximate location, browser, operating system, device
            type, and page-performance measurements. Vercel Web Analytics is
            designed to use aggregated, cookie-free data rather than persistent
            cross-site identifiers.
          </li>
        </ul>
        <p>
          Uzbekistan OS does not currently ask you to upload identity documents
          or provide a PINFL, passport number, payment card, or government
          account credential. Please do not include those items in chat.
        </p>
      </>
    ),
  },
  {
    id: "how-we-use-information",
    title: "How we use information",
    content: (
      <>
        <p>We use information to:</p>
        <ul>
          <li>create, verify, secure, and support your account;</li>
          <li>provide personalized guidance and save conversation history;</li>
          <li>send account confirmation, recovery, and SMS verification;</li>
          <li>
            retrieve official sources and generate structured assistant
            responses;
          </li>
          <li>
            prevent fraud, abuse, excessive usage, and security incidents;
          </li>
          <li>measure reliability, usage, and website performance; and</li>
          <li>meet legal obligations and enforce our Terms of Use.</li>
        </ul>
        <p>
          Depending on the context and applicable law, we process information
          with your consent, to provide the service you request, for legitimate
          interests such as security and product improvement, or to comply with
          law. You may withdraw consent where consent is the applicable basis,
          but that will not affect processing already completed lawfully.
        </p>
      </>
    ),
  },
  {
    id: "ai-processing",
    title: "How AI processing works",
    content: (
      <>
        <p>
          When you use the assistant, Uzbekistan OS sends a bounded portion of
          your recent conversation and relevant official-source excerpts to
          OpenAI to produce and validate a response. OpenAI may also perform a
          restricted search of approved official government domains when the
          retained evidence is insufficient.
        </p>
        <p>
          OpenAI states that API inputs and outputs are not used to train its
          models by default unless the account holder opts in. Under OpenAI’s
          default API controls, prompts, responses, and related abuse-monitoring
          data may be retained for up to 30 days, and some Responses API state
          may also be retained for that period. See OpenAI’s{" "}
          <a
            href="https://platform.openai.com/docs/models/default-usage-policies-by-endpoint"
            rel="noreferrer"
            target="_blank"
          >
            API data controls
          </a>
          .
        </p>
        <p>
          AI responses can be incomplete or incorrect. Uzbekistan OS retains the
          saved conversation in your account so it can be available across
          devices; OpenAI is not the system of record for that history.
        </p>
      </>
    ),
  },
  {
    id: "sharing",
    title: "When we share information",
    content: (
      <>
        <p>We use service providers to operate Uzbekistan OS:</p>
        <ul>
          <li>
            <strong>Supabase</strong> for authentication, PostgreSQL account
            data, private profile-image storage, and session management;
          </li>
          <li>
            <strong>OpenAI</strong> for AI response generation and restricted
            official-source web search;
          </li>
          <li>
            <strong>Vercel</strong> for website hosting, security logs,
            cookie-free web analytics, and performance monitoring; and
          </li>
          <li>
            <strong>DevSMS</strong> for phone verification, which receives the
            destination phone number and one-time verification details needed to
            deliver the message.
          </li>
        </ul>
        <p>
          We may also disclose information when required by law, to protect
          users and the service, or as part of a merger, financing,
          reorganization, or transfer of the service subject to appropriate
          safeguards. We do not sell personal information or use it for
          third-party targeted advertising.
        </p>
      </>
    ),
  },
  {
    id: "international-processing",
    title: "International processing and localization",
    content: (
      <>
        <p>
          Uzbekistan OS is operated from Uzbekistan, but its current hosting,
          primary customer database, authentication, AI, analytics, and
          messaging providers may process information in the United States and
          other countries. Those countries may have different privacy laws from
          your country.
        </p>
        <p>
          Uzbekistan has specific registration and local-storage requirements
          for databases containing Uzbek citizens’ personal data. We are
          evaluating the infrastructure and registration changes required for
          localization. This policy describes the service’s current technical
          setup and does not claim that localization work is complete.
        </p>
      </>
    ),
  },
  {
    id: "retention",
    title: "How long we keep information",
    content: (
      <>
        <p>
          Saved conversations do not currently expire automatically. We keep a
          saved conversation and its messages until you delete that conversation
          or delete your account. Account details, profile information, optional
          profile images, and checklists are kept while your account remains
          active or until you remove them through the available controls.
        </p>
        <p>
          Deleting a conversation removes that conversation and its messages
          from the active customer database. Deleting your account removes your
          authentication account and active profile, profile image, saved
          conversations, messages, checklists, and account-linked usage-limit
          records. These actions cannot be undone.
        </p>
        <p>
          Short-term rate-limit records are also removed on a rolling basis.
          Operational logs, backups, authentication events, analytics, SMS
          delivery records, and AI-provider records follow security, legal, and
          provider retention schedules. Limited copies may therefore remain
          temporarily in provider systems or backups after you use a deletion
          control. As described above, OpenAI API records may remain for up to
          30 days under its default controls.
        </p>
      </>
    ),
  },
  {
    id: "rights",
    title: "Your rights and choices",
    content: (
      <>
        <p>
          Subject to applicable law, you may ask to access, correct, receive,
          restrict, object to, or delete your personal information, or withdraw
          consent. Account settings let you download a current JSON export of
          your account data or permanently delete your account, and conversation
          history includes a control to delete each saved conversation. You can
          also update several profile and contact fields there. For other
          requests, email{" "}
          <a href="mailto:info@uzbekistanos.com">info@uzbekistanos.com</a> from
          the address associated with your account so we can verify the request.
        </p>
        <p>
          You may also contact the competent privacy authority or a court. In
          Uzbekistan, information about personal-data rights and complaints is
          available from the{" "}
          <a href="https://pd.gov.uz/" rel="noreferrer" target="_blank">
            Personal Data Authority
          </a>
          .
        </p>
      </>
    ),
  },
  {
    id: "security",
    title: "Security and account protection",
    content: (
      <>
        <p>
          We use access controls, encrypted connections, owner-scoped database
          policies, private profile-image storage, signed access links,
          authenticated sessions, request-size limits, and rate limits. No
          online service can guarantee absolute security. Use a unique password
          and tell us promptly if you believe your account has been compromised.
        </p>
      </>
    ),
  },
  {
    id: "children",
    title: "Children",
    content: (
      <>
        <p>
          Uzbekistan OS is not directed to children under 16. If you are under
          the age at which you can consent to data processing in your country,
          use the service only with the involvement of a parent or legal
          guardian. Contact us if you believe a child provided personal
          information without appropriate authorization.
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
          We may update this policy as the service, providers, or legal
          requirements change. We will revise the effective date and provide
          additional notice when a change materially affects your rights.
        </p>
        <p>
          Privacy contact: Uzbekistan OS, Tashkent, Uzbekistan ·{" "}
          <a href="mailto:info@uzbekistanos.com">info@uzbekistanos.com</a>
        </p>
      </>
    ),
  },
] as const;

export default function PrivacyPage() {
  return (
    <LegalPage
      description="This policy explains what information Uzbekistan OS handles, why we use it, which providers help us, and the choices available to you."
      effectiveDate="11 August 2026"
      eyebrow="Your information"
      sections={[...sections]}
      summary={
        <p>
          We use account details and saved conversations to provide personalized
          visa guidance. We do not sell personal information. The service uses
          Supabase, OpenAI, Vercel, and DevSMS, and data may currently be
          processed outside Uzbekistan. Do not enter passport numbers, PINFLs,
          payment details, or government credentials in chat.
        </p>
      }
      title="Privacy Policy"
    />
  );
}
