"use client";

import { FormEvent, useEffect, useState } from "react";
import { BackendStatus } from "./BackendStatus";
import { ProgressLogLine, ProgressPanel } from "./ProgressPanel";
import { ScholarshipRow } from "./ScholarshipRow";
import {
  getLatestDemoResponse,
  searchScholarshipsWithProfileInput,
} from "../services/scholarshipApi";
import { ScholarshipResult, WorkflowStep, WorkflowStepStatus } from "../types/scholarship";

const LESS_RECOMMENDED_DISPLAY_LIMIT = 10;

type PipelineTemplate = {
  id: string;
  label: string;
  log: () => string;
};

const PIPELINE: PipelineTemplate[] = [
  {
    id: "profile",
    label: "Reading profile input",
    log: () => "Profile input received.",
  },
  {
    id: "normalize",
    label: "Normalizing profile",
    log: () => "Preparing a normalized profile.",
  },
  {
    id: "intent",
    label: "Building search intent",
    log: () => "Waiting for backend search intent.",
  },
  {
    id: "queries",
    label: "Generating global scholarship queries",
    log: () => "Waiting for backend query generation.",
  },
  {
    id: "search",
    label: "Searching global sources",
    log: () => "Waiting for backend source search.",
  },
  {
    id: "dedupe",
    label: "Deduplicating candidates",
    log: () => "Waiting for backend candidate deduplication.",
  },
  {
    id: "validate",
    label: "Validating trusted sources",
    log: () => "Waiting for backend source validation.",
  },
  {
    id: "read-pages",
    label: "Reading scholarship pages",
    log: () => "Waiting for backend page reading.",
  },
  {
    id: "extract",
    label: "Extracting scholarship data",
    log: () => "Waiting for backend extraction.",
  },
  {
    id: "links",
    label: "Resolving useful links",
    log: () => "Waiting for backend link resolution.",
  },
  {
    id: "score",
    label: "Scoring compatibility",
    log: () => "Waiting for backend compatibility scoring.",
  },
  {
    id: "rank",
    label: "Ranking recommendations",
    log: () => "Waiting for backend ranking.",
  },
  {
    id: "final",
    label: "Preparing final results",
    log: () => "Search completed.",
  },
];

const initialSteps = createSteps(-1);

type ScholarshipResultsProps = {
  results: ScholarshipResult[];
};

