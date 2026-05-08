export type ScholarshipPriorityLabel =
  | "high_priority"
  | "medium_priority"
  | "possible_match"
  | "low_priority"
  | "insufficient_information"
  | "not_recommended"
  | "rejected";

export type WorkflowStepStatus =
  | "completed"
  | "active"
  | "pending"
  | "failed"
  | "skipped";

export type WorkflowStep = {
  id: string;
  label: string;
  status: WorkflowStepStatus;
  count?: number;
  countLabel?: string;
  message?: string;
};

export type PipelineMetrics = {
  generated_queries_count: number;
  sources_found_count: number;
  sources_deduplicated_count: number;
  sources_accepted_count: number;
  sources_accepted_with_warning_count: number;
  sources_rejected_count: number;
  pages_read_count: number;
  pages_failed_count: number;
  scholarships_extracted_count: number;
  scholarships_with_useful_link_count: number;
  expired_rejected_count: number;
  matched_count: number;
  ranked_count: number;
  recommended_count: number;
  less_recommended_count: number;
};

export type RejectionSummary = {
  non_scholarship_page: number;
  untrusted_source: number;
  expired_or_closed: number;
  no_useful_link: number;
  duplicate: number;
  read_failed: number;
  extraction_failed: number;
};

export type ScholarshipResult = {
  id: string;
  rank?: number;
  scholarship_name: string;
  institution: string;
  country: string;
  final_score: number;
  compatibility_score: number;
  eligibility_decision: string;
  priority_label: ScholarshipPriorityLabel;
  recommendation_summary: string;
  ranking_reasons: string[];
  risk_factors: string[];
  missing_requirements: string[];
  source_url: string;
  official_link?: string;
  application_url?: string;
  pdf_url?: string;
  display_link?: string;
  benefits?: string[];
  requirements?: string[];
  deadline?: string;
  eligible_nationalities?: string[];
  required_languages?: string[];
  fields?: string[];
  result_section?: "recommended" | "less_recommended";
};
