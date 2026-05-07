import {
  ScholarshipPriorityLabel,
  ScholarshipResult,
  WorkflowStep,
  WorkflowStepStatus,
} from "../types/scholarship";

export type ScholarshipResponseMapping = {
  results: ScholarshipResult[];
  workflowSteps: WorkflowStep[];
  workflowLogs: string[];
  warnings: string[];
  isPartialFailure: boolean;
  isUnsupportedShape: boolean;
};

export function mapScholarshipResponse(payload: unknown): ScholarshipResult[] {
  return mapScholarshipResponseDetails(payload).results;
}

export function mapScholarshipResponseDetails(
  payload: unknown,
): ScholarshipResponseMapping {
  const records = dedupeScholarshipRecords(findScholarshipRecords(payload));
  const warnings = collectWarnings(payload);
  const isPartialFailure = detectPartialFailure(payload);

  return {
    results: records.map((record, index) => {
      const item = isRecord(record) ? record : {};
      return {
        id: textValue(item.id) || `backend-scholarship-${index + 1}`,
        scholarship_name:
          textValue(item.scholarship_name) ||
          textValue(item.name) ||
          "Untitled scholarship",
        institution: textValue(item.institution) || "Institution not specified",
        country: textValue(item.country) || "Country not specified",
        final_score: scoreValue(item.final_score),
        compatibility_score: scoreValue(item.compatibility_score),
        eligibility_decision:
          textValue(item.eligibility_decision) || "insufficient_information",
        priority_label: priorityValue(
          textValue(item.priority_label) ||
            textValue(item.priority) ||
            textValue(item.match_quality) ||
            textValue(item.eligibility_decision),
        ),
        recommendation_summary:
          textValue(item.recommendation_summary) ||
          textValue(item.recommendation_reason) ||
          "No recommendation summary was provided.",
        ranking_reasons: listValue(item.ranking_reasons),
        risk_factors: listValue(item.risk_factors),
        missing_requirements: listValue(item.missing_requirements),
        source_url:
          textValue(item.source_url) ||
          textValue(item.official_link) ||
          textValue(item.url) ||
          textValue(item.link) ||
          "",
        benefits: listValue(item.benefits),
        requirements: listValue(item.requirements),
        deadline: textValue(item.deadline),
        eligible_nationalities: listValue(item.eligible_nationalities),
        required_languages: listValue(item.required_languages),
        fields: listValue(item.fields),
      };
    }),
    workflowSteps: findWorkflowSteps(payload),
    workflowLogs: findWorkflowLogs(payload),
    warnings,
    isPartialFailure,
    isUnsupportedShape: isRecord(payload) && !records.length && !hasKnownResultKey(payload),
  };
}

function findWorkflowSteps(payload: unknown): WorkflowStep[] {
  const stepRecords = findWorkflowStepRecords(payload);

  return stepRecords.map((record, index) => {
    const item = isRecord(record) ? record : {};
    const fallbackLabel = `Workflow step ${index + 1}`;

    return {
      id: textValue(item.id) || textValue(item.key) || `workflow-step-${index + 1}`,
      label:
        textValue(item.step_name) ||
        textValue(item.label) ||
        textValue(item.name) ||
        textValue(item.step) ||
        fallbackLabel,
      status: workflowStatusValue(item.status),
      count: optionalNumberValue(item.count),
      countLabel:
        textValue(item.count_label) ||
        textValue(item.countLabel) ||
        textValue(item.metric),
      message:
        textValue(item.message) ||
        textValue(item.log) ||
        textValue(item.detail),
    };
  });
}

function findWorkflowStepRecords(payload: unknown): unknown[] {
  if (!isRecord(payload)) {
    return [];
  }

  const possibleKeys = [
    "workflow_steps",
    "workflowSteps",
    "pipeline_steps",
    "pipelineSteps",
    "progress",
  ];

  for (const key of possibleKeys) {
    const value = payload[key];
    if (Array.isArray(value)) {
      return value;
    }

    if (isRecord(value)) {
      const nestedRecords = findWorkflowStepRecords(value);
      if (nestedRecords.length) {
        return nestedRecords;
      }
    }
  }

  return [];
}

function findWorkflowLogs(payload: unknown): string[] {
  if (!isRecord(payload)) {
    return [];
  }

  const possibleKeys = [
    "workflow_logs",
    "workflowLogs",
    "progress_logs",
    "progressLogs",
    "terminal_logs",
    "terminalLogs",
    "logs",
  ];

  for (const key of possibleKeys) {
    const value = payload[key];
    const logs = logListValue(value);
    if (logs.length) {
      return logs;
    }

    if (isRecord(value)) {
      const nestedLogs = findWorkflowLogs(value);
      if (nestedLogs.length) {
        return nestedLogs;
      }
    }
  }

  return [];
}

