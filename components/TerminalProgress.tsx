"use client";

import { FormEvent, useEffect, useState } from "react";
import { ProgressLogLine, ProgressPanel } from "./ProgressPanel";
import { mockScholarships } from "../src/data/mockScholarships";
import {
  getLatestDemoResponse,
  searchScholarshipsWithProfileInput,
} from "../services/scholarshipApi";
import {
  ScholarshipResult,
  WorkflowStep,
  WorkflowStepStatus,
} from "../types/scholarship";

type PipelineTemplate = {
  id: string;
  label: string;
  count?: number;
  countLabel?: string;
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
    log: () => "Preparing a normalized profile from the submitted text.",
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

export function TerminalProgressWorkflow() {
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

  const visibleSteps = backendWorkflowSteps.length
    ? backendWorkflowSteps
    : hasSubmitted
      ? createSteps(activeIndex)
      : initialSteps;
  const showResults = hasSubmitted && !isRunning && results.length > 0;
  const showFallbackActions = hasSubmitted && !isRunning && Boolean(pageMessage);

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
        setLogs((currentLogs) => {
          if (currentLogs.some((log) => log.id === `${runId}-waiting-backend`)) {
            return currentLogs;
          }

          return [
            ...currentLogs,
            {
              id: `${runId}-waiting-backend`,
              message: "Waiting for backend search response. Global search can take several minutes.",
              tone: "warning",
            },
          ];
        });
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
    const trimmedProfile = profileText.trim();

    if (!trimmedProfile) {
      setProfileError("Describe your profile and scholarship goals before submitting.");
      return;
    }

    setProfileError("");
    setHasSubmitted(true);
    setPageMessage("");
    setBackendWorkflowSteps([]);
    setResults([]);
    setActiveIndex(-1);
    setIsRunning(true);
    setRunId((currentRunId) => currentRunId + 1);

    try {
      const response = await searchScholarshipsWithProfileInput({
        rawProfileText: trimmedProfile,
      });

      if (!response.results.length) {
        setResults([]);
        setBackendWorkflowSteps(
          response.workflowSteps.length
            ? response.workflowSteps
            : createFailedSteps(activeIndex),
        );
        setPageMessage(
          response.isUnsupportedShape
            ? "The backend responded, but recommendations could not be read."
            : response.warnings[0] ||
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
          {
            id: `${Date.now()}-no-results`,
            message: "No live recommendations were returned for this profile.",
            tone: "warning",
          },
        ]);
        return;
      }

      setResults(response.results);
      setBackendWorkflowSteps(response.workflowSteps);
      setActiveIndex(PIPELINE.length);
      setLogs((currentLogs) => [
        ...currentLogs,
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
    } catch (error) {
      setResults([]);
      setBackendWorkflowSteps(createFailedSteps(activeIndex));
      setPageMessage(`${getReadableErrorMessage(error)} Choose a fallback option below.`);
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
        setPageMessage("No latest demo recommendations were available.");
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
      setPageMessage(`${getReadableErrorMessage(error)} You can still use sample results.`);
    } finally {
      setIsLoadingDemo(false);
    }
  }

  function handleUseSampleResults() {
    setHasSubmitted(true);
    setIsRunning(false);
    setActiveIndex(PIPELINE.length);
    setBackendWorkflowSteps([]);
    setResults(mockScholarships);
    setPageMessage("");
    setLogs((currentLogs) => [
      ...currentLogs,
      {
        id: `${Date.now()}-sample-results`,
        message: `Loaded ${mockScholarships.length} local sample scholarship results.`,
        tone: "success",
      },
    ]);
  }

  function handleTryAgain() {
    if (isRunning) {
      return;
    }

    const syntheticEvent = {
      preventDefault() {
        return undefined;
      },
    } as FormEvent<HTMLFormElement>;

    void handleSubmit(syntheticEvent);
  }

  return (
    <main className="page-shell honeycomb-surface">
      <section className="content-frame">
        <header className="site-header" aria-label="Scholarship finder intro">
          <div className="hero-copy-block">
            <p className="eyebrow">Global scholarship finder</p>
            <h1>Follow every search step, then open the source.</h1>
            <p className="hero-copy">
              Enter your written profile and watch a clear search pipeline
              before the recommendations appear.
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
          <form className="profile-form" onSubmit={handleSubmit}>
            <div className="input-panel">
              <p className="section-kicker">Profile input</p>
              <h2>Ingresa tu perfil y el tipo de beca al que tú quieres aplicar</h2>
              <p className="input-helper">
                Describe your academic profile, nationality, languages, study
                area, target countries, and scholarship goals.
              </p>

              <label className="field-group profile-textarea">
                <span>Your profile and scholarship goals</span>
                <textarea
                  value={profileText}
                  onChange={(event) => {
                    setProfileText(event.target.value);
                    setProfileError("");
                  }}
                  placeholder="Soy estudiante colombiano de ingeniería de sistemas, hablo español e inglés B2, quiero aplicar a becas de maestría en Canadá o Alemania para inteligencia artificial..."
                />
                <small>
                  Include your profile and scholarship intent here. The backend
                  receives this as raw_profile_text.
                </small>
              </label>

              {profileError ? <p className="form-error">{profileError}</p> : null}

              <button className="form-submit" type="submit" disabled={isRunning}>
                {isRunning ? "Searching globally..." : "Search scholarships"}
              </button>
            </div>

            <ProgressPanel steps={visibleSteps} logs={logs} isRunning={isRunning} />

            {showFallbackActions ? (
              <section className="message-panel message-panel-warning" role="status">
                <div>
                  <p className="section-kicker">Search status</p>
                  <p>{pageMessage}</p>
                </div>
                <div className="fallback-actions">
                  <button
                    className="official-link"
                    type="button"
                    onClick={handleTryAgain}
                    disabled={isRunning || isLoadingDemo}
                  >
                    Try again
                  </button>
                  <button
                    className="official-link"
                    type="button"
                    onClick={handleLoadLatestDemo}
                    disabled={isRunning || isLoadingDemo}
                  >
                    {isLoadingDemo ? "Loading..." : "Load saved demo results"}
                  </button>
                  <button
                    className="official-link"
                    type="button"
                    onClick={handleUseSampleResults}
                    disabled={isRunning || isLoadingDemo}
                  >
                    Use sample results
                  </button>
                </div>
              </section>
            ) : null}

            {showResults ? <ScholarshipResultLists results={results} /> : null}
          </form>
        </section>
      </section>
    </main>
  );
}

function ScholarshipResultLists({ results }: { results: ScholarshipResult[] }) {
  const recommendedResults = sortResults(
    results.filter((result) =>
      isRecommended(result.priority_label),
    ),
  );
  const lessRecommendedResults = sortResults(
    results.filter((result) => !isRecommended(result.priority_label)),
  );

  return (
    <section className="results-section" aria-label="Scholarship results">
      <div className="results-heading">
        <p className="section-kicker">Results</p>
        <h3>Scholarship matches</h3>
      </div>

      <ResultGroup title="Recomendadas" results={recommendedResults} />
      <ResultGroup title="No tan recomendadas" results={lessRecommendedResults} />
    </section>
  );
}

function ResultGroup({
  title,
  results,
}: {
  title: string;
  results: ScholarshipResult[];
}) {
  return (
    <section className="result-group">
      <h4>{title}</h4>
      {results.length ? (
        <ul className="scholarship-list">
          {results.map((result) => (
            <li className="scholarship-row" key={result.id}>
              <span>{result.scholarship_name}</span>
              {getResultDisplayLink(result) ? (
                <a
                  className="official-link"
                  href={getResultDisplayLink(result)}
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
          ))}
        </ul>
      ) : (
        <p className="empty-results">No scholarships in this group yet.</p>
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

function createSteps(activeIndex: number): WorkflowStep[] {
  return PIPELINE.map((step, index) => ({
    id: step.id,
    label: step.label,
    status: getStatus(index, activeIndex),
    count: index <= activeIndex || activeIndex >= PIPELINE.length ? step.count : undefined,
    countLabel: step.countLabel,
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

function sortResults(results: ScholarshipResult[]) {
  return [...results].sort(
    (firstResult, secondResult) =>
      secondResult.final_score - firstResult.final_score ||
      secondResult.compatibility_score - firstResult.compatibility_score,
  );
}

function isRecommended(priorityLabel: string) {
  return ["high_priority", "medium_priority"].includes(priorityLabel);
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
