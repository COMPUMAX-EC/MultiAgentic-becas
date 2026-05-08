import { ScholarshipResult } from "../types/scholarship";

type ScholarshipRowProps = {
  result: ScholarshipResult;
};

export function ScholarshipRow({ result }: ScholarshipRowProps) {
  const sourceUrl = getResultDisplayLink(result);
  const hasLink = Boolean(sourceUrl && sourceUrl !== "#");

  return (
    <li className="scholarship-row">
      <span className="scholarship-row-name">{result.scholarship_name}</span>
      {hasLink ? (
        <a
          className="official-link"
          href={sourceUrl}
          target="_blank"
          rel="noopener noreferrer"
        >
          Open
        </a>
      ) : (
        <button className="official-link official-link-disabled" type="button" disabled>
          No link
        </button>
      )}
    </li>
  );
}

function getResultDisplayLink(result: ScholarshipRowProps["result"]) {
  return (
    result.display_link ||
    result.official_link ||
    result.application_url ||
    result.source_url ||
    result.pdf_url ||
    ""
  ).trim();
}
