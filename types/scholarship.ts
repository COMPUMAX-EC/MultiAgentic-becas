export type ScholarshipPriorityLabel =
  | "high_priority"
  | "medium_priority"
  | "low_priority"
  | "not_recommended";

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

export type ScholarshipResult = {
  id: string;
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
  benefits?: string[];
  requirements?: string[];
  deadline?: string;
  eligible_nationalities?: string[];
  required_languages?: string[];
  fields?: string[];
};
