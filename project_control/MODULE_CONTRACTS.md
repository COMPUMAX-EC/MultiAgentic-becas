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
- official_link
- application_url
- pdf_url
- display_link
- source_validation_status

## Source Validation Output

Required fields:
- url
- source_type
- validation_status

Allowed validation_status:
- accepted
- accepted_with_warning
- rejected

Accepted source types:
- university
- institute
- institution
- government
- organization
- foundation
- company
- verified_news
- verified_magazine
- verified_newspaper
- official_pdf

## Final Result Output

Required fields:
- scholarship_name
- display_link
- source_url
- official_link
- priority_label
- final_score
- compatibility_score
- eligibility_decision

## Frontend Display Contract

Recommended section:
- show all recommended scholarships

Less recommended section:
- show maximum 10

Each visible result:
- scholarship name
- Open button using display_link