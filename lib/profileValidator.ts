import { NormalizedProfile } from "./profileNormalizer";

export type ProfileValidationMessage = {
  field: string;
  message: string;
};

export type ProfileValidationResult = {
  isValid: boolean;
  errors: ProfileValidationMessage[];
  warnings: ProfileValidationMessage[];
};

const ACCEPTED_LANGUAGE_LEVELS = new Set([
  "Native",
  "A1",
  "A2",
  "B1",
  "B2",
  "C1",
  "C2",
]);

export function validateProfile(
  profile: NormalizedProfile,
): ProfileValidationResult {
  const errors: ProfileValidationMessage[] = [];
  const warnings: ProfileValidationMessage[] = [];

  requireText(profile.nationality, "nationality", "Nationality is required.", errors);
  requireText(
    profile.country_of_residence,
    "country_of_residence",
    "Country of residence is required.",
    errors,
  );
  requireText(
    profile.academic_level,
    "academic_level",
    "Academic level is required.",
    errors,
  );
  requireText(
    profile.field_of_study,
    "field_of_study",
    "Field of study is required.",
    errors,
  );
  requireText(
    profile.scholarship_type,
    "scholarship_type",
    "Scholarship type is required.",
    errors,
  );
  requireText(
    profile.preferred_modality,
    "preferred_modality",
    "Preferred modality is required.",
    errors,
  );

  validateLanguages(profile.languages, errors, warnings);

  if (!profile.interests.length) {
    warnings.push({
      field: "interests",
      message: "Interests are optional, but they help improve scholarship matching.",
    });
  }

  if (!profile.target_countries.length) {
    errors.push({
      field: "target_countries",
      message: "At least one target country is required.",
    });
  }

  validateBudget(profile, errors);

  if (profile.raw_profile_text && errors.length > 0) {
    warnings.push({
      field: "raw_profile_text",
      message:
        "Some structured fields are incomplete. They will need normalization before search.",
    });
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}

function requireText(
  value: string,
  field: string,
  message: string,
  errors: ProfileValidationMessage[],
) {
  if (!value.trim()) {
    errors.push({ field, message });
  }
}

function validateLanguages(
  languages: NormalizedProfile["languages"],
  errors: ProfileValidationMessage[],
  warnings: ProfileValidationMessage[],
) {
  if (!Array.isArray(languages) || languages.length === 0) {
    errors.push({
      field: "languages",
      message: "At least one language is required.",
    });
    return;
  }

  languages.forEach((languageEntry, index) => {
    const field = `languages.${index}`;
    if (!languageEntry.language.trim()) {
      errors.push({
        field,
        message: "Language name is required.",
      });
    }

    if (!languageEntry.level.trim()) {
      warnings.push({
        field,
        message: "Language level is missing.",
      });
      return;
    }

    if (!ACCEPTED_LANGUAGE_LEVELS.has(languageEntry.level)) {
      warnings.push({
        field,
        message: `Language level "${languageEntry.level}" is not a standard option.`,
      });
    }
  });
}

function validateBudget(
  profile: NormalizedProfile,
  errors: ProfileValidationMessage[],
) {
  if (!profile.budget.currency.trim()) {
    errors.push({
      field: "budget.currency",
      message: "Budget currency is required.",
    });
  }

  const contribution = profile.budget.max_personal_contribution;
  if (contribution === null) {
    return;
  }

  if (
    typeof contribution !== "number" ||
    !Number.isFinite(contribution) ||
    contribution < 0
  ) {
    errors.push({
      field: "budget.max_personal_contribution",
      message: "Maximum personal contribution must be a number greater than or equal to 0.",
    });
  }
}
