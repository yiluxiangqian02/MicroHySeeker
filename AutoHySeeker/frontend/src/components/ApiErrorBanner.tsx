import { HttpError, ValidationError, getErrorMessage } from "@/api/client";

interface ApiErrorBannerProps {
  error: unknown;
  title?: string;
  onRetry?: () => void;
  className?: string;
}

const getSeverityLabel = (error: unknown): string => {
  if (error instanceof ValidationError) {
    return "Validation Error";
  }
  if (error instanceof HttpError) {
    return `HTTP ${error.status}`;
  }
  return "Request Error";
};

export function ApiErrorBanner({
  error,
  title = "Unable to load data",
  onRetry,
  className = ""
}: ApiErrorBannerProps) {
  return (
    <div className={`rounded-lg border border-red-200 bg-red-50 p-4 ${className}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="text-sm font-semibold text-red-700">{title}</p>
          <p className="text-sm text-red-600">{getSeverityLabel(error)}</p>
          <p className="text-sm text-red-600">{getErrorMessage(error)}</p>
        </div>
        {onRetry ? (
          <button
            type="button"
            onClick={onRetry}
            className="rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700"
          >
            Retry
          </button>
        ) : null}
      </div>
    </div>
  );
}

