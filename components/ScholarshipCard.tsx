"use client";

import { useState } from "react";
import { ScholarshipResult } from "../types/scholarship";
import { ScholarshipDetails } from "./ScholarshipDetails";

type ScholarshipCardProps = {
  result: ScholarshipResult;
};

export function ScholarshipCard({ result }: ScholarshipCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const topRankingReasons = result.ranking_reasons.slice(0, 3);

  return (
    <article className="scholarship-card">
      <div className="scholarship-card-header">
        <div>
          <p className="priority-label">{formatPriorityLabel(result.priority_label)}</p>
          <h6>{result.scholarship_name}</h6>
        </div>
        <span className="score-badge" aria-label={`Final score ${result.final_score} out of 100`}>
          {result.final_score}/100
        </span>
      </div>

      <p className="institution-line">
        {result.institution} / {result.country}
      </p>
      <p className="recommendation-copy">{result.recommendation_summary}</p>

      <dl className="score-list">
        <div>
          <dt>Final score</dt>
          <dd>{result.final_score}/100</dd>
        </div>
        <div>
          <dt>Compatibility</dt>
          <dd>{result.compatibility_score}/100</dd>
        </div>
        <div>
          <dt>Priority</dt>
          <dd>{formatPriorityLabel(result.priority_label)}</dd>
        </div>
        <div>
          <dt>Eligibility</dt>
          <dd>{formatDecision(result.eligibility_decision)}</dd>
        </div>
      </dl>

      <DetailList title="Top ranking reasons" items={topRankingReasons} />
      <DetailList title="Missing requirements" items={result.missing_requirements} />
      <DetailList title="Risk factors" items={result.risk_factors} />

      <a
        className="official-link"
        href={result.source_url}
        target="_blank"
        rel="noopener noreferrer"
      >
        Open official source
      </a>

      <button
        className="details-toggle"
        type="button"
        aria-expanded={isExpanded}
        onClick={() => setIsExpanded((currentValue) => !currentValue)}
      >
        {isExpanded ? "Hide details" : "View details"}
      </button>

      {isExpanded ? <ScholarshipDetails result={result} /> : null}
    </article>
  );
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

function formatPriorityLabel(label: string) {
  return label
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatDecision(decision: string) {
  return decision
    .replaceAll("_", " ")
    .replace(/^\w/, (firstLetter) => firstLetter.toUpperCase());
}