export function ScholarshipSearchExperience() {
  const [profileText, setProfileText] = useState("");
  const [profileError, setProfileError] = useState("");
  const [runId, setRunId] = useState(0);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [isRunning, setIsRunning] = useState(false);
  const [isLoadingDemo, setIsLoadingDemo] = useState(false);
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const [logs, setLogs] = useState<ProgressLogLine[]>([]);
  const [results, setResults] = useState<ScholarshipResult[]>([]);
  const [backendWorkflowSteps, setBackendWorkflowSteps] = useState<WorkflowStep[]>([]);
  const [pageMessage, setPageMessage] = useState("");
  const [missingRequiredFields, setMissingRequiredFields] = useState<string[]>([]);
  const [inputWarning, setInputWarning] = useState("");

  const visibleSteps = backendWorkflowSteps.length
    ? backendWorkflowSteps
    : hasSubmitted
      ? createSteps(activeIndex)
      : initialSteps;
  const showResults = hasSubmitted && !isRunning && results.length > 0;
  const showMessage = hasSubmitted && !isRunning && Boolean(pageMessage);

  useEffect(() => {
    if (!isRunning || !hasSubmitted) {
      return;
    }

    setActiveIndex(0);
    setLogs([]);

    let stepIndex = 0;
    const intervalId = window.setInterval(() => {
      const step = PIPELINE[stepIndex];
      if (!step) {
        setActiveIndex(PIPELINE.length - 1);
        setLogs((currentLogs) =>
          currentLogs.some((log) => log.id === `${runId}-waiting-backend`)
            ? currentLogs
            : [
                ...currentLogs,
                {
                  id: `${runId}-waiting-backend`,
                  message:
                    "Waiting for backend search response. Global search can take several minutes.",
                  tone: "warning",
                },
              ],
        );
        return;
      }

      setActiveIndex(stepIndex);
      setLogs((currentLogs) => [
        ...currentLogs,
        {
          id: `${runId}-${step.id}`,
          message: step.log(),
          tone: step.id === "final" ? "success" : "default",
        },
      ]);

      stepIndex += 1;
    }, 620);

    return () => window.clearInterval(intervalId);
  }, [hasSubmitted, isRunning, runId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isRunning) {
      return;
    }

    const trimmedProfile = profileText.trim();
    if (!trimmedProfile) {
      setProfileError("Describe your profile before submitting.");
      return;
    }

    setProfileError("");
    setPageMessage("");
    setMissingRequiredFields([]);
    setInputWarning("");
    setBackendWorkflowSteps([]);
    setResults([]);
    setActiveIndex(-1);
    setHasSubmitted(true);
    setIsRunning(true);
    setRunId((currentRunId) => currentRunId + 1);

    try {
      const response = await searchScholarshipsWithProfileInput({
        rawProfileText: trimmedProfile,
      });

      setInputWarning("");
      setMissingRequiredFields(response.missingRequiredFields);

      if (!response.results.length) {
        const missingMessage = response.missingRequiredFields.length
          ? `Missing required fields: ${response.missingRequiredFields
              .map(formatMissingField)
              .join(", ")}.`
          : "";
        setBackendWorkflowSteps(
          response.workflowSteps.length
            ? response.workflowSteps
            : createFailedSteps(activeIndex),
        );
        setPageMessage(
          response.isUnsupportedShape
            ? "The backend responded, but recommendations could not be read."
            : missingMessage ||
                response.message ||
                response.warnings[0] ||
                "No live scholarship recommendations are available for this profile yet.",
        );
        setLogs((currentLogs) => [
          ...currentLogs,
          ...response.workflowLogs.map((logMessage, index) => ({
            id: `${Date.now()}-backend-empty-log-${index}`,
            message: logMessage,
            tone: "default" as const,
          })),
          ...response.warnings.map((warning, index) => ({
            id: `${Date.now()}-empty-warning-${index}`,
            message: warning,
            tone: "warning" as const,
          })),
          ...(missingMessage
            ? [
                {
                  id: `${Date.now()}-missing-fields`,
                  message: missingMessage,
                  tone: "warning" as const,
                },
              ]
            : []),
        ]);
        return;
      }

      setResults(response.results);
      setBackendWorkflowSteps(response.workflowSteps);
      setActiveIndex(PIPELINE.length);
      setLogs((currentLogs) => [
        ...currentLogs,
        ...response.workflowLogs.map((logMessage, index) => ({
          id: `${Date.now()}-backend-log-${index}`,
          message: logMessage,
          tone: "default" as const,
        })),
        ...response.warnings.map((warning, index) => ({
          id: `${Date.now()}-warning-${index}`,
          message: warning,
          tone: "warning" as const,
        })),
        {
          id: `${Date.now()}-backend-complete`,
          message: `Backend search returned ${response.results.length} scholarship results.`,
          tone: "success",
        },
      ]);

      if (response.isPartialFailure) {
        setPageMessage(
          "The backend returned partial results. You can review the available scholarships or retry the search.",
        );
      }
    } catch (error) {
      setBackendWorkflowSteps(createFailedSteps(activeIndex));
      setPageMessage(getReadableErrorMessage(error));
      setLogs((currentLogs) => [
        ...currentLogs,
        {
          id: `${Date.now()}-backend-error`,
          message: getReadableErrorMessage(error),
          tone: "error",
        },
      ]);
    } finally {
      setIsRunning(false);
    }
  }

  async function handleLoadLatestDemo() {
    setIsLoadingDemo(true);
    setPageMessage("");

    try {
      const response = await getLatestDemoResponse();
      if (!response.results.length) {
        setPageMessage("No saved demo recommendations were available.");
        return;
      }

      setHasSubmitted(true);
      setIsRunning(false);
      setActiveIndex(PIPELINE.length);
      setBackendWorkflowSteps(response.workflowSteps);
      setResults(response.results);
      setLogs((currentLogs) => [
        ...currentLogs,
        {
          id: `${Date.now()}-demo-loaded`,
          message: `Loaded ${response.results.length} recommendations from saved demo results.`,
          tone: "success",
        },
      ]);
    } catch (error) {
      setPageMessage(getReadableErrorMessage(error));
    } finally {
      setIsLoadingDemo(false);
    }
  }

  function handleTryAgain() {
    if (!isRunning) {
      void handleSubmit({
        preventDefault() {
          return undefined;
        },
      } as FormEvent<HTMLFormElement>);
    }
  }

  function handleClearForm() {
    if (isRunning) {
      return;
    }
    setProfileText("");
    setProfileError("");
    setHasSubmitted(false);
    setPageMessage("");
    setMissingRequiredFields([]);
    setInputWarning("");
    setBackendWorkflowSteps([]);
    setResults([]);
    setLogs([]);
    setActiveIndex(-1);
  }

  const quickActions = (
    <>
      <button
        className="quick-action quick-action-primary"
        type="submit"
        disabled={isRunning || isLoadingDemo}
      >
        {isRunning ? "Searching..." : "Start search"}
      </button>
      <button
        className="quick-action"
        type="button"
        onClick={handleClearForm}
        disabled={isRunning || isLoadingDemo}
      >
        Clear form
      </button>
      {hasSubmitted ? (
        <button
          className="quick-action"
          type="button"
          onClick={handleTryAgain}
          disabled={isRunning || isLoadingDemo}
        >
          Retry search
        </button>
      ) : null}
      <button
        className="quick-action"
        type="button"
        onClick={handleLoadLatestDemo}
        disabled={isRunning || isLoadingDemo}
      >
        {isLoadingDemo ? "Loading..." : "Load saved demo"}
      </button>
    </>
  );

  return (
    <main className="page-shell scholarbee-surface">
      <header className="site-header" aria-label="ScholarBee header">
        <div className="brand-lockup">
          <div className="bee-mark" aria-hidden="true">
            <span />
          </div>
          <div>
            <p className="eyebrow">AI Scholarship Search</p>
            <h1>ScholarBee</h1>
          </div>
        </div>
        <BackendStatus />
      </header>

      <section className="content-frame">
        <div className="dashboard-intro">
          <div>
            <p className="section-kicker">Global scholarship finder</p>
            <h2>Find scholarships that fit your profile, then open the source.</h2>
          </div>
          <p>
            Add your written profile and watch the live search pipeline move
            from profile understanding to ranked results.
          </p>
        </div>

        <form className="profile-form" onSubmit={handleSubmit}>
          <section className="dashboard-grid" aria-label="ScholarBee dashboard">
            <div className="input-panel">
              <p className="section-kicker">Profile input</p>
              <h3>Ingresa tu perfil y el tipo de beca al que tú quieres aplicar</h3>
              <p className="input-helper">
                Escribe tu nacionalidad o país, idioma(s), tipo de beca, meta
                académica, destino, área de estudio, presupuesto o modalidad si aplica.
              </p>
              <p className="minimum-guidance">
                Para buscar, incluye mínimo país o nacionalidad, idioma(s) y tipo de beca.
              </p>

              <label className="field-group profile-textarea">
                <span>Profile and scholarship intent</span>
                <textarea
                  value={profileText}
                  onChange={(event) => {
                    setProfileText(event.target.value);
                    setProfileError("");
                  }}
                  placeholder="Soy estudiante colombiano de ingeniería de sistemas, hablo español e inglés B2, busco beca completa para maestría en inteligencia artificial en Canadá..."
                />
                <small>
                  One clear paragraph is enough. ScholarBee uses only this written profile text.
                </small>
              </label>

              {profileError ? <p className="form-error">{profileError}</p> : null}
              {missingRequiredFields.length ? (
                <div className="missing-fields-panel" role="status">
                  <strong>Missing required fields</strong>
                  <ul>
                    {missingRequiredFields.map((field) => (
                      <li key={field}>{formatMissingField(field)}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {inputWarning ? <p className="form-warning">{inputWarning}</p> : null}

              <button className="form-submit" type="submit" disabled={isRunning}>
                {isRunning ? "Searching globally..." : "Search scholarships"}
              </button>
            </div>

            <ProgressPanel
              steps={visibleSteps}
              logs={logs}
              isRunning={isRunning}
              actions={quickActions}
            />
          </section>

          {showMessage ? (
            <section className="message-panel message-panel-warning" role="status">
              <div>
                <p className="section-kicker">Search status</p>
                <p>{pageMessage}</p>
              </div>
            </section>
          ) : null}

          <ScholarshipResults results={showResults ? results : []} />
        </form>
      </section>
    </main>
  );
}

export function ScholarshipResults({ results }: ScholarshipResultsProps) {
  if (!results.length) {
    return (
      <section className="results-section" aria-label="Scholarship results">
        <div className="results-heading">
          <p className="section-kicker">Results</p>
          <h3>Scholarship matches</h3>
        </div>
        <div className="result-columns">
          <ResultGroup
            title="Recommended Scholarships"
            results={[]}
            emptyMessage="No recommended scholarships yet."
          />
          <ResultGroup
            title="Less Recommended"
            results={[]}
            emptyMessage="No less recommended scholarships yet."
            secondary
          />
        </div>
      </section>
    );
  }

  const uniqueResults = dedupeScholarships(results);
  const hasHighOrMediumRecommendation = uniqueResults.some((result) =>
    ["high_priority", "medium_priority"].includes(result.priority_label),
  );
  const recommendedResults = sortResults(
    uniqueResults.filter((result) =>
      isRecommended(result, hasHighOrMediumRecommendation),
    ),
  );
  const lessRecommendedResults = sortResults(
    uniqueResults.filter(
      (result) => !isRecommended(result, hasHighOrMediumRecommendation),
    ),
  ).slice(0, LESS_RECOMMENDED_DISPLAY_LIMIT);

  return (
    <section className="results-section" aria-label="Scholarship results">
      <div className="results-heading">
        <p className="section-kicker">Results</p>
        <h3>Scholarship matches</h3>
      </div>

      <div className="result-columns">
        <ResultGroup
          title="Recommended Scholarships"
          results={recommendedResults}
          emptyMessage="No recommended scholarships were found."
        />
        <ResultGroup
          title="Less Recommended"
          results={lessRecommendedResults}
          emptyMessage="No additional scholarships were found."
          secondary
        />
      </div>
    </section>
  );
}

function ResultGroup({
  title,
  results,
  emptyMessage,
  secondary = false,
}: {
  title: string;
  results: ScholarshipResult[];
  emptyMessage: string;
  secondary?: boolean;
}) {
  return (
    <section className={`result-group${secondary ? " result-group-secondary" : ""}`}>
      <div className="result-group-header">
        <h4>{title}</h4>
        <span>{results.length}</span>
      </div>
      {results.length ? (
        <ul className="scholarship-list">
          {results.map((result) => (
            <ScholarshipRow key={getScholarshipKey(result)} result={result} />
          ))}
        </ul>
      ) : (
        <p className="empty-results">{emptyMessage}</p>
      )}
    </section>
  );
}

function isRecommended(
  result: ScholarshipResult,
  hasHighOrMediumRecommendation: boolean,
) {
  if (result.result_section === "recommended") {
    return true;
  }
  if (result.result_section === "less_recommended") {
    return false;
  }

  if (["high_priority", "medium_priority", "possible_match"].includes(result.priority_label)) {
    return true;
  }

  return (
    !hasHighOrMediumRecommendation &&
    result.priority_label === "low_priority" &&
    result.final_score >= 45
  );
}

function dedupeScholarships(results: ScholarshipResult[]) {
  const seen = new Set<string>();
  const uniqueResults: ScholarshipResult[] = [];

  for (const result of results) {
    const key = getScholarshipKey(result);
    if (seen.has(key)) {
      continue;
    }

    seen.add(key);
    uniqueResults.push(result);
  }

  return uniqueResults;
}

function getScholarshipKey(result: ScholarshipResult) {
  const link = getResultDisplayLink(result).toLowerCase();
  if (link && link !== "#") {
    return `link:${link}`;
  }

  return `name:${result.scholarship_name.trim().toLowerCase()}`;
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

function sortResults(results: ScholarshipResult[]) {
  return [...results].sort(
    (firstResult, secondResult) =>
      secondResult.final_score - firstResult.final_score ||
      secondResult.compatibility_score - firstResult.compatibility_score ||
      getSortRank(firstResult) - getSortRank(secondResult),
  );
}

function getSortRank(result: ScholarshipResult) {
  return typeof result.rank === "number" && Number.isFinite(result.rank)
    ? result.rank
    : Number.MAX_SAFE_INTEGER;
}

function createSteps(activeIndex: number): WorkflowStep[] {
  return PIPELINE.map((step, index) => ({
    id: step.id,
    label: step.label,
    status: getStatus(index, activeIndex),
    message: getStepMessage(step, index, activeIndex),
  }));
}

function getStatus(index: number, activeIndex: number): WorkflowStepStatus {
  if (activeIndex >= PIPELINE.length || index < activeIndex) {
    return "completed";
  }
  if (index === activeIndex) {
    return "active";
  }
  return "pending";
}

function getStepMessage(
  step: PipelineTemplate,
  index: number,
  activeIndex: number,
) {
  if (index > activeIndex && activeIndex < PIPELINE.length) {
    return "Waiting for previous step.";
  }

  return step.log();
}

function createFailedSteps(activeIndex: number): WorkflowStep[] {
  const failedIndex = Math.max(0, Math.min(activeIndex, PIPELINE.length - 1));

  return createSteps(failedIndex).map((step, index) => {
    if (index === failedIndex) {
      return {
        ...step,
        status: "failed",
        message: "Backend search could not complete this step.",
      };
    }

    return step;
  });
}

function formatMissingField(field: string) {
  return field.replaceAll("_", " ");
}

function getReadableErrorMessage(error: unknown) {
  if (!(error instanceof Error)) {
    return "The backend request failed.";
  }
  if (error.message.includes("timed out")) {
    return "The backend took too long to respond.";
  }
  if (error.message.includes("invalid JSON")) {
    return "The backend returned an unreadable response.";
  }
  if (error.message.includes("unavailable")) {
    return "The backend is unavailable right now.";
  }
  return error.message;
}
