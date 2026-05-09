# Module Contracts

## Minimum Required Input

Before global search, the user must provide:

Required:
- country_or_nationality
- languages
- scholarship_type

If missing, return:
- status: needs_more_information
- missing_required_fields
- message

Global search must not run when required fields are missing.

---

## Profile Understanding Output

Required fields:
- raw_profile_text
- normalized_profile
- country_or_nationality
- country_of_residence
- languages
- academic_level
- field_of_study
- specialization
- interests
- target_countries
- scholarship_type
- budget
- preferred_modality
- detected_input_language
- normalization_warnings

Rules:
- normalize fields to English when required by schema
- correct common typos when confidence is high
- do not invent highly specific facts
- preserve uncertainty in warnings

---

## Search Intent Output

Required fields:
- country_or_nationality
- languages
- scholarship_type
- academic_level
- field_of_study
- specialization
- target_countries
- budget
- modality only if explicitly provided
- search_specificity
- missing_optional_fields
- warnings
- search_signature

Rules:
- do not include modality if user did not specify it
- do not force default target countries
- do not use demo/sample profile values

---

## Query Generation Output

Required fields:
- query
- query_family
- target_country
- source_family
- reason

Query families:
- destination
- nationality
- field
- academic_level
- scholarship_type
- university
- government
- embassy
- international_organization
- foundation
- company
- professional_association
- verified_secondary_source

---

## Search Result Output

Required fields:
- title
- url
- snippet
- source
- source_domain
- query_used
- query_family
- source_family

Rules:
- preserve url
- url becomes source_url later
- do not drop candidates before validation except obvious duplicates

---

## Candidate Deduplication Output

Required fields:
- deduplicated_candidates
- duplicate_count
- deduplication_reason

Deduplication priority:
- canonical URL
- normalized URL
- title + domain
- scholarship name + institution if already extracted

Prefer candidates with better links:
1. official_link
2. application_url
3. source_url
4. pdf_url

---

## Source Validation Output

Required fields:
- url
- source_domain
- source_type
- validation_status
- validation_reason
- warnings

Allowed validation_status:
- accepted
- accepted_with_warning
- rejected

Trusted source types:
- university
- government
- embassy
- international_organization
- recognized_foundation
- official_company
- professional_association
- official_pdf

Secondary guidance source types:
- verified_news
- verified_magazine
- verified_newspaper
- verified_education_portal

Rejected source types:
- generic_blog
- spam
- copied_aggregator
- unknown_unverified
- non_scholarship_page
- no_traceable_url

---

## Untrusted Source Output

Required fields:
- url
- domain
- rejection_reason
- source_type
- first_seen_at
- last_checked_at

Rules:
- store untrusted sources separately
- avoid revisiting known untrusted domains in future searches
- do not store trusted sources in this list

---

## Page Reading Output

Required fields:
- source_url
- page_title
- cleaned_text
- read_status
- read_error
- source_type
- validation_status
- query_used

Rules:
- accepted and accepted_with_warning sources proceed to reading
- failed reads should not stop the full pipeline

---

## Scholarship Extraction Output

Required fields:
- scholarship_name
- institution
- country
- academic_level
- eligible_nationalities
- required_languages
- fields
- benefits
- deadline
- deadline_status
- requirements
- source_url
- official_link
- application_url
- pdf_url
- display_link
- source_validation_status

Rules:
- do not reject only because optional data is incomplete
- preserve source_url
- extract official/application links when possible

---

## Useful Link Resolution

display_link priority:
1. official_link
2. application_url
3. source_url
4. pdf_url

Final visible results must have display_link.

If no useful link exists, do not include the scholarship in final visible results.

---

## Compatibility Scoring Output

Required fields:
- scholarship_name
- compatibility_points
- max_possible_points
- matched_profile_fields
- missing_profile_fields
- risk_factors
- source_trust_score
- final_score
- compatibility_score

Point rule:
Each profile item matched by the scholarship gives one point.

Possible points:
- nationality compatible
- language compatible
- academic level compatible
- field compatible
- target country compatible
- scholarship type compatible
- budget compatible
- modality compatible only if user specified modality
- active/current scholarship
- trusted source
- useful official/traceable link

---

## Final Result Output

Required fields:
- scholarship_name
- display_link
- source_url
- official_link
- application_url
- pdf_url
- priority_label
- final_score
- compatibility_score
- eligibility_decision
- matched_profile_fields
- missing_profile_fields
- risk_factors

---

## Frontend Display Contract

Recommended section:
- show all recommended scholarships

Less recommended section:
- show maximum 10

Each visible result:
- scholarship name
- Open button using display_link

No visible result should appear without a useful link.

---

## Pipeline Metrics Output

Required fields:
- generated_queries_count
- sources_found_count
- sources_deduplicated_count
- sources_accepted_count
- sources_accepted_with_warning_count
- sources_rejected_count
- pages_read_count
- pages_failed_count
- scholarships_extracted_count
- scholarships_with_useful_link_count
- expired_rejected_count
- matched_count
- ranked_count
- recommended_count
- less_recommended_count