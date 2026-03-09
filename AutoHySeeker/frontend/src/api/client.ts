import axios, { AxiosError } from "axios";
import { DEFAULT_SETTINGS, useSettingsStore } from "@/stores/settingsStore";

type ErrorPayload = { detail?: string } | string | null | undefined;

export class NetworkError extends Error {
  constructor(message = "AutoHySeeker API is unreachable.") {
    super(message);
    this.name = "NetworkError";
  }
}

export class HttpError extends Error {
  status: number;
  detail: string;
  endpoint?: string;

  constructor(status: number, detail: string, endpoint?: string) {
    super(detail);
    this.name = "HttpError";
    this.status = status;
    this.detail = detail;
    this.endpoint = endpoint;
  }
}

export class ValidationError extends HttpError {
  constructor(detail = "Validation failed.", endpoint?: string) {
    super(422, detail, endpoint);
    this.name = "ValidationError";
  }
}

const readDetail = (payload: ErrorPayload): string => {
  if (typeof payload === "string") {
    return payload;
  }
  if (payload && typeof payload.detail === "string") {
    return payload.detail;
  }
  return "";
};

export const getErrorMessage = (error: unknown): string => {
  if (error instanceof ValidationError) {
    return error.detail;
  }
  if (error instanceof HttpError) {
    return `[${error.status}] ${error.detail}`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "An unexpected error occurred.";
};

export const apiClient = axios.create({
  baseURL: DEFAULT_SETTINGS.apiBaseUrl,
  timeout: DEFAULT_SETTINGS.requestTimeoutMs,
  headers: {
    "Content-Type": "application/json"
  }
});

apiClient.interceptors.request.use((config) => {
  const settings = useSettingsStore.getState();
  config.baseURL = settings.apiBaseUrl || DEFAULT_SETTINGS.apiBaseUrl;
  config.timeout = settings.requestTimeoutMs || DEFAULT_SETTINGS.requestTimeoutMs;
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ErrorPayload>) => {
    if (!error.response) {
      return Promise.reject(new NetworkError());
    }

    const detail = readDetail(error.response.data) || error.message || "Request failed.";
    const endpoint = error.config?.url;

    if (error.response.status === 422) {
      return Promise.reject(new ValidationError(detail, endpoint));
    }

    return Promise.reject(new HttpError(error.response.status, detail, endpoint));
  }
);

