# Module Contracts

## Profile Input

Input:
data/profiles/sample_profile.json

Required fields:
- nationality
- country_of_residence
- languages
- academic_level
- field_of_study
- interests
- target_countries
- scholarship_type
- budget
- preferred_modality

## Query Generation Output

Output:
list of search queries

Required fields:
- query
- target_country
- reason

## Search Result Output

Required fields:
- title
- url
- snippet
- source

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
- requirements
- source_url

## Matching Output

Required fields:
- scholarship_name
- compatibility_score
- matched_factors
- missing_or_risk_factors
- recommendation_reason
- source_url