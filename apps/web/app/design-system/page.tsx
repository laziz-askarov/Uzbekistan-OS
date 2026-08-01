import {
  Alert,
  Badge,
  Button,
  Card,
  SelectField,
  Stack,
  TextField,
} from "@uzbekistan-os/design-system";

import styles from "./page.module.css";
import { ThemeToggle } from "./theme-toggle";

export const metadata = {
  description:
    "The accessible, iOS-inspired visual foundation for Uzbekistan OS.",
  title: "Design system | Uzbekistan OS",
};

const principles = [
  {
    index: "01",
    title: "Clear hierarchy",
    description:
      "Content leads. Scale, spacing, and restrained depth make the next action obvious.",
  },
  {
    index: "02",
    title: "Familiar by default",
    description:
      "Native controls and platform typography reduce learning and preserve expected behavior.",
  },
  {
    index: "03",
    title: "Flexible for everyone",
    description:
      "Every surface reflows, supports multiple inputs, and keeps context through change.",
  },
  {
    index: "04",
    title: "Calmly delightful",
    description:
      "Purposeful color and gentle motion add warmth without competing with the task.",
  },
];

export default function DesignSystemPage() {
  return (
    <div className={styles.page}>
      <a className={styles.skipLink} href="#main-content">
        Skip to content
      </a>

      <header className={styles.topbar}>
        <a
          aria-label="Uzbekistan OS design system home"
          className={styles.brand}
          href="#top"
        >
          <span aria-hidden="true" className={styles.brandMark}>
            U
          </span>
          <span>Uzbekistan OS</span>
        </a>
        <nav aria-label="Design system sections" className={styles.nav}>
          <a href="#principles">Principles</a>
          <a href="#components">Components</a>
          <a href="#patterns">Patterns</a>
        </nav>
        <div className={styles.topbarStatus}>
          <ThemeToggle className={styles.themeToggle} />
          <Badge tone="success">Foundation 02</Badge>
        </div>
      </header>

      <main className={styles.main} id="main-content">
        <section className={styles.hero} id="top">
          <div className={styles.heroCopy}>
            <p className={styles.eyebrow}>Human interface foundation</p>
            <h1>Familiar. Focused. Made for people.</h1>
            <p className={styles.lede}>
              A calm, accessible visual language that helps people find trusted
              guidance and complete important tasks with confidence.
            </p>
            <div className={styles.heroActions}>
              <a className={styles.primaryLink} href="#components">
                Explore components <span aria-hidden="true">↓</span>
              </a>
              <a className={styles.secondaryLink} href="#principles">
                View principles
              </a>
            </div>
          </div>

          <div
            aria-label="Layered interface material example"
            className={styles.materialStage}
          >
            <span aria-hidden="true" className={styles.orbOne} />
            <span aria-hidden="true" className={styles.orbTwo} />
            <article className={styles.workflowPreview}>
              <div className={styles.previewTopline}>
                <Badge tone="success">Verified guidance</Badge>
                <span>3 of 5</span>
              </div>
              <p className={styles.previewEyebrow}>Your workflow</p>
              <h2>Register a business</h2>
              <p className={styles.previewCopy}>
                Continue where you left off. Your progress is saved.
              </p>
              <ol className={styles.stepList}>
                <li className={styles.stepComplete}>
                  <span aria-hidden="true">✓</span>
                  Confirm eligibility
                </li>
                <li className={styles.stepCurrent}>
                  <span aria-hidden="true">2</span>
                  Prepare documents
                </li>
                <li>
                  <span aria-hidden="true">3</span>
                  Submit application
                </li>
              </ol>
            </article>
            <div aria-hidden="true" className={styles.floatingUtility}>
              <span>‹</span>
              <strong>Workflow</strong>
              <span>•••</span>
            </div>
          </div>
        </section>

        <section
          aria-labelledby="principles-heading"
          className={styles.section}
          id="principles"
        >
          <div className={styles.sectionIntro}>
            <p className={styles.eyebrow}>Design principles</p>
            <h2 id="principles-heading">Simple enough to feel natural.</h2>
            <p>
              We use platform conventions as a foundation, then express the
              clarity, trust, and hospitality of Uzbekistan OS.
            </p>
          </div>
          <div className={styles.principleGrid}>
            {principles.map((principle) => (
              <article className={styles.principleCard} key={principle.index}>
                <span>{principle.index}</span>
                <h3>{principle.title}</h3>
                <p>{principle.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section
          aria-labelledby="components-heading"
          className={styles.section}
          id="components"
        >
          <div className={styles.sectionIntro}>
            <p className={styles.eyebrow}>Core components</p>
            <h2 id="components-heading">Controls that explain themselves.</h2>
            <p>
              Generous targets, direct labels, immediate feedback, and familiar
              behavior across touch, pointer, keyboard, and assistive
              technology.
            </p>
          </div>

          <div className={styles.componentGrid}>
            <Card
              aria-labelledby="actions-heading"
              className={styles.componentCard}
            >
              <div className={styles.cardHeading}>
                <div>
                  <Badge>Actions</Badge>
                  <h3 id="actions-heading">Buttons</h3>
                </div>
                <span>48px comfort target</span>
              </div>
              <div className={styles.buttonStage}>
                <Button>Continue</Button>
                <Button variant="secondary">Save draft</Button>
                <Button variant="danger">Delete</Button>
                <Button disabled>Unavailable</Button>
              </div>
            </Card>

            <Card
              aria-labelledby="form-heading"
              className={styles.componentCard}
            >
              <div className={styles.cardHeading}>
                <div>
                  <Badge>Input</Badge>
                  <h3 id="form-heading">Profile fields</h3>
                </div>
                <span>Labels stay visible</span>
              </div>
              <Stack gap="lg">
                <TextField
                  autoComplete="name"
                  defaultValue="Dilnoza Karimova"
                  hint="Use the name shown on your official document."
                  id="full-name"
                  label="Full name"
                  name="fullName"
                />
                <SelectField
                  defaultValue="uz"
                  id="preferred-language"
                  label="Preferred language"
                  name="preferredLanguage"
                >
                  <option value="uz">O‘zbekcha</option>
                  <option value="ru">Русский</option>
                  <option value="en">English</option>
                </SelectField>
                <TextField
                  error="Enter a valid email address."
                  id="email-example"
                  label="Email address"
                  name="email"
                  readOnly
                  type="email"
                  value="not-an-email"
                />
              </Stack>
            </Card>
          </div>
        </section>

        <section
          aria-labelledby="patterns-heading"
          className={styles.section}
          id="patterns"
        >
          <div className={styles.sectionIntro}>
            <p className={styles.eyebrow}>Feedback and state</p>
            <h2 id="patterns-heading">Always know what happened.</h2>
            <p>
              State is written plainly, paired with semantic color, and
              announced without unexpectedly moving focus.
            </p>
          </div>
          <div className={styles.alertGrid}>
            <Alert
              message="The draft passed validation."
              title="Ready for review"
            />
            <Alert
              message="Confirm the source publication date."
              title="Action required"
              tone="warning"
            />
            <Alert
              message="Try again or contact support if the issue continues."
              title="Could not save"
              tone="error"
            />
          </div>

          <Card aria-labelledby="status-heading" className={styles.statusCard}>
            <div>
              <p className={styles.previewEyebrow}>Status language</p>
              <h3 id="status-heading">Meaning before decoration</h3>
              <p>
                Every color has one job. Text always carries the meaning, so
                state remains clear in every appearance and contrast mode.
              </p>
            </div>
            <div className={styles.badgeStage}>
              <Badge>Draft</Badge>
              <Badge tone="success">Verified source</Badge>
              <Badge tone="warning">In progress</Badge>
              <Badge tone="danger">Needs attention</Badge>
            </div>
          </Card>
        </section>
      </main>

      <footer className={styles.footer}>
        <div>
          <strong>Uzbekistan OS</strong>
          <span>Accessible by design.</span>
        </div>
        <span>Phase 2 visual foundation · 2026</span>
      </footer>
    </div>
  );
}
