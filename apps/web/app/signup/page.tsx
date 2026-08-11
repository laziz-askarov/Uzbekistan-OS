import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import AuthForm from "./auth-form";

export const metadata: Metadata = {
  title: "Create your account | Uzbekistan OS",
  description:
    "Create an Uzbekistan OS account to receive a personalized Uzbekistan visa plan.",
};

const planBenefits = [
  "The visa route that matches your nationality and purpose",
  "A complete, personalized document checklist",
  "Application steps in the right order",
  "Processing time, fees, validity, and entry limits",
  "Arrival registration and compliance guidance",
] as const;

export default function SignupPage() {
  return (
    <main className="signup-page">
      <Link className="signup-brand" href="/" aria-label="Uzbekistan OS home">
        Uzbekistan OS
      </Link>

      <div className="signup-layout">
        <section className="signup-value" aria-labelledby="signup-value-title">
          <p className="section-kicker">Personal visa guidance</p>
          <h1 id="signup-value-title">
            Your Uzbekistan visa plan starts here.
          </h1>
          <p>
            Create one account, answer a short set of questions, and receive a
            visa path tailored to your passport, purpose, sponsor, and intended
            stay.
          </p>
          <ul>
            {planBenefits.map((benefit) => (
              <li key={benefit}>
                <span aria-hidden="true">✓</span>
                {benefit}
              </li>
            ))}
          </ul>
        </section>

        <section className="signup-card" aria-labelledby="signup-card-title">
          <span className="signup-icon">
            <Image
              alt=""
              height={28}
              src="/landing/feature-official.svg"
              width={28}
            />
          </span>
          <p className="signup-step">Progressive account</p>
          <h2 id="signup-card-title">Create your free account</h2>
          <p>
            Keep your conversations and personalized visa plan available across
            devices. Start with your Uzbekistan mobile number.
          </p>
          <AuthForm />
          <Link className="pill pill-light signup-guest" href="/chat">
            Continue as guest
          </Link>
          <Link className="signup-back" href="/">
            Return to visa guide
          </Link>
        </section>
      </div>
    </main>
  );
}
