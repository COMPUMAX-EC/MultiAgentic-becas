import { ScholarshipResult } from "../types/scholarship";

type ScholarshipRowProps = {
  result: ScholarshipResult;
};

export function ScholarshipRow({ result }: ScholarshipRowProps) {
  const sourceUrl = (result.display_link || result.source_url).trim();
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
