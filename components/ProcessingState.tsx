"use client";

import { useEffect, useState } from "react";

const PROCESSING_STEPS = [
  "Reading free-text profile",
  "Checking scholarship goals",
  "Preparing written profile payload",
  "Selecting recommended opportunities",
  "Separating less recommended options",
];

type ProcessingStateProps = {
  runId: number;
  onComplete: () => void;
  helperMessage?: string;
  completionMessage?: string;
};

export function ProcessingState({
  runId,
  onComplete,
  helperMessage,
  completionMessage = "Recommendations are ready for review.",
}: ProcessingStateProps) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const isComplete = currentStepIndex >= PROCESSING_STEPS.length;
  const completedCount = Math.min(currentStepIndex, PROCESSING_STEPS.length);
  const progressValue = Math.round(
    (completedCount / PROCESSING_STEPS.length) * 100,
  );

  useEffect(() => {
    setCurrentStepIndex(0);

    const intervalId = window.setInterval(() => {
      setCurrentStepIndex((stepIndex) => {
        if (stepIndex >= PROCESSING_STEPS.length) {
          window.clearInterval(intervalId);
          return stepIndex;
        }

        return stepIndex + 1;
      });
    }, 650);

    return () => window.clearInterval(intervalId);
  }, [runId]);

  useEffect(() => {
    if (isComplete) {
      onComplete();
    }
  }, [isComplete, onComplete]);

  return (
    <section className="processing-card" aria-live="polite">
      <div className="processing-header">
        <div>
          <p className="terminal-label">terminal</p>
          <h3>{isComplete ? "Processing complete" : PROCESSING_STEPS[currentStepIndex]}</h3>
          {helperMessage ? (
            <p className="processing-helper">{helperMessage}</p>
          ) : null}
        </div>
        <span className="progress-count">{progressValue}%</span>
      </div>

      <div
        className="progress-track"
        role="progressbar"
        aria-label="Profile processing progress"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={progressValue}
      >
        <span style={{ width: `${progressValue}%` }} />
      </div>

      <ol className="processing-steps" aria-label="Processing log">
        {PROCESSING_STEPS.map((step, index) => {
          const status = getStepStatus(index, currentStepIndex);
          return (
            <li className={`processing-step processing-step-${status}`} key={step}>
              <span className="step-status">{formatStatus(status)}</span>
              <span>{step}</span>
            </li>
          );
        })}
      </ol>

      {isComplete ? (
        <p className="processing-result">
          {completionMessage}
        </p>
      ) : null}
    </section>
  );
}

function getStepStatus(stepIndex: number, currentStepIndex: number) {
  if (stepIndex < currentStepIndex) {
    return "completed";
  }
  if (stepIndex === currentStepIndex) {
    return "current";
  }
  return "pending";
}

function formatStatus(status: string) {
  if (status === "completed") {
    return "ok";
  }
  if (status === "current") {
    return "run";
  }
  return "wait";
}
