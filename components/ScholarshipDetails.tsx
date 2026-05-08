import { ScholarshipResult } from "../types/scholarship";

type ScholarshipDetailsProps = {
  result: ScholarshipResult;
};

export function ScholarshipDetails({ result }: ScholarshipDetailsProps) {
  const sourceUrl = getResultDisplayLink(result);

  return (
    <section className="scholarship-details" aria-label="Expanded scholarship details">
      <p className="card-label">Archival record</p>
      <p className="recommendation-copy">{result.recommendation_summary}</p>

      <dl className="details-meta">
        <div>
          <dt>Institution</dt>
          <dd>{result.institution}</dd>
        </div>
        <div>
          <dt>Country</dt>
          <dd>{result.country}</dd>
        </div>
        <div>
          <dt>Final score</dt>
          <dd>{result.final_score}/100</dd>
        </div>
        <div>
          <dt>Compatibility</dt>
          <dd>{result.compatibility_score}/100</dd>
        </div>
        <div>
          <dt>Eligibility decision</dt>
          <dd>{formatDecision(result.eligibility_decision)}</dd>
        </div>
        {result.deadline ? (
          <div>
            <dt>Deadline</dt>
            <dd>{result.deadline}</dd>
          </div>
        ) : null}
      </dl>

      <DetailList title="Ranking reasons" items={result.ranking_reasons} />
      <DetailList title="Missing requirements" items={result.missing_requirements} />
      <DetailList title="Risk factors" items={result.risk_factors} />
      <DetailList title="Benefits" items={result.benefits || []} />
      <DetailList title="Requirements" items={result.requirements || []} />
      <DetailList
        title="Eligible nationalities"
        items={result.eligible_nationalities || []}
      />
      <DetailList title="Required languages" items={result.required_languages || []} />
      <DetailList title="Fields" items={result.fields || []} />

      {sourceUrl ? (
        <a
          className="official-link"
          href={sourceUrl}
          target="_blank"
          rel="noopener noreferrer"
        >
          Open official source
        </a>
      ) : (
        <button className="official-link official-link-disabled" type="button" disabled>
          No link
        </button>
      )}
    </section>
  );
}

function getResultDisplayLink(result: ScholarshipResult) {
  return (
    result.display_link ||
    result.official_link ||
    result.application_url ||
    result.source_url ||
    result.pdf_url ||
    ""
  ).trim();
}

function formatDecision(decision: string) {
  return decision
    .replaceAll("_", " ")
    .replace(/^\w/, (firstLetter) => firstLetter.toUpperCase());
}

function DetailList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="detail-list">
      <p>{title}</p>
      {items.length ? (
        <ul>
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <span>None listed.</span>
      )}
    </div>
  );
}
