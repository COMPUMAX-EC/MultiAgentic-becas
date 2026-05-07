const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const DEFAULT_TIMEOUT_MS = 8000;

export class ApiClientError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiClientError";
  }
}

export function getApiBaseUrl() {
  return (
    process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
    DEFAULT_API_BASE_URL
  );
}

export async function apiGet<T>(path: string, timeoutMs = DEFAULT_TIMEOUT_MS) {
  return requestJson<T>("GET", path, undefined, timeoutMs);
}

export async function apiPost<T>(
  path: string,
  payload: unknown,
  timeoutMs = DEFAULT_TIMEOUT_MS,
) {
  return requestJson<T>("POST", path, payload, timeoutMs);
}

export async function apiPostFormData<T>(
  path: string,
  formData: FormData,
  timeoutMs = DEFAULT_TIMEOUT_MS,
) {
  return request<T>("POST", path, formData, timeoutMs);
}

async function requestJson<T>(
  method: "GET" | "POST",
  path: string,
  payload?: unknown,
  timeoutMs = DEFAULT_TIMEOUT_MS,
) {
  return request<T>(
    method,
    path,
    payload === undefined ? undefined : JSON.stringify(payload),
    timeoutMs,
    payload === undefined ? undefined : { "Content-Type": "application/json" },
  );
}

async function request<T>(
  method: "GET" | "POST",
  path: string,
  body?: BodyInit,
  timeoutMs = DEFAULT_TIMEOUT_MS,
  headers?: HeadersInit,
) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${getApiBaseUrl()}${path}`, {
      method,
      headers,
      body,
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new ApiClientError(
        `Backend request failed with status ${response.status}.`,
      );
    }

    try {
      return (await response.json()) as T;
    } catch (error) {
      throw new ApiClientError("Backend returned invalid JSON.");
    }
  } catch (error) {
    if (error instanceof ApiClientError) {
      throw error;
    }

    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiClientError("Backend request timed out.");
    }

    throw new ApiClientError("Backend is unavailable.");
  } finally {
    window.clearTimeout(timeoutId);
  }
}
