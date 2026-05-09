"use client";

import { FormEvent, useState } from "react";
import { ProgressLogLine, ProgressPanel } from "./ProgressPanel";
import { ScholarshipResults } from "./ScholarshipResults";
import { searchScholarshipsWithProfileInput } from "../services/scholarshipApi";
import { ScholarshipResult, WorkflowStep } from "../types/scholarship";

const INITIAL_STEPS: WorkflowStep[] = [
  {
    id: "profile",
    label: "Reading profile input",
    status: "pending",
    message: "Waiting for written profile text.",
  },
  {
    id: "normalize",
    label: "Normalizing profile",
    status: "pending",
    message: "Waiting for backend normalization.",
  },
  {
    id: "intent",
    label: "Building search intent",
    status: "pending",
    message: "Waiting for backend search intent.",
  },
  {
    id: "search",
    label: "Searching global sources",
    status: "pending",
    message: "Waiting for backend source search.",
  },
  {
    id: "rank",
    label: "Ranking recommendations",
    status: "pending",
    message: "Waiting for backend ranking.",
  },
];

export function ProfileForm() {
  const [profileText, setProfileText] = useState("");
  const [profileError, setProfileError] = useState("");
  const [pageMessage, setPageMessage] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const [scholarshipResults, setScholarshipResults] = useState<ScholarshipResult[]>([]);
  const [workflowSteps, setWorkflowSteps] = useState<WorkflowStep[]>(INITIAL_STEPS);
  const [logs, setLogs] = useState<ProgressLogLine[]>([]);
  const [missingRequiredFields, setMissingRequiredFields] = useState<string[]>([]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedProfile = profileText.trim();

    if (!trimmedProfile) {
      setProfileError("Describe your profile before submitting.");
      return;
    }

    setProfileError("");
    setPageMessage("");
    setMissingRequiredFields([]);
    setScholarshipResults([]);
    setWorkflowSteps(markInitialStepsRunning());
    setLogs([
      {
        id: `${Date.now()}-submit`,
        message: "Submitting written profile text to backend /search.",
      },
    ]);
    setHasSubmitted(true);
    setIsProcessing(true);

    try {
      const response = await searchScholarshipsWithProfileInput({
        rawProfileText: trimmedProfile,
      });

      setWorkflowSteps(response.workflowSteps.length ? response.workflowSteps : INITIAL_STEPS);
      setScholarshipResults(response.results);
      setMissingRequiredFields(response.missingRequiredFields);
      setLogs((currentLogs) => [
        ...currentLogs,
        ...response.workflowLogs.map((message, index) => ({
          id: `${Date.now()}-workflow-${index}`,
          message,
        })),
        ...response.warnings.map((message, index) => ({
          id: `${Date.now()}-warning-${index}`,
          message,
          tone: "warning" as const,
        })),
      ]);

      if (response.missingRequiredFields.length) {
        setPageMessage(
          `Missing required fields: ${response.missingRequiredFields
            .map(formatMissingField)
            .join(", ")}.`,
        );
      } else if (!response.results.length) {
        setPageMessage(
          response.message ||
            "No live scholarship recommendations are available for this profile yet.",
        );
      } else if (response.isPartialFailure) {
        setPageMessage("The backend returned partial results. Review available matches.");
      }
    } catch (error) {
      setWorkflowSteps(markInitialStepsFailed());
      setPageMessage(getReadableErrorMessage(error));
      setLogs((currentLogs) => [
        ...currentLogs,
        {
          id: `${Date.now()}-error`,
          message: getReadableErrorMessage(error),
          tone: "error",
        },
      ]);
    } finally {
      setIsProcessing(false);
    }
  }

  return (
    <form className="profile-form" onSubmit={handleSubmit}>
      <div className="input-panel">
        <p className="section-kicker">Profile input</p>
        <h2>Ingresa tu perfil y el tipo de beca al que tu quieres aplicar</h2>
        <p className="input-helper">
          Include at minimum country or nationality, language(s), and scholarship type.
        </p>

        <label className="field-group profile-textarea">
          <span>Your profile and scholarship goals</span>
          <textarea
            value={profileText}
            onChange={(event) => {
              setProfileText(event.target.value);
              setProfileError("");
            }}
            placeholder="I am Ecuadorian, I speak Spanish as my native language and English B1, and I am looking for partial or full scholarships for undergraduate studies in Information Technology..."
          />
          <small>
            Write one clear profile paragraph. This is sent to the backend as raw_profile_text.
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

        <button className="form-submit" type="submit" disabled={isProcessing}>
          {isProcessing ? "Searching..." : "Find scholarships"}
        </button>
      </div>

      {hasSubmitted ? (
        <ProgressPanel steps={workflowSteps} logs={logs} isRunning={isProcessing} />
      ) : (
        <section className="processing-card processing-card-idle" aria-label="Processing preview">
          <p className="terminal-label">terminal</p>
          <pre>{`$ waiting_for_profile
> submit your written profile to start matching
> backend endpoint: /search`}</pre>
        </section>
      )}

      {pageMessage ? (
        <section className="message-panel message-panel-warning" role="status">
          <div>
            <p className="section-kicker">Search status</p>
            <p>{pageMessage}</p>
          </div>
        </section>
      ) : null}

      {hasSubmitted && !isProcessing ? (
        <ScholarshipResults results={scholarshipResults} />
      ) : null}
    </form>
  );
}

function markInitialStepsRunning(): WorkflowStep[] {
  return INITIAL_STEPS.map((step, index) => ({
    ...step,
    status: index === 0 ? "running" : "pending",
  }));
}

function markInitialStepsFailed(): WorkflowStep[] {
  return INITIAL_STEPS.map((step, index) => ({
    ...step,
    status: index === 0 ? "failed" : "skipped",
  }));
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
