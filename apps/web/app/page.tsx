const domains = [
  {
    title: "Immigration",
    description: "Visas, permits, and arrival requirements",
  },
  {
    title: "Tourism",
    description: "Plan visits with verified official guidance",
  },
  {
    title: "Business",
    description: "Understand registration steps and requirements",
  },
  {
    title: "Healthcare",
    description: "Find reliable access and procedure information",
  },
  {
    title: "Everyday living",
    description: "Navigate essential services and daily life",
  },
];

export default function HomePage() {
  return (
    <main>
      <header className="site-header">
        <a className="brand" href="#top" aria-label="Uzbekistan OS home">
          <span className="brand-mark" aria-hidden="true">
            U
          </span>
          <span>Uzbekistan OS</span>
        </a>
        <nav aria-label="Primary navigation">
          <a href="#domains">Explore</a>
          <a href="#principles">How it works</a>
        </nav>
      </header>

      <section className="hero" id="top" aria-labelledby="hero-title">
        <p className="eyebrow">Official sources. Clear next steps.</p>
        <h1 id="hero-title">Navigate Uzbekistan with confidence.</h1>
        <p className="hero-copy">
          Ask questions and follow guided workflows backed by verified, current
          sources. English, Uzbek, and Russian support is being built into every
          experience.
        </p>
        <div className="prompt-shell" aria-label="Assistant preview">
          <span>What do you need help with?</span>
          <button type="button" disabled aria-describedby="preview-note">
            Ask Uzbekistan OS
          </button>
        </div>
        <p className="preview-note" id="preview-note">
          The assistant will be enabled after the evidence pipeline is
          connected.
        </p>
      </section>

      <section className="section" id="domains" aria-labelledby="domains-title">
        <div className="section-heading">
          <p className="eyebrow">MVP coverage</p>
          <h2 id="domains-title">Five focused domains</h2>
        </div>
        <div className="domain-grid">
          {domains.map((domain) => (
            <article className="domain-card" key={domain.title}>
              <h3>{domain.title}</h3>
              <p>{domain.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section
        className="trust-section"
        id="principles"
        aria-labelledby="principles-title"
      >
        <div>
          <p className="eyebrow">Built for trust</p>
          <h2 id="principles-title">Answers should show their work.</h2>
        </div>
        <ul>
          <li>
            <strong>Verified evidence</strong>
            <span>
              Only eligible, reviewed knowledge can support an answer.
            </span>
          </li>
          <li>
            <strong>Visible citations</strong>
            <span>
              Every factual claim should trace back to an official source.
            </span>
          </li>
          <li>
            <strong>Safe uncertainty</strong>
            <span>
              When evidence is missing or conflicting, the assistant says so.
            </span>
          </li>
        </ul>
      </section>

      <footer>
        <span>Uzbekistan OS MVP</span>
        <span>Foundation milestone</span>
      </footer>
    </main>
  );
}
