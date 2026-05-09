import { NormalizedProfile } from "../lib/profileNormalizer";
import { apiGet, apiPost } from "../lib/apiClient";
import {
  mapScholarshipResponse,
  mapScholarshipResponseDetails,
  ScholarshipResponseMapping,
} from "../lib/resultMapper";

type BackendPayload = Record<string, unknown>;
const GLOBAL_SEARCH_TIMEOUT_MS = 600000;

export type ProfileSearchSubmission = {
  rawProfileText: string;
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
  const payload = await postJsonSearch(submission);
  return mapScholarshipResponseDetails(payload);
}

async function postJsonSearch(submission: ProfileSearchSubmission) {
  return apiPost<BackendPayload>(
    "/search",
    {
      raw_profile_text: submission.rawProfileText.trim(),
      profile: null,
    },
    GLOBAL_SEARCH_TIMEOUT_MS,
  );
}

export async function normalizeProfile(profilePayload: unknown) {
  return apiPost<BackendPayload>("/profile/normalize", profilePayload, 15000);
}
