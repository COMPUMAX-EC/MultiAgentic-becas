import { NormalizedProfile } from "../lib/profileNormalizer";
import { ApiClientError, apiGet, apiPost, apiPostFormData } from "../lib/apiClient";
import {
  mapScholarshipResponse,
  mapScholarshipResponseDetails,
  ScholarshipResponseMapping,
} from "../lib/resultMapper";

type BackendPayload = Record<string, unknown>;
const GLOBAL_SEARCH_TIMEOUT_MS = 600000;

export type ProfileSearchSubmission = {
  rawProfileText: string;
  cvPdf?: File | null;
};

export async function checkBackendHealth() {
  return apiGet<BackendPayload>("/health", 5000);
}

export async function getLatestDemo() {
  const payload = await apiGet<BackendPayload>("/demo/latest", 10000);
  return mapScholarshipResponse(payload);
}

export async function getLatestDemoResponse() {
  const payload = await apiGet<BackendPayload>("/demo/latest", 20000);
  return mapScholarshipResponseDetails(payload);
}

export async function searchScholarships(profile: NormalizedProfile) {
  const payload = await apiPost<BackendPayload>(
    "/search",
    { profile },
    GLOBAL_SEARCH_TIMEOUT_MS,
  );
  return mapScholarshipResponse(payload);
}

export async function searchScholarshipsResponse(profile: NormalizedProfile) {
  const payload = await apiPost<BackendPayload>(
    "/search",
    { profile },
    GLOBAL_SEARCH_TIMEOUT_MS,
  );
  return mapScholarshipResponseDetails(payload);
}

export async function searchScholarshipsWithProfileInput(
  submission: ProfileSearchSubmission,
): Promise<ScholarshipResponseMapping> {
  const payload = submission.cvPdf
    ? await postMultipartSearch(submission)
    : await postJsonSearch(submission);

  return mapScholarshipResponseDetails(payload);
}

async function postJsonSearch(submission: ProfileSearchSubmission) {
  return apiPost<BackendPayload>(
    "/search",
    {
      raw_profile_text: submission.rawProfileText,
      profile: null,
    },
    GLOBAL_SEARCH_TIMEOUT_MS,
  );
}

async function postMultipartSearch(submission: ProfileSearchSubmission) {
  const formData = new FormData();
  formData.append("raw_profile_text", submission.rawProfileText);

  if (submission.cvPdf) {
    formData.append("cv_pdf", submission.cvPdf);
  }

  try {
    return await apiPostFormData<BackendPayload>(
      "/search-with-profile-document",
      formData,
      GLOBAL_SEARCH_TIMEOUT_MS,
    );
  } catch (error) {
    if (!shouldFallbackToSearchEndpoint(error)) {
      throw error;
    }

    return apiPostFormData<BackendPayload>(
      "/search",
      formData,
      GLOBAL_SEARCH_TIMEOUT_MS,
    );
  }
}

function shouldFallbackToSearchEndpoint(error: unknown) {
  return (
    error instanceof ApiClientError &&
    (error.message.includes("status 404") ||
      error.message.includes("status 405") ||
      error.message.includes("status 422"))
  );
}

export async function normalizeProfile(profilePayload: unknown) {
  return apiPost<BackendPayload>("/profile/normalize", profilePayload, 15000);
}
