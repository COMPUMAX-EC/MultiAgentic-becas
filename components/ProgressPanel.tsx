"use client";

import { ReactNode } from "react";
import { WorkflowStep } from "../types/scholarship";

const MAX_VISIBLE_LOG_LINES = 200;

export type ProgressLogLine = {
  id: string;
  message: string;
  tone?: "default" | "success" | "warning" | "error";
};

type ProgressPanelProps = {
  steps: WorkflowStep[];
  logs: ProgressLogLine[];
  isRunning: boolean;
  headline?: string;
  actions?: ReactNode;
};

export function ProgressPanel({
  steps,
  logs,
  isRunning,
  headline = "Progress & quick actions",
  actions,
}: ProgressPanelProps) {
  const completedCount = steps.filter((step) => step.status === "completed").length;
  const failedCount = steps.filter((step) => step.status === "failed").length;
  const activeStep = steps.find(
    (step) => step.status === "active" || step.status === "running",
  );
  const visibleLogs = logs.slice(-MAX_VISIBLE_LOG_LINES);

  return (
    <section className="terminal-panel" aria-live="polite" aria-label="Progress and quick actions">
      <div className="terminal-panel-bar">
        <div className="mini-bee-mark" aria-hidden="true" />
        <div>
          <p className="terminal-label">ScholarBee pipeline</p>
          <h2>{headline}</h2>
        </div>
        <span className={`terminal-run-state ${failedCount ? "terminal-run-state-failed" : ""}`}>
          {failedCount ? "failed" : isRunning ? "running" : "complete"}
        </span>
      </div>

      <div className="terminal-summary" aria-label="Pipeline counts">
        <span>{completedCount}/{steps.length} steps complete</span>
        <span>{failedCount} failed</span>
        <span>{activeStep ? `active: ${activeStep.label}` : "active: none"}</span>
      </div>

      {actions ? <div className="quick-actions-panel">{actions}</div> : null}

      <ol className="terminal-step-grid" aria-label="Pipeline steps">
        {steps.map((step, index) => {
          const visualStatus = step.status === "running" ? "active" : step.status;
          return (
            <li className={`terminal-step terminal-step-${visualStatus}`} key={step.id}>
              <span className="terminal-step-index">{String(index + 1).padStart(2, "0")}</span>
              <span className="terminal-step-copy">
                <strong>{step.label}</strong>
                {step.message ? <small>{step.message}</small> : null}
              </span>
              {typeof step.count === "number" ? (
                <span className="terminal-step-count">
                  {step.count}
                  {step.countLabel ? <small>{step.countLabel}</small> : null}
                </span>
              ) : null}
            </li>
          );
        })}
      </ol>

      <div className="terminal-log" aria-label="Search log lines">
        {logs.length ? (
          visibleLogs.map((log) => (
            <p className={`terminal-log-line terminal-log-line-${log.tone || "default"}`} key={log.id}>
              <span>$</span>
              {log.message}
            </p>
          ))
        ) : (
          <p className="terminal-log-line">
            <span>$</span>
            Waiting for profile input.
          </p>
        )}
        {logs.length > visibleLogs.length ? (
          <p className="terminal-log-line terminal-log-line-warning">
            <span>$</span>
            Showing latest {visibleLogs.length} log lines of {logs.length}.
          </p>
        ) : null}
      </div>
    </section>
  );
}
