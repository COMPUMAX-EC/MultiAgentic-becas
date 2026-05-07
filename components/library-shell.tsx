import { ProfileForm } from "./ProfileForm";

export function HoneycombShell() {
  return (
    <main className="page-shell honeycomb-surface">
      <section className="content-frame">
        <header className="site-header" aria-label="Scholarship finder intro">
          <div className="hero-copy-block">
            <p className="eyebrow">Scholarship finder</p>
            <h1>Find the scholarships that fit your next move.</h1>
            <p className="hero-copy">
              Tell us who you are, what you want to study, and where you want to
              go. We will prepare a focused list without accounts, dashboards,
              or extra ceremony.
            </p>
          </div>

          <div className="honey-mark" aria-hidden="true">
            <span />
            <span />
            <span />
            <span />
            <span />
          </div>
        </header>

        <section className="workflow-card" aria-label="Scholarship profile flow">
          <div className="workflow-card-header">
            <ProfileForm />
          </div>
        </section>
      </section>
    </main>
  );
}

export const LibraryShell = HoneycombShell;