function findScholarshipRecords(payload: unknown): unknown[] {
  if (Array.isArray(payload)) {
    return payload;
  }

  if (!isRecord(payload)) {
    return [];
  }

  const possibleKeys = [
    "top_recommendations",
    "ranked_results",
    "ranked_recommendations",
    "recommendations",
    "results",
    "scholarships",
    "matches",
    "data",
  ];

  for (const key of possibleKeys) {
    const value = payload[key];
    if (Array.isArray(value)) {
      return value;
    }

    if (isRecord(value)) {
      const nestedRecords = findScholarshipRecords(value);
      if (nestedRecords.length) {
        return nestedRecords;
      }
    }
  }

  return [];
}

function dedupeScholarshipRecords(records: unknown[]) {
  const seen = new Set<string>();
  const uniqueRecords: unknown[] = [];

  for (const record of records) {
    const item = isRecord(record) ? record : {};
    const urlKey =
      textValue(item.source_url) ||
      textValue(item.official_link) ||
      textValue(item.url) ||
      textValue(item.link);
    const nameKey =
      textValue(item.scholarship_name) ||
      textValue(item.name) ||
      "Untitled scholarship";
    const key = urlKey
      ? `url:${urlKey.toLowerCase()}`
      : `name:${nameKey.toLowerCase()}`;

    if (seen.has(key)) {
      continue;
    }

    seen.add(key);
    uniqueRecords.push(record);
  }

  return uniqueRecords;
}

function hasKnownResultKey(payload: Record<string, unknown>) {
  return [
    "top_recommendations",
    "ranked_results",
    "ranked_recommendations",
    "recommendations",
    "results",
    "scholarships",
    "matches",
    "data",
  ].some((key) => key in payload);
}

function detectPartialFailure(payload: unknown): boolean {
  if (!isRecord(payload)) {
    return false;
  }

  const status = textValue(payload.status).toLowerCase();
  const demoStatus = textValue(payload.demo_status).toLowerCase();
  return (
    status === "partial_failure" ||
    demoStatus === "partial_failure" ||
    Boolean(payload.partial_failure)
  );
}

function collectWarnings(payload: unknown): string[] {
  if (!isRecord(payload)) {
    return [];
  }

  return [
    textValue(payload.message),
    ...listValue(payload.warnings),
    ...listValue(payload.errors),
    textValue(payload.error),
  ].filter(Boolean);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function textValue(value: unknown) {
  return typeof value === "string" ? value.trim() : "";
}

function scoreValue(value: unknown) {
  const score = typeof value === "number" ? value : Number(value);
  return Number.isFinite(score) ? Math.max(0, Math.min(100, score)) : 0;
}

function optionalNumberValue(value: unknown) {
  const count = typeof value === "number" ? value : Number(value);
  return Number.isFinite(count) ? count : undefined;
}

function listValue(value: unknown) {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => String(item).trim())
    .filter(Boolean);
}

function logListValue(value: unknown) {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => {
      if (typeof item === "string") {
        return item.trim();
      }

      if (isRecord(item)) {
        return (
          textValue(item.message) ||
          textValue(item.log) ||
          textValue(item.detail) ||
          textValue(item.text)
        );
      }

      return "";
    })
    .filter(Boolean);
}

function priorityValue(value: unknown): ScholarshipPriorityLabel {
  const priority = textValue(value).toLowerCase();
  if (
    priority === "high_priority" ||
    priority === "medium_priority" ||
    priority === "low_priority" ||
    priority === "not_recommended"
  ) {
    return priority;
  }

  if (priority === "strong_match") {
    return "high_priority";
  }

  if (priority === "possible_match") {
    return "medium_priority";
  }

  if (priority === "weak_match") {
    return "low_priority";
  }

  if (
    priority === "not_eligible" ||
    priority === "insufficient_information"
  ) {
    return "not_recommended";
  }

  return "not_recommended";
}

function workflowStatusValue(value: unknown): WorkflowStepStatus {
  const status = textValue(value).toLowerCase();
  if (
    status === "completed" ||
    status === "active" ||
    status === "pending" ||
    status === "failed" ||
    status === "skipped"
  ) {
    return status;
  }

  if (status === "running" || status === "current" || status === "in_progress") {
    return "active";
  }

  if (status === "done" || status === "success" || status === "ok") {
    return "completed";
  }

  if (status === "error") {
    return "failed";
  }

  return "pending";
}
