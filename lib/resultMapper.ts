import {
  ScholarshipPriorityLabel,
  PipelineMetrics,
  RejectionSummary,
  ScholarshipResult,
  WorkflowStep,
  WorkflowStepStatus,
} from "../types/scholarship";

export type ScholarshipResponseMapping = {
  results: ScholarshipResult[];
  workflowSteps: WorkflowStep[];
  workflowLogs: string[];
  warnings: string[];
  status: string;
  message: string;
  missingRequiredFields: string[];
  metrics: PipelineMetrics;
  rejectionSummary: RejectionSummary;
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
  const hasMetrics = isRecord(payload) && isRecord(payload.metrics);
  const warnings = collectWarnings(payload, hasMetrics);
  const isPartialFailure = detectPartialFailure(payload);

  return {
    results: records.map((record, index) => {
      const item = isRecord(record) ? record : {};
      return {
        id: textValue(item.id) || `backend-scholarship-${index + 1}`,
        rank: optionalNumberValue(item.rank),
        scholarship_name:
          textValue(item.scholarship_name) ||
          textValue(item.name) ||
          "Untitled scholarship",
        institution: textValue(item.institution) || "Institution not specified",
        country: textValue(item.country) || "Country not specified",
        final_score: scoreValue(item.final_score),
        compatibility_score: scoreValue(item.compatibility_score),
        compatibility_points: nonNegativeIntValue(item.compatibility_points),
        max_possible_points: nonNegativeIntValue(item.max_possible_points),
        source_trust_score: scoreValue(item.source_trust_score),
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
        matched_profile_fields: listValue(
          item.matched_profile_fields || item.matched_factors,
        ),
        missing_profile_fields: listValue(item.missing_profile_fields),
        source_url: usefulLink(item.source_url, item.url, item.link) || "",
        official_link: usefulLink(item.official_link),
        application_url: usefulLink(item.application_url, item.apply_url),
        pdf_url: usefulLink(item.pdf_url),
        display_link: usefulLink(
          item.display_link,
          item.official_link,
          item.application_url,
          item.apply_url,
          item.source_url,
          item.pdf_url,
          item.url,
          item.link,
        ),
        benefits: listValue(item.benefits),
        requirements: listValue(item.requirements),
        deadline: textValue(item.deadline),
        eligible_nationalities: listValue(item.eligible_nationalities),
        required_languages: listValue(item.required_languages),
        fields: listValue(item.fields),
        result_section: resultSectionValue(item.result_section),
      };
    }),
    workflowSteps: findWorkflowSteps(payload),
    workflowLogs: findWorkflowLogs(payload),
    warnings,
    status: isRecord(payload) ? textValue(payload.status) : "",
    message: isRecord(payload) ? textValue(payload.message) : "",
    missingRequiredFields: isRecord(payload)
      ? listValue(payload.missing_required_fields || payload.missingRequiredFields)
      : [],
    metrics: metricsValue(isRecord(payload) ? payload.metrics : undefined),
    rejectionSummary: rejectionSummaryValue(
      isRecord(payload) ? payload.rejection_summary || payload.rejectionSummary : undefined,
    ),
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

  const groupedRecords = findGroupedScholarshipRecords(payload);
  if (groupedRecords.length) {
    return groupedRecords;
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

function findGroupedScholarshipRecords(payload: Record<string, unknown>): unknown[] {
  const recommendedRecords = markResultSection(payload.recommended, "recommended");
  const lessRecommendedRecords = markResultSection(
    payload.less_recommended || payload.lessRecommended,
    "less_recommended",
  );

  return [...recommendedRecords, ...lessRecommendedRecords];
}

function markResultSection(
  value: unknown,
  resultSection: "recommended" | "less_recommended",
) {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .filter(isRecord)
    .map((record) => ({
      ...record,
      result_section: resultSection,
    }));
}

function dedupeScholarshipRecords(records: unknown[]) {
  const seen = new Set<string>();
  const uniqueRecords: unknown[] = [];

  for (const record of records) {
    const item = isRecord(record) ? record : {};
    const urlKey = usefulLink(
      item.display_link,
      item.official_link,
      item.application_url,
      item.apply_url,
      item.source_url,
      item.pdf_url,
      item.url,
      item.link,
    );
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
    "recommended",
    "less_recommended",
    "lessRecommended",
    "results",
    "scholarships",
    "matches",
    "data",
  ].some((key) => key in payload);
}

function resultSectionValue(value: unknown) {
  const resultSection = textValue(value);
  if (resultSection === "recommended" || resultSection === "less_recommended") {
    return resultSection;
  }
  return undefined;
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

function collectWarnings(payload: unknown, hasMetrics: boolean): string[] {
  if (!isRecord(payload)) {
    return [];
  }

  const warnings = [
    textValue(payload.message),
    ...listValue(payload.warnings),
    ...listValue(payload.errors),
    textValue(payload.error),
  ].filter(Boolean);

  if (!hasMetrics) {
    warnings.push("Backend did not return pipeline metrics.");
  }

  return warnings;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function textValue(value: unknown) {
  return typeof value === "string" ? value.trim() : "";
}

function usefulLink(...values: unknown[]) {
  for (const value of values) {
    const rawValue = textValue(value);
    if (!rawValue) {
      continue;
    }

    const normalizedValue = rawValue.replace(/\s+/g, " ");
    const lowerValue = normalizedValue.toLowerCase();
    if (
      lowerValue.startsWith("javascript:") ||
      lowerValue.startsWith("mailto:") ||
      lowerValue.startsWith("file:") ||
      lowerValue.startsWith("data:") ||
      normalizedValue.startsWith("/") ||
      normalizedValue.startsWith("\\") ||
      normalizedValue.startsWith(".")
    ) {
      continue;
    }

    const candidate =
      normalizedValue.includes("://") ||
      normalizedValue.startsWith("www.") ||
      normalizedValue.split("/", 1)[0]?.includes(".")
        ? normalizedValue.includes("://")
          ? normalizedValue
          : `https://${normalizedValue}`
        : "";

    if (!candidate) {
      continue;
    }

    try {
      const parsedUrl = new URL(candidate);
      if (
        (parsedUrl.protocol === "http:" || parsedUrl.protocol === "https:") &&
        parsedUrl.hostname
      ) {
        return parsedUrl.toString();
      }
    } catch {
      continue;
    }
  }

  return "";
}

function scoreValue(value: unknown) {
  const score = typeof value === "number" ? value : Number(value);
  return Number.isFinite(score) ? Math.max(0, Math.min(100, score)) : 0;
}

function optionalNumberValue(value: unknown) {
  const count = typeof value === "number" ? value : Number(value);
  return Number.isFinite(count) ? count : undefined;
}

function nonNegativeIntValue(value: unknown) {
  const count = optionalNumberValue(value);
  return typeof count === "number" ? Math.max(0, Math.trunc(count)) : undefined;
}

function metricsValue(value: unknown): PipelineMetrics {
  const item = isRecord(value) ? value : {};
  return {
    generated_queries_count: countValue(item.generated_queries_count),
    sources_found_count: countValue(item.sources_found_count),
    sources_deduplicated_count: countValue(item.sources_deduplicated_count),
    expansion_rounds_used: countValue(item.expansion_rounds_used),
    untrusted_sources_skipped_count: countValue(
      item.untrusted_sources_skipped_count,
    ),
    secondary_guidance_sources_count: countValue(
      item.secondary_guidance_sources_count,
    ),
    sources_accepted_count: countValue(item.sources_accepted_count),
    sources_accepted_with_warning_count: countValue(
      item.sources_accepted_with_warning_count,
    ),
    sources_rejected_count: countValue(item.sources_rejected_count),
    pages_read_count: countValue(item.pages_read_count),
    pages_failed_count: countValue(item.pages_failed_count),
    scholarships_extracted_count: countValue(item.scholarships_extracted_count),
    scholarships_with_useful_link_count: countValue(
      item.scholarships_with_useful_link_count,
    ),
    expired_rejected_count: countValue(item.expired_rejected_count),
    matched_count: countValue(item.matched_count),
    ranked_count: countValue(item.ranked_count),
    recommended_count: countValue(item.recommended_count),
    less_recommended_count: countValue(item.less_recommended_count),
  };
}

function rejectionSummaryValue(value: unknown): RejectionSummary {
  const item = isRecord(value) ? value : {};
  return {
    duplicate: countValue(item.duplicate),
    known_untrusted_source: countValue(item.known_untrusted_source),
    non_scholarship_page: countValue(item.non_scholarship_page),
    untrusted_source: countValue(item.untrusted_source),
    validation_failed: countValue(item.validation_failed),
    expired_or_closed: countValue(item.expired_or_closed),
    no_useful_link: countValue(item.no_useful_link),
    read_failed: countValue(item.read_failed),
    extraction_failed: countValue(item.extraction_failed),
    profile_missing_required_fields: countValue(
      item.profile_missing_required_fields,
    ),
    other: countValue(item.other),
  };
}

function countValue(value: unknown) {
  const count = optionalNumberValue(value);
  return typeof count === "number" ? Math.max(0, Math.trunc(count)) : 0;
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
    priority === "possible_match" ||
    priority === "low_priority" ||
    priority === "insufficient_information" ||
    priority === "not_recommended" ||
    priority === "rejected"
  ) {
    return priority;
  }

  if (priority === "confirmed_match" || priority === "likely_match" || priority === "strong_match") {
    return "high_priority";
  }

  if (priority === "possible_match") {
    return "possible_match";
  }

  if (priority === "weak_match") {
    return "low_priority";
  }

  if (priority === "insufficient_information") {
    return "insufficient_information";
  }

  if (priority === "not_eligible" || priority === "mismatch") {
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
    return "running";
  }

  if (status === "done" || status === "success" || status === "ok") {
    return "completed";
  }

  if (status === "error") {
    return "failed";
  }

  return "pending";
}
