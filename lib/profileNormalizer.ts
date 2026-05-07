export type GuidedProfileValues = {
  rawProfileText: string;
  nationality: string;
  countryOfResidence: string;
  languages: string;
  languageLevel: string;
  academicLevel: string;
  fieldOfStudy: string;
  interests: string;
  targetCountries: string;
  scholarshipType: string;
  budgetCurrency: string;
  maxPersonalContribution: string;
  preferredModality: string;
};

export type NormalizedProfile = {
  nationality: string;
  country_of_residence: string;
  languages: Array<{
    language: string;
    level: string;
  }>;
  academic_level: string;
  field_of_study: string;
  interests: string[];
  target_countries: string[];
  scholarship_type: string;
  budget: {
    currency: string;
    max_personal_contribution: number | null;
  };
  preferred_modality: string;
  raw_profile_text: string;
};

const LANGUAGE_LEVELS = new Set(["native", "a1", "a2", "b1", "b2", "c1", "c2"]);

export function normalizeProfile(values: GuidedProfileValues): NormalizedProfile {
  return {
    nationality: normalizeText(values.nationality),
    country_of_residence: normalizeText(values.countryOfResidence),
    languages: normalizeLanguages(values.languages, values.languageLevel),
    academic_level: normalizeAcademicLevel(values.academicLevel),
    field_of_study: normalizeText(values.fieldOfStudy),
    interests: splitList(values.interests),
    target_countries: splitList(values.targetCountries),
    scholarship_type: normalizeText(values.scholarshipType),
    budget: {
      currency: normalizeText(values.budgetCurrency).toLowerCase(),
      max_personal_contribution: normalizeBudgetAmount(
        values.maxPersonalContribution,
      ),
    },
    preferred_modality: normalizeText(values.preferredModality),
    raw_profile_text: normalizeText(values.rawProfileText),
  };
}

function normalizeLanguages(languageText: string, selectedLevel: string) {
  const fallbackLevel = normalizeLanguageLevel(selectedLevel);

  return splitList(languageText).map((entry) => {
    const parsedEntry = parseLanguageEntry(entry);
    return {
      language: parsedEntry.language,
      level: parsedEntry.level || fallbackLevel,
    };
  });
}

function parseLanguageEntry(entry: string) {
  const parts = normalizeText(entry).split(" ").filter(Boolean);
  const lastPart = parts[parts.length - 1] || "";

  if (parts.length > 1 && LANGUAGE_LEVELS.has(lastPart.toLowerCase())) {
    return {
      language: parts.slice(0, -1).join(" "),
      level: normalizeLanguageLevel(lastPart),
    };
  }

  return {
    language: parts.join(" "),
    level: "",
  };
}

function splitList(value: string) {
  const seen = new Set<string>();
  const items: string[] = [];

  for (const item of value.split(",")) {
    const normalizedItem = normalizeText(item);
    const comparisonKey = normalizedItem.toLowerCase();
    if (!normalizedItem || seen.has(comparisonKey)) {
      continue;
    }

    seen.add(comparisonKey);
    items.push(normalizedItem);
  }

  return items;
}

function normalizeAcademicLevel(value: string) {
  const normalizedValue = normalizeText(value).toLowerCase();
  const academicLevelMap: Record<string, string> = {
    bachelor: "bachelors",
    bachelors: "bachelors",
    undergraduate: "bachelors",
    master: "masters",
    masters: "masters",
    graduate: "masters",
    phd: "phd",
    doctorate: "phd",
    doctoral: "phd",
    technical: "technical",
    other: "other",
  };

  return academicLevelMap[normalizedValue] || normalizedValue;
}

function normalizeLanguageLevel(value: string) {
  const normalizedValue = normalizeText(value);
  if (normalizedValue.toLowerCase() === "native") {
    return "Native";
  }

  return LANGUAGE_LEVELS.has(normalizedValue.toLowerCase())
    ? normalizedValue.toUpperCase()
    : normalizedValue;
}

function normalizeBudgetAmount(value: string) {
  const normalizedValue = normalizeText(value);
  if (!normalizedValue) {
    return null;
  }

  const parsedValue = Number(normalizedValue);
  return parsedValue;
}

function normalizeText(value: string) {
  return value.trim().replace(/\s+/g, " ");
}
